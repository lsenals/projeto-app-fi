import pytest

from app_fi.core.summary import (
    MonthTotals,
    category_breakdown,
    income_by_source,
    month_over_month,
    month_totals,
)


def _row(kind, amount_cents, status="confirmed", category_name=None, income_source_name=None):
    return {
        "kind": kind, "amount_cents": amount_cents, "status": status,
        "category_name": category_name, "income_source_name": income_source_name,
    }


def test_empty_month_is_all_zeros():
    t = month_totals([])
    assert t == MonthTotals(0, 0)
    assert t.balance_cents == 0


def test_sums_expense_and_income_separately():
    rows = [
        _row("income", 840000),
        _row("expense", 3490),
        _row("expense", 12000),
    ]
    t = month_totals(rows)
    assert t.expense_cents == 15490
    assert t.income_cents == 840000
    assert t.balance_cents == 824510


def test_pending_rows_are_excluded():
    rows = [
        _row("expense", 10000),
        _row("expense", 5000, status="pending"),   # recorrência a confirmar
        _row("income", 20000, status="pending"),
    ]
    t = month_totals(rows)
    assert t.expense_cents == 10000
    assert t.income_cents == 0


def test_category_breakdown_sums_and_sorts_desc():
    rows = [
        _row("expense", 1000, category_name="Lazer"),
        _row("expense", 5000, category_name="Moradia"),
        _row("expense", 2000, category_name="Moradia"),
        _row("expense", 500, category_name=None),  # sem categoria
        _row("income", 999999, income_source_name="Salário"),  # ignorado aqui
    ]
    assert category_breakdown(rows) == [
        ("Moradia", 7000), ("Lazer", 1000), ("Sem categoria", 500),
    ]


def test_income_by_source_sums_and_sorts_desc():
    rows = [
        _row("income", 500000, income_source_name="Salário"),
        _row("income", 30000, income_source_name="Renda extra"),
        _row("income", 20000, income_source_name="Renda extra"),
        _row("expense", 999999, category_name="Moradia"),  # ignorado aqui
    ]
    assert income_by_source(rows) == [("Salário", 500000), ("Renda extra", 50000)]


def test_month_over_month_includes_both_sides_and_sorts_by_current():
    atual = [
        _row("expense", 3000, category_name="Alimentação"),
        _row("expense", 1000, category_name="Lazer"),
    ]
    anterior = [
        _row("expense", 2000, category_name="Alimentação"),
        _row("expense", 4000, category_name="Transporte"),  # só existia antes
    ]
    linhas = month_over_month(atual, anterior)
    by_cat = {r.category: r for r in linhas}

    assert by_cat["Alimentação"].current_cents == 3000
    assert by_cat["Alimentação"].previous_cents == 2000
    assert by_cat["Alimentação"].delta_pct == pytest.approx(50.0)

    assert by_cat["Lazer"].previous_cents == 0
    assert by_cat["Lazer"].delta_pct is None  # divide por zero -> sem variação

    assert by_cat["Transporte"].current_cents == 0
    assert by_cat["Transporte"].previous_cents == 4000

    # maior gasto do mês atual primeiro
    assert [r.category for r in linhas][0] == "Alimentação"
