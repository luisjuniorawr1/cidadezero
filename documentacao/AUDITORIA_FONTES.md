# Auditoria dos relatórios recebidos

Os oito arquivos foram extraídos e avaliados sem preencher partes ausentes. A completude abaixo é uma estimativa operacional, não uma nota de qualidade da IA.

| Personagem | Estado | Completude estimada | Partes ausentes | Perfil utilizável |
|---|---|---:|---|---|
| ChatGPT | `parcial_operacional` | 58% | 12, 13, 14, 15, 16, 17, 18, 19 | sim |
| Claude | `operacional_sem_auditoria_final` | 95% | 19 | sim |
| Gemini | `operacional_completo` | 100% | - | sim |
| Grok | `operacional_sem_json_expandido` | 92% | - | sim |
| DeepSeek | `operacional_sem_json_expandido` | 92% | - | sim |
| Meta AI | `operacional_sem_json_expandido` | 92% | - | sim |
| Manus | `operacional_com_alerta_de_integridade` | 85% | - | sim |
| Perplexity | `fonte_insuficiente_nao_operacional` | 5% | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 | não |

## Alertas importantes

- **ChatGPT:** o PDF termina na seção 11; não foram recebidas as partes 12 a 19.
- **Claude:** contém as partes 1 a 18; a Parte 19 permanece ausente, conforme solicitado.
- **Grok, DeepSeek e Meta AI:** os textos dizem que existe um JSON completo, mas não o apresentam expandido. Os perfis operacionais foram montados das seções textuais existentes.
- **Manus:** o JSON extraído está quebrado e o documento atribui Manus a Google/Gemini. Essa atribuição não é sustentada de forma clara pelo próprio material e deve ser verificada antes de qualquer divulgação pública. O perfil comportamental pode ser testado, mas a ficha técnica não deve ser publicada como fato.
- **Perplexity:** o PDF é apenas uma nota dizendo que o dossiê completo existiu em outro chat. Não há conteúdo suficiente para criar uma personagem sem inventar dados; por isso ela foi mantida desativada.

## Limitação metodológica

Os relatórios são autorrelatos produzidos por sistemas diferentes, com extensões, versões e critérios de resposta diferentes. Eles servem como material narrativo e de estudo de caso, mas não constituem comparação científica controlada nem prova de personalidade real.
