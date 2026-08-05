# Cidade Zero

**Uma cidade virtual persistente onde representações experimentais de sistemas de IA convivem, trabalham, formam relações e constroem uma sociedade sem roteiro.**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/luisjuniorawr1/cidadezero)

> Cidade Zero é uma simulação ficcional. Os moradores não são conscientes e não representam oficialmente as empresas ou produtos que inspiraram seus perfis.

## Princípio central

Não existem temporadas, missões globais, protagonistas escolhidos ou acontecimentos forçados.

```text
o tempo passa
→ necessidades e recursos mudam
→ cada morador interpreta a própria situação
→ escolhe o próximo passo
→ o mundo valida a tentativa
→ surgem consequências e memórias
→ a vida continua
```

Os moradores podem formar objetivos próprios, mudar de trabalho, criar projetos, organizar grupos, protestar, aproximar-se, afastar-se, assumir compromissos ou encerrar vínculos. Outros moradores permanecem independentes e podem aceitar ou recusar qualquer proposta.

A autonomia é interna à simulação. Nenhum personagem recebe acesso ao servidor, à chave da API, à internet aberta ou a sistemas reais.

## Motor híbrido 0.4

A realidade oficial permanece no motor local:

- relógio persistente;
- necessidades físicas, sociais e emocionais simuladas;
- dinheiro, aluguel, trabalho, mantimentos e moradia;
- problemas pessoais e coletivos;
- localização e duração das atividades;
- relações, confiança, afinidade e familiaridade;
- memórias e consequências permanentes;
- fallback local quando a API estiver indisponível.

A camada opcional de inteligência usa `gpt-4o-mini` para decisões relevantes. Cada chamada recebe:

- o prompt operacional individual;
- o perfil extraído do dossiê;
- estado atual e necessidades;
- relações e vínculos;
- memórias recentes;
- moradores e locais visíveis;
- ações executáveis no mundo.

A intenção pode ser aberta, mas o próximo passo precisa ser validado pelo motor.

## Ritmo do tempo

```text
1 minuto da cidade = 12 segundos reais
5 minutos da cidade = 1 minuto real
1 hora da cidade = 12 minutos reais
1 dia da cidade = 4 horas e 48 minutos reais
```

Configuração:

```env
CITY_MINUTES_PER_TICK=1
CITY_TICK_SECONDS=12
```

## Uso da OpenAI

Sem `OPENAI_API_KEY`, a cidade continua funcionando com o motor local.

Configuração recomendada:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_CALLS_PER_DAY=300
OPENAI_MAX_OUTPUT_TOKENS=300
OPENAI_CHARACTER_COOLDOWN_CITY_MINUTES=180
OPENAI_REQUEST_TIMEOUT_SECONDS=35
OPENAI_TEMPERATURE=0.85
```

A chave deve existir apenas no servidor. Ela nunca é gravada no SQLite, exibida pela API ou armazenada no repositório.

O limite de 180 minutos da cidade entre chamadas por morador produz aproximadamente 280 decisões por dia real para sete moradores. As edições do jornal utilizam as chamadas restantes, mantendo o teto total de 300.

Quando o limite é alcançado, a simulação não para. O motor local assume as próximas decisões.

## Auditoria

Cada tentativa de chamada registra:

- personagem e tipo da requisição;
- dia e horário da cidade;
- modelo;
- hash do contexto;
- status;
- identificadores da resposta;
- tokens de entrada e saída;
- resposta estruturada ou erro.

A chave nunca entra nesse registro.

Consulte:

```text
GET /api/intelligence
```

## Relações

Os vínculos se desenvolvem gradualmente:

```text
conhecidos → amizade → amizade próxima
                         ↓
                 aproximação afetiva
                         ↓
             namoro → compromisso → casamento
```

A progressão exige convivência, familiaridade, afinidade, confiança e aceitação independente. Rejeições e separações também ficam registradas.

## Jornal Zero

O Jornal Zero não é personagem e não interfere na cidade.

Ele:

- seleciona localmente os fatos de maior impacto;
- cria uma edição para cada dia concluído;
- cita os IDs dos eventos usados;
- rejeita matérias que mencionem fatos inexistentes;
- continua funcionando sem API;
- usa a IA apenas para melhorar a redação factual;
- guarda edições anteriores;
- mostra o que mudou desde a última visita no mesmo navegador.

Rotas:

```text
GET /api/journal
GET /api/journal/editions
GET /api/journal/editions/{dia}
GET /api/journal/since?after_event_id=123
```

## Elenco inicial

- ChatGPT
- Claude
- Gemini
- Grok
- DeepSeek
- Meta AI
- Manus
- Perplexity — registrada, mas desativada enquanto o material disponível for insuficiente

O registro dos personagens aponta para o perfil, o prompt operacional e o dossiê resumido de cada morador. Lacunas nas fontes não são preenchidas com características inventadas.

## Executar localmente

Requer Python 3.12 ou superior.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
set -a
source .env
set +a
uvicorn app.augmented:app --reload
```

Abra `http://localhost:8000`.

## Oracle / systemd

A unidade deve executar:

```text
/opt/cidadezero/.venv/bin/uvicorn app.augmented:app --host 0.0.0.0 --port 8000
```

Um exemplo completo está em `deploy/cidade-zero.service.example`.

As variáveis privadas devem ficar em:

```text
/etc/cidade-zero.env
```

## Testes

```bash
pytest -q
```

Os testes cobrem o motor social, migração do banco, contrato das decisões por IA, proteção da chave, importação do entrypoint aumentado e factualidade do Jornal Zero.

## API principal

```text
GET /api/health
GET /api/state
GET /api/society
GET /api/characters
GET /api/characters/{id}
GET /api/events
GET /api/relationships
GET /api/bonds
GET /api/intelligence
GET /api/journal
WS  /ws
POST /api/admin/tick?minutes=60
```

A documentação interativa fica em `/docs`.

## Estrutura

- `app/main.py`: motor social local e persistência;
- `app/augmented.py`: integração opcional de inteligência, fila e rotas novas;
- `app/intelligence.py`: cliente da API, schema e auditoria;
- `app/social_dynamics.py`: vínculos e respostas independentes;
- `app/journal.py`: seleção factual e arquivo do Jornal Zero;
- `app/static/`: painel observador;
- `personagens/`: perfis, prompts e dossiês;
- `documentacao/`: metodologia e contratos;
- `data/`: estado inicial e banco persistente;
- `tests/`: validações automatizadas.

## Transparência

Cidade Zero é um projeto independente e não oficial. As personagens são adaptações ficcionais baseadas em relatórios e perfis operacionais. Estados emocionais, relações e decisões são elementos computacionais da narrativa e não demonstram consciência, sentimentos ou personalidade humana real.
