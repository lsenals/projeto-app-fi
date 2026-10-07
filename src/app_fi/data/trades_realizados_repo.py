"""Acesso a `trades_realizados` — o diário de trades encerrados de Cripto e Ações (008)."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from app_fi.core.trades import TradeRealizado, trade_de_linha, validar_trade


def _txt(valor: Decimal) -> str:
    return f"{valor:f}"


def list_trades(conn: sqlite3.Connection, modulo: str) -> list[TradeRealizado]:
    """Do mais recente (data da venda) para o mais antigo."""
    rows = conn.execute(
        "SELECT * FROM trades_realizados WHERE modulo = ? ORDER BY sell_date DESC, id DESC", (modulo,),
    ).fetchall()
    return [trade_de_linha(r) for r in rows]


def get_trade(conn: sqlite3.Connection, trade_id: int) -> TradeRealizado | None:
    row = conn.execute("SELECT * FROM trades_realizados WHERE id = ?", (trade_id,)).fetchone()
    return trade_de_linha(row) if row else None


def add_trade(
    conn: sqlite3.Connection, *, modulo: str, simbolo: str, nome: str | None = None, moeda: str = "BRL",
    quantidade: Decimal | None = None, data_compra: str, valor_compra: Decimal, data_venda: str,
    valor_venda: Decimal, custos: Decimal = Decimal(0), nota: str | None = None,
) -> int:
    simbolo = (simbolo or "").strip().upper()
    validar_trade(modulo=modulo, simbolo=simbolo, moeda=moeda, data_compra=data_compra, valor_compra=valor_compra,
                  data_venda=data_venda, valor_venda=valor_venda, custos=custos, quantidade=quantidade)
    cur = conn.execute(
        "INSERT INTO trades_realizados (modulo, symbol, name, currency, quantity, buy_date, buy_value, "
        "sell_date, sell_value, costs, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (modulo, simbolo, (nome or "").strip() or None, moeda, _txt(quantidade) if quantidade else None,
         data_compra, _txt(valor_compra), data_venda, _txt(valor_venda), _txt(custos), (nota or "").strip() or None),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_trade(
    conn: sqlite3.Connection, trade_id: int, *, simbolo: str, nome: str | None = None, moeda: str = "BRL",
    quantidade: Decimal | None = None, data_compra: str, valor_compra: Decimal, data_venda: str,
    valor_venda: Decimal, custos: Decimal = Decimal(0), nota: str | None = None,
) -> None:
    atual = get_trade(conn, trade_id)
    if atual is None:
        raise ValueError("Trade não encontrado.")
    simbolo = (simbolo or "").strip().upper()
    validar_trade(modulo=atual.modulo, simbolo=simbolo, moeda=moeda, data_compra=data_compra,
                  valor_compra=valor_compra, data_venda=data_venda, valor_venda=valor_venda, custos=custos,
                  quantidade=quantidade)
    conn.execute(
        "UPDATE trades_realizados SET symbol = ?, name = ?, currency = ?, quantity = ?, buy_date = ?, "
        "buy_value = ?, sell_date = ?, sell_value = ?, costs = ?, note = ? WHERE id = ?",
        (simbolo, (nome or "").strip() or None, moeda, _txt(quantidade) if quantidade else None, data_compra,
         _txt(valor_compra), data_venda, _txt(valor_venda), _txt(custos), (nota or "").strip() or None, trade_id),
    )
    conn.commit()


def delete_trade(conn: sqlite3.Connection, trade_id: int) -> None:
    conn.execute("DELETE FROM trades_realizados WHERE id = ?", (trade_id,))
    conn.commit()
