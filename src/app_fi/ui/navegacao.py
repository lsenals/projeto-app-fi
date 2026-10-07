"""Mapa de navegação: para cada tela, qual é a tela "pai" (o que o botão voltar deve mostrar).

Sem Flet aqui de propósito — é só dado e uma função, para poder ser testado. O `main.py` liga
cada nome à função que desenha a tela. `None` = raiz (o hub): o voltar sai do app.
"""

from __future__ import annotations

PAI_DA_TELA: dict[str, str | None] = {
    "hub": None,
    "financas": "hub",
    "objetivos": "hub",
    "investimentos": "hub",
    "categorias": "hub",      # as três vêm do menu lateral, que só existe no hub
    "recorrentes": "hub",
    "config": "hub",
    "cripto": "investimentos",
    "lancamento": "financas",
    "fechamento": "financas",
    "revisao": "financas",    # revisão da importação de fatura
}


def pai_de(tela: str) -> str | None:
    """Tela para onde o voltar leva; None no hub (sair do app). Levanta KeyError em nome desconhecido."""
    return PAI_DA_TELA[tela]
