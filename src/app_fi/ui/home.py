"""Home em hub e o grupo "Investimentos" (design: canvas "Finapple – Nova Home").

A Home deixou de ser o painel de finanças: virou um índice de módulos (Finanças pessoais,
Investimentos, Objetivos). "Investimentos" agrupa Cripto, Renda Fixa e Ações — os dois
últimos ainda não existem e aparecem como "Em breve". Só desenha e navega: os números vêm de
`core/` e `data/`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

import flet as ft

from app_fi.core import crypto as core_crypto
from app_fi.core import goals as goals_core
from app_fi.data import crypto_repo, goals_repo
from app_fi.ui import cores


def _icone(icone) -> ft.Control:
    return ft.Container(
        content=ft.Icon(icone, color=cores.PRIMARIA, size=22), width=44, height=44, border_radius=12,
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
                ft.Text(titulo, font_family=cores.FONTE_TITULO, size=17, weight=ft.FontWeight.W_600,
                        color=cores.TEXTO),
                ft.Text(subtitulo, size=13, color=cores.TEXTO_SUAVE),
            ], spacing=2, expand=True),
            direita,
        ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(left=20, right=20, top=16, bottom=16),
        ink=ao_clicar is not None, on_click=ao_clicar,
        opacity=0.6 if em_breve else 1,
    )


def _lista(linhas: list[ft.Control]) -> ft.Control:
    """Cartão com as linhas separadas por divisórias finas."""
    itens: list[ft.Control] = []
    for i, linha in enumerate(linhas):
        if i:
            itens.append(ft.Divider(height=1, thickness=1, color=cores.BORDA))
        itens.append(linha)
    return ft.Container(
        content=ft.Column(itens, spacing=0), bgcolor=cores.SUPERFICIE, border_radius=18,
        border=ft.Border.all(1, cores.BORDA), clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


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
    ir_cripto: Callable[[], None],
) -> tuple[Callable[[], None], Callable[[], None]]:
    """Devolve `(montar_hub, montar_investimentos)`."""

    def _resumo_cripto() -> str | None:
        r = crypto_repo.load_wallet(conn).resumo
        if r.investido <= 0:
            return None
        return f"{core_crypto.formatar_valor(r.valor_atual, r.moeda)} · {core_crypto.formatar_pct(r.lucro_pct)}"

    def montar_hub() -> None:
        page.appbar = ft.AppBar(leading=ft.IconButton(icon=ft.Icons.MENU, on_click=abrir_menu))
        page.floating_action_button = None
        nivel = goals_core.calcular_nivel(goals_repo.count_achieved(conn))
        resumo = _resumo_cripto()
        body.controls = [ft.Column([
            ft.Column([
                ft.Image(src="logo_finapple.svg", width=72, height=84, fit=ft.BoxFit.CONTAIN),
                _nome_marca(28),
                ft.Text("Bem-vindo de volta! Para onde vamos?", size=15, color=cores.TEXTO_SUAVE),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            _lista([
                _linha(ft.Icons.CREDIT_CARD_ROUNDED, "Finanças pessoais", "Lançamentos e despesas",
                       lambda e: ir_financas()),
                _linha(ft.Icons.TRENDING_UP_ROUNDED, "Investimentos",
                       f"Cripto {resumo}" if resumo else "Cripto, renda fixa e ações",
                       lambda e: montar_investimentos()),
                _linha(ft.Icons.EMOJI_EVENTS_ROUNDED, "Objetivos", "Metas e conquistas",
                       lambda e: ir_objetivos()),
            ]),
            ft.Text(f"Nível {nivel.nivel} · {nivel.xp_no_nivel}/{nivel.xp_por_nivel} XP", size=13,
                    color=cores.TEXTO_SUAVE),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=28, scroll=ft.ScrollMode.AUTO, expand=True)]
        page.update()

    def montar_investimentos() -> None:
        page.appbar = ft.AppBar(
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: montar_hub()),
            title=ft.Text("Investimentos", font_family=cores.FONTE_TITULO, weight=ft.FontWeight.W_600),
        )
        page.floating_action_button = None
        resumo = _resumo_cripto()
        body.controls = [ft.Column([
            _lista([
                _linha(ft.Icons.CURRENCY_BITCOIN, "Cripto", resumo or "Carteira e cotações",
                       lambda e: ir_cripto()),
                _linha(ft.Icons.ACCOUNT_BALANCE_ROUNDED, "Renda Fixa", "Tesouro, CDB e outros títulos",
                       em_breve=True),
                _linha(ft.Icons.CANDLESTICK_CHART_ROUNDED, "Ações", "Carteira de ações e proventos",
                       em_breve=True),
            ]),
        ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)]
        page.update()

    return montar_hub, montar_investimentos
