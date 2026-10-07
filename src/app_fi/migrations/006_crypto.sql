-- 006_crypto.sql — carteira de criptoativos (lançada à mão; o app não acessa a internet).
--
-- Preços, quantidades e taxas são TEXT com um número decimal exato ('0.00002100'),
-- lidos como Decimal em core/crypto.py: centavos inteiros não cabem em cripto
-- (SHIB custa frações de centavo e a quantidade tem até 8 casas). Valores em reais (BRL).

CREATE TABLE crypto_assets (
    id               INTEGER PRIMARY KEY,
    symbol           TEXT NOT NULL UNIQUE,
    name             TEXT NOT NULL,
    current_price    TEXT,                      -- preço atual por unidade, informado à mão
    price_updated_at TEXT,                      -- 'YYYY-MM-DD' do último preço informado
    target_gain_pct  TEXT,                      -- meta de trade: ganho sobre o preço médio (ex.: '20')
    stop_loss_pct    TEXT,                      -- perda máxima tolerada sobre o preço médio (ex.: '10')
    is_custom        INTEGER NOT NULL DEFAULT 0 -- 1 = cadastrado pelo usuário (fora do catálogo)
);

CREATE TABLE crypto_trades (
    id         INTEGER PRIMARY KEY,
    asset_id   INTEGER NOT NULL REFERENCES crypto_assets(id),
    side       TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    date       TEXT NOT NULL,                   -- 'YYYY-MM-DD'
    quantity   TEXT NOT NULL,
    unit_price TEXT NOT NULL,
    fee        TEXT NOT NULL DEFAULT '0',       -- em reais; entra no custo (compra) ou sai do recebido (venda)
    note       TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_crypto_trades_asset ON crypto_trades (asset_id, date);

-- Cada preço informado vira um ponto: é o que alimenta o gráfico de evolução.
CREATE TABLE crypto_price_history (
    id       INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES crypto_assets(id),
    date     TEXT NOT NULL,
    price    TEXT NOT NULL,
    UNIQUE (asset_id, date)
);

-- Catálogo dos principais criptoativos (espelha core.crypto.CATALOGO_PRINCIPAIS).
INSERT INTO crypto_assets (symbol, name) VALUES
    ('BTC', 'Bitcoin'), ('ETH', 'Ethereum'), ('USDT', 'Tether'), ('XRP', 'XRP'),
    ('BNB', 'BNB'), ('SOL', 'Solana'), ('USDC', 'USD Coin'), ('DOGE', 'Dogecoin'),
    ('ADA', 'Cardano'), ('TRX', 'TRON'), ('LINK', 'Chainlink'), ('AVAX', 'Avalanche'),
    ('XLM', 'Stellar'), ('SHIB', 'Shiba Inu'), ('BCH', 'Bitcoin Cash'), ('TON', 'Toncoin'),
    ('DOT', 'Polkadot'), ('LTC', 'Litecoin'), ('HBAR', 'Hedera'), ('UNI', 'Uniswap'),
    ('POL', 'Polygon'), ('NEAR', 'NEAR Protocol'), ('APT', 'Aptos'), ('ICP', 'Internet Computer'),
    ('ETC', 'Ethereum Classic'), ('AAVE', 'Aave'), ('ATOM', 'Cosmos'), ('ALGO', 'Algorand'),
    ('FIL', 'Filecoin'), ('ARB', 'Arbitrum'), ('OP', 'Optimism'), ('SUI', 'Sui'),
    ('INJ', 'Injective'), ('VET', 'VeChain'), ('XMR', 'Monero'), ('PEPE', 'Pepe'),
    ('DAI', 'Dai'), ('RNDR', 'Render'), ('SAND', 'The Sandbox'), ('MANA', 'Decentraland');
