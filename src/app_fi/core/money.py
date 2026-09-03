"""Formatação e parsing de valores monetários (BRL, pt-BR).

Regra do projeto: dinheiro é sempre INTEGER em centavos. Estas funções são a
única fronteira entre "centavos" e "texto que a pessoa lê/digita".
"""

from __future__ import annotations


def format_brl(cents: int) -> str:
    """3490 -> 'R$ 34,90'   ·   -123456 -> '-R$ 1.234,56'"""
    sign = "-" if cents < 0 else ""
    reais, centavos = divmod(abs(cents), 100)
    reais_str = f"{reais:,}".replace(",", ".")  # separador de milhar pt-BR
    return f"{sign}R$ {reais_str},{centavos:02d}"


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
