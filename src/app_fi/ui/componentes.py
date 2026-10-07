"""Pequenos componentes e formatadores compartilhados pelas telas de investimentos."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from decimal import Decimal

import flet as ft

APENAS_NUMEROS = ft.InputFilter(regex_string=r"^[0-9.,]*$", allow=True)


def data_br(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"


def data_curta(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[2:4]}"


def texto_exato(valor: Decimal) -> str:
    """Valor para pré-preencher um campo de edição, sem arredondar: 0.000021 -> '0,000021',
    1234.567 -> '1234,567' (o formato de exibição arredondaria a centavos e alteraria o dado ao salvar)."""
    return f"{valor.normalize():f}".replace(".", ",")


def cor(valor: Decimal | None) -> str:
    """Verde para ganho, vermelho para perda, cinza para zero/ausente (semântica financeira, fora da marca)."""
    if valor is None or valor == 0:
        return ft.Colors.GREY
    return ft.Colors.GREEN if valor > 0 else ft.Colors.RED


def rotulo_valor(rotulo: str, valor: str, cor_valor: str | None = None, destaque: bool = False) -> ft.Control:
    return ft.Column(
        [
            ft.Text(rotulo, size=11, color=ft.Colors.GREY),
            ft.Text(valor, size=15 if destaque else 13, weight=ft.FontWeight.BOLD, color=cor_valor, max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS),
        ],
        spacing=2, expand=True,
    )


def botao_data(
    page: ft.Page, estado: dict, chave: str, prefixo: str, *, primeira: dt.date, ultima: dt.date,
    ao_mudar: Callable[[], None] | None = None,
) -> ft.TextButton:
    """Botão que mostra `prefixo: dd/mm/aaaa` e abre um DatePicker; grava a data ISO em `estado[chave]`
    (ou limpa para None se `estado[chave]` começar vazio e o usuário não escolher)."""
    atual = estado.get(chave)
    botao = ft.TextButton(f"{prefixo}: {data_br(atual) if atual else 'não definida'}",
                          icon=ft.Icons.CALENDAR_MONTH_ROUNDED)

    def escolher(e: ft.ControlEvent) -> None:
        valor = e.data if e.data is not None else e.control.value
        if valor is None:
            return
        estado[chave] = valor[:10] if isinstance(valor, str) else valor.isoformat()[:10]
        botao.content = f"{prefixo}: {data_br(estado[chave])}"
        if ao_mudar:
            ao_mudar()
        page.update()

    seletor = ft.DatePicker(
        value=dt.date.fromisoformat(atual) if atual else min(max(dt.date.today(), primeira), ultima),
        first_date=primeira, last_date=ultima, on_change=escolher,
    )
    botao.on_click = lambda e: page.show_dialog(seletor)
    return botao
