#!/usr/bin/env python3
"""Prepara um vídeo (ex.: post do LinkedIn) para o Claude analisar.

Gera, numa pasta de saída:
  - quadros/            imagens-chave do vídeo (troca de cena ou intervalo fixo)
  - audio.wav           áudio mono 16 kHz
  - transcricao.txt     transcrição com marcação de tempo [mm:ss]
  - transcricao.srt     legenda no formato SRT
  - resumo.md           índice único: metadados, quadros e transcrição

Depois é só pedir ao Claude: "leia <saida>/resumo.md e os quadros e resuma o vídeo".

Uso:
  python analisar_video.py "https://www.linkedin.com/posts/..." --cookies-navegador chrome
  python analisar_video.py video.mp4 --modelo medium
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def erro(msg):
    print(f"erro: {msg}", file=sys.stderr)
    sys.exit(1)


def exigir_ffmpeg():
    for exe in ("ffmpeg", "ffprobe"):
        if not shutil.which(exe):
            erro(f"'{exe}' não encontrado. Instale o ffmpeg (brew install ffmpeg / apt install ffmpeg / winget install ffmpeg).")


def formatar_tempo(segundos, srt=False):
    total_ms = int(round(segundos * 1000))
    h, resto = divmod(total_ms, 3_600_000)
    m, resto = divmod(resto, 60_000)
    s, ms = divmod(resto, 1000)
    if srt:
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def baixar(url, saida, navegador):
    try:
        import yt_dlp
    except ImportError:
        erro("yt-dlp não instalado. Rode: pip install -r requirements.txt")

    opcoes = {
        "outtmpl": str(saida / "video.%(ext)s"),
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }
    if navegador:
        # Reaproveita a sessão logada no navegador (a maioria dos posts exige login).
        opcoes["cookiesfrombrowser"] = (navegador,)

    print(f"Baixando {url} ...")
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as e:
            erro(f"falha no download ({e}).\n"
                 "Se o post exige login, use --cookies-navegador chrome (com o Chrome fechado) "
                 "ou baixe o vídeo manualmente e passe o arquivo.")
        if info.get("_type") == "playlist" and info.get("entries"):
            info = info["entries"][0]
        caminho = Path(ydl.prepare_filename(info)).with_suffix(".mp4")

    if not caminho.exists():
        candidatos = sorted(saida.glob("video.*"))
        if not candidatos:
            erro("download concluído, mas o arquivo de vídeo não foi encontrado.")
        caminho = candidatos[0]

    metadados = {
        "titulo": info.get("title"),
        "autor": info.get("uploader") or info.get("channel"),
        "data": info.get("upload_date"),
        "url": info.get("webpage_url") or url,
        "descricao": info.get("description"),
    }
    return caminho, metadados


def duracao(video):
    saida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(saida)["format"]["duration"])


def extrair_quadros(video, pasta, limiar, intervalo, max_quadros, dur):
    """Extrai quadros nas trocas de cena; se houver poucas, usa intervalo fixo."""
    if pasta.exists():
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True)

    def rodar(filtro):
        for f in pasta.glob("*.jpg"):
            f.unlink()
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
             "-vf", f"{filtro},scale='min(1280,iw)':-2,showinfo",
             "-fps_mode", "vfr", "-q:v", "3", str(pasta / "tmp_%05d.jpg")],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            erro(f"ffmpeg falhou ao extrair quadros:\n{proc.stderr[-2000:]}")
        tempos = [float(t) for t in re.findall(r"pts_time:([\d.]+)", proc.stderr)]
        arquivos = sorted(pasta.glob("tmp_*.jpg"))
        return list(zip(tempos, arquivos))

    # O primeiro quadro sempre entra; depois, cada troca de cena acima do limiar.
    quadros = rodar(f"select='eq(n\\,0)+gt(scene\\,{limiar})'")
    minimo = max(3, int(dur // max(intervalo * 3, 1)))
    if len(quadros) < minimo:
        quadros = rodar(f"fps=1/{intervalo}")

    if len(quadros) > max_quadros:
        passo = len(quadros) / max_quadros
        manter = {int(i * passo) for i in range(max_quadros)}
        for i, (_, arq) in enumerate(quadros):
            if i not in manter:
                arq.unlink()
        quadros = [q for i, q in enumerate(quadros) if i in manter]

    final = []
    for i, (t, arq) in enumerate(quadros, 1):
        nome = f"quadro_{i:03d}_{formatar_tempo(t).replace(':', 'm')}s.jpg"
        destino = arq.with_name(nome)
        arq.rename(destino)
        final.append((t, destino))
    return final


def extrair_audio(video, destino):
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
         "-vn", "-ac", "1", "-ar", "16000", str(destino)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        if "does not contain any stream" in proc.stderr or "Output file #0 does not contain" in proc.stderr:
            return False
        erro(f"ffmpeg falhou ao extrair o áudio:\n{proc.stderr[-2000:]}")
    return destino.exists() and destino.stat().st_size > 1000


def transcrever(audio, modelo, idioma):
    """Retorna (idioma_detectado, [(inicio, fim, texto), ...])."""
    lingua = None if idioma == "auto" else idioma
    print(f"Transcrevendo com Whisper (modelo '{modelo}'; a 1ª execução baixa o modelo)...")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        WhisperModel = None

    if WhisperModel:
        try:
            model = WhisperModel(modelo, device="auto", compute_type="auto")
        except Exception as e:
            erro(f"não foi possível carregar o modelo Whisper '{modelo}' ({type(e).__name__}: {e}).\n"
                 "Na 1ª execução o modelo é baixado de huggingface.co — verifique a conexão/proxy.")
        segmentos, info = model.transcribe(str(audio), language=lingua, vad_filter=True)
        return info.language, [(s.start, s.end, s.text.strip()) for s in segmentos]

    try:
        import whisper
    except ImportError:
        erro("nenhum Whisper instalado. Rode: pip install -r requirements.txt")
    model = whisper.load_model(modelo)
    resultado = model.transcribe(str(audio), language=lingua)
    return resultado.get("language"), [
        (s["start"], s["end"], s["text"].strip()) for s in resultado["segments"]
    ]


def salvar_transcricao(segmentos, saida):
    txt = "\n".join(f"[{formatar_tempo(i)}] {t}" for i, _, t in segmentos)
    (saida / "transcricao.txt").write_text(txt + "\n", encoding="utf-8")
    srt = "\n".join(
        f"{n}\n{formatar_tempo(i, srt=True)} --> {formatar_tempo(f, srt=True)}\n{t}\n"
        for n, (i, f, t) in enumerate(segmentos, 1)
    )
    (saida / "transcricao.srt").write_text(srt, encoding="utf-8")
    return txt


def escrever_resumo(saida, origem, metadados, dur, quadros, idioma, transcricao):
    linhas = ["# Material do vídeo para análise", ""]
    linhas.append("> Para o Claude: leia este arquivo e abra as imagens listadas em *Quadros-chave*. "
                  "Combine o que é dito (transcrição) com o que aparece na tela (quadros).")
    linhas += ["", "## Metadados", "", f"- **Origem:** {origem}", f"- **Duração:** {formatar_tempo(dur)}"]
    for chave, rotulo in (("titulo", "Título"), ("autor", "Autor"), ("data", "Data")):
        if metadados.get(chave):
            linhas.append(f"- **{rotulo}:** {metadados[chave]}")
    if idioma:
        linhas.append(f"- **Idioma detectado:** {idioma}")
    if metadados.get("descricao"):
        linhas += ["", "### Texto do post", "", metadados["descricao"].strip()]

    linhas += ["", "## Quadros-chave", ""]
    if quadros:
        linhas += [f"- `{formatar_tempo(t)}` — `quadros/{arq.name}`" for t, arq in quadros]
    else:
        linhas.append("_(extração de quadros desativada)_")

    linhas += ["", "## Transcrição", ""]
    linhas.append(transcricao if transcricao else "_(sem transcrição: desativada ou vídeo sem áudio)_")
    (saida / "resumo.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Extrai quadros e transcrição de um vídeo para análise pelo Claude.")
    p.add_argument("entrada", help="URL do post/vídeo (LinkedIn, YouTube etc.) ou caminho de um arquivo local")
    p.add_argument("--saida", type=Path, help="pasta de saída (padrão: ./video_<nome>)")
    p.add_argument("--cookies-navegador", metavar="NAVEGADOR",
                   help="usa a sessão logada do navegador no download: chrome, edge, firefox, brave, safari")
    p.add_argument("--modelo", default="small",
                   help="modelo Whisper: tiny, base, small, medium, large-v3 (padrão: small)")
    p.add_argument("--idioma", default="pt", help="código do idioma falado ou 'auto' (padrão: pt)")
    p.add_argument("--limiar-cena", type=float, default=0.3, help="sensibilidade à troca de cena, 0–1 (padrão: 0.3)")
    p.add_argument("--intervalo", type=float, default=10, help="segundos entre quadros no modo intervalo (padrão: 10)")
    p.add_argument("--max-quadros", type=int, default=40, help="limite de quadros (padrão: 40)")
    p.add_argument("--sem-transcricao", action="store_true", help="não transcreve o áudio")
    p.add_argument("--sem-quadros", action="store_true", help="não extrai quadros")
    a = p.parse_args()

    exigir_ffmpeg()
    eh_url = re.match(r"^https?://", a.entrada) is not None

    if eh_url:
        saida = a.saida or Path("video_" + re.sub(r"\W+", "_", a.entrada.rstrip("/").split("/")[-1])[:40])
        saida.mkdir(parents=True, exist_ok=True)
        video, metadados = baixar(a.entrada, saida, a.cookies_navegador)
    else:
        video = Path(a.entrada)
        if not video.is_file():
            erro(f"arquivo não encontrado: {video}")
        saida = a.saida or Path(f"video_{video.stem}")
        saida.mkdir(parents=True, exist_ok=True)
        metadados = {}

    dur = duracao(video)
    print(f"Vídeo: {video} ({formatar_tempo(dur)})")

    quadros = []
    if not a.sem_quadros:
        quadros = extrair_quadros(video, saida / "quadros", a.limiar_cena, a.intervalo, a.max_quadros, dur)
        print(f"{len(quadros)} quadros salvos em {saida / 'quadros'}")

    idioma, transcricao = None, ""
    if not a.sem_transcricao:
        audio = saida / "audio.wav"
        if extrair_audio(video, audio):
            idioma, segmentos = transcrever(audio, a.modelo, a.idioma)
            transcricao = salvar_transcricao(segmentos, saida)
            print(f"Transcrição: {len(segmentos)} trechos em {saida / 'transcricao.txt'}")
        else:
            print("O vídeo não tem áudio; transcrição ignorada.")

    escrever_resumo(saida, a.entrada, metadados, dur, quadros, idioma, transcricao)
    print(f"\nPronto. Peça ao Claude: \"leia {saida / 'resumo.md'} e os quadros e resuma o vídeo\".")


if __name__ == "__main__":
    main()
