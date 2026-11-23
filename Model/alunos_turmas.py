"""Student and class queries and persistence."""

from dataclasses import dataclass
from datetime import date

from mysql.connector import Error

from SQL.connection import close_connection, get_connection


@dataclass(frozen=True)
class Turma:
    id: int
    ano_escolar: int
    letra: str
    total_alunos: int

    @property
    def designacao(self) -> str:
        return f"{self.ano_escolar}.º {self.letra}"


@dataclass(frozen=True)
class Aluno:
    numeroprocesso: int
    nome: str
    datanasc: date
    sexo: str
    turma_id: int | None
    turma: str


def listar_turmas() -> list[Turma]:
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT t.id, t.ano_escolar, t.letra, COUNT(a.numeroprocesso)
            FROM turma AS t
            LEFT JOIN aluno AS a ON a.turma_id = t.id
            GROUP BY t.id, t.ano_escolar, t.letra
            ORDER BY t.ano_escolar, t.letra
            """
        )
        return [Turma(*row) for row in cursor.fetchall()]
    except Error as exc:
        raise ConnectionError(f"Unable to load classes from MySQL: {exc}") from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def listar_alunos(
    pesquisa: str = "",
    turma_id: int | None = None,
) -> list[Aluno]:
    connection = get_connection()
    cursor = None
    conditions: list[str] = []
    parameters: list[object] = []

    if pesquisa.strip():
        conditions.append(
            "(a.nome LIKE %s OR CAST(a.numeroprocesso AS CHAR) LIKE %s "
            "OR LPAD(CAST(a.numeroprocesso AS CHAR), 5, '0') LIKE %s)"
        )
        search_pattern = f"%{pesquisa.strip()}%"
        parameters.extend((search_pattern, search_pattern, search_pattern))
    if turma_id is not None:
        conditions.append("a.turma_id = %s")
        parameters.append(turma_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT a.numeroprocesso, a.nome, a.datanasc, a.sexo, a.turma_id,
                   COALESCE(CONCAT(t.ano_escolar, '.º ', t.letra), 'Sem turma')
            FROM aluno AS a
            LEFT JOIN turma AS t ON t.id = a.turma_id
            {where_clause}
            ORDER BY a.nome, a.numeroprocesso
            """,
            tuple(parameters),
        )
        return [Aluno(*row) for row in cursor.fetchall()]
    except Error as exc:
        raise ConnectionError(f"Unable to load students from MySQL: {exc}") from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def criar_aluno(
    numeroprocesso: int,
    nome: str,
    datanasc: date,
    sexo: str,
    turma_id: int | None,
) -> None:
    _validar_aluno(numeroprocesso, nome, datanasc, sexo, turma_id)
    _executar_escrita(
        """
        INSERT INTO aluno (numeroprocesso, nome, datanasc, sexo, turma_id)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (numeroprocesso, nome.strip(), datanasc, sexo, turma_id),
        "Unable to create student",
    )


def atualizar_aluno(
    numeroprocesso: int,
    nome: str,
    datanasc: date,
    sexo: str,
    turma_id: int | None,
) -> None:
    _validar_aluno(numeroprocesso, nome, datanasc, sexo, turma_id)
    _executar_escrita(
        """
        UPDATE aluno
        SET nome = %s, datanasc = %s, sexo = %s, turma_id = %s
        WHERE numeroprocesso = %s
        """,
        (nome.strip(), datanasc, sexo, turma_id, numeroprocesso),
        "Unable to update student",
    )


def criar_turma(ano_escolar: int, letra: str) -> None:
    letra = letra.strip().upper()
    _validar_turma(ano_escolar, letra)
    _executar_escrita(
        "INSERT INTO turma (ano_escolar, letra) VALUES (%s, %s)",
        (ano_escolar, letra),
        "Unable to create class",
    )


def atualizar_turma(id_turma: int, ano_escolar: int, letra: str) -> None:
    if id_turma <= 0:
        raise ValueError("O identificador da turma é inválido.")
    letra = letra.strip().upper()
    _validar_turma(ano_escolar, letra)
    _executar_escrita(
        "UPDATE turma SET ano_escolar = %s, letra = %s WHERE id = %s",
        (ano_escolar, letra, id_turma),
        "Unable to update class",
    )


def eliminar_alunos(numeros_processo: list[int]) -> None:
    ids = _validar_ids(numeros_processo)
    placeholders = ", ".join("%s" for _ in ids)
    _executar_escrita(
        f"DELETE FROM aluno WHERE numeroprocesso IN ({placeholders})",
        ids,
        "Unable to delete students",
    )


def eliminar_turmas(ids_turmas: list[int]) -> None:
    ids = _validar_ids(ids_turmas)
    placeholders = ", ".join("%s" for _ in ids)
    _executar_escrita(
        f"DELETE FROM turma WHERE id IN ({placeholders})",
        ids,
        "Unable to delete classes",
    )


def _validar_aluno(
    numeroprocesso: int,
    nome: str,
    datanasc: date,
    sexo: str,
    turma_id: int | None,
) -> None:
    if numeroprocesso <= 0:
        raise ValueError("O número de processo deve ser positivo.")
    if not nome.strip() or len(nome.strip()) > 150:
        raise ValueError("O nome é obrigatório e deve ter até 150 caracteres.")
    if (
        not isinstance(datanasc, date)
        or datanasc < date(1900, 1, 1)
        or datanasc > date.today()
    ):
        raise ValueError("A data de nascimento é inválida.")
    if sexo not in ("F", "M"):
        raise ValueError("Selecione um sexo válido.")
    if turma_id is not None and turma_id <= 0:
        raise ValueError("Selecione uma turma válida.")


def _validar_turma(ano_escolar: int, letra: str) -> None:
    if not 1 <= ano_escolar <= 12:
        raise ValueError("O ano escolar deve estar entre 1 e 12.")
    if len(letra) != 1 or not "A" <= letra.upper() <= "Z":
        raise ValueError("A letra da turma deve ser uma letra de A a Z.")


def _validar_ids(ids: list[int]) -> tuple[int, ...]:
    unique_ids = tuple(dict.fromkeys(ids))
    if not unique_ids or any(
        not isinstance(item, int) or item <= 0 for item in unique_ids
    ):
        raise ValueError("Selecione pelo menos um registo válido.")
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
