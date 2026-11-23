"""Controller for managing school athletics events."""

from datetime import date, time

from Model.provas import (
    Prova,
    atualizar_prova,
    contar_alunos_inscritos,
    criar_prova,
    eliminar_provas,
    listar_provas,
)


class ProvasController:
    """Coordinates event-list requests from the view to the model."""

    def listar_provas(self) -> list[Prova]:
        return listar_provas()

    def criar_prova(
        self,
        anolectivo: str,
        concelho: str,
        escola: str,
        data: date,
        horainicio: time,
        horafinal: time,
    ) -> None:
        criar_prova(anolectivo, concelho, escola, data, horainicio, horafinal)

    def atualizar_prova(
        self,
        idprova: int,
        anolectivo: str,
        concelho: str,
        escola: str,
        data: date,
        horainicio: time,
        horafinal: time,
    ) -> None:
        atualizar_prova(
            idprova,
            anolectivo,
            concelho,
            escola,
            data,
            horainicio,
            horafinal,
        )

    def eliminar_provas(self, ids_provas: list[int]) -> None:
        eliminar_provas(ids_provas)

    def contar_alunos_inscritos(self, idprova: int) -> int:
        return contar_alunos_inscritos(idprova)
