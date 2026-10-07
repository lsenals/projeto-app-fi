-- 008_acoes_e_trades.sql — carteira de ações e diário de trades realizados.
--
-- 1) Ações: mesmo modelo de Cripto (006/007), tabelas com as mesmas colunas e o prefixo `acoes_`.
--    Sem catálogo: os tickers (PETR4, VALE3, IVVB11…) são cadastrados à mão. Preços, quantidades e
--    taxas são TEXT com número decimal exato (lidos como Decimal em core/crypto.py, que é genérico).
--
-- 2) trades_realizados: diário de trades já encerrados, de Cripto e de Ações (a coluna `modulo` separa
--    os dois). É um registro manual à parte do livro de operações — serve para lançar trades feitos
--    antes de usar o app ou fora da carteira. lucro = valor_venda − valor_compra − custos (calculado
--    em core/trades.py, não guardado).

CREATE TABLE acoes_assets (
    id               INTEGER PRIMARY KEY,
    symbol           TEXT NOT NULL UNIQUE,
    name             TEXT NOT NULL,
    current_price    TEXT,
    price_updated_at TEXT,
    target_gain_pct  TEXT,
    stop_loss_pct    TEXT,
    is_custom        INTEGER NOT NULL DEFAULT 0,
    currency         TEXT NOT NULL DEFAULT 'BRL'
);

CREATE TABLE acoes_trades (
    id         INTEGER PRIMARY KEY,
    asset_id   INTEGER NOT NULL REFERENCES acoes_assets(id),
    side       TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    date       TEXT NOT NULL,
    quantity   TEXT NOT NULL,
    unit_price TEXT NOT NULL,
    fee        TEXT NOT NULL DEFAULT '0',
    note       TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_acoes_trades_asset ON acoes_trades (asset_id, date);

CREATE TABLE acoes_price_history (
    id       INTEGER PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES acoes_assets(id),
    date     TEXT NOT NULL,
    price    TEXT NOT NULL,
    UNIQUE (asset_id, date)
);

CREATE TABLE trades_realizados (
    id           INTEGER PRIMARY KEY,
    modulo       TEXT NOT NULL CHECK (modulo IN ('cripto', 'acoes')),
    symbol       TEXT NOT NULL,
    name         TEXT,
    currency     TEXT NOT NULL DEFAULT 'BRL',
    quantity     TEXT,                    -- opcional: informativo
    buy_date     TEXT NOT NULL,
    buy_value    TEXT NOT NULL,           -- valor total pago na compra (na moeda do trade)
    sell_date    TEXT NOT NULL,
    sell_value   TEXT NOT NULL,           -- valor total recebido na venda
    costs        TEXT NOT NULL DEFAULT '0',  -- taxas, corretagem, impostos pagos
    note         TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_trades_realizados_modulo ON trades_realizados (modulo, sell_date);
