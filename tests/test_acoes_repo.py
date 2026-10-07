from decimal import Decimal as D

import pytest

from app_fi.data import acoes_repo as acoes
from app_fi.data import crypto_repo as crypto
from app_fi.data.carteira_repo import CarteiraRepo
from app_fi.data.db import get_db


@pytest.fixture
def conn(tmp_path):
    return get_db(tmp_path / "t.db")


def test_acoes_comecam_sem_ativos_nem_catalogo(conn):
    assert acoes.list_assets(conn) == []
    assert len(crypto.list_assets(conn)) == 40   # o catálogo de cripto não vaza para as ações


def test_cadastra_ticker_e_calcula_preco_medio_e_lucro(conn):
    petr = acoes.add_custom_asset(conn, " petr4 ", "Petrobras PN")
    acoes.add_trade(conn, asset_id=petr, side="buy", date="2026-01-10", quantity=D(100), unit_price=D("30"), fee=D("5"))
    acoes.add_trade(conn, asset_id=petr, side="buy", date="2026-02-10", quantity=D(100), unit_price=D("34"))
    acoes.set_price(conn, petr, D("38"), "2026-03-01")
    acoes.set_targets(conn, petr, D(20), D(10))
    c = acoes.load_wallet(conn)
    (a,) = c.ativos
    assert a.simbolo == "PETR4"
    assert a.posicao.quantidade == D(200) and a.posicao.preco_medio == D("32.025")   # (3005 + 3400) / 200
    assert a.avaliacao.lucro == D("1195")                                              # 200*38 - 6405
    assert a.meta.preco_alvo == D("38.43")                                             # 32.025 * 1.2


def test_venda_maior_que_o_saldo_e_recusada(conn):
    vale = acoes.add_custom_asset(conn, "vale3", "Vale ON")
    acoes.add_trade(conn, asset_id=vale, side="buy", date="2026-01-01", quantity=D(10), unit_price=D(60))
    with pytest.raises(ValueError, match="maior que a quantidade"):
        acoes.add_trade(conn, asset_id=vale, side="sell", date="2026-01-02", quantity=D(11), unit_price=D(61))


def test_carteiras_nao_se_misturam(conn):
    a = acoes.add_custom_asset(conn, "xyz", "Ação XYZ")
    c = crypto.add_custom_asset(conn, "xyz", "Cripto XYZ")      # mesmo símbolo, módulos diferentes
    acoes.add_trade(conn, asset_id=a, side="buy", date="2026-01-01", quantity=D(1), unit_price=D(10))
    assert len(acoes.list_trades(conn)) == 1 and crypto.list_trades(conn) == []
    assert acoes.get_asset(conn, a)["name"] == "Ação XYZ" and crypto.get_asset(conn, c)["name"] == "Cripto XYZ"


def test_moeda_de_exibicao_e_por_modulo_mas_a_cotacao_e_uma_so(conn):
    acoes.set_display_currency(conn, "USD")
    assert acoes.get_display_currency(conn) == "USD" and crypto.get_display_currency(conn) == "BRL"
    acoes.set_usd_rate(conn, D("5.2"))
    assert crypto.get_usd_rate(conn) == D("5.2")


def test_acao_em_dolar(conn):
    aapl = acoes.add_custom_asset(conn, "aapl", "Apple", currency="USD")
    acoes.add_trade(conn, asset_id=aapl, side="buy", date="2026-01-01", quantity=D(2), unit_price=D(200))
    acoes.set_price(conn, aapl, D(220), "2026-02-01")
    acoes.set_usd_rate(conn, D(5))
    r = acoes.load_wallet(conn).resumo
    assert (r.investido, r.valor_atual) == (D(2000), D(2200))     # em R$: 400 e 440 em US$ × 5


def test_prefixo_invalido_e_recusado():
    with pytest.raises(ValueError):
        CarteiraRepo("transactions; DROP TABLE x")
