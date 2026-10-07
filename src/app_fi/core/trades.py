"""Diário de trades realizados (Cripto e Ações) — cálculos puros.

Um trade realizado é uma operação já encerrada, lançada à mão com os valores totais: data e valor da
compra, data e valor da venda e os custos da operação (taxas, corretagem, impostos pagos).
`lucro = valor_venda − valor_compra − custos`; o percentual é sobre o valor de compra.

É um registro **à parte** do livro de operações da carteira (compras/vendas com preço médio): serve para
trades feitos antes de usar o app ou fora da carteira. Os dois não se somam sozinhos.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from app_fi.core.crypto import ZERO, fator_conversao, validar_moeda

MODULOS = ("cripto", "acoes")
_CEM = Decimal(100)


@dataclass(frozen=True)
class TradeRealizado:
    id: int
    modulo: str
    simbolo: str
    nome: str | None
    moeda: str
    quantidade: Decimal | None
    data_compra: str
    valor_compra: Decimal
    data_venda: str
    valor_venda: Decimal
    custos: Decimal
    nota: str | None

    @property
    def lucro(self) -> Decimal:
        return self.valor_venda - self.valor_compra - self.custos

    @property
    def lucro_pct(self) -> Decimal:
        return self.lucro / self.valor_compra * _CEM

    @property
    def dias(self) -> int:
        return (dt.date.fromisoformat(self.data_venda) - dt.date.fromisoformat(self.data_compra)).days


def validar_trade(
    *, modulo: str, simbolo: str, moeda: str, data_compra: str, valor_compra: Decimal,
    data_venda: str, valor_venda: Decimal, custos: Decimal, quantidade: Decimal | None = None,
) -> None:
    """Levanta ValueError com mensagem legível se o trade não faz sentido."""
    if modulo not in MODULOS:
        raise ValueError("Módulo inválido.")
    if not (simbolo or "").strip():
        raise ValueError("Informe o ativo.")
    validar_moeda(moeda)
    try:
        compra, venda = dt.date.fromisoformat(data_compra), dt.date.fromisoformat(data_venda)
    except ValueError:
        raise ValueError("Data inválida.") from None
    if venda < compra:
        raise ValueError("A data da venda não pode ser anterior à da compra.")
    if valor_compra <= 0:
        raise ValueError("O valor da compra deve ser maior que zero.")
    if valor_venda < 0:
        raise ValueError("O valor da venda não pode ser negativo.")
    if custos < 0:
        raise ValueError("Os custos não podem ser negativos.")
    if quantidade is not None and quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")


def trade_de_linha(row: Mapping) -> TradeRealizado:
    return TradeRealizado(
        id=row["id"], modulo=row["modulo"], simbolo=row["symbol"], nome=row["name"], moeda=row["currency"],
        quantidade=Decimal(row["quantity"]) if row["quantity"] else None,
        data_compra=row["buy_date"], valor_compra=Decimal(row["buy_value"]),
        data_venda=row["sell_date"], valor_venda=Decimal(row["sell_value"]),
        custos=Decimal(row["costs"] or "0"), nota=row["note"],
    )


@dataclass(frozen=True)
class ResumoTrades:
    moeda: str
    total: int                  # trades somados
    sem_cotacao: int            # trades em outra moeda deixados de fora por falta da cotação do dólar
    lucro_total: Decimal
    custos_total: Decimal
    investido_total: Decimal    # soma dos valores de compra
    lucro_pct: Decimal | None   # lucro_total sobre investido_total
    vitorias: int
    derrotas: int
    taxa_acerto: Decimal | None  # % de trades com lucro > 0
    melhor: TradeRealizado | None
    pior: TradeRealizado | None


def resumir_trades(
    trades: Iterable[TradeRealizado], moeda_exibicao: str = "BRL", cotacao_usd: Decimal | None = None,
) -> ResumoTrades:
    """Totais na moeda de exibição (cada trade convertido pela cotação do dólar informada)."""
    validar_moeda(moeda_exibicao)
    lucro = custos = investido = ZERO
    vitorias = derrotas = sem_cotacao = 0
    melhor = pior = None
    melhor_v = pior_v = ZERO
    total = 0
    for t in trades:
        fator = fator_conversao(t.moeda, moeda_exibicao, cotacao_usd)
        if fator is None:
            sem_cotacao += 1
            continue
        total += 1
        l = t.lucro * fator
        lucro += l
        custos += t.custos * fator
        investido += t.valor_compra * fator
        if l > 0:
            vitorias += 1
        elif l < 0:
            derrotas += 1
        if melhor is None or l > melhor_v:
            melhor, melhor_v = t, l
        if pior is None or l < pior_v:
            pior, pior_v = t, l
    return ResumoTrades(
        moeda=moeda_exibicao, total=total, sem_cotacao=sem_cotacao, lucro_total=lucro, custos_total=custos,
        investido_total=investido, lucro_pct=lucro / investido * _CEM if investido > 0 else None,
        vitorias=vitorias, derrotas=derrotas,
        taxa_acerto=Decimal(vitorias) / total * _CEM if total else None,
        melhor=melhor, pior=pior,
    )
