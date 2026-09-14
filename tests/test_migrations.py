import sqlite3

import pytest

from app_fi.data import db


def test_migrations_create_all_tables(tmp_path):
    conn = db.get_db(tmp_path / "t.db")
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )}
    assert {
        "accounts", "categories", "income_sources", "payees",
        "transactions", "recurring", "schema_migrations",
    } <= tables


def test_migrations_are_idempotent(tmp_path):
    path = tmp_path / "t.db"
    db.get_db(path).close()
    conn = db.get_db(path)  # segunda passada: nada a aplicar
    versions = [r["version"] for r in conn.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    )]
    assert versions == ["001_init", "002_seed", "003_recurring_forecast"]


def test_seed_categories_exclude_income(tmp_path):
    conn = db.get_db(tmp_path / "t.db")
    categories = [r["name"] for r in conn.execute("SELECT name FROM categories")]
    assert "Alimentação" in categories
    assert "Salário" not in categories  # receita não é categoria

    sources = [r["name"] for r in conn.execute("SELECT name FROM income_sources")]
    assert "Salário" in sources


def test_seed_creates_one_cash_account(tmp_path):
    conn = db.get_db(tmp_path / "t.db")
    rows = list(conn.execute("SELECT name, type FROM accounts"))
    assert len(rows) == 1
    assert rows[0]["type"] == "cash"


def test_expense_may_omit_category(tmp_path):
    conn = db.get_db(tmp_path / "t.db")
    conn.execute(
        "INSERT INTO transactions (date, amount_cents, account_id, kind) "
        "VALUES ('2026-09-01', 3490, 1, 'expense')"
    )
    conn.commit()


def test_expense_cannot_carry_income_source(tmp_path):
    conn = db.get_db(tmp_path / "t.db")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO transactions (date, amount_cents, account_id, kind, income_source_id) "
            "VALUES ('2026-09-01', 3490, 1, 'expense', 1)"
        )


def test_income_cannot_carry_category(tmp_path):
    conn = db.get_db(tmp_path / "t.db")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO transactions (date, amount_cents, account_id, kind, category_id) "
            "VALUES ('2026-09-01', 840000, 1, 'income', 1)"
        )


def test_negative_amount_rejected(tmp_path):
    conn = db.get_db(tmp_path / "t.db")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO transactions (date, amount_cents, account_id, kind) "
            "VALUES ('2026-09-01', -100, 1, 'expense')"
        )
