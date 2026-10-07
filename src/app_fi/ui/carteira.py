"""Tela de uma carteira de ativos negociados lançada à mão — serve a Cripto e a Ações.

Só desenha e coleta entradas: todo cálculo está em `core/crypto.py` (genérico) e `core/trades.py`, e toda
gravação nos repositórios (`CarteiraRepo`, `trades_realizados_repo`) — regra do projeto: `ui/` não tem
lógica financeira. O app não acessa a internet, então o preço atual de cada ativo é informado pelo
usuário (botão "Atualizar preços"). Cada módulo passa o seu repositório e a sua `ConfigCarteira`.

Abaixo da carteira há a seção "Trades realizados": o diário de trades já encerrados (valor e data de
compra e de venda, custos e lucro final), lançado à mão e separado do livro de operações.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

import flet as ft

from app_fi.core import crypto as core
from app_fi.core import trades as core_trades
from app_fi.data import trades_realizados_repo as trades_repo
from app_fi.ui import cores

_APENAS_NUMEROS = ft.InputFilter(regex_string=r"^[0-9.,]*$", allow=True)
_MAX_BARRAS = 10


def _data_br(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"


def _data_curta(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[2:4]}"


def _texto_exato(valor: Decimal) -> str:
    """Valor para pré-preencher um campo de edição, sem arredondar: 0.000021 -> '0,000021',
    1234.567 -> '1234,567' (o formato de exibição arredondaria a centavos e alteraria o dado ao salvar)."""
    texto = f"{valor.normalize():f}"
    return texto.replace(".", ",")


def _cor(valor: Decimal | None) -> str:
    if valor is None or valor == 0:
        return ft.Colors.GREY
    return ft.Colors.GREEN if valor > 0 else ft.Colors.RED


def _rotulo_valor(rotulo: str, valor: str, cor: str | None = None, destaque: bool = False) -> ft.Control:
    return ft.Column(
        [
            ft.Text(rotulo, size=11, color=ft.Colors.GREY),
            ft.Text(valor, size=15 if destaque else 13, weight=ft.FontWeight.BOLD, color=cor, max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS),
        ],
        spacing=2, expand=True,
    )


@dataclass(frozen=True)
class ConfigCarteira:
    """O que muda de um módulo para outro (textos e ícone); a lógica é a mesma."""
    modulo: str            # 'cripto' | 'acoes' — também separa os trades realizados
    titulo: str
    icone: str
    vazio_titulo: str
    vazio_texto: str
    texto_cadastrar: str   # botão para cadastrar um ativo que não está na lista
    ticker_exemplo: str
    nome_exemplo: str


def criar_tela_carteira(
    page: ft.Page, conn: sqlite3.Connection, body: ft.Column, *,
    repo, config: ConfigCarteira, voltar: Callable, confirmar: Callable[[str], None],
) -> Callable[[], None]:
    """Devolve `montar()`, que desenha a tela do módulo no `body` do app. `repo` é o módulo de
    repositório do módulo (`crypto_repo` ou `acoes_repo`)."""

    # ------------------------------------------------------------ componentes

    def _card_resumo(r: core.ResumoCarteira, cotacao: Decimal | None, tem_ativo_em_dolar: bool) -> ft.Control:
        m = r.moeda

        def fmt(valor: Decimal) -> str:
            return core.formatar_valor(valor, m)

        avisos: list[ft.Control] = []
        if r.ativos_sem_preco:
            avisos.append(ft.Text(
                f"{r.ativos_sem_preco} ativo(s) sem preço atual — contados pelo custo até você "
                "informar o preço (botão no topo).", size=11, color=cores.SECUNDARIA,
            ))
        if r.ativos_sem_cotacao:
            avisos.append(ft.Text(
                f"{r.ativos_sem_cotacao} ativo(s) em outra moeda ficaram fora dos totais: informe a "
                "cotação do dólar abaixo.", size=11, color=ft.Colors.RED,
            ))

        def trocar_moeda(e: ft.ControlEvent) -> None:
            repo.set_display_currency(conn, e.control.selected[0] if e.control.selected else "BRL")
            atualizar()

        seletor_moeda = ft.SegmentedButton(
            segments=[ft.Segment(value="BRL", label=ft.Text("R$")), ft.Segment(value="USD", label=ft.Text("US$"))],
            selected=[m], on_change=trocar_moeda, show_selected_icon=False,
        )
        texto_cotacao = (
            f"Cotação do dólar: {core.formatar_preco(cotacao)}" if cotacao is not None
            else "Cotação do dólar: não informada"
        )
        precisa_cotacao = tem_ativo_em_dolar or m == "USD"
        return ft.Container(
            content=ft.Column([
                ft.Row([ft.Text("Valor atual da carteira", size=12, color=ft.Colors.GREY, expand=True), seletor_moeda]),
                ft.Text(fmt(r.valor_atual), size=28, weight=ft.FontWeight.BOLD),
                ft.Row([
                    _rotulo_valor("Total investido", fmt(r.investido)),
                    _rotulo_valor(
                        "Lucro / prejuízo", f"{fmt(r.lucro_nao_realizado)}  ({core.formatar_pct(r.lucro_pct)})",
                        _cor(r.lucro_nao_realizado),
                    ),
                ]),
                ft.Row([
                    _rotulo_valor("Já realizado (vendas)", fmt(r.realizado), _cor(r.realizado)),
                    _rotulo_valor("Resultado total", fmt(r.resultado_total), _cor(r.resultado_total)),
                ]),
                ft.TextButton(
                    texto_cotacao, icon=ft.Icons.CURRENCY_EXCHANGE_ROUNDED, on_click=lambda e: abrir_cotacao(),
                    style=ft.ButtonStyle(color=cores.SECUNDARIA if precisa_cotacao and cotacao is None else None),
                ),
                *avisos,
            ], spacing=10),
            padding=16, border_radius=20, bgcolor=cores.SUPERFICIE,
        )

    def _card_evolucao(pontos: tuple[core.PontoEvolucao, ...], moeda: str) -> ft.Control:
        titulo = ft.Text(f"Evolução da carteira ({core.simbolo_moeda(moeda)})", size=14, weight=ft.FontWeight.BOLD)
        if len(pontos) < 2:
            corpo: list[ft.Control] = [ft.Text(
                "Informe o preço dos ativos em dias diferentes (botão no topo) para acompanhar a "
                "evolução do valor da carteira.", size=12, italic=True, color=ft.Colors.GREY,
            )]
        else:
            recentes = pontos[-_MAX_BARRAS:]
            teto = max(max(p.valor, p.investido) for p in recentes) or Decimal(1)
            altura = 110
            barras = [
                ft.Column([
                    ft.Container(
                        height=max(4, int(altura * float(p.valor / teto))), width=22, border_radius=4,
                        bgcolor=ft.Colors.GREEN if p.valor >= p.investido else ft.Colors.RED,
                        tooltip=f"{_data_br(p.data)}: {core.formatar_valor(p.valor, moeda)}",
                    ),
                    ft.Text(f"{p.data[8:10]}/{p.data[5:7]}", size=9, color=ft.Colors.GREY),
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.END)
                for p in recentes
            ]
            ultimo, primeiro = pontos[-1], pontos[0]
            variacao = (ultimo.valor - ultimo.investido)
            corpo = [
                ft.Container(
                    content=ft.Row(barras, alignment=ft.MainAxisAlignment.SPACE_AROUND,
                                   vertical_alignment=ft.CrossAxisAlignment.END),
                    height=altura + 20,
                ),
                ft.Text(
                    f"Verde: valor acima do investido · vermelho: abaixo. Desde {_data_br(primeiro.data)}; "
                    f"hoje {core.formatar_valor(ultimo.valor, moeda)} para "
                    f"{core.formatar_valor(ultimo.investido, moeda)} investidos "
                    f"({core.formatar_valor(variacao, moeda)}).",
                    size=11, color=ft.Colors.GREY,
                ),
            ]
        return ft.Container(
            content=ft.Column([titulo, *corpo], spacing=10),
            padding=16, border_radius=20, bgcolor=cores.SUPERFICIE,
        )

    def _bloco_meta(a: core.AtivoCarteira) -> list[ft.Control]:
        m = a.meta
        if m is None:
            return []
        linhas: list[ft.Control] = []
        if m.preco_alvo is not None:
            if m.atingiu_alvo:
                estado = ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=cores.SECUNDARIA, size=16),
                    ft.Text(f"Meta de +{a.ganho_alvo_pct:f}% atingida! Alvo {core.formatar_preco(m.preco_alvo, a.moeda)}",
                            size=12, color=cores.SECUNDARIA, weight=ft.FontWeight.BOLD),
                ], spacing=6)
            else:
                falta = f" · faltam {core.formatar_pct(m.falta_pct)} no preço" if m.falta_pct is not None else ""
                estado = ft.Text(
                    f"Meta +{a.ganho_alvo_pct:f}% → alvo {core.formatar_preco(m.preco_alvo, a.moeda)}{falta}",
                    size=12, color=ft.Colors.GREY,
                )
            linhas += [
                estado,
                ft.ProgressBar(value=m.ratio, color=cores.SECUNDARIA if m.atingiu_alvo else cores.PRIMARIA,
                               bgcolor=ft.Colors.GREY_800, border_radius=8, bar_height=8),
            ]
        if m.preco_stop is not None:
            linhas.append(ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED if m.atingiu_stop else ft.Icons.FLAG_ROUNDED,
                        color=ft.Colors.RED if m.atingiu_stop else ft.Colors.GREY, size=14),
                ft.Text(
                    f"Stop -{a.stop_pct:f}% ({core.formatar_preco(m.preco_stop, a.moeda)})"
                    + (" — atingido!" if m.atingiu_stop else ""),
                    size=11, color=ft.Colors.RED if m.atingiu_stop else ft.Colors.GREY,
                ),
            ], spacing=4))
        return linhas

    def _card_ativo(a: core.AtivoCarteira) -> ft.Control:
        pos, av = a.posicao, a.avaliacao
        if av is not None:
            selo = ft.Container(
                content=ft.Text(core.formatar_pct(av.lucro_pct), size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                bgcolor=ft.Colors.GREEN if (av.lucro or 0) >= 0 else ft.Colors.RED,
                border_radius=100, padding=ft.Padding(left=10, right=10, top=3, bottom=3),
            )
        else:
            selo = ft.Text("sem preço atual", size=11, italic=True, color=cores.SECUNDARIA)
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Row([
                            ft.Text(a.simbolo, size=17, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Text(core.simbolo_moeda(a.moeda), size=10, color=ft.Colors.GREY),
                                border=ft.Border.all(1, ft.Colors.GREY_700), border_radius=6,
                                padding=ft.Padding(left=5, right=5, top=1, bottom=1),
                            ),
                        ], spacing=8),
                        ft.Text(a.nome, size=11, color=ft.Colors.GREY),
                    ], spacing=0, expand=True),
                    selo,
                ]),
                ft.Row([
                    _rotulo_valor("Quantidade", core.formatar_quantidade(pos.quantidade)),
                    _rotulo_valor("Preço médio", core.formatar_preco(pos.preco_medio, a.moeda)),
                    _rotulo_valor("Preço atual", core.formatar_preco(a.preco_atual, a.moeda) if a.preco_atual else "—"),
                ]),
                ft.Row([
                    _rotulo_valor("Investido", core.formatar_valor(pos.custo_total, a.moeda)),
                    _rotulo_valor("Valor atual", core.formatar_valor(av.valor_atual, a.moeda) if av else "—"),
                    _rotulo_valor("Lucro", core.formatar_valor(av.lucro, a.moeda) if av else "—", _cor(av.lucro if av else None)),
                ]),
                *_bloco_meta(a),
            ], spacing=10),
            padding=14, border_radius=16, bgcolor=cores.SUPERFICIE, ink=True,
            on_click=lambda e, ativo_id=a.id: abrir_detalhe(ativo_id),
        )

    def _card_encerrado(a: core.AtivoCarteira) -> ft.Control:
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(a.simbolo, size=14, weight=ft.FontWeight.BOLD),
                    ft.Text("posição encerrada", size=11, color=ft.Colors.GREY),
                ], spacing=0, expand=True),
                _rotulo_valor(
                    "Resultado realizado", core.formatar_valor(a.posicao.realizado, a.moeda), _cor(a.posicao.realizado),
                ),
            ]),
            padding=12, border_radius=14, bgcolor=cores.SUPERFICIE, ink=True,
            on_click=lambda e, ativo_id=a.id: abrir_detalhe(ativo_id),
        )

    # ------------------------------------------------------------------ tela

    def montar() -> None:
        page.appbar = ft.AppBar(
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=voltar),
            title=ft.Text(config.titulo, font_family=cores.FONTE_TITULO, weight=ft.FontWeight.W_600),
            actions=[ft.IconButton(
                icon=ft.Icons.PRICE_CHANGE_ROUNDED, tooltip="Atualizar preços", on_click=lambda e: abrir_precos(),
            )],
        )
        page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD, bgcolor=cores.VERDE_CLARO, tooltip="Registrar compra ou venda",
            on_click=lambda e: abrir_operacao(),
        )
        atualizar()

    def atualizar() -> None:
        carteira = repo.load_wallet(conn)
        abertos = [a for a in carteira.ativos if a.em_carteira]
        encerrados = [a for a in carteira.ativos if not a.em_carteira]
        if not carteira.ativos:
            conteudo: list[ft.Control] = [ft.Container(
                content=ft.Column([
                    ft.Icon(config.icone, size=48, color=cores.SECUNDARIA),
                    ft.Text(config.vazio_titulo, size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(config.vazio_texto, size=12, color=ft.Colors.GREY, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                padding=ft.Padding(left=16, right=16, top=48, bottom=16),
            )]
        else:
            conteudo = [
                _card_resumo(carteira.resumo, repo.get_usd_rate(conn), any(a.moeda == "USD" for a in carteira.ativos)),
                _card_evolucao(carteira.evolucao, carteira.resumo.moeda),
            ]
            if abertos:
                conteudo += [ft.Text("Minha carteira", size=15, weight=ft.FontWeight.BOLD)]
                conteudo += [_card_ativo(a) for a in abertos]
            if encerrados:
                conteudo += [ft.Text("Posições encerradas", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY)]
                conteudo += [_card_encerrado(a) for a in encerrados]
        conteudo += _secao_trades()  # o diário de trades existe mesmo com a carteira vazia
        body.controls = [ft.Column(
            [*conteudo, ft.Container(height=72)],  # folga: o + não cobre o último card
            spacing=12, scroll=ft.ScrollMode.AUTO, expand=True,
        )]
        page.update()

    # --------------------------------------------------------------- diálogos

    def _fechar() -> None:
        page.pop_dialog()

    def _campo_numero(rotulo: str, valor: str = "", **kw) -> ft.TextField:
        return ft.TextField(
            label=rotulo, value=valor, input_filter=_APENAS_NUMEROS,
            keyboard_type=ft.KeyboardType.NUMBER, dense=True, **kw,
        )

    def _erro_texto() -> ft.Text:
        return ft.Text(color=ft.Colors.RED, size=12, visible=False)

    def _mostrar_erro(erro: ft.Text, mensagem: str) -> None:
        erro.value, erro.visible = mensagem, True
        page.update()

    def _depois(voltar_para: int | None, mensagem: str | None = None) -> None:
        """Fecha o diálogo atual, atualiza a tela e, se veio do detalhe de um ativo, volta para ele."""
        _fechar()
        atualizar()
        if mensagem:
            confirmar(mensagem)
        if voltar_para is not None:
            abrir_detalhe(voltar_para)

    def _cancelar(voltar_para: int | None) -> None:
        _fechar()
        if voltar_para is not None:
            abrir_detalhe(voltar_para)

    # -- detalhe do ativo

    def abrir_detalhe(ativo_id: int) -> None:
        a = next((x for x in repo.load_wallet(conn).ativos if x.id == ativo_id), None)
        if a is None:
            return
        pos, av = a.posicao, a.avaliacao

        def ir(acao: Callable[[], None]) -> Callable:
            def handler(_e) -> None:
                _fechar()
                acao()
            return handler

        linhas_ops = [
            ft.Container(
                content=ft.Row([
                    ft.Text(_data_br(op.data), size=12, color=ft.Colors.GREY, width=82),
                    ft.Text("Compra" if op.lado == "buy" else "Venda", size=12, width=50,
                            color=ft.Colors.GREEN if op.lado == "buy" else ft.Colors.RED),
                    ft.Text(f"{core.formatar_quantidade(op.quantidade)} × {core.formatar_preco(op.preco_unitario, a.moeda)}",
                            size=12, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Icon(ft.Icons.EDIT_OUTLINED, size=14, color=ft.Colors.GREY),
                ], spacing=6),
                ink=True, border_radius=6, padding=ft.Padding(left=4, right=4, top=6, bottom=6),
                on_click=lambda e, tid=op.id: (_fechar(), abrir_operacao(trade_id=tid, voltar_para=ativo_id)),
            )
            for op in reversed(a.operacoes)
        ]
        info = [
            _rotulo_valor("Quantidade", core.formatar_quantidade(pos.quantidade)),
            _rotulo_valor("Preço médio", core.formatar_preco(pos.preco_medio, a.moeda) if pos.quantidade > 0 else "—"),
        ]
        info2 = [
            _rotulo_valor("Preço atual", core.formatar_preco(a.preco_atual, a.moeda) if a.preco_atual else "—"),
            _rotulo_valor("Atualizado em", _data_br(a.data_preco) if a.data_preco else "—"),
        ]
        info3 = [
            _rotulo_valor("Lucro não realizado", core.formatar_valor(av.lucro, a.moeda) if av else "—", _cor(av.lucro if av else None)),
            _rotulo_valor("Realizado", core.formatar_valor(pos.realizado, a.moeda), _cor(pos.realizado)),
        ]
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text(f"{a.simbolo} · {a.nome}"),
            content=ft.Column([
                ft.Row(info), ft.Row(info2), ft.Row(info3),
                *_bloco_meta(a),
                ft.Row([
                    ft.FilledButton("Comprar", on_click=ir(lambda: abrir_operacao(ativo_id, "buy", voltar_para=ativo_id))),
                    ft.OutlinedButton("Vender", on_click=ir(lambda: abrir_operacao(ativo_id, "sell", voltar_para=ativo_id)),
                                      disabled=pos.quantidade <= 0),
                ], spacing=8),
                ft.Row([
                    ft.OutlinedButton("Atualizar preço", icon=ft.Icons.PRICE_CHANGE_ROUNDED,
                                      on_click=ir(lambda: abrir_preco(ativo_id))),
                    ft.OutlinedButton("Meta", icon=ft.Icons.FLAG_ROUNDED,
                                      on_click=ir(lambda: abrir_meta(ativo_id)), disabled=pos.quantidade <= 0),
                ], spacing=8, wrap=True),
                ft.Divider(),
                ft.Text("Operações (toque para editar)", size=12, weight=ft.FontWeight.BOLD),
                ft.Column(linhas_ops, spacing=0, scroll=ft.ScrollMode.AUTO, height=min(200, 44 * len(linhas_ops))),
            ], tight=True, spacing=10, width=380, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Fechar", on_click=lambda e: _fechar())],
        ))

    # -- nova operação (compra / venda), também usada para editar

    def abrir_operacao(
        ativo_id: int | None = None, lado: str = "buy", *, trade_id: int | None = None,
        voltar_para: int | None = None,
    ) -> None:
        existente = repo.get_trade(conn, trade_id) if trade_id is not None else None
        if existente is not None:
            ativo_id, lado = existente["asset_id"], existente["side"]
        estado = {"lado": lado, "data": existente["date"] if existente else dt.date.today().isoformat()}

        ativos = repo.list_assets(conn)
        moeda_ativo = {x["id"]: x["currency"] for x in ativos}
        # a moeda só pode ser escolhida enquanto o ativo não tem operações (depois, os números já
        # lançados ficariam reinterpretados em outra moeda)
        estado["moeda"] = moeda_ativo.get(ativo_id) or repo.get_display_currency(conn)
        ativo_dd = ft.Dropdown(
            label="Ativo", editable=True, enable_filter=True, menu_height=320, dense=True,
            options=[ft.DropdownOption(key=str(x["id"]), text=f"{x['symbol']} — {x['name']}") for x in ativos],
            value=str(ativo_id) if ativo_id is not None else None,
            disabled=existente is not None,
        )
        qtd = _campo_numero("Quantidade", _texto_exato(Decimal(existente["quantity"])) if existente else "")
        preco = _campo_numero(
            "Preço unitário", _texto_exato(Decimal(existente["unit_price"])) if existente else "",
        )
        taxa = _campo_numero(
            "Taxa (opcional)",
            _texto_exato(Decimal(existente["fee"])) if existente and Decimal(existente["fee"]) > 0 else "",
        )
        moeda_info = ft.Text(size=11, color=ft.Colors.GREY, visible=False)

        def moeda_editavel() -> bool:
            return existente is None and bool(ativo_dd.value) and not repo.list_trades(conn, int(ativo_dd.value))

        def aplicar_moeda() -> None:
            simbolo = core.simbolo_moeda(estado["moeda"])
            preco.label, taxa.label = f"Preço unitário ({simbolo})", f"Taxa ({simbolo}, opcional)"
            moeda_btn.selected = [estado["moeda"]]
            moeda_btn.disabled = not moeda_editavel()
            moeda_info.visible = bool(ativo_dd.value) and moeda_btn.disabled
            moeda_info.value = f"Este ativo é negociado em {simbolo}; a moeda não muda depois da 1ª operação."

        def trocar_moeda(e: ft.ControlEvent) -> None:
            estado["moeda"] = e.control.selected[0] if e.control.selected else estado["moeda"]
            aplicar_moeda()
            recalcular()

        moeda_btn = ft.SegmentedButton(
            segments=[ft.Segment(value="BRL", label=ft.Text("R$ (real)")), ft.Segment(value="USD", label=ft.Text("US$ (dólar)"))],
            selected=[estado["moeda"]], on_change=trocar_moeda, show_selected_icon=False,
        )

        def ao_escolher_ativo(_e) -> None:
            if ativo_dd.value:
                estado["moeda"] = moeda_ativo[int(ativo_dd.value)]
            aplicar_moeda()
            recalcular()

        ativo_dd.on_select = ao_escolher_ativo
        nota = ft.TextField(label="Observação (opcional)", dense=True, value=(existente["note"] or "") if existente else "")
        total = ft.Text(size=12, color=ft.Colors.GREY)
        erro = _erro_texto()
        data_botao = ft.TextButton(f"Data: {_data_br(estado['data'])}", icon=ft.Icons.CALENDAR_MONTH_ROUNDED)

        def recalcular(_e=None) -> None:
            try:
                q, p, t = core.parse_decimal(qtd.value), core.parse_decimal(preco.value), core.parse_decimal(taxa.value)
            except ValueError:
                total.value = ""
            else:
                if q and p:
                    bruto = q * p
                    liquido = bruto + (t or 0) if estado["lado"] == "buy" else bruto - (t or 0)
                    rotulo = "Total a pagar" if estado["lado"] == "buy" else "Total a receber"
                    total.value = f"{rotulo}: {core.formatar_valor(liquido, estado['moeda'])}"
                else:
                    total.value = ""
            page.update()

        for campo in (qtd, preco, taxa):
            campo.on_change = recalcular

        def escolher_data(e: ft.ControlEvent) -> None:
            valor = e.data if e.data is not None else e.control.value
            if valor is None:
                return
            estado["data"] = valor[:10] if isinstance(valor, str) else valor.isoformat()[:10]
            data_botao.content = f"Data: {_data_br(estado['data'])}"
            page.update()

        seletor = ft.DatePicker(
            value=dt.date.fromisoformat(estado["data"]), first_date=dt.date(2009, 1, 1),
            last_date=dt.date.today(), on_change=escolher_data,
        )
        data_botao.on_click = lambda e: page.show_dialog(seletor)

        def trocar_lado(e: ft.ControlEvent) -> None:
            estado["lado"] = e.control.selected[0] if e.control.selected else "buy"
            recalcular()

        lado_btn = ft.SegmentedButton(
            segments=[ft.Segment(value="buy", label=ft.Text("Compra")), ft.Segment(value="sell", label=ft.Text("Venda"))],
            selected=[estado["lado"]], on_change=trocar_lado,
        )

        def novo_ativo(_e) -> None:
            _fechar()
            abrir_novo_ativo(lambda novo_id: abrir_operacao(novo_id, estado["lado"], voltar_para=voltar_para),
                             lambda: abrir_operacao(ativo_id, estado["lado"], voltar_para=voltar_para),
                             estado["moeda"])

        def salvar(_e) -> None:
            erro.visible = False
            if not ativo_dd.value:
                return _mostrar_erro(erro, "Escolha o ativo.")
            try:
                q, p = core.parse_decimal(qtd.value), core.parse_decimal(preco.value)
                t = core.parse_decimal(taxa.value) or Decimal(0)
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            if q is None or p is None:
                return _mostrar_erro(erro, "Informe a quantidade e o preço unitário.")
            campos = dict(side=estado["lado"], date=estado["data"], quantity=q, unit_price=p, fee=t,
                          note=(nota.value or "").strip() or None)
            try:
                if existente is None:
                    if moeda_editavel() and estado["moeda"] != moeda_ativo[int(ativo_dd.value)]:
                        repo.set_asset_currency(conn, int(ativo_dd.value), estado["moeda"])
                    repo.add_trade(conn, asset_id=int(ativo_dd.value), **campos)
                else:
                    repo.update_trade(conn, trade_id, **campos)
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            _depois(voltar_para, "Operação registrada." if existente is None else "Operação atualizada.")

        def excluir(_e) -> None:
            try:
                repo.delete_trade(conn, trade_id)
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            _depois(voltar_para, "Operação excluída.")

        acoes = [
            ft.TextButton("Cancelar", on_click=lambda e: _cancelar(voltar_para)),
            ft.FilledButton("Salvar", on_click=salvar),
        ]
        if existente is not None:
            acoes.insert(0, ft.TextButton("Excluir", on_click=excluir, style=ft.ButtonStyle(color=ft.Colors.RED)))
        aplicar_moeda()
        recalcular_inicial = existente is not None
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar operação" if existente else "Nova operação"),
            content=ft.Column([
                lado_btn, ativo_dd,
                ft.TextButton(config.texto_cadastrar, on_click=novo_ativo, visible=existente is None),
                moeda_btn, moeda_info,
                qtd, preco, taxa, data_botao, nota, total, erro,
            ], tight=True, spacing=8, width=380, scroll=ft.ScrollMode.AUTO),
            actions=acoes,
        ))
        if recalcular_inicial:
            recalcular()

    def abrir_novo_ativo(ao_criar: Callable[[int], None], ao_cancelar: Callable[[], None], moeda: str = "BRL") -> None:
        simbolo = ft.TextField(label=f"Símbolo (ex.: {config.ticker_exemplo})", dense=True, capitalization=ft.TextCapitalization.CHARACTERS)
        nome = ft.TextField(label=f"Nome (ex.: {config.nome_exemplo})", dense=True)
        moeda_btn = ft.SegmentedButton(
            segments=[ft.Segment(value="BRL", label=ft.Text("R$ (real)")), ft.Segment(value="USD", label=ft.Text("US$ (dólar)"))],
            selected=[moeda], show_selected_icon=False,
        )
        erro = _erro_texto()

        def salvar(_e) -> None:
            try:
                novo = repo.add_custom_asset(
                    conn, simbolo.value or "", nome.value or "", moeda_btn.selected[0] if moeda_btn.selected else "BRL",
                )
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            _fechar()
            ao_criar(novo)

        def cancelar(_e) -> None:
            _fechar()
            ao_cancelar()

        page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text("Novo ativo"),
            content=ft.Column([simbolo, nome, ft.Text("Moeda em que você negocia este ativo", size=12, color=ft.Colors.GREY), moeda_btn, erro], tight=True, spacing=10, width=380),
            actions=[ft.TextButton("Cancelar", on_click=cancelar), ft.FilledButton("Cadastrar", on_click=salvar)],
        ))

    # -- preço atual (um ativo) e em lote

    def abrir_preco(ativo_id: int) -> None:
        a = repo.get_asset(conn, ativo_id)
        atual = Decimal(a["current_price"]) if a["current_price"] else None
        simbolo_m = core.simbolo_moeda(a["currency"])
        campo = _campo_numero(f"Preço atual ({simbolo_m})", _texto_exato(atual) if atual else "", autofocus=True)
        erro = _erro_texto()

        def salvar(_e) -> None:
            try:
                p = core.parse_decimal(campo.value)
                if p is None:
                    raise ValueError("Informe o preço.")
                repo.set_price(conn, ativo_id, p)
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            _depois(ativo_id, "Preço atualizado.")

        page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text(f"Preço de {a['symbol']}"),
            content=ft.Column([
                ft.Text(f"Preço de 1 unidade em {'dólares' if a['currency'] == 'USD' else 'reais'}, hoje.", size=12, color=ft.Colors.GREY), campo, erro,
            ], tight=True, spacing=10, width=380),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: _cancelar(ativo_id)),
                     ft.FilledButton("Salvar", on_click=salvar)],
        ))

    def abrir_precos() -> None:
        abertos = [a for a in repo.load_wallet(conn).ativos if a.em_carteira]
        if not abertos:
            confirmar("Registre uma compra primeiro para poder informar preços.")
            return
        campos = {
            a.id: _campo_numero(
                f"{a.simbolo} ({core.simbolo_moeda(a.moeda)})", _texto_exato(a.preco_atual) if a.preco_atual else "",
                helper=f"Atualizado em {_data_br(a.data_preco)}" if a.data_preco else "Ainda sem preço",
            )
            for a in abertos
        }
        erro = _erro_texto()

        def salvar(_e) -> None:
            novos: dict[int, Decimal] = {}
            for ativo_id, campo in campos.items():
                try:
                    valor = core.parse_decimal(campo.value)
                except ValueError as ex:
                    return _mostrar_erro(erro, f"{campo.label}: {ex}")
                if valor is not None:
                    novos[ativo_id] = valor
            try:
                for ativo_id, valor in novos.items():
                    repo.set_price(conn, ativo_id, valor)
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            _depois(None, "Preços atualizados.")

        page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text("Atualizar preços"),
            content=ft.Column(
                [ft.Text("Preço de 1 unidade, na moeda de cada ativo, hoje.", size=12, color=ft.Colors.GREY), *campos.values(), erro],
                tight=True, spacing=10, width=380, scroll=ft.ScrollMode.AUTO, height=min(460, 80 * len(campos) + 80),
            ),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: _fechar()), ft.FilledButton("Salvar", on_click=salvar)],
        ))

    # -- cotação do dólar (manual: o app não acessa a internet)

    def abrir_cotacao() -> None:
        atual = repo.get_usd_rate(conn)
        campo = _campo_numero("Quantos reais vale 1 dólar (R$)", _texto_exato(atual) if atual else "", autofocus=True)
        erro = _erro_texto()

        def salvar(_e) -> None:
            try:
                valor = core.parse_decimal(campo.value)
                if valor is None:
                    raise ValueError("Informe a cotação.")
                repo.set_usd_rate(conn, valor)
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            _depois(None, "Cotação do dólar atualizada.")

        page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text("Cotação do dólar"),
            content=ft.Column([
                ft.Text(
                    "Usada para somar na carteira os ativos em dólar e em real. Vale a cotação de hoje "
                    "para todo o histórico (não a do dia de cada compra). Atualize quando quiser.",
                    size=12, color=ft.Colors.GREY,
                ), campo, erro,
            ], tight=True, spacing=10, width=380),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: _fechar()), ft.FilledButton("Salvar", on_click=salvar)],
        ))

    # -- meta de trade

    def abrir_meta(ativo_id: int) -> None:
        a = next(x for x in repo.load_wallet(conn).ativos if x.id == ativo_id)
        medio = a.posicao.preco_medio
        ganho = _campo_numero("Meta de ganho (%) sobre o preço médio",
                              f"{a.ganho_alvo_pct:f}" if a.ganho_alvo_pct is not None else "", autofocus=True)
        stop = _campo_numero("Stop: perda máxima (%) — opcional",
                             f"{a.stop_pct:f}" if a.stop_pct is not None else "")
        previa = ft.Text(size=12, color=ft.Colors.GREY)
        erro = _erro_texto()

        def recalcular(_e=None) -> None:
            partes = []
            try:
                g, s = core.parse_decimal(ganho.value), core.parse_decimal(stop.value)
            except ValueError:
                g = s = None
            if g is not None:
                partes.append(f"Alvo: {core.formatar_preco(medio * (1 + g / 100), a.moeda)}")
            if s is not None:
                partes.append(f"Stop: {core.formatar_preco(medio * (1 - s / 100), a.moeda)}")
            previa.value = " · ".join(partes)
            page.update()

        ganho.on_change = stop.on_change = recalcular

        def salvar(_e) -> None:
            try:
                repo.set_targets(conn, ativo_id, core.parse_decimal(ganho.value), core.parse_decimal(stop.value))
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            _depois(ativo_id, "Meta salva.")

        def remover(_e) -> None:
            repo.set_targets(conn, ativo_id, None, None)
            _depois(ativo_id, "Metas removidas.")

        page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text(f"Meta de trade — {a.simbolo}"),
            content=ft.Column([
                ft.Text(f"Seu preço médio é {core.formatar_preco(medio, a.moeda)}. A meta é calculada sobre ele "
                        f"(ex.: 20% → alvo de {core.formatar_preco(medio * Decimal('1.2'), a.moeda)}).",
                        size=12, color=ft.Colors.GREY),
                ganho, stop, previa, erro,
            ], tight=True, spacing=10, width=380),
            actions=[
                ft.TextButton("Remover", on_click=remover, style=ft.ButtonStyle(color=ft.Colors.RED)),
                ft.TextButton("Cancelar", on_click=lambda e: _cancelar(ativo_id)),
                ft.FilledButton("Salvar", on_click=salvar),
            ],
        ))
        recalcular()

    # ----------------------------------------------------- trades realizados

    def _secao_trades() -> list[ft.Control]:
        trades = trades_repo.list_trades(conn, config.modulo)
        resumo = core_trades.resumir_trades(trades, repo.get_display_currency(conn), repo.get_usd_rate(conn))
        m = resumo.moeda
        cabecalho = ft.Row([
            ft.Column([
                ft.Text("Trades realizados", size=15, weight=ft.FontWeight.BOLD),
                ft.Text("Diário de trades já encerrados, à parte das operações acima.", size=11, color=ft.Colors.GREY),
            ], spacing=0, expand=True),
            ft.TextButton("Registrar", icon=ft.Icons.ADD, on_click=lambda e: abrir_trade_realizado()),
        ], vertical_alignment=ft.CrossAxisAlignment.START)
        if not trades:
            return [ft.Container(height=8), cabecalho, ft.Text(
                "Nenhum trade registrado. Lance o valor e a data de compra e de venda, os custos e veja o lucro final.",
                size=12, italic=True, color=ft.Colors.GREY,
            )]
        avisos = [ft.Text(
            f"{resumo.sem_cotacao} trade(s) em outra moeda ficaram fora do total: informe a cotação do dólar.",
            size=11, color=ft.Colors.RED,
        )] if resumo.sem_cotacao else []
        card_resumo = ft.Container(
            content=ft.Column([
                ft.Row([
                    _rotulo_valor("Lucro final", f"{core.formatar_valor(resumo.lucro_total, m)}  ({core.formatar_pct(resumo.lucro_pct)})",
                                  _cor(resumo.lucro_total)),
                    _rotulo_valor("Custos pagos", core.formatar_valor(resumo.custos_total, m)),
                ]),
                ft.Row([
                    _rotulo_valor("Trades", f"{resumo.total}"),
                    _rotulo_valor(
                        "Taxa de acerto",
                        f"{resumo.taxa_acerto:.0f}%  ({resumo.vitorias} de {resumo.total})" if resumo.taxa_acerto is not None else "—",
                    ),
                ]),
                *avisos,
            ], spacing=10),
            padding=14, border_radius=16, bgcolor=cores.SUPERFICIE, border=ft.Border.all(1, cores.BORDA),
        )
        linhas = [
            ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text(t.simbolo, size=14, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{_data_curta(t.data_compra)} → {_data_curta(t.data_venda)} · {t.dias} d",
                                size=11, color=ft.Colors.GREY),
                    ], spacing=0, expand=True),
                    ft.Column([
                        ft.Text(core.formatar_valor(t.lucro, t.moeda), size=13, weight=ft.FontWeight.BOLD, color=_cor(t.lucro)),
                        ft.Text(core.formatar_pct(t.lucro_pct), size=11, color=_cor(t.lucro)),
                    ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.END),
                    ft.Icon(ft.Icons.EDIT_OUTLINED, size=14, color=ft.Colors.GREY),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding(left=14, right=14, top=10, bottom=10), ink=True,
                on_click=lambda e, tid=t.id: abrir_trade_realizado(tid),
            )
            for t in trades
        ]
        itens: list[ft.Control] = []
        for i, linha in enumerate(linhas):
            if i:
                itens.append(ft.Divider(height=1, thickness=1, color=cores.BORDA))
            itens.append(linha)
        lista = ft.Container(
            content=ft.Column(itens, spacing=0), bgcolor=cores.SUPERFICIE, border_radius=16,
            border=ft.Border.all(1, cores.BORDA), clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        return [ft.Container(height=8), cabecalho, card_resumo, lista]

    def abrir_trade_realizado(trade_id: int | None = None) -> None:
        existente = trades_repo.get_trade(conn, trade_id) if trade_id is not None else None
        hoje = dt.date.today().isoformat()
        estado = {
            "moeda": existente.moeda if existente else repo.get_display_currency(conn),
            "compra": existente.data_compra if existente else hoje,
            "venda": existente.data_venda if existente else hoje,
        }
        simbolo = ft.TextField(
            label=f"Ativo (ex.: {config.ticker_exemplo})", dense=True, value=existente.simbolo if existente else "",
            capitalization=ft.TextCapitalization.CHARACTERS,
        )
        qtd = _campo_numero("Quantidade (opcional)", _texto_exato(existente.quantidade) if existente and existente.quantidade else "")
        valor_compra = _campo_numero("Valor da compra (total)", _texto_exato(existente.valor_compra) if existente else "")
        valor_venda = _campo_numero("Valor da venda (total)", _texto_exato(existente.valor_venda) if existente else "")
        custos = _campo_numero("Custos da operação (opcional)",
                               _texto_exato(existente.custos) if existente and existente.custos > 0 else "")
        nota = ft.TextField(label="Observação (opcional)", dense=True, value=(existente.nota or "") if existente else "")
        previa = ft.Text(size=12, color=ft.Colors.GREY)
        erro = _erro_texto()

        def rotular() -> None:
            s = core.simbolo_moeda(estado["moeda"])
            valor_compra.label, valor_venda.label = f"Valor da compra — total em {s}", f"Valor da venda — total em {s}"
            custos.label = f"Custos da operação em {s} (opcional)"

        def recalcular(_e=None) -> None:
            try:
                c, v, k = (core.parse_decimal(valor_compra.value), core.parse_decimal(valor_venda.value),
                           core.parse_decimal(custos.value) or Decimal(0))
            except ValueError:
                c = v = None
                k = Decimal(0)
            if c and c > 0 and v is not None:
                lucro = v - c - k
                previa.value = f"Lucro final: {core.formatar_valor(lucro, estado['moeda'])} ({core.formatar_pct(lucro / c * 100)})"
                previa.color = _cor(lucro)
            else:
                previa.value = ""
            page.update()

        for campo in (valor_compra, valor_venda, custos):
            campo.on_change = recalcular

        def trocar_moeda(e: ft.ControlEvent) -> None:
            estado["moeda"] = e.control.selected[0] if e.control.selected else estado["moeda"]
            rotular()
            recalcular()

        moeda_btn = ft.SegmentedButton(
            segments=[ft.Segment(value="BRL", label=ft.Text("R$ (real)")), ft.Segment(value="USD", label=ft.Text("US$ (dólar)"))],
            selected=[estado["moeda"]], on_change=trocar_moeda, show_selected_icon=False,
        )

        def botao_data(chave: str, prefixo: str) -> ft.TextButton:
            botao = ft.TextButton(f"{prefixo}: {_data_br(estado[chave])}", icon=ft.Icons.CALENDAR_MONTH_ROUNDED)

            def escolher(e: ft.ControlEvent) -> None:
                valor = e.data if e.data is not None else e.control.value
                if valor is None:
                    return
                estado[chave] = valor[:10] if isinstance(valor, str) else valor.isoformat()[:10]
                botao.content = f"{prefixo}: {_data_br(estado[chave])}"
                page.update()

            seletor = ft.DatePicker(
                value=dt.date.fromisoformat(estado[chave]), first_date=dt.date(2009, 1, 1),
                last_date=dt.date.today(), on_change=escolher,
            )
            botao.on_click = lambda e: page.show_dialog(seletor)
            return botao

        botao_compra, botao_venda = botao_data("compra", "Data da compra"), botao_data("venda", "Data da venda")

        def salvar(_e) -> None:
            erro.visible = False
            try:
                c, v = core.parse_decimal(valor_compra.value), core.parse_decimal(valor_venda.value)
                k = core.parse_decimal(custos.value) or Decimal(0)
                q = core.parse_decimal(qtd.value)
                if c is None or v is None:
                    raise ValueError("Informe o valor da compra e o da venda.")
                campos = dict(simbolo=simbolo.value or "", moeda=estado["moeda"], quantidade=q,
                              data_compra=estado["compra"], valor_compra=c, data_venda=estado["venda"],
                              valor_venda=v, custos=k, nota=nota.value)
                if existente is None:
                    trades_repo.add_trade(conn, modulo=config.modulo, **campos)
                else:
                    trades_repo.update_trade(conn, existente.id, **campos)
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            _depois(None, "Trade registrado." if existente is None else "Trade atualizado.")

        def excluir(_e) -> None:
            trades_repo.delete_trade(conn, existente.id)
            _depois(None, "Trade excluído.")

        acoes_dialogo = [ft.TextButton("Cancelar", on_click=lambda e: _fechar()), ft.FilledButton("Salvar", on_click=salvar)]
        if existente is not None:
            acoes_dialogo.insert(0, ft.TextButton("Excluir", on_click=excluir, style=ft.ButtonStyle(color=ft.Colors.RED)))
        rotular()
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar trade" if existente else "Novo trade realizado"),
            content=ft.Column([
                simbolo, moeda_btn, qtd, botao_compra, valor_compra, botao_venda, valor_venda, custos, nota, previa, erro,
            ], tight=True, spacing=8, width=380, scroll=ft.ScrollMode.AUTO),
            actions=acoes_dialogo,
        ))
        if existente is not None:
            recalcular()

    return montar
