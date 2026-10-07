from decimal import Decimal as D

import pytest

from app_fi.core.crypto import (
    CATALOGO_PRINCIPAIS, Operacao, avaliar, calcular_posicao, fator_conversao, formatar_pct, formatar_preco,
    formatar_quantidade, formatar_valor, montar_carteira, normalizar_simbolo, parse_decimal,
    progresso_meta,
)


def _op(lado, data, qtd, preco, taxa="0", id=0):
    return Operacao(lado, data, D(qtd), D(preco), D(taxa), id)


# ------------------------------------------------------------------ posição

def test_compra_unica_define_preco_medio():
    p = calcular_posicao([_op("buy", "2026-01-01", "100", "2")])
    assert p.quantidade == D(100)
    assert p.preco_medio == D(2)
    assert p.custo_total == D(200)
    assert p.realizado == D(0)


def test_duas_compras_fazem_preco_medio_ponderado():
    p = calcular_posicao([_op("buy", "2026-01-01", "100", "2"), _op("buy", "2026-01-02", "100", "4")])
    assert p.quantidade == D(200)
    assert p.preco_medio == D(3)


def test_taxa_de_compra_entra_no_custo():
    p = calcular_posicao([_op("buy", "2026-01-01", "10", "10", taxa="5")])
    assert p.custo_total == D(105)
    assert p.preco_medio == D("10.5")


def test_venda_parcial_realiza_lucro_e_mantem_preco_medio():
    p = calcular_posicao([_op("buy", "2026-01-01", "100", "2"), _op("sell", "2026-02-01", "40", "3")])
    assert p.quantidade == D(60)
    assert p.preco_medio == D(2)  # venda não muda o preço médio
    assert p.realizado == D(40)   # 40 * (3 - 2)
    assert p.total_vendido == D(120)


def test_taxa_de_venda_reduz_o_realizado():
    p = calcular_posicao([_op("buy", "2026-01-01", "10", "10"), _op("sell", "2026-02-01", "10", "12", taxa="4")])
    assert p.realizado == D(16)  # 10*12 - 4 - 100
    assert p.quantidade == D(0)
    assert p.custo_total == D(0)


def test_venda_com_prejuizo():
    p = calcular_posicao([_op("buy", "2026-01-01", "10", "10"), _op("sell", "2026-02-01", "5", "8")])
    assert p.realizado == D(-10)


def test_vender_tudo_e_recomprar_reinicia_o_preco_medio():
    p = calcular_posicao([
        _op("buy", "2026-01-01", "10", "10"), _op("sell", "2026-01-02", "10", "20"),
        _op("buy", "2026-01-03", "5", "30"),
    ])
    assert p.preco_medio == D(30)
    assert p.realizado == D(100)


def test_venda_maior_que_o_saldo_e_recusada():
    with pytest.raises(ValueError, match=r"em 02/01/2026 é maior que a quantidade em carteira \(1\)"):
        calcular_posicao([_op("buy", "2026-01-01", "1", "10"), _op("sell", "2026-01-02", "2", "10")])


def test_ordem_cronologica_vale_mais_que_a_ordem_de_chegada():
    # a venda é de 02/01, mas foi cadastrada antes da compra de 01/01 (id menor)
    p = calcular_posicao([_op("sell", "2026-01-02", "5", "12", id=1), _op("buy", "2026-01-01", "10", "10", id=2)])
    assert p.quantidade == D(5)
    assert p.realizado == D(10)


def test_decimais_pequenos_sao_exatos():
    p = calcular_posicao([_op("buy", "2026-01-01", "1000000", "0.00002100")])
    assert p.custo_total == D("21")


# ---------------------------------------------------------------- avaliação

def test_avaliar_lucro_e_percentual():
    pos = calcular_posicao([_op("buy", "2026-01-01", "100", "2")])
    a = avaliar(pos, D("2.5"))
    assert a.valor_atual == D(250)
    assert a.lucro == D(50)
    assert a.lucro_pct == D(25)


def test_avaliar_sem_preco_devolve_none():
    assert avaliar(calcular_posicao([_op("buy", "2026-01-01", "1", "1")]), None) is None


# --------------------------------------------------------------------- meta

def test_meta_de_20_pct_sobre_o_preco_medio():
    m = progresso_meta(D("2"), D("2.2"), D(20), None)
    assert m.preco_alvo == D("2.4")
    assert m.ratio == pytest.approx(0.5)
    assert not m.atingiu_alvo
    assert m.falta_pct == pytest.approx(D("9.0909"), abs=D("0.001"))


def test_meta_atingida():
    m = progresso_meta(D("2"), D("2.5"), D(20), None)
    assert m.atingiu_alvo and m.ratio == 1.0 and m.falta_pct is None


def test_progresso_nunca_fica_negativo():
    assert progresso_meta(D("2"), D("1"), D(20), None).ratio == 0.0


def test_stop_loss():
    m = progresso_meta(D("10"), D("8.9"), None, D(10))
    assert m.preco_stop == D(9) and m.atingiu_stop
    assert not progresso_meta(D("10"), D("9.5"), None, D(10)).atingiu_stop


def test_meta_sem_preco_atual_nao_quebra():
    m = progresso_meta(D("2"), None, D(20), D(10))
    assert m.ratio == 0.0 and not m.atingiu_alvo and not m.atingiu_stop


# ----------------------------------------------------------------- carteira

def _ativo(id, simbolo, preco=None, ganho=None, stop=None, data="2026-03-01", moeda="BRL"):
    return {
        "id": id, "symbol": simbolo, "name": simbolo, "current_price": preco,
        "price_updated_at": data if preco else None, "target_gain_pct": ganho, "stop_loss_pct": stop,
        "currency": moeda,
    }


def _trade(id, asset_id, side, data, qtd, preco, taxa="0"):
    return {"id": id, "asset_id": asset_id, "side": side, "date": data, "quantity": qtd,
            "unit_price": preco, "fee": taxa}


def test_resumo_da_carteira():
    ativos = [_ativo(1, "ADA", preco="3"), _ativo(2, "BTC", preco="1000")]
    ops = [
        _trade(1, 1, "buy", "2026-01-01", "100", "2"),       # custo 200, vale 300
        _trade(2, 2, "buy", "2026-01-01", "1", "800"),       # custo 800, vale 1000
        _trade(3, 2, "sell", "2026-02-01", "0.5", "1200"),   # realiza 0.5*(1200-800)=200
    ]
    r = montar_carteira(ativos, ops, []).resumo
    assert r.investido == D(600)               # 200 + 400 que sobrou de BTC
    assert r.valor_atual == D(800)             # 300 + 0.5*1000
    assert r.lucro_nao_realizado == D(200)
    assert r.realizado == D(200)
    assert r.resultado_total == D(400)
    assert r.ativos_sem_preco == 0


def test_ativo_sem_preco_entra_pelo_custo_e_e_sinalizado():
    r = montar_carteira([_ativo(1, "ADA")], [_trade(1, 1, "buy", "2026-01-01", "10", "2")], []).resumo
    assert r.valor_atual == D(20) and r.lucro_nao_realizado == D(0) and r.ativos_sem_preco == 1


def test_ativos_sem_operacoes_ficam_fora_da_carteira():
    c = montar_carteira([_ativo(1, "ADA"), _ativo(2, "BTC")], [_trade(1, 1, "buy", "2026-01-01", "1", "1")], [])
    assert [a.simbolo for a in c.ativos] == ["ADA"]


def test_em_carteira_vem_antes_dos_encerrados():
    ativos = [_ativo(1, "ADA", preco="1"), _ativo(2, "BTC", preco="1")]
    ops = [
        _trade(1, 1, "buy", "2026-01-01", "1", "1"), _trade(2, 1, "sell", "2026-01-02", "1", "2"),
        _trade(3, 2, "buy", "2026-01-01", "1", "1"),
    ]
    assert [a.simbolo for a in montar_carteira(ativos, ops, []).ativos] == ["BTC", "ADA"]


def test_meta_so_existe_com_posicao_aberta_e_meta_definida():
    ativos = [_ativo(1, "ADA", preco="2.2", ganho="20"), _ativo(2, "BTC", preco="1")]
    ops = [_trade(1, 1, "buy", "2026-01-01", "10", "2"), _trade(2, 2, "buy", "2026-01-01", "1", "1")]
    por_simbolo = {a.simbolo: a for a in montar_carteira(ativos, ops, []).ativos}
    assert por_simbolo["ADA"].meta.preco_alvo == D("2.4")
    assert por_simbolo["BTC"].meta is None


def test_evolucao_usa_o_ultimo_preco_conhecido_em_cada_data():
    ativos = [_ativo(1, "ADA", preco="3")]
    ops = [_trade(1, 1, "buy", "2026-01-01", "100", "2")]
    hist = [
        {"asset_id": 1, "date": "2026-02-01", "price": "2.5"},
        {"asset_id": 1, "date": "2026-03-01", "price": "3"},
    ]
    serie = montar_carteira(ativos, ops, hist).evolucao
    assert [(p.data, p.valor, p.investido) for p in serie] == [
        ("2026-01-01", D(200), D(200)),   # sem histórico ainda: vale o preço da compra
        ("2026-02-01", D(250), D(200)),
        ("2026-03-01", D(300), D(200)),
    ]


def test_evolucao_ignora_datas_sem_posicao_aberta():
    ativos = [_ativo(1, "ADA", preco="3")]
    ops = [_trade(1, 1, "buy", "2026-01-01", "10", "2"), _trade(2, 1, "sell", "2026-01-05", "10", "3")]
    hist = [{"asset_id": 1, "date": "2026-02-01", "price": "3"}]
    assert [p.data for p in montar_carteira(ativos, ops, hist).evolucao] == ["2026-01-01"]


# ------------------------------------------------------------------ parsing

@pytest.mark.parametrize("texto,esperado", [
    ("1.234,56", D("1234.56")), ("0,5", D("0.5")), ("0.5", D("0.5")), ("R$ 2,10", D("2.10")),
    ("20%", D(20)), ("  ", None), (None, None), ("0,00002100", D("0.00002100")),
])
def test_parse_decimal(texto, esperado):
    assert parse_decimal(texto) == esperado


@pytest.mark.parametrize("texto", ["abc", "1,2,3", "NaN", "Infinity"])
def test_parse_decimal_invalido(texto):
    with pytest.raises(ValueError):
        parse_decimal(texto)


# -------------------------------------------------------------- formatação

def test_formatar_quantidade():
    assert formatar_quantidade(D("0.5")) == "0,5"
    assert formatar_quantidade(D("1234.5678")) == "1.234,5678"
    assert formatar_quantidade(D("100")) == "100"
    assert formatar_quantidade(D("0.000000019")) == "0,00000002"


def test_formatar_preco_pequeno_nao_vira_zero():
    assert formatar_preco(D("34.9")) == "R$ 34,90"
    assert formatar_preco(D("0.000021")) == "R$ 0,000021"
    assert formatar_preco(D("0.5")) == "R$ 0,50"
    assert formatar_preco(D("1234.567")) == "R$ 1.234,57"


def test_formatar_valor_e_pct():
    assert formatar_valor(D("5049.101")) == "R$ 5.049,10"
    assert formatar_valor(D("-12.5")) == "-R$ 12,50"
    assert formatar_pct(D("12.345")) == "+12,35%"
    assert formatar_pct(D("-3")) == "-3,00%"
    assert formatar_pct(None) == "—"


def test_normalizar_simbolo():
    assert normalizar_simbolo("  ada ") == "ADA"
    for ruim in ("", "A B", "ADA!", "X" * 13):
        with pytest.raises(ValueError):
            normalizar_simbolo(ruim)


def test_catalogo_nao_tem_simbolos_repetidos():
    simbolos = [s for s, _ in CATALOGO_PRINCIPAIS]
    assert len(simbolos) == len(set(simbolos)) and {"BTC", "ETH", "ADA"} <= set(simbolos)


# ------------------------------------------------------------------- moedas

def test_fator_de_conversao():
    assert fator_conversao("BRL", "BRL", None) == D(1)
    assert fator_conversao("USD", "USD", None) == D(1)
    assert fator_conversao("USD", "BRL", D("5")) == D(5)
    assert fator_conversao("BRL", "USD", D("5")) == D("0.2")
    assert fator_conversao("USD", "BRL", None) is None
    assert fator_conversao("USD", "BRL", D(0)) is None


def test_ativo_em_dolar_exibido_em_reais_converte_pela_cotacao():
    ativos = [_ativo(1, "ETH", preco="3000", moeda="USD")]
    ops = [_trade(1, 1, "buy", "2026-01-01", "2", "2000")]   # custo US$ 4.000, vale US$ 6.000
    c = montar_carteira(ativos, ops, [], moeda_exibicao="BRL", cotacao_usd=D("5"))
    r = c.resumo
    assert (r.moeda, r.investido, r.valor_atual, r.lucro_nao_realizado) == ("BRL", D(20000), D(30000), D(10000))
    assert r.lucro_pct == D(50)  # o percentual não depende do câmbio
    (a,) = c.ativos
    assert a.moeda == "USD" and a.avaliacao.lucro == D(2000)  # o ativo continua em dólar


def test_carteira_mista_soma_na_moeda_de_exibicao():
    ativos = [_ativo(1, "ETH", preco="3000", moeda="USD"), _ativo(2, "ADA", preco="3")]
    ops = [_trade(1, 1, "buy", "2026-01-01", "1", "2000"), _trade(2, 2, "buy", "2026-01-01", "100", "2")]
    r_brl = montar_carteira(ativos, ops, [], moeda_exibicao="BRL", cotacao_usd=D("5")).resumo
    assert r_brl.investido == D(10200) and r_brl.valor_atual == D(15300)   # 1*2000*5 + 200 | 3000*5 + 300
    r_usd = montar_carteira(ativos, ops, [], moeda_exibicao="USD", cotacao_usd=D("5")).resumo
    assert r_usd.investido == D(2040) and r_usd.valor_atual == D(3060)     # 2000 + 200/5 | 3000 + 300/5


def test_sem_cotacao_o_ativo_em_outra_moeda_fica_de_fora_e_e_sinalizado():
    ativos = [_ativo(1, "ETH", preco="3000", moeda="USD"), _ativo(2, "ADA", preco="3")]
    ops = [_trade(1, 1, "buy", "2026-01-01", "1", "2000"), _trade(2, 2, "buy", "2026-01-01", "100", "2")]
    r = montar_carteira(ativos, ops, [], moeda_exibicao="BRL", cotacao_usd=None).resumo
    assert r.ativos_sem_cotacao == 1
    assert r.investido == D(200) and r.valor_atual == D(300)


def test_realizado_de_ativo_em_dolar_tambem_converte():
    ativos = [_ativo(1, "ETH", moeda="USD")]
    ops = [_trade(1, 1, "buy", "2026-01-01", "1", "2000"), _trade(2, 1, "sell", "2026-02-01", "1", "2500")]
    r = montar_carteira(ativos, ops, [], moeda_exibicao="BRL", cotacao_usd=D("5.5")).resumo
    assert r.realizado == D(2750)


def test_evolucao_converte_cada_ativo():
    ativos = [_ativo(1, "ETH", preco="3000", moeda="USD")]
    ops = [_trade(1, 1, "buy", "2026-01-01", "1", "2000")]
    hist = [{"asset_id": 1, "date": "2026-02-01", "price": "3000"}]
    serie = montar_carteira(ativos, ops, hist, moeda_exibicao="BRL", cotacao_usd=D("5")).evolucao
    assert [(p.valor, p.investido) for p in serie] == [(D(10000), D(10000)), (D(15000), D(10000))]


def test_moeda_de_exibicao_invalida_e_recusada():
    with pytest.raises(ValueError):
        montar_carteira([], [], [], moeda_exibicao="EUR")
    with pytest.raises(ValueError):
        montar_carteira([_ativo(1, "X", moeda="EUR")], [_trade(1, 1, "buy", "2026-01-01", "1", "1")], [])


def test_formatacao_em_dolar():
    assert formatar_valor(D("5049.101"), "USD") == "US$ 5.049,10"
    assert formatar_valor(D("-12.5"), "USD") == "-US$ 12,50"
    assert formatar_preco(D("34.9"), "USD") == "US$ 34,90"
    assert formatar_preco(D("0.000021"), "USD") == "US$ 0,000021"
    assert formatar_preco(D("-0.5"), "USD") == "-US$ 0,50"
    assert formatar_preco(D("34.9")) == "R$ 34,90"  # padrão segue em reais


def test_parse_decimal_aceita_simbolo_de_dolar():
    assert parse_decimal("US$ 1.234,50") == D("1234.50")
    assert parse_decimal("$3.5") == D("3.5")