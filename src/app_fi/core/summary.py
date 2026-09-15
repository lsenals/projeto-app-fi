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


def _group(rows: Iterable[Mapping], kind: str, name_key: str, fallback: str) -> list[tuple[str, int]]:
    totals: dict[str, int] = {}
    for row in rows:
        if row["status"] != "confirmed" or row["kind"] != kind:
            continue
        nome = row[name_key] or fallback
        totals[nome] = totals.get(nome, 0) + row["amount_cents"]
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)


def category_breakdown(rows: Iterable[Mapping]) -> list[tuple[str, int]]:
    """Despesas confirmadas somadas por categoria, maior primeiro.
    Sem categoria entra como sua própria linha ("Sem categoria")."""
    return _group(rows, "expense", "category_name", "Sem categoria")


def income_by_source(rows: Iterable[Mapping]) -> list[tuple[str, int]]:
    """Receitas confirmadas somadas por origem, maior primeiro."""
    return _group(rows, "income", "income_source_name", "Outros")


@dataclass(frozen=True)
class ComparisonRow:
    category: str
    current_cents: int
    previous_cents: int

    @property
    def delta_pct(self) -> float | None:
        """None quando o mês anterior não teve gasto nessa categoria (variação
        percentual não faz sentido dividindo por zero)."""
        if self.previous_cents == 0:
            return None
        return (self.current_cents - self.previous_cents) / self.previous_cents * 100


def month_over_month(
    current_rows: Iterable[Mapping], previous_rows: Iterable[Mapping],
) -> list[ComparisonRow]:
    """Compara despesas por categoria entre dois meses. Categorias que só
    aparecem num dos dois lados entram com 0 do outro. Ordenado pelo gasto do
    mês atual, maior primeiro — reconhece quedas tanto quanto aumentos."""
    atual = dict(category_breakdown(current_rows))
    anterior = dict(category_breakdown(previous_rows))
    linhas = [
        ComparisonRow(cat, atual.get(cat, 0), anterior.get(cat, 0))
        for cat in set(atual) | set(anterior)
    ]
    linhas.sort(key=lambda r: r.current_cents, reverse=True)
    return linhas


def consecutive_positive_streak(monthly_balances_cents: list[int]) -> int:
    """`monthly_balances_cents` do mês mais recente pro mais antigo. Conta quantos
    meses seguidos, a partir do primeiro, tiveram saldo positivo (> 0)."""
    streak = 0
    for saldo in monthly_balances_cents:
        if saldo <= 0:
            break
        streak += 1
    return streak
