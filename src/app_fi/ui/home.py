"""Home em hub e o grupo "Investimentos" (design: canvas "Finapple – Nova Home").

A Home deixou de ser o painel de finanças: virou um índice de módulos (Finanças pessoais,
Investimentos, Objetivos). "Investimentos" agrupa Cripto, Ações e Renda Fixa. A linha "Em breve"
(`em_breve=True` em `_linha`) existe para módulos futuros. Só desenha e navega: os números vêm de
`core/` e `data/`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

import flet as ft

from app_fi.core import goals as goals_core
from app_fi.data import goals_repo
from app_fi.ui import cores


def _icone(icone) -> ft.Control:
    return ft.Container(
        content=ft.Icon(icone, color=cores.PRIMARIA, size=20), width=40, height=40, border_radius=12,
        bgcolor=cores.ICONE_FUNDO, border=ft.Border.all(1, cores.ICONE_BORDA),
        alignment=ft.Alignment.CENTER,
    )


def _linha(
    icone, titulo: str, subtitulo: str, ao_clicar: Callable | None = None, em_breve: bool = False,
) -> ft.Control:
    """Uma linha do índice: bloco de ícone, título, subtítulo e seta (ou o selo "Em breve")."""
    direita = (
        ft.Container(
            content=ft.Text("Em breve", size=11, color=cores.PRIMARIA, weight=ft.FontWeight.W_600),
            border=ft.Border.all(1, cores.PRIMARIA), border_radius=100,
            padding=ft.Padding(left=10, right=10, top=3, bottom=3),
        )
        if em_breve else ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=cores.SETA, size=22)
    )
    return ft.Container(
        content=ft.Row([
            _icone(icone),
            ft.Column([
                ft.Text(titulo, font_family=cores.FONTE_TITULO, size=16, weight=ft.FontWeight.W_600,
                        color=cores.TEXTO),
                ft.Text(subtitulo, size=12, color=cores.TEXTO_SUAVE),
            ], spacing=1, expand=True),
            direita,
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(left=14, right=14, top=11, bottom=11),
        ink=ao_clicar is not None, on_click=ao_clicar,
        opacity=0.6 if em_breve else 1,
    )


def _lista(linhas: list[ft.Control]) -> ft.Control:
    """Cartão com as linhas separadas por divisórias finas, estreito e centralizado: ocupa 80% da
    largura (margens laterais iguais), então as linhas não vão até as bordas da tela. Proporção em
    vez de largura fixa: não depende do tamanho da tela, que o Flet só informa depois do 1º desenho."""
    itens: list[ft.Control] = []
    for i, linha in enumerate(linhas):
        if i:
            itens.append(ft.Divider(height=1, thickness=1, color=cores.BORDA))
        itens.append(linha)
    cartao = ft.Container(
        content=ft.Column(itens, spacing=0), bgcolor=cores.SUPERFICIE, border_radius=18,
        border=ft.Border.all(1, cores.BORDA), clip_behavior=ft.ClipBehavior.HARD_EDGE, expand=8,
    )
    return ft.Row([ft.Container(expand=1), cartao, ft.Container(expand=1)], spacing=0)


def _nome_marca(tamanho: int) -> ft.Control:
    return ft.Row([
        ft.Text("Fin", font_family=cores.FONTE_TITULO, size=tamanho, weight=ft.FontWeight.W_500,
                color=cores.TEXTO_TITULO),
        ft.Text("apple", font_family=cores.FONTE_TITULO, size=tamanho, weight=ft.FontWeight.W_500,
                color=cores.PRIMARIA),
    ], spacing=0, alignment=ft.MainAxisAlignment.CENTER)


def criar_home(
    page: ft.Page, conn: sqlite3.Connection, body: ft.Column, *,
    abrir_menu: Callable, ir_financas: Callable[[], None], ir_objetivos: Callable[[], None],
    ir_cripto: Callable[[], None], ir_acoes: Callable[[], None], ir_renda_fixa: Callable[[], None],
) -> tuple[Callable[[], None], Callable[[], None]]:
    """Devolve `(montar_hub, montar_investimentos)`."""

    def montar_hub() -> None:
        page.appbar = ft.AppBar(leading=ft.IconButton(icon=ft.Icons.MENU, on_click=abrir_menu))
        page.floating_action_button = None
        nivel = goals_core.calcular_nivel(goals_repo.count_achieved(conn))
        # espaçadores proporcionais centralizam o bloco na altura da tela (um pouco acima do meio, que
        # parece mais centrado). O bloco tem ~315 px de altura: cabe em qualquer celular
        body.controls = [ft.Column([
            ft.Container(expand=4),
            ft.Column([
                ft.Image(src="logo_finapple.svg", width=84, height=98, fit=ft.BoxFit.CONTAIN),
                _nome_marca(26),
                ft.Text("Bem-vindo de volta! Para onde vamos?", size=14, color=cores.TEXTO_SUAVE),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            _lista([
                _linha(ft.Icons.CREDIT_CARD_ROUNDED, "Finanças pessoais", "Lançamentos e despesas",
                       lambda e: ir_financas()),
                _linha(ft.Icons.TRENDING_UP_ROUNDED, "Investimentos",
                       "Cripto, renda fixa e ações",
                       lambda e: montar_investimentos()),
                _linha(ft.Icons.EMOJI_EVENTS_ROUNDED, "Objetivos", "Metas e conquistas",
                       lambda e: ir_objetivos()),
            ]),
            ft.Text(f"Nível {nivel.nivel} · {nivel.xp_no_nivel}/{nivel.xp_por_nivel} XP", size=12,
                    color=cores.TEXTO_SUAVE),
            ft.Container(expand=5),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20, expand=True)]
        page.update()

    def montar_investimentos() -> None:
        page.appbar = ft.AppBar(
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: montar_hub()),
            title=ft.Text("Investimentos", font_family=cores.FONTE_TITULO, weight=ft.FontWeight.W_600),
        )
        page.floating_action_button = None
        body.controls = [ft.Column([
            _lista([
                _linha(ft.Icons.CURRENCY_BITCOIN, "Cripto", "Moedas digitais, em reais ou dólares",
                       lambda e: ir_cripto()),
                _linha(ft.Icons.ACCOUNT_BALANCE_ROUNDED, "Renda Fixa", "Tesouro, CDB, LCI, LCA e IR",
                       lambda e: ir_renda_fixa()),
                _linha(ft.Icons.CANDLESTICK_CHART_ROUNDED, "Ações", "Ações e fundos da bolsa",
                       lambda e: ir_acoes()),
            ]),
        ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)]
        page.update()

    return montar_hub, montar_investimentos
