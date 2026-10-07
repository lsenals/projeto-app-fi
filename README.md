# Finapple

App financeiro pessoal e gamificado, em Python + Flet. Repositório: `projeto-app-fi`.
100% local: sem backend e sem acesso à internet (o APK nem pede a permissão).

## Módulos
- **Finanças pessoais** — lançamentos, fechamento do mês, importação de fatura C6, recorrentes,
  categorias, relatórios (HTML/CSV) e backup.
- **Investimentos** — **Cripto** e **Ações** (carteira lançada à mão, em R$ ou US$, preço médio, metas de
  trade e diário de trades realizados) e **Renda Fixa** (Tesouro, CDB, LCI/LCA…: rentabilidade pré ou pós,
  vencimento, dias desde o aporte e faixa de IR).
- **Objetivos** — metas, recordes pessoais (PRs), ofensiva e nível.

## Como rodar
```bash
pip install -e ".[dev]"
python src/app_fi/main.py     # ou Finapple.bat no Windows
pytest
```
Detalhes de arquitetura, convenções e do build Android em `CLAUDE.md`; design em `DESIGN.md`;
histórico em `CHANGELOG.md`.
