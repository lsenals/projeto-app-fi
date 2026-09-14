"""CSV dos lançamentos do mês — texto puro, sem tocar em arquivo.
`;` como separador porque é o padrão do Excel em pt-BR."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping

from app_fi.core.money import format_brl

_HEADER = ["Data", "Tipo", "Categoria/Origem", "Valor (R$)", "Status"]


def render_csv(rows: Iterable[Mapping]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(_HEADER)
    for r in rows:
        receita = r["kind"] == "income"
        nome = (r["income_source_name"] if receita else r["category_name"]) or (
            "" if receita else "Sem categoria"
        )
        writer.writerow([
            r["date"],
            "Receita" if receita else "Despesa",
            nome,
            format_brl(r["amount_cents"]),
            "Confirmado" if r["status"] == "confirmed" else "A confirmar",
        ])
    return buf.getvalue()
