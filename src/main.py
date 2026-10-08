"""Launcher fino usado só pelo `flet build` (Android/iOS/web empacotado).

O Flet exige um `main.py` direto na pasta apontada por `tool.flet.app.path`
(ver pyproject.toml). O app de verdade mora em `app_fi/main.py`, que continua
sendo o ponto de entrada usado no desenvolvimento desktop
(`python src/app_fi/main.py`) — este arquivo não substitui aquele, só permite
que o build encontre um entry point sem forçar `app_fi/` a virar a raiz do
bundle (o que quebraria os imports absolutos `from app_fi.xxx import ...`
usados em todo o projeto).

No aparelho o Python executa ESTE arquivo uma vez e o app só fica de pé enquanto
ele roda: por isso o `ft.run` precisa estar aqui, sem `if __name__ == "__main__"`
(só importar `main`, como era antes, fazia o app abrir e fechar na hora).
"""

from pathlib import Path

import flet as ft

from app_fi.main import main

# assets (logo, fontes) ficam ao lado deste arquivo: src/assets no código, assets/ no bundle
ft.run(main, assets_dir=str(Path(__file__).parent / "assets"))
