-- 004_goals.sql — Objetivos Inteligentes (gamificação) + preferências simples do app.
--
-- `kind` fixo (v1, sem motor de regras livre): teto_categoria, reducao_categoria,
-- renda_extra, saldo_positivo_seguido. O significado de target_cents/target_months
-- depende do kind — ver core/goals.py.

CREATE TABLE goals (
    id             INTEGER PRIMARY KEY,
    kind           TEXT    NOT NULL CHECK (kind IN (
                       'teto_categoria', 'reducao_categoria',
                       'renda_extra', 'saldo_positivo_seguido'
                   )),
    label          TEXT    NOT NULL,
    category_id    INTEGER REFERENCES categories(id),
    target_cents   INTEGER,
    target_months  INTEGER,
    active         INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Um registro por objetivo x mês avaliado — histórico de PRs (achieved = 1) e
-- também a base para a "ofensiva geral" (meses seguidos com >=1 PR).
CREATE TABLE goal_records (
    id         INTEGER PRIMARY KEY,
    goal_id    INTEGER NOT NULL REFERENCES goals(id),
    year_month TEXT    NOT NULL,   -- 'YYYY-MM'
    achieved   INTEGER NOT NULL,
    UNIQUE (goal_id, year_month)
);

-- Preferências chave/valor (ex: tema claro/escuro) — não precisa de tabela própria.
CREATE TABLE app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
