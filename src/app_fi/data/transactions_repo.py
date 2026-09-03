"""Acesso a `transactions` (e leitura de `categories` para a UI de lançamento).

Toda a SQL de lançamentos mora aqui. `core/` nunca fala com o SQLite direto.
"""

from __future__ import annotations

import sqlite3


def _default_cash_account_id(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT id FROM accounts WHERE type = 'cash' AND archived = 0 ORDER BY id LIMIT 1"
    ).fetchone()
    if row is None:
        raise RuntimeError("Nenhuma conta do tipo 'cash' cadastrada.")
    return row["id"]


def add_expense(
    conn: sqlite3.Connection,
    *,
    date: str,
    amount_cents: int,
    category_id: int | None = None,
    payee_id: int | None = None,
    note: str | None = None,
    status: str = "confirmed",
) -> int:
    """Insere uma despesa e devolve o id. `date` no formato ISO 'YYYY-MM-DD'."""
    if amount_cents <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    cur = conn.execute(
        "INSERT INTO transactions "
        "  (date, amount_cents, account_id, kind, status, category_id, payee_id, note) "
        "VALUES (?, ?, ?, 'expense', ?, ?, ?, ?)",
        (date, amount_cents, _default_cash_account_id(conn), status, category_id, payee_id, note),
    )
    conn.commit()
    return int(cur.lastrowid)


_SELECT = (
    "SELECT t.*, c.name AS category_name "
    "FROM transactions t "
    "LEFT JOIN categories c ON c.id = t.category_id "
)


def list_month(conn: sqlite3.Connection, year: int, month: int) -> list[sqlite3.Row]:
    ym = f"{year:04d}-{month:02d}"
    return conn.execute(
        _SELECT + "WHERE strftime('%Y-%m', t.date) = ? ORDER BY t.date DESC, t.id DESC",
        (ym,),
    ).fetchall()


def list_recent(conn: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    return conn.execute(
        _SELECT + "ORDER BY t.date DESC, t.id DESC LIMIT ?", (limit,)
    ).fetchall()


def list_categories(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, name FROM categories WHERE archived = 0 ORDER BY name"
    ).fetchall()
