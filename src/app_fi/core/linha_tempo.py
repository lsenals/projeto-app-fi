"""Linha do tempo do mês — função pura, sem banco nem UI.

Cada lançamento confirmado do mês vira um evento no dia em que ocorreu (despesas, receitas e
recorrentes já gerados). A tela desenha uma bolinha por dia e por tipo (despesa/receita), com tamanho
proporcional ao total do dia: os maiores círculos mostram onde o dinheiro se concentra e `pico_dia`
aponta o dia de maior gasto. Os eventos individuais ficam para o detalhe do dia.
"""

from __future__ import annotations

import calendar
import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Evento:
    id: int | None
    dia: int
    tipo: str  # "income" | "expense"
    valor_cents: int
    recorrente: bool
    descricao: str  # "Categoria · Favorecido", já pronta para exibir


@dataclass(frozen=True)
class LinhaTempo:
    ano: int
    mes: int
    dias_no_mes: int
    dia_hoje: int | None  # None quando o mês exibido não é o de hoje
    eventos_por_dia: tuple[tuple[Evento, ...], ...]  # índice 0 = dia 1
    pico_dia: int | None  # dia com mais gasto no mês (None sem despesas)
    pico_cents: int
    maior_total_cents: int  # maior total diário (de um tipo): escala o tamanho das bolinhas

    def eventos_do_dia(self, dia: int) -> tuple[Evento, ...]:
        return self.eventos_por_dia[dia - 1]

    def total_do_dia(self, dia: int, tipo: str) -> int:
        return sum(e.valor_cents for e in self.eventos_do_dia(dia) if e.tipo == tipo)


def _campo(r: Mapping, chave: str):
    """Campo opcional: aceita dict e sqlite3.Row, com ou sem a coluna."""
    return r[chave] if chave in r.keys() else None


def _descricao(r: Mapping) -> str:
    """Categoria (ou fonte de renda) e favorecido, quando existem."""
    if r["kind"] == "income":
        base = _campo(r, "income_source_name")
    else:
        base = _campo(r, "category_name") or "Sem categoria"
    partes = [p for p in (base, _campo(r, "payee_name")) if p]
    return " · ".join(partes) if partes else "—"


def montar_linha_tempo(rows: Iterable[Mapping], ano: int, mes: int, hoje: dt.date) -> LinhaTempo:
    """Linha do mês `mes`/`ano` (o que a tela está mostrando). `rows` pode trazer outros meses: só
    entram os desse mês. `hoje` só serve para marcar o dia atual, quando ele cai neste mês."""
    dias_no_mes = calendar.monthrange(ano, mes)[1]
    dias: list[list[Evento]] = [[] for _ in range(dias_no_mes)]
    for r in rows:
        if r["status"] != "confirmed" or r["kind"] not in ("income", "expense"):
            continue
        data = dt.date.fromisoformat(r["date"])
        if (data.year, data.month) != (ano, mes):
            continue
        dias[data.day - 1].append(Evento(
            id=_campo(r, "id"), dia=data.day, tipo=r["kind"], valor_cents=r["amount_cents"],
            recorrente=_campo(r, "recurring_id") is not None, descricao=_descricao(r),
        ))
    por_dia = tuple(tuple(sorted(d, key=lambda e: -e.valor_cents)) for d in dias)

    pico_dia, pico_cents = None, 0
    maior_total = 0
    for i, eventos in enumerate(por_dia, start=1):
        gasto = sum(e.valor_cents for e in eventos if e.tipo == "expense")
        entrada = sum(e.valor_cents for e in eventos if e.tipo == "income")
        maior_total = max(maior_total, gasto, entrada)
        if gasto > pico_cents:
            pico_dia, pico_cents = i, gasto
    no_mes = (hoje.year, hoje.month) == (ano, mes)
    return LinhaTempo(
        ano=ano, mes=mes, dias_no_mes=dias_no_mes, dia_hoje=hoje.day if no_mes else None,
        eventos_por_dia=por_dia, pico_dia=pico_dia, pico_cents=pico_cents, maior_total_cents=maior_total,
    )