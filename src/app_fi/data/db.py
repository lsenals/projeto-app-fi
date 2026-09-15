"""Conexão SQLite e runner de migrations.

Uso normal:

    from app_fi.data.db import get_db
    conn = get_db()          # abre o banco padrão e aplica migrations pendentes

Nos testes, passe um caminho:

    conn = get_db(tmp_path / "test.db")

O caminho do banco pode ser sobrescrito pela variável de ambiente
``APP_FI_DATA_DIR`` (usada nos testes e para rodar contra um banco descartável).
"""

# Nota mobile: em Android/iOS não existe %LOCALAPPDATA%. Um app empacotado via
# `flet build` expõe o diretório de dados correto (sandbox do app) na variável
# de ambiente `FLET_APP_STORAGE_DATA`, sincronamente — sem precisar de
# `ft.StoragePaths` (que é assíncrono e depende de uma `page` já rodando).

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

APP_DIR_NAME = "app-fi"
DB_FILENAME = "app-fi.db"

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def default_db_path() -> Path:
    """Resolve o caminho do banco e garante que a pasta exista.

    Ordem: ``APP_FI_DATA_DIR`` (se definida, usada nos testes) ->
    ``FLET_APP_STORAGE_DATA`` (definida automaticamente pelo Flet num app
    empacotado — Android/iOS/macOS/Linux) -> ``%LOCALAPPDATA%\\app-fi`` como
    fallback do modo desenvolvimento no Windows (`python src/app_fi/main.py`
    direto, sem empacotar, onde nenhuma das duas variáveis acima existe).
    """
    override = os.environ.get("APP_FI_DATA_DIR")
    if override:
        root = Path(override)
    else:
        storage_data = os.environ.get("FLET_APP_STORAGE_DATA")
        if storage_data:
            root = Path(storage_data)
        else:
            local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
            root = Path(local) / APP_DIR_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root / DB_FILENAME


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Abre uma conexão com row_factory=Row e as PRAGMAs do projeto.

    Não aplica migrations — use :func:`get_db` para isso.
    """
    path = str(db_path) if db_path is not None else str(default_db_path())
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _discover_migrations() -> list[Path]:
    """Arquivos ``NNN_*.sql`` da pasta migrations, em ordem numérica."""
    return sorted(_MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Aplica as migrations ainda não registradas. Retorna as versões aplicadas nesta chamada.

    Cada arquivo roda como um script; a versão só é gravada se o script inteiro
    passou. Se uma migration falhar no meio, corrija o ``.sql`` — em
    desenvolvimento, apagar o banco e recriar é aceitável.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version TEXT PRIMARY KEY,"
        " applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    applied = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}

    ran: list[str] = []
    for path in _discover_migrations():
        version = path.stem
        if version in applied:
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        ran.append(version)
    return ran


def get_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Abre o banco e garante o schema atualizado."""
    conn = connect(db_path)
    migrate(conn)
    return conn
