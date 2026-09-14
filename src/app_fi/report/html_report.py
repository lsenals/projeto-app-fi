"""Relatório mensal em HTML autocontido — o "Exportar HTML" do Fechamento.

Sem CDN, sem biblioteca de gráficos: SVG desenhado aqui mesmo. Abre offline
no navegador e pode ser salvo como PDF por ele. Função pura — recebe os
números já calculados, devolve uma string; quem escreve o arquivo é
`data/backup.py`.
"""

from __future__ import annotations

from app_fi.core.money import format_brl
from app_fi.core.summary import ComparisonRow


def _bars_svg(items: list[tuple[str, int]], color: str) -> str:
    if not items:
        return '<p class="muted">Nenhum lançamento.</p>'
    max_v = max(v for _, v in items) or 1
    bar_w, gap, left, plot_h, top = 52, 30, 34, 160, 22
    width = left + len(items) * (bar_w + gap)
    height = top + plot_h + 40
    parts = [
        f'<line x1="{left - 10}" y1="{top + plot_h}" x2="{width - 8}" y2="{top + plot_h}" '
        f'stroke="#3a3a3a"/>'
    ]
    for i, (name, value) in enumerate(items):
        x = left + i * (bar_w + gap)
        h = round(plot_h * value / max_v) if max_v else 0
        y = top + (plot_h - h)
        label = name if len(name) <= 12 else name[:11] + "…"
        parts.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{max(h, 1)}" fill="{color}" rx="2"/>'
            f'<text x="{x + bar_w / 2}" y="{y - 8}" text-anchor="middle" class="val">'
            f'{format_brl(value)}</text>'
            f'<text x="{x + bar_w / 2}" y="{top + plot_h + 18}" text-anchor="middle" class="lbl">'
            f'{label}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'class="chart" role="img">' + "".join(parts) + "</svg>"
    )


def _comparison_table(rows: list[ComparisonRow], mes_atual: str, mes_anterior: str) -> str:
    if not rows:
        return '<p class="muted">Sem dados suficientes para comparar.</p>'
    trs = []
    for r in rows:
        if r.delta_pct is None:
            variacao, cls = "—", "neutro"
        else:
            variacao = f"{r.delta_pct:+.0f}%"
            cls = "alta" if r.delta_pct > 0 else ("queda" if r.delta_pct < 0 else "neutro")
        trs.append(
            f"<tr><td>{r.category}</td><td>{format_brl(r.current_cents)}</td>"
            f"<td>{format_brl(r.previous_cents)}</td><td class='{cls}'>{variacao}</td></tr>"
        )
    return (
        f"<table><thead><tr><th>Categoria</th><th>{mes_atual}</th>"
        f"<th>{mes_anterior}</th><th>Variação</th></tr></thead>"
        f"<tbody>{''.join(trs)}</tbody></table>"
    )


def render_report(
    *,
    mes_nome: str,
    ano: int,
    mes_anterior_nome: str,
    entradas_cents: int,
    saidas_cents: int,
    saldo_cents: int,
    despesas: list[tuple[str, int]],
    receitas: list[tuple[str, int]],
    comparacao: list[ComparisonRow],
    gerado_em: str,
) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Fechamento · {mes_nome} {ano}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{
    font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
    background: #121212; color: #e8e8e2; margin: 0;
    padding: 32px clamp(16px, 5vw, 48px) 56px; max-width: 760px; margin-inline: auto;
  }}
  h1 {{ font-size: 1.5rem; margin: 0 0 4px; }}
  .sub {{ color: #9a9a92; font-size: .85rem; margin: 0 0 28px; }}
  .tiles {{ display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 32px; }}
  .tile .k {{ font-size: .75rem; color: #9a9a92; text-transform: uppercase; letter-spacing: .05em; }}
  .tile .v {{ font-size: 1.3rem; font-weight: 600; }}
  .pos {{ color: #7ba98a; }} .neg {{ color: #cf8b83; }}
  h2 {{ font-size: 1rem; margin: 36px 0 12px; border-top: 1px solid #2c2c2c; padding-top: 20px; }}
  .chart {{ width: 100%; height: auto; }}
  .chart .val {{ font-size: 11px; fill: #cfcfc8; }}
  .chart .lbl {{ font-size: 11px; fill: #9a9a92; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
  th, td {{ text-align: right; padding: 8px 6px; border-bottom: 1px solid #2c2c2c; }}
  th:first-child, td:first-child {{ text-align: left; }}
  th {{ color: #9a9a92; font-weight: 500; font-size: .75rem; text-transform: uppercase; }}
  td.alta {{ color: #cf8b83; }} td.queda {{ color: #7ba98a; }} td.neutro {{ color: #9a9a92; }}
  .muted {{ color: #9a9a92; font-style: italic; }}
  .foot {{ margin-top: 40px; font-size: .75rem; color: #6b6b64; border-top: 1px solid #2c2c2c; padding-top: 16px; }}
</style>
</head>
<body>
  <h1>Fechamento · {mes_nome} {ano}</h1>
  <p class="sub">App FI — gerado em {gerado_em}</p>

  <div class="tiles">
    <div class="tile"><div class="k">Entradas</div><div class="v pos">{format_brl(entradas_cents)}</div></div>
    <div class="tile"><div class="k">Saídas</div><div class="v neg">{format_brl(saidas_cents)}</div></div>
    <div class="tile"><div class="k">Saldo do mês</div><div class="v">{format_brl(saldo_cents)}</div></div>
  </div>

  <h2>Gastos por categoria</h2>
  {_bars_svg(despesas, "#a5544c")}

  <h2>Entradas por origem</h2>
  {_bars_svg(receitas, "#4c7a5c")}

  <h2>Comparado a {mes_anterior_nome}</h2>
  {_comparison_table(comparacao, mes_nome[:3], mes_anterior_nome[:3])}

  <p class="foot">Dados locais · nenhuma informação enviada para a internet</p>
</body>
</html>"""
