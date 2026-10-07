"""Linha do tempo do mês, compacta, para consulta: uma bolinha por dia e por tipo.

A despesa do dia fica acima do eixo e a receita abaixo; o tamanho da bolinha cresce com o total do
dia, então os círculos maiores mostram onde o dinheiro se concentra. O dia de hoje fica em dourado e
tocar num dia abre o detalhe. Só desenha: os números vêm de `core/linha_tempo.py`.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import flet as ft

from app_fi.core.linha_tempo import LinhaTempo
from app_fi.core.money import format_brl
from app_fi.ui import cores

_DIAMETRO_MIN, _DIAMETRO_MAX = 4, 10   # a coluna de um dia tem ~10 px num celular
_ALTURA_METADE = 12                    # espaço da bolinha acima e abaixo do eixo
_DIAS_ROTULADOS = (1, 5, 10, 15, 20, 25)


def _cor_do_tipo(tipo: str) -> str:
    return ft.Colors.GREEN if tipo == "income" else ft.Colors.RED


def _bolinha(total_cents: int, maior_cents: int, tipo: str, de_baixo_para_cima: bool) -> ft.Control:
    """Diâmetro proporcional à raiz do total (a raiz evita que um dia enorme esmague os pequenos)."""
    conteudo = None
    if total_cents > 0 and maior_cents > 0:
        d = round(_DIAMETRO_MIN + (_DIAMETRO_MAX - _DIAMETRO_MIN) * math.sqrt(total_cents / maior_cents))
        conteudo = ft.Container(width=d, height=d, border_radius=d, bgcolor=_cor_do_tipo(tipo))
    return ft.Container(
        content=conteudo, height=_ALTURA_METADE,
        alignment=ft.Alignment.BOTTOM_CENTER if de_baixo_para_cima else ft.Alignment.TOP_CENTER,
    )


def _coluna_do_dia(linha: LinhaTempo, dia: int, ao_tocar_dia: Callable[[int], None]) -> ft.Control:
    tem_eventos = bool(linha.eventos_do_dia(dia))
    hoje = dia == linha.dia_hoje
    futuro = linha.dia_hoje is not None and dia > linha.dia_hoje
    rotulo = str(dia) if dia in _DIAS_ROTULADOS or dia in (linha.dias_no_mes, linha.dia_hoje) else ""
    return ft.Container(
        content=ft.Column([
            _bolinha(linha.total_do_dia(dia, "expense"), linha.maior_total_cents, "expense", True),
            ft.Container(height=2, bgcolor=cores.PRIMARIA if hoje else cores.BORDA),
            _bolinha(linha.total_do_dia(dia, "income"), linha.maior_total_cents, "income", False),
            ft.Text(
                rotulo, size=9, no_wrap=True, text_align=ft.TextAlign.CENTER,
                color=cores.PRIMARIA if hoje else cores.TEXTO_SUAVE,
                weight=ft.FontWeight.BOLD if hoje else None,
            ),
        ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.10, cores.PRIMARIA) if hoje else None,
        border_radius=4,
        opacity=0.45 if futuro else 1,
        ink=tem_eventos, on_click=(lambda e, d=dia: ao_tocar_dia(d)) if tem_eventos else None,
    )


def _legenda_ponto(cor: str, texto: str) -> ft.Control:
    return ft.Row([
        ft.Container(width=7, height=7, border_radius=7, bgcolor=cor),
        ft.Text(texto, size=10, color=cores.TEXTO_SUAVE),
    ], spacing=4)


def card_linha_tempo(linha: LinhaTempo, ao_tocar_dia: Callable[[int], None]) -> ft.Control:
    """Faixa da linha do tempo do mês exibido. `ao_tocar_dia(dia)` abre o detalhe do dia."""
    if linha.pico_dia is None:
        pico = "Sem gastos neste mês"
    else:
        pico = f"Maior gasto: dia {linha.pico_dia} · {format_brl(linha.pico_cents)}"
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Linha do tempo", size=12, weight=ft.FontWeight.W_600, color=cores.TEXTO_TITULO),
                ft.Row([_legenda_ponto(ft.Colors.RED, "Despesa"), _legenda_ponto(ft.Colors.GREEN, "Receita")],
                       spacing=10),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([_coluna_do_dia(linha, d, ao_tocar_dia) for d in range(1, linha.dias_no_mes + 1)], spacing=0),
            ft.Text(pico, size=10, color=cores.TEXTO_SUAVE),
        ], spacing=6),
        bgcolor=cores.SUPERFICIE, border=ft.Border.all(1, cores.BORDA), border_radius=14,
        padding=ft.Padding(left=10, right=10, top=10, bottom=8),
    )
