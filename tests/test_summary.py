from app_fi.core.summary import MonthTotals, month_totals


def _row(kind, amount_cents, status="confirmed"):
    return {"kind": kind, "amount_cents": amount_cents, "status": status}


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
