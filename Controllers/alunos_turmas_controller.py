"""Controller for student and class management."""

from datetime import date

from Model.alunos_turmas import (
    Aluno,
    Turma,
    atualizar_aluno,
    atualizar_turma,
    criar_aluno,
    criar_turma,
    eliminar_alunos,
    eliminar_turmas,
    listar_alunos,
    listar_turmas,
)


class AlunosTurmasController:
    """Coordinates student and class requests from the view to the model."""

    def listar_alunos(
        self,
        pesquisa: str = "",
        turma_id: int | None = None,
    ) -> list[Aluno]:
        return listar_alunos(pesquisa, turma_id)

    def listar_turmas(self) -> list[Turma]:
        return listar_turmas()

    def criar_aluno(
        self,
        numeroprocesso: int,
        nome: str,
        datanasc: date,
        sexo: str,
        turma_id: int | None,
    ) -> None:
        criar_aluno(numeroprocesso, nome, datanasc, sexo, turma_id)

    def atualizar_aluno(
        self,
        numeroprocesso: int,
        nome: str,
        datanasc: date,
        sexo: str,
        turma_id: int | None,
    ) -> None:
        atualizar_aluno(numeroprocesso, nome, datanasc, sexo, turma_id)

    def criar_turma(self, ano_escolar: int, letra: str) -> None:
        criar_turma(ano_escolar, letra)

    def atualizar_turma(
        self,
        id_turma: int,
        ano_escolar: int,
        letra: str,
    ) -> None:
        atualizar_turma(id_turma, ano_escolar, letra)

    def eliminar_alunos(self, numeros_processo: list[int]) -> None:
        eliminar_alunos(numeros_processo)

    def eliminar_turmas(self, ids_turmas: list[int]) -> None:
        eliminar_turmas(ids_turmas)
