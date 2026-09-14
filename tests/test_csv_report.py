from app_fi.report.csv_report import render_csv


def _row(kind, amount_cents, status="confirmed", category_name=None, income_source_name=None, date="2026-09-03"):
    return {
        "date": date, "kind": kind, "amount_cents": amount_cents, "status": status,
        "category_name": category_name, "income_source_name": income_source_name,
    }


def test_csv_header():
    csv_text = render_csv([])
    assert csv_text.strip() == "Data;Tipo;Categoria/Origem;Valor (R$);Status"


def test_csv_row_for_expense_with_category():
    csv_text = render_csv([_row("expense", 3490, category_name="Alimentação")])
    lines = csv_text.strip().splitlines()
    assert lines[1] == "2026-09-03;Despesa;Alimentação;R$ 34,90;Confirmado"


def test_csv_row_for_expense_without_category():
    csv_text = render_csv([_row("expense", 13200)])
    lines = csv_text.strip().splitlines()
    assert "Sem categoria" in lines[1]


def test_csv_row_for_income_with_source():
    csv_text = render_csv([_row("income", 840000, income_source_name="Salário")])
    lines = csv_text.strip().splitlines()
    assert lines[1] == "2026-09-03;Receita;Salário;R$ 8.400,00;Confirmado"


def test_csv_marks_pending_status():
    csv_text = render_csv([_row("expense", 1000, status="pending", category_name="Assinaturas")])
    assert "A confirmar" in csv_text


def test_csv_row_count_matches_input():
    rows = [_row("expense", 100 * i, category_name="Outros") for i in range(1, 6)]
    csv_text = render_csv(rows)
    assert len(csv_text.strip().splitlines()) == 1 + 5  # header + 5 linhas
