"""Carteira de ações — as tabelas `acoes_*` (008_acoes.sql).

Mesmo modelo de Cripto (`CarteiraRepo`), mas **sem catálogo**: os ativos (tickers como PETR4, VALE3,
IVVB11) são cadastrados à mão pelo usuário.
"""

from __future__ import annotations

from app_fi.data.carteira_repo import CarteiraRepo

_repo = CarteiraRepo("acoes")

list_assets = _repo.list_assets
get_asset = _repo.get_asset
add_custom_asset = _repo.add_custom_asset
set_asset_currency = _repo.set_asset_currency
get_usd_rate = _repo.get_usd_rate
set_usd_rate = _repo.set_usd_rate
get_display_currency = _repo.get_display_currency
set_display_currency = _repo.set_display_currency
list_trades = _repo.list_trades
get_trade = _repo.get_trade
add_trade = _repo.add_trade
update_trade = _repo.update_trade
delete_trade = _repo.delete_trade
set_price = _repo.set_price
set_targets = _repo.set_targets
load_wallet = _repo.load_wallet
