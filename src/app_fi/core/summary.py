"""Agregações puras sobre lançamentos.

Funções sem efeito colateral: recebem linhas (qualquer mapping com as chaves
'kind', 'amount_cents', 'status'), devolvem números. Testáveis sem banco.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class MonthTotals:
    expense_cents: int
    income_cents: int

    @property
    def balance_cents(self) -> int:
        return self.income_cents - self.expense_cents


def month_totals(rows: Iterable[Mapping]) -> MonthTotals:
    """Soma entradas e saídas de um conjunto de lançamentos já filtrado para o mês.

    Lançamentos com status != 'confirmed' (recorrências a confirmar) são
    ignorados — regra da spec: pendentes não entram no saldo.
    """
    expense = income = 0
    for row in rows:
        if row["status"] != "confirmed":
            continue
        if row["kind"] == "expense":
            expense += row["amount_cents"]
        elif row["kind"] == "income":
            income += row["amount_cents"]
    return MonthTotals(expense, income)
