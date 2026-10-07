"""Renda fixa — cálculos puros (sem banco, sem UI).

Modelo: uma **aplicação** (um CDB, um Tesouro IPCA+ 2035…) tem aportes e resgates (os movimentos), uma
rentabilidade contratada (pré ou pós-fixada), um vencimento e um **valor atual informado à mão** (o app
não acessa a internet; o usuário copia do extrato). Tudo em reais (BRL) e em `Decimal`.

Acompanhamento de IR: conta os **dias corridos desde o aporte** e mostra a faixa da tabela regressiva
(22,5% até 180 dias, 20% até 360, 17,5% até 720, 15% depois), quanto falta para a próxima faixa e uma
**estimativa** do imposto. É uma estimativa: não considera IOF (só cobrado nos primeiros 30 dias), come-cotas
de fundos, nem a marcação a mercado do Tesouro antes do vencimento — o valor atual é o que o usuário informa.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app_fi.core.crypto import ZERO, formatar_valor, parse_decimal  # noqa: F401  (re-exportados para a UI)

_CEM = Decimal(100)

# ------------------------------------------------------------------ catálogo

INDEXADORES = ("PRE", "CDI", "CDI_MAIS", "SELIC", "IPCA", "OUTRO")

NOME_INDEXADOR = {
    "PRE": "Pré-fixado (% a.a.)",
    "CDI": "% do CDI",
    "CDI_MAIS": "CDI + taxa a.a.",
    "SELIC": "Selic + taxa a.a.",
    "IPCA": "IPCA + taxa a.a.",
    "OUTRO": "Outro",
}

LIQUIDEZES = ("diaria", "vencimento", "carencia")
NOME_LIQUIDEZ = {"diaria": "Diária", "vencimento": "No vencimento", "carencia": "Diária após carência"}


@dataclass(frozen=True)
class TipoRendaFixa:
    chave: str
    nome: str
    grupo: str
    indexador: str       # sugestão ao escolher o tipo
    liquidez: str        # sugestão
    isento_ir: bool      # pessoa física: isento de IR sobre o rendimento
    fgc: bool            # coberto pelo FGC (até o limite por CPF e instituição)


TIPOS: tuple[TipoRendaFixa, ...] = (
    TipoRendaFixa("TESOURO_SELIC", "Tesouro Selic (LFT)", "Tesouro Direto", "SELIC", "diaria", False, False),
    TipoRendaFixa("TESOURO_PREFIXADO", "Tesouro Prefixado (LTN)", "Tesouro Direto", "PRE", "diaria", False, False),
    TipoRendaFixa("TESOURO_PREFIXADO_JUROS", "Tesouro Prefixado com Juros Semestrais (NTN-F)", "Tesouro Direto",
                  "PRE", "diaria", False, False),
    TipoRendaFixa("TESOURO_IPCA", "Tesouro IPCA+ (NTN-B Principal)", "Tesouro Direto", "IPCA", "diaria", False, False),
    TipoRendaFixa("TESOURO_IPCA_JUROS", "Tesouro IPCA+ com Juros Semestrais (NTN-B)", "Tesouro Direto",
                  "IPCA", "diaria", False, False),
    TipoRendaFixa("TESOURO_RENDA_MAIS", "Tesouro Renda+ Aposentadoria Extra", "Tesouro Direto", "IPCA",
                  "vencimento", False, False),
    TipoRendaFixa("TESOURO_EDUCA_MAIS", "Tesouro Educa+", "Tesouro Direto", "IPCA", "vencimento", False, False),
    TipoRendaFixa("CDB", "CDB", "Bancários (FGC)", "CDI", "vencimento", False, True),
    TipoRendaFixa("LCI", "LCI", "Bancários (FGC)", "CDI", "carencia", True, True),
    TipoRendaFixa("LCA", "LCA", "Bancários (FGC)", "CDI", "carencia", True, True),
    TipoRendaFixa("LC", "LC — Letra de Câmbio", "Bancários (FGC)", "CDI", "vencimento", False, True),
    TipoRendaFixa("POUPANCA", "Poupança", "Bancários (FGC)", "OUTRO", "diaria", True, True),
    TipoRendaFixa("CRI", "CRI", "Crédito privado", "IPCA", "vencimento", True, False),
    TipoRendaFixa("CRA", "CRA", "Crédito privado", "IPCA", "vencimento", True, False),
    TipoRendaFixa("DEBENTURE", "Debênture", "Crédito privado", "CDI_MAIS", "vencimento", False, False),
    TipoRendaFixa("DEBENTURE_INCENTIVADA", "Debênture incentivada", "Crédito privado", "IPCA", "vencimento", True, False),
    TipoRendaFixa("OUTRO", "Outro título de renda fixa", "Outros", "PRE", "vencimento", False, False),
)

_TIPO_POR_CHAVE = {t.chave: t for t in TIPOS}


def tipo_por_chave(chave: str) -> TipoRendaFixa:
    try:
        return _TIPO_POR_CHAVE[chave]
    except KeyError:
        raise ValueError(f"Tipo de renda fixa desconhecido: {chave!r}") from None


# ----------------------------------------------------------- rentabilidade

def classe_da_taxa(indexador: str) -> str:
    """'Pré-fixado', 'Pós-fixado' ou 'Híbrido (IPCA+)' — o que o usuário quer saber de relance."""
    if indexador == "PRE":
        return "Pré-fixado"
    if indexador in ("CDI", "CDI_MAIS", "SELIC"):
        return "Pós-fixado"
    if indexador == "IPCA":
        return "Híbrido (IPCA+)"
    return "Outro"


def _pct(taxa: Decimal) -> str:
    return f"{taxa.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):f}".replace(".", ",") + "%"


def descrever_rentabilidade(indexador: str, taxa: Decimal | None) -> str:
    """'12,50% a.a.' · '110,00% do CDI' · 'IPCA + 6,20% a.a.' …"""
    if taxa is None:
        return "taxa não informada"
    if indexador == "PRE":
        return f"{_pct(taxa)} a.a."
    if indexador == "CDI":
        return f"{_pct(taxa)} do CDI"
    if indexador == "CDI_MAIS":
        return f"CDI + {_pct(taxa)} a.a."
    if indexador == "SELIC":
        return f"Selic + {_pct(taxa)} a.a."
    if indexador == "IPCA":
        return f"IPCA + {_pct(taxa)} a.a."
    return _pct(taxa)


# ------------------------------------------------------------- IR e prazos

# (até quantos dias, alíquota %) — tabela regressiva do IR sobre renda fixa, contada em dias corridos
FAIXAS_IR: tuple[tuple[int | None, Decimal], ...] = (
    (180, Decimal("22.5")), (360, Decimal("20")), (720, Decimal("17.5")), (None, Decimal("15")),
)
_LIMITES_IR = (180, 360, 720)


def aliquota_ir(dias: int) -> Decimal:
    """Alíquota (%) pela idade do aporte, em dias corridos. 180 d ainda é 22,5%; 181 d já é 20%."""
    for limite, aliquota in FAIXAS_IR:
        if limite is None or dias <= limite:
            return aliquota
    raise AssertionError("inalcançável: a última faixa não tem limite")  # pragma: no cover


def faixa_do_ir(dias: int) -> str:
    """Texto da faixa: 'até 180 dias', '181 a 360 dias'…"""
    if dias <= 180:
        return "até 180 dias"
    if dias <= 360:
        return "181 a 360 dias"
    if dias <= 720:
        return "361 a 720 dias"
    return "acima de 720 dias"


def proxima_faixa(dias: int) -> tuple[int, Decimal] | None:
    """(dias que faltam, nova alíquota) para a próxima redução do IR; None se já está na última faixa."""
    for limite in _LIMITES_IR:
        if dias <= limite:
            return limite + 1 - dias, aliquota_ir(limite + 1)
    return None


def dias_entre(inicio: str, fim: dt.date) -> int:
    return (fim - dt.date.fromisoformat(inicio)).days


# ------------------------------------------------------------------ posição

@dataclass(frozen=True)
class Movimento:
    id: int
    tipo: str            # 'aporte' | 'resgate'
    data: str
    valor: Decimal       # bruto
    custos: Decimal      # IR/IOF/taxas retidos (resgate) ou taxas pagas (aporte)
    nota: str | None


@dataclass(frozen=True)
class PosicaoRF:
    id: int
    tipo: TipoRendaFixa
    nome: str | None
    instituicao: str
    corretora: str | None
    indexador: str
    taxa: Decimal | None
    vencimento: str | None
    liquidez: str
    isento_ir: bool
    valor_atual: Decimal | None       # informado à mão (bruto)
    data_valor_atual: str | None
    observacao: str | None
    movimentos: tuple[Movimento, ...] = field(default_factory=tuple)
    hoje: dt.date = field(default_factory=dt.date.today)

    # --- identificação
    @property
    def titulo(self) -> str:
        return self.nome or self.tipo.nome

    @property
    def aportes(self) -> list[Movimento]:
        return [m for m in self.movimentos if m.tipo == "aporte"]

    @property
    def resgates(self) -> list[Movimento]:
        return [m for m in self.movimentos if m.tipo == "resgate"]

    # --- valores
    @property
    def aportado(self) -> Decimal:
        return sum((m.valor + m.custos for m in self.aportes), ZERO)

    @property
    def resgatado_bruto(self) -> Decimal:
        return sum((m.valor for m in self.resgates), ZERO)

    @property
    def custos_resgates(self) -> Decimal:
        return sum((m.custos for m in self.resgates), ZERO)

    @property
    def encerrada(self) -> bool:
        return self.valor_atual is not None and self.valor_atual == 0

    @property
    def sem_valor_atual(self) -> bool:
        return self.valor_atual is None

    @property
    def valor_efetivo(self) -> Decimal:
        """Valor atual informado; sem ele, o que restou aplicado (sem rendimento)."""
        if self.valor_atual is not None:
            return self.valor_atual
        return max(ZERO, self.aportado - self.resgatado_bruto)

    @property
    def rendimento_bruto(self) -> Decimal:
        return self.valor_efetivo + self.resgatado_bruto - self.aportado

    @property
    def rentabilidade_pct(self) -> Decimal | None:
        return self.rendimento_bruto / self.aportado * _CEM if self.aportado > 0 else None

    # --- prazos
    @property
    def primeiro_aporte(self) -> str | None:
        datas = [m.data for m in self.aportes]
        return min(datas) if datas else None

    @property
    def dias_desde_primeiro_aporte(self) -> int | None:
        return dias_entre(self.primeiro_aporte, self.hoje) if self.primeiro_aporte else None

    @property
    def dias_para_vencimento(self) -> int | None:
        return (dt.date.fromisoformat(self.vencimento) - self.hoje).days if self.vencimento else None

    @property
    def vencida(self) -> bool:
        return self.dias_para_vencimento is not None and self.dias_para_vencimento < 0

    @property
    def progresso_do_prazo(self) -> float | None:
        """0..1: quanto do caminho entre o primeiro aporte e o vencimento já passou."""
        if not (self.primeiro_aporte and self.vencimento):
            return None
        total = (dt.date.fromisoformat(self.vencimento) - dt.date.fromisoformat(self.primeiro_aporte)).days
        if total <= 0:
            return 1.0
        return max(0.0, min(1.0, self.dias_desde_primeiro_aporte / total))

    # --- IR (estimativa)
    @property
    def aliquota_atual(self) -> Decimal | None:
        """Alíquota da faixa em que está o primeiro aporte; 0 se isento; None sem aporte."""
        if self.isento_ir:
            return ZERO
        dias = self.dias_desde_primeiro_aporte
        return aliquota_ir(dias) if dias is not None else None

    @property
    def proxima_reducao(self) -> tuple[int, Decimal, str] | None:
        """(dias que faltam, nova alíquota, data em que acontece) — só se há IR e ainda há faixa a cair."""
        dias = self.dias_desde_primeiro_aporte
        if self.isento_ir or dias is None:
            return None
        prox = proxima_faixa(dias)
        if prox is None:
            return None
        faltam, nova = prox
        return faltam, nova, (self.hoje + dt.timedelta(days=faltam)).isoformat()

    @property
    def ir_estimado(self) -> Decimal:
        """IR sobre o rendimento, repartido entre os aportes proporcionalmente ao valor e cada um na
        sua faixa (aporte mais novo paga mais), menos o que já foi retido nos resgates. Nunca negativo."""
        if self.isento_ir or self.rendimento_bruto <= 0 or self.aportado <= 0:
            return ZERO
        total = ZERO
        for ap in self.aportes:
            peso = (ap.valor + ap.custos) / self.aportado
            total += self.rendimento_bruto * peso * aliquota_ir(dias_entre(ap.data, self.hoje)) / _CEM
        return max(ZERO, total - self.custos_resgates)

    @property
    def liquido_estimado(self) -> Decimal:
        """Quanto sobraria, descontado o IR estimado, se o valor atual fosse resgatado hoje."""
        return self.valor_efetivo - self.ir_estimado


@dataclass(frozen=True)
class ResumoRendaFixa:
    aplicado: Decimal            # aportes das aplicações ativas
    valor_atual: Decimal
    rendimento_bruto: Decimal    # de todas (inclui as encerradas)
    rentabilidade_pct: Decimal | None  # das ativas: rendimento sobre o aportado
    ir_estimado: Decimal
    liquido_estimado: Decimal
    ativas: int
    encerradas: int
    sem_valor_atual: int         # entram pelo valor aplicado, sem rendimento, até o valor ser informado


@dataclass(frozen=True)
class CarteiraRendaFixa:
    posicoes: tuple[PosicaoRF, ...]   # ativas primeiro (vencimento mais próximo antes), depois encerradas
    resumo: ResumoRendaFixa


def montar_posicao(row: Mapping, movimentos: Iterable[Mapping], hoje: dt.date) -> PosicaoRF:
    return PosicaoRF(
        id=row["id"], tipo=tipo_por_chave(row["tipo"]), nome=row["nome"], instituicao=row["instituicao"],
        corretora=row["corretora"], indexador=row["indexador"],
        taxa=Decimal(row["taxa"]) if row["taxa"] not in (None, "") else None,
        vencimento=row["vencimento"], liquidez=row["liquidez"], isento_ir=bool(row["isento_ir"]),
        valor_atual=Decimal(row["valor_atual"]) if row["valor_atual"] not in (None, "") else None,
        data_valor_atual=row["data_valor_atual"], observacao=row["observacao"],
        movimentos=tuple(
            Movimento(m["id"], m["tipo"], m["data"], Decimal(m["valor"]), Decimal(m["custos"] or "0"), m["nota"])
            for m in sorted(movimentos, key=lambda m: (m["data"], m["id"]))
        ),
        hoje=hoje,
    )


def montar_carteira_rf(
    posicoes: Iterable[Mapping], movimentos: Iterable[Mapping], hoje: dt.date | None = None,
) -> CarteiraRendaFixa:
    hoje = hoje or dt.date.today()
    por_posicao: dict[int, list[Mapping]] = {}
    for m in movimentos:
        por_posicao.setdefault(m["posicao_id"], []).append(m)
    itens = [montar_posicao(p, por_posicao.get(p["id"], []), hoje) for p in posicoes]
    itens.sort(key=lambda p: (p.encerrada, p.vencimento or "9999-12-31", p.id))
    ativas = [p for p in itens if not p.encerrada]
    aplicado = sum((p.aportado for p in ativas), ZERO)
    valor = sum((p.valor_efetivo for p in ativas), ZERO)
    rend_ativas = sum((p.rendimento_bruto for p in ativas), ZERO)
    return CarteiraRendaFixa(
        posicoes=tuple(itens),
        resumo=ResumoRendaFixa(
            aplicado=aplicado, valor_atual=valor,
            rendimento_bruto=sum((p.rendimento_bruto for p in itens), ZERO),
            rentabilidade_pct=rend_ativas / aplicado * _CEM if aplicado > 0 else None,
            ir_estimado=sum((p.ir_estimado for p in ativas), ZERO),
            liquido_estimado=sum((p.liquido_estimado for p in ativas), ZERO),
            ativas=len(ativas), encerradas=len(itens) - len(ativas),
            sem_valor_atual=sum(1 for p in ativas if p.sem_valor_atual),
        ),
    )


def validar_posicao(
    *, tipo: str, instituicao: str, indexador: str, taxa: Decimal | None, vencimento: str | None,
    liquidez: str, data_aporte: str | None = None,
) -> None:
    """Levanta ValueError com mensagem legível. `data_aporte` só ao criar (checa o vencimento)."""
    tipo_por_chave(tipo)
    if not (instituicao or "").strip():
        raise ValueError("Informe a instituição (banco, emissor ou Tesouro Nacional).")
    if indexador not in INDEXADORES:
        raise ValueError("Escolha o tipo de rentabilidade.")
    if liquidez not in LIQUIDEZES:
        raise ValueError("Escolha a liquidez.")
    if indexador != "OUTRO" and taxa is None:
        raise ValueError("Informe a taxa de rentabilidade.")
    if taxa is not None and taxa < 0:
        raise ValueError("A taxa não pode ser negativa.")
    if vencimento:
        try:
            venc = dt.date.fromisoformat(vencimento)
        except ValueError:
            raise ValueError("Data de vencimento inválida.") from None
        if data_aporte and venc < dt.date.fromisoformat(data_aporte):
            raise ValueError("O vencimento não pode ser anterior à data da aplicação.")


def validar_movimento(*, tipo: str, data: str, valor: Decimal, custos: Decimal) -> None:
    if tipo not in ("aporte", "resgate"):
        raise ValueError("Escolha aporte ou resgate.")
    try:
        dt.date.fromisoformat(data)
    except ValueError:
        raise ValueError("Data inválida.") from None
    if valor <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    if custos < 0:
        raise ValueError("Os custos não podem ser negativos.")
