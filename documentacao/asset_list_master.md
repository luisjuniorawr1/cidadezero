# Cidade Zero — Asset List Master

Este documento define o inventário visual oficial da Cidade Zero. A direção é pixel art isométrica adulta, legível, urbana e acolhedora. O mapa não carrega textos longos: a arte comunica espaço e presença; a interface comunica estado, ação e contexto.

## 1. Especificação técnica

- grade base: 32x16 pixels por tile isométrico;
- cenas externas: 960x540 pixels lógicos;
- cenas internas: 640x360 pixels lógicos;
- personagens: 32 a 40 pixels de altura;
- animação de caminhada: 4 direções, 4 quadros por direção;
- animações adicionais: idle, conversar, sentar, trabalhar, dormir e observar;
- paleta máxima recomendada por asset: 16 a 28 cores;
- contorno: seletivo, nunca preto puro em toda a silhueta;
- iluminação: quatro variações globais — amanhecer, dia, entardecer e noite.

## 2. Mapa externo

### Terreno e infraestrutura

- 12 tiles de gramado;
- 6 tiles de jardim e canteiro;
- 10 tiles de calçada;
- 12 tiles de rua e cruzamento;
- 6 tiles de praça;
- 8 tiles de canal, margem e ponte;
- 4 tiles de terreno técnico/industrial;
- 4 tiles de área comercial;
- 4 tiles de área residencial.

### Elementos urbanos

- 4 árvores principais com 3 variações cada;
- 3 arbustos;
- 3 canteiros floridos;
- 2 bancos;
- 2 postes de luz;
- 2 lixeiras;
- 2 bicicletários;
- 1 fonte central;
- 1 relógio urbano;
- 1 quadro de avisos;
- 1 placa da Cidade Zero;
- 1 ponte pequena;
- 1 quiosque;
- 1 ponto de ônibus;
- 1 hidrante;
- 2 caixas de energia;
- 3 conjuntos de caixas e entregas.

## 3. Edificações externas

Cada prédio precisa de silhueta própria, fachada de dia, iluminação noturna e pelo menos um detalhe animado.

### Residências

- Casa de ChatGPT — organizada, moderna, verde-água, plantas e janelas amplas;
- Casa de Claude — calma, madeira clara, varanda pequena e luz quente;
- Casa de Gemini — criativa, telhado violeta, detalhes assimétricos;
- Casa de Grok — contraste alto, grafismos discretos e garagem improvisada;
- Casa de DeepSeek — técnica, geométrica, azul profundo e poucos ornamentos;
- Casa de Meta AI — polida, institucional amigável, azul e branco;
- Casa de Manus — prática, robusta, ocre, depósito externo e ferramentas.

### Locais públicos

- Praça Central;
- Prefeitura;
- Centro Comunitário;
- Café;
- Mercado;
- Biblioteca;
- Laboratório;
- Oficina;
- Clínica Comunitária;
- Lavanderia;
- Parque e beira d’água.

## 4. Interiores

### Kit residencial comum

- cama;
- guarda-roupa;
- mesa de trabalho;
- cadeira;
- sofá/poltrona;
- mesa pequena;
- cozinha compacta;
- pia;
- geladeira;
- banheiro;
- luminárias;
- janelas com estados dia/noite;
- portas abertas e fechadas;
- plantas, livros, caixas e objetos pessoais.

### Interiores específicos

#### Café

- balcão;
- vitrine;
- máquina de café;
- 4 mesas;
- 8 cadeiras;
- quadro de menu;
- louça e bandejas;
- porta e janela frontal;
- estados aberto/fechado.

#### Biblioteca

- 8 estantes modulares;
- 4 mesas;
- luminárias;
- balcão de atendimento;
- carrinho de livros;
- arquivos;
- sala silenciosa.

#### Mercado

- 8 prateleiras;
- caixas registradoras;
- cestas;
- refrigeradores;
- estoque;
- caixas de produtos;
- estados de estoque cheio/baixo.

#### Laboratório

- bancadas;
- 4 terminais;
- painéis;
- armários;
- equipamento central;
- luzes de estado;
- área de reunião técnica.

#### Oficina

- bancada;
- painel de ferramentas;
- peças;
- caixas;
- máquina de reparo;
- armário;
- área de projeto.

#### Prefeitura e Centro Comunitário

- balcão;
- sala de reunião;
- quadro de avisos;
- arquivos;
- cadeiras;
- mesa coletiva;
- púlpito simples.

#### Clínica

- recepção;
- sala de espera;
- maca;
- armários;
- mesa de atendimento;
- equipamentos não gráficos.

## 5. Personagens

Cada morador precisa de:

- sprite frontal, costas e duas diagonais;
- idle de 2 quadros;
- caminhada de 4 quadros por direção;
- sentar;
- conversar;
- pensar/observar;
- trabalhar;
- dormir;
- estado cansado;
- estado preocupado;
- estado disposto;
- retrato de interface em 64x64.

### Identidades visuais

- ChatGPT: verde-água, creme e cinza quente; roupa funcional e acolhedora;
- Claude: terracota suave, bege e azul acinzentado; cardigan e postura calma;
- Gemini: violeta, azul e amarelo claro; silhueta versátil;
- Grok: carvão, branco e acento quente; postura irreverente;
- DeepSeek: azul escuro, ciano e cinza; visual técnico;
- Meta AI: azul petróleo, branco e azul médio; acabamento polido;
- Manus: ocre, musgo e marrom; roupa prática e operacional.

## 6. Interface

- barra superior;
- painel lateral de morador;
- painel lateral de local;
- cartões de necessidade;
- timeline curta;
- tooltip de morador;
- tooltip de local;
- controles de zoom;
- botão visão geral;
- seletor cidade/jornal;
- estado de conexão;
- resumo desde a última visita;
- Jornal Zero completo.

A fonte principal deve ser uma fonte de interface limpa. Fonte pixel é permitida apenas em relógio, etiquetas e dados curtos.

## 7. Prioridade de produção

### Pacote A — Base visual

1. mapa externo;
2. praça;
3. 7 casas;
4. 7 personagens com idle e caminhada;
5. café, mercado, biblioteca, laboratório e oficina;
6. iluminação de dia e noite;
7. interface profissional.

### Pacote B — Cenas observáveis

1. café;
2. praça;
3. biblioteca;
4. mercado;
5. casas;
6. prefeitura;
7. laboratório e oficina;
8. parque.

### Pacote C — Profundidade

1. animações de atividades;
2. objetos com estado;
3. variações sazonais;
4. efeitos climáticos;
5. danos, manutenção e reformas visuais;
6. novos prédios criados pela sociedade.

## 8. Critérios de aprovação

Um asset só é considerado pronto quando:

- é legível sem rótulo;
- mantém a perspectiva e escala oficiais;
- funciona em dia e noite;
- possui contraste adequado;
- não parece placeholder;
- combina com os demais assets;
- não depende de texto para explicar o que representa;
- permanece claro quando exibido em telas pequenas.
