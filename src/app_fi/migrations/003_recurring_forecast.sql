-- 003_recurring_forecast.sql — permite prever até quando uma recorrência
-- com número fixo de parcelas ainda vai cobrar. Sem valor (NULL) = sem fim
-- definido (assinatura, conta de consumo) — de propósito, não é omissão.

ALTER TABLE recurring ADD COLUMN total_installments INTEGER;
ALTER TABLE recurring ADD COLUMN current_installment INTEGER NOT NULL DEFAULT 1;
