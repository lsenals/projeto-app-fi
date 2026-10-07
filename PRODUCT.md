# Product

<!-- impeccable:product-schema 1 -->

## Platform

android

## Users

Usuário único: o próprio desenvolvedor (Leandro), controlando as próprias finanças pessoais
no dia a dia — lançamentos manuais, fechamento mensal, acompanhamento de metas. Não há
multiusuário, autenticação, nem papéis distintos: é um app pessoal, sem lançamento oficial
nem equipe planejados.

## Product Purpose

App financeiro pessoal e gamificado. Existe para tornar o controle financeiro diário menos
enfadonho, usando mecânicas de jogo (Objetivos Inteligentes com "PRs", ofensiva/streak,
Sistema de Nível) sobre uma base sólida de lançamentos, fechamento mensal e relatórios. Desde
2026-10-07 o app é um **hub de módulos**: Finanças pessoais, Investimentos (Cripto, Ações e Renda
Fixa) e Objetivos.
Sucesso é subjetivo — não há métrica de negócio — e é medido por "chegar a um estado pronto
para lançar" caso algum dia isso fizesse sentido, e pelo aprendizado do processo de construir.

## Positioning

Não compete por mercado; a diferenciação é de mecanismo, não de posicionamento comercial.
O que um "concorrente" (um app de finanças genérico) não copiaria sem reformular a proposta:
Objetivos Inteligentes tratados como recordes pessoais (PRs) que geram XP e sobem de Nível,
com ofensiva mensal derivada sempre do histórico real (nunca um contador solto) — a mesma
filosofia se repete em toda a camada de gamificação (`overall_streak`, `calcular_nivel`).

## Operating Context

Fluxos reais de uso: lançamento rápido diário de receitas/despesas; fechamento de mês;
importação de fatura de cartão C6 (arquivo baixado do banco); lançamentos recorrentes
configurados uma vez; exportação de relatório em HTML; acompanhamento de Objetivos
(metas com critério de sucesso, ex.: saldo positivo seguido, redução de categoria, renda
extra) e do Sistema de Nível (no rodapé da Home) e da ofensiva (em Objetivos); carteira de
criptoativos e de ações lançadas à mão, diário de trades realizados e acompanhamento de renda fixa (dias
desde o aporte e faixa de IR), sempre com o preço ou valor atual informado pelo próprio usuário. Uso é 100% local — sem sincronização entre
dispositivos, sem backend, sem internet necessária pro app funcionar.

## Capabilities and Constraints

- **Stack:** Python 3.13 + Flet 0.86.5, single-codebase compilando pra desktop, web e mobile
  (Android primeiro; iOS depende de macOS/Xcode, ainda não perseguido).
- **Dados:** SQLite local em modo WAL, sem backend externo — decisão consciente pra não
  introduzir complexidade de infra/time num projeto solo.
- **Dinheiro:** sempre representado em centavos inteiros (evita bugs de casa decimal),
  formatado via `core/money.py::format_brl`. **Exceção: investimentos** (`core/crypto.py`, que também serve às ações, `core/trades.py` e
  `core/renda_fixa.py`), que usam
  `Decimal` exato — preço de cripto pode ser R$ 0,000021 e a quantidade tem até 8 casas — e têm
  moeda própria por ativo (R$ ou US$), com cotação do dólar informada à mão.
- **Privacidade:** nenhum dado financeiro real ou número de cartão deve aparecer em código,
  testes, specs ou demos — sempre dados fictícios.
- **Mobile:** toolchain Android (Flutter 3.47.4 + SDK) instalada e `flet build apk` validado
  ponta a ponta (2026-09-23 e 2026-10-07). O APK é endurecido: **sem permissão de internet**, sem
  backup automático do Android. Ainda **não testado num aparelho**; será reconstruído ao final de
  todas as alterações em andamento (hub, Cripto, Ações, Renda Fixa, fontes).
- **Sem multiusuário/autenticação** — indefinidamente fora de escopo pro momento atual.

## Brand Commitments

Nome do produto: **Finapple** (trocadilho "Pineapple" + Finanças), definido em 2026-09-15.
O nome técnico do pacote/repositório (`app_fi`/`app-fi`) permanece diferente do nome de
produto por decisão consciente (renomear migraria dados de usuários já existentes — não é
prioridade). Grafia: **"Finapple"** (a minúsculo), em todo o projeto. Logo: abacaxi lapidado
em traço fino com uma fechadura de cofre (`src/assets/logo_finapple.svg`), sem símbolo extra ao
lado do nome. Identidade: grafite e dourado discreto, fontes Sora (títulos) e Manrope (texto).
Paleta, tokens e decisões documentados em `DESIGN.md`, `CLAUDE.md` e no vault Obsidian ("Finapple —
Identidade Visual" e "Finapple — Nova Home (design)"); este arquivo não duplica esses detalhes.

## Evidence on Hand

- Logo SVG em `src/assets/logo_finapple.svg` e fontes em `src/assets/fonts/`. Os mascotes PNG
  antigos (`mascote_*.png`, fase neon de 09/2026) seguem em `src/assets/`, sem uso na interface.
- Design de referência: canvas "Finapple – Nova Home" no claude.ai (sem link automático com o repo;
  endereço no `CLAUDE.md`).
- Nenhum dado financeiro real, depoimento, caso de uso ou métrica de negócio existe ou deve
  ser inventado — é um projeto pessoal sem clientes, sem imprensa, sem benchmarks.

## Product Principles

1. **Núcleo puro, UI fina.** `core/` calcula sem efeito colateral; `main.py` só renderiza —
   nunca o contrário (regra documentada em `CLAUDE.md`).
2. **Derivar, nunca duplicar estado.** Métricas de gamificação (ofensiva, nível) sempre vêm
   do histórico real em `goal_records`, nunca de um contador guardado à parte.
3. **Privacidade em primeiro lugar.** Nenhum dado sensível real em código, testes ou specs.
4. **Sem pressa artificial, com padrão real.** Sem prazo de lançamento, mas qualidade de
   código e organização importam como se houvesse.
5. **Simplicidade de infra.** Sem backend, sem dependência nova sem necessidade clara —
   cada peça a mais pesa no empacotamento mobile.

## Accessibility & Inclusion

Nenhum requisito específico de acessibilidade foi levantado pelo usuário — projeto pessoal,
sem usuário externo conhecido com necessidade declarada. Boas práticas gerais de contraste,
alvo de toque e legibilidade (ex.: os mínimos do Material Design em Android) se aplicam por
padrão de qualidade, não por requisito confirmado.
