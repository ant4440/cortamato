-- Database: cortamato
-- Schema (Passos 1 a 6 + 8) - Com suporte para Fotografias de Perfil
-- Compatível com MySQL 8.0+ / MariaDB 10.2+

DROP DATABASE IF EXISTS cortamato;
CREATE DATABASE cortamato
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE cortamato;

-- ---------------------------------------------------------------------------
-- Passo 1 — Identidade, perfis e permissões
-- ---------------------------------------------------------------------------
CREATE TABLE utilizador (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nome            VARCHAR(150) NOT NULL,
    email           VARCHAR(150) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    foto_perfil     VARCHAR(255) NULL,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_utilizador_email UNIQUE (email),
    CONSTRAINT chk_utilizador_email CHECK (email LIKE '%@%.%')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE perfil (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    nome    VARCHAR(50) NOT NULL,
    CONSTRAINT uq_perfil_nome UNIQUE (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE permissao (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    recurso     VARCHAR(50) NOT NULL,
    acao        VARCHAR(20) NOT NULL,
    CONSTRAINT uq_permissao UNIQUE (recurso, acao),
    CONSTRAINT chk_permissao_acao CHECK (acao IN ('create','read','update','delete','manage'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE utilizador_perfil (
    utilizador_id   INT NOT NULL,
    perfil_id       INT NOT NULL,
    PRIMARY KEY (utilizador_id, perfil_id),
    CONSTRAINT fk_upl_utilizador FOREIGN KEY (utilizador_id) REFERENCES utilizador(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_upl_perfil FOREIGN KEY (perfil_id) REFERENCES perfil(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE perfil_permissao (
    perfil_id       INT NOT NULL,
    permissao_id    INT NOT NULL,
    PRIMARY KEY (perfil_id, permissao_id),
    CONSTRAINT fk_pp_perfil FOREIGN KEY (perfil_id) REFERENCES perfil(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_pp_permissao FOREIGN KEY (permissao_id) REFERENCES permissao(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Passo 2 — Estrutura escolar
-- ---------------------------------------------------------------------------
CREATE TABLE turma (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    ano_escolar       TINYINT NOT NULL,
    letra             CHAR(1) NOT NULL,
    diretor_turma_id  INT NULL,
    CONSTRAINT uq_turma UNIQUE (ano_escolar, letra),
    CONSTRAINT chk_turma_ano   CHECK (ano_escolar BETWEEN 1 AND 12),
    CONSTRAINT chk_turma_letra CHECK (letra BETWEEN 'A' AND 'Z'),
    CONSTRAINT fk_turma_dt FOREIGN KEY (diretor_turma_id) REFERENCES utilizador(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE prova (
    idprova INT AUTO_INCREMENT PRIMARY KEY,
    anolectivo VARCHAR(9) NOT NULL,
    concelho VARCHAR(100) NOT NULL,
    escola VARCHAR(150) NOT NULL,
    data DATE NOT NULL,
    horainicio TIME NOT NULL,
    horafinal TIME NOT NULL,
    CONSTRAINT chk_prova_horas CHECK (horafinal >= horainicio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE aluno (
    numeroprocesso INT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    datanasc DATE NOT NULL,
    sexo CHAR(1) NOT NULL,
    turma_id INT NULL,
    CONSTRAINT chk_aluno_datanasc CHECK (datanasc >= '1900-01-01' AND datanasc <= '2100-12-31'),
    CONSTRAINT chk_aluno_sexo CHECK (sexo IN ('M', 'F')),
    CONSTRAINT fk_aluno_turma FOREIGN KEY (turma_id) REFERENCES turma(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Passo 3 — Inscrição
-- ---------------------------------------------------------------------------
CREATE TABLE inscricao (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    idprova          INT NOT NULL,
    numeroprocesso   INT NOT NULL,
    data_inscricao   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado           ENUM('nao_inscrito','inscrito','participante','organizacao') NOT NULL DEFAULT 'inscrito',
    indicador_da     BOOLEAN NOT NULL DEFAULT FALSE,
    funcao           VARCHAR(50) NULL,
    CONSTRAINT uq_inscricao UNIQUE (idprova, numeroprocesso),
    CONSTRAINT chk_inscricao_funcao
        CHECK ((estado = 'organizacao' AND funcao IS NOT NULL) OR (estado <> 'organizacao')),
    CONSTRAINT fk_inscricao_prova FOREIGN KEY (idprova) REFERENCES prova(idprova) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_inscricao_aluno FOREIGN KEY (numeroprocesso) REFERENCES aluno(numeroprocesso) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Passo 4 — Escalões
-- ---------------------------------------------------------------------------
CREATE TABLE escalao (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    prova_id      INT NOT NULL,
    designacao    VARCHAR(100) NOT NULL,
    sexo          CHAR(1) NOT NULL,
    anonasc_min   SMALLINT NOT NULL,
    anonasc_max   SMALLINT NOT NULL,
    da            BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_escalao UNIQUE (prova_id, designacao),
    CONSTRAINT chk_escalao_sexo      CHECK (sexo IN ('M','F')),
    CONSTRAINT chk_escalao_intervalo CHECK (anonasc_min <= anonasc_max),
    CONSTRAINT chk_escalao_anos CHECK (anonasc_min BETWEEN 1900 AND 2100 AND anonasc_max BETWEEN 1900 AND 2100),
    CONSTRAINT fk_escalao_prova FOREIGN KEY (prova_id) REFERENCES prova(idprova) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Passo 5 — Secretariados
-- ---------------------------------------------------------------------------
CREATE TABLE dorsal (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    inscricao_id         INT NOT NULL,
    numero               INT NOT NULL,
    estado               ENUM('atribuido','entregue','devolvido') NOT NULL DEFAULT 'atribuido',
    entregue_em          DATETIME(3) NULL,
    CONSTRAINT uq_dorsal_inscricao UNIQUE (inscricao_id),
    CONSTRAINT chk_dorsal_numero   CHECK (numero > 0),
    CONSTRAINT chk_dorsal_entrega  CHECK ((estado = 'entregue' AND entregue_em IS NOT NULL) OR (estado <> 'entregue')),
    CONSTRAINT fk_dorsal_inscricao FOREIGN KEY (inscricao_id) REFERENCES inscricao(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE chegada (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    inscricao_id      INT NOT NULL,
    tempo_chegada     TIME(3) NOT NULL,
    metodo            ENUM('qrcode','manual') NOT NULL DEFAULT 'manual',
    corrigido_de      INT NULL,
    CONSTRAINT uq_chegada_inscricao UNIQUE (inscricao_id),
    CONSTRAINT fk_chegada_inscricao FOREIGN KEY (inscricao_id) REFERENCES inscricao(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_chegada_correcao FOREIGN KEY (corrigido_de) REFERENCES chegada(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE desistencia (
    inscricao_id   INT NOT NULL,
    hora           DATETIME(3) NOT NULL,
    motivo         VARCHAR(255) NULL,
    PRIMARY KEY (inscricao_id),
    CONSTRAINT fk_desistencia_inscricao FOREIGN KEY (inscricao_id) REFERENCES inscricao(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE desclassificacao (
    inscricao_id   INT NOT NULL,
    hora           DATETIME(3) NOT NULL,
    motivo         VARCHAR(255) NOT NULL,
    PRIMARY KEY (inscricao_id),
    CONSTRAINT fk_desclassificacao_inscricao FOREIGN KEY (inscricao_id) REFERENCES inscricao(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE lista_partida (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    prova_id      INT NOT NULL,
    escalao_id    INT NOT NULL,
    designacao    VARCHAR(100) NOT NULL,
    CONSTRAINT uq_lista_partida UNIQUE (prova_id, designacao),
    CONSTRAINT fk_lista_partida_prova FOREIGN KEY (prova_id) REFERENCES prova(idprova) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_lista_partida_escalao FOREIGN KEY (escalao_id) REFERENCES escalao(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE lista_partida_inscricao (
    lista_partida_id   INT NOT NULL,
    inscricao_id       INT NOT NULL,
    ordem              INT NOT NULL,
    PRIMARY KEY (lista_partida_id, inscricao_id),
    CONSTRAINT uq_lista_partida_ordem UNIQUE (lista_partida_id, ordem),
    CONSTRAINT chk_lista_partida_ordem CHECK (ordem > 0),
    CONSTRAINT fk_lpi_lista FOREIGN KEY (lista_partida_id) REFERENCES lista_partida(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_lpi_inscricao FOREIGN KEY (inscricao_id) REFERENCES inscricao(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Passo 6 — Classificações e Apuramentos
-- ---------------------------------------------------------------------------
CREATE TABLE classificacao (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    inscricao_id   INT NOT NULL,
    prova_id       INT NOT NULL,
    escalao_id     INT NULL,
    posicao        INT NOT NULL,
    CONSTRAINT uq_classificacao_inscricao UNIQUE (inscricao_id, escalao_id),
    CONSTRAINT chk_classificacao_posicao  CHECK (posicao > 0),
    CONSTRAINT fk_classificacao_inscricao FOREIGN KEY (inscricao_id) REFERENCES inscricao(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_classificacao_prova FOREIGN KEY (prova_id) REFERENCES prova(idprova) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_classificacao_escalao FOREIGN KEY (escalao_id) REFERENCES escalao(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE regra_apuramento (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    prova_origem_id     INT NOT NULL,
    prova_destino_id    INT NOT NULL,
    escalao_id          INT NOT NULL,
    numero_apurados     INT NOT NULL,
    CONSTRAINT uq_regra_apuramento UNIQUE (prova_origem_id, prova_destino_id, escalao_id),
    CONSTRAINT chk_regra_numero   CHECK (numero_apurados > 0),
    CONSTRAINT chk_regra_provas   CHECK (prova_origem_id <> prova_destino_id),
    CONSTRAINT fk_regra_origem FOREIGN KEY (prova_origem_id) REFERENCES prova(idprova) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_regra_destino FOREIGN KEY (prova_destino_id) REFERENCES prova(idprova) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_regra_escalao FOREIGN KEY (escalao_id) REFERENCES escalao(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE apurado (
    inscricao_id       INT NOT NULL,
    prova_destino_id   INT NOT NULL,
    classificacao_id   INT NOT NULL,
    estado             ENUM('apurado','confirmado','desistiu') NOT NULL DEFAULT 'apurado',
    PRIMARY KEY (inscricao_id, prova_destino_id),
    CONSTRAINT fk_apurado_inscricao FOREIGN KEY (inscricao_id) REFERENCES inscricao(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_apurado_prova FOREIGN KEY (prova_destino_id) REFERENCES prova(idprova) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_apurado_classificacao FOREIGN KEY (classificacao_id) REFERENCES classificacao(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- View de compatibilidade
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_competidor AS
SELECT
    i.idprova, i.numeroprocesso, d.numero AS numdorsal, d.estado AS estado_dorsal,
    c.tempo_chegada, CASE WHEN c.id IS NOT NULL THEN TRUE ELSE FALSE END AS tem_chegada,
    CASE WHEN ds.inscricao_id IS NOT NULL THEN TRUE ELSE FALSE END AS desistiu,
    CASE WHEN dcl.inscricao_id IS NOT NULL THEN TRUE ELSE FALSE END AS desclassificado
FROM inscricao i
LEFT JOIN dorsal d ON d.inscricao_id = i.id
LEFT JOIN chegada c ON c.inscricao_id = i.id
LEFT JOIN desistencia ds ON ds.inscricao_id = i.id
LEFT JOIN desclassificacao dcl ON dcl.inscricao_id = i.id;