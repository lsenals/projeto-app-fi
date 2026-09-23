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
Sistema de Nível) sobre uma base sólida de lançamentos, fechamento mensal e relatórios.
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
extra) e do Sistema de Nível/ofensiva na Home. Uso é 100% local — sem sincronização entre
dispositivos, sem backend, sem internet necessária pro app funcionar.

## Capabilities and Constraints

- **Stack:** Python 3.13 + Flet 0.86.5, single-codebase compilando pra desktop, web e mobile
  (Android primeiro; iOS depende de macOS/Xcode, ainda não perseguido).
- **Dados:** SQLite local em modo WAL, sem backend externo — decisão consciente pra não
  introduzir complexidade de infra/time num projeto solo.
- **Dinheiro:** sempre representado em centavos inteiros (evita bugs de casa decimal),
  formatado via `core/money.py::format_brl`.
- **Privacidade:** nenhum dado financeiro real ou número de cartão deve aparecer em código,
  testes, specs ou demos — sempre dados fictícios.
- **Mobile:** toolchain Android (Flutter 3.47.4 + SDK) já instalada; ainda não existe um
  build `flet build apk` de teste rodado ponta a ponta — é o próximo passo real do projeto.
- **Sem multiusuário/autenticação** — indefinidamente fora de escopo pro momento atual.

## Brand Commitments

Nome do produto: **FinApple** (trocadilho "Pineapple" + Finanças), definido em 2026-09-15.
O nome técnico do pacote/repositório (`app_fi`/`app-fi`) permanece diferente do nome de
produto por decisão consciente (renomear migraria dados de usuários já existentes — não é
prioridade). Mascote: abacaxi ilustrado (cofrinho + moeda de porcentagem é a variante
principal, usada no cabeçalho da Home; há duas variantes reservas sem uso definido ainda —
coroa/escudo/cofre e globo/moedas internacionais). Paleta e identidade visual completa já
documentadas em `CLAUDE.md` e no vault Obsidian ("FinApple — Identidade Visual"); este
arquivo não duplica esses detalhes visuais.

## Evidence on Hand

- Ilustrações do mascote em `src/app_fi/assets/` (`mascote_poupanca.png` processado e
  pronto; `mascote_seguranca.png`/`mascote_global.png` ainda com fundo branco não tratado).
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
