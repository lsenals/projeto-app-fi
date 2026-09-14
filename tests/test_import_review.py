"""Dados fabricados — nunca uma fatura real."""

import pytest

from app_fi.core.c6_import import ImportedRow
from app_fi.data import import_review as review
from app_fi.data import transactions_repo as tx_repo
from app_fi.data.db import get_db


@pytest.fixture()
def conn(tmp_path):
    c = get_db(tmp_path / "t.db")
    yield c
    c.close()


def _expense(**overrides):
    base = dict(
        date="2026-08-10", description="LOJA TESTE", amount_cents=5000,
        kind="expense", suggested_category_name=None, income_source_name=None, note=None,
    )
    base.update(overrides)
    return ImportedRow(**base)


def test_suggest_category_uses_c6_mapping_when_no_memory(conn):
    row = _expense(suggested_category_name="Alimentação")
    cat_id = review.suggest_category_id(conn, row)
    names = {c["id"]: c["name"] for c in conn.execute("SELECT id, name FROM categories")}
    assert names[cat_id] == "Alimentação"


def test_suggest_category_returns_none_when_unmapped(conn):
    row = _expense(suggested_category_name=None)
    assert review.suggest_category_id(conn, row) is None


def test_suggest_category_prefers_payee_memory_over_c6_map(conn):
    cats = {c["name"]: c["id"] for c in conn.execute("SELECT id, name FROM categories")}
    # confirma uma vez com "Lazer" mesmo o C6 sugerindo "Alimentação"
    first = _expense(description="LOJA TESTE", suggested_category_name="Alimentação")
    review.confirm_expense(conn, first, cats["Lazer"])

    second = _expense(description="LOJA TESTE", suggested_category_name="Alimentação")
    assert review.suggest_category_id(conn, second) == cats["Lazer"]


def test_income_rows_never_get_a_category_suggestion(conn):
    row = _expense(kind="income", suggested_category_name="Alimentação")
    assert review.suggest_category_id(conn, row) is None


def test_is_probable_duplicate_false_when_nothing_confirmed_yet(conn):
    row = _expense()
    assert review.is_probable_duplicate(conn, row) is False


def test_is_probable_duplicate_true_after_confirming_matching_row(conn):
    row = _expense()
    review.confirm_expense(conn, row, category_id=None)
    assert review.is_probable_duplicate(conn, row) is True


def test_two_identical_rows_in_same_batch_are_not_duplicates_of_each_other(conn):
    """A checagem só olha o banco, não os irmãos do próprio lote — reflete o
    caso real de duas compras iguais no mesmo dia no mesmo estabelecimento."""
    a, b = _expense(), _expense()
    assert review.is_probable_duplicate(conn, a) is False
    assert review.is_probable_duplicate(conn, b) is False


def test_confirm_expense_creates_transaction_and_teaches_payee(conn):
    cats = {c["name"]: c["id"] for c in conn.execute("SELECT id, name FROM categories")}
    row = _expense(note="Cartão final 0000")
    tx_id = review.confirm_expense(conn, row, cats["Compras"])

    saved = tx_repo.get(conn, tx_id)
    assert saved["amount_cents"] == 5000
    assert saved["category_name"] == "Compras"
    assert saved["note"] == "Cartão final 0000"

    from app_fi.data import payees_repo
    assert payees_repo.find_default_category_id(conn, "LOJA TESTE") == cats["Compras"]


def test_confirm_income_creates_transaction_with_source(conn):
    row = _expense(kind="income", description="Estorno Teste")
    sources = {s["name"]: s["id"] for s in tx_repo.list_income_sources(conn)}
    tx_id = review.confirm_income(conn, row, sources["Reembolso"])

    saved = tx_repo.get(conn, tx_id)
    assert saved["kind"] == "income"
    assert saved["income_source_name"] == "Reembolso"
