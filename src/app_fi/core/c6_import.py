"""Classificação pura de linhas de fatura do C6 Bank (CSV/XLSX).

Recebe linhas já tabulares (uma por transação, chaves = cabeçalho do arquivo
do emissor) e devolve pré-lançamentos prontos para revisão. Não toca em
banco nem em arquivo — isso é trabalho de `data/statement_files.py` (leitura)
e `data/import_review.py` (ligação com o banco).

Cabeçalho esperado (C6 Bank, fatura exportada em CSV ou XLSX):
Data de Compra;Nome no Cartão;Final do Cartão;Categoria;Descrição;Parcela;
Valor (em US$);Cotação (em R$);Valor (em R$)
"""

from __future__ import annotations

from dataclasses import dataclass

# Mapeamento da categoria que o próprio C6 já atribui -> nossas categorias.
# Só os casos inequívocos. O resto fica sem sugestão e vai pro check manual
# de propósito — categoria ambígua chutada errado é pior que vazia.
CATEGORY_MAP: dict[str, str] = {
    "Supermercados / Mercearia / Padarias / Lojas de Conveniência": "Alimentação",
    "Restaurante / Lanchonete / Bar": "Alimentação",
    "TV por assinatura / Serviços de rádio": "Assinaturas",
    "Educacional": "Educação",
    "Assistência médica e odontológica": "Saúde",
    "Vestuário / Roupas": "Compras",
    "Especialidade varejo": "Compras",
    "Departamento / Desconto": "Compras",
    "Recreativo": "Lazer",
    "Casa / Escritório Mobiliário": "Moradia",
}


@dataclass(frozen=True)
class ImportedRow:
    date: str                              # ISO yyyy-mm-dd
    description: str
    amount_cents: int                      # sempre positivo
    kind: str                              # 'expense' | 'income'
    suggested_category_name: str | None = None   # só para despesa
    income_source_name: str | None = None        # 'Reembolso' para receita
    note: str | None = None


def _to_cents(raw: str) -> int:
    s = str(raw).strip().replace(",", "")  # vírgula aqui é separador de milhar
    return round(float(s) * 100)


def _to_iso_date(raw: str) -> str:
    d, m, y = raw.strip().split("/")
    return f"{y}-{m.zfill(2)}-{d.zfill(2)}"


def classify_rows(rows: list[dict]) -> list[ImportedRow]:
    """Filtra e classifica. Linhas de pagamento da fatura ("Inclusão de
    Pagamento" etc.) são descartadas aqui — não são gasto nem receita, são
    você quitando o cartão. Valor negativo que não é pagamento vira estorno
    (Receita, origem Reembolso). O resto vira despesa.
    """
    result: list[ImportedRow] = []
    for row in rows:
        data_compra = (row.get("Data de Compra") or "").strip()
        valor_bruto = (row.get("Valor (em R$)") or "").strip()
        if not data_compra or not valor_bruto:
            continue  # linha em branco no fim do arquivo, por exemplo

        descricao = " ".join((row.get("Descrição") or "").split())  # colapsa espaços
        if "pagamento" in descricao.lower():
            continue

        cents = _to_cents(valor_bruto)
        if cents == 0:
            continue

        categoria_c6 = (row.get("Categoria") or "").strip()
        parcela = (row.get("Parcela") or "").strip()
        final_cartao = (row.get("Final do Cartão") or "").strip()

        note_parts = []
        if final_cartao:
            note_parts.append(f"Cartão final {final_cartao}")
        if parcela and parcela.lower() != "única":
            note_parts.append(f"Parcela {parcela}")
        note = " · ".join(note_parts) or None

        date_iso = _to_iso_date(data_compra)

        if cents < 0:
            result.append(ImportedRow(
                date=date_iso, description=descricao, amount_cents=abs(cents),
                kind="income", income_source_name="Reembolso", note=note,
            ))
        else:
            result.append(ImportedRow(
                date=date_iso, description=descricao, amount_cents=cents,
                kind="expense", suggested_category_name=CATEGORY_MAP.get(categoria_c6),
                note=note,
            ))
    return result
