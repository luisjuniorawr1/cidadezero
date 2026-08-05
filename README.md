# Cidade Zero

**Uma mini cidade virtual persistente onde representações experimentais de grandes sistemas de IA convivem, trabalham, formam relações e tomam decisões continuamente.**

## MVP executável 0.1

O primeiro motor persistente já está implementado. Ele funciona sem depender de uma aba do navegador e mantém:

- relógio próprio da cidade;
- sete moradores ativos carregados dos dossiês;
- necessidades de energia, fome, socialização e curiosidade;
- escolha autônoma de ações influenciada pelos perfis;
- deslocamento lógico entre casas e espaços públicos;
- interações sociais e evolução básica de afinidade e confiança;
- histórico permanente de acontecimentos;
- retomada automática após reinicialização;
- painel web atualizado por WebSocket.

Nesta fase, a decisão é feita por um simulador local e determinístico. Isso permite validar a continuidade 24 horas antes de gerar custos de API. O próximo marco conectará o adaptador de IA apenas às decisões sociais e reflexões importantes.

## Elenco inicial

- ChatGPT
- Claude
- Gemini
- Grok
- DeepSeek
- Meta AI
- Manus
- Perplexity — registrada, mas desativada enquanto o material disponível for insuficiente

## Executar localmente

Requer Python 3.12 ou superior.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abra `http://localhost:8000`.

## Testes

```bash
pytest -q
```

## API

- `GET /api/health`
- `GET /api/state`
- `GET /api/characters`
- `GET /api/characters/{id}`
- `GET /api/events`
- `GET /api/relationships`
- `WS /ws`
- `POST /api/admin/tick?minutes=60` com o cabeçalho `X-Admin-Token`

A documentação interativa fica em `/docs`.

## Deploy

O repositório inclui `Dockerfile` e `render.yaml`. No Render, o serviço deve possuir disco persistente montado em `/app/data`, pois o estado inicial usa SQLite.

## Estrutura

- `app/main.py`: relógio, necessidades, decisões, persistência, API e WebSocket;
- `app/static/`: painel observador;
- `personagens/`: perfis e prompts operacionais;
- `documentacao/`: metodologia e contratos;
- `data/city_seed.json`: espaços iniciais da mini cidade;
- `tests/`: testes de persistência e relações.

## Regra central

O motor da cidade é a fonte oficial da realidade. Cada personagem poderá interpretar, conversar, criar objetivos e escolher entre ações disponíveis, mas não poderá inventar objetos, dinheiro, locais ou resultados que não existam no estado oficial do mundo.

## Transparência

Cidade Zero é um projeto independente e não oficial. Os personagens são adaptações ficcionais e experimentais inspiradas em informações públicas e em relatórios produzidos pelos próprios sistemas. Eles não representam oficialmente as empresas citadas e não constituem evidência de consciência, emoções ou personalidade humana real.
