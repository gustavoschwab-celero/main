# Regras de Relatório — Higiene

> Regras de higiene para os reports da rotina, conforme feedback de 2026-09-01.

## Pendências abertas

### E-mails sem resposta
- Se não há e-mail pendente, **não** registrar como "pendência aberta" nem explicar.
- Apenas sinalizar que não há pendência de e-mail.

### Threads de Slack
- Se não há ação pendente, **não** explicar.
- Apenas reportar que não há pendência.

## Prioridades do dia

### Higiene de cadastro
- Reavaliar a posição sobre higiene de cadastro conforme os ajustes de entendimento por deal (ver `entendimento.md`), em especial a separação BRB SUGOV × BRB SUSEB.

## Regras adicionais (feedback de 2026-09-10)

### Verificar avanço real antes de declarar "sem movimento"
- Nunca declarar "sem sinal de avanço", "zero movimento" ou equivalente sobre um deal só com base nos campos de propriedade (notes_last_contacted, hs_next_step, hs_lastmodifieddate). Esses campos não capturam notas manuais.
- Antes de concluir isso, buscar as NOTES/engagements associadas ao deal no HubSpot (search_crm_objects objectType NOTE, associatedWith o deal) e ler o conteúdo.
- Caso confirmado: BRB SUSEB tinha avanço real registrado em nota manual em 03/09 (ligação do Distretti/SUSEB, cronograma atualizado) que o digest de 09/09 e 10/09 não capturou por checar só propriedades do deal.

### Amount/closedate vazio só é problema a partir de Client Evaluation
- Amount_in_home_currency e closedate vazios ou zerados só entram como prioridade de higiene de dado a partir da etapa **Client Evaluation** (inclusive) em diante.
- Em Prospecting, Qualifying e Structuring isso é esperado e normal — não sinalizar como falha de higiene nessas etapas.

### BNB — sem reunião formal externa
- BNB é processo licitatório, tratativas via sistema. Não existem reuniões com participantes externos na agenda para esse deal — não tratar isso como gap/risco de reunião não registrada.

### BASA — checar conversa de Atuação antes de sinalizar risco
- Antes de sinalizar risco no BASA, conferir a DM do Slack entre Gustavo e o bot "Claude" (user ID `U0BFJ7VCW67`, canal `D0BU9J7PBL4`) por atualizações de "Atuação BASA".
