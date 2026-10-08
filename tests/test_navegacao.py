import re
from pathlib import Path

import pytest

from app_fi.ui.navegacao import PAI_DA_TELA, pai_de

MAIN = Path(__file__).resolve().parent.parent / "src" / "app_fi" / "main.py"


def test_so_o_hub_e_raiz():
    assert [t for t, pai in PAI_DA_TELA.items() if pai is None] == ["hub"]


@pytest.mark.parametrize("tela", sorted(PAI_DA_TELA))
def test_toda_tela_chega_ao_hub_sem_ciclo(tela):
    vistas = []
    while tela is not None:
        assert tela not in vistas, f"ciclo de navegação: {vistas + [tela]}"
        vistas.append(tela)
        tela = pai_de(tela)
    assert vistas[-1] == "hub"


def test_o_pai_de_toda_tela_existe():
    assert all(pai is None or pai in PAI_DA_TELA for pai in PAI_DA_TELA.values())


def test_telas_do_menu_lateral_voltam_ao_hub():
    for tela in ("categorias", "recorrentes", "config"):
        assert pai_de(tela) == "hub"


def test_cripto_volta_para_investimentos_e_lancamento_para_financas():
    assert pai_de("cripto") == "investimentos"
    assert pai_de("lancamento") == "financas"


def test_tela_desconhecida_e_erro_explicito():
    with pytest.raises(KeyError):
        pai_de("nao-existe")


def test_main_registra_todas_as_telas_do_mapa():
    # cada nome do mapa precisa ser registrado em main.py (senão o voltar dessa tela cai no hub sem querer)
    registradas = set(re.findall(r'_registrando_tela\("(\w+)"', MAIN.read_text(encoding="utf-8")))
    assert registradas == set(PAI_DA_TELA)

def test_home_navega_por_callbacks_registrados_e_nao_pelas_funcoes_locais():
    """O botão voltar do Android usa a "tela atual" gravada pelos montar_* registrados em main.py.
    Se home.py chamar as suas próprias montar_hub/montar_investimentos, a tela atual não muda e o
    voltar fecha o app (bug visto no aparelho em Investimentos)."""
    home = (MAIN.parent / "ui" / "home.py").read_text(encoding="utf-8")
    assert not re.search(r"lambda e: montar_(hub|investimentos)\(\)", home)
