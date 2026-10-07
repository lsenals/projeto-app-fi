"""Repositório genérico de uma carteira de ativos negociados (Cripto, Ações).

Os dois módulos têm o mesmo modelo — ativos, operações de compra/venda com preço médio, preço atual
informado à mão e histórico de preços — e só mudam o catálogo e os textos. Por isso as tabelas têm as
mesmas colunas e o mesmo prefixo (`crypto_*`, `acoes_*`) e este repositório é parametrizado por ele.

O prefixo vai para o SQL por interpolação, então só aceita os valores da lista fixa `PREFIXOS` (nunca
texto vindo da tela). Números decimais entram e saem como `Decimal` e ficam como TEXT no banco
(ver 006_crypto.sql). A regra "não vender mais do que se tem" mora aqui porque depende do histórico
inteiro de operações do ativo.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from decimal import Decimal

from app_fi.core.crypto import (
    Carteira, Operacao, calcular_posicao, montar_carteira, normalizar_simbolo, validar_moeda,
)
from app_fi.data import goals_repo  # app_settings (get_setting/set_setting)

PREFIXOS = ("crypto", "acoes")

_CHAVE_COTACAO_USD = "usd_brl"  # uma só cotação do dólar para o app inteiro


def _txt(valor: Decimal) -> str:
    # 'f' evita notação científica ('1E-8') no banco
    return f"{valor:f}"


class CarteiraRepo:
    def __init__(self, prefixo: str) -> None:
        if prefixo not in PREFIXOS:
            raise ValueError(f"Prefixo de carteira desconhecido: {prefixo!r}")
        self.prefixo = prefixo
        self._assets = f"{prefixo}_assets"
        self._trades = f"{prefixo}_trades"
        self._history = f"{prefixo}_price_history"
        self._chave_moeda_exibicao = f"{prefixo}_display_currency"

    # ---------------------------------------------------------------- ativos

    def list_assets(self, conn: sqlite3.Connection) -> list[sqlite3.Row]:
        return conn.execute(f"SELECT * FROM {self._assets} ORDER BY id").fetchall()

    def get_asset(self, conn: sqlite3.Connection, asset_id: int) -> sqlite3.Row | None:
        return conn.execute(f"SELECT * FROM {self._assets} WHERE id = ?", (asset_id,)).fetchone()

    def add_custom_asset(self, conn: sqlite3.Connection, symbol: str, name: str, currency: str = "BRL") -> int:
        """Cadastra um ativo fora do catálogo. Levanta ValueError se o símbolo for inválido ou já existir."""
        simbolo = normalizar_simbolo(symbol)
        nome = (name or "").strip() or simbolo
        moeda = validar_moeda(currency)
        if conn.execute(f"SELECT 1 FROM {self._assets} WHERE symbol = ?", (simbolo,)).fetchone():
            raise ValueError(f"{simbolo} já está na lista.")
        cur = conn.execute(
            f"INSERT INTO {self._assets} (symbol, name, is_custom, currency) VALUES (?, ?, 1, ?)",
            (simbolo, nome, moeda),
        )
        conn.commit()
        return int(cur.lastrowid)

    def set_asset_currency(self, conn: sqlite3.Connection, asset_id: int, currency: str) -> None:
        """Muda a moeda de um ativo. Só enquanto ele não tem operações: depois disso os números
        já lançados seriam reinterpretados em outra moeda (1.000 US$ não vira 1.000 R$)."""
        moeda = validar_moeda(currency)
        if conn.execute(f"SELECT 1 FROM {self._trades} WHERE asset_id = ?", (asset_id,)).fetchone():
            raise ValueError("Este ativo já tem operações — a moeda não pode mais ser trocada.")
        # o preço informado antes da 1ª operação também é interpretado na moeda antiga: descarta
        conn.execute(
            f"UPDATE {self._assets} SET currency = ?, current_price = NULL, price_updated_at = NULL WHERE id = ?",
            (moeda, asset_id),
        )
        conn.execute(f"DELETE FROM {self._history} WHERE asset_id = ?", (asset_id,))
        conn.commit()

    # ---------------------------------------------------------------- moeda

    def get_usd_rate(self, conn: sqlite3.Connection) -> Decimal | None:
        """Reais por dólar, informado à mão. None se ainda não foi definido."""
        valor = goals_repo.get_setting(conn, _CHAVE_COTACAO_USD, default=None)
        return Decimal(valor) if valor else None

    def set_usd_rate(self, conn: sqlite3.Connection, rate: Decimal) -> None:
        if rate <= 0:
            raise ValueError("A cotação do dólar deve ser maior que zero.")
        goals_repo.set_setting(conn, _CHAVE_COTACAO_USD, _txt(rate))

    def get_display_currency(self, conn: sqlite3.Connection) -> str:
        return goals_repo.get_setting(conn, self._chave_moeda_exibicao, default="BRL") or "BRL"

    def set_display_currency(self, conn: sqlite3.Connection, currency: str) -> None:
        goals_repo.set_setting(conn, self._chave_moeda_exibicao, validar_moeda(currency))

    # ------------------------------------------------------------- operações

    def list_trades(self, conn: sqlite3.Connection, asset_id: int | None = None) -> list[sqlite3.Row]:
        sql = f"SELECT * FROM {self._trades}"
        params: tuple = ()
        if asset_id is not None:
            sql += " WHERE asset_id = ?"
            params = (asset_id,)
        return conn.execute(sql + " ORDER BY date, id", params).fetchall()

    def get_trade(self, conn: sqlite3.Connection, trade_id: int) -> sqlite3.Row | None:
        return conn.execute(f"SELECT * FROM {self._trades} WHERE id = ?", (trade_id,)).fetchone()

    def _operacoes(self, conn: sqlite3.Connection, asset_id: int) -> list[Operacao]:
        return [
            Operacao(r["side"], r["date"], Decimal(r["quantity"]), Decimal(r["unit_price"]),
                     Decimal(r["fee"] or "0"), r["id"])
            for r in self.list_trades(conn, asset_id)
        ]

    @staticmethod
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
        self, conn: sqlite3.Connection, *, asset_id: int, side: str, date: str,
        quantity: Decimal, unit_price: Decimal, fee: Decimal = Decimal(0), note: str | None = None,
    ) -> int:
        self._validar(side=side, date=date, quantity=quantity, unit_price=unit_price, fee=fee)
        # replay com a nova operação: recusa vender mais do que existe naquele momento
        calcular_posicao([*self._operacoes(conn, asset_id), Operacao(side, date, quantity, unit_price, fee, 10**9)])
        cur = conn.execute(
            f"INSERT INTO {self._trades} (asset_id, side, date, quantity, unit_price, fee, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (asset_id, side, date, _txt(quantity), _txt(unit_price), _txt(fee), note or None),
        )
        conn.commit()
        return int(cur.lastrowid)

    def update_trade(
        self, conn: sqlite3.Connection, trade_id: int, *, side: str, date: str,
        quantity: Decimal, unit_price: Decimal, fee: Decimal = Decimal(0), note: str | None = None,
    ) -> None:
        self._validar(side=side, date=date, quantity=quantity, unit_price=unit_price, fee=fee)
        atual = self.get_trade(conn, trade_id)
        if atual is None:
            raise ValueError("Operação não encontrada.")
        outras = [o for o in self._operacoes(conn, atual["asset_id"]) if o.id != trade_id]
        calcular_posicao([*outras, Operacao(side, date, quantity, unit_price, fee, trade_id)])
        conn.execute(
            f"UPDATE {self._trades} SET side = ?, date = ?, quantity = ?, unit_price = ?, fee = ?, note = ? "
            "WHERE id = ?",
            (side, date, _txt(quantity), _txt(unit_price), _txt(fee), note or None, trade_id),
        )
        conn.commit()

    def delete_trade(self, conn: sqlite3.Connection, trade_id: int) -> None:
        """Levanta ValueError se apagar a operação deixaria uma venda posterior sem saldo."""
        atual = self.get_trade(conn, trade_id)
        if atual is None:
            return
        calcular_posicao([o for o in self._operacoes(conn, atual["asset_id"]) if o.id != trade_id])
        conn.execute(f"DELETE FROM {self._trades} WHERE id = ?", (trade_id,))
        conn.commit()

    # ---------------------------------------------------------- preço e metas

    def set_price(self, conn: sqlite3.Connection, asset_id: int, price: Decimal, date: str | None = None) -> None:
        """Informa o preço atual (e guarda o ponto no histórico, que alimenta a evolução)."""
        if price <= 0:
            raise ValueError("O preço deve ser maior que zero.")
        dia = date or dt.date.today().isoformat()
        conn.execute(
            f"UPDATE {self._assets} SET current_price = ?, price_updated_at = ? WHERE id = ?",
            (_txt(price), dia, asset_id),
        )
        conn.execute(
            f"INSERT INTO {self._history} (asset_id, date, price) VALUES (?, ?, ?) "
            "ON CONFLICT (asset_id, date) DO UPDATE SET price = excluded.price",
            (asset_id, dia, _txt(price)),
        )
        conn.commit()

    def set_targets(
        self, conn: sqlite3.Connection, asset_id: int, gain_pct: Decimal | None, stop_pct: Decimal | None,
    ) -> None:
        """Meta de trade (ganho % sobre o preço médio) e stop (perda % máxima). None remove."""
        if gain_pct is not None and gain_pct <= 0:
            raise ValueError("A meta de ganho deve ser maior que zero.")
        if stop_pct is not None and not 0 < stop_pct < 100:
            raise ValueError("O stop deve ficar entre 0 e 100%.")
        conn.execute(
            f"UPDATE {self._assets} SET target_gain_pct = ?, stop_loss_pct = ? WHERE id = ?",
            (None if gain_pct is None else _txt(gain_pct), None if stop_pct is None else _txt(stop_pct), asset_id),
        )
        conn.commit()

    def load_wallet(self, conn: sqlite3.Connection, moeda: str | None = None) -> Carteira:
        """`moeda`: moeda do resumo; sem ela, usa a preferência de exibição salva do módulo."""
        return montar_carteira(
            self.list_assets(conn),
            self.list_trades(conn),
            conn.execute(f"SELECT * FROM {self._history} ORDER BY date").fetchall(),
            moeda_exibicao=moeda or self.get_display_currency(conn),
            cotacao_usd=self.get_usd_rate(conn),
        )
