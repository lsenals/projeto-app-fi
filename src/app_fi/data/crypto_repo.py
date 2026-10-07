"""Acesso a `crypto_assets`, `crypto_trades` e `crypto_price_history`.

Números decimais entram e saem como `Decimal` na API pública e ficam como TEXT
no banco (ver 006_crypto.sql). A regra "não vender mais do que se tem" mora aqui
porque depende do histórico inteiro de operações do ativo.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from decimal import Decimal

from app_fi.core.crypto import (
    Carteira, Operacao, calcular_posicao, montar_carteira, normalizar_simbolo,
)


def _txt(valor: Decimal) -> str:
    # 'f' evita notação científica ('1E-8') no banco
    return f"{valor:f}"


def list_assets(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM crypto_assets ORDER BY id").fetchall()


def get_asset(conn: sqlite3.Connection, asset_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM crypto_assets WHERE id = ?", (asset_id,)).fetchone()


def add_custom_asset(conn: sqlite3.Connection, symbol: str, name: str) -> int:
    """Cadastra um ativo fora do catálogo. Levanta ValueError se o símbolo for inválido ou já existir."""
    simbolo = normalizar_simbolo(symbol)
    nome = (name or "").strip() or simbolo
    if conn.execute("SELECT 1 FROM crypto_assets WHERE symbol = ?", (simbolo,)).fetchone():
        raise ValueError(f"{simbolo} já está na lista.")
    cur = conn.execute(
        "INSERT INTO crypto_assets (symbol, name, is_custom) VALUES (?, ?, 1)", (simbolo, nome),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_trades(conn: sqlite3.Connection, asset_id: int | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM crypto_trades"
    params: tuple = ()
    if asset_id is not None:
        sql += " WHERE asset_id = ?"
        params = (asset_id,)
    return conn.execute(sql + " ORDER BY date, id", params).fetchall()


def get_trade(conn: sqlite3.Connection, trade_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM crypto_trades WHERE id = ?", (trade_id,)).fetchone()


def _operacoes(conn: sqlite3.Connection, asset_id: int) -> list[Operacao]:
    return [
        Operacao(r["side"], r["date"], Decimal(r["quantity"]), Decimal(r["unit_price"]),
                 Decimal(r["fee"] or "0"), r["id"])
        for r in list_trades(conn, asset_id)
    ]


def _validar(*, side: str, date: str, quantity: Decimal, unit_price: Decimal, fee: Decimal) -> None:
    if side not in ("buy", "sell"):
        raise ValueError("Escolha compra ou venda.")
    try:
        dt.date.fromisoformat(date)
    except ValueError:
        raise ValueError("Data inválida.") from None
    if quantity <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")
    if unit_price <= 0:
        raise ValueError("O preço deve ser maior que zero.")
    if fee < 0:
        raise ValueError("A taxa não pode ser negativa.")


def add_trade(
    conn: sqlite3.Connection, *, asset_id: int, side: str, date: str,
    quantity: Decimal, unit_price: Decimal, fee: Decimal = Decimal(0), note: str | None = None,
) -> int:
    _validar(side=side, date=date, quantity=quantity, unit_price=unit_price, fee=fee)
    # replay com a nova operação: recusa vender mais do que existe naquele momento
    calcular_posicao([*_operacoes(conn, asset_id), Operacao(side, date, quantity, unit_price, fee, 10**9)])
    cur = conn.execute(
        "INSERT INTO crypto_trades (asset_id, side, date, quantity, unit_price, fee, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (asset_id, side, date, _txt(quantity), _txt(unit_price), _txt(fee), note or None),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_trade(
    conn: sqlite3.Connection, trade_id: int, *, side: str, date: str,
    quantity: Decimal, unit_price: Decimal, fee: Decimal = Decimal(0), note: str | None = None,
) -> None:
    _validar(side=side, date=date, quantity=quantity, unit_price=unit_price, fee=fee)
    atual = get_trade(conn, trade_id)
    if atual is None:
        raise ValueError("Operação não encontrada.")
    outras = [o for o in _operacoes(conn, atual["asset_id"]) if o.id != trade_id]
    calcular_posicao([*outras, Operacao(side, date, quantity, unit_price, fee, trade_id)])
    conn.execute(
        "UPDATE crypto_trades SET side = ?, date = ?, quantity = ?, unit_price = ?, fee = ?, note = ? "
        "WHERE id = ?",
        (side, date, _txt(quantity), _txt(unit_price), _txt(fee), note or None, trade_id),
    )
    conn.commit()


def delete_trade(conn: sqlite3.Connection, trade_id: int) -> None:
    """Levanta ValueError se apagar a operação deixaria uma venda posterior sem saldo."""
    atual = get_trade(conn, trade_id)
    if atual is None:
        return
    calcular_posicao([o for o in _operacoes(conn, atual["asset_id"]) if o.id != trade_id])
    conn.execute("DELETE FROM crypto_trades WHERE id = ?", (trade_id,))
    conn.commit()


def set_price(conn: sqlite3.Connection, asset_id: int, price: Decimal, date: str | None = None) -> None:
    """Informa o preço atual (e guarda o ponto no histórico, que alimenta a evolução)."""
    if price <= 0:
        raise ValueError("O preço deve ser maior que zero.")
    dia = date or dt.date.today().isoformat()
    conn.execute(
        "UPDATE crypto_assets SET current_price = ?, price_updated_at = ? WHERE id = ?",
        (_txt(price), dia, asset_id),
    )
    conn.execute(
        "INSERT INTO crypto_price_history (asset_id, date, price) VALUES (?, ?, ?) "
        "ON CONFLICT (asset_id, date) DO UPDATE SET price = excluded.price",
        (asset_id, dia, _txt(price)),
    )
    conn.commit()


def set_targets(
    conn: sqlite3.Connection, asset_id: int, gain_pct: Decimal | None, stop_pct: Decimal | None,
) -> None:
    """Meta de trade (ganho % sobre o preço médio) e stop (perda % máxima). None remove."""
    if gain_pct is not None and gain_pct <= 0:
        raise ValueError("A meta de ganho deve ser maior que zero.")
    if stop_pct is not None and not 0 < stop_pct < 100:
        raise ValueError("O stop deve ficar entre 0 e 100%.")
    conn.execute(
        "UPDATE crypto_assets SET target_gain_pct = ?, stop_loss_pct = ? WHERE id = ?",
        (None if gain_pct is None else _txt(gain_pct), None if stop_pct is None else _txt(stop_pct), asset_id),
    )
    conn.commit()


def load_wallet(conn: sqlite3.Connection) -> Carteira:
    return montar_carteira(
        list_assets(conn),
        list_trades(conn),
        conn.execute("SELECT * FROM crypto_price_history ORDER BY date").fetchall(),
    )
