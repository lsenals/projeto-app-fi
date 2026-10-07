"""Carteira de criptoativos — cálculos puros (sem banco, sem UI).

Diferente do resto do app, aqui o dinheiro **não** é centavos inteiros: o preço
de uma cripto pode ser R$ 0,000021 (SHIB) e a quantidade tem até 8 casas, então
tudo é `Decimal` (exato, sem erro de ponto flutuante). Só os totais exibidos são
arredondados para centavos, na hora de formatar.

Método de custo: **preço médio** (o padrão no Brasil). A taxa de uma compra
entra no custo; a taxa de uma venda sai do valor recebido. Preços e valores
sempre em reais (BRL) — o app não fala com a internet, então não há cotação
automática: o preço atual de cada ativo é informado manualmente.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app_fi.core.money import format_brl

ZERO = Decimal(0)
_CEM = Decimal(100)
_UM_CENTAVO = Decimal("0.01")
_OITO_CASAS = Decimal("0.00000001")

# 1 satoshi de tolerância: evita rejeitar uma venda "de tudo" por sobra de arredondamento
_TOLERANCIA_QTD = Decimal("0.000000001")


# ----------------------------------------------------------------- operações

@dataclass(frozen=True)
class Operacao:
    lado: str            # 'buy' | 'sell'
    data: str            # ISO 'YYYY-MM-DD'
    quantidade: Decimal
    preco_unitario: Decimal
    taxa: Decimal = ZERO
    id: int = 0          # desempata operações do mesmo dia (ordem de inserção)


@dataclass(frozen=True)
class Posicao:
    quantidade: Decimal
    custo_total: Decimal       # custo (com taxas) do que ainda está em carteira
    realizado: Decimal         # lucro/prejuízo já realizado nas vendas
    total_comprado: Decimal    # tudo que já saiu do bolso em compras (com taxas)
    total_vendido: Decimal     # tudo que já entrou em vendas (líquido de taxas)

    @property
    def preco_medio(self) -> Decimal:
        return self.custo_total / self.quantidade if self.quantidade > 0 else ZERO


def calcular_posicao(operacoes: Iterable[Operacao]) -> Posicao:
    """Repete as operações em ordem cronológica. Levanta ValueError se alguma
    venda for maior que a quantidade em carteira naquele momento."""
    qtd = custo = realizado = comprado = vendido = ZERO
    for op in sorted(operacoes, key=lambda o: (o.data, o.id)):
        if op.lado == "buy":
            gasto = op.quantidade * op.preco_unitario + op.taxa
            custo += gasto
            qtd += op.quantidade
            comprado += gasto
        elif op.lado == "sell":
            if op.quantidade > qtd + _TOLERANCIA_QTD:
                raise ValueError(
                    f"Venda de {formatar_quantidade(op.quantidade)} em "
                    f"{op.data[8:10]}/{op.data[5:7]}/{op.data[:4]} é maior que "
                    f"a quantidade em carteira ({formatar_quantidade(qtd)})."
                )
            qtd_vendida = min(op.quantidade, qtd)
            medio = custo / qtd if qtd > 0 else ZERO
            recebido = op.quantidade * op.preco_unitario - op.taxa
            realizado += recebido - medio * qtd_vendida
            vendido += recebido
            custo -= medio * qtd_vendida
            qtd -= qtd_vendida
            if qtd <= _TOLERANCIA_QTD:
                qtd = custo = ZERO
        else:
            raise ValueError(f"Lado de operação desconhecido: {op.lado!r}")
    return Posicao(qtd, custo, realizado, comprado, vendido)


# ----------------------------------------------------------------- avaliação

@dataclass(frozen=True)
class Avaliacao:
    valor_atual: Decimal
    lucro: Decimal                # não realizado
    lucro_pct: Decimal | None     # sobre o custo; None quando não há custo


def avaliar(posicao: Posicao, preco_atual: Decimal | None) -> Avaliacao | None:
    """None quando o ativo ainda não tem preço atual informado."""
    if preco_atual is None:
        return None
    valor = posicao.quantidade * preco_atual
    lucro = valor - posicao.custo_total
    pct = lucro / posicao.custo_total * _CEM if posicao.custo_total > 0 else None
    return Avaliacao(valor, lucro, pct)


@dataclass(frozen=True)
class ProgressoMeta:
    preco_alvo: Decimal | None
    preco_stop: Decimal | None
    ratio: float            # 0..1 — quanto do caminho (preço médio -> alvo) já foi percorrido
    atingiu_alvo: bool
    atingiu_stop: bool
    falta_pct: Decimal | None  # quanto ainda falta de alta sobre o preço atual para o alvo (None se já atingiu)


def progresso_meta(
    preco_medio: Decimal,
    preco_atual: Decimal | None,
    ganho_alvo_pct: Decimal | None,
    stop_pct: Decimal | None,
) -> ProgressoMeta:
    """Meta de trade sobre o preço médio: "quero +20%" -> alvo = médio * 1,20.
    `stop_pct` é a perda máxima tolerada ("-10%") — opcional."""
    alvo = preco_medio * (1 + ganho_alvo_pct / _CEM) if ganho_alvo_pct is not None else None
    stop = preco_medio * (1 - stop_pct / _CEM) if stop_pct is not None else None
    ratio = 0.0
    atingiu_alvo = atingiu_stop = False
    falta = None
    if preco_atual is not None:
        if alvo is not None and alvo > preco_medio:
            ratio = float(max(ZERO, min(Decimal(1), (preco_atual - preco_medio) / (alvo - preco_medio))))
            atingiu_alvo = preco_atual >= alvo
            if not atingiu_alvo and preco_atual > 0:
                falta = (alvo - preco_atual) / preco_atual * _CEM
        atingiu_stop = stop is not None and preco_atual <= stop
    return ProgressoMeta(alvo, stop, ratio, atingiu_alvo, atingiu_stop, falta)


# ------------------------------------------------------------------ carteira

@dataclass(frozen=True)
class AtivoCarteira:
    id: int
    simbolo: str
    nome: str
    posicao: Posicao
    preco_atual: Decimal | None
    data_preco: str | None
    avaliacao: Avaliacao | None
    ganho_alvo_pct: Decimal | None
    stop_pct: Decimal | None
    meta: ProgressoMeta | None   # só quando há meta/stop definidos e posição aberta
    operacoes: tuple[Operacao, ...]

    @property
    def em_carteira(self) -> bool:
        return self.posicao.quantidade > 0


@dataclass(frozen=True)
class ResumoCarteira:
    investido: Decimal          # custo do que está em carteira
    valor_atual: Decimal
    lucro_nao_realizado: Decimal
    lucro_pct: Decimal | None
    realizado: Decimal
    resultado_total: Decimal    # não realizado + realizado
    ativos_sem_preco: int       # entram no valor atual pelo custo (lucro 0) até o preço ser informado


@dataclass(frozen=True)
class PontoEvolucao:
    data: str
    valor: Decimal       # valor da carteira na data
    investido: Decimal   # custo das posições abertas na data


@dataclass(frozen=True)
class Carteira:
    ativos: tuple[AtivoCarteira, ...]   # só os que têm operações, em carteira primeiro
    resumo: ResumoCarteira
    evolucao: tuple[PontoEvolucao, ...]


def parse_decimal(texto: str | None) -> Decimal | None:
    """Campo de texto -> Decimal. Vazio vira None. Aceita '1.234,56' (pt-BR) e,
    sem vírgula, o ponto como separador decimal ('0.5'). Levanta ValueError."""
    s = (texto or "").strip().replace("R$", "").replace("%", "").replace(" ", "")
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        valor = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Número inválido: {texto!r}") from None
    if not valor.is_finite():
        raise ValueError(f"Número inválido: {texto!r}")
    return valor


def _dec(texto: str | None) -> Decimal | None:
    return Decimal(texto) if texto not in (None, "") else None


def _operacao(row: Mapping) -> Operacao:
    return Operacao(
        lado=row["side"], data=row["date"], quantidade=Decimal(row["quantity"]),
        preco_unitario=Decimal(row["unit_price"]), taxa=Decimal(row["fee"] or "0"), id=row["id"],
    )


def montar_carteira(
    ativos: Iterable[Mapping], operacoes: Iterable[Mapping], historico_precos: Iterable[Mapping],
) -> Carteira:
    """Junta linhas do banco (ativos, operações, histórico de preços) no modelo da tela."""
    por_ativo: dict[int, list[Operacao]] = {}
    for row in operacoes:
        por_ativo.setdefault(row["asset_id"], []).append(_operacao(row))
    historico: dict[int, list[tuple[str, Decimal]]] = {}
    for row in historico_precos:
        historico.setdefault(row["asset_id"], []).append((row["date"], Decimal(row["price"])))

    itens: list[AtivoCarteira] = []
    for a in ativos:
        ops = por_ativo.get(a["id"])
        if not ops:
            continue
        pos = calcular_posicao(ops)
        preco = _dec(a["current_price"])
        ganho, stop = _dec(a["target_gain_pct"]), _dec(a["stop_loss_pct"])
        meta = None
        if pos.quantidade > 0 and (ganho is not None or stop is not None):
            meta = progresso_meta(pos.preco_medio, preco, ganho, stop)
        itens.append(AtivoCarteira(
            id=a["id"], simbolo=a["symbol"], nome=a["name"], posicao=pos, preco_atual=preco,
            data_preco=a["price_updated_at"],
            avaliacao=avaliar(pos, preco) if pos.quantidade > 0 else None,
            ganho_alvo_pct=ganho, stop_pct=stop, meta=meta,
            operacoes=tuple(sorted(ops, key=lambda o: (o.data, o.id))),
        ))
    itens.sort(key=lambda x: (not x.em_carteira, -(x.avaliacao.valor_atual if x.avaliacao else x.posicao.custo_total)))

    return Carteira(
        ativos=tuple(itens),
        resumo=_resumir(itens),
        evolucao=tuple(_evolucao(itens, historico)),
    )


def _resumir(ativos: Iterable[AtivoCarteira]) -> ResumoCarteira:
    investido = valor = realizado = ZERO
    sem_preco = 0
    for a in ativos:
        realizado += a.posicao.realizado
        if not a.em_carteira:
            continue
        investido += a.posicao.custo_total
        if a.avaliacao is None:
            valor += a.posicao.custo_total
            sem_preco += 1
        else:
            valor += a.avaliacao.valor_atual
    lucro = valor - investido
    return ResumoCarteira(
        investido=investido, valor_atual=valor, lucro_nao_realizado=lucro,
        lucro_pct=lucro / investido * _CEM if investido > 0 else None,
        realizado=realizado, resultado_total=lucro + realizado, ativos_sem_preco=sem_preco,
    )


def _evolucao(
    ativos: list[AtivoCarteira], historico: Mapping[int, list[tuple[str, Decimal]]],
) -> list[PontoEvolucao]:
    """Valor da carteira em cada data em que algo aconteceu (operação ou preço
    informado). Em cada data, cada ativo vale: quantidade então em carteira × último
    preço conhecido até ali (histórico informado ou, na falta, o preço da última operação)."""
    datas = {op.data for a in ativos for op in a.operacoes}
    datas |= {d for a in ativos for d, _ in historico.get(a.id, [])}
    pontos: list[PontoEvolucao] = []
    for data in sorted(datas):
        valor = investido = ZERO
        for a in ativos:
            ops = [op for op in a.operacoes if op.data <= data]
            if not ops:
                continue
            pos = calcular_posicao(ops)
            if pos.quantidade <= 0:
                continue
            pontos_preco = [(op.data, op.preco_unitario) for op in ops]
            pontos_preco += [(d, p) for d, p in historico.get(a.id, []) if d <= data]
            # ordena só por data (estável): em empate, o preço informado (adicionado depois) prevalece
            preco = max(enumerate(pontos_preco), key=lambda t: (t[1][0], t[0]))[1][1]
            valor += pos.quantidade * preco
            investido += pos.custo_total
        if investido > 0:
            pontos.append(PontoEvolucao(data, valor, investido))
    return pontos


# ---------------------------------------------------------------- formatação

def formatar_quantidade(q: Decimal) -> str:
    """0.5 -> '0,5'   ·   1234.5678 -> '1.234,5678'   (até 8 casas, sem zeros à direita)"""
    q = q.quantize(_OITO_CASAS, rounding=ROUND_HALF_UP)
    inteiro, _, frac = f"{q:f}".partition(".")
    frac = frac.rstrip("0")
    inteiro = f"{int(inteiro):,}".replace(",", ".")
    return f"{inteiro},{frac}" if frac else inteiro


def formatar_preco(p: Decimal) -> str:
    """Preço unitário: 2 casas a partir de R$ 1; abaixo disso, mais casas (até 8)
    para não virar 'R$ 0,00'. 34.9 -> 'R$ 34,90'  ·  0.000021 -> 'R$ 0,000021'"""
    sinal = "-" if p < 0 else ""
    p = abs(p)
    if p >= 1:
        return f"{sinal}{format_brl(_centavos(p))}"
    texto = f"{p.quantize(_OITO_CASAS, rounding=ROUND_HALF_UP):f}".rstrip("0")
    inteiro, _, frac = texto.partition(".")
    frac = frac.ljust(2, "0")
    return f"{sinal}R$ {inteiro or '0'},{frac}"


def _centavos(valor: Decimal) -> int:
    return int((valor * _CEM).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def formatar_valor(valor: Decimal) -> str:
    """Total em reais, arredondado para centavos: 5049.101 -> 'R$ 5.049,10'"""
    return format_brl(_centavos(valor))


def formatar_pct(pct: Decimal | None) -> str:
    if pct is None:
        return "—"
    return f"{pct.quantize(_UM_CENTAVO, rounding=ROUND_HALF_UP):+f}%".replace(".", ",")


# --------------------------------------------------------- catálogo de ativos

# (símbolo, nome) dos principais criptoativos por capitalização de mercado — ponto de
# partida para o usuário escolher na lista. É dado de referência estático (a ordem
# muda com o tempo); ativos fora da lista podem ser cadastrados na tela.
CATALOGO_PRINCIPAIS: tuple[tuple[str, str], ...] = (
    ("BTC", "Bitcoin"), ("ETH", "Ethereum"), ("USDT", "Tether"), ("XRP", "XRP"),
    ("BNB", "BNB"), ("SOL", "Solana"), ("USDC", "USD Coin"), ("DOGE", "Dogecoin"),
    ("ADA", "Cardano"), ("TRX", "TRON"), ("LINK", "Chainlink"), ("AVAX", "Avalanche"),
    ("XLM", "Stellar"), ("SHIB", "Shiba Inu"), ("BCH", "Bitcoin Cash"), ("TON", "Toncoin"),
    ("DOT", "Polkadot"), ("LTC", "Litecoin"), ("HBAR", "Hedera"), ("UNI", "Uniswap"),
    ("POL", "Polygon"), ("NEAR", "NEAR Protocol"), ("APT", "Aptos"), ("ICP", "Internet Computer"),
    ("ETC", "Ethereum Classic"), ("AAVE", "Aave"), ("ATOM", "Cosmos"), ("ALGO", "Algorand"),
    ("FIL", "Filecoin"), ("ARB", "Arbitrum"), ("OP", "Optimism"), ("SUI", "Sui"),
    ("INJ", "Injective"), ("VET", "VeChain"), ("XMR", "Monero"), ("PEPE", "Pepe"),
    ("DAI", "Dai"), ("RNDR", "Render"), ("SAND", "The Sandbox"), ("MANA", "Decentraland"),
)

_SIMBOLO_VALIDO = re.compile(r"^[A-Z0-9]{1,12}$")


def normalizar_simbolo(texto: str) -> str:
    """'  ada ' -> 'ADA'. Levanta ValueError se não for um símbolo plausível."""
    simbolo = (texto or "").strip().upper()
    if not _SIMBOLO_VALIDO.match(simbolo):
        raise ValueError("Símbolo inválido: use letras e números, até 12 caracteres.")
    return simbolo
