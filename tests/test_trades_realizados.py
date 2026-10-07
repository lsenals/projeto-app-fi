from decimal import Decimal as D

import pytest

from app_fi.core.trades import resumir_trades, validar_trade
from app_fi.data import trades_realizados_repo as repo
from app_fi.data.db import get_db


@pytest.fixture
def conn(tmp_path):
    return get_db(tmp_path / "t.db")


def _novo(conn, **kw):
    base = dict(modulo="cripto", simbolo="ada", data_compra="2026-01-10", valor_compra=D(1000),
                data_venda="2026-02-10", valor_venda=D(1300), custos=D(10))
    return repo.add_trade(conn, **{**base, **kw})


# ---------------------------------------------------------------- cálculo

def test_lucro_dias_e_percentual(conn):
    t = repo.get_trade(conn, _novo(conn))
    assert t.lucro == D(290)            # 1300 - 1000 - 10
    assert t.lucro_pct == D(29)         # sobre o valor de compra
    assert t.dias == 31
    assert t.simbolo == "ADA"           # normaliza para maiúsculas


def test_trade_com_prejuizo(conn):
    t = repo.get_trade(conn, _novo(conn, valor_venda=D(800), custos=D(0)))
    assert t.lucro == D(-200) and t.lucro_pct == D(-20)


def test_resumo_basico(conn):
    _novo(conn)                                                          # +290
    _novo(conn, simbolo="btc", valor_venda=D(900), custos=D(0))          # -100
    _novo(conn, simbolo="eth", valor_venda=D(1000), custos=D(0))         # 0 (nem vitória nem derrota)
    r = resumir_trades(repo.list_trades(conn, "cripto"))
    assert (r.total, r.vitorias, r.derrotas) == (3, 1, 1)
    assert r.lucro_total == D(190) and r.custos_total == D(10) and r.investido_total == D(3000)
    assert r.taxa_acerto == D(1) / 3 * 100
    assert r.melhor.simbolo == "ADA" and r.pior.simbolo == "BTC"


def test_resumo_vazio():
    r = resumir_trades([])
    assert r.total == 0 and r.lucro_pct is None and r.taxa_acerto is None and r.melhor is None


def test_resumo_converte_moedas(conn):
    _novo(conn)                                                                         # +290 BRL
    _novo(conn, simbolo="eth", moeda="USD", valor_compra=D(100), valor_venda=D(150), custos=D(0))  # +50 USD
    trades = repo.list_trades(conn, "cripto")
    em_brl = resumir_trades(trades, "BRL", D(5))
    assert em_brl.lucro_total == D(290) + D(250)
    em_usd = resumir_trades(trades, "USD", D(5))
    assert em_usd.lucro_total == D(58) + D(50)           # 290/5 + 50
    sem = resumir_trades(trades, "BRL", None)
    assert sem.sem_cotacao == 1 and sem.total == 1 and sem.lucro_total == D(290)


# -------------------------------------------------------------- validação

@pytest.mark.parametrize("campos", [
    dict(data_venda="2026-01-01"),            # venda antes da compra
    dict(valor_compra=D(0)),
    dict(valor_venda=D(-1)),
    dict(custos=D(-1)),
    dict(quantidade=D(0)),
    dict(data_compra="10/01/2026"),
    dict(simbolo="  "),
    dict(moeda="EUR"),
    dict(modulo="rendafixa"),
])
def test_validacoes(conn, campos):
    with pytest.raises(ValueError):
        _novo(conn, **campos)
    assert repo.list_trades(conn, "cripto") == []


def test_venda_zero_e_permitida_como_perda_total(conn):
    t = repo.get_trade(conn, _novo(conn, valor_venda=D(0), custos=D(0)))
    assert t.lucro == D(-1000)


# ------------------------------------------------------------ persistência

def test_modulos_ficam_separados(conn):
    _novo(conn, modulo="cripto")
    _novo(conn, modulo="acoes", simbolo="petr4")
    assert [t.simbolo for t in repo.list_trades(conn, "cripto")] == ["ADA"]
    assert [t.simbolo for t in repo.list_trades(conn, "acoes")] == ["PETR4"]


def test_lista_do_mais_recente_para_o_mais_antigo(conn):
    _novo(conn, simbolo="a", data_venda="2026-02-01")
    _novo(conn, simbolo="b", data_venda="2026-03-01")
    assert [t.simbolo for t in repo.list_trades(conn, "cripto")] == ["B", "A"]


def test_editar_e_excluir(conn):
    tid = _novo(conn)
    repo.update_trade(conn, tid, simbolo="sol", nome="Solana", moeda="USD", quantidade=D("2.5"),
                      data_compra="2026-03-01", valor_compra=D(500), data_venda="2026-03-05",
                      valor_venda=D(600), custos=D("1.5"), nota="teste")
    t = repo.get_trade(conn, tid)
    assert (t.simbolo, t.nome, t.moeda, t.quantidade, t.nota) == ("SOL", "Solana", "USD", D("2.5"), "teste")
    assert t.lucro == D("98.5")
    repo.delete_trade(conn, tid)
    assert repo.get_trade(conn, tid) is None


def test_validar_trade_direto_recusa_venda_antes_da_compra():
    with pytest.raises(ValueError):
        validar_trade(modulo="cripto", simbolo="X", moeda="BRL", data_compra="2026-01-02", valor_compra=D(1),
                      data_venda="2026-01-01", valor_venda=D(1), custos=D(0))
