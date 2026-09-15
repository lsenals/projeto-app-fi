"""Resolução do caminho de dados — importa pra mobile (Android/iOS não tem
%LOCALAPPDATA%; um app empacotado via `flet build` expõe FLET_APP_STORAGE_DATA
no lugar)."""

from app_fi.data.db import DB_FILENAME, default_db_path


def test_app_fi_data_dir_tem_prioridade_sobre_tudo(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_FI_DATA_DIR", str(tmp_path / "override"))
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path / "flet"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))

    path = default_db_path()

    assert path == tmp_path / "override" / DB_FILENAME
    assert path.parent.exists()


def test_flet_app_storage_data_usado_quando_sem_override(tmp_path, monkeypatch):
    monkeypatch.delenv("APP_FI_DATA_DIR", raising=False)
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path / "flet"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))

    path = default_db_path()

    assert path == tmp_path / "flet" / DB_FILENAME
    assert path.parent.exists()


def test_fallback_localappdata_quando_nenhuma_variavel_de_empacotamento(tmp_path, monkeypatch):
    monkeypatch.delenv("APP_FI_DATA_DIR", raising=False)
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))

    path = default_db_path()

    assert path == tmp_path / "localappdata" / "app-fi" / DB_FILENAME
    assert path.parent.exists()
