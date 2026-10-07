-- 009_renda_fixa.sql — renda fixa: aplicações (CDB, Tesouro, LCI/LCA…) e seus aportes/resgates.
--
-- Valores em reais, como TEXT com número decimal exato (lidos como Decimal em core/renda_fixa.py).
-- O tipo (`tipo`) é uma chave do catálogo em core/renda_fixa.py (TESOURO_SELIC, CDB, LCI…).
-- `taxa` depende do indexador: PRE = % a.a.; CDI = % do CDI; CDI_MAIS/SELIC/IPCA = taxa a.a. somada ao
-- índice. `valor_atual` é informado à mão (o app não acessa a internet); 0 marca a aplicação como encerrada.

CREATE TABLE rf_posicoes (
    id               INTEGER PRIMARY KEY,
    tipo             TEXT NOT NULL,
    nome             TEXT,                          -- rótulo livre (ex.: "CDB Banco X 2028")
    instituicao      TEXT NOT NULL,                 -- emissor: banco, Tesouro Nacional…
    corretora        TEXT,                          -- onde está custodiado (opcional)
    indexador        TEXT NOT NULL CHECK (indexador IN ('PRE', 'CDI', 'CDI_MAIS', 'SELIC', 'IPCA', 'OUTRO')),
    taxa             TEXT,
    vencimento       TEXT,                          -- 'YYYY-MM-DD'
    liquidez         TEXT NOT NULL DEFAULT 'vencimento' CHECK (liquidez IN ('diaria', 'vencimento', 'carencia')),
    isento_ir        INTEGER NOT NULL DEFAULT 0,    -- pessoa física isenta (LCI, LCA, CRI, CRA, poupança…)
    valor_atual      TEXT,
    data_valor_atual TEXT,
    observacao       TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE rf_movimentos (
    id         INTEGER PRIMARY KEY,
    posicao_id INTEGER NOT NULL REFERENCES rf_posicoes(id) ON DELETE CASCADE,
    tipo       TEXT NOT NULL CHECK (tipo IN ('aporte', 'resgate')),
    data       TEXT NOT NULL,
    valor      TEXT NOT NULL,                       -- bruto
    custos     TEXT NOT NULL DEFAULT '0',           -- IR/IOF/taxas retidos num resgate, ou taxa paga num aporte
    nota       TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_rf_movimentos_posicao ON rf_movimentos (posicao_id, data);
