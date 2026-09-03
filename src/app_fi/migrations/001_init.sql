-- 001_init.sql — schema inicial do App FI
-- Valores monetários: sempre INTEGER em centavos, positivos. O sinal vem de `kind`.
-- Datas: TEXT no formato ISO 'YYYY-MM-DD' (sem hora).

CREATE TABLE accounts (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL,
    type      TEXT    NOT NULL CHECK (type IN ('cash', 'investment', 'property')),
    archived  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE categories (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL UNIQUE,
    archived  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE income_sources (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL UNIQUE,
    archived  INTEGER NOT NULL DEFAULT 0
);

-- Memória "estabelecimento -> categoria": ao digitar um payee conhecido,
-- a UI sugere default_category_id.
CREATE TABLE payees (
    id                  INTEGER PRIMARY KEY,
    name                TEXT    NOT NULL UNIQUE,
    default_category_id INTEGER REFERENCES categories(id)
);

CREATE TABLE recurring (
    id                    INTEGER PRIMARY KEY,
    label                 TEXT    NOT NULL,
    kind                  TEXT    NOT NULL CHECK (kind IN ('expense', 'income')),
    expected_amount_cents INTEGER NOT NULL CHECK (expected_amount_cents > 0),
    category_id           INTEGER REFERENCES categories(id),
    income_source_id      INTEGER REFERENCES income_sources(id),
    account_id            INTEGER NOT NULL REFERENCES accounts(id),
    interval_unit         TEXT    NOT NULL DEFAULT 'month' CHECK (interval_unit IN ('month', 'week')),
    interval_count        INTEGER NOT NULL DEFAULT 1 CHECK (interval_count > 0),
    next_date             TEXT    NOT NULL,
    active                INTEGER NOT NULL DEFAULT 1,
    -- receita não carrega categoria de despesa; despesa não carrega origem de receita
    CHECK (kind = 'income'  OR income_source_id IS NULL),
    CHECK (kind = 'expense' OR category_id IS NULL)
);

CREATE TABLE transactions (
    id               INTEGER PRIMARY KEY,
    date             TEXT    NOT NULL,
    amount_cents     INTEGER NOT NULL CHECK (amount_cents > 0),
    account_id       INTEGER NOT NULL REFERENCES accounts(id),
    kind             TEXT    NOT NULL CHECK (kind IN ('expense', 'income')),
    status           TEXT    NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'pending')),
    category_id      INTEGER REFERENCES categories(id),       -- opcional em despesa ("Sem categoria")
    income_source_id INTEGER REFERENCES income_sources(id),   -- obrigatório em receita (regra na camada core)
    payee_id         INTEGER REFERENCES payees(id),
    recurring_id     INTEGER REFERENCES recurring(id),
    note             TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (kind = 'income'  OR income_source_id IS NULL),
    CHECK (kind = 'expense' OR category_id IS NULL)
);

CREATE INDEX idx_tx_date   ON transactions(date);
CREATE INDEX idx_tx_status ON transactions(status);
CREATE INDEX idx_tx_kind   ON transactions(kind);
