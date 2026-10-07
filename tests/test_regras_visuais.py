"""Regras visuais que a documentação (DESIGN.md) promete e que é fácil quebrar sem perceber."""

import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "app_fi"
ARQUIVOS = [SRC / "main.py", *sorted((SRC / "ui").glob("*.py"))]


def _fabs():
    for arquivo in ARQUIVOS:
        texto = arquivo.read_text(encoding="utf-8")
        for m in re.finditer(r"ft\.FloatingActionButton\(", texto):
            trecho = texto[m.end(): m.end() + 200].split(")\n", 1)[0]
            yield arquivo.name, trecho


def test_existem_botoes_de_criar_para_conferir():
    assert len(list(_fabs())) >= 6   # Finanças, Categorias, Recorrentes, Objetivos, carteira, renda fixa


def test_todo_botao_mais_usa_o_verde_claro_da_marca():
    errados = [nome for nome, trecho in _fabs() if "bgcolor=cores.VERDE_CLARO" not in trecho]
    assert errados == [], f"FAB sem cores.VERDE_CLARO em: {errados}"


def test_telas_nao_hardcodam_hex():
    # as cores moram em ui/cores.py; hex solto nas telas é o que a regra do DESIGN.md proíbe
    achados = []
    for arquivo in ARQUIVOS:
        if arquivo.name == "cores.py":
            continue
        for n, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r'["\']#[0-9A-Fa-f]{6}["\']', linha):
                achados.append(f"{arquivo.name}:{n}")
    assert achados == [], achados
