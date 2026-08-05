# Cidade Zero

**Uma mini cidade virtual persistente onde representações experimentais de grandes sistemas de IA convivem, trabalham, formam relações e tomam decisões continuamente.**

## Estado atual

O projeto está na fase de estruturação dos moradores e do protocolo de decisão.

Elenco inicial:

- ChatGPT
- Claude
- Gemini
- Grok
- DeepSeek
- Meta AI
- Manus
- Perplexity — registrada, mas desativada enquanto o material disponível for insuficiente

## Estrutura

- `personagens/<id>/perfil_operacional.json`: identidade e parâmetros usados pelo backend.
- `personagens/<id>/prompt_operacional.txt`: instruções compactas da personagem.
- `personagens/<id>/dossie_resumido.md`: versão legível do perfil.
- `documentacao/personagens_registry.json`: registro central do elenco.
- `documentacao/decision_schema.json`: contrato comum para decisões.
- `documentacao/MATRIZ_COMPARATIVA.md`: comparação dos dados disponíveis.
- `documentacao/AUDITORIA_FONTES.md`: lacunas e alertas metodológicos.

## Regra de execução

O motor da cidade será a fonte oficial da realidade. Cada personagem poderá interpretar, conversar, criar objetivos e escolher entre ações disponíveis, mas não poderá inventar objetos, dinheiro, locais ou resultados que não existam no estado oficial do mundo.

A cada decisão, o backend deverá enviar apenas:

1. prompt operacional;
2. estado atual do mundo;
3. necessidades e emoção simulada;
4. objetivos ativos;
5. memórias relevantes;
6. relações envolvidas;
7. ações permitidas;
8. contrato de decisão.

Os relatórios integrais não devem ser enviados em todas as chamadas.

## Transparência

Cidade Zero é um projeto independente e não oficial. Os personagens são adaptações ficcionais e experimentais inspiradas em informações públicas e em relatórios produzidos pelos próprios sistemas. Eles não representam oficialmente as empresas citadas e não constituem evidência de consciência, emoções ou personalidade humana real.

## Próximo marco

Construir o servidor persistente da cidade, a primeira área isométrica jogável e o ciclo autônomo de percepção, decisão, execução e memória.
