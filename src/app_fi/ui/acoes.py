"""Tela de Ações — mesma carteira de Cripto, sem catálogo: os tickers são cadastrados à mão."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from app_fi.data import acoes_repo
from app_fi.ui.carteira import ConfigCarteira, criar_tela_carteira

CONFIG = ConfigCarteira(
    modulo="acoes", titulo="Ações", icone=ft.Icons.CANDLESTICK_CHART_ROUNDED,
    vazio_titulo="Sua carteira de ações está vazia",
    vazio_texto="Cadastre uma ação (ticker, como PETR4) pelo botão +, registre a compra e informe o preço atual "
                "para ver lucro, prejuízo e metas de trade.",
    texto_cadastrar="Cadastrar nova ação (ticker)", ticker_exemplo="PETR4", nome_exemplo="Petrobras PN",
)


def criar_tela_acoes(page: ft.Page, conn, body: ft.Column, *, voltar: Callable,
                     confirmar: Callable[[str], None]) -> Callable[[], None]:
    return criar_tela_carteira(page, conn, body, repo=acoes_repo, config=CONFIG, voltar=voltar, confirmar=confirmar)
