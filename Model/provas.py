"""School athletics event queries and persistence."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from mysql.connector import Error

from SQL.connection import close_connection, get_connection


@dataclass(frozen=True)
class Prova:
    idprova: int
    anolectivo: str
    concelho: str
    escola: str
    data: date
    horainicio: time | timedelta
    horafinal: time | timedelta


def listar_provas() -> list[Prova]:
    """Return events that have not yet passed, ordered by date and start time."""
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT idprova, anolectivo, concelho, escola, data, horainicio, horafinal
            FROM prova
            WHERE data >= CURDATE()
            ORDER BY data, horainicio, idprova
            """
        )
        return [Prova(*row) for row in cursor.fetchall()]
    except Error as exc:
        raise ConnectionError(f"Unable to load events from MySQL: {exc}") from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def criar_prova(
    anolectivo: str,
    concelho: str,
    escola: str,
    data: date,
    horainicio: time,
    horafinal: time,
) -> None:
    anolectivo = anolectivo.strip()
    concelho = concelho.strip()
    escola = escola.strip()
    _validar_prova(anolectivo, concelho, escola, data, horainicio, horafinal)
    _executar_escrita(
        """
        INSERT INTO prova (anolectivo, concelho, escola, data, horainicio, horafinal)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (anolectivo, concelho, escola, data, horainicio, horafinal),
        "Unable to create event",
    )


def atualizar_prova(
    idprova: int,
    anolectivo: str,
    concelho: str,
    escola: str,
    data: date,
    horainicio: time,
    horafinal: time,
) -> None:
    if idprova <= 0:
        raise ValueError("O identificador da prova é inválido.")
    anolectivo = anolectivo.strip()
    concelho = concelho.strip()
    escola = escola.strip()
    _validar_prova(anolectivo, concelho, escola, data, horainicio, horafinal)
    _executar_escrita(
        """
        UPDATE prova
        SET anolectivo = %s, concelho = %s, escola = %s, data = %s,
            horainicio = %s, horafinal = %s
        WHERE idprova = %s
        """,
        (
            anolectivo,
            concelho,
            escola,
            data,
            horainicio,
            horafinal,
            idprova,
        ),
        "Unable to update event",
    )


def eliminar_provas(ids_provas: list[int]) -> None:
    ids = _validar_ids(ids_provas)
    placeholders = ", ".join("%s" for _ in ids)
    _executar_escrita(
        f"DELETE FROM prova WHERE idprova IN ({placeholders})",
        ids,
        "Unable to delete events",
    )


def contar_alunos_inscritos(idprova: int) -> int:
    """Return the number of registered students for an event."""
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM inscricao
            WHERE idprova = %s AND estado IN ('inscrito', 'participante')
            """,
            (idprova,),
        )
        result = cursor.fetchone()
        if not isinstance(result, tuple) or len(result) != 1:
            raise RuntimeError(
                "The student registration count query returned an invalid result."
            )
        enrolled_students = result[0]
        if not isinstance(enrolled_students, (int, Decimal)):
            raise RuntimeError(
                "The student registration count query returned an invalid count."
            )
        return int(enrolled_students)
    except Error as exc:
        raise ConnectionError(
            f"Unable to count registered students in MySQL: {exc}"
        ) from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def _validar_prova(
    anolectivo: str,
    concelho: str,
    escola: str,
    data: date,
    horainicio: time,
    horafinal: time,
) -> None:
    if not anolectivo or len(anolectivo) > 9:
        raise ValueError("O ano letivo é obrigatório e deve ter até 9 caracteres.")
    if not concelho or len(concelho) > 100:
        raise ValueError("O concelho é obrigatório e deve ter até 100 caracteres.")
    if not escola or len(escola) > 150:
        raise ValueError("A escola é obrigatória e deve ter até 150 caracteres.")
    if not isinstance(data, date) or isinstance(data, datetime):
        raise ValueError("A data da prova é inválida.")
    if data < date.today():
        raise ValueError("A data da prova não pode ser anterior a hoje.")
    if not isinstance(horainicio, time) or not isinstance(horafinal, time):
        raise ValueError("Introduza horas válidas no formato HH:MM.")
    if horafinal < horainicio:
        raise ValueError("A hora final não pode ser anterior à hora de início.")


def _validar_ids(ids: list[int]) -> tuple[int, ...]:
    unique_ids = tuple(dict.fromkeys(ids))
    if not unique_ids or any(
        not isinstance(item, int) or item <= 0 for item in unique_ids
    ):
        raise ValueError("Selecione pelo menos uma prova válida.")
    return unique_ids


def _executar_escrita(
    query: str,
    parameters: tuple[object, ...],
    operation: str,
) -> None:
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(query, parameters)
    except Error as exc:
        raise ConnectionError(f"{operation} in MySQL: {exc}") from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)
