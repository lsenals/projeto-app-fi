from app_fi.core.goals import (
    calcular_nivel,
    evaluate_reducao_categoria,
    evaluate_renda_extra,
    evaluate_saldo_positivo_seguido,
    evaluate_teto_categoria,
    overall_streak,
)


def test_teto_categoria_dentro_do_limite():
    p = evaluate_teto_categoria(spent_cents=8000, target_cents=10000)
    assert p.achieved is True
    assert p.ratio == 0.8


def test_teto_categoria_estourou():
    p = evaluate_teto_categoria(spent_cents=12000, target_cents=10000)
    assert p.achieved is False
    assert p.ratio == 1.0  # capado, não passa de 100% na barra


def test_reducao_categoria_gastou_menos():
    p = evaluate_reducao_categoria(spent_this_month_cents=8000, spent_last_month_cents=10000)
    assert p.achieved is True


def test_reducao_categoria_gastou_igual_ou_mais_nao_bate():
    assert evaluate_reducao_categoria(10000, 10000).achieved is False
    assert evaluate_reducao_categoria(12000, 10000).achieved is False


def test_reducao_categoria_mes_anterior_zerado():
    # não gastou nada nos dois meses: não tem o que reduzir, mas também não piorou
    p = evaluate_reducao_categoria(spent_this_month_cents=0, spent_last_month_cents=0)
    assert p.achieved is False
    assert p.ratio == 1.0


def test_renda_extra_bateu_meta():
    p = evaluate_renda_extra(extra_income_cents=50000, target_cents=30000)
    assert p.achieved is True


def test_renda_extra_abaixo_da_meta():
    p = evaluate_renda_extra(extra_income_cents=10000, target_cents=30000)
    assert p.achieved is False
    assert round(p.ratio, 4) == round(10000 / 30000, 4)


def test_saldo_positivo_seguido():
    p = evaluate_saldo_positivo_seguido(current_streak_months=2, target_months=3)
    assert p.achieved is False
    p2 = evaluate_saldo_positivo_seguido(current_streak_months=3, target_months=3)
    assert p2.achieved is True


def test_overall_streak_para_no_primeiro_mes_sem_pr():
    assert overall_streak([True, True, False, True]) == 2


def test_overall_streak_zero_quando_mes_atual_nao_bateu():
    assert overall_streak([False, True, True]) == 0


def test_overall_streak_vazio():
    assert overall_streak([]) == 0


def test_calcular_nivel_zero_prs_e_nivel_1_zerado():
    n = calcular_nivel(total_prs=0, xp_por_pr=50, xp_por_nivel=100)
    assert n.nivel == 1
    assert n.xp_total == 0
    assert n.xp_no_nivel == 0
    assert n.ratio == 0.0


def test_calcular_nivel_sobe_exatamente_no_limite():
    # 2 PRs * 50 XP = 100 XP = exatamente 1 nível cheio -> nível 2, zerado
    n = calcular_nivel(total_prs=2, xp_por_pr=50, xp_por_nivel=100)
    assert n.nivel == 2
    assert n.xp_no_nivel == 0
    assert n.ratio == 0.0


def test_calcular_nivel_meio_do_nivel():
    # 1 PR * 50 XP = 50 XP -> metade do nível 1
    n = calcular_nivel(total_prs=1, xp_por_pr=50, xp_por_nivel=100)
    assert n.nivel == 1
    assert n.xp_no_nivel == 50
    assert n.ratio == 0.5


def test_calcular_nivel_usa_constantes_padrao():
    n = calcular_nivel(total_prs=3)  # 3 * XP_POR_PR (50) = 150 XP
    assert n.nivel == 2
    assert n.xp_no_nivel == 50
