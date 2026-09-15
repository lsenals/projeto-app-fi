-- 005_sort_order.sql — ordem customizável (arrastar-e-soltar) das categorias e
-- origens de receita na tela de Lançar. Backfill preserva a ordem visual atual
-- (alfabética, com "Outros" por último) como ponto de partida.

ALTER TABLE categories ADD COLUMN sort_order INTEGER;
ALTER TABLE income_sources ADD COLUMN sort_order INTEGER;

UPDATE categories SET sort_order = (
    SELECT t.rn FROM (
        SELECT id, ROW_NUMBER() OVER (ORDER BY (name = 'Outros'), name) AS rn
        FROM categories
    ) t WHERE t.id = categories.id
);

UPDATE income_sources SET sort_order = (
    SELECT t.rn FROM (
        SELECT id, ROW_NUMBER() OVER (ORDER BY (name = 'Outros'), name) AS rn
        FROM income_sources
    ) t WHERE t.id = income_sources.id
);
