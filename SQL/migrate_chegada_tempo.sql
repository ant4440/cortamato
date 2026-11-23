-- Execute once on an existing v0.5 database.
-- The original timestamps are preserved; they cannot be reliably converted
-- into elapsed race times, so existing rows start without a tempo_chegada.
ALTER TABLE chegada
    MODIFY COLUMN hora_chegada DATETIME(3) NULL,
    ADD COLUMN tempo_chegada TIME(3) NULL AFTER hora_chegada;

CREATE OR REPLACE VIEW v_competidor AS
SELECT
    i.idprova, i.numeroprocesso, d.numero AS numdorsal, d.estado AS estado_dorsal,
    c.tempo_chegada,
    CASE WHEN c.id IS NOT NULL THEN TRUE ELSE FALSE END AS tem_chegada,
    CASE WHEN ds.inscricao_id IS NOT NULL THEN TRUE ELSE FALSE END AS desistiu,
    CASE WHEN dcl.inscricao_id IS NOT NULL THEN TRUE ELSE FALSE END AS desclassificado
FROM inscricao i
LEFT JOIN dorsal d ON d.inscricao_id = i.id
LEFT JOIN chegada c ON c.inscricao_id = i.id
LEFT JOIN desistencia ds ON ds.inscricao_id = i.id
LEFT JOIN desclassificacao dcl ON dcl.inscricao_id = i.id;
