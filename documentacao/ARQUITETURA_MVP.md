# Arquitetura do MVP

## Objetivo

Manter uma cidade virtual persistente em que personagens artificiais percebam o estado do mundo, tomem decisões estruturadas, executem ações permitidas e formem memórias.

## Componentes

1. **Motor do mundo** — relógio, mapa, objetos, economia, regras e consequências objetivas.
2. **Orquestrador de agentes** — agenda ciclos de percepção e decisão.
3. **Memória** — eventos, crenças, relações e resumos autobiográficos.
4. **Adaptador de modelo** — envia contexto compacto ao fornecedor de IA e valida a resposta.
5. **Cliente visual** — renderiza a cidade isométrica e acompanha o estado oficial.
6. **Diretor de transmissão** — seleciona cenas relevantes e produz resumos.

## Ciclo de uma decisão

1. reunir estado atual e percepção disponível;
2. recuperar objetivos e memórias relevantes;
3. listar ações permitidas;
4. solicitar decisão conforme `decision_schema.json`;
5. validar a resposta;
6. executar a ação no motor;
7. registrar consequências e memória;
8. transmitir o novo estado aos espectadores.

## Regra de segurança e coerência

O modelo propõe intenções e ações. O motor decide o que existe, o que é permitido e qual foi o resultado objetivo.
