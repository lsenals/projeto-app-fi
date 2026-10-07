"""Números do Painel de Finanças da Home — função pura, sem banco nem UI.

Tudo é derivado dos lançamentos confirmados e dos objetivos do mês (mesma
filosofia do resto do app: nada de contador guardado à parte).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

DIAS_SEMANA = 7


@dataclass(frozen=True)
class Anel:
    rotulo: str
    percentual: int  # 0..100


@dataclass(frozen=True)
class PainelFinancas:
    aneis: tuple[Anel, Anel]
    saldo_semana_cents: int
    saldo_semana_ratio: float  # 0..1 — fatia da renda dos últimos 7 dias que sobrou
    poupanca_mes_cents: int
    poupanca_mes_ratio: float  # 0..1 — fatia da renda do mês que sobrou


def _ratio(parte_cents: int, total_cents: int) -> float:
    """parte/total limitado a 0..1; 0 quando não há total (sem renda, sem divisão por zero)."""
    if total_cents <= 0:
        return 0.0
    return max(0.0, min(1.0, parte_cents / total_cents))


def _somar(rows: Iterable[Mapping], inicio: dt.date, fim: dt.date) -> tuple[int, int]:
    """(entradas, saídas) confirmadas com data em [inicio, fim]."""
    entradas = saidas = 0
    for r in rows:
        if r["status"] != "confirmed":
            continue
        if not inicio <= dt.date.fromisoformat(r["date"]) <= fim:
            continue
        if r["kind"] == "income":
            entradas += r["amount_cents"]
        elif r["kind"] == "expense":
            saidas += r["amount_cents"]
    return entradas, saidas


def calcular_painel(
    rows: Iterable[Mapping],
    hoje: dt.date,
    objetivos_batidos: int,
    objetivos_total: int,
) -> PainelFinancas:
    """`rows` deve cobrir pelo menos o mês de `hoje` e os 6 dias anteriores
    (basta passar o mês atual e o anterior)."""
    rows = list(rows)
    primeiro_dia = hoje.replace(day=1)

    entradas_mes, saidas_mes = _somar(rows, primeiro_dia, hoje)
    entradas_sem, saidas_sem = _somar(rows, hoje - dt.timedelta(days=DIAS_SEMANA - 1), hoje)
    saldo_mes = entradas_mes - saidas_mes
    saldo_sem = entradas_sem - saidas_sem

    return PainelFinancas(
        aneis=(
            Anel("Objetivos", round(_ratio(objetivos_batidos, objetivos_total) * 100)),
            Anel("Gasto/renda", round(_ratio(saidas_mes, entradas_mes) * 100)),
        ),
        saldo_semana_cents=saldo_sem,
        saldo_semana_ratio=_ratio(saldo_sem, entradas_sem),
        poupanca_mes_cents=saldo_mes,
        poupanca_mes_ratio=_ratio(saldo_mes, entradas_mes),
    )
