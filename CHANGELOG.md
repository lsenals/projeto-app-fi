# Changelog

## v1.0.0 — 2026-09-15

Primeira versão fechada do FinApple (antes "App FI").

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
- Rebrand para **FinApple**: tema dark com paleta verde esmeralda (primária) e
  dourado neon (secundária), header com ícone de coroa (workspace_premium).
  Tema claro disponível via toggle em Configurações.

### Arquitetura
- Python + Flet, SQLite local (WAL), migrations numeradas, repository pattern
  por entidade, `core/` puro e testável sem banco nem UI. 131 testes (`pytest`).
