"""Escrita em disco de relatórios e backup — a única parte de `report/` que
toca arquivo. Tudo local: `%LOCALAPPDATA%\\app-fi\\relatorios` e `...\\backups`
(ou `APP_FI_DATA_DIR` quando definida, mesma regra do banco)."""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from app_fi.data.db import default_db_path


def _app_dir() -> Path:
    return default_db_path().parent


def reports_dir() -> Path:
    d = _app_dir() / "relatorios"
    d.mkdir(parents=True, exist_ok=True)
    return d


def backups_dir() -> Path:
    d = _app_dir() / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_html_report(html: str, ano: int, mes: int) -> Path:
    path = reports_dir() / f"relatorio-{ano:04d}-{mes:02d}.html"
    path.write_text(html, encoding="utf-8")
    return path


def write_csv_report(csv_text: str, ano: int, mes: int) -> Path:
    # utf-8-sig: o BOM faz o Excel abrir acentuação corretamente
    path = reports_dir() / f"lancamentos-{ano:04d}-{mes:02d}.csv"
    path.write_text(csv_text, encoding="utf-8-sig")
    return path


def backup_database() -> Path:
    """Copia o arquivo do banco atual para backups/ com timestamp no nome.

    O banco roda em modo WAL: dados recentes podem estar só no arquivo
    auxiliar `-wal`, não no `.sqlite` principal. Sem o checkpoint abaixo,
    copiar direto arrisca um backup sem os últimos lançamentos.
    """
    db_path = default_db_path()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest = backups_dir() / f"app-fi-{stamp}.sqlite"
    shutil.copy2(db_path, dest)
    return dest
