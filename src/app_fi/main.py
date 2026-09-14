"""App FI — ponto de entrada.

Passo 3: dialog de lançamento (criar e editar), despesa/receita com chips,
"Salvar e novo", Enter salva, filtro numérico, e agora editar/excluir um
lançamento da lista com "Desfazer" via toast. Drawer e telas de
gerenciamento (categorias, recorrentes, config) vêm nos próximos commits.
"""

import datetime as dt

import flet as ft

from app_fi.core.money import format_amount_input, format_brl, parse_brl
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

    def notificar(mensagem: str, desfazer) -> None:
        def ao_clicar_desfazer(_e) -> None:
            desfazer()
            atualizar()

        page.show_dialog(ft.SnackBar(
            content=ft.Text(mensagem),
            action="Desfazer",
            on_action=ao_clicar_desfazer,
            duration=5000,
        ))

    def linha(r) -> ft.Control:
        receita = r["kind"] == "income"
        nome = (r["income_source_name"] if receita else r["category_name"]) or (
            "—" if receita else "Sem categoria"
        )
        sinal = "+" if receita else "−"
        cor = ft.Colors.GREEN if receita else ft.Colors.RED
        return ft.Container(
            content=ft.Row([
                ft.Text(f"{r['date'][8:10]}/{r['date'][5:7]}", width=44, color=ft.Colors.GREY),
                ft.Text(nome, expand=True),
                ft.Text(f"{sinal} {format_brl(r['amount_cents'])}", color=cor),
            ]),
            on_click=lambda e, tx_id=r["id"]: abrir_dialog(None, tx_id=tx_id),
            ink=True,
            border_radius=6,
            padding=4,
        )

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

    def abrir_dialog(_, tx_id: int | None = None) -> None:
        existente = repo.get(conn, tx_id) if tx_id is not None else None
        kind = existente["kind"] if existente else "expense"
        escolhido: dict[str, int | None] = {
            "expense": existente["category_id"] if existente and kind == "expense" else None,
            "income": existente["income_source_id"] if existente and kind == "income" else None,
        }
        # o tipo não muda na edição; ao criar, é sempre para hoje
        data_lancamento = existente["date"] if existente else hoje.isoformat()

        valor = ft.TextField(
            label="Valor (R$)",
            autofocus=True,
            value=format_amount_input(existente["amount_cents"]) if existente else "",
            # bloqueia letras já na digitação: só dígitos, vírgula e ponto entram
            input_filter=ft.InputFilter(regex_string=r"^[0-9.,]*$", allow=True),
        )
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
            chips_label.value = "Categoria (opcional)" if kind == "expense" else "Origem"
            page.update()

        def trocar_tipo(e: ft.ControlEvent) -> None:
            nonlocal kind
            kind = e.control.selected[0] if e.control.selected else "expense"
            erro.visible = False
            montar_chips()

        def fechar() -> None:
            page.on_keyboard_event = None
            page.pop_dialog()

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

            if kind == "income" and escolhido["income"] is None:
                erro.value = "Escolha a origem da receita."
                erro.visible = True
                page.update()
                return

            if existente:
                antes = repo.snapshot(existente)
                if kind == "expense":
                    repo.update_expense(
                        conn, existente["id"], date=data_lancamento, amount_cents=cents,
                        category_id=escolhido["expense"],
                    )
                else:
                    repo.update_income(
                        conn, existente["id"], date=data_lancamento, amount_cents=cents,
                        income_source_id=escolhido["income"],
                    )
                atualizar()
                fechar()
                notificar("Lançamento atualizado.", lambda: repo.restore(conn, antes))
                return

            if kind == "expense":
                novo_id = repo.add_expense(
                    conn, date=data_lancamento, amount_cents=cents,
                    category_id=escolhido["expense"],
                )
            else:
                novo_id = repo.add_income(
                    conn, date=data_lancamento, amount_cents=cents,
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
                fechar()
            notificar("Lançamento adicionado.", lambda i=novo_id: repo.delete(conn, i))

        def excluir(_e) -> None:
            antes = repo.snapshot(existente)
            repo.delete(conn, existente["id"])
            atualizar()
            fechar()
            notificar("Lançamento excluído.", lambda: repo.restore(conn, antes))

        def on_key(e: ft.KeyboardEvent) -> None:
            # Enter salva mesmo quando o foco está num chip (o campo perde o on_submit)
            if e.key == "Enter":
                salvar(and_new=False)

        valor.on_submit = lambda e: salvar(and_new=False)
        page.on_keyboard_event = on_key
        montar_chips()

        tipo = ft.SegmentedButton(
            segments=[
                ft.Segment(value="expense", label=ft.Text("Despesa")),
                ft.Segment(value="income", label=ft.Text("Receita")),
            ],
            selected=[kind],
            disabled=existente is not None,
            on_change=trocar_tipo,
        )

        acoes = (
            [
                ft.TextButton(
                    "Excluir", style=ft.ButtonStyle(color=ft.Colors.RED), on_click=excluir,
                ),
                ft.FilledButton("Salvar", on_click=lambda e: salvar(and_new=False)),
            ]
            if existente else [
                ft.TextButton("Cancelar", on_click=lambda e: fechar()),
                ft.TextButton("Salvar e novo", on_click=lambda e: salvar(and_new=True)),
                ft.FilledButton("Salvar", on_click=lambda e: salvar(and_new=False)),
            ]
        )

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar lançamento" if existente else "Novo lançamento"),
            content=ft.Column(
                [tipo, valor, chips_label, chips, erro], tight=True, width=360, spacing=10,
            ),
            on_dismiss=lambda e: setattr(page, "on_keyboard_event", None),
            actions_alignment=(
                ft.MainAxisAlignment.SPACE_BETWEEN if existente else ft.MainAxisAlignment.END
            ),
            actions=acoes,
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
    ft.run(main)
