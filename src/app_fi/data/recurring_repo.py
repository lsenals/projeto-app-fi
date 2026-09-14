"""Acesso a `recurring` — definições de cobrança recorrente.

Só modela e guarda. Nada aqui cria lançamento sozinho — isso é o motor de
materialização, trabalho futuro. `total_installments=None` é "sem fim
definido" (assinatura, conta de consumo), não um caso vazio a preencher.
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


def _validate(expected_amount_cents: int, total_installments: int | None) -> None:
    if expected_amount_cents <= 0:
        raise ValueError("O valor esperado deve ser maior que zero.")
    if total_installments is not None and total_installments <= 0:
        raise ValueError("O total de parcelas deve ser maior que zero.")


_SELECT = (
    "SELECT r.*, c.name AS category_name, s.name AS income_source_name "
    "FROM recurring r "
    "LEFT JOIN categories c ON c.id = r.category_id "
    "LEFT JOIN income_sources s ON s.id = r.income_source_id "
)


def add(
    conn: sqlite3.Connection,
    *,
    label: str,
    kind: str,
    expected_amount_cents: int,
    interval_unit: str,
    next_date: str,
    interval_count: int = 1,
    category_id: int | None = None,
    income_source_id: int | None = None,
    total_installments: int | None = None,
    current_installment: int = 1,
) -> int:
    _validate(expected_amount_cents, total_installments)
    cur = conn.execute(
        "INSERT INTO recurring "
        "  (label, kind, expected_amount_cents, category_id, income_source_id, "
        "   account_id, interval_unit, interval_count, next_date, "
        "   total_installments, current_installment) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (label, kind, expected_amount_cents, category_id, income_source_id,
         _default_cash_account_id(conn), interval_unit, interval_count, next_date,
         total_installments, current_installment),
    )
    conn.commit()
    return int(cur.lastrowid)


def update(
    conn: sqlite3.Connection,
    recurring_id: int,
    *,
    label: str,
    kind: str,
    expected_amount_cents: int,
    interval_unit: str,
    next_date: str,
    interval_count: int = 1,
    category_id: int | None = None,
    income_source_id: int | None = None,
    total_installments: int | None = None,
    current_installment: int = 1,
) -> None:
    _validate(expected_amount_cents, total_installments)
    conn.execute(
        "UPDATE recurring SET label = ?, kind = ?, expected_amount_cents = ?, "
        "  category_id = ?, income_source_id = ?, interval_unit = ?, "
        "  interval_count = ?, next_date = ?, total_installments = ?, "
        "  current_installment = ? "
        "WHERE id = ?",
        (label, kind, expected_amount_cents, category_id, income_source_id,
         interval_unit, interval_count, next_date, total_installments,
         current_installment, recurring_id),
    )
    conn.commit()


def list_active(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(_SELECT + "WHERE r.active = 1 ORDER BY r.next_date").fetchall()


def get(conn: sqlite3.Connection, recurring_id: int) -> sqlite3.Row | None:
    return conn.execute(_SELECT + "WHERE r.id = ?", (recurring_id,)).fetchone()


def deactivate(conn: sqlite3.Connection, recurring_id: int) -> None:
    conn.execute("UPDATE recurring SET active = 0 WHERE id = ?", (recurring_id,))
    conn.commit()
