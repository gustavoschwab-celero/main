# Análise de vídeos (LinkedIn e outros)

O Claude não escuta áudio. Ele lê texto e imagens. Este script converte o vídeo nesses dois formatos:

- **Transcrição** do que é falado (Whisper, roda localmente, sem custo de API)
- **Quadros-chave**, imagens do que aparece na tela (slides, gráficos, texto)
- **`resumo.md`**, que junta metadados, texto do post, lista de quadros e transcrição com marcação de tempo

## Instalação (uma vez)

```bash
# ffmpeg
brew install ffmpeg            # macOS
winget install ffmpeg          # Windows
sudo apt install ffmpeg        # Linux

# dependências Python
pip install -r ferramentas/video/requirements.txt
```

## Uso

```bash
# Post do LinkedIn, usando a sessão já logada no Chrome (necessário para a maioria dos posts)
python ferramentas/video/analisar_video.py "https://www.linkedin.com/posts/..." --cookies-navegador chrome

# Arquivo já baixado
python ferramentas/video/analisar_video.py ~/Downloads/video.mp4
```

Depois, no Claude Code:

> leia `video_xxx/resumo.md` e os quadros, e resuma o vídeo destacando os pontos relevantes para a Celero

### Opções úteis

| Opção | Padrão | Para quê |
|---|---|---|
| `--cookies-navegador` | — | `chrome`, `edge`, `firefox`, `brave`, `safari`. Usa seu login no download. |
| `--modelo` | `small` | `tiny`/`base` são mais rápidos; `medium`/`large-v3` são mais precisos. |
| `--idioma` | `pt` | Idioma falado (`en`, `es`…) ou `auto`. |
| `--max-quadros` | `40` | Limite de imagens geradas. |
| `--intervalo` | `10` | Segundos entre quadros quando há poucas trocas de cena (ex.: pessoa falando para a câmera). |
| `--sem-transcricao` / `--sem-quadros` | — | Pula uma das etapas. |

## Observações

- Na primeira transcrição, o modelo Whisper é baixado de `huggingface.co` (~500 MB para `small`).
- Nas sessões do Claude Code na nuvem, `linkedin.com`, `licdn.com` e `huggingface.co` precisam estar liberados em *Network access* do ambiente. Sem isso, rode o script localmente e envie a pasta gerada.
- O Chrome precisa estar fechado para que `--cookies-navegador chrome` consiga ler os cookies em alguns sistemas (principalmente no Windows).
