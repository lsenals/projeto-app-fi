# CLAUDE.md — App FI

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
- Sem dependências novas sem necessidade clara — cada pacote a mais é peso extra para
  empacotar no mobile depois. Declarar em `pyproject.toml` (`dependencies`), não só instalar.
- Commits pequenos e descritivos; não commitar `.venv/`, `__pycache__/`, builds, nem
  saída de ferramentas de análise (`graphify-out/`).

## Relação com o vault do Obsidian

Decisões de arquitetura, aprendizados e anotações de produto deste projeto vivem no vault
do Obsidian (`C:\Users\le_se\AI-Projects\Obsidian\Obsidian Vault`, pasta `06-Projects`),
não neste repositório — o repo é só código. Ver `CLAUDE.md` do vault para as convenções
de notas. Ambos ficam abertos juntos no workspace `app-fi.code-workspace`.

## O que evitar

- Não introduzir Kivy, BeeWare ou outro framework de UI em paralelo ao Flet — escolha já
  feita, mudar de framework é uma decisão grande, não um detalhe de implementação.
- Não commitar chaves, tokens ou dados financeiros reais de exemplo — usar dados fictícios
  em qualquer teste/demo.
- Não empacotar para mobile (`flet build apk/ipa`) até o app ter uma funcionalidade mínima
  completa — builds mobile são lentos e não vale iterar por esse caminho ainda.
