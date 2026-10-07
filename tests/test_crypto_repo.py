from decimal import Decimal as D

import pytest

from app_fi.core.crypto import CATALOGO_PRINCIPAIS
from app_fi.data import crypto_repo as repo
from app_fi.data.db import get_db


@pytest.fixture
def conn(tmp_path):
    return get_db(tmp_path / "t.db")


def _id(conn, simbolo):
    return conn.execute("SELECT id FROM crypto_assets WHERE symbol = ?", (simbolo,)).fetchone()["id"]


def test_catalogo_do_banco_espelha_o_do_core(conn):
    no_banco = [(r["symbol"], r["name"]) for r in repo.list_assets(conn)]
    assert no_banco == list(CATALOGO_PRINCIPAIS)


def test_compra_e_leitura_exata_de_decimais(conn):
    ada = _id(conn, "ADA")
    repo.add_trade(conn, asset_id=ada, side="buy", date="2026-01-01",
                   quantity=D("1000.12345678"), unit_price=D("0.00002100"), fee=D("1.5"))
    t = repo.list_trades(conn, ada)[0]
    assert (t["quantity"], t["unit_price"], t["fee"]) == ("1000.12345678", "0.00002100", "1.5")


def test_venda_maior_que_o_saldo_e_recusada_e_nada_e_gravado(conn):
    btc = _id(conn, "BTC")
    repo.add_trade(conn, asset_id=btc, side="buy", date="2026-01-01", quantity=D(1), unit_price=D(100))
    with pytest.raises(ValueError, match="maior que a quantidade"):
        repo.add_trade(conn, asset_id=btc, side="sell", date="2026-01-02", quantity=D(2), unit_price=D(100))
    assert len(repo.list_trades(conn, btc)) == 1


@pytest.mark.parametrize("campos", [
    dict(quantity=D(0)), dict(unit_price=D(0)), dict(fee=D(-1)), dict(date="01/02/2026"), dict(side="x"),
])
def test_validacoes_de_operacao(conn, campos):
    base = dict(asset_id=_id(conn, "BTC"), side="buy", date="2026-01-01", quantity=D(1), unit_price=D(1))
    with pytest.raises(ValueError):
        repo.add_trade(conn, **{**base, **campos})


def test_apagar_compra_que_sustenta_uma_venda_e_recusado(conn):
    eth = _id(conn, "ETH")
    compra = repo.add_trade(conn, asset_id=eth, side="buy", date="2026-01-01", quantity=D(1), unit_price=D(10))
    repo.add_trade(conn, asset_id=eth, side="sell", date="2026-01-02", quantity=D(1), unit_price=D(12))
    with pytest.raises(ValueError):
        repo.delete_trade(conn, compra)
    assert len(repo.list_trades(conn, eth)) == 2


def test_apagar_venda_e_permitido(conn):
    eth = _id(conn, "ETH")
    repo.add_trade(conn, asset_id=eth, side="buy", date="2026-01-01", quantity=D(1), unit_price=D(10))
    venda = repo.add_trade(conn, asset_id=eth, side="sell", date="2026-01-02", quantity=D(1), unit_price=D(12))
    repo.delete_trade(conn, venda)
    assert len(repo.list_trades(conn, eth)) == 1


def test_editar_operacao_revalida_o_saldo(conn):
    eth = _id(conn, "ETH")
    compra = repo.add_trade(conn, asset_id=eth, side="buy", date="2026-01-01", quantity=D(2), unit_price=D(10))
    repo.add_trade(conn, asset_id=eth, side="sell", date="2026-01-02", quantity=D(2), unit_price=D(12))
    with pytest.raises(ValueError):  # reduzir a compra deixaria a venda sem saldo
        repo.update_trade(conn, compra, side="buy", date="2026-01-01", quantity=D(1), unit_price=D(10))
    repo.update_trade(conn, compra, side="buy", date="2026-01-01", quantity=D(3), unit_price=D(10), note="ajuste")
    assert repo.get_trade(conn, compra)["quantity"] == "3"


def test_set_price_atualiza_atual_e_historico_sem_duplicar_o_dia(conn):
    ada = _id(conn, "ADA")
    repo.set_price(conn, ada, D("2.5"), "2026-03-01")
    repo.set_price(conn, ada, D("2.7"), "2026-03-01")  # mesmo dia: corrige, não duplica
    repo.set_price(conn, ada, D("3"), "2026-03-02")
    a = repo.get_asset(conn, ada)
    assert (a["current_price"], a["price_updated_at"]) == ("3", "2026-03-02")
    hist = conn.execute("SELECT date, price FROM crypto_price_history ORDER BY date").fetchall()
    assert [(h["date"], h["price"]) for h in hist] == [("2026-03-01", "2.7"), ("2026-03-02", "3")]


def test_set_price_recusa_zero(conn):
    with pytest.raises(ValueError):
        repo.set_price(conn, _id(conn, "ADA"), D(0))


def test_metas(conn):
    ada = _id(conn, "ADA")
    repo.set_targets(conn, ada, D(20), D(10))
    a = repo.get_asset(conn, ada)
    assert (a["target_gain_pct"], a["stop_loss_pct"]) == ("20", "10")
    repo.set_targets(conn, ada, None, None)
    assert repo.get_asset(conn, ada)["target_gain_pct"] is None
    for ganho, stop in ((D(0), None), (None, D(100)), (None, D(0))):
        with pytest.raises(ValueError):
            repo.set_targets(conn, ada, ganho, stop)


def test_ativo_personalizado(conn):
    novo = repo.add_custom_asset(conn, " xyz ", "Meu Token")
    a = repo.get_asset(conn, novo)
    assert (a["symbol"], a["name"], a["is_custom"]) == ("XYZ", "Meu Token", 1)
    with pytest.raises(ValueError, match="já está"):
        repo.add_custom_asset(conn, "btc", "Outro")
    with pytest.raises(ValueError):
        repo.add_custom_asset(conn, "!!", "x")


def test_carteira_de_ponta_a_ponta(conn):
    ada = _id(conn, "ADA")
    repo.add_trade(conn, asset_id=ada, side="buy", date="2026-01-01", quantity=D(100), unit_price=D(2))
    repo.set_price(conn, ada, D("2.4"), "2026-02-01")
    repo.set_targets(conn, ada, D(20), None)
    c = repo.load_wallet(conn)
    (ativo,) = c.ativos
    assert ativo.simbolo == "ADA" and ativo.avaliacao.lucro == D(40)
    assert ativo.meta.atingiu_alvo  # 2,4 = 2 * 1,20
    assert c.resumo.lucro_pct == D(20)
