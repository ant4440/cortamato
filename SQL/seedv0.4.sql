USE cortamato;

-- ---------------------------------------------------------------------------
-- Utilizadores e Perfis
-- ---------------------------------------------------------------------------
INSERT INTO utilizador (nome, email, password_hash, ativo) VALUES
    ('Admin',              'admin@escola.pt',      'x', TRUE),
    ('Carlos Carvalho',    'carlos@escola.pt',     'x', TRUE),
    ('Cristiano Ferreira', 'cristiano@escola.pt',  'x', TRUE),
    ('Ana Professora',     'ana@escola.pt',        'x', TRUE);

INSERT INTO perfil (nome) VALUES ('admin'), ('professor'), ('diretor_turma'), ('secretariado');

INSERT INTO utilizador_perfil (utilizador_id, perfil_id) VALUES
    (1,1), (2,2), (2,3), (3,2), (3,4), (4,2);

INSERT INTO permissao (recurso, acao) VALUES
    ('inscricao','create'), ('inscricao','read'), ('inscricao','update'),
    ('dorsal','create'),    ('dorsal','update'),
    ('chegada','create'),   ('classificacao','read'),
    ('relatorio','read');

INSERT INTO perfil_permissao (perfil_id, permissao_id)
SELECT 1, id FROM permissao;

-- ---------------------------------------------------------------------------
-- Turmas
-- ---------------------------------------------------------------------------
INSERT INTO turma (ano_escolar, letra, diretor_turma_id) VALUES
    (5, 'A', 2),
    (7, 'B', 3),
    (9, 'C', 4);

-- ---------------------------------------------------------------------------
-- Alunos
-- ---------------------------------------------------------------------------
INSERT INTO aluno (numeroprocesso, nome, datanasc, sexo, turma_id) VALUES
    (10001, 'Ana Silva',         '2013-05-14', 'F', 1),
    (10002, 'João Martins',      '2013-08-22', 'M', 1),
    (10003, 'Maria Almeida',     '2013-02-10', 'F', 1),
    (10004, 'Diogo Costa',       '2013-11-03', 'M', 1),
    (10005, 'Beatriz Sousa',     '2011-04-18', 'F', 2),
    (10006, 'Tiago Correia',     '2011-09-27', 'M', 2),
    (10007, 'Leonor Ferreira',   '2011-01-15', 'F', 2),
    (10008, 'Pedro Santos',      '2011-12-05', 'M', 2),
    (10009, 'Inês Gomes',        '2009-06-30', 'F', 3),
    (10010, 'Rafael Pereira',    '2009-10-11', 'M', 3),
    (10011, 'Sofia Mendes',      '2009-03-25', 'F', 3),
    (10012, 'Miguel Lopes',      '2009-07-19', 'M', 3);

-- ---------------------------------------------------------------------------
-- Provas
-- ---------------------------------------------------------------------------
INSERT INTO prova (anolectivo, concelho, escola, data, horainicio, horafinal) VALUES
    ('2026/2027', 'Braga', 'Escola Básica de Exemplo', '2026-11-12', '09:00:00', '13:00:00'),
    ('2026/2027', 'Braga', 'Escola Básica de Exemplo', '2027-03-18', '09:30:00', '12:30:00');

-- ---------------------------------------------------------------------------
-- Escalões
-- ---------------------------------------------------------------------------
INSERT INTO escalao (prova_id, designacao, sexo, anonasc_min, anonasc_max, da) VALUES
    (1, 'Infantis Femininos', 'F', 2011, 2013, FALSE),
    (1, 'Infantis Masculinos','M', 2011, 2013, FALSE),
    (1, 'Juvenis Femininos',  'F', 2009, 2010, FALSE),
    (1, 'Juvenis Masculinos', 'M', 2009, 2010, FALSE);

-- ---------------------------------------------------------------------------
-- Inscrições (Atletas 10001–10010)
-- ---------------------------------------------------------------------------
INSERT INTO inscricao (idprova, numeroprocesso, estado, indicador_da) VALUES
    (1, 10001, 'participante', FALSE),
    (1, 10002, 'participante', FALSE),
    (1, 10003, 'participante', FALSE),
    (1, 10004, 'participante', FALSE),
    (1, 10005, 'participante', FALSE),
    (1, 10006, 'participante', FALSE),
    (1, 10007, 'participante', FALSE),
    (1, 10008, 'participante', FALSE),
    (1, 10009, 'participante', FALSE),
    (1, 10010, 'participante', FALSE);

-- ---------------------------------------------------------------------------
-- Inscrições (Staff 10011–10012)
-- ---------------------------------------------------------------------------
INSERT INTO inscricao (idprova, numeroprocesso, estado, indicador_da, funcao) VALUES
    (1, 10011, 'organizacao', FALSE, 'juiz'),
    (1, 10012, 'organizacao', FALSE, 'secretariado');

-- ---------------------------------------------------------------------------
-- Dorsais
-- ---------------------------------------------------------------------------
INSERT INTO dorsal (inscricao_id, numero, estado, entregue_em) VALUES
    (1, 1, 'entregue', '2026-11-12 08:30:00.000'),
    (2, 2, 'entregue', '2026-11-12 08:31:00.000'),
    (3, 3, 'entregue', '2026-11-12 08:32:00.000'),
    (4, 4, 'entregue', '2026-11-12 08:33:00.000'),
    (5, 5, 'entregue', '2026-11-12 08:34:00.000'),
    (6, 6, 'entregue', '2026-11-12 08:35:00.000'),
    (7, 7, 'entregue', '2026-11-12 08:36:00.000'),
    (8, 8, 'entregue', '2026-11-12 08:37:00.000'),
    (9, 9, 'entregue', '2026-11-12 08:38:00.000'),
    (10, 10, 'entregue', '2026-11-12 08:39:00.000');

-- ---------------------------------------------------------------------------
-- Chegadas
-- ---------------------------------------------------------------------------
INSERT INTO chegada (inscricao_id, hora_chegada, metodo) VALUES
    (1, '2026-11-12 10:00:12.120', 'qrcode'),
    (2, '2026-11-12 10:00:10.450', 'qrcode'),
    (3, '2026-11-12 10:00:15.890', 'manual'),
    (4, '2026-11-12 10:00:11.230', 'qrcode'),
    (5, '2026-11-12 10:00:14.560', 'manual'),
    (6, '2026-11-12 10:00:09.120', 'qrcode'),
    (7, '2026-11-12 10:00:13.780', 'manual'),
    (8, '2026-11-12 10:00:16.340', 'qrcode'),
    (9, '2026-11-12 10:00:08.900', 'qrcode');

-- Desistência (10010) e Desclassificação (10009)
INSERT INTO desistencia (inscricao_id, hora, motivo) VALUES
    (10, '2026-11-12 09:55:00.000', 'Lesão');

INSERT INTO desclassificacao (inscricao_id, hora, motivo) VALUES
    (9, '2026-11-12 10:05:00.000', 'Cortou caminho');

-- ---------------------------------------------------------------------------
-- Classificações (Gerais e por Escalão)
-- ---------------------------------------------------------------------------
INSERT INTO classificacao (inscricao_id, prova_id, escalao_id, posicao) VALUES
    -- Gerais
    (6, 1, NULL, 1), (2, 1, NULL, 2), (4, 1, NULL, 3), (1, 1, NULL, 4),
    (7, 1, NULL, 5), (5, 1, NULL, 6), (3, 1, NULL, 7), (8, 1, NULL, 8),
    -- Infantis F
    (3, 1, 1, 1), (1, 1, 1, 2), (5, 1, 1, 3), (7, 1, 1, 4),
    -- Infantis M
    (2, 1, 2, 1), (4, 1, 2, 2), (6, 1, 2, 3), (8, 1, 2, 4);

-- ---------------------------------------------------------------------------
-- Apuramentos
-- ---------------------------------------------------------------------------
INSERT INTO regra_apuramento (prova_origem_id, prova_destino_id, escalao_id, numero_apurados) VALUES
    (1, 2, 1, 2),
    (1, 2, 2, 2);

INSERT INTO apurado (inscricao_id, prova_destino_id, classificacao_id, estado)
SELECT cl.inscricao_id, 2, cl.id, 'apurado'
FROM classificacao cl
JOIN regra_apuramento r
  ON r.prova_origem_id = cl.prova_id
 AND r.escalao_id = cl.escalao_id
 AND cl.posicao <= r.numero_apurados
WHERE cl.prova_id = 1 AND cl.escalao_id IS NOT NULL;