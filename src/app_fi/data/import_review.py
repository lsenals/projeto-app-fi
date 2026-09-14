"""Liga os pré-lançamentos (core/c6_import.py) ao banco: sugestão de
categoria, aviso de possível duplicata, e a gravação em definitivo quando o
usuário confirma a revisão manual.

Nada aqui grava sozinho — cada `ImportedRow` só vira lançamento de verdade
quando `confirm_expense`/`confirm_income` é chamado explicitamente, uma vez
por linha que o usuário manteve na tela de revisão.
"""

from __future__ import annotations

import sqlite3

from app_fi.core.c6_import import ImportedRow
from app_fi.data import payees_repo
from app_fi.data import transactions_repo as repo


def suggest_category_id(conn: sqlite3.Connection, row: ImportedRow) -> int | None:
    """Memória de estabelecimento (mais forte, é o seu próprio histórico)
    prevalece sobre a categoria que o C6 atribuiu no arquivo."""
    if row.kind != "expense":
        return None

    from_memory = payees_repo.find_default_category_id(conn, row.description)
    if from_memory is not None:
        return from_memory

    if row.suggested_category_name is None:
        return None
    match = conn.execute(
        "SELECT id FROM categories WHERE name = ? AND archived = 0",
        (row.suggested_category_name,),
    ).fetchone()
    return match["id"] if match is not None else None


def is_probable_duplicate(conn: sqlite3.Connection, row: ImportedRow) -> bool:
    """Mesma data + valor + estabelecimento já lançado antes — provável
    reimportação do mesmo período, não um alerta automático de exclusão."""
    match = conn.execute(
        "SELECT 1 FROM transactions t JOIN payees p ON p.id = t.payee_id "
        "WHERE t.date = ? AND t.amount_cents = ? AND t.kind = ? AND p.name = ? "
        "LIMIT 1",
        (row.date, row.amount_cents, row.kind, row.description),
    ).fetchone()
    return match is not None


def confirm_expense(conn: sqlite3.Connection, row: ImportedRow, category_id: int | None) -> int:
    """Grava a despesa e ensina a memória de estabelecimento com a categoria
    que o usuário confirmou (ou escolheu) na revisão."""
    payee_id = payees_repo.get_or_create(conn, row.description)
    if category_id is not None:
        payees_repo.set_default_category(conn, payee_id, category_id)
    return repo.add_expense(
        conn, date=row.date, amount_cents=row.amount_cents,
        category_id=category_id, payee_id=payee_id, note=row.note,
    )


def confirm_income(conn: sqlite3.Connection, row: ImportedRow, income_source_id: int) -> int:
    payee_id = payees_repo.get_or_create(conn, row.description)
    return repo.add_income(
        conn, date=row.date, amount_cents=row.amount_cents,
        income_source_id=income_source_id, payee_id=payee_id, note=row.note,
    )
