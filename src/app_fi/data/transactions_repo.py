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
    """Insere uma despesa e devolve o id. `date` no formato ISO 'YYYY-MM-DD'.

    Categoria é opcional (fica "Sem categoria").
    """
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


def add_income(
    conn: sqlite3.Connection,
    *,
    date: str,
    amount_cents: int,
    income_source_id: int,
    payee_id: int | None = None,
    note: str | None = None,
    status: str = "confirmed",
) -> int:
    """Insere uma receita e devolve o id. A origem (`income_source_id`) é obrigatória."""
    if amount_cents <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    if income_source_id is None:
        raise ValueError("A receita precisa de uma origem.")
    cur = conn.execute(
        "INSERT INTO transactions "
        "  (date, amount_cents, account_id, kind, status, income_source_id, payee_id, note) "
        "VALUES (?, ?, ?, 'income', ?, ?, ?, ?)",
        (date, amount_cents, _default_cash_account_id(conn), status, income_source_id, payee_id, note),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_expense(
    conn: sqlite3.Connection,
    tx_id: int,
    *,
    date: str,
    amount_cents: int,
    category_id: int | None = None,
    payee_id: int | None = None,
    note: str | None = None,
) -> None:
    """Atualiza uma despesa existente. O tipo (despesa) não muda na edição."""
    if amount_cents <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    conn.execute(
        "UPDATE transactions "
        "SET date = ?, amount_cents = ?, category_id = ?, payee_id = ?, note = ? "
        "WHERE id = ? AND kind = 'expense'",
        (date, amount_cents, category_id, payee_id, note, tx_id),
    )
    conn.commit()


def update_income(
    conn: sqlite3.Connection,
    tx_id: int,
    *,
    date: str,
    amount_cents: int,
    income_source_id: int,
    payee_id: int | None = None,
    note: str | None = None,
) -> None:
    """Atualiza uma receita existente. A origem é obrigatória."""
    if amount_cents <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    if income_source_id is None:
        raise ValueError("A receita precisa de uma origem.")
    conn.execute(
        "UPDATE transactions "
        "SET date = ?, amount_cents = ?, income_source_id = ?, payee_id = ?, note = ? "
        "WHERE id = ? AND kind = 'income'",
        (date, amount_cents, income_source_id, payee_id, note, tx_id),
    )
    conn.commit()


def delete(conn: sqlite3.Connection, tx_id: int) -> None:
    conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()


_ROW_COLUMNS = (
    "id", "date", "amount_cents", "account_id", "kind", "status",
    "category_id", "income_source_id", "payee_id", "recurring_id",
    "note", "created_at",
)


def snapshot(row: sqlite3.Row) -> dict:
    """Extrai só as colunas reais da tabela de uma linha (que pode vir com os
    joins de categoria/origem). Guarde o retorno antes de editar/excluir para
    poder chamar :func:`restore` depois (o "Desfazer")."""
    d = dict(row)
    return {k: d[k] for k in _ROW_COLUMNS}


def restore(conn: sqlite3.Connection, values: dict) -> None:
    """Repõe um lançamento exatamente como estava, id incluído — o "Desfazer"
    de uma edição ou exclusão. `values` vem de :func:`snapshot`."""
    conn.execute(
        "INSERT OR REPLACE INTO transactions "
        "(id, date, amount_cents, account_id, kind, status, "
        " category_id, income_source_id, payee_id, recurring_id, note, created_at) "
        "VALUES (:id, :date, :amount_cents, :account_id, :kind, :status, "
        " :category_id, :income_source_id, :payee_id, :recurring_id, :note, :created_at)",
        values,
    )
    conn.commit()


def get(conn: sqlite3.Connection, tx_id: int) -> sqlite3.Row | None:
    return conn.execute(_SELECT + "WHERE t.id = ?", (tx_id,)).fetchone()


_SELECT = (
    "SELECT t.*, c.name AS category_name, s.name AS income_source_name, "
    "  pay.name AS payee_name "
    "FROM transactions t "
    "LEFT JOIN categories c ON c.id = t.category_id "
    "LEFT JOIN income_sources s ON s.id = t.income_source_id "
    "LEFT JOIN payees pay ON pay.id = t.payee_id "
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


def list_income_sources(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, name FROM income_sources WHERE archived = 0 ORDER BY id"
    ).fetchall()
