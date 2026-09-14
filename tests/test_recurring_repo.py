import pytest

from app_fi.data import recurring_repo as repo
from app_fi.data.db import get_db


@pytest.fixture()
def conn(tmp_path):
    c = get_db(tmp_path / "t.db")
    yield c
    c.close()


def _cat_id(conn, name):
    row = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
    return row["id"]


def test_add_indefinite_recurring(conn):
    new_id = repo.add(
        conn, label="Netflix", kind="expense", expected_amount_cents=4490,
        interval_unit="month", next_date="2026-10-16", category_id=_cat_id(conn, "Assinaturas"),
    )
    saved = repo.get(conn, new_id)
    assert saved["label"] == "Netflix"
    assert saved["total_installments"] is None
    assert saved["current_installment"] == 1
    assert saved["category_name"] == "Assinaturas"


def test_add_with_installments(conn):
    new_id = repo.add(
        conn, label="Seguro do carro", kind="expense", expected_amount_cents=25000,
        interval_unit="month", next_date="2026-10-05", category_id=_cat_id(conn, "Transporte"),
        total_installments=12, current_installment=5,
    )
    saved = repo.get(conn, new_id)
    assert saved["total_installments"] == 12
    assert saved["current_installment"] == 5


def test_add_rejects_non_positive_amount(conn):
    with pytest.raises(ValueError):
        repo.add(conn, label="X", kind="expense", expected_amount_cents=0,
                 interval_unit="month", next_date="2026-10-01")


def test_add_rejects_non_positive_total_installments(conn):
    with pytest.raises(ValueError):
        repo.add(conn, label="X", kind="expense", expected_amount_cents=100,
                 interval_unit="month", next_date="2026-10-01", total_installments=0)


def test_update_changes_fields(conn):
    new_id = repo.add(conn, label="Academia", kind="expense", expected_amount_cents=10000,
                       interval_unit="month", next_date="2026-10-01")
    repo.update(conn, new_id, label="Academia Plus", kind="expense",
                expected_amount_cents=12000, interval_unit="month", next_date="2026-10-05",
                total_installments=6, current_installment=2)
    saved = repo.get(conn, new_id)
    assert saved["label"] == "Academia Plus"
    assert saved["expected_amount_cents"] == 12000
    assert saved["total_installments"] == 6


def test_list_active_excludes_deactivated(conn):
    a = repo.add(conn, label="A", kind="expense", expected_amount_cents=100,
                 interval_unit="month", next_date="2026-10-01")
    b = repo.add(conn, label="B", kind="expense", expected_amount_cents=200,
                 interval_unit="month", next_date="2026-10-02")
    repo.deactivate(conn, a)
    ativos = [r["label"] for r in repo.list_active(conn)]
    assert ativos == ["B"]


def test_income_recurring_uses_income_source(conn):
    src = conn.execute("SELECT id FROM income_sources WHERE name = 'Salário'").fetchone()["id"]
    new_id = repo.add(conn, label="Salário mensal", kind="income", expected_amount_cents=800000,
                       interval_unit="month", next_date="2026-10-05", income_source_id=src)
    saved = repo.get(conn, new_id)
    assert saved["income_source_name"] == "Salário"
