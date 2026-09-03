-- 002_seed.sql — dados iniciais. Roda uma vez; edições posteriores do usuário
-- (renomear/arquivar categoria) não são revertidas.

INSERT INTO accounts (name, type) VALUES ('Conta principal', 'cash');

INSERT INTO categories (name) VALUES
    ('Moradia'),
    ('Alimentação'),
    ('Transporte'),
    ('Saúde'),
    ('Lazer'),
    ('Compras'),
    ('Assinaturas'),
    ('Educação'),
    ('Outros');

INSERT INTO income_sources (name) VALUES
    ('Salário'),
    ('Renda extra'),
    ('Reembolso'),
    ('Outros');
