"""App FI — ponto de entrada.

Passo 3 (em progresso): dialog de lançamento de verdade — despesa/receita,
categoria em chips sempre visíveis, "Salvar e novo", Enter salva. A tela
definitiva (card Hoje, drawer, edição/exclusão) vem nos próximos commits.
"""

import datetime as dt

import flet as ft

from app_fi.core.money import format_brl, parse_brl
from app_fi.core.summary import month_totals
from app_fi.data import transactions_repo as repo
from app_fi.data.db import get_db

_MESES = [
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def main(page: ft.Page) -> None:
    page.title = "App FI"
    page.padding = 20
    conn = get_db()
    hoje = dt.date.today()

    saldo = ft.Text(size=22, weight=ft.FontWeight.BOLD)
    resumo = ft.Text(size=13, color=ft.Colors.GREY)
    lista = ft.ListView(expand=True, spacing=2)

    def linha(r) -> ft.Control:
        receita = r["kind"] == "income"
        nome = (r["income_source_name"] if receita else r["category_name"]) or (
            "—" if receita else "Sem categoria"
        )
        sinal = "+" if receita else "−"
        cor = ft.Colors.GREEN if receita else ft.Colors.RED
        return ft.Row([
            ft.Text(f"{r['date'][8:10]}/{r['date'][5:7]}", width=44, color=ft.Colors.GREY),
            ft.Text(nome, expand=True),
            ft.Text(f"{sinal} {format_brl(r['amount_cents'])}", color=cor),
        ])

    def atualizar() -> None:
        rows = repo.list_month(conn, hoje.year, hoje.month)
        t = month_totals(rows)
        saldo.value = f"Saldo do mês: {format_brl(t.balance_cents)}"
        resumo.value = (
            f"Entradas {format_brl(t.income_cents)}   ·   "
            f"Saídas {format_brl(t.expense_cents)}"
        )
        lista.controls = [linha(r) for r in rows] or [
            ft.Text("Nenhum lançamento neste mês.", italic=True, color=ft.Colors.GREY)
        ]
        page.update()

    def abrir_dialog(_) -> None:
        kind = "expense"
        escolhido: dict[str, int | None] = {"expense": None, "income": None}

        valor = ft.TextField(label="Valor (R$)", autofocus=True)
        erro = ft.Text(color=ft.Colors.RED, visible=False)
        chips_label = ft.Text("Categoria (opcional)", size=12, color=ft.Colors.GREY)
        chips = ft.Row(wrap=True, spacing=6)

        def pick(item_id: int) -> None:
            atual = escolhido[kind]
            escolhido[kind] = None if atual == item_id else item_id
            montar_chips()

        def montar_chips() -> None:
            itens = (
                repo.list_categories(conn) if kind == "expense"
                else repo.list_income_sources(conn)
            )
            sel = escolhido[kind]
            chips.controls = [
                ft.Chip(
                    label=ft.Text(it["name"]),
                    selected=(it["id"] == sel),
                    on_click=lambda e, i=it["id"]: pick(i),
                )
                for it in itens
            ]
            chips_label.value = (
                "Categoria (opcional)" if kind == "expense" else "Origem"
            )
            page.update()

        def trocar_tipo(e: ft.ControlEvent) -> None:
            nonlocal kind
            kind = e.control.selected[0] if e.control.selected else "expense"
            erro.visible = False
            montar_chips()

        def salvar(and_new: bool) -> None:
            try:
                cents = parse_brl(valor.value or "")
                if cents <= 0:
                    raise ValueError("O valor deve ser maior que zero.")
            except ValueError as ex:
                erro.value = str(ex)
                erro.visible = True
                page.update()
                return

            if kind == "expense":
                repo.add_expense(
                    conn, date=hoje.isoformat(), amount_cents=cents,
                    category_id=escolhido["expense"],
                )
            else:
                if escolhido["income"] is None:
                    erro.value = "Escolha a origem da receita."
                    erro.visible = True
                    page.update()
                    return
                repo.add_income(
                    conn, date=hoje.isoformat(), amount_cents=cents,
                    income_source_id=escolhido["income"],
                )

            atualizar()
            if and_new:
                valor.value = ""
                escolhido[kind] = None
                erro.visible = False
                montar_chips()
                valor.focus()
            else:
                page.pop_dialog()

        valor.on_submit = lambda e: salvar(and_new=False)
        montar_chips()

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Novo lançamento"),
            content=ft.Column([
                ft.SegmentedButton(
                    segments=[
                        ft.Segment(value="expense", label=ft.Text("Despesa")),
                        ft.Segment(value="income", label=ft.Text("Receita")),
                    ],
                    selected=["expense"],
                    on_change=trocar_tipo,
                ),
                valor,
                chips_label,
                chips,
                erro,
            ], tight=True, width=360, spacing=10),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Salvar e novo", on_click=lambda e: salvar(and_new=True)),
                ft.FilledButton("Salvar", on_click=lambda e: salvar(and_new=False)),
            ],
        ))

    page.add(
        ft.Text(f"{_MESES[hoje.month].capitalize()} {hoje.year}", size=13, color=ft.Colors.GREY),
        saldo,
        resumo,
        ft.Divider(),
        lista,
    )
    page.floating_action_button = ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=abrir_dialog)
    atualizar()


if __name__ == "__main__":
    ft.app(main)
