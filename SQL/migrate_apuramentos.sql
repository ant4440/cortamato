-- Add the qualification tables to an existing database without deleting data.
USE cortamato;

CREATE TABLE IF NOT EXISTS regra_apuramento (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    prova_origem_id     INT NOT NULL,
    prova_destino_id    INT NOT NULL,
    escalao_id          INT NOT NULL,
    numero_apurados     INT NOT NULL,
    CONSTRAINT uq_regra_apuramento UNIQUE (prova_origem_id, prova_destino_id, escalao_id),
    CONSTRAINT chk_regra_numero CHECK (numero_apurados > 0),
    CONSTRAINT fk_regra_origem FOREIGN KEY (prova_origem_id) REFERENCES prova(idprova) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_regra_destino FOREIGN KEY (prova_destino_id) REFERENCES prova(idprova) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_regra_escalao FOREIGN KEY (escalao_id) REFERENCES escalao(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS apurado (
    inscricao_id       INT NOT NULL,
    prova_destino_id   INT NOT NULL,
    classificacao_id   INT NOT NULL,
    estado             ENUM('apurado','confirmado','desistiu') NOT NULL DEFAULT 'apurado',
    PRIMARY KEY (inscricao_id, prova_destino_id),
    CONSTRAINT fk_apurado_inscricao FOREIGN KEY (inscricao_id) REFERENCES inscricao(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_apurado_prova FOREIGN KEY (prova_destino_id) REFERENCES prova(idprova) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_apurado_classificacao FOREIGN KEY (classificacao_id) REFERENCES classificacao(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
