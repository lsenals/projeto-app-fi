import pytest

from app_fi.core.summary import month_totals
from app_fi.data import transactions_repo as repo
from app_fi.data.db import get_db


@pytest.fixture()
def conn(tmp_path):
    c = get_db(tmp_path / "t.db")
    yield c
    c.close()


def test_add_expense_returns_id_and_appears_in_month(conn):
    new_id = repo.add_expense(conn, date="2026-09-03", amount_cents=3490)
    assert isinstance(new_id, int)

    rows = repo.list_month(conn, 2026, 9)
    assert len(rows) == 1
    assert rows[0]["id"] == new_id
    assert rows[0]["amount_cents"] == 3490
    assert rows[0]["kind"] == "expense"
    assert rows[0]["category_name"] is None  # sem categoria


def test_add_expense_with_category_joins_name(conn):
    cats = {c["name"]: c["id"] for c in repo.list_categories(conn)}
    repo.add_expense(conn, date="2026-09-03", amount_cents=8000, category_id=cats["Alimentação"])
    row = repo.list_month(conn, 2026, 9)[0]
    assert row["category_name"] == "Alimentação"


def test_list_month_filters_by_month(conn):
    repo.add_expense(conn, date="2026-09-30", amount_cents=100)
    repo.add_expense(conn, date="2026-10-01", amount_cents=200)
    assert len(repo.list_month(conn, 2026, 9)) == 1
    assert len(repo.list_month(conn, 2026, 10)) == 1


def test_add_expense_rejects_non_positive(conn):
    with pytest.raises(ValueError):
        repo.add_expense(conn, date="2026-09-03", amount_cents=0)


def test_repo_and_core_compose(conn):
    repo.add_expense(conn, date="2026-09-01", amount_cents=5000)
    repo.add_expense(conn, date="2026-09-15", amount_cents=2500)
    totals = month_totals(repo.list_month(conn, 2026, 9))
    assert totals.expense_cents == 7500
    assert totals.balance_cents == -7500


def test_add_income_joins_source_name(conn):
    sources = {s["name"]: s["id"] for s in repo.list_income_sources(conn)}
    repo.add_income(conn, date="2026-09-05", amount_cents=840000,
                    income_source_id=sources["Salário"])
    row = repo.list_month(conn, 2026, 9)[0]
    assert row["kind"] == "income"
    assert row["income_source_name"] == "Salário"
    assert row["category_name"] is None


def test_add_income_requires_source(conn):
    with pytest.raises(ValueError):
        repo.add_income(conn, date="2026-09-05", amount_cents=1000, income_source_id=None)


def test_income_and_expense_net_in_balance(conn):
    src = repo.list_income_sources(conn)[0]["id"]
    repo.add_income(conn, date="2026-09-01", amount_cents=500000, income_source_id=src)
    repo.add_expense(conn, date="2026-09-02", amount_cents=120000)
    totals = month_totals(repo.list_month(conn, 2026, 9))
    assert totals.income_cents == 500000
    assert totals.expense_cents == 120000
    assert totals.balance_cents == 380000


def test_update_expense_changes_fields_keeps_id(conn):
    cats = {c["name"]: c["id"] for c in repo.list_categories(conn)}
    tx_id = repo.add_expense(conn, date="2026-09-01", amount_cents=1000)
    repo.update_expense(
        conn, tx_id, date="2026-09-02", amount_cents=2000, category_id=cats["Lazer"],
    )
    row = repo.get(conn, tx_id)
    assert row["id"] == tx_id
    assert row["date"] == "2026-09-02"
    assert row["amount_cents"] == 2000
    assert row["category_name"] == "Lazer"


def test_update_income_requires_source(conn):
    src = repo.list_income_sources(conn)[0]["id"]
    tx_id = repo.add_income(conn, date="2026-09-01", amount_cents=1000, income_source_id=src)
    with pytest.raises(ValueError):
        repo.update_income(conn, tx_id, date="2026-09-01", amount_cents=1000, income_source_id=None)


def test_delete_removes_transaction(conn):
    tx_id = repo.add_expense(conn, date="2026-09-01", amount_cents=1000)
    repo.delete(conn, tx_id)
    assert repo.get(conn, tx_id) is None


def test_snapshot_and_restore_undoes_a_delete(conn):
    cats = {c["name"]: c["id"] for c in repo.list_categories(conn)}
    tx_id = repo.add_expense(
        conn, date="2026-09-01", amount_cents=4990, category_id=cats["Alimentação"], note="padaria",
    )
    before = repo.snapshot(repo.get(conn, tx_id))
    repo.delete(conn, tx_id)
    assert repo.get(conn, tx_id) is None

    repo.restore(conn, before)
    restored = repo.get(conn, tx_id)
    assert restored["id"] == tx_id
    assert restored["amount_cents"] == 4990
    assert restored["category_name"] == "Alimentação"
    assert restored["note"] == "padaria"


def test_snapshot_and_restore_undoes_an_edit(conn):
    tx_id = repo.add_expense(conn, date="2026-09-01", amount_cents=1000)
    before = repo.snapshot(repo.get(conn, tx_id))
    repo.update_expense(conn, tx_id, date="2026-09-01", amount_cents=9999)
    assert repo.get(conn, tx_id)["amount_cents"] == 9999

    repo.restore(conn, before)
    assert repo.get(conn, tx_id)["amount_cents"] == 1000
