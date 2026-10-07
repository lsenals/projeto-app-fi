-- 007_crypto_currency.sql — moeda por ativo (BRL ou USD).
--
-- Todos os valores de um ativo (compras, vendas, taxas, preço atual, histórico) ficam
-- na moeda dele, então o lucro % não carrega ruído de câmbio. Só o resumo da carteira
-- converte para a moeda de exibição, com a cotação do dólar informada à mão
-- (app_settings: 'usd_brl' e 'crypto_display_currency'). Ativos existentes ficam em BRL,
-- que é a moeda em que foram lançados até aqui.

ALTER TABLE crypto_assets ADD COLUMN currency TEXT NOT NULL DEFAULT 'BRL';
