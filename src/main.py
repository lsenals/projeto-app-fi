"""Launcher fino usado só pelo `flet build` (Android/iOS/web empacotado).

O Flet exige um `main.py` direto na pasta apontada por `tool.flet.app.path`
(ver pyproject.toml). O app de verdade mora em `app_fi/main.py`, que continua
sendo o ponto de entrada usado no desenvolvimento desktop
(`python src/app_fi/main.py`) — este arquivo não substitui aquele, só permite
que o build encontre um entry point sem forçar `app_fi/` a virar a raiz do
bundle (o que quebraria os imports absolutos `from app_fi.xxx import ...`
usados em todo o projeto).
"""

from app_fi.main import main
