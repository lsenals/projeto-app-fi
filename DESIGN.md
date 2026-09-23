---
name: FinApple
description: App financeiro pessoal e gamificado — cofre descontraído em Material dark, abacaxi como mascote de conquista.
colors:
  verde-cofre: "#00E676"
  dourado-conquista: "#FFD600"
  azul-confianca: "#40C4FF"
  carbono-fundo: "#263238"
  carbono-superficie: "#37474F"
  branco-cartao: "#FFFFFF"
  texto-sobre-dark: "#FFFFFF"
  texto-secundario: "#9E9E9E"
  texto-sobre-cartao: "#616161"
  receita: "#4CAF50"
  despesa-erro: "#F44336"
typography:
  display:
    fontFamily: "Roboto"
    fontSize: "30"
    fontWeight: 700
    lineHeight: 1.1
  headline:
    fontFamily: "Roboto"
    fontSize: "20"
    fontWeight: 700
    lineHeight: 1.2
  title:
    fontFamily: "Roboto"
    fontSize: "18"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "Roboto"
    fontSize: "13"
    fontWeight: 400
    lineHeight: 1.4
  label:
    fontFamily: "Roboto"
    fontSize: "11"
    fontWeight: 600
    letterSpacing: "normal"
rounded:
  xs: "6"
  sm: "8"
  md: "15"
  lg: "20"
  pill: "100"
spacing:
  xs: "4"
  sm: "8"
  md: "12"
  lg: "16"
  xl: "20"
components:
  button-primary:
    backgroundColor: "{colors.verde-cofre}"
    textColor: "#000000"
    rounded: "{rounded.sm}"
  card-dark:
    backgroundColor: "{colors.carbono-superficie}"
    textColor: "{colors.texto-sobre-dark}"
    rounded: "{rounded.lg}"
    padding: "16"
  card-floating:
    backgroundColor: "{colors.branco-cartao}"
    textColor: "#000000"
    rounded: "{rounded.md}"
    padding: "16"
  badge-pill:
    backgroundColor: "{colors.dourado-conquista}"
    textColor: "#000000"
    rounded: "{rounded.pill}"
---

# Design System: FinApple

## Overview

**Creative North Star: "O Cofre Descontraído"**

FinApple trata dinheiro a sério sem parecer um banco. A base é um dark mode carbono — quase
um cofre discreto — onde a maior parte da interface fica quieta, em tons de cinza-azulado, e
a cor só aparece nos momentos que importam: um botão de ação, um PR batido, uma barra de
progresso subindo. O abacaxi mascote e a gamificação (Nível, ofensiva, PRs) trazem calor e
personalidade sem infantilizar — a tipografia é sólida, os números são grandes e diretos, e
nada compete com a leitura clara de quanto dinheiro entrou, saiu ou falta pra bater a meta.

Os dois cards brancos do Painel de Finanças são a única exceção deliberada a esse fundo
escuro: eles "flutuam" com sombra sobre o carbono, um contraste de marca proposital, não uma
inconsistência. Fora deles, profundidade vem de tom (superfície um degrau mais clara que o
fundo), nunca de sombra.

**Key Characteristics:**
- Dark carbono como base; cor é reservada para ação e conquista, não decoração.
- Tipografia direta e confiante — números financeiros sempre em destaque (bold, tamanho maior).
- Um único par de cards brancos "flutuando" é a exceção de contraste da marca, não o padrão.
- Cantos generosos em cards de conteúdo (20), pílulas fechadas em badges/emblemas (100).

## Colors

Paleta pequena e deliberada: três acentos vibrantes sobre uma base neutra de dois tons de
carbono. Nenhuma cor de acento aparece em mais de um papel — cada uma tem um único job.

### Primary
- **Verde Cofre** (#00E676): ação seguro e confiante — botões principais (FilledButton,
  FAB de criação), seleção de categoria, primeiro anel do Painel de Finanças, wordmark "Fin".

### Secondary
- **Dourado Conquista** (#FFD600): recompensa e conquista — ofensiva (chama + contador), PRs
  ("PR!" no card de missão), badge de recorde recente, Nível/XP, wordmark "Apple", ícone de
  coroa no cabeçalho da marca.

### Tertiary
- **Azul Confiança** (#40C4FF): dado neutro/informativo — hoje só o terceiro anel do Painel
  de Finanças; reservada para leituras que não são nem ação nem conquista.

### Neutral
- **Carbono Fundo** (#263238): fundo geral do app (dark theme, `scaffold_bgcolor`).
- **Carbono Superfície** (#37474F): um degrau acima do fundo — cards escuros, linhas de
  lista, campo de valor, chips não selecionados. É a única forma de "elevação" nesse fundo.
- **Branco Cartão** (#FFFFFF): fundo dos dois cards do Painel de Finanças — a exceção de
  contraste da marca (ver Elevação).
- **Texto sobre dark** (#FFFFFF) / **Texto secundário** (#9E9E9E, `Colors.GREY`): texto
  primário e legendas sobre o fundo escuro.
- **Texto sobre cartão** (#616161, `Colors.GREY_700`): texto secundário dentro dos cards
  brancos, onde o texto primário vira preto.

### Named Rules
**The One Job Rule.** Verde é sempre ação/progresso; dourado é sempre recompensa/conquista já
alcançada; azul é sempre leitura neutra. Nenhuma dessas três cores de acento cobre mais de um
papel — se uma tela precisa de uma quarta cor semântica, ela não deve pegar emprestado uma
das três, vem de fora dessa paleta (como o Verde/Vermelho financeiro abaixo).

**The Financial Semantics Are Separate Rule.** Receita usa `Colors.GREEN` (#4CAF50) e despesa
usa `Colors.RED` (#F44336) — cores padrão do Material, deliberadamente diferentes do Verde
Cofre da marca. Dinheiro entrando/saindo é semântica financeira universal (verde/vermelho),
não branding; não trocar essas por Verde Cofre/Dourado só por consistência de marca.

## Typography

**Display/Body/Label Font:** Roboto (face padrão do Material/Android; a marca não introduz
uma tipografia própria — a personalidade vem da paleta e do mascote, não da fonte).

**Character:** Direta e confiante. Números financeiros e de conquista (saldo, streak, XP)
sempre em peso Bold, maiores que o texto ao redor — a hierarquia é "o número fala primeiro".

### Hierarchy
- **Display** (Bold, 30): o número de maior destaque da tela — hoje só a contagem de meses de
  ofensiva no cabeçalho de Objetivos.
- **Headline** (Bold, 20-22): saldo do mês, valores em destaque nos cards brancos, wordmark
  "FinApple" no cabeçalho de marca.
- **Title** (Bold, 18): saudação da Home ("Bem-vindo!"), títulos de diálogo ("Novo objetivo").
- **Body** (Regular/W_600, 12-13): texto de conteúdo padrão, rótulos de card, progresso textual.
- **Label** (W_600/Bold, 10-12, cor secundária): legendas, datas, textos de apoio — sempre em
  `Colors.GREY` sobre fundo escuro.

### Named Rules
**The Number-First Rule.** Qualquer valor monetário ou de conquista (saldo, XP, streak, %) é
sempre Bold e pelo menos um degrau de tamanho acima do texto que o rotula — o rótulo nunca
compete visualmente com o número.

## Layout

Coluna única, sem grid multi-coluna — layout de app mobile mesmo quando rodando em desktop/web
pra desenvolvimento (`page.padding = 20`). Espaçamento segue um ritmo apertado de múltiplos de
4 (4, 8, 12, 16, 20); 8 é o passo mais comum entre elementos relacionados (ícone+texto,
itens de uma Row), 16 é o padding interno padrão de cards, 20 é a margem externa da página.

Navegação principal: `NavigationBar` fixa na base (3 destinos — Home, Lançar, Objetivos).
Telas secundárias (Categorias, Recorrentes, Configurações) são acessadas por um drawer lateral
e mantêm a mesma bottom bar visível. FAB circular no canto inferior direito para a ação de
criação primária de cada tela (novo lançamento, novo objetivo, nova categoria/recorrência).

## Elevation & Depth

Sistema é **flat/tonal por padrão** — a profundidade normal vem de um único degrau de cor
(fundo Carbono → superfície Carbono um tom mais clara), nunca de sombra. Sombra existe em
exatamente um lugar: os dois cards brancos do Painel de Finanças, que "flutuam" de propósito
sobre o fundo escuro como contraste de marca.

### Shadow Vocabulary
- **Floating card** (`blur_radius: 16, spread_radius: 1, color: rgba(0,0,0,0.25), offset: 0 4`):
  uso exclusivo dos cards brancos do Painel de Finanças. Não usar em nenhum outro componente.

### Named Rules
**The Shadow-Is-An-Exception Rule.** Sombra não é um recurso de hierarquia geral do sistema —
é a assinatura visual de um único par de componentes (os cards brancos do Painel de Finanças).
Qualquer outro componente que "precisar se destacar" resolve isso com cor de superfície
(Carbono Superfície) ou borda, nunca adicionando `BoxShadow`.

## Shapes

Escala de raio vai de apertada a generosa conforme o peso visual do componente: containers
utilitários (linhas de lista, botão de mês) usam 6; barras de progresso e o painel externo do
Painel de Finanças usam 8; os cards brancos usam 15; cards de conteúdo escuro (missão, PR)
usam 16-20, os mais generosos do sistema; badges, avatares de ícone e pílulas de status
(PR!/Ativo, ícone circular do card) fecham em 100 (círculo/pílula completa).

### Named Rules
**The Content-Gets-The-Rounder-Corner Rule.** Quanto mais um elemento é "conteúdo" (um card
de missão, um card de recorde) em vez de "utilidade" (uma linha de lista, uma barra), mais
generoso o raio — a hierarquia visual de raio acompanha a hierarquia de importância.

## Components

### Buttons
- **Shape:** cantos levemente arredondados (raio padrão do Material `FilledButton`/`TextButton`
  do Flet, sem customização extra).
- **Primary (`FilledButton`):** Verde Cofre de fundo, texto escuro — ações que confirmam/salvam
  (Registrar, Salvar, Confirmar importação).
- **Text (`TextButton`):** texto Verde Cofre sobre fundo transparente — ações secundárias
  (Cancelar) ou destrutivas com override de cor (Excluir/Arquivar/Desativar em `Colors.RED`).
- **Outlined (`OutlinedButton`):** usado só uma vez hoje (backup manual) — ação pouco frequente
  que não deve competir visualmente com o botão primário da tela.

### FAB
- **Style:** circular, canto inferior direito, ícone `ADD` branco.
- **Cor:** deve ser sempre Verde Cofre explícito (`bgcolor=_COR_PRIMARIA`).

### Chips (categorias)
- **Style:** ícone + rótulo empilhados verticalmente, cantos arredondados, fundo Carbono
  Superfície quando não selecionado.
- **State:** selecionado assume Verde Cofre de fundo — mesmo verde de ação/confirmação.

### Cards / Containers
- **Dark (missão, PR, ofensiva, linhas de lista):** fundo Carbono Superfície, raio 6-20
  conforme o peso do conteúdo, sem sombra — ver Elevação.
- **Floating (Painel de Finanças):** fundo branco, raio 15, sombra (ver Elevação), texto preto/
  cinza — única dupla de componentes com esse tratamento.
- **Badge/pill (PR!/Ativo, ícone circular):** fundo sólido na cor semântica do estado (dourado
  = batido, verde = ativo), raio 100, padding apertado.

### Inputs / Fields
- **Style:** `TextField` padrão do Material (outline sutil, label flutuante), sem customização
  visual própria — herda o tema.
- **Error:** texto de erro em `Colors.RED`, abaixo do campo, oculto por padrão (`visible=False`).

### Navigation
- **Bottom (`NavigationBar`):** 3 destinos fixos (Home/Lançar/Objetivos), ícone + rótulo,
  destino ativo destacado pelo tema.
- **Top app bar:** simples (seta de voltar + título) em telas secundárias; só a Home recebe o
  cabeçalho de marca completo (`cabecalho_finapple`).
- **Drawer:** acesso a telas de configuração/manutenção (Categorias, Recorrentes,
  Configurações) — não compete com a bottom bar, que continua visível.

### Progress Ring com % central (signature component)
Componente assinatura do app: `ft.ProgressRing` não tem texto central nativo no Flet, então
o sistema empilha um `ft.Text` centralizado por cima via `ft.Stack` — usado nos 3 anéis do
Painel de Finanças. Qualquer nova leitura circular de progresso (%) deve reusar esse padrão,
não inventar uma variação.

## Do's and Don'ts

### Do:
- **Do** usar Verde Cofre só pra ação/confirmação, Dourado Conquista só pra recompensa já
  alcançada — a regra "um job por cor" (ver **The One Job Rule**).
- **Do** manter sombra restrita aos cards brancos do Painel de Finanças; todo o resto usa
  Carbono Superfície pra se destacar do fundo.
- **Do** deixar números financeiros/de conquista em Bold, um degrau de tamanho acima do rótulo.
- **Do** usar `Colors.GREEN`/`Colors.RED` (não a paleta de marca) para semântica financeira
  de receita/despesa.

### Don't:
- **Don't** deixar o FAB sem `bgcolor` explícito — hoje isso acontece em Categorias e
  Recorrentes, que caem no azul-claro padrão do tema em vez do Verde Cofre da marca. É uma
  inconsistência confirmada no código atual, não um padrão a seguir; corrigir ao tocar nessas
  telas.
- **Don't** adicionar `BoxShadow` fora dos dois cards brancos do Painel de Finanças.
- **Don't** introduzir uma quarta cor de acento sem um papel próprio — se parecer que falta
  cor numa tela, a resposta quase sempre é mais espaço/tom, não mais cor.
- **Don't** trocar Roboto por uma fonte de marca própria sem decisão explícita — a
  personalidade do FinApple vem da paleta e do mascote, não da tipografia.
