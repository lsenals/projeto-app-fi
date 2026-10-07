# CLAUDE.md — FinApple

O produto se chama **FinApple** (nome + identidade visual definidos em 2026-09-15,
detalhes em Obsidian > 06-Projects > FinApple — Identidade Visual). O repositório,
pacote Python (`app_fi`) e pasta de dados do usuário (`%LOCALAPPDATA%\app-fi`)
continuam com o nome técnico antigo — renomear isso é uma decisão à parte, ainda
não tomada, porque implicaria migrar dados de quem já usa o app.

Projeto pessoal: app financeiro mobile em **Python + Flet**. Sem lançamento oficial nem
equipe planejados, mas o objetivo é levar até um estado "pronto para lançar" — ou seja,
qualidade de código e organização importam, mesmo sem pressão de prazo real.

## Stack

- **Python 3.13**, ambiente virtual em `.venv/` (não versionado).
- **Flet** (`pip install flet`) — UI declarativa em Python, compila para mobile
  (Android/iOS), web e desktop a partir do mesmo código.
- Sem backend externo por enquanto — dados locais primeiro; se precisar de API/backend
  separado no futuro, discutir antes de introduzir.

## Estrutura do projeto

```
projeto-app-fi/
├── src/app_fi/
│   ├── main.py       → ponto de entrada (ft.app)
│   ├── ui/           → telas e componentes visuais (Flet controls)
│   ├── core/         → lógica de domínio (cálculos financeiros, regras)
│   └── data/         → persistência (arquivos locais, banco embutido, etc.)
├── tests/            → testes (pytest)
├── .vscode/          → settings.json + launch.json versionados
├── pyproject.toml    → metadados do pacote + dependências diretas + config do pytest
└── requirements.txt  → só a dep direta (flet); pyproject.toml é a fonte de verdade
```

Regra geral: **`ui/` nunca deve conter lógica financeira** — telas só chamam funções de
`core/`. Isso mantém a lógica testável sem precisar renderizar UI.

## Comandos

```bash
# ativar o venv (PowerShell)
.venv\Scripts\Activate.ps1

# instalar o projeto em modo editável (uma vez, e após mudar dependências)
pip install -e ".[dev]"

# rodar o app (modo desktop, mais rápido para desenvolver)
python src/app_fi/main.py

# rodar testes
pytest

# adicionar uma dependência nova: editar `dependencies` no pyproject.toml,
# refletir no requirements.txt e reinstalar
pip install -e ".[dev]"
```

## Convenções

- Funções e módulos em `core/` devem ser puros sempre que possível (entrada → saída, sem
  efeito colateral) — facilita testar cálculos financeiros sem mockar nada.
- Nomes de variáveis monetárias sempre explícitos sobre a unidade (`valor_reais`, não
  `valor`) — evita bugs de casas decimais/moeda mais adiante.
- **Exceção à regra de centavos: criptoativos** (`core/crypto.py`, `data/crypto_repo.py`, tabelas
  `crypto_*`). Preço de cripto pode ser R$ 0,000021 e a quantidade tem até 8 casas, então ali tudo é
  `Decimal` (TEXT no banco) e só os totais exibidos são arredondados a centavos. Método de custo:
  preço médio. Sem internet, o preço atual é informado à mão (cada preço vira um ponto do histórico
  que alimenta o gráfico de evolução). **Moeda por ativo (BRL ou USD)**: todos os valores de um ativo
  ficam na moeda dele (lucro % sem ruído de câmbio); só o resumo converte para a moeda de exibição
  (alternância R$/US$ na tela), usando a cotação do dólar **informada à mão** (`app_settings`:
  `usd_brl`, `crypto_display_currency`) — vale a cotação de hoje para todo o histórico. A moeda do
  ativo só pode ser trocada antes da 1ª operação. O catálogo de ativos está duplicado de propósito em
  `006_crypto.sql` e `CATALOGO_PRINCIPAIS` — um teste garante que não divirjam.
- Telas novas vão em `src/app_fi/ui/` (uma função `criar_tela_x(...)` que devolve `montar()`), com a
  paleta em `ui/cores.py`; `main.py` só liga a aba/rota.
- Sem dependências novas sem necessidade clara — cada pacote a mais é peso extra para
  empacotar no mobile depois. Declarar em `pyproject.toml` (`dependencies`), não só instalar.
- Commits pequenos e descritivos; não commitar `.venv/`, `__pycache__/`, builds, nem
  saída de ferramentas de análise (`graphify-out/`).

## Relação com o vault do Obsidian

Decisões de arquitetura, aprendizados e anotações de produto deste projeto vivem no vault
do Obsidian (`C:\Users\le_se\AI-Projects\Obsidian\Obsidian Vault`, pasta `06-Projects`),
não neste repositório — o repo é só código. Ver `CLAUDE.md` do vault para as convenções
de notas. Ambos ficam abertos juntos no workspace `app-fi.code-workspace`.

## Design e paleta

Em 2026-10-07 a marca mudou para **grafite e dourado discreto** (vinda do canvas de design
"FinApple – Nova Home", no claude.ai: https://claude.ai/artifact/GsMnTt1H4npwX6GNsfxLiv, fonte da
verdade visual — não há link automático com o repositório). Tokens em `src/app_fi/ui/cores.py`
(nunca hardcodar hex nas telas), logo em `src/assets/logo_finapple.svg`. Decisões em aberto (Home em
hub, grupo "Investimentos", fontes Sora/Manrope, barra inferior) em Obsidian > 06-Projects >
`FinApple — Nova Home (design)`. O `DESIGN.md` e o `PRODUCT.md` ainda descrevem a paleta neon antiga.

## O que evitar

- Não introduzir Kivy, BeeWare ou outro framework de UI em paralelo ao Flet — escolha já
  feita, mudar de framework é uma decisão grande, não um detalhe de implementação.
- Não commitar chaves, tokens ou dados financeiros reais de exemplo — usar dados fictícios
  em qualquer teste/demo.

## Mobile

**v1.0.0 (2026-09-15) fechou o escopo desktop/web** — a partir daqui, mobile (Android
primeiro, iOS depois) é o próximo passo real, não mais bloqueado. Já corrigidos os dois
pontos do código que dependiam do Windows: `data/db.py::default_db_path()` (usa
`FLET_APP_STORAGE_DATA`, que o Flet expõe automaticamente num app empacotado, antes de
cair no fallback `%LOCALAPPDATA%`) e o "abrir relatório exportado" em `main.py` (usa
`os.startfile` só no Windows; `page.launch_url()` nas outras plataformas).

`flet build apk` roda em qualquer SO com Flutter + Android SDK instalados — dá pra gerar o
APK direto no Windows. `flet build ipa` exige macOS com Xcode; sem isso, iOS fica pra depois
(Mac físico ou CI com runner macOS). Builds mobile ainda são lentos pra iterar — prefira
testar via `ft.AppView.WEB_BROWSER`/desktop primeiro e só buildar pra Android quando quiser
validar algo que só existe no dispositivo de verdade (permissões, file picker nativo, etc.).

**Toolchain Android instalado em 2026-09-15** (`flutter doctor` limpo, exceto Visual Studio —
irrelevante, é só pra app Windows nativo):
- Flutter 3.47.4 stable em `C:\src\flutter` (não versionado, é infra da máquina)
- Android SDK em `%LOCALAPPDATA%\Android\Sdk`: cmdline-tools, platform-tools, platform
  android-36, build-tools 28.0.3 e 34.0.0
- JDK 17 (já existia em `C:\Program Files\Java\jdk-17`)
- Variáveis de usuário: `JAVA_HOME`, `ANDROID_HOME`, `ANDROID_SDK_ROOT`, PATH com
  `flutter\bin`, `Sdk\platform-tools` e `Sdk\cmdline-tools\latest\bin`

Pra rodar `flet build apk`, abrir um terminal **novo** (as variáveis são de usuário, uma
sessão já aberta antes da instalação não as tem).

**Primeiro `flet build apk` de teste rodado com sucesso em 2026-09-23** (APK em
`build/apk/finapple.apk`, ~54MB, `--org com.finapple --product FinApple --project finapple
--arch arm64-v8a`). `flet build` gerencia a própria versão pinada do Flutter, separada da
instalada em `C:\src\flutter` — baixou Flutter 3.44.8 em `C:\Users\le_se\flutter\3.44.8` na
primeira execução (normal, não é um erro). Três bloqueios de ambiente encontrados e
resolvidos nessa primeira tentativa:
- Console do Windows em `cp1252` quebra com o emoji `✅` que o Flet imprime — rodar com
  `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` no ambiente.
- O wrapper novo do Android CLI (que substituiu o `sdkmanager` legado) trocou a sintaxe de
  pacote de `platforms;android-35` pra `platforms/android-35` (`;` → `/`). O instalador
  interno do `flet build` ainda usa a sintaxe antiga e falha ao tentar instalar
  automaticamente — instalar manualmente antes, com a sintaxe nova:
  `sdkmanager.bat "platforms/android-35"` e `"build-tools/35.0.0"`.
- Flutter precisa criar symlinks mesmo em build Android — exige o **Modo de Desenvolvedor**
  do Windows ativado (`start ms-settings:developers`).

**Layout `src/` exigiu um launcher fino** — `flet build` exige um `main.py` direto na pasta
apontada por `[tool.flet.app] path`, e essa pasta vira a raiz do app empacotado. Como
`app_fi/main.py` usa imports absolutos (`from app_fi.core import ...`) em todo o projeto,
apontar `path` direto pra `src/app_fi/` quebraria esses imports em runtime (o conteúdo viraria
a raiz, sem a pasta `app_fi/` para resolver). Solução: `path = "src"` (preserva `app_fi/` como
pacote real dentro do bundle) + `src/main.py` como launcher fino (`from app_fi.main import
main`) só para o build encontrar um entry point. `python src/app_fi/main.py` continua sendo o
comando de desenvolvimento desktop, sem mudança.

## Assets (imagens)

Ficam em **`src/assets/`** (não dentro do pacote `app_fi/` — mudou em 2026-09-23). Motivo:
o `flet build` também exige que os assets fiquem ao lado do `main.py` que ele usa
(`src/main.py`, ver seção Mobile acima), então um único diretório fora do pacote serve tanto
o desktop quanto o build mobile. `main.py` passa `assets_dir` explícito pro `ft.run()`
(`Path(__file__).parent.parent / "assets"`) em vez de depender do padrão implícito do Flet,
que resolve via `sys.argv[0]` e quebra quando o arquivo é importado por outro script (como o
launcher de build) ou testado via `python -c "..."`.

Mascotes do abacaxi (2026-09-15, ilustrações fornecidas pelo usuário):
- `mascote_poupanca.png` — o principal, usado no cabeçalho de boas-vindas/Nível da Home.
  As ilustrações originais vêm em JPEG com fundo branco sólido; em vez de deixar
  transparente (primeira tentativa — funcionava, mas decidimos que pintar com a cor do
  app fica mais natural, sem risco de halo/anti-aliasing nas bordas), o fundo é **pintado
  com a cor exata do app** (`#263238`, a mesma de `_COR_FUNDO`). Processo: BFS com critério
  de "quase branco" (não o `ImageDraw.floodfill` do Pillow, que compara pixel a pixel
  contra a cor da semente e deixa sobras) a partir de toda a borda da imagem, **mais**
  qualquer bolsão de fundo isolado internamente (ex: o vão entre o braço e a moeda) —
  identificado inspecionando o tamanho de cada bolsão branco encontrado (os pequenos, tipo
  brilho dos olhos e dentes, são partes do personagem e não devem ser preenchidos). Usei
  `Pillow` temporariamente no venv só pra esse processamento, **não é dependência do app**
  (não entrou no `pyproject.toml`, não é importado em nenhum lugar do código).
- `mascote_seguranca.png` e `mascote_global.png` — variantes (coroa/escudo/cofre; globo/
  moedas internacionais), ainda **com fundo branco** — se forem usadas na UI, precisam do
  mesmo tratamento de remoção de fundo.
