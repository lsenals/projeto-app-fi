from app_fi.core.summary import ComparisonRow
from app_fi.report.html_report import render_report


def _render(**overrides):
    base = dict(
        mes_nome="Setembro",
        ano=2026,
        mes_anterior_nome="Agosto",
        entradas_cents=855000,
        saidas_cents=285700,
        saldo_cents=569300,
        despesas=[("Alimentação", 106600), ("Moradia", 98000)],
        receitas=[("Salário", 840000)],
        comparacao=[ComparisonRow("Alimentação", 106600, 100000)],
        gerado_em="14/09/2026 10:00",
    )
    base.update(overrides)
    return render_report(**base)


def test_report_contains_key_figures():
    html = _render()
    assert "Setembro" in html and "2026" in html
    assert "R$ 8.550,00" in html  # entradas
    assert "R$ 2.857,00" in html  # saídas
    assert "R$ 5.693,00" in html  # saldo
    assert "Alimentação" in html
    assert "Salário" in html
    assert "Agosto" in html


def test_report_is_self_contained_html():
    html = _render()
    assert html.strip().startswith("<!doctype html>")
    assert "<html" in html and "</html>" in html
    assert "cdn" not in html.lower()  # sem biblioteca externa
    assert "<script" not in html.lower()


def test_report_handles_empty_sections():
    html = _render(despesas=[], receitas=[], comparacao=[])
    assert "Nenhum lançamento" in html
    assert "Sem dados suficientes para comparar" in html


def test_report_marks_increase_and_decrease_distinctly():
    comparacao = [
        ComparisonRow("Alimentação", 120000, 100000),  # alta
        ComparisonRow("Lazer", 40000, 50000),  # queda
    ]
    html = _render(comparacao=comparacao)
    assert "class='alta'" in html
    assert "class='queda'" in html
