import sqlite3

import pytest

from app_fi.data import backup
from app_fi.data.db import get_db


@pytest.fixture()
def app_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_FI_DATA_DIR", str(tmp_path))
    get_db()  # garante que o banco existe em tmp_path antes do backup
    return tmp_path


def test_write_html_report_creates_file(app_dir):
    path = backup.write_html_report("<html>oi</html>", 2026, 9)
    assert path.exists()
    assert path.name == "relatorio-2026-09.html"
    assert path.parent == app_dir / "relatorios"
    assert path.read_text(encoding="utf-8") == "<html>oi</html>"


def test_write_csv_report_creates_file_with_bom(app_dir):
    path = backup.write_csv_report("Data;Tipo\n2026-09-01;Despesa\n", 2026, 9)
    assert path.exists()
    assert path.name == "lancamentos-2026-09.csv"
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM utf-8-sig


def test_backup_database_copies_real_sqlite_file(app_dir):
    dest = backup.backup_database()
    assert dest.exists()
    assert dest.parent == app_dir / "backups"
    assert dest.suffix == ".sqlite"

    # o arquivo copiado tem que ser um banco válido com o schema aplicado
    conn = sqlite3.connect(dest)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "transactions" in tables
    conn.close()


def test_backup_database_filename_has_timestamp(app_dir):
    dest = backup.backup_database()
    assert dest.name.startswith("app-fi-")
    # app-fi-YYYY-MM-DD_HHMMSS.sqlite
    stamp = dest.stem.removeprefix("app-fi-")
    assert len(stamp) == len("2026-09-14_153000")
