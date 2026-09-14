"""Todos os valores aqui são fabricados — nenhum dado real de fatura."""

from app_fi.core.c6_import import classify_rows


def _row(
    data="10/08/2026", nome="FULANO DE TAL", final="0000",
    categoria="Restaurante / Lanchonete / Bar", descricao="RESTAURANTE TESTE",
    parcela="Única", valor="50.00",
):
    return {
        "Data de Compra": data, "Nome no Cartão": nome, "Final do Cartão": final,
        "Categoria": categoria, "Descrição": descricao, "Parcela": parcela,
        "Valor (em US$)": "0", "Cotação (em R$)": "0", "Valor (em R$)": valor,
    }


def test_basic_expense_row():
    rows = classify_rows([_row()])
    assert len(rows) == 1
    r = rows[0]
    assert r.date == "2026-08-10"
    assert r.description == "RESTAURANTE TESTE"
    assert r.amount_cents == 5000
    assert r.kind == "expense"
    assert r.suggested_category_name == "Alimentação"
    assert r.note == "Cartão final 0000"


def test_unmapped_category_has_no_suggestion():
    rows = classify_rows([_row(categoria="Associação")])
    assert rows[0].suggested_category_name is None


def test_negative_value_becomes_income_reembolso():
    rows = classify_rows([_row(descricao="Estorno Tarifa", valor="-98.00")])
    assert len(rows) == 1
    r = rows[0]
    assert r.kind == "income"
    assert r.income_source_name == "Reembolso"
    assert r.amount_cents == 9800  # sempre positivo


def test_payment_rows_are_skipped_entirely():
    rows = classify_rows([_row(descricao="Inclusao de Pagamento", valor="-7210.23", categoria="-")])
    assert rows == []


def test_payment_marker_is_case_insensitive():
    rows = classify_rows([_row(descricao="pagamento recebido", valor="-100.00")])
    assert rows == []


def test_zero_value_row_is_skipped():
    rows = classify_rows([_row(valor="0")])
    assert rows == []


def test_blank_trailing_row_is_skipped():
    rows = classify_rows([{"Data de Compra": "", "Valor (em R$)": ""}])
    assert rows == []


def test_installment_note():
    rows = classify_rows([_row(parcela="4/9", final="1234")])
    assert rows[0].note == "Cartão final 1234 · Parcela 4/9"


def test_unica_installment_not_mentioned_in_note():
    rows = classify_rows([_row(parcela="Única", final="1234")])
    assert rows[0].note == "Cartão final 1234"


def test_description_whitespace_is_collapsed():
    rows = classify_rows([_row(descricao="EC          *TESTE   LOJA")])
    assert rows[0].description == "EC *TESTE LOJA"


def test_thousands_separator_in_amount():
    rows = classify_rows([_row(valor="1,234.56")])
    assert rows[0].amount_cents == 123456


def test_duplicate_looking_lines_both_survive():
    """Duas compras reais, mesmo dia, mesmo estabelecimento, mesmo valor —
    não é duplicata de arquivo, são duas transações de verdade. A checagem de
    duplicata (contra o banco) é responsabilidade de outra camada, não desta."""
    rows = classify_rows([_row(), _row()])
    assert len(rows) == 2
