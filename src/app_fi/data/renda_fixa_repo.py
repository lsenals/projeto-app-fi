"""Acesso a `rf_posicoes` e `rf_movimentos` (009_renda_fixa.sql).

Valores decimais entram e saem como `Decimal` e ficam como TEXT no banco. As regras de negócio
(validação, estimativa de IR, resumo) moram em `core/renda_fixa.py`.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from decimal import Decimal

from app_fi.core.renda_fixa import (
    CarteiraRendaFixa, PosicaoRF, montar_carteira_rf, montar_posicao, validar_movimento, validar_posicao,
)


def _txt(valor: Decimal | None) -> str | None:
    return None if valor is None else f"{valor:f}"


def _limpo(texto: str | None) -> str | None:
    return (texto or "").strip() or None


def load(conn: sqlite3.Connection, hoje: dt.date | None = None) -> CarteiraRendaFixa:
    return montar_carteira_rf(
        conn.execute("SELECT * FROM rf_posicoes ORDER BY id").fetchall(),
        conn.execute("SELECT * FROM rf_movimentos ORDER BY data, id").fetchall(),
        hoje,
    )


def get(conn: sqlite3.Connection, posicao_id: int, hoje: dt.date | None = None) -> PosicaoRF | None:
    row = conn.execute("SELECT * FROM rf_posicoes WHERE id = ?", (posicao_id,)).fetchone()
    if row is None:
        return None
    movs = conn.execute("SELECT * FROM rf_movimentos WHERE posicao_id = ?", (posicao_id,)).fetchall()
    return montar_posicao(row, movs, hoje or dt.date.today())


def add_posicao(
    conn: sqlite3.Connection, *, tipo: str, nome: str | None, instituicao: str, corretora: str | None,
    indexador: str, taxa: Decimal | None, vencimento: str | None, liquidez: str, isento_ir: bool,
    observacao: str | None, data_aporte: str, valor_aporte: Decimal, custos_aporte: Decimal = Decimal(0),
) -> int:
    """Cria a aplicação já com o primeiro aporte (tudo ou nada). Retorna o id da aplicação."""
    validar_posicao(tipo=tipo, instituicao=instituicao, indexador=indexador, taxa=taxa, vencimento=vencimento,
                    liquidez=liquidez, data_aporte=data_aporte)
    validar_movimento(tipo="aporte", data=data_aporte, valor=valor_aporte, custos=custos_aporte)
    cur = conn.execute(
        "INSERT INTO rf_posicoes (tipo, nome, instituicao, corretora, indexador, taxa, vencimento, liquidez, "
        "isento_ir, observacao) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (tipo, _limpo(nome), instituicao.strip(), _limpo(corretora), indexador, _txt(taxa), vencimento or None,
         liquidez, 1 if isento_ir else 0, _limpo(observacao)),
    )
    posicao_id = int(cur.lastrowid)
    conn.execute(
        "INSERT INTO rf_movimentos (posicao_id, tipo, data, valor, custos) VALUES (?, 'aporte', ?, ?, ?)",
        (posicao_id, data_aporte, _txt(valor_aporte), _txt(custos_aporte)),
    )
    conn.commit()
    return posicao_id


def update_posicao(
    conn: sqlite3.Connection, posicao_id: int, *, tipo: str, nome: str | None, instituicao: str,
    corretora: str | None, indexador: str, taxa: Decimal | None, vencimento: str | None, liquidez: str,
    isento_ir: bool, observacao: str | None,
) -> None:
    atual = get(conn, posicao_id)
    if atual is None:
        raise ValueError("Aplicação não encontrada.")
    validar_posicao(tipo=tipo, instituicao=instituicao, indexador=indexador, taxa=taxa, vencimento=vencimento,
                    liquidez=liquidez, data_aporte=atual.primeiro_aporte)
    conn.execute(
        "UPDATE rf_posicoes SET tipo = ?, nome = ?, instituicao = ?, corretora = ?, indexador = ?, taxa = ?, "
        "vencimento = ?, liquidez = ?, isento_ir = ?, observacao = ? WHERE id = ?",
        (tipo, _limpo(nome), instituicao.strip(), _limpo(corretora), indexador, _txt(taxa), vencimento or None,
         liquidez, 1 if isento_ir else 0, _limpo(observacao), posicao_id),
    )
    conn.commit()


def delete_posicao(conn: sqlite3.Connection, posicao_id: int) -> None:
    """Apaga a aplicação e todos os seus movimentos (ON DELETE CASCADE)."""
    conn.execute("DELETE FROM rf_posicoes WHERE id = ?", (posicao_id,))
    conn.commit()


def set_valor_atual(conn: sqlite3.Connection, posicao_id: int, valor: Decimal, data: str | None = None) -> None:
    """Informa o valor atual (bruto). 0 marca a aplicação como encerrada (resgate total)."""
    if valor < 0:
        raise ValueError("O valor atual não pode ser negativo.")
    conn.execute(
        "UPDATE rf_posicoes SET valor_atual = ?, data_valor_atual = ? WHERE id = ?",
        (_txt(valor), data or dt.date.today().isoformat(), posicao_id),
    )
    conn.commit()


def get_movimento(conn: sqlite3.Connection, movimento_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM rf_movimentos WHERE id = ?", (movimento_id,)).fetchone()


def add_movimento(
    conn: sqlite3.Connection, posicao_id: int, *, tipo: str, data: str, valor: Decimal,
    custos: Decimal = Decimal(0), nota: str | None = None,
) -> int:
    validar_movimento(tipo=tipo, data=data, valor=valor, custos=custos)
    posicao = get(conn, posicao_id)
    if posicao is None:
        raise ValueError("Aplicação não encontrada.")
    if posicao.primeiro_aporte and data < posicao.primeiro_aporte and tipo == "resgate":
        raise ValueError("O resgate não pode ser anterior ao primeiro aporte.")
    cur = conn.execute(
        "INSERT INTO rf_movimentos (posicao_id, tipo, data, valor, custos, nota) VALUES (?, ?, ?, ?, ?, ?)",
        (posicao_id, tipo, data, _txt(valor), _txt(custos), _limpo(nota)),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_movimento(
    conn: sqlite3.Connection, movimento_id: int, *, data: str, valor: Decimal, custos: Decimal = Decimal(0),
    nota: str | None = None,
) -> None:
    atual = get_movimento(conn, movimento_id)
    if atual is None:
        raise ValueError("Movimento não encontrado.")
    validar_movimento(tipo=atual["tipo"], data=data, valor=valor, custos=custos)
    conn.execute(
        "UPDATE rf_movimentos SET data = ?, valor = ?, custos = ?, nota = ? WHERE id = ?",
        (data, _txt(valor), _txt(custos), _limpo(nota), movimento_id),
    )
    conn.commit()


def delete_movimento(conn: sqlite3.Connection, movimento_id: int) -> None:
    """Recusa apagar o único aporte (a aplicação ficaria sem origem): exclua a aplicação."""
    atual = get_movimento(conn, movimento_id)
    if atual is None:
        return
    if atual["tipo"] == "aporte":
        restantes = conn.execute(
            "SELECT COUNT(*) FROM rf_movimentos WHERE posicao_id = ? AND tipo = 'aporte' AND id <> ?",
            (atual["posicao_id"], movimento_id),
        ).fetchone()[0]
        if restantes == 0:
            raise ValueError("É o único aporte da aplicação. Para removê-lo, exclua a aplicação.")
    conn.execute("DELETE FROM rf_movimentos WHERE id = ?", (movimento_id,))
    conn.commit()
