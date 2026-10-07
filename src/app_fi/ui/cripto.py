"""Tela de Cripto — a carteira de criptoativos (catálogo dos 40 principais + ativos próprios)."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from app_fi.data import crypto_repo
from app_fi.ui.carteira import ConfigCarteira, criar_tela_carteira

CONFIG = ConfigCarteira(
    modulo="cripto", titulo="Cripto", icone=ft.Icons.CURRENCY_BITCOIN,
    vazio_titulo="Sua carteira cripto está vazia",
    vazio_texto="Registre uma compra no botão + e depois informe o preço atual para ver lucro, prejuízo e metas de trade.",
    texto_cadastrar="Ativo não está na lista? Cadastrar", ticker_exemplo="ADA", nome_exemplo="Cardano",
)


def criar_tela_cripto(page: ft.Page, conn, body: ft.Column, *, voltar: Callable,
                      confirmar: Callable[[str], None]) -> Callable[[], None]:
    return criar_tela_carteira(page, conn, body, repo=crypto_repo, config=CONFIG, voltar=voltar, confirmar=confirmar)
