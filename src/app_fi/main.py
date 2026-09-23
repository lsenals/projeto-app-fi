"""FinApple — ponto de entrada.

Passos 3-5 fecham a v1 planejada (dialog, drawer+Categorias, Fechamento,
Exportar/backup). Depois: importar fatura de cartão (CSV/XLSX do C6 Bank) com
revisão manual, navegação entre meses, estabelecimento no lançamento manual
(finalmente usa a memória de `payees`) + tela de Recorrentes que modela e
prevê término, sem ainda criar lançamento sozinha — isso é o motor de
materialização, trabalho futuro. Depois disso: UI gamificada (Lançar +
Objetivos) e, agora, a identidade visual FinApple (era "App FI").
"""

import asyncio
import datetime as dt
import os
import sqlite3

import flet as ft

from app_fi.core import goals as goals_core
from app_fi.core.c6_import import ImportedRow, classify_rows
from app_fi.core.dates import previous_month
from app_fi.core.money import format_amount_input, format_brl, parse_brl
from app_fi.core.recurring import forecast as recurring_forecast
from app_fi.core.summary import (
    category_breakdown,
    consecutive_positive_streak,
    income_by_source,
    month_over_month,
    month_totals,
)
from app_fi.data import backup, categories_repo
from app_fi.data import goals_repo
from app_fi.data import import_review
from app_fi.data import payees_repo
from app_fi.data import recurring_repo
from app_fi.data import transactions_repo as repo
from app_fi.data.db import get_db
from app_fi.data.statement_files import read_statement
from app_fi.report.csv_report import render_csv
from app_fi.report.html_report import render_report

_MESES = [
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

# Identidade visual FinApple — abacaxi: a "coroa" remete a vitória/recordes,
# verde e dourado vêm da própria fruta. Ver brand book em Obsidian > 06-Projects.
_COR_PRIMARIA = "#00E676"      # verde esmeralda/limão — destaques, sucesso, botões
_COR_SECUNDARIA = "#FFD600"    # amarelo dourado/neon — ofensiva, PRs, moedas
_COR_TERCIARIA = "#40C4FF"     # azul claro — terceiro anel do Painel de Finanças
_COR_FUNDO = ft.Colors.BLUE_GREY_900       # carbono — fundo do app
_COR_SUPERFICIE = ft.Colors.BLUE_GREY_800  # carbono, um tom mais claro — cards/superfícies

_ICONES_CATEGORIA = {
    "Moradia": ft.Icons.HOME_ROUNDED,
    "Alimentação": ft.Icons.RESTAURANT_ROUNDED,
    "Transporte": ft.Icons.DIRECTIONS_CAR_ROUNDED,
    "Saúde": ft.Icons.FAVORITE_ROUNDED,
    "Lazer": ft.Icons.SPORTS_ESPORTS_ROUNDED,
    "Compras": ft.Icons.SHOPPING_BAG_ROUNDED,
    "Assinaturas": ft.Icons.SUBSCRIPTIONS_ROUNDED,
    "Educação": ft.Icons.SCHOOL_ROUNDED,
    "Outros": ft.Icons.MORE_HORIZ_ROUNDED,
}
_ICONES_RECEITA = {
    "Salário": ft.Icons.PAYMENTS_ROUNDED,
    "Renda extra": ft.Icons.BOLT_ROUNDED,
    "Reembolso": ft.Icons.UNDO_ROUNDED,
    "Outros": ft.Icons.MORE_HORIZ_ROUNDED,
}
_ICONE_PADRAO = ft.Icons.LABEL_ROUNDED

_ICONES_OBJETIVO = {
    "teto_categoria": ft.Icons.SHIELD_ROUNDED,
    "reducao_categoria": ft.Icons.TRENDING_DOWN_ROUNDED,
    "renda_extra": ft.Icons.BOLT_ROUNDED,
    "saldo_positivo_seguido": ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED,
}


def _icone_categoria(nome: str, receita: bool = False):
    return (_ICONES_RECEITA if receita else _ICONES_CATEGORIA).get(nome, _ICONE_PADRAO)


def _formatar_data_br(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"


def _formatar_mes_ano(iso: str) -> str:
    return f"{iso[5:7]}/{iso[0:4]}"


def _anel_progresso(percentual: int, cor: str) -> ft.Control:
    """Um ProgressRing com a porcentagem escrita no centro — Flet não tem
    isso pronto, então empilhamos um Text por cima com ft.Stack."""
    return ft.Stack(
        [
            ft.ProgressRing(
                value=percentual / 100, color=cor,
                bgcolor=ft.Colors.with_opacity(0.15, cor),
                width=64, height=64, stroke_width=6,
            ),
            ft.Container(
                content=ft.Text(f"{percentual}%", size=13, weight=ft.FontWeight.BOLD),
                width=64, height=64, alignment=ft.Alignment.CENTER,
            ),
        ],
        width=64, height=64,
    )


def _card_saldo_meta(titulo: str, valor_cents: int, ratio: float, icone, cor: str) -> ft.Control:
    """Card branco "flutuando" sobre o fundo dark do app — contraste
    deliberado, não é o tema dark padrão do resto da UI (decisão de marca)."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(icone, color=ft.Colors.WHITE, size=16),
                            bgcolor=cor, width=30, height=30, border_radius=100,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(
                            titulo, size=12, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_700,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Text(format_brl(valor_cents), size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                ft.ProgressBar(value=ratio, color=cor, bgcolor=ft.Colors.GREY_200, border_radius=8, bar_height=6),
            ],
            spacing=8,
        ),
        expand=True,
        bgcolor=ft.Colors.WHITE,
        border_radius=15,
        padding=16,
        shadow=ft.BoxShadow(
            blur_radius=16, spread_radius=1,
            color=ft.Colors.with_opacity(0.25, ft.Colors.BLACK),
            offset=ft.Offset(0, 4),
        ),
    )


def _saudacao_mascote() -> ft.Control:
    """Mascote + saudação genérica — fica no topo da Home, fora dos cards
    claros do Painel de Finanças (mesmo fundo dark do resto do app)."""
    return ft.Row(
        [
            ft.Image(
                src="mascote_poupanca.png", width=64, height=64,
                fit=ft.BoxFit.CONTAIN,
            ),
            ft.Text("Bem-vindo!", size=18, weight=ft.FontWeight.BOLD),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _progresso_nivel(nivel: goals_core.NivelProgresso) -> ft.Control:
    """Nível + barra de XP — mesma ideia de `_anel_progresso`/`_card_saldo_meta`:
    um componente, um dado."""
    return ft.Column(
        [
            ft.Row(
                [
                    ft.Text(f"Nível {nivel.nivel}", size=13, color=_COR_SECUNDARIA, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{nivel.xp_no_nivel}/{nivel.xp_por_nivel} XP", size=11, color=ft.Colors.GREY),
                ],
                spacing=8,
            ),
            ft.ProgressBar(
                value=nivel.ratio, color=_COR_SECUNDARIA, bgcolor=ft.Colors.GREY_800,
                border_radius=8, bar_height=8, width=200,
            ),
        ],
        spacing=4,
    )


def cabecalho_boas_vindas(nivel: goals_core.NivelProgresso) -> ft.Control:
    """Compõe mascote+saudação e o progresso de Nível numa linha só."""
    return ft.Row(
        [_saudacao_mascote(), _progresso_nivel(nivel)],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# Painel de Finanças ainda não está ligado a dados reais — valores de exemplo
# do mockup da marca, até existir um cálculo em core/ pra alimentar isso.
_PAINEL_ANEIS = ((0, _COR_PRIMARIA), (20, _COR_SECUNDARIA), (10, _COR_TERCIARIA))
_PAINEL_SALDO_SEMANA_CENTS = 10000
_PAINEL_SALDO_SEMANA_RATIO = 0.35
_PAINEL_META_POUPANCA_CENTS = 60000
_PAINEL_META_POUPANCA_RATIO = 0.6


def painel_financas() -> ft.Control:
    """Painel de Finanças — 3 anéis de progresso + 2 cards (Saldos da Semana,
    Metas de Poupança)."""
    return ft.Column(
        [
            ft.Row(
                [_anel_progresso(p, c) for p, c in _PAINEL_ANEIS],
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            ),
            ft.Row(
                [
                    _card_saldo_meta(
                        "Saldos da Semana", _PAINEL_SALDO_SEMANA_CENTS, _PAINEL_SALDO_SEMANA_RATIO,
                        ft.Icons.ATTACH_MONEY_ROUNDED, _COR_PRIMARIA,
                    ),
                    _card_saldo_meta(
                        "Metas de Poupança", _PAINEL_META_POUPANCA_CENTS, _PAINEL_META_POUPANCA_RATIO,
                        ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, _COR_SECUNDARIA,
                    ),
                ],
                spacing=12,
            ),
        ],
        spacing=16,
    )


def main(page: ft.Page) -> None:
    page.title = "FinApple"
    page.padding = 20
    conn = get_db()
    hoje = dt.date.today()

    tema_salvo = goals_repo.get_setting(conn, "theme_mode", default="dark")
    page.theme_mode = ft.ThemeMode.LIGHT if tema_salvo == "light" else ft.ThemeMode.DARK

    # Identidade visual FinApple: verde primário + dourado secundário sobre
    # fundo carbono no escuro (a base da marca); o claro herda os mesmos
    # destaques pra não perder identidade quando o usuário alterna o tema.
    page.dark_theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=_COR_PRIMARIA, on_primary=ft.Colors.BLACK,
            secondary=_COR_SECUNDARIA, on_secondary=ft.Colors.BLACK,
            surface=_COR_FUNDO, on_surface=ft.Colors.WHITE,
            surface_container=_COR_SUPERFICIE, surface_container_high=_COR_SUPERFICIE,
        ),
        scaffold_bgcolor=_COR_FUNDO,
    )
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=_COR_PRIMARIA, on_primary=ft.Colors.BLACK,
            secondary=_COR_SECUNDARIA, on_secondary=ft.Colors.BLACK,
        ),
    )

    body = ft.Column(expand=True)
    page.add(body)

    def cabecalho_finapple() -> ft.Control:
        """Header/AppBar com a identidade da marca — a "coroa" do abacaxi como
        ícone de conquista, nome em duas cores (Fin verde, Apple dourado)."""
        return ft.Row(
            [
                ft.Icon(ft.Icons.WORKSPACE_PREMIUM_ROUNDED, color=_COR_SECUNDARIA, size=26),
                ft.Row(
                    [
                        ft.Text("Fin", size=20, weight=ft.FontWeight.BOLD, color=_COR_PRIMARIA),
                        ft.Text("Apple", size=20, weight=ft.FontWeight.BOLD, color=_COR_SECUNDARIA),
                    ],
                    spacing=0,
                ),
            ],
            spacing=8,
        )

    # -------------------------------------------------------- navegação (bottom bar)

    def ir_para(indice: int) -> None:
        page.navigation_bar.selected_index = indice
        [montar_home, montar_lancamento_rapido, montar_objetivos][indice]()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME_ROUNDED, label="Home"),
            ft.NavigationBarDestination(icon=ft.Icons.ADD_CIRCLE_ROUNDED, label="Lançar"),
            ft.NavigationBarDestination(icon=ft.Icons.EMOJI_EVENTS_ROUNDED, label="Objetivos"),
        ],
        on_change=lambda e: ir_para(e.control.selected_index),
    )

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

    def confirmar(mensagem: str) -> None:
        """Toast simples, sem Desfazer — para ações que não fazem sentido reverter
        (gerar um relatório, fazer backup)."""
        page.show_dialog(ft.SnackBar(content=ft.Text(mensagem), duration=4000))

    # ---------------------------------------------------------------- menu

    async def abrir_menu(_e) -> None:
        await page.show_drawer()

    async def ir_para_categorias(_e) -> None:
        await page.close_drawer()
        montar_categorias()

    async def ir_para_config(_e) -> None:
        await page.close_drawer()
        montar_config()

    async def ir_para_recorrentes(_e) -> None:
        await page.close_drawer()
        montar_recorrentes()

    def linha_menu(icone, texto, ao_clicar) -> ft.Control:
        return ft.Container(
            content=ft.Row([ft.Icon(icone), ft.Text(texto)], spacing=16),
            on_click=ao_clicar,
            ink=True,
            border_radius=6,
            padding=16,
        )

    page.drawer = ft.NavigationDrawer(controls=[
        ft.Container(height=12),
        linha_menu(ft.Icons.LABEL_OUTLINE, "Categorias", ir_para_categorias),
        linha_menu(ft.Icons.AUTORENEW, "Recorrentes", ir_para_recorrentes),
        linha_menu(ft.Icons.SETTINGS_OUTLINED, "Configurações", ir_para_config),
    ])

    # ---------------------------------------------------------------- home

    # mês que a Home/Fechamento estão mostrando — separado de `hoje` (a data
    # real), que segue ancorando o card "Hoje" e a data padrão de lançamento
    mes_visualizado = {"ano": hoje.year, "mes": hoje.month}

    def mudar_mes(delta: int) -> None:
        ano, mes = mes_visualizado["ano"], mes_visualizado["mes"] + delta
        if mes < 1:
            ano, mes = ano - 1, 12
        elif mes > 12:
            ano, mes = ano + 1, 1
        mes_visualizado["ano"], mes_visualizado["mes"] = ano, mes
        atualizar()

    saldo = ft.Text(size=22, weight=ft.FontWeight.BOLD)
    resumo = ft.Text(size=13, color=ft.Colors.GREY)
    mes_titulo = ft.Text(size=13, color=ft.Colors.GREY)
    lista = ft.ListView(expand=True, spacing=2)

    def cabecalho_lista() -> ft.Control:
        return ft.Container(
            content=ft.Row([
                ft.Text("Data", width=44, size=11, color=ft.Colors.GREY),
                ft.Text("Categoria", width=110, size=11, color=ft.Colors.GREY),
                ft.Text("Descrição", expand=True, size=11, color=ft.Colors.GREY),
                ft.Text("Valor", size=11, color=ft.Colors.GREY),
            ]),
            padding=ft.Padding(left=4, right=4, top=0, bottom=0),
        )

    def linha(r) -> ft.Control:
        receita = r["kind"] == "income"
        categoria = r["income_source_name"] if receita else (r["category_name"] or "Sem categoria")
        descricao = r["payee_name"] or "—"
        sinal = "+" if receita else "−"
        cor = ft.Colors.GREEN if receita else ft.Colors.RED
        return ft.Container(
            content=ft.Row([
                ft.Text(f"{r['date'][8:10]}/{r['date'][5:7]}", width=44, color=ft.Colors.GREY),
                ft.Text(categoria, width=110, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(
                    descricao, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                    color=ft.Colors.GREY if descricao == "—" else None,
                ),
                ft.Text(f"{sinal} {format_brl(r['amount_cents'])}", color=cor),
            ]),
            on_click=lambda e, tx_id=r["id"]: abrir_dialog_lancamento(tx_id=tx_id),
            ink=True,
            border_radius=6,
            padding=4,
        )

    def atualizar() -> None:
        ano, mes = mes_visualizado["ano"], mes_visualizado["mes"]
        rows = repo.list_month(conn, ano, mes)
        t = month_totals(rows)
        mes_titulo.value = f"{_MESES[mes].capitalize()} {ano}"
        saldo.value = f"Saldo do mês: {format_brl(t.balance_cents)}"
        resumo.value = (
            f"Entradas {format_brl(t.income_cents)}   ·   "
            f"Saídas {format_brl(t.expense_cents)}"
        )
        lista.controls = [linha(r) for r in rows] or [
            ft.Text("Nenhum lançamento neste mês.", italic=True, color=ft.Colors.GREY)
        ]
        page.update()

    def montar_home() -> None:
        page.navigation_bar.selected_index = 0
        page.appbar = ft.AppBar(
            leading=ft.IconButton(icon=ft.Icons.MENU, on_click=abrir_menu),
            title=cabecalho_finapple(),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.UPLOAD_FILE,
                    tooltip="Importar fatura (CSV/XLSX)",
                    on_click=abrir_importacao,
                ),
                ft.IconButton(
                    icon=ft.Icons.SUMMARIZE,
                    tooltip="Fechamento do mês",
                    on_click=lambda e: montar_fechamento(),
                ),
            ],
        )
        nivel = goals_core.calcular_nivel(goals_repo.count_achieved(conn))
        body.controls = [
            cabecalho_boas_vindas(nivel),
            painel_financas(),
            ft.Divider(),
            ft.Row([
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT, icon_size=18, tooltip="Mês anterior",
                    on_click=lambda e: mudar_mes(-1),
                ),
                mes_titulo,
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT, icon_size=18, tooltip="Próximo mês",
                    on_click=lambda e: mudar_mes(1),
                ),
            ], spacing=0),
            saldo,
            resumo,
            ft.Divider(),
            cabecalho_lista(),
            lista,
        ]
        page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD, bgcolor=_COR_PRIMARIA, on_click=lambda e: ir_para(1),
        )
        atualizar()

    def abrir_dialog_lancamento(tx_id: int | None = None) -> None:
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
        estabelecimento = ft.TextField(
            label="Estabelecimento (opcional)",
            value=(existente["payee_name"] or "") if existente else "",
        )
        erro = ft.Text(color=ft.Colors.RED, visible=False)
        chips_label = ft.Text("Categoria (opcional)", size=12, color=ft.Colors.GREY)
        chips = ft.Row(wrap=True, spacing=6)

        def sugerir_pela_memoria(_e) -> None:
            # ao sair do campo: se já conhecemos esse estabelecimento e nenhuma
            # categoria foi escolhida ainda, pré-seleciona pelo que aprendemos
            nome = (estabelecimento.value or "").strip()
            if not nome or kind != "expense" or escolhido["expense"] is not None:
                return
            sugestao = payees_repo.find_default_category_id(conn, nome)
            if sugestao is not None:
                escolhido["expense"] = sugestao
                montar_chips()

        estabelecimento.on_blur = sugerir_pela_memoria

        def pick(item_id: int) -> None:
            atual = escolhido[kind]
            escolhido[kind] = None if atual == item_id else item_id
            montar_chips()

        def montar_chips() -> None:
            itens = (
                categories_repo.list_active(conn) if kind == "expense"
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

            nome_estabelecimento = (estabelecimento.value or "").strip()
            payee_id = payees_repo.get_or_create(conn, nome_estabelecimento) if nome_estabelecimento else None
            if payee_id is not None and kind == "expense":
                payees_repo.set_default_category(conn, payee_id, escolhido["expense"])

            if existente:
                antes = repo.snapshot(existente)
                if kind == "expense":
                    repo.update_expense(
                        conn, existente["id"], date=data_lancamento, amount_cents=cents,
                        category_id=escolhido["expense"], payee_id=payee_id,
                    )
                else:
                    repo.update_income(
                        conn, existente["id"], date=data_lancamento, amount_cents=cents,
                        income_source_id=escolhido["income"], payee_id=payee_id,
                    )
                atualizar()
                fechar()
                notificar("Lançamento atualizado.", lambda: repo.restore(conn, antes))
                return

            if kind == "expense":
                novo_id = repo.add_expense(
                    conn, date=data_lancamento, amount_cents=cents,
                    category_id=escolhido["expense"], payee_id=payee_id,
                )
            else:
                novo_id = repo.add_income(
                    conn, date=data_lancamento, amount_cents=cents,
                    income_source_id=escolhido["income"], payee_id=payee_id,
                )

            atualizar()
            if and_new:
                valor.value = ""
                estabelecimento.value = ""
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
                [tipo, valor, estabelecimento, chips_label, chips, erro], tight=True, width=360, spacing=10,
            ),
            on_dismiss=lambda e: setattr(page, "on_keyboard_event", None),
            actions_alignment=(
                ft.MainAxisAlignment.SPACE_BETWEEN if existente else ft.MainAxisAlignment.END
            ),
            actions=acoes,
        ))

    # ------------------------------------------------------------ importação

    class _ItemImportado:
        __slots__ = ("linha", "incluir", "category_id", "duplicata")

        def __init__(self, linha: ImportedRow, category_id: int | None, duplicata: bool):
            self.linha = linha
            self.incluir = True
            self.category_id = category_id
            self.duplicata = duplicata

    # FilePicker é um "Service" (não um controle visual) — se registra
    # sozinho na página ao ser criado. Colocá-lo em page.overlay (API antiga)
    # faz o Flutter tentar desenhá-lo como widget e falhar com "Unknown
    # control: FilePicker".
    file_picker = ft.FilePicker()

    itens_importacao: list[_ItemImportado] = []
    importacao_lista = ft.ListView(expand=True, spacing=6)
    importacao_resumo = ft.Text(size=13, color=ft.Colors.GREY)

    def _mostrar_pop_up(titulo: str, icone, cor, linhas: list[ft.Control]) -> None:
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(icone, color=cor), ft.Text(titulo)], spacing=8),
            content=ft.Column(linhas, tight=True, spacing=6, width=380),
            actions=[ft.FilledButton("OK", on_click=lambda e: page.pop_dialog())],
        ))

    async def abrir_importacao(_e) -> None:
        selecionados = await file_picker.pick_files(
            dialog_title="Selecionar fatura (CSV ou XLSX)",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["csv", "xlsx"],
        )
        if not selecionados or not selecionados[0].path:
            return
        caminho, nome_arquivo = selecionados[0].path, selecionados[0].name

        try:
            linhas_arquivo = read_statement(caminho)
            pre_lancamentos = classify_rows(linhas_arquivo)
        except Exception as ex:
            _mostrar_pop_up(
                "Não consegui importar", ft.Icons.ERROR_ROUNDED, ft.Colors.RED,
                [
                    ft.Text(f"Arquivo: {nome_arquivo}"),
                    ft.Text(f"Motivo: {ex}" if str(ex) else f"Erro: {type(ex).__name__}"),
                    ft.Text(
                        "Confira se é uma fatura do C6 em CSV ou XLSX, com o cabeçalho "
                        "de colunas original do banco.",
                        size=12, color=ft.Colors.GREY,
                    ),
                ],
            )
            return

        if not pre_lancamentos:
            _mostrar_pop_up(
                "Nada para importar", ft.Icons.INFO_ROUNDED, ft.Colors.GREY,
                [
                    ft.Text(f"Arquivo: {nome_arquivo}"),
                    ft.Text(f"Lemos {len(linhas_arquivo)} linha(s), mas nenhuma virou lançamento."),
                    ft.Text(
                        "Pode ser uma fatura só com pagamentos (não entram como gasto), "
                        "ou o arquivo não é do formato esperado.",
                        size=12, color=ft.Colors.GREY,
                    ),
                ],
            )
            return

        itens_importacao.clear()
        for linha in pre_lancamentos:
            itens_importacao.append(_ItemImportado(
                linha,
                category_id=import_review.suggest_category_id(conn, linha),
                duplicata=import_review.is_probable_duplicate(conn, linha),
            ))

        montar_revisao_importacao()

    def _atualizar_resumo_importacao() -> None:
        n = sum(1 for i in itens_importacao if i.incluir)
        importacao_resumo.value = f"{n} de {len(itens_importacao)} selecionados"
        page.update()

    def _linha_importacao(item: _ItemImportado) -> ft.Control:
        linha = item.linha
        receita = linha.kind == "income"
        sinal = "+" if receita else "−"
        cor = ft.Colors.GREEN if receita else ft.Colors.RED

        def alternar_incluir(e: ft.ControlEvent) -> None:
            item.incluir = e.control.value
            _atualizar_resumo_importacao()

        if receita:
            campo_categoria: ft.Control = ft.Text(
                f"Receita: {linha.income_source_name}", size=12, color=ft.Colors.GREY, width=160,
            )
        else:
            def mudar_categoria(e: ft.ControlEvent) -> None:
                item.category_id = int(e.control.value) if e.control.value else None

            campo_categoria = ft.Dropdown(
                value=str(item.category_id) if item.category_id else None,
                hint_text="Sem categoria",
                dense=True,
                width=160,
                options=[
                    ft.dropdown.Option(key=str(c["id"]), text=c["name"])
                    for c in categories_repo.list_active(conn)
                ],
                on_select=mudar_categoria,
            )

        detalhe = ft.Column([
            ft.Text(linha.description, size=13),
            ft.Text("Possível duplicata", size=11, color=ft.Colors.ORANGE) if item.duplicata else ft.Container(),
        ], expand=True, spacing=0)

        return ft.Row([
            ft.Checkbox(value=item.incluir, on_change=alternar_incluir),
            ft.Text(f"{linha.date[8:10]}/{linha.date[5:7]}", width=44, color=ft.Colors.GREY),
            detalhe,
            campo_categoria,
            ft.Text(f"{sinal} {format_brl(linha.amount_cents)}", color=cor, width=100),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def confirmar_importacao(_e) -> None:
        fontes = {s["name"]: s["id"] for s in repo.list_income_sources(conn)}
        gravados = despesas = receitas = ignorados = 0
        total_cents = 0
        meses: set[str] = set()
        for item in itens_importacao:
            if not item.incluir:
                ignorados += 1
                continue
            if item.linha.kind == "expense":
                import_review.confirm_expense(conn, item.linha, item.category_id)
                despesas += 1
            else:
                import_review.confirm_income(conn, item.linha, fontes[item.linha.income_source_name])
                receitas += 1
            gravados += 1
            total_cents += item.linha.amount_cents
            meses.add(item.linha.date[:7])
        montar_home()

        if gravados == 0:
            _mostrar_pop_up(
                "Nada foi gravado", ft.Icons.INFO_ROUNDED, ft.Colors.GREY,
                [ft.Text("Todos os lançamentos da revisão estavam desmarcados.")],
            )
            return

        linhas_meses = ", ".join(
            f"{_MESES[int(m[5:7])].capitalize()}/{m[:4]}" for m in sorted(meses)
        )
        detalhes = [
            ft.Text(f"{gravados} lançamento(s) gravado(s) — {despesas} despesa(s), {receitas} receita(s)."),
            ft.Text(f"Mês(es): {linhas_meses}."),
            ft.Text(f"Total movimentado: {format_brl(total_cents)}."),
        ]
        if ignorados:
            detalhes.append(ft.Text(
                f"{ignorados} linha(s) deixada(s) de fora (desmarcada(s) na revisão).",
                size=12, color=ft.Colors.GREY,
            ))
        _mostrar_pop_up("Fatura importada", ft.Icons.CHECK_CIRCLE_ROUNDED, _COR_PRIMARIA, detalhes)

    def montar_revisao_importacao() -> None:
        page.appbar = ft.AppBar(
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: montar_home()),
            title=ft.Text("Revisar importação"),
        )
        page.floating_action_button = None
        importacao_lista.controls = [_linha_importacao(item) for item in itens_importacao]
        body.controls = [
            importacao_resumo,
            ft.Divider(),
            importacao_lista,
            ft.Row([
                ft.TextButton("Cancelar", on_click=lambda e: montar_home()),
                ft.FilledButton("Confirmar importação", on_click=confirmar_importacao),
            ], alignment=ft.MainAxisAlignment.END),
        ]
        _atualizar_resumo_importacao()

    # ------------------------------------------------------------- fechamento

    fechamento_conteudo = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=18)

    def _barra(nome: str, cents: int, maximo: int, cor) -> ft.Control:
        return ft.Column([
            ft.Row([ft.Text(nome, expand=True), ft.Text(format_brl(cents))]),
            ft.ProgressBar(
                value=(cents / maximo) if maximo else 0,
                bar_height=6, color=cor, bgcolor=ft.Colors.GREY_200,
            ),
        ], spacing=2)

    def _dados_fechamento():
        """Os mesmos dados alimentam a tela e os dois exports — uma fonte só.
        Segue o mês que a Home está mostrando, não necessariamente hoje."""
        ano, mes = mes_visualizado["ano"], mes_visualizado["mes"]
        rows = repo.list_month(conn, ano, mes)
        ano_ant, mes_ant = previous_month(ano, mes)
        rows_anterior = repo.list_month(conn, ano_ant, mes_ant)
        return {
            "ano": ano, "mes": mes,
            "rows": rows,
            "t": month_totals(rows),
            "ano_ant": ano_ant,
            "mes_ant": mes_ant,
            "despesas": category_breakdown(rows),
            "receitas": income_by_source(rows),
            "comparacao": month_over_month(rows, rows_anterior),
        }

    def exportar_html(_e) -> None:
        d = _dados_fechamento()
        html = render_report(
            mes_nome=_MESES[d["mes"]].capitalize(),
            ano=d["ano"],
            mes_anterior_nome=_MESES[d["mes_ant"]].capitalize(),
            entradas_cents=d["t"].income_cents,
            saidas_cents=d["t"].expense_cents,
            saldo_cents=d["t"].balance_cents,
            despesas=d["despesas"],
            receitas=d["receitas"],
            comparacao=d["comparacao"],
            gerado_em=dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
        )
        path = backup.write_html_report(html, d["ano"], d["mes"])
        if page.platform == ft.PagePlatform.WINDOWS:
            try:
                os.startfile(path)  # abre no navegador padrão, como a spec pede
            except OSError:
                pass  # sem programa associado a .html; o arquivo já está salvo
        else:
            # fora do Windows não há "abrir no programa padrão" via os.startfile;
            # launch_url deixa a plataforma decidir como abrir o arquivo local.
            page.launch_url(path.as_uri())
        confirmar(f"Relatório salvo em {path}")

    def exportar_csv(_e) -> None:
        d = _dados_fechamento()
        csv_text = render_csv(d["rows"])
        path = backup.write_csv_report(csv_text, d["ano"], d["mes"])
        confirmar(f"CSV salvo em {path}")

    def atualizar_fechamento() -> None:
        d = _dados_fechamento()
        mes, t, mes_ant = d["mes"], d["t"], d["mes_ant"]
        despesas, receitas, comparacao = d["despesas"], d["receitas"], d["comparacao"]

        max_despesa = max((c for _, c in despesas), default=0)
        max_receita = max((c for _, c in receitas), default=0)

        resumo_row = ft.Row([
            ft.Column([
                ft.Text("Entradas", size=12, color=ft.Colors.GREY),
                ft.Text(format_brl(t.income_cents), size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
            ]),
            ft.Column([
                ft.Text("Saídas", size=12, color=ft.Colors.GREY),
                ft.Text(format_brl(t.expense_cents), size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
            ]),
            ft.Column([
                ft.Text("Saldo do mês", size=12, color=ft.Colors.GREY),
                ft.Text(format_brl(t.balance_cents), size=18, weight=ft.FontWeight.BOLD),
            ]),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        linhas_despesa = [_barra(nome, c, max_despesa, ft.Colors.RED) for nome, c in despesas] or [
            ft.Text("Nenhuma despesa neste mês.", italic=True, color=ft.Colors.GREY)
        ]
        linhas_receita = [_barra(nome, c, max_receita, ft.Colors.GREEN) for nome, c in receitas] or [
            ft.Text("Nenhuma receita neste mês.", italic=True, color=ft.Colors.GREY)
        ]

        if comparacao:
            tabela: ft.Control = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Categoria")),
                    ft.DataColumn(ft.Text(_MESES[mes][:3].capitalize()), numeric=True),
                    ft.DataColumn(ft.Text(_MESES[mes_ant][:3].capitalize()), numeric=True),
                    ft.DataColumn(ft.Text("Variação"), numeric=True),
                ],
                rows=[
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(r.category)),
                        ft.DataCell(ft.Text(format_brl(r.current_cents))),
                        ft.DataCell(ft.Text(format_brl(r.previous_cents))),
                        ft.DataCell(ft.Text(
                            "—" if r.delta_pct is None else f"{r.delta_pct:+.0f}%",
                            color=(
                                ft.Colors.GREY if r.delta_pct is None or r.delta_pct == 0
                                else ft.Colors.RED if r.delta_pct > 0
                                else ft.Colors.GREEN
                            ),
                        )),
                    ])
                    for r in comparacao
                ],
            )
        else:
            tabela = ft.Text("Sem dados suficientes para comparar.", italic=True, color=ft.Colors.GREY)

        fechamento_conteudo.controls = [
            resumo_row,
            ft.Divider(),
            ft.Text("Gastos por categoria", size=13, weight=ft.FontWeight.BOLD),
            ft.Column(linhas_despesa, spacing=10),
            ft.Divider(),
            ft.Text("Entradas por origem", size=13, weight=ft.FontWeight.BOLD),
            ft.Column(linhas_receita, spacing=10),
            ft.Divider(),
            ft.Text(f"Comparado a {_MESES[mes_ant]}", size=13, weight=ft.FontWeight.BOLD),
            tabela,
        ]
        page.update()

    def montar_fechamento() -> None:
        ano, mes = mes_visualizado["ano"], mes_visualizado["mes"]
        page.appbar = ft.AppBar(
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: montar_home()),
            title=ft.Text(f"Fechamento — {_MESES[mes].capitalize()} {ano}"),
            actions=[
                ft.IconButton(icon=ft.Icons.DOWNLOAD, tooltip="Exportar HTML", on_click=exportar_html),
                ft.IconButton(icon=ft.Icons.TABLE_CHART, tooltip="Exportar CSV", on_click=exportar_csv),
            ],
        )
        page.floating_action_button = None
        body.controls = [fechamento_conteudo]
        atualizar_fechamento()

    # ---------------------------------------------------------- categorias

    categorias_lista = ft.ListView(expand=True, spacing=2)

    def linha_categoria(c) -> ft.Control:
        return ft.Container(
            content=ft.Row([
                ft.Text(c["name"], expand=True),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.GREY, size=18),
            ]),
            on_click=lambda e, cat_id=c["id"]: abrir_dialog_categoria(cat_id),
            ink=True,
            border_radius=6,
            padding=10,
        )

    def atualizar_categorias() -> None:
        itens = categories_repo.list_active(conn)
        categorias_lista.controls = [linha_categoria(c) for c in itens] or [
            ft.Text("Nenhuma categoria cadastrada.", italic=True, color=ft.Colors.GREY)
        ]
        page.update()

    def montar_categorias() -> None:
        page.appbar = ft.AppBar(
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: montar_home()),
            title=ft.Text("Categorias"),
        )
        body.controls = [categorias_lista]
        page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD, on_click=lambda e: abrir_dialog_categoria(),
        )
        atualizar_categorias()

    def abrir_dialog_categoria(category_id: int | None = None) -> None:
        existente = next(
            (c for c in categories_repo.list_active(conn) if c["id"] == category_id), None,
        ) if category_id is not None else None

        nome = ft.TextField(label="Nome", autofocus=True, value=existente["name"] if existente else "")
        erro = ft.Text(color=ft.Colors.RED, visible=False)

        def fechar() -> None:
            page.pop_dialog()

        def salvar(_e) -> None:
            try:
                if existente:
                    categories_repo.rename(conn, existente["id"], nome.value or "")
                else:
                    categories_repo.add(conn, nome.value or "")
            except ValueError as ex:
                erro.value = str(ex)
                erro.visible = True
                page.update()
                return
            except sqlite3.IntegrityError:
                erro.value = "Já existe uma categoria com esse nome."
                erro.visible = True
                page.update()
                return
            fechar()
            atualizar_categorias()

        def arquivar(_e) -> None:
            categories_repo.archive(conn, existente["id"])
            fechar()
            atualizar_categorias()

        nome.on_submit = salvar

        acoes = (
            [
                ft.TextButton(
                    "Arquivar", style=ft.ButtonStyle(color=ft.Colors.RED), on_click=arquivar,
                ),
                ft.FilledButton("Salvar", on_click=salvar),
            ]
            if existente else [
                ft.TextButton("Cancelar", on_click=lambda e: fechar()),
                ft.FilledButton("Salvar", on_click=salvar),
            ]
        )

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar categoria" if existente else "Nova categoria"),
            content=ft.Column([nome, erro], tight=True, width=320),
            actions_alignment=(
                ft.MainAxisAlignment.SPACE_BETWEEN if existente else ft.MainAxisAlignment.END
            ),
            actions=acoes,
        ))

    # ----------------------------------------------------------- recorrentes

    recorrentes_lista = ft.ListView(expand=True, spacing=2)

    def linha_recorrencia(r) -> ft.Control:
        f = recurring_forecast(
            r["next_date"], r["interval_unit"], r["interval_count"],
            r["total_installments"], r["current_installment"],
        )
        detalhe = (
            "Sem fim definido" if f.remaining_installments is None
            else f"Faltam {f.remaining_installments} · termina {_formatar_mes_ano(f.predicted_end_date)}"
        )
        receita = r["kind"] == "income"
        sinal = "+" if receita else "−"
        cor = ft.Colors.GREEN if receita else ft.Colors.RED
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(r["label"], size=13),
                    ft.Text(
                        f"Próxima: {_formatar_data_br(r['next_date'])} · {detalhe}",
                        size=11, color=ft.Colors.GREY,
                    ),
                ], expand=True, spacing=0),
                ft.Text(f"{sinal} {format_brl(r['expected_amount_cents'])}", color=cor),
            ]),
            on_click=lambda e, rid=r["id"]: abrir_dialog_recorrencia(rid),
            ink=True, border_radius=6, padding=8,
        )

    def atualizar_recorrentes() -> None:
        itens = recurring_repo.list_active(conn)
        recorrentes_lista.controls = [linha_recorrencia(r) for r in itens] or [
            ft.Text("Nenhuma recorrência cadastrada.", italic=True, color=ft.Colors.GREY)
        ]
        page.update()

    def montar_recorrentes() -> None:
        page.appbar = ft.AppBar(
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: montar_home()),
            title=ft.Text("Recorrentes"),
        )
        page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD, on_click=lambda e: abrir_dialog_recorrencia(),
        )
        body.controls = [recorrentes_lista]
        atualizar_recorrentes()

    def abrir_dialog_recorrencia(recurring_id: int | None = None) -> None:
        existente = recurring_repo.get(conn, recurring_id) if recurring_id is not None else None
        kind = existente["kind"] if existente else "expense"
        escolhido: dict[str, int | None] = {
            "expense": existente["category_id"] if existente and kind == "expense" else None,
            "income": existente["income_source_id"] if existente and kind == "income" else None,
        }
        proxima_data = {"iso": existente["next_date"] if existente else hoje.isoformat()}

        estabelecimento = ft.TextField(
            label="Descrição", autofocus=True,
            value=existente["label"] if existente else "",
        )
        valor = ft.TextField(
            label="Valor esperado (R$)",
            value=format_amount_input(existente["expected_amount_cents"]) if existente else "",
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
                categories_repo.list_active(conn) if kind == "expense"
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

        tipo = ft.SegmentedButton(
            segments=[
                ft.Segment(value="expense", label=ft.Text("Despesa")),
                ft.Segment(value="income", label=ft.Text("Receita")),
            ],
            selected=[kind],
            on_change=trocar_tipo,
        )

        unidade = ft.SegmentedButton(
            segments=[
                ft.Segment(value="month", label=ft.Text("Mensal")),
                ft.Segment(value="week", label=ft.Text("Semanal")),
            ],
            selected=[existente["interval_unit"] if existente else "month"],
            on_change=lambda e: atualizar_previsao(),
        )

        data_botao = ft.TextButton(f"Próxima cobrança: {_formatar_data_br(proxima_data['iso'])}")

        def ao_escolher_data(e: ft.ControlEvent) -> None:
            # a data escolhida vem em e.data (documentado no DatePicker), não
            # em e.control.value — o server nunca sincroniza .value sozinho
            valor = e.data if e.data is not None else e.control.value
            if valor is None:
                return
            if isinstance(valor, str):
                iso = valor[:10]
            elif callable(getattr(valor, "date", None)):
                iso = valor.date().isoformat()
            else:
                iso = valor.isoformat()
            proxima_data["iso"] = iso
            # TextButton não tem atributo .text — o conteúdo mora em .content
            data_botao.content = f"Próxima cobrança: {_formatar_data_br(iso)}"
            atualizar_previsao()
            page.update()

        date_picker = ft.DatePicker(
            value=dt.date.fromisoformat(proxima_data["iso"]),
            first_date=dt.date(2000, 1, 1),
            last_date=dt.date(2100, 12, 31),
            on_change=ao_escolher_data,
        )
        data_botao.on_click = lambda e: page.show_dialog(date_picker)

        tem_fim = ft.Switch(
            label="Tem fim previsto (parcelado)",
            value=bool(existente and existente["total_installments"] is not None),
        )
        total_parcelas = ft.TextField(
            label="Total de parcelas",
            value=str(existente["total_installments"]) if existente and existente["total_installments"] else "",
            input_filter=ft.InputFilter(regex_string=r"^[0-9]*$", allow=True),
            visible=tem_fim.value,
        )
        parcela_atual = ft.TextField(
            label="Parcela atual (1 = ainda não cobrou nenhuma)",
            value=str(existente["current_installment"]) if existente else "1",
            input_filter=ft.InputFilter(regex_string=r"^[0-9]*$", allow=True),
            visible=tem_fim.value,
        )
        previsao_texto = ft.Text(size=12, color=ft.Colors.GREY)

        def atualizar_previsao() -> None:
            if not tem_fim.value:
                previsao_texto.value = "Sem fim definido."
                page.update()
                return
            try:
                total = int(total_parcelas.value or 0)
                atual = int(parcela_atual.value or 1)
            except ValueError:
                previsao_texto.value = ""
                page.update()
                return
            if total <= 0:
                previsao_texto.value = ""
                page.update()
                return
            unidade_valor = unidade.selected[0] if unidade.selected else "month"
            f = recurring_forecast(proxima_data["iso"], unidade_valor, 1, total, atual)
            previsao_texto.value = (
                f"Faltam {f.remaining_installments} parcela(s) · "
                f"termina em {_formatar_mes_ano(f.predicted_end_date)}"
            )
            page.update()

        def alternar_tem_fim(e: ft.ControlEvent) -> None:
            total_parcelas.visible = tem_fim.value
            parcela_atual.visible = tem_fim.value
            atualizar_previsao()

        tem_fim.on_change = alternar_tem_fim
        total_parcelas.on_change = lambda e: atualizar_previsao()
        parcela_atual.on_change = lambda e: atualizar_previsao()

        def fechar() -> None:
            page.pop_dialog()

        def salvar(_e) -> None:
            nome = (estabelecimento.value or "").strip()
            if not nome:
                erro.value = "Informe uma descrição."
                erro.visible = True
                page.update()
                return
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

            total = None
            atual = 1
            if tem_fim.value:
                try:
                    total = int(total_parcelas.value or 0)
                    atual = int(parcela_atual.value or 1)
                    if total <= 0 or atual <= 0:
                        raise ValueError
                except ValueError:
                    erro.value = "Informe o total de parcelas e a parcela atual corretamente."
                    erro.visible = True
                    page.update()
                    return

            unidade_valor = unidade.selected[0] if unidade.selected else "month"
            kwargs = dict(
                label=nome, kind=kind, expected_amount_cents=cents,
                interval_unit=unidade_valor, next_date=proxima_data["iso"],
                category_id=escolhido["expense"] if kind == "expense" else None,
                income_source_id=escolhido["income"] if kind == "income" else None,
                total_installments=total, current_installment=atual,
            )
            if existente:
                recurring_repo.update(conn, existente["id"], **kwargs)
            else:
                recurring_repo.add(conn, **kwargs)
            fechar()
            atualizar_recorrentes()
            confirmar("Recorrência salva.")

        def desativar(_e) -> None:
            recurring_repo.deactivate(conn, existente["id"])
            fechar()
            atualizar_recorrentes()
            confirmar("Recorrência desativada.")

        montar_chips()
        atualizar_previsao()

        acoes = (
            [
                ft.TextButton(
                    "Desativar", style=ft.ButtonStyle(color=ft.Colors.RED), on_click=desativar,
                ),
                ft.FilledButton("Salvar", on_click=salvar),
            ]
            if existente else [
                ft.TextButton("Cancelar", on_click=lambda e: fechar()),
                ft.FilledButton("Salvar", on_click=salvar),
            ]
        )

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar recorrência" if existente else "Nova recorrência"),
            content=ft.Column([
                tipo, estabelecimento, valor, chips_label, chips,
                unidade, data_botao, tem_fim, total_parcelas, parcela_atual,
                previsao_texto, erro,
            ], tight=True, width=360, spacing=10, scroll=ft.ScrollMode.AUTO, height=420),
            actions_alignment=(
                ft.MainAxisAlignment.SPACE_BETWEEN if existente else ft.MainAxisAlignment.END
            ),
            actions=acoes,
        ))

    # ----------------------------------------------------------- configurações

    ultimo_backup_texto = ft.Text("Nenhum backup feito ainda nesta sessão.", color=ft.Colors.GREY)

    def fazer_backup(_e) -> None:
        path = backup.backup_database()
        ultimo_backup_texto.value = f"Último backup: {path}"
        ultimo_backup_texto.color = None
        page.update()
        confirmar("Backup criado.")

    # ---------------------------------------------------------- lançamento rápido

    def montar_lancamento_rapido() -> None:
        page.navigation_bar.selected_index = 1
        page.appbar = ft.AppBar(title=ft.Text("Lançar"))
        page.floating_action_button = None

        kind = {"valor": "expense"}
        escolhido = {"valor": None}

        valor = ft.TextField(
            value="", autofocus=True, text_align=ft.TextAlign.CENTER,
            text_style=ft.TextStyle(size=40, weight=ft.FontWeight.BOLD),
            border=ft.InputBorder.NONE, hint_text="0,00",
            input_filter=ft.InputFilter(regex_string=r"^[0-9.,]*$", allow=True),
        )
        estabelecimento = ft.TextField(label="Estabelecimento (opcional)", dense=True)
        grid = ft.Row(wrap=True, spacing=10, run_spacing=10)
        erro = ft.Text(color=ft.Colors.RED, visible=False, size=12)
        texto_botao = ft.Text("Registrar", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK)
        botao_confirmar = ft.Container(
            content=texto_botao,
            bgcolor=_COR_PRIMARIA,
            border_radius=100,
            padding=ft.Padding(left=24, right=24, top=16, bottom=16),
            alignment=ft.Alignment.CENTER,
            animate=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
            ink=True,
        )

        itens_atuais: dict[str, list] = {"valor": []}

        def item_icone(item_id: int, nome: str, icone, arrastando: bool = False) -> ft.Control:
            selecionado = escolhido["valor"] == item_id
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(icone, size=26, color=ft.Colors.BLACK if selecionado else ft.Colors.WHITE),
                        ft.Text(
                            nome, size=10, color=ft.Colors.BLACK if selecionado else ft.Colors.WHITE,
                            text_align=ft.TextAlign.CENTER, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, tight=True,
                ),
                width=74, height=74,
                bgcolor=_COR_PRIMARIA if selecionado else _COR_SUPERFICIE,
                border_radius=18,
                alignment=ft.Alignment.CENTER,
                animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
                opacity=0.35 if arrastando else 1,
                ink=True,
                on_click=None if arrastando else (lambda e, i=item_id: selecionar(i)),
            )

        def ao_soltar(e: ft.DragTargetEvent) -> None:
            origem_id, destino_id = e.src.data, e.control.data
            if origem_id == destino_id:
                return
            lista = itens_atuais["valor"]
            ids = [it["id"] for it in lista]
            lista.insert(ids.index(destino_id), lista.pop(ids.index(origem_id)))
            if kind["valor"] == "expense":
                categories_repo.reorder(conn, [it["id"] for it in lista])
            else:
                repo.reorder_income_sources(conn, [it["id"] for it in lista])
            montar_grid()

        def item_arrastavel(it, receita: bool) -> ft.Control:
            icone = _icone_categoria(it["name"], receita=receita)
            return ft.DragTarget(
                group="itens_lancamento",
                data=it["id"],
                on_accept=ao_soltar,
                content=ft.Draggable(
                    group="itens_lancamento",
                    data=it["id"],
                    content=item_icone(it["id"], it["name"], icone),
                    content_feedback=ft.Container(opacity=0.85, content=item_icone(it["id"], it["name"], icone)),
                    content_when_dragging=item_icone(it["id"], it["name"], icone, arrastando=True),
                ),
            )

        def montar_grid() -> None:
            itens = (
                categories_repo.list_active(conn) if kind["valor"] == "expense"
                else repo.list_income_sources(conn)
            )
            itens_atuais["valor"] = list(itens)
            grid.controls = [item_arrastavel(it, receita=kind["valor"] == "income") for it in itens]
            page.update()

        def selecionar(item_id: int) -> None:
            escolhido["valor"] = None if escolhido["valor"] == item_id else item_id
            montar_grid()

        def trocar_tipo(e: ft.ControlEvent) -> None:
            kind["valor"] = e.control.selected[0] if e.control.selected else "expense"
            escolhido["valor"] = None
            montar_grid()

        tipo = ft.SegmentedButton(
            segments=[
                ft.Segment(value="expense", label=ft.Text("Despesa")),
                ft.Segment(value="income", label=ft.Text("Receita")),
            ],
            selected=["expense"],
            on_change=trocar_tipo,
        )

        async def confirmar_lancamento(_e) -> None:
            erro.visible = False
            try:
                cents = parse_brl(valor.value or "")
                if cents <= 0:
                    raise ValueError("Informe um valor válido.")
            except ValueError as ex:
                erro.value = str(ex)
                erro.visible = True
                page.update()
                return
            if kind["valor"] == "income" and escolhido["valor"] is None:
                erro.value = "Escolha a origem da receita."
                erro.visible = True
                page.update()
                return

            nome_estabelecimento = (estabelecimento.value or "").strip()
            payee_id = payees_repo.get_or_create(conn, nome_estabelecimento) if nome_estabelecimento else None
            if kind["valor"] == "expense":
                if payee_id is not None and escolhido["valor"] is not None:
                    payees_repo.set_default_category(conn, payee_id, escolhido["valor"])
                repo.add_expense(
                    conn, date=hoje.isoformat(), amount_cents=cents,
                    category_id=escolhido["valor"], payee_id=payee_id,
                )
            else:
                repo.add_income(
                    conn, date=hoje.isoformat(), amount_cents=cents,
                    income_source_id=escolhido["valor"], payee_id=payee_id,
                )

            # feedback visual instantâneo: botão pisca dourado (like a coin), depois volta
            # ao verde primário pro próximo lançamento
            botao_confirmar.bgcolor = _COR_SECUNDARIA
            texto_botao.value = "Registrado!"
            page.update()
            await asyncio.sleep(0.6)
            valor.value = ""
            estabelecimento.value = ""
            escolhido["valor"] = None
            botao_confirmar.bgcolor = _COR_PRIMARIA
            texto_botao.value = "Registrar"
            montar_grid()
            await valor.focus()
            page.update()

        botao_confirmar.on_click = confirmar_lancamento

        montar_grid()
        body.controls = [
            ft.Text("Novo lançamento", size=20, weight=ft.FontWeight.BOLD),
            tipo,
            ft.Container(
                content=valor, padding=16, border_radius=20, bgcolor=_COR_SUPERFICIE,
                alignment=ft.Alignment.CENTER,
            ),
            ft.Text("Categoria" if kind["valor"] == "expense" else "Origem", size=12, color=ft.Colors.GREY),
            grid,
            estabelecimento,
            erro,
            ft.Container(content=botao_confirmar, alignment=ft.Alignment.CENTER, padding=ft.Padding(left=0, right=0, top=12, bottom=0)),
        ]
        page.update()

    # ---------------------------------------------------------------- objetivos

    def _saldos_ultimos_meses(ano: int, mes: int, quantidade: int) -> list[int]:
        saldos = []
        a, m = ano, mes
        for _ in range(quantidade):
            saldos.append(month_totals(repo.list_month(conn, a, m)).balance_cents)
            a, m = previous_month(a, m)
        return saldos

    def _avaliar_objetivo(g: sqlite3.Row, rows_atual, rows_anterior, ano: int, mes: int) -> goals_core.GoalProgress:
        kind = g["kind"]
        if kind == "teto_categoria":
            gasto = dict(category_breakdown(rows_atual)).get(g["category_name"], 0)
            return goals_core.evaluate_teto_categoria(gasto, g["target_cents"])
        if kind == "reducao_categoria":
            atual = dict(category_breakdown(rows_atual)).get(g["category_name"], 0)
            anterior = dict(category_breakdown(rows_anterior)).get(g["category_name"], 0)
            return goals_core.evaluate_reducao_categoria(atual, anterior)
        if kind == "renda_extra":
            extra = sum(
                r["amount_cents"] for r in rows_atual
                if r["status"] == "confirmed" and r["kind"] == "income" and r["income_source_name"] != "Salário"
            )
            return goals_core.evaluate_renda_extra(extra, g["target_cents"])
        if kind == "saldo_positivo_seguido":
            saldos = _saldos_ultimos_meses(ano, mes, g["target_months"])
            streak = consecutive_positive_streak(saldos)
            return goals_core.evaluate_saldo_positivo_seguido(streak, g["target_months"])
        raise ValueError(f"Tipo de objetivo desconhecido: {kind!r}")

    def _texto_progresso(g: sqlite3.Row, p: goals_core.GoalProgress) -> str:
        if g["kind"] == "saldo_positivo_seguido":
            return f"{p.current} de {p.target} meses seguidos com saldo positivo"
        if g["kind"] == "reducao_categoria":
            return f"{format_brl(p.current)} este mês · era {format_brl(p.target)} no mês passado"
        return f"{format_brl(p.current)} de {format_brl(p.target)}"

    def card_missao(g: sqlite3.Row, p: goals_core.GoalProgress) -> ft.Control:
        # batido = dourado (PR); ainda ativo = verde primário (crescendo rumo à meta)
        cor = _COR_SECUNDARIA if p.achieved else _COR_PRIMARIA
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(_ICONES_OBJETIVO.get(g["kind"], _ICONE_PADRAO), color=cor, size=22),
                    ft.Text(g["label"], weight=ft.FontWeight.BOLD, expand=True),
                    ft.Container(
                        content=ft.Text(
                            "PR!" if p.achieved else "Ativo", size=11, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLACK,
                        ),
                        bgcolor=cor, border_radius=100,
                        padding=ft.Padding(left=10, right=10, top=3, bottom=3),
                    ),
                ], spacing=8),
                ft.ProgressBar(value=p.ratio, color=cor, bgcolor=ft.Colors.GREY_800, border_radius=8, bar_height=10),
                ft.Text(_texto_progresso(g, p), size=12, color=ft.Colors.GREY),
            ], spacing=10),
            padding=16, border_radius=20, bgcolor=_COR_SUPERFICIE,
            animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
        )

    def card_pr(r: sqlite3.Row) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.EMOJI_EVENTS_ROUNDED, color=_COR_SECUNDARIA, size=24),
                    ft.Text(
                        r["goal_label"], size=11, weight=ft.FontWeight.BOLD, max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(f"{r['year_month'][5:7]}/{r['year_month'][0:4]}", size=10, color=ft.Colors.GREY),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, tight=True,
            ),
            width=110, padding=12, border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.12, _COR_SECUNDARIA),
            border=ft.Border.all(1, _COR_SECUNDARIA),
        )

    def cabecalho_atleta(ofensiva: int, batidos: int, total: int) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, color=_COR_SECUNDARIA, size=30),
                                    ft.Text(str(ofensiva), size=30, weight=ft.FontWeight.BOLD),
                                ],
                                spacing=4, tight=True,
                            ),
                            ft.Text("meses de ofensiva", size=12, color=ft.Colors.GREY),
                        ],
                        spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.VerticalDivider(),
                    ft.Column(
                        [
                            ft.Text(f"{batidos}/{total}", size=30, weight=ft.FontWeight.BOLD, color=_COR_SECUNDARIA),
                            ft.Text("objetivos batidos este mês", size=12, color=ft.Colors.GREY),
                        ],
                        spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            ),
            padding=20, border_radius=20, bgcolor=_COR_SUPERFICIE,
        )

    def montar_objetivos() -> None:
        page.navigation_bar.selected_index = 2
        page.appbar = ft.AppBar(
            leading=ft.IconButton(icon=ft.Icons.MENU, on_click=abrir_menu),
            title=ft.Text("Objetivos"),
        )
        page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD, bgcolor=_COR_PRIMARIA, on_click=lambda e: abrir_dialog_objetivo(),
        )

        ano, mes = hoje.year, hoje.month
        ano_ant, mes_ant = previous_month(ano, mes)
        rows_atual = repo.list_month(conn, ano, mes)
        rows_anterior = repo.list_month(conn, ano_ant, mes_ant)
        year_month = f"{ano:04d}-{mes:02d}"

        objetivos = goals_repo.list_active(conn)
        progresso: list[tuple[sqlite3.Row, goals_core.GoalProgress]] = []
        for g in objetivos:
            p = _avaliar_objetivo(g, rows_atual, rows_anterior, ano, mes)
            goals_repo.record_result(conn, g["id"], year_month, p.achieved)
            progresso.append((g, p))

        ofensiva = goals_core.overall_streak(goals_repo.monthly_any_achieved(conn))
        recentes = goals_repo.recent_achievements(conn, limit=8)
        batidos = sum(1 for _, p in progresso if p.achieved)

        secoes: list[ft.Control] = [
            cabecalho_atleta(ofensiva, batidos, len(progresso)),
            ft.Container(height=4),
        ]
        if recentes:
            secoes += [
                ft.Text("Recordes recentes", size=13, weight=ft.FontWeight.BOLD, color=_COR_SECUNDARIA),
                ft.Row([card_pr(r) for r in recentes], scroll=ft.ScrollMode.AUTO, spacing=10),
                ft.Container(height=4),
            ]
        secoes.append(ft.Text("Missões do mês", size=15, weight=ft.FontWeight.BOLD))
        if progresso:
            secoes.append(ft.Column([card_missao(g, p) for g, p in progresso], spacing=10))
        else:
            secoes.append(ft.Text(
                "Nenhum objetivo ativo. Toque em + para criar um.", italic=True, color=ft.Colors.GREY,
            ))

        body.controls = [ft.Column(secoes, spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)]
        page.update()

    def abrir_dialog_objetivo() -> None:
        kind_map = {
            "Manter uma categoria abaixo de um teto": "teto_categoria",
            "Diminuir uma categoria vs. mês passado": "reducao_categoria",
            "Gerar renda extra (fora do salário)": "renda_extra",
            "Acumular meses seguidos de saldo positivo": "saldo_positivo_seguido",
        }
        tipo_dd = ft.Dropdown(
            label="Tipo de objetivo",
            options=[ft.DropdownOption(key=k, text=k) for k in kind_map],
        )
        categoria_dd = ft.Dropdown(
            label="Categoria",
            options=[
                ft.DropdownOption(key=str(c["id"]), text=c["name"])
                for c in categories_repo.list_active(conn)
            ],
            visible=False,
        )
        valor_alvo = ft.TextField(label="Valor alvo (R$)", visible=False)
        meses_alvo = ft.TextField(label="Meses seguidos", visible=False)
        label_campo = ft.TextField(label="Nome do objetivo (opcional)")
        erro = ft.Text(color=ft.Colors.RED, visible=False)

        def ao_trocar_tipo(_e) -> None:
            kind = kind_map.get(tipo_dd.value)
            categoria_dd.visible = kind in ("teto_categoria", "reducao_categoria")
            valor_alvo.visible = kind in ("teto_categoria", "renda_extra")
            meses_alvo.visible = kind == "saldo_positivo_seguido"
            page.update()

        tipo_dd.on_select = ao_trocar_tipo

        def fechar() -> None:
            page.pop_dialog()

        def salvar(_e) -> None:
            kind = kind_map.get(tipo_dd.value)
            erro.visible = False
            if kind is None:
                erro.value = "Escolha o tipo de objetivo."
                erro.visible = True
                page.update()
                return
            category_id = int(categoria_dd.value) if categoria_dd.visible and categoria_dd.value else None
            if categoria_dd.visible and category_id is None:
                erro.value = "Escolha a categoria."
                erro.visible = True
                page.update()
                return
            target_cents = None
            if valor_alvo.visible:
                try:
                    target_cents = parse_brl(valor_alvo.value or "")
                    if target_cents <= 0:
                        raise ValueError
                except ValueError:
                    erro.value = "Informe um valor alvo válido."
                    erro.visible = True
                    page.update()
                    return
            target_months = None
            if meses_alvo.visible:
                try:
                    target_months = int(meses_alvo.value or "0")
                except ValueError:
                    target_months = 0
                if target_months <= 0:
                    erro.value = "Informe quantos meses seguidos."
                    erro.visible = True
                    page.update()
                    return
            nome_categoria = next(
                (c["name"] for c in categories_repo.list_active(conn) if c["id"] == category_id), None,
            )
            label = (label_campo.value or "").strip() or _rotulo_padrao(kind, nome_categoria, target_cents, target_months)
            goals_repo.add(
                conn, kind=kind, label=label, category_id=category_id,
                target_cents=target_cents, target_months=target_months,
            )
            fechar()
            montar_objetivos()

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Novo objetivo"),
            content=ft.Column(
                [tipo_dd, categoria_dd, valor_alvo, meses_alvo, label_campo, erro],
                tight=True, spacing=10, width=380,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: fechar()),
                ft.FilledButton("Salvar", on_click=salvar),
            ],
        ))

    def _rotulo_padrao(kind: str, categoria: str | None, target_cents: int | None, target_months: int | None) -> str:
        if kind == "teto_categoria":
            return f"Manter {categoria} abaixo de {format_brl(target_cents)}"
        if kind == "reducao_categoria":
            return f"Diminuir {categoria} vs. mês passado"
        if kind == "renda_extra":
            return f"Gerar {format_brl(target_cents)} de renda extra"
        if kind == "saldo_positivo_seguido":
            return f"Acumular {target_months} meses de saldo positivo"
        return "Objetivo"

    tema_claro_switch = ft.Switch(value=(tema_salvo == "light"))

    def alternar_tema(_e) -> None:
        claro = tema_claro_switch.value
        page.theme_mode = ft.ThemeMode.LIGHT if claro else ft.ThemeMode.DARK
        goals_repo.set_setting(conn, "theme_mode", "light" if claro else "dark")
        page.update()

    tema_claro_switch.on_change = alternar_tema

    def montar_config() -> None:
        page.appbar = ft.AppBar(
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: montar_home()),
            title=ft.Text("Configurações"),
        )
        page.floating_action_button = None
        body.controls = [
            ft.Column([
                ft.Text("Aparência", size=13, weight=ft.FontWeight.BOLD),
                ft.Row([tema_claro_switch, ft.Text("Tema claro")], spacing=8),
                ft.Divider(),
                ft.Text("Backup", size=13, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Copia o banco de dados inteiro (lançamentos, categorias, recorrentes) "
                    "para uma pasta local, com data e hora no nome do arquivo.",
                    size=12, color=ft.Colors.GREY,
                ),
                ft.OutlinedButton("Fazer backup agora", icon=ft.Icons.BACKUP, on_click=fazer_backup),
                ultimo_backup_texto,
            ], spacing=10),
        ]
        page.update()

    montar_home()


if __name__ == "__main__":
    ft.run(main)
