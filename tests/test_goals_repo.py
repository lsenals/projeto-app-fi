import pytest

from app_fi.data import goals_repo as repo
from app_fi.data.db import get_db


@pytest.fixture()
def conn(tmp_path):
    c = get_db(tmp_path / "t.db")
    yield c
    c.close()


def _cat_id(conn, name):
    return conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()["id"]


def test_add_and_get(conn):
    cat = _cat_id(conn, "Alimentação")
    goal_id = repo.add(conn, kind="teto_categoria", label="Delivery até R$300", category_id=cat, target_cents=30000)
    saved = repo.get(conn, goal_id)
    assert saved["label"] == "Delivery até R$300"
    assert saved["category_name"] == "Alimentação"
    assert saved["target_cents"] == 30000


def test_list_active_excludes_deactivated(conn):
    a = repo.add(conn, kind="renda_extra", label="A", target_cents=10000)
    b = repo.add(conn, kind="renda_extra", label="B", target_cents=20000)
    repo.deactivate(conn, a)
    ativos = [g["label"] for g in repo.list_active(conn)]
    assert ativos == ["B"]


def test_record_result_is_idempotent_per_month(conn):
    goal_id = repo.add(conn, kind="renda_extra", label="X", target_cents=10000)
    repo.record_result(conn, goal_id, "2026-09", achieved=False)
    repo.record_result(conn, goal_id, "2026-09", achieved=True)  # sobrescreve
    rows = conn.execute("SELECT achieved FROM goal_records WHERE goal_id = ?", (goal_id,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["achieved"] == 1


def test_recent_achievements_only_lists_achieved(conn):
    goal_id = repo.add(conn, kind="renda_extra", label="X", target_cents=10000)
    repo.record_result(conn, goal_id, "2026-08", achieved=False)
    repo.record_result(conn, goal_id, "2026-09", achieved=True)
    achieved = repo.recent_achievements(conn)
    assert len(achieved) == 1
    assert achieved[0]["year_month"] == "2026-09"
    assert achieved[0]["goal_label"] == "X"


def test_monthly_any_achieved_most_recent_first(conn):
    a = repo.add(conn, kind="renda_extra", label="A", target_cents=10000)
    b = repo.add(conn, kind="renda_extra", label="B", target_cents=10000)
    repo.record_result(conn, a, "2026-07", achieved=False)
    repo.record_result(conn, b, "2026-07", achieved=False)
    repo.record_result(conn, a, "2026-08", achieved=True)
    repo.record_result(conn, b, "2026-08", achieved=False)
    repo.record_result(conn, a, "2026-09", achieved=False)
    flags = repo.monthly_any_achieved(conn)
    assert flags == [False, True, False]


def test_count_achieved_conta_so_os_batidos(conn):
    a = repo.add(conn, kind="renda_extra", label="A", target_cents=10000)
    b = repo.add(conn, kind="renda_extra", label="B", target_cents=10000)
    assert repo.count_achieved(conn) == 0
    repo.record_result(conn, a, "2026-08", achieved=True)
    repo.record_result(conn, b, "2026-08", achieved=False)
    repo.record_result(conn, a, "2026-09", achieved=True)
    assert repo.count_achieved(conn) == 2


def test_settings_roundtrip(conn):
    assert repo.get_setting(conn, "theme_mode", default="dark") == "dark"
    repo.set_setting(conn, "theme_mode", "light")
    assert repo.get_setting(conn, "theme_mode") == "light"
    repo.set_setting(conn, "theme_mode", "dark")
    assert repo.get_setting(conn, "theme_mode") == "dark"
