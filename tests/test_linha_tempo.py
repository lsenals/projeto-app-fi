import datetime as dt

from app_fi.core.linha_tempo import montar_linha_tempo

HOJE = dt.date(2026, 10, 7)


def _tx(date, kind, cents, status="confirmed", **extra):
    return {"date": date, "kind": kind, "amount_cents": cents, "status": status, **extra}


def test_mes_vazio_tem_um_slot_por_dia_e_sem_pico():
    lt = montar_linha_tempo([], 2026, 10, HOJE)
    assert lt.dias_no_mes == 31 and len(lt.eventos_por_dia) == 31
    assert lt.dia_hoje == 7 and lt.pico_dia is None and lt.pico_cents == 0
    assert all(d == () for d in lt.eventos_por_dia)


def test_fevereiro_tem_28_dias():
    assert montar_linha_tempo([], 2026, 2, HOJE).dias_no_mes == 28


def test_eventos_vao_para_o_dia_certo_e_ignoram_outros_meses_e_pendentes():
    rows = [
        _tx("2026-10-03", "expense", 1000), _tx("2026-10-03", "income", 5000),
        _tx("2026-09-30", "expense", 9999),                      # outro mês
        _tx("2026-10-05", "expense", 700, status="pending"),     # ainda não ocorreu
    ]
    lt = montar_linha_tempo(rows, 2026, 10, HOJE)
    assert [e.tipo for e in lt.eventos_do_dia(3)] == ["income", "expense"]  # maior valor primeiro
    assert lt.eventos_do_dia(5) == () and lt.eventos_do_dia(30) == ()


def test_pico_e_o_dia_de_maior_gasto_somando_o_dia():
    rows = [
        _tx("2026-10-02", "expense", 3000),
        _tx("2026-10-04", "expense", 2000), _tx("2026-10-04", "expense", 2500),
        _tx("2026-10-06", "income", 90000),                      # receita não conta como pico
    ]
    lt = montar_linha_tempo(rows, 2026, 10, HOJE)
    assert (lt.pico_dia, lt.pico_cents) == (4, 4500)
    assert lt.maior_total_cents == 90000 and lt.total_do_dia(4, "expense") == 4500


def test_recorrente_e_descricao():
    rows = [
        _tx("2026-10-01", "expense", 150000, id=1, recurring_id=7, category_name="Moradia", payee_name="Aluguel"),
        _tx("2026-10-02", "income", 800000, id=2, recurring_id=None, income_source_name="Salário", payee_name=None),
        _tx("2026-10-02", "expense", 1000, id=3, category_name=None, payee_name=None),
    ]
    lt = montar_linha_tempo(rows, 2026, 10, HOJE)
    aluguel = lt.eventos_do_dia(1)[0]
    assert aluguel.recorrente and aluguel.descricao == "Moradia · Aluguel" and aluguel.id == 1
    dia2 = {e.id: e for e in lt.eventos_do_dia(2)}
    assert not dia2[2].recorrente and dia2[2].descricao == "Salário"
    assert dia2[3].descricao == "Sem categoria"


def test_navegar_para_outro_mes_usa_os_lancamentos_dele_e_sem_marca_de_hoje():
    rows = [_tx("2026-09-10", "expense", 1000), _tx("2026-10-03", "expense", 5000)]
    lt = montar_linha_tempo(rows, 2026, 9, HOJE)
    assert (lt.ano, lt.mes, lt.dias_no_mes) == (2026, 9, 30)
    assert lt.dia_hoje is None and lt.pico_dia == 10 and lt.pico_cents == 1000
    assert montar_linha_tempo(rows, 2026, 10, HOJE).dia_hoje == 7


def test_total_diario_soma_o_tipo_e_escala_pelo_maior_dia():
    rows = [_tx("2026-10-02", "expense", 300), _tx("2026-10-02", "expense", 200), _tx("2026-10-02", "income", 100)]
    lt = montar_linha_tempo(rows, 2026, 10, HOJE)
    assert lt.total_do_dia(2, "expense") == 500 and lt.total_do_dia(2, "income") == 100
    assert lt.maior_total_cents == 500