"""Formatação e parsing de valores monetários (BRL, pt-BR).

Regra do projeto: dinheiro é sempre INTEGER em centavos. Estas funções são a
única fronteira entre "centavos" e "texto que a pessoa lê/digita".
"""

from __future__ import annotations


def _plain(cents: int) -> str:
    reais, centavos = divmod(abs(cents), 100)
    reais_str = f"{reais:,}".replace(",", ".")  # separador de milhar pt-BR
    return f"{reais_str},{centavos:02d}"


def format_brl(cents: int) -> str:
    """3490 -> 'R$ 34,90'   ·   -123456 -> '-R$ 1.234,56'"""
    sign = "-" if cents < 0 else ""
    return f"{sign}R$ {_plain(cents)}"


def format_amount_input(cents: int) -> str:
    """3490 -> '34,90' — sem 'R$', para pré-preencher o campo de valor ao editar."""
    return _plain(cents)


def parse_brl(text: str) -> int:
    """'34,90' | 'R$ 1.234,56' | '1000' -> centavos (int).

    Aceita o valor com ou sem 'R$', com separador de milhar '.' e decimal ','.
    Levanta ValueError com mensagem legível se não der para interpretar.
    (Expressões como '12+3' são um recurso do dialog de lançamento, não daqui.)
    """
    s = text.strip().replace("R$", "").replace(" ", "").replace(" ", "")
    if not s:
        raise ValueError("Informe um valor.")
    # pt-BR ("1.234,56") -> forma numérica ("1234.56")
    s = s.replace(".", "").replace(",", ".")
    try:
        value = float(s)
    except ValueError:
        raise ValueError(f"Valor inválido: {text!r}") from None
    return round(value * 100)
