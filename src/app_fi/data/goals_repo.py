"""Acesso a `goals`, `goal_records` (histórico de PRs) e `app_settings`.

Toda a SQL de objetivos e preferências mora aqui — `core/goals.py` só avalia
números, nunca fala com o SQLite.
"""

from __future__ import annotations

import sqlite3

_SELECT = (
    "SELECT g.*, c.name AS category_name "
    "FROM goals g "
    "LEFT JOIN categories c ON c.id = g.category_id "
)


def add(
    conn: sqlite3.Connection,
    *,
    kind: str,
    label: str,
    category_id: int | None = None,
    target_cents: int | None = None,
    target_months: int | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO goals (kind, label, category_id, target_cents, target_months) "
        "VALUES (?, ?, ?, ?, ?)",
        (kind, label, category_id, target_cents, target_months),
    )
    conn.commit()
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, goal_id: int) -> sqlite3.Row | None:
    return conn.execute(_SELECT + "WHERE g.id = ?", (goal_id,)).fetchone()


def list_active(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(_SELECT + "WHERE g.active = 1 ORDER BY g.id").fetchall()


def deactivate(conn: sqlite3.Connection, goal_id: int) -> None:
    conn.execute("UPDATE goals SET active = 0 WHERE id = ?", (goal_id,))
    conn.commit()


def record_result(conn: sqlite3.Connection, goal_id: int, year_month: str, achieved: bool) -> None:
    """Grava (ou atualiza) o resultado de um objetivo para um mês — idempotente,
    pode ser chamado toda vez que a tela de Objetivos é aberta."""
    conn.execute(
        "INSERT INTO goal_records (goal_id, year_month, achieved) VALUES (?, ?, ?) "
        "ON CONFLICT (goal_id, year_month) DO UPDATE SET achieved = excluded.achieved",
        (goal_id, year_month, int(achieved)),
    )
    conn.commit()


def recent_achievements(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    """PRs (objetivos batidos), mais recentes primeiro."""
    return conn.execute(
        "SELECT r.*, g.label AS goal_label FROM goal_records r "
        "JOIN goals g ON g.id = r.goal_id "
        "WHERE r.achieved = 1 "
        "ORDER BY r.year_month DESC, r.id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def monthly_any_achieved(conn: sqlite3.Connection, limit: int = 12) -> list[bool]:
    """Um bool por mês (mais recente primeiro): True se algum objetivo bateu
    naquele mês. Base para `core.goals.overall_streak`."""
    rows = conn.execute(
        "SELECT year_month, MAX(achieved) AS any_achieved FROM goal_records "
        "GROUP BY year_month ORDER BY year_month DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [bool(r["any_achieved"]) for r in rows]


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row is not None else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
