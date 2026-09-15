"""Avaliação pura dos Objetivos Inteligentes.

Cada função recebe números já calculados (por `core/summary.py` ou pelo
repositório) e devolve um `GoalProgress` — a UI nunca precisa saber a regra
por trás de cada tipo de objetivo, só desenhar a barra de progresso.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoalProgress:
    # unidade depende do tipo de objetivo: centavos para os monetários, meses
    # para saldo_positivo_seguido — por isso os nomes genéricos, não "_cents".
    current: int
    target: int
    achieved: bool
    ratio: float  # 0..1, já capado — pronto para uma barra de progresso


def _ratio(current: int, target: int) -> float:
    if target <= 0:
        return 1.0 if current <= 0 else 0.0
    return min(current / target, 1.0)


def evaluate_teto_categoria(spent_cents: int, target_cents: int) -> GoalProgress:
    """"Manter [categoria] abaixo de R$X" — bate a meta enquanto o gasto não passa do teto."""
    return GoalProgress(spent_cents, target_cents, spent_cents <= target_cents, _ratio(spent_cents, target_cents))


def evaluate_reducao_categoria(spent_this_month_cents: int, spent_last_month_cents: int) -> GoalProgress:
    """"Diminuir gasto com [categoria] em relação ao mês passado" — a "meta" é o valor do mês
    anterior; bater é gastar estritamente menos."""
    achieved = spent_this_month_cents < spent_last_month_cents
    return GoalProgress(
        spent_this_month_cents, spent_last_month_cents, achieved,
        _ratio(spent_this_month_cents, spent_last_month_cents) if spent_last_month_cents > 0 else (0.0 if spent_this_month_cents > 0 else 1.0),
    )


def evaluate_renda_extra(extra_income_cents: int, target_cents: int) -> GoalProgress:
    """"Gerar renda extra fora do salário" — bate ao atingir/passar o valor alvo."""
    return GoalProgress(extra_income_cents, target_cents, extra_income_cents >= target_cents, _ratio(extra_income_cents, target_cents))


def evaluate_saldo_positivo_seguido(current_streak_months: int, target_months: int) -> GoalProgress:
    """"Acumular N meses de saldo positivo" — current_streak_months já vem calculado
    por `consecutive_positive_streak` (core/summary.py)."""
    return GoalProgress(current_streak_months, target_months, current_streak_months >= target_months, _ratio(current_streak_months, target_months))


def overall_streak(monthly_achieved_flags: list[bool]) -> int:
    """Ofensiva geral: meses seguidos (mais recente primeiro) com pelo menos um
    objetivo batido. Para no primeiro mês sem nenhum."""
    streak = 0
    for ok in monthly_achieved_flags:
        if not ok:
            break
        streak += 1
    return streak
