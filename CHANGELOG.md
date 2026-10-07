# Changelog

## Não lançado (desenvolvimento pós-v1.0.0, a partir de 2026-10-07)

### Criptoativos (nova aba "Cripto")
- Carteira lançada à mão: compras e vendas, preço médio, lucro/prejuízo realizado e não realizado,
  total investido, evolução do valor da carteira e **metas de trade** (ganho % sobre o preço médio,
  stop opcional) com barra de progresso. Catálogo dos 40 principais ativos + cadastro de outros.
- **Moeda por ativo (R$ ou US$)**, alternância de exibição R$/US$ no resumo e cotação do dólar
  informada à mão (o app não acessa a internet).
- Valores em `Decimal` exato (exceção à regra de centavos inteiros); migrações 006 e 007.

### Ações, Renda Fixa e trades realizados
- **Ações:** mesma carteira de Cripto (preço médio, lucro, metas e stop, moeda por ativo, evolução), sem
  catálogo — tickers como PETR4 cadastrados à mão. Código compartilhado (`CarteiraRepo`, `ui/carteira.py`).
- **Trades realizados** no rodapé de Cripto e de Ações: data e valor de compra e de venda, custos da
  operação, lucro final e %, com resumo (lucro total, custos, taxa de acerto). Migração 008.
- **Renda Fixa:** aplicações com tipo (17 opções: Tesouro Selic/Prefixado/IPCA+/Renda+/Educa+, CDB, LCI, LCA,
  LC, CRI, CRA, debêntures, poupança…), instituição, corretora, rentabilidade pré, pós ou híbrida e taxa,
  vencimento, liquidez, isenção de IR e FGC, aportes e resgates, valor atual informado à mão, **contador de
  dias desde o 1º aporte** e **faixa e estimativa de IR** (tabela regressiva). Migração 009.

### Home
- Painel de Finanças ligado a dados reais (objetivos batidos, gasto/renda, dia do mês, saldo dos
  últimos 7 dias, poupança do mês).

### Segurança (APK)
- Sem permissão de internet; backup automático do Android desligado; escape de HTML no relatório e
  neutralização de fórmulas no CSV.

### Home em hub, marca e navegação
- A Home virou um índice de módulos: **Finanças pessoais**, **Investimentos** (Cripto, Renda Fixa e
  Ações) e **Objetivos**, com o nível/XP no rodapé. O painel e os
  lançamentos de antes agora vivem em "Finanças pessoais".
- **Barra inferior removida**: cada módulo tem seta de volta; o menu lateral (Categorias,
  Recorrentes, Configurações) fica na Home. Lançar abre pelo botão + de Finanças pessoais.
- Nova identidade "grafite e dourado discreto", logo SVG, fontes Sora e Manrope empacotadas
  (`src/assets/fonts`, licença OFL), nome grafado "Finapple" e símbolo ao lado do nome removido.
- Cartões do painel de finanças redesenhados (escuros, na linguagem da Home), com a mesma altura.
- Hub mais compacto: cartão com 80% da largura, centralizado na tela, linhas menores e mais juntas.
- Botão **+** do módulo de finanças (Finanças pessoais, Categorias, Recorrentes) em verde claro
  (`#5AC27D`, mesma saturação e luminosidade do dourado); nos demais módulos segue dourado.
- **Botão voltar do Android** passa a voltar uma tela (para o módulo pai) em vez de fechar o app; só
  no hub ele sai. Mapa de telas em `ui/navegacao.py`.
- Botão **+** em verde claro em todos os módulos de dinheiro (inclui Cripto, Ações e Renda Fixa); só
  Objetivos segue dourado. Subtítulos do hub e de Investimentos voltam a ser descrições, sem números.
- Documentação alinhada: `DESIGN.md`, `PRODUCT.md`, `README.md` e `CLAUDE.md` descrevem a identidade
  e a navegação atuais.
- Barra de XP, títulos dos cards, tabela do Fechamento e lista de lançamentos ajustados para telas
  de celular.

## v1.0.0 — 2026-09-15

Primeira versão fechada do Finapple (antes "App FI").

### Lançamentos e fechamento do mês
- Lançar despesa/receita, editar, excluir com Desfazer (toast).
- Navegação entre meses, fechamento do mês, exportação (HTML, CSV, backup do banco).
- Categorias e origens de receita administráveis, com ordem customizável
  (arrastar-e-soltar) na tela de Lançar.
- Campo Estabelecimento com memória de categoria (aprende qual categoria você
  usa pra cada estabelecimento e sugere da próxima vez).

### Recorrentes
- Modelagem de recorrências (mensal/semanal) com previsão de término para as
  que têm número fixo de parcelas (ex: financiamento). Ainda não materializa
  lançamentos sozinha — isso fica pra depois.

### Importação de fatura
- Importa fatura de cartão C6 Bank em CSV ou XLSX, com revisão manual antes de
  gravar, sugestão automática de categoria e aviso de possível duplicata.
- Leitura de CSV robusta a UTF-8 e Windows-1252 (comum em exportações de banco
  no Brasil).

### UI gamificada
- Tela "Lançar" com seletor visual de categorias (grade de ícones) e feedback
  instantâneo — pensada pra registrar uma despesa em poucos toques.
- Tela "Objetivos": Objetivos Inteligentes (teto por categoria, redução vs. mês
  anterior, renda extra, saldo positivo seguido), com Recordes Pessoais (PRs) e
  ofensiva geral.
- Bottom NavigationBar (Home / Lançar / Objetivos), Drawer pra itens
  secundários (Categorias, Recorrentes, Configurações).

### Identidade visual
- Rebrand para **Finapple**: tema dark com paleta verde esmeralda (primária) e
  dourado neon (secundária), header com ícone de coroa (workspace_premium).
  Tema claro disponível via toggle em Configurações.

### Arquitetura
- Python + Flet, SQLite local (WAL), migrations numeradas, repository pattern
  por entidade, `core/` puro e testável sem banco nem UI. 131 testes (`pytest`).
