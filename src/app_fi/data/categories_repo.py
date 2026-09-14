"""Acesso a `categories`. Renomear e arquivar refletem em toda a base porque
lançamentos guardam `category_id`, não o nome.
"""

from __future__ import annotations

import sqlite3


def list_active(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, name, archived FROM categories WHERE archived = 0 ORDER BY name"
    ).fetchall()


def add(conn: sqlite3.Connection, name: str) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Informe um nome.")
    cur = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    return int(cur.lastrowid)


def rename(conn: sqlite3.Connection, category_id: int, name: str) -> None:
    name = (name or "").strip()
    if not name:
        raise ValueError("Informe um nome.")
    conn.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
    conn.commit()


def archive(conn: sqlite3.Connection, category_id: int) -> None:
    """Marca como arquivada. Não apaga — lançamentos antigos continuam mostrando
    o nome via join; ela só some das listas de escolha para novos lançamentos.
    """
    conn.execute("UPDATE categories SET archived = 1 WHERE id = ?", (category_id,))
    conn.commit()
