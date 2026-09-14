"""Acesso a `payees` — a memória "estabelecimento -> categoria".

Não tinha nenhuma função de escrita até agora (o dialog de lançamento manual
nunca chegou a ter campo de estabelecimento). A importação de fatura é o
primeiro fluxo a alimentar essa memória de verdade.
"""

from __future__ import annotations

import sqlite3


def get_or_create(conn: sqlite3.Connection, name: str) -> int:
    name = name.strip()
    row = conn.execute("SELECT id FROM payees WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return int(row["id"])
    cur = conn.execute("INSERT INTO payees (name) VALUES (?)", (name,))
    conn.commit()
    return int(cur.lastrowid)


def find_default_category_id(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute(
        "SELECT default_category_id FROM payees WHERE name = ?", (name.strip(),)
    ).fetchone()
    if row is None:
        return None
    return row["default_category_id"]


def set_default_category(conn: sqlite3.Connection, payee_id: int, category_id: int | None) -> None:
    conn.execute("UPDATE payees SET default_category_id = ? WHERE id = ?", (category_id, payee_id))
    conn.commit()
