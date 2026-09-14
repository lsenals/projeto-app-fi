"""Previsão de término de uma recorrência com número fixo de parcelas.

Pura: só aritmética de data a partir de `next_date` (a próxima cobrança),
`current_installment` (qual parcela essa próxima cobrança representa) e
`total_installments` (quantas no total). Recorrências sem `total_installments`
(assinatura, conta de consumo) não têm previsão — e está certo não ter,
não é um caso não tratado.
"""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class RecurringForecast:
    remaining_installments: int | None   # None = sem fim definido
    predicted_end_date: str | None       # ISO yyyy-mm-dd; None = sem fim definido


def _add_months(date_iso: str, months: int) -> str:
    y, m, d = (int(p) for p in date_iso.split("-"))
    total = (y * 12 + (m - 1)) + months
    y2, m2 = divmod(total, 12)
    m2 += 1
    last_day = calendar.monthrange(y2, m2)[1]
    return f"{y2:04d}-{m2:02d}-{min(d, last_day):02d}"


def _add_weeks(date_iso: str, weeks: int) -> str:
    y, m, d = (int(p) for p in date_iso.split("-"))
    return (dt.date(y, m, d) + dt.timedelta(weeks=weeks)).isoformat()


def forecast(
    next_date: str,
    interval_unit: str,
    interval_count: int,
    total_installments: int | None,
    current_installment: int,
) -> RecurringForecast:
    """`next_date` é a data da próxima cobrança, que representa a parcela
    `current_installment` (1 = ainda não cobrou nenhuma vez). Sem
    `total_installments`, devolve "sem fim definido"."""
    if total_installments is None:
        return RecurringForecast(None, None)

    remaining = total_installments - current_installment + 1
    if remaining <= 0:
        return RecurringForecast(0, next_date)

    steps = interval_count * (remaining - 1)
    if interval_unit == "month":
        end_date = _add_months(next_date, steps)
    elif interval_unit == "week":
        end_date = _add_weeks(next_date, steps)
    else:
        raise ValueError(f"Unidade de intervalo desconhecida: {interval_unit!r}")

    return RecurringForecast(remaining, end_date)
