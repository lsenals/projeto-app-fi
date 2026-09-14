"""Leitura de arquivo de fatura (CSV ou XLSX) para linhas tabulares.

Só abre o arquivo e devolve uma lista de dicts (chave = cabeçalho). Não
interpreta nada do conteúdo — isso é trabalho de `core/c6_import.py`. Datas
de célula do Excel são normalizadas de volta para o texto 'DD/MM/AAAA' que o
CSV usa, para as duas fontes caírem no mesmo formato na saída daqui.
"""

from __future__ import annotations

import csv
import datetime
from pathlib import Path

import openpyxl


def _cell_to_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.strftime("%d/%m/%Y")
    return str(value)


def read_csv(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def read_xlsx(path: str | Path) -> list[dict]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        header = [_cell_to_str(h).strip() for h in next(rows_iter)]
        result = []
        for values in rows_iter:
            if all(v is None for v in values):
                continue
            result.append({
                header[i]: _cell_to_str(v)
                for i, v in enumerate(values) if i < len(header)
            })
        return result
    finally:
        wb.close()


def read_statement(path: str | Path) -> list[dict]:
    """Escolhe o leitor certo pela extensão."""
    if Path(path).suffix.lower() == ".xlsx":
        return read_xlsx(path)
    return read_csv(path)
