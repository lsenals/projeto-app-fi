"""Tela de Renda Fixa — aplicações (Tesouro, CDB, LCI/LCA…) lançadas à mão.

Só desenha e coleta entradas: os cálculos (rentabilidade pré/pós, dias desde o primeiro aporte, faixa e
estimativa de IR) estão em `core/renda_fixa.py` e a gravação em `data/renda_fixa_repo.py`. O app não acessa a
internet, então o **valor atual** de cada aplicação é informado pelo usuário (copiado do extrato).
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Callable
from decimal import Decimal

import flet as ft

from app_fi.core import renda_fixa as core
from app_fi.core.crypto import formatar_pct, formatar_valor, parse_decimal
from app_fi.data import renda_fixa_repo as repo
from app_fi.ui import cores
from app_fi.ui.componentes import APENAS_NUMEROS, botao_data, centralizado, cor, data_br, rotulo_valor, texto_exato

_ROTULO_TAXA = {
    "PRE": "Taxa pré-fixada (% ao ano)",
    "CDI": "Percentual do CDI (ex.: 110)",
    "CDI_MAIS": "Taxa acima do CDI (% ao ano)",
    "SELIC": "Taxa acima da Selic (% ao ano)",
    "IPCA": "Taxa acima do IPCA (% ao ano)",
    "OUTRO": "Taxa (opcional)",
}


def _pill(texto: str, destaque: bool = False) -> ft.Control:
    return ft.Container(
        content=ft.Text(texto, size=10, color=cores.PRIMARIA if destaque else ft.Colors.GREY),
        border=ft.Border.all(1, cores.PRIMARIA if destaque else ft.Colors.GREY_700), border_radius=100,
        padding=ft.Padding(left=8, right=8, top=2, bottom=2),
    )


def _dias(n: int) -> str:
    return f"{n} dia" if abs(n) == 1 else f"{n} dias"


def _aliq(a: Decimal) -> str:
    return f"{a.normalize():f}".replace(".", ",") + "%"


def criar_tela_renda_fixa(
    page: ft.Page, conn: sqlite3.Connection, body: ft.Column, *,
    voltar: Callable, confirmar: Callable[[str], None],
) -> Callable[[], None]:
    """Devolve `montar()`, que desenha a tela de Renda Fixa no `body` do app."""

    # ------------------------------------------------------------ componentes

    def _card_resumo(r: core.ResumoRendaFixa) -> ft.Control:
        avisos: list[ft.Control] = []
        if r.sem_valor_atual:
            avisos.append(ft.Text(
                f"* {r.sem_valor_atual} aplicação(ões) sem valor atual informado — contadas pelo valor aplicado, sem "
                "rendimento. Abra a aplicação e informe o valor do extrato.", size=11, color=cores.SECUNDARIA,
            ))
        avisos.append(ft.Text(
            "IR estimado pela tabela regressiva (22,5% até 180 dias · 20% até 360 · 17,5% até 720 · 15% depois), "
            "contada do aporte. Não inclui IOF nem a marcação a mercado do Tesouro.", size=10, color=ft.Colors.GREY,
        ))
        return ft.Container(
            content=ft.Column([
                ft.Text("Valor atual das aplicações", size=12, color=ft.Colors.GREY),
                ft.Text(formatar_valor(r.valor_atual), size=28, weight=ft.FontWeight.BOLD),
                ft.Row([
                    rotulo_valor("Total aplicado", formatar_valor(r.aplicado)),
                    rotulo_valor("Rendimento bruto", f"{formatar_valor(r.rendimento_bruto)}  ({formatar_pct(r.rentabilidade_pct)})",
                                 cor(r.rendimento_bruto)),
                ]),
                ft.Row([
                    rotulo_valor("IR estimado", formatar_valor(r.ir_estimado)),
                    rotulo_valor("Líquido estimado", formatar_valor(r.liquido_estimado)),
                ]),
                ft.Text(f"{r.ativas} ativa(s)" + (f" · {r.encerradas} encerrada(s)" if r.encerradas else ""),
                        size=11, color=ft.Colors.GREY),
                *avisos,
            ], spacing=10),
            padding=16, border_radius=20, bgcolor=cores.SUPERFICIE,
        )

    def _linha_prazo(p: core.PosicaoRF) -> list[ft.Control]:
        linhas: list[ft.Control] = []
        dias = p.dias_desde_primeiro_aporte
        if dias is not None:
            linhas.append(ft.Row([
                ft.Icon(ft.Icons.HOURGLASS_BOTTOM_ROUNDED, size=14, color=cores.PRIMARIA),
                ft.Text(f"{_dias(dias)} desde o 1º aporte ({data_br(p.primeiro_aporte)})", size=12, expand=True),
            ], spacing=6))
            if p.isento_ir:
                texto_ir = "Isento de IR (pessoa física)"
            else:
                texto_ir = f"IR {_aliq(p.aliquota_atual)} · faixa de {core.faixa_do_ir(dias)}"
                if p.proxima_reducao:
                    faltam, nova, quando = p.proxima_reducao
                    texto_ir += f" · cai para {_aliq(nova)} em {_dias(faltam)} ({data_br(quando)})"
                else:
                    texto_ir += " · menor alíquota"
            linhas.append(ft.Row([
                ft.Icon(ft.Icons.RECEIPT_LONG_ROUNDED, size=14, color=ft.Colors.GREY),
                ft.Text(texto_ir, size=11, color=ft.Colors.GREY, expand=True),
            ], spacing=6))
        if p.vencimento:
            ate = p.dias_para_vencimento
            texto = (f"Venceu há {_dias(-ate)} ({data_br(p.vencimento)})" if p.vencida
                     else f"Vence em {_dias(ate)} ({data_br(p.vencimento)})")
            linhas.append(ft.Row([
                ft.Icon(ft.Icons.EVENT_ROUNDED, size=14, color=ft.Colors.RED if p.vencida else ft.Colors.GREY),
                ft.Text(texto, size=11, color=ft.Colors.RED if p.vencida else ft.Colors.GREY, expand=True),
            ], spacing=6))
            if p.progresso_do_prazo is not None:
                linhas.append(ft.ProgressBar(value=p.progresso_do_prazo, color=cores.PRIMARIA, bgcolor=cores.BORDA,
                                             border_radius=8, bar_height=6))
        return linhas

    def _card_posicao(p: core.PosicaoRF) -> ft.Control:
        chips = [_pill(core.classe_da_taxa(p.indexador), destaque=True)]
        if p.isento_ir:
            chips.append(_pill("Isento de IR"))
        if p.tipo.fgc:
            chips.append(_pill("FGC"))
        chips.append(_pill(core.NOME_LIQUIDEZ[p.liquidez]))
        rend = p.rendimento_bruto
        return ft.Container(
            content=ft.Column([
                ft.Column([
                    ft.Text(p.titulo, size=16, weight=ft.FontWeight.BOLD, font_family=cores.FONTE_TITULO),
                    ft.Text(f"{p.instituicao} · {p.tipo.nome}" + (f" · via {p.corretora}" if p.corretora else ""),
                            size=11, color=ft.Colors.GREY),
                ], spacing=0),
                ft.Row(chips, spacing=6, wrap=True, run_spacing=4),
                ft.Text(core.descrever_rentabilidade(p.indexador, p.taxa), size=14, weight=ft.FontWeight.W_600,
                        color=cores.PRIMARIA),
                ft.Row([
                    rotulo_valor("Aplicado", formatar_valor(p.aportado)),
                    rotulo_valor("Valor atual" + ("*" if p.sem_valor_atual else ""), formatar_valor(p.valor_efetivo)),
                    rotulo_valor(f"Rendimento {formatar_pct(p.rentabilidade_pct)}", formatar_valor(rend), cor(rend)),
                ]),
                *_linha_prazo(p),
            ], spacing=10),
            padding=14, border_radius=16, bgcolor=cores.SUPERFICIE, border=ft.Border.all(1, cores.BORDA), ink=True,
            on_click=lambda e, pid=p.id: abrir_detalhe(pid),
        )

    def _card_encerrada(p: core.PosicaoRF) -> ft.Control:
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(p.titulo, size=14, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{p.instituicao} · encerrada", size=11, color=ft.Colors.GREY),
                ], spacing=0, expand=True),
                rotulo_valor("Rendimento", f"{formatar_valor(p.rendimento_bruto)} ({formatar_pct(p.rentabilidade_pct)})",
                             cor(p.rendimento_bruto)),
            ]),
            padding=12, border_radius=14, bgcolor=cores.SUPERFICIE, ink=True,
            on_click=lambda e, pid=p.id: abrir_detalhe(pid),
        )

    # ------------------------------------------------------------------ tela

    def montar() -> None:
        page.appbar = ft.AppBar(
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=voltar),
            title=ft.Text("Renda Fixa", font_family=cores.FONTE_TITULO, weight=ft.FontWeight.W_600),
        )
        page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD, bgcolor=cores.VERDE_CLARO, tooltip="Nova aplicação",
            on_click=lambda e: abrir_aplicacao(),
        )
        atualizar()

    def atualizar() -> None:
        carteira = repo.load(conn)
        ativas = [p for p in carteira.posicoes if not p.encerrada]
        encerradas = [p for p in carteira.posicoes if p.encerrada]
        if not carteira.posicoes:
            conteudo: list[ft.Control] = [centralizado(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_ROUNDED, size=48, color=cores.SECUNDARIA),
                    ft.Text("Nenhuma aplicação de renda fixa", size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Cadastre um título pelo botão +: tipo (Tesouro, CDB, LCI…), instituição, rentabilidade, "
                        "data e valor do primeiro aporte e vencimento. O app conta os dias desde o aporte e "
                        "mostra a faixa do IR.", size=12, color=ft.Colors.GREY, text_align=ft.TextAlign.CENTER,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                padding=ft.Padding(left=16, right=16, top=48, bottom=16),
            ))]
        else:
            conteudo = [_card_resumo(carteira.resumo)]
            if ativas:
                conteudo += [ft.Text("Minhas aplicações", size=15, weight=ft.FontWeight.BOLD)]
                conteudo += [_card_posicao(p) for p in ativas]
            if encerradas:
                conteudo += [ft.Text("Aplicações encerradas", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY)]
                conteudo += [_card_encerrada(p) for p in encerradas]
        body.controls = [ft.Column([*conteudo, ft.Container(height=72)], spacing=12, scroll=ft.ScrollMode.AUTO,
                                   expand=True)]
        page.update()

    # --------------------------------------------------------------- diálogos

    def _fechar() -> None:
        page.pop_dialog()

    def _campo_numero(rotulo: str, valor: str = "", **kw) -> ft.TextField:
        return ft.TextField(label=rotulo, value=valor, input_filter=APENAS_NUMEROS,
                            keyboard_type=ft.KeyboardType.NUMBER, dense=True, **kw)

    def _erro_texto() -> ft.Text:
        return ft.Text(color=ft.Colors.RED, size=12, visible=False)

    def _mostrar_erro(erro: ft.Text, mensagem: str) -> None:
        erro.value, erro.visible = mensagem, True
        page.update()

    def _depois(voltar_para: int | None, mensagem: str | None = None) -> None:
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

    # -- detalhe

    def abrir_detalhe(posicao_id: int) -> None:
        p = repo.get(conn, posicao_id)
        if p is None:
            return

        def ir(acao: Callable[[], None]) -> Callable:
            def handler(_e) -> None:
                _fechar()
                acao()
            return handler

        linhas_mov = [
            ft.Container(
                content=ft.Row([
                    ft.Text(data_br(m.data), size=12, color=ft.Colors.GREY, width=82),
                    ft.Text("Aporte" if m.tipo == "aporte" else "Resgate", size=12, width=54,
                            color=ft.Colors.GREEN if m.tipo == "aporte" else ft.Colors.RED),
                    ft.Text(formatar_valor(m.valor) + (f" (custos {formatar_valor(m.custos)})" if m.custos > 0 else ""),
                            size=12, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Icon(ft.Icons.EDIT_OUTLINED, size=14, color=ft.Colors.GREY),
                ], spacing=6),
                ink=True, border_radius=6, padding=ft.Padding(left=4, right=4, top=6, bottom=6),
                on_click=lambda e, mid=m.id: (_fechar(), abrir_movimento(posicao_id, movimento_id=mid)),
            )
            for m in reversed(p.movimentos)
        ]
        valor_info = formatar_valor(p.valor_efetivo) + (f" (em {data_br(p.data_valor_atual)})" if p.data_valor_atual else " — não informado")
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text(p.titulo, font_family=cores.FONTE_TITULO),
            content=ft.Column([
                ft.Row([rotulo_valor("Tipo", p.tipo.nome), rotulo_valor("Instituição", p.instituicao)]),
                ft.Row([rotulo_valor("Rentabilidade", f"{core.descrever_rentabilidade(p.indexador, p.taxa)} · {core.classe_da_taxa(p.indexador)}"),
                        rotulo_valor("Liquidez", core.NOME_LIQUIDEZ[p.liquidez])]),
                ft.Row([rotulo_valor("Aplicado", formatar_valor(p.aportado)), rotulo_valor("Valor atual", valor_info)]),
                ft.Row([rotulo_valor("Rendimento bruto", f"{formatar_valor(p.rendimento_bruto)} ({formatar_pct(p.rentabilidade_pct)})",
                                     cor(p.rendimento_bruto)),
                        rotulo_valor("IR estimado", formatar_valor(p.ir_estimado))]),
                ft.Row([rotulo_valor("Líquido estimado", formatar_valor(p.liquido_estimado)),
                        rotulo_valor("Resgatado", formatar_valor(p.resgatado_bruto))]),
                *_linha_prazo(p),
                *([ft.Text(f"Corretora: {p.corretora}", size=11, color=ft.Colors.GREY)] if p.corretora else []),
                *([ft.Text(p.observacao, size=11, italic=True, color=ft.Colors.GREY)] if p.observacao else []),
                ft.Row([
                    ft.FilledButton("Aporte", on_click=ir(lambda: abrir_movimento(posicao_id, "aporte"))),
                    ft.OutlinedButton("Resgate", on_click=ir(lambda: abrir_movimento(posicao_id, "resgate"))),
                ], spacing=8),
                ft.Row([
                    ft.OutlinedButton("Atualizar valor", icon=ft.Icons.PRICE_CHANGE_ROUNDED,
                                      on_click=ir(lambda: abrir_valor(posicao_id))),
                    ft.OutlinedButton("Editar", icon=ft.Icons.EDIT_OUTLINED,
                                      on_click=ir(lambda: abrir_aplicacao(posicao_id))),
                ], spacing=8, wrap=True),
                ft.Divider(),
                ft.Text("Movimentos (toque para editar)", size=12, weight=ft.FontWeight.BOLD),
                ft.Column(linhas_mov, spacing=0, scroll=ft.ScrollMode.AUTO, height=min(180, 44 * len(linhas_mov))),
            ], tight=True, spacing=10, width=380, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Excluir", on_click=ir(lambda: abrir_exclusao(posicao_id)),
                              style=ft.ButtonStyle(color=ft.Colors.RED)),
                ft.TextButton("Fechar", on_click=lambda e: _fechar()),
            ],
        ))

    # -- nova aplicação / editar dados

    def abrir_aplicacao(posicao_id: int | None = None) -> None:
        existente = repo.get(conn, posicao_id) if posicao_id is not None else None
        hoje = dt.date.today()
        estado = {"data": hoje.isoformat(), "venc": existente.vencimento if existente else None}

        tipo_dd = ft.Dropdown(
            label="Tipo de título", editable=True, enable_filter=True, menu_height=320, dense=True,
            options=[ft.DropdownOption(key=t.chave, text=t.nome) for t in core.TIPOS],
            value=existente.tipo.chave if existente else None,
        )
        tipo_info = ft.Text(size=11, color=ft.Colors.GREY)
        nome = ft.TextField(label="Nome (opcional, ex.: CDB Banco X 2028)", dense=True,
                            value=(existente.nome or "") if existente else "")
        instituicao = ft.TextField(label="Instituição (banco ou emissor)", dense=True,
                                   value=existente.instituicao if existente else "")
        corretora = ft.TextField(label="Corretora / plataforma (opcional)", dense=True,
                                 value=(existente.corretora or "") if existente else "")
        indexador_dd = ft.Dropdown(
            label="Rentabilidade", dense=True,
            options=[ft.DropdownOption(key=k, text=core.NOME_INDEXADOR[k]) for k in core.INDEXADORES],
            value=existente.indexador if existente else None, expand=True,
        )
        taxa = _campo_numero(_ROTULO_TAXA[existente.indexador] if existente else "Taxa",
                             texto_exato(existente.taxa) if existente and existente.taxa is not None else "")
        liquidez_dd = ft.Dropdown(
            label="Liquidez", dense=True,
            options=[ft.DropdownOption(key=k, text=core.NOME_LIQUIDEZ[k]) for k in core.LIQUIDEZES],
            value=existente.liquidez if existente else None, expand=True,
        )
        isento = ft.Switch(label="Isento de IR (pessoa física)", value=existente.isento_ir if existente else False)
        valor_aporte = _campo_numero("Valor aplicado (R$)", "", visible=existente is None)
        obs = ft.TextField(label="Observação (opcional)", dense=True, value=(existente.observacao or "") if existente else "")
        erro = _erro_texto()

        botao_aplicacao = botao_data(page, estado, "data", "Data da aplicação (1º aporte)",
                                     primeira=dt.date(2000, 1, 1), ultima=hoje)
        botao_aplicacao.visible = existente is None
        botao_venc = botao_data(page, estado, "venc", "Vencimento", primeira=dt.date(2000, 1, 1),
                                ultima=dt.date(2100, 12, 31))
        sem_venc = ft.TextButton("Sem vencimento")

        def tirar_vencimento(_e) -> None:
            estado["venc"] = None
            botao_venc.content = "Vencimento: não definida"
            page.update()
        sem_venc.on_click = tirar_vencimento

        def descrever_tipo() -> None:
            if not tipo_dd.value:
                tipo_info.value = ""
                return
            t = core.tipo_por_chave(tipo_dd.value)
            tipo_info.value = f"{t.grupo} · " + ("coberto pelo FGC" if t.fgc else "sem FGC") + (
                " · isento de IR para pessoa física" if t.isento_ir else " · IR regressivo")

        def ao_escolher_tipo(_e) -> None:
            # sugere os padrões do tipo (rentabilidade, liquidez, isenção); o usuário ainda pode mudar
            if tipo_dd.value:
                t = core.tipo_por_chave(tipo_dd.value)
                indexador_dd.value, liquidez_dd.value, isento.value = t.indexador, t.liquidez, t.isento_ir
                taxa.label = _ROTULO_TAXA[t.indexador]
            descrever_tipo()
            page.update()

        def ao_escolher_indexador(_e) -> None:
            if indexador_dd.value:
                taxa.label = _ROTULO_TAXA[indexador_dd.value]
            page.update()

        tipo_dd.on_select = ao_escolher_tipo
        indexador_dd.on_select = ao_escolher_indexador
        descrever_tipo()

        def salvar(_e) -> None:
            erro.visible = False
            try:
                if not tipo_dd.value:
                    raise ValueError("Escolha o tipo de título.")
                t = parse_decimal(taxa.value)
                campos = dict(tipo=tipo_dd.value, nome=nome.value, instituicao=instituicao.value or "",
                              corretora=corretora.value, indexador=indexador_dd.value or "", taxa=t,
                              vencimento=estado["venc"], liquidez=liquidez_dd.value or "", isento_ir=isento.value,
                              observacao=obs.value)
                if existente is None:
                    v = parse_decimal(valor_aporte.value)
                    if v is None:
                        raise ValueError("Informe o valor aplicado.")
                    novo = repo.add_posicao(conn, data_aporte=estado["data"], valor_aporte=v, **campos)
                    _depois(None, "Aplicação cadastrada.")
                    abrir_detalhe(novo)
                else:
                    repo.update_posicao(conn, existente.id, **campos)
                    _depois(existente.id, "Dados atualizados.")
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar aplicação" if existente else "Nova aplicação"),
            content=ft.Column([
                tipo_dd, tipo_info, nome, instituicao, corretora, ft.Row([indexador_dd]), taxa, ft.Row([liquidez_dd]), isento,
                botao_aplicacao, valor_aporte, ft.Row([botao_venc, sem_venc], wrap=True, spacing=0), obs, erro,
            ], tight=True, spacing=8, width=380, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: _cancelar(existente.id if existente else None)),
                     ft.FilledButton("Salvar", on_click=salvar)],
        ))

    # -- aporte / resgate (também edita)

    def abrir_movimento(posicao_id: int, tipo: str = "aporte", *, movimento_id: int | None = None) -> None:
        existente = repo.get_movimento(conn, movimento_id) if movimento_id is not None else None
        if existente is not None:
            tipo = existente["tipo"]
        hoje = dt.date.today()
        estado = {"data": existente["data"] if existente else hoje.isoformat()}
        valor = _campo_numero("Valor (R$, bruto)", texto_exato(Decimal(existente["valor"])) if existente else "", autofocus=True)
        custos = _campo_numero(
            "IR, IOF e taxas retidos (R$, opcional)" if tipo == "resgate" else "Taxas pagas (R$, opcional)",
            texto_exato(Decimal(existente["custos"])) if existente and Decimal(existente["custos"]) > 0 else "",
        )
        nota = ft.TextField(label="Observação (opcional)", dense=True, value=(existente["nota"] or "") if existente else "")
        total = ft.Switch(label="Resgate total (encerra a aplicação)", value=False,
                          visible=tipo == "resgate" and existente is None)
        erro = _erro_texto()
        botao = botao_data(page, estado, "data", "Data", primeira=dt.date(2000, 1, 1), ultima=hoje)

        def salvar(_e) -> None:
            erro.visible = False
            try:
                v, c = parse_decimal(valor.value), parse_decimal(custos.value) or Decimal(0)
                if v is None:
                    raise ValueError("Informe o valor.")
                if existente is None:
                    repo.add_movimento(conn, posicao_id, tipo=tipo, data=estado["data"], valor=v, custos=c, nota=nota.value)
                    if total.value:
                        repo.set_valor_atual(conn, posicao_id, Decimal(0), estado["data"])
                else:
                    repo.update_movimento(conn, movimento_id, data=estado["data"], valor=v, custos=c, nota=nota.value)
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            _depois(posicao_id, "Aporte registrado." if tipo == "aporte" else "Resgate registrado.")

        def excluir(_e) -> None:
            try:
                repo.delete_movimento(conn, movimento_id)
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            _depois(posicao_id, "Movimento excluído.")

        acoes = [ft.TextButton("Cancelar", on_click=lambda e: _cancelar(posicao_id)), ft.FilledButton("Salvar", on_click=salvar)]
        if existente is not None:
            acoes.insert(0, ft.TextButton("Excluir", on_click=excluir, style=ft.ButtonStyle(color=ft.Colors.RED)))
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text(("Editar " if existente else "Novo ") + ("aporte" if tipo == "aporte" else "resgate")),
            content=ft.Column([botao, valor, custos, total, nota, erro], tight=True, spacing=8, width=380),
            actions=acoes,
        ))

    # -- valor atual (manual)

    def abrir_valor(posicao_id: int) -> None:
        p = repo.get(conn, posicao_id)
        campo = _campo_numero("Valor atual bruto (R$)", texto_exato(p.valor_atual) if p.valor_atual is not None else "",
                              autofocus=True)
        erro = _erro_texto()

        def salvar(_e) -> None:
            try:
                v = parse_decimal(campo.value)
                if v is None:
                    raise ValueError("Informe o valor atual.")
                repo.set_valor_atual(conn, posicao_id, v)
            except ValueError as ex:
                return _mostrar_erro(erro, str(ex))
            _depois(posicao_id, "Valor atualizado.")

        page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text("Valor atual"),
            content=ft.Column([
                ft.Text("Valor bruto de hoje, como aparece no extrato (antes do IR). Use 0 para marcar a aplicação "
                        "como encerrada.", size=12, color=ft.Colors.GREY), campo, erro,
            ], tight=True, spacing=10, width=380),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: _cancelar(posicao_id)),
                     ft.FilledButton("Salvar", on_click=salvar)],
        ))

    # -- excluir aplicação

    def abrir_exclusao(posicao_id: int) -> None:
        p = repo.get(conn, posicao_id)

        def confirmar_exclusao(_e) -> None:
            repo.delete_posicao(conn, posicao_id)
            _depois(None, "Aplicação excluída.")

        page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text("Excluir aplicação?"),
            content=ft.Text(f"“{p.titulo}” e todos os seus aportes e resgates serão apagados. "
                            "Essa ação não pode ser desfeita.", size=13),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: _cancelar(posicao_id)),
                     ft.FilledButton("Excluir", on_click=confirmar_exclusao,
                                     style=ft.ButtonStyle(bgcolor=ft.Colors.RED, color=ft.Colors.WHITE))],
        ))

    return montar
