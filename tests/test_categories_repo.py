import sqlite3

import pytest

from app_fi.data import categories_repo as repo
from app_fi.data import transactions_repo as tx_repo
from app_fi.data.db import get_db


@pytest.fixture()
def conn(tmp_path):
    c = get_db(tmp_path / "t.db")
    yield c
    c.close()


def test_add_creates_and_lists(conn):
    new_id = repo.add(conn, "Pets")
    names = {c["name"]: c["id"] for c in repo.list_active(conn)}
    assert names["Pets"] == new_id


def test_add_rejects_empty_name(conn):
    with pytest.raises(ValueError):
        repo.add(conn, "   ")


def test_add_duplicate_name_raises(conn):
    with pytest.raises(sqlite3.IntegrityError):
        repo.add(conn, "Alimentação")  # já existe no seed


def test_rename_changes_name(conn):
    cat_id = repo.add(conn, "Pets")
    repo.rename(conn, cat_id, "Animais de estimação")
    names = [c["name"] for c in repo.list_active(conn)]
    assert "Animais de estimação" in names
    assert "Pets" not in names


def test_archive_removes_from_active_list(conn):
    before = len(repo.list_active(conn))
    cat_id = repo.add(conn, "Pets")
    assert len(repo.list_active(conn)) == before + 1
    repo.archive(conn, cat_id)
    assert len(repo.list_active(conn)) == before


def test_archived_category_still_shows_on_past_transaction(conn):
    cat_id = repo.add(conn, "Pets")
    tx_repo.add_expense(conn, date="2026-09-01", amount_cents=1000, category_id=cat_id)
    repo.archive(conn, cat_id)

    row = tx_repo.list_month(conn, 2026, 9)[0]
    assert row["category_name"] == "Pets"  # o join não filtra arquivada
    assert cat_id not in [c["id"] for c in repo.list_active(conn)]
