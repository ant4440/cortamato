USE cortamato;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Limpar dados (DELETE respeita melhor as FKs do que TRUNCATE em algumas versões)
DELETE FROM apurado;
DELETE FROM regra_apuramento;
DELETE FROM classificacao;
DELETE FROM lista_partida_inscricao;
DELETE FROM lista_partida;
DELETE FROM desclassificacao;
DELETE FROM desistencia;
DELETE FROM chegada;
DELETE FROM dorsal;
DELETE FROM inscricao;
DELETE FROM escalao;
DELETE FROM prova;
DELETE FROM aluno;
DELETE FROM turma;
DELETE FROM perfil_permissao;
DELETE FROM utilizador_perfil;
DELETE FROM permissao;
DELETE FROM perfil;
DELETE FROM utilizador;

-- 2. Reiniciar os contadores (AUTO_INCREMENT)
ALTER TABLE utilizador AUTO_INCREMENT = 1;
ALTER TABLE perfil AUTO_INCREMENT = 1;
ALTER TABLE permissao AUTO_INCREMENT = 1;
ALTER TABLE turma AUTO_INCREMENT = 1;
ALTER TABLE prova AUTO_INCREMENT = 1;
ALTER TABLE escalao AUTO_INCREMENT = 1;
ALTER TABLE inscricao AUTO_INCREMENT = 1;
ALTER TABLE dorsal AUTO_INCREMENT = 1;
ALTER TABLE chegada AUTO_INCREMENT = 1;
ALTER TABLE lista_partida AUTO_INCREMENT = 1;
ALTER TABLE classificacao AUTO_INCREMENT = 1;
ALTER TABLE regra_apuramento AUTO_INCREMENT = 1;

SET FOREIGN_KEY_CHECKS = 1;