import datetime as dt
from decimal import Decimal as D

import pytest

from app_fi.core.renda_fixa import (
    TIPOS, aliquota_ir, classe_da_taxa, descrever_rentabilidade, faixa_do_ir, montar_carteira_rf,
    proxima_faixa, tipo_por_chave, validar_movimento, validar_posicao,
)
from app_fi.data import renda_fixa_repo as repo
from app_fi.data.db import get_db

HOJE = dt.date(2026, 10, 7)


@pytest.fixture
def conn(tmp_path):
    return get_db(tmp_path / "t.db")


def _nova(conn, **kw):
    base = dict(tipo="CDB", nome="CDB Banco X 2028", instituicao="Banco X", corretora="Corretora Y",
                indexador="CDI", taxa=D("110"), vencimento="2028-01-10", liquidez="vencimento", isento_ir=False,
                observacao=None, data_aporte="2026-01-10", valor_aporte=D(10000))
    return repo.add_posicao(conn, **{**base, **kw})


# -------------------------------------------------------------- tabela de IR

@pytest.mark.parametrize("dias,esperado", [
    (0, "22.5"), (1, "22.5"), (180, "22.5"), (181, "20"), (360, "20"), (361, "17.5"), (720, "17.5"),
    (721, "15"), (5000, "15"),
])
def test_aliquota_regressiva_nos_limites(dias, esperado):
    assert aliquota_ir(dias) == D(esperado)


def test_faixa_em_texto():
    assert [faixa_do_ir(d) for d in (10, 180, 181, 361, 721)] == [
        "até 180 dias", "até 180 dias", "181 a 360 dias", "361 a 720 dias", "acima de 720 dias",
    ]


@pytest.mark.parametrize("dias,esperado", [
    (0, (181, D("20"))), (100, (81, D("20"))), (180, (1, D("20"))), (181, (180, D("17.5"))),
    (360, (1, D("17.5"))), (361, (360, D("15"))), (720, (1, D("15"))), (721, None), (900, None),
])
def test_proxima_faixa(dias, esperado):
    assert proxima_faixa(dias) == esperado


# ---------------------------------------------------------------- catálogo

def test_catalogo_cobre_os_principais_titulos():
    chaves = {t.chave for t in TIPOS}
    assert {"TESOURO_SELIC", "TESOURO_PREFIXADO", "TESOURO_IPCA", "CDB", "LCI", "LCA", "LC", "CRI", "CRA",
            "DEBENTURE", "POUPANCA", "OUTRO"} <= chaves
    assert len(chaves) == len(TIPOS)  # sem chaves repetidas


def test_isencao_e_fgc_do_catalogo():
    assert tipo_por_chave("LCI").isento_ir and tipo_por_chave("LCA").isento_ir and tipo_por_chave("CRI").isento_ir
    assert not tipo_por_chave("CDB").isento_ir and tipo_por_chave("CDB").fgc
    assert not tipo_por_chave("TESOURO_SELIC").fgc and not tipo_por_chave("CRI").fgc


def test_tipo_desconhecido():
    with pytest.raises(ValueError):
        tipo_por_chave("XPTO")


def test_pre_ou_pos():
    assert classe_da_taxa("PRE") == "Pré-fixado"
    assert {classe_da_taxa(i) for i in ("CDI", "CDI_MAIS", "SELIC")} == {"Pós-fixado"}
    assert classe_da_taxa("IPCA") == "Híbrido (IPCA+)"


@pytest.mark.parametrize("indexador,taxa,texto", [
    ("PRE", D("12.5"), "12,50% a.a."), ("CDI", D("110"), "110,00% do CDI"), ("CDI_MAIS", D("2"), "CDI + 2,00% a.a."),
    ("SELIC", D("0.1"), "Selic + 0,10% a.a."), ("IPCA", D("6.2"), "IPCA + 6,20% a.a."), ("PRE", None, "taxa não informada"),
])
def test_descricao_da_rentabilidade(indexador, taxa, texto):
    assert descrever_rentabilidade(indexador, taxa) == texto


# ---------------------------------------------------------- posição e prazos

def test_contador_de_dias_desde_o_primeiro_aporte(conn):
    pid = _nova(conn)
    repo.add_movimento(conn, pid, tipo="aporte", data="2026-06-10", valor=D(5000))
    p = repo.get(conn, pid, HOJE)
    assert p.primeiro_aporte == "2026-01-10"          # o mais antigo, não o último
    assert p.dias_desde_primeiro_aporte == 270
    assert p.aliquota_atual == D("20")
    faltam, nova, quando = p.proxima_reducao
    assert (faltam, nova, quando) == (91, D("17.5"), "2027-01-06")   # 361 - 270 dias


def test_isento_nao_tem_aliquota_nem_proxima_reducao(conn):
    p = repo.get(conn, _nova(conn, tipo="LCI", isento_ir=True), HOJE)
    assert p.aliquota_atual == D(0) and p.proxima_reducao is None and p.ir_estimado == D(0)


def test_ultima_faixa_nao_tem_proxima_reducao(conn):
    p = repo.get(conn, _nova(conn, data_aporte="2024-01-01"), HOJE)
    assert p.aliquota_atual == D("15") and p.proxima_reducao is None


def test_vencimento_e_progresso_do_prazo(conn):
    p = repo.get(conn, _nova(conn, vencimento="2026-11-06"), HOJE)   # aporte 10/01 -> venc 06/11
    assert p.dias_para_vencimento == 30 and not p.vencida
    assert p.progresso_do_prazo == pytest.approx(270 / 300)
    vencida = repo.get(conn, _nova(conn, nome="velha", vencimento="2026-10-01", data_aporte="2026-01-10"), HOJE)
    assert vencida.vencida and vencida.dias_para_vencimento == -6


def test_sem_vencimento(conn):
    p = repo.get(conn, _nova(conn, vencimento=None), HOJE)
    assert p.dias_para_vencimento is None and p.progresso_do_prazo is None and not p.vencida


# ------------------------------------------------------------- rendimento/IR

def test_rendimento_e_ir_estimado_numa_faixa(conn):
    pid = _nova(conn)                                    # 10.000 há 270 dias -> faixa de 20%
    repo.set_valor_atual(conn, pid, D(10800), "2026-10-07")
    p = repo.get(conn, pid, HOJE)
    assert p.rendimento_bruto == D(800)
    assert p.rentabilidade_pct == D(8)
    assert p.ir_estimado == D(160)                       # 20% de 800
    assert p.liquido_estimado == D(10640)


def test_ir_com_aportes_em_faixas_diferentes(conn):
    pid = _nova(conn, data_aporte="2025-01-01")          # 9/10/26: 644 dias -> 17,5%
    repo.add_movimento(conn, pid, tipo="aporte", data="2026-09-07", valor=D(10000))   # 30 dias -> 22,5%
    repo.set_valor_atual(conn, pid, D(21000))
    p = repo.get(conn, pid, HOJE)
    # rendimento 1000, metade em cada aporte: 500*17,5% + 500*22,5%
    assert p.rendimento_bruto == D(1000) and p.ir_estimado == D(200)


def test_sem_rendimento_nao_ha_ir(conn):
    pid = _nova(conn)
    repo.set_valor_atual(conn, pid, D(9900))             # perdeu valor (marcação a mercado)
    p = repo.get(conn, pid, HOJE)
    assert p.rendimento_bruto == D(-100) and p.ir_estimado == D(0) and p.liquido_estimado == D(9900)


def test_sem_valor_atual_usa_o_valor_aplicado_e_sinaliza(conn):
    p = repo.get(conn, _nova(conn), HOJE)
    assert p.sem_valor_atual and p.valor_efetivo == D(10000) and p.rendimento_bruto == D(0)


def test_resgate_parcial_entra_no_rendimento_e_o_ir_retido_abate(conn):
    pid = _nova(conn)
    repo.add_movimento(conn, pid, tipo="resgate", data="2026-08-10", valor=D(4000), custos=D(30))
    repo.set_valor_atual(conn, pid, D(6500))
    p = repo.get(conn, pid, HOJE)
    assert p.resgatado_bruto == D(4000) and p.custos_resgates == D(30)
    assert p.rendimento_bruto == D(500)                  # 6500 + 4000 - 10000
    assert p.ir_estimado == D(70)                        # 20% de 500 = 100, menos 30 já retidos


def test_resgate_total_encerra(conn):
    pid = _nova(conn)
    repo.set_valor_atual(conn, pid, D(0))
    assert repo.get(conn, pid, HOJE).encerrada


# ----------------------------------------------------------------- resumo

def test_resumo_separa_ativas_de_encerradas(conn):
    a = _nova(conn); repo.set_valor_atual(conn, a, D(10800))
    b = _nova(conn, nome="outra", valor_aporte=D(2000), data_aporte="2025-01-01", vencimento="2027-01-01")
    repo.set_valor_atual(conn, b, D(2300))
    c = _nova(conn, nome="resgatada", valor_aporte=D(1000)); repo.set_valor_atual(conn, c, D(0))
    repo.add_movimento(conn, c, tipo="resgate", data="2026-05-10", valor=D(1100))
    r = repo.load(conn, HOJE).resumo
    assert (r.ativas, r.encerradas) == (2, 1)
    assert r.aplicado == D(12000) and r.valor_atual == D(13100)
    assert r.rendimento_bruto == D(800) + D(300) + D(100)      # inclui a encerrada
    assert r.rentabilidade_pct == D(1100) / D(12000) * 100
    assert r.sem_valor_atual == 0


def test_ordem_ativas_primeiro_e_vencimento_mais_proximo(conn):
    longa = _nova(conn, nome="longa", vencimento="2030-01-01")
    curta = _nova(conn, nome="curta", vencimento="2027-01-01")
    morta = _nova(conn, nome="morta"); repo.set_valor_atual(conn, morta, D(0))
    assert [p.nome for p in repo.load(conn, HOJE).posicoes] == ["curta", "longa", "morta"]


# ---------------------------------------------------------------- validações

@pytest.mark.parametrize("campos", [
    dict(instituicao="  "), dict(tipo="XPTO"), dict(indexador="XYZ"), dict(liquidez="xyz"),
    dict(taxa=None), dict(taxa=D(-1)), dict(vencimento="31/12/2030"), dict(vencimento="2025-01-01"),
    dict(valor_aporte=D(0)), dict(data_aporte="10/01/2026"),
])
def test_validacoes_ao_criar(conn, campos):
    with pytest.raises(ValueError):
        _nova(conn, **campos)
    assert repo.load(conn, HOJE).posicoes == ()


def test_indexador_outro_nao_exige_taxa(conn):
    assert repo.get(conn, _nova(conn, tipo="POUPANCA", indexador="OUTRO", taxa=None, vencimento=None), HOJE)


def test_validar_movimento():
    for ruim in (dict(tipo="x"), dict(data="2026-13-01"), dict(valor=D(0)), dict(custos=D(-1))):
        with pytest.raises(ValueError):
            validar_movimento(**{**dict(tipo="aporte", data="2026-01-01", valor=D(1), custos=D(0)), **ruim})


def test_validar_posicao_direto():
    with pytest.raises(ValueError, match="instituição"):
        validar_posicao(tipo="CDB", instituicao="", indexador="PRE", taxa=D(1), vencimento=None, liquidez="diaria")


# --------------------------------------------------------------- persistência

def test_resgate_anterior_ao_primeiro_aporte_e_recusado(conn):
    pid = _nova(conn)
    with pytest.raises(ValueError, match="anterior ao primeiro aporte"):
        repo.add_movimento(conn, pid, tipo="resgate", data="2025-12-31", valor=D(100))


def test_nao_apaga_o_unico_aporte_mas_apaga_um_de_varios(conn):
    pid = _nova(conn)
    unico = repo.get(conn, pid).aportes[0].id
    with pytest.raises(ValueError, match="único aporte"):
        repo.delete_movimento(conn, unico)
    extra = repo.add_movimento(conn, pid, tipo="aporte", data="2026-03-01", valor=D(500))
    repo.delete_movimento(conn, extra)
    assert len(repo.get(conn, pid).aportes) == 1
    repo.delete_movimento(conn, 999999)   # inexistente: silencioso


def test_editar_movimento_e_posicao(conn):
    pid = _nova(conn)
    mov = repo.get(conn, pid).aportes[0].id
    repo.update_movimento(conn, mov, data="2026-02-01", valor=D(12000), custos=D(10), nota="ajuste")
    repo.update_posicao(conn, pid, tipo="LCI", nome=" LCI nova ", instituicao="Banco Z", corretora="",
                        indexador="PRE", taxa=D("11.5"), vencimento="2029-01-01", liquidez="carencia",
                        isento_ir=True, observacao="obs")
    p = repo.get(conn, pid, HOJE)
    assert (p.tipo.chave, p.nome, p.instituicao, p.corretora, p.isento_ir) == ("LCI", "LCI nova", "Banco Z", None, True)
    assert p.primeiro_aporte == "2026-02-01" and p.aportado == D(12010)   # valor + custos do aporte


def test_excluir_aplicacao_apaga_os_movimentos(conn):
    pid = _nova(conn)
    repo.add_movimento(conn, pid, tipo="aporte", data="2026-03-01", valor=D(500))
    repo.delete_posicao(conn, pid)
    assert conn.execute("SELECT COUNT(*) FROM rf_movimentos").fetchone()[0] == 0
    assert repo.get(conn, pid) is None


def test_valor_atual_negativo_e_recusado(conn):
    with pytest.raises(ValueError):
        repo.set_valor_atual(conn, _nova(conn), D(-1))


def test_carteira_vazia():
    c = montar_carteira_rf([], [], HOJE)
    assert c.posicoes == () and c.resumo.aplicado == 0 and c.resumo.rentabilidade_pct is None
