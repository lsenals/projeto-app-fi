"""App FI — ponto de entrada.

Fatia vertical mínima (passo 2): lançar uma despesa e vê-la na lista do mês,
com o saldo do mês no topo. A tela definitiva (card Hoje, chips de categoria,
teclado próprio) vem no passo 3 — esta versão só prova que a pilha
UI -> core -> repo -> SQLite funciona ponta a ponta.
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
        return ft.Row([
            ft.Text(f"{r['date'][8:10]}/{r['date'][5:7]}", width=44, color=ft.Colors.GREY),
            ft.Text(r["category_name"] or "Sem categoria", expand=True),
            ft.Text(f"− {format_brl(r['amount_cents'])}", color=ft.Colors.RED),
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
        valor = ft.TextField(label="Valor", prefix_text="R$ ", autofocus=True)
        cats = repo.list_categories(conn)
        categoria = ft.Dropdown(
            label="Categoria (opcional)",
            options=[ft.dropdown.Option(key=str(c["id"]), text=c["name"]) for c in cats],
        )
        erro = ft.Text(color=ft.Colors.RED, visible=False)

        def salvar(_) -> None:
            try:
                cents = parse_brl(valor.value or "")
                if cents <= 0:
                    raise ValueError("O valor deve ser maior que zero.")
            except ValueError as ex:
                erro.value = str(ex)
                erro.visible = True
                page.update()
                return
            repo.add_expense(
                conn,
                date=hoje.isoformat(),
                amount_cents=cents,
                category_id=int(categoria.value) if categoria.value else None,
            )
            page.pop_dialog()
            atualizar()

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Nova despesa"),
            content=ft.Column([valor, categoria, erro], tight=True, width=320),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton("Salvar", on_click=salvar),
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
