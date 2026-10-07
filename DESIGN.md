---
name: Finapple
description: App financeiro pessoal e gamificado — cofre discreto em grafite e dourado, abacaxi lapidado como logo.
colors:
  dourado: "#C2A15A"
  dourado-claro: "#E3C77E"
  azul-aco: "#8FB0BF"
  verde-claro: "#5AC27D"
  carbono-fundo: "#1A2227"
  carbono-superficie: "#222C32"
  carbono-borda: "#2F3B42"
  icone-fundo: "#2A353C"
  icone-borda: "#36434A"
  texto: "#E6EAEC"
  texto-titulo: "#C9D0D3"
  texto-suave: "#9AA6AC"
  seta: "#7D8A90"
  prata: "#A9B3B8"
  receita: "#4CAF50"
  despesa-erro: "#F44336"
typography:
  display:
    fontFamily: "Manrope"
    fontSize: "30"
    fontWeight: 700
    lineHeight: 1.1
  headline:
    fontFamily: "Sora"
    fontSize: "20"
    fontWeight: 600
    lineHeight: 1.2
  title:
    fontFamily: "Sora"
    fontSize: "16"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Manrope"
    fontSize: "13"
    fontWeight: 400
    lineHeight: 1.4
  label:
    fontFamily: "Manrope"
    fontSize: "11"
    fontWeight: 600
    letterSpacing: "normal"
rounded:
  xs: "6"
  sm: "8"
  md: "12"
  lg: "18"
  pill: "100"
spacing:
  xs: "4"
  sm: "8"
  md: "12"
  lg: "16"
  xl: "20"
components:
  button-primary:
    backgroundColor: "{colors.dourado}"
    textColor: "#000000"
    rounded: "{rounded.sm}"
  fab-financas:
    backgroundColor: "{colors.verde-claro}"
    textColor: "#000000"
    rounded: "{rounded.pill}"
  card-dark:
    backgroundColor: "{colors.carbono-superficie}"
    textColor: "{colors.texto}"
    rounded: "{rounded.lg}"
    padding: "16"
  icon-tile:
    backgroundColor: "{colors.icone-fundo}"
    textColor: "{colors.dourado}"
    rounded: "{rounded.md}"
  badge-pill:
    backgroundColor: "{colors.dourado-claro}"
    textColor: "#000000"
    rounded: "{rounded.pill}"
---

# Design System: Finapple

> Atualizado em 2026-10-07 para a identidade "grafite e dourado discreto" (canvas de design
> "Finapple – Nova Home"). Substitui a versão de 2026-09-23 (verde/amarelo neon, Roboto, cartões
> brancos com sombra, barra inferior). Decisões e histórico no vault: `Finapple — Nova Home (design)`.

## Overview

**Creative North Star: "O Cofre Discreto"**

Finapple trata dinheiro a sério sem parecer um banco. A base é um dark mode carbono — um cofre
quieto — onde quase tudo fica em tons de grafite e cinza-azulado e o **dourado** aparece só onde
importa: uma ação, um recorde batido, uma barra subindo. O logo é um abacaxi lapidado em traço
fino, com uma fechadura de cofre no centro: precisão e proteção, sem infantilizar. Os números são
grandes e diretos, e nada compete com a leitura clara de quanto dinheiro entrou, saiu ou falta
pra bater a meta.

Tudo é **plano e tonal**: profundidade vem de um degrau de cor (fundo → superfície) e de uma
borda de 1 px, nunca de sombra. Os antigos cartões brancos com sombra do Painel de Finanças
foram redesenhados no mesmo padrão escuro dos demais.

**Key Characteristics:**
- Dark carbono como base; um único destaque (dourado, em dois tons); cor não é decoração.
- Navegação por **hub**: a Home é um índice de módulos, sem barra inferior.
- Títulos em **Sora**, texto em **Manrope** — fontes empacotadas, o app não usa a internet.
- Cartões generosos (raio 18) com borda fina; ícones sempre dentro de um bloco quadrado arredondado.

## Colors

Paleta pequena e deliberada: um destaque dourado sobre uma base neutra de grafite, mais dois
acentos de papel único (azul-aço e verde-claro) e as cores semânticas do dinheiro. Tokens em
`src/app_fi/ui/cores.py` — nunca hardcodar hex nas telas.

### Primary
- **Dourado** (#C2A15A): a cor da marca e da ação — botões principais (FilledButton, FAB),
  seleção de categoria, barras de progresso, ícones dos módulos, "apple" do nome, selo "Em breve".

### Secondary
- **Dourado claro** (#E3C77E): recompensa e conquista — PRs, Nível/XP, ofensiva, meta atingida.
  É o mesmo dourado, um tom acima, para ainda distinguir "conquistei" de "posso agir".

### Tertiary
- **Azul-aço** (#8FB0BF): leitura neutra — hoje só o terceiro anel do Painel de Finanças.

### Accent (um único uso)
- **Verde claro** (#5AC27D): exclusivo do botão **+** do módulo de finanças (Finanças pessoais,
  Categorias, Recorrentes) — o verde com a mesma saturação e luminosidade do dourado (HSL), para
  parecer irmão dele. Contraste com o ícone preto: 9,4:1.

### Neutral
- **Carbono fundo** (#1A2227): fundo do app. **Carbono superfície** (#222C32): cartões e linhas.
  **Borda** (#2F3B42): contorno de cartões e divisórias. **Bloco de ícone** (#2A353C, borda #36434A).
- **Texto** (#E6EAEC), **título** (#C9D0D3, "Fin" do nome), **suave** (#9AA6AC, legendas),
  **seta** (#7D8A90, chevrons), **prata** (#A9B3B8, detalhes do logo).

### Named Rules
**The One Accent Rule.** O destaque da marca é um só — o dourado. Ação e conquista usam dois tons
dele (dourado e dourado claro), não duas famílias de cor. O verde claro tem um único emprego (o +
das finanças) e o azul-aço uma única leitura (neutra); nenhuma terceira cor de destaque entra
sem papel próprio. *Tensão conhecida:* com um destaque só, ação e conquista ficam mais parecidas
que na paleta antiga; se confundir no uso, separar de novo (ex.: prata para ação).

**The Financial Semantics Are Separate Rule.** Receita usa `Colors.GREEN` (#4CAF50) e despesa
usa `Colors.RED` (#F44336) — cores padrão do Material, fora da marca. Dinheiro entrando/saindo é
semântica universal; não trocar por dourado/verde-claro só por consistência.

## Typography

**Títulos:** Sora (600; 500 no nome da marca) — geométrica, para o nome, títulos de tela e de
linha e valores de destaque. **Texto:** Manrope — corpo, rótulos e legendas.

Ambas são **variáveis** (um arquivo cobre todos os pesos), licença OFL, em `src/assets/fonts`
e registradas por `page.fonts`; Manrope é a fonte padrão do tema. *A conferir no Android:* se os
pesos intermediários da fonte variável são aplicados (no navegador funcionam).

### Hierarchy
- **Display** (Manrope Bold, 30): o número de maior destaque da tela — a contagem de meses de
  ofensiva em Objetivos.
- **Headline** (Sora 600, 20-28): nome "Finapple" no hub (26, peso 500), saldo e valores dos
  cartões do painel (20), valor da carteira cripto (28).
- **Title** (Sora 600, 16-17): títulos de linha do hub e de tela (AppBar), títulos de diálogo.
- **Body** (Manrope, 12-13): conteúdo padrão, subtítulos de linha (12), progresso textual.
- **Label** (Manrope 600/Bold, 10-12, cor suave): legendas, datas, apoio secundário.

### Named Rules
**The Number-First Rule.** Qualquer valor monetário ou de conquista (saldo, XP, streak, %) é
sempre destacado (peso maior) e pelo menos um degrau acima do texto que o rotula.

## Layout

Coluna única, layout de app mobile mesmo em desktop/web (`page.padding = 20`). Espaçamento em
múltiplos de 4 (4, 8, 12, 16, 20); 16 é o padding interno padrão dos cartões, 20 a margem da página.

**Navegação por hub (sem barra inferior):** a Home (`ui/home.py`) mostra logo, nome, saudação e um
cartão com 3 linhas — **Finanças pessoais**, **Investimentos** e **Objetivos** — e "Nível · XP"
no rodapé. O bloco é centralizado na tela (espaçadores proporcionais), e o cartão ocupa 80% da
largura (margens iguais), para as linhas não irem até as bordas. *Investimentos* abre um segundo
índice com **Cripto** (ativa) e **Renda Fixa** e **Ações** como "Em breve". Todo módulo tem **seta
de volta** na AppBar (Cripto volta para Investimentos, Lançar para Finanças); o **menu lateral**
(Categorias, Recorrentes, Configurações) só existe na Home. *Pendência:* o botão voltar do Android
ainda fecha o app.

FAB circular no canto inferior direito para a criação primária de cada tela.

## Elevation & Depth

**Flat/tonal, sem sombras.** A profundidade vem de um degrau de cor (fundo Carbono → superfície
Carbono mais clara) e de uma borda de 1 px (#2F3B42). Não há `BoxShadow` em nenhum componente.

### Named Rules
**The No-Shadow Rule.** Quando algo precisa se destacar, usa cor de superfície ou borda — nunca
`BoxShadow`. (A exceção anterior, os cartões brancos do painel, deixou de existir.)

## Shapes

Raios por peso visual: utilitários (linhas de lista, botão de mês) 6; barras de progresso 8;
**blocos de ícone 12**; **cartões e cartão do hub 18**; badges, pílulas e FAB fecham em 100.

### Named Rules
**The Content-Gets-The-Rounder-Corner Rule.** Quanto mais um elemento é "conteúdo" (cartão de
missão, de ativo, do hub) em vez de "utilidade" (linha de lista, barra), mais generoso o raio.

## Components

### Buttons
- **Primary (`FilledButton`):** dourado de fundo, texto escuro — confirmar/salvar (Registrar,
  Salvar, Confirmar importação).
- **Text (`TextButton`):** texto dourado, fundo transparente — secundárias (Cancelar) ou
  destrutivas com override `Colors.RED` (Excluir/Arquivar).
- **Outlined (`OutlinedButton`):** ações pouco frequentes (backup, "Atualizar preço", "Meta").

### FAB
- **Cor:** dourado em Objetivos e Cripto; **verde claro (#5AC27D)** no módulo de finanças
  (Finanças pessoais, Categorias, Recorrentes). Sempre `bgcolor` explícito (token de `cores.py`),
  senão cai no azul padrão do tema.

### Linha do hub (`ui/home.py`)
- Bloco de ícone 40×40 (raio 12, fundo e borda de ícone, ícone dourado 20), título Sora 16/600,
  subtítulo Manrope 12 suave, chevron à direita; padding 14×11, divisórias de 1 px.
- **Em breve:** linha com opacidade 0,6, sem toque, selo "Em breve" em pílula de contorno dourado.
- Linha de **Investimentos** mostra o resumo real da carteira cripto (valor e lucro %).

### Chips (categorias)
- Ícone + rótulo empilhados; fundo Carbono superfície quando não selecionado; **selecionado em
  dourado**.

### Cartões
- **Padrão (missão, PR, ativo, resumo, cartões do painel):** superfície Carbono, borda 1 px, raio
  18, sem sombra. Cartões do painel de finanças: bloco de ícone, título suave (até 2 linhas), valor
  em Sora, barra de progresso dourada; os dois com altura 168 (iguais).
- **Badge/pílula (PR!/Ativo, selo de lucro %):** fundo na cor do estado, raio 100.
- **Etiqueta de moeda (R$/US$)** nos ativos cripto: pílula de contorno fino cinza.

### Inputs / Fields
- `TextField` padrão do Material (herda o tema); erro em `Colors.RED` abaixo do campo.

### Navigation
- **Top app bar:** seta de voltar + título (Sora 600). A Home só tem o ícone do menu (o nome fica
  sob o logo, no corpo). O símbolo de coroa que ficava ao lado do nome **foi removido**.
- **Drawer:** só na Home.

### Progress Ring com % central (componente assinatura)
`ft.ProgressRing` não tem texto central no Flet: empilha-se um `ft.Text` por cima com `ft.Stack`
— 3 anéis do Painel de Finanças (dourado, dourado claro, azul-aço), cada um com rótulo embaixo.
Qualquer nova leitura circular de progresso deve reusar esse padrão.

## Do's and Don'ts

### Do:
- **Do** usar os tokens de `ui/cores.py` e as fontes por nome (`cores.FONTE_TITULO`).
- **Do** dar destaque à marca com o dourado; usar o dourado claro só para conquista.
- **Do** separar com cor de superfície e borda de 1 px; deixar valores de destaque em peso maior.
- **Do** usar `Colors.GREEN`/`Colors.RED` para receita/despesa e lucro/prejuízo.

### Don't:
- **Don't** adicionar `BoxShadow` — o sistema é plano.
- **Don't** hardcodar hex nas telas nem usar o verde claro fora do + do módulo de finanças.
- **Don't** introduzir uma terceira cor de destaque sem um papel próprio.
- **Don't** voltar a usar Roboto/ícone de coroa ao lado do nome, nem os cartões brancos antigos.
- **Don't** assumir que o tema claro está pronto: as superfícies são escuras fixas (revisão pendente).
