import datetime as dt

from app_fi.core.painel import calcular_painel

HOJE = dt.date(2026, 10, 7)


def _tx(date, kind, cents, status="confirmed"):
    return {"date": date, "kind": kind, "amount_cents": cents, "status": status}


def test_sem_lancamentos_tudo_zerado():
    p = calcular_painel([], HOJE, objetivos_batidos=0, objetivos_total=0)
    assert [a.percentual for a in p.aneis] == [0, 0]
    assert p.saldo_semana_cents == 0 and p.saldo_semana_ratio == 0.0
    assert p.poupanca_mes_cents == 0 and p.poupanca_mes_ratio == 0.0


def test_painel_tem_so_dois_aneis():
    assert [a.rotulo for a in calcular_painel([], HOJE, 0, 0).aneis] == ["Objetivos", "Gasto/renda"]


def test_anel_de_objetivos():
    p = calcular_painel([], HOJE, objetivos_batidos=1, objetivos_total=4)
    assert p.aneis[0].percentual == 25


def test_poupanca_do_mes_e_gasto_sobre_renda():
    rows = [
        _tx("2026-10-01", "income", 100000),
        _tx("2026-10-03", "expense", 25000),
    ]
    p = calcular_painel(rows, HOJE, 0, 0)
    assert p.poupanca_mes_cents == 75000
    assert p.poupanca_mes_ratio == 0.75
    assert p.aneis[1].percentual == 25


def test_saldo_da_semana_usa_os_ultimos_7_dias_atravessando_o_mes():
    rows = [
        _tx("2026-09-30", "income", 50000),   # fora: a janela de 7 dias até 07/10 começa em 01/10
        _tx("2026-10-02", "income", 20000),
        _tx("2026-10-05", "expense", 5000),
    ]
    p = calcular_painel(rows, HOJE, 0, 0)
    assert p.saldo_semana_cents == 15000
    assert p.saldo_semana_ratio == 0.75


def test_janela_da_semana_inclui_dias_do_mes_anterior():
    hoje = dt.date(2026, 10, 3)  # janela: 27/09 a 03/10
    rows = [_tx("2026-09-28", "income", 10000), _tx("2026-10-02", "expense", 4000)]
    p = calcular_painel(rows, hoje, 0, 0)
    assert p.saldo_semana_cents == 6000
    assert p.poupanca_mes_cents == -4000  # mês só enxerga outubro


def test_pendentes_nao_entram():
    rows = [_tx("2026-10-02", "income", 100000), _tx("2026-10-03", "expense", 90000, status="pending")]
    p = calcular_painel(rows, HOJE, 0, 0)
    assert p.poupanca_mes_cents == 100000


def test_saldo_negativo_zera_a_razao_mas_mantem_o_valor():
    rows = [_tx("2026-10-01", "income", 10000), _tx("2026-10-02", "expense", 30000)]
    p = calcular_painel(rows, HOJE, 0, 0)
    assert p.poupanca_mes_cents == -20000
    assert p.poupanca_mes_ratio == 0.0
    assert p.aneis[1].percentual == 100  # gasto limitado a 100% da renda


def test_lancamentos_futuros_ficam_de_fora():
    rows = [_tx("2026-10-20", "expense", 99999), _tx("2026-10-01", "income", 1000)]
    p = calcular_painel(rows, HOJE, 0, 0)
    assert p.poupanca_mes_cents == 1000
