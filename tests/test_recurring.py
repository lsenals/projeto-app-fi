from app_fi.core.recurring import forecast


def test_no_total_means_no_forecast():
    f = forecast("2026-09-14", "month", 1, total_installments=None, current_installment=1)
    assert f.remaining_installments is None
    assert f.predicted_end_date is None


def test_fresh_monthly_plan_from_first_installment():
    # 12x, ainda na 1ª — a próxima (1ª) já é a de hoje; a última é 11 meses depois
    f = forecast("2026-09-14", "month", 1, total_installments=12, current_installment=1)
    assert f.remaining_installments == 12
    assert f.predicted_end_date == "2027-08-14"


def test_plan_started_midway():
    # já na parcela 5 de 12: faltam 8 (5,6,7,8,9,10,11,12)
    f = forecast("2026-09-14", "month", 1, total_installments=12, current_installment=5)
    assert f.remaining_installments == 8
    assert f.predicted_end_date == "2027-04-14"


def test_last_installment_ends_on_next_date():
    f = forecast("2026-09-14", "month", 1, total_installments=12, current_installment=12)
    assert f.remaining_installments == 1
    assert f.predicted_end_date == "2026-09-14"


def test_already_past_total_returns_zero_remaining():
    f = forecast("2026-09-14", "month", 1, total_installments=12, current_installment=13)
    assert f.remaining_installments == 0
    assert f.predicted_end_date == "2026-09-14"


def test_weekly_interval():
    f = forecast("2026-09-01", "week", 1, total_installments=4, current_installment=1)
    assert f.remaining_installments == 4
    assert f.predicted_end_date == "2026-09-22"  # +3 semanas


def test_interval_count_greater_than_one():
    # a cada 2 meses, 3 parcelas: 0, +2, +4 meses
    f = forecast("2026-01-15", "month", 2, total_installments=3, current_installment=1)
    assert f.predicted_end_date == "2026-05-15"


def test_month_end_clamping():
    # 31/01 + 1 mês não existe -> cai pro último dia de fevereiro
    f = forecast("2026-01-31", "month", 1, total_installments=2, current_installment=1)
    assert f.predicted_end_date == "2026-02-28"
