"""Queries and persistence for competition operations."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from mysql.connector import Error

from SQL.connection import close_connection, get_connection


@dataclass(frozen=True)
class Inscricao:
    id: int
    idprova: int
    numeroprocesso: int
    estado: str
    indicador_da: bool
    funcao: str | None
    nome_aluno: str
    prova_label: str
    data_inscricao: datetime


@dataclass(frozen=True)
class Dorsal:
    id: int
    inscricao_id: int
    numero: int
    estado: str
    entregue_em: datetime | None
    nome_aluno: str
    numeroprocesso: int
    prova_label: str


@dataclass(frozen=True)
class Chegada:
    id: int
    inscricao_id: int
    tempo_chegada: timedelta | None
    metodo: str
    corrigido_de: int | None
    nome_aluno: str
    numeroprocesso: int
    prova_label: str
    dorsal: int | None


@dataclass(frozen=True)
class Classificacao:
    id: int
    inscricao_id: int
    prova_id: int
    escalao_id: int | None
    posicao: int
    nome_aluno: str
    numeroprocesso: int
    prova_label: str
    escalao: str


@dataclass(frozen=True)
class Escalao:
    id: int
    prova_id: int
    designacao: str
    sexo: str
    anonasc_min: int
    anonasc_max: int
    da: bool
    prova_label: str


@dataclass(frozen=True)
class RegraApuramento:
    id: int
    prova_origem_id: int
    prova_destino_id: int
    escalao_id: int
    numero_apurados: int
    prova_origem: str
    prova_destino: str
    escalao: str


@dataclass(frozen=True)
class Apurado:
    inscricao_id: int
    prova_destino_id: int
    classificacao_id: int
    estado: str
    nome_aluno: str
    numeroprocesso: int
    prova_destino: str
    prova_origem: str
    escalao: str
    posicao: int


def listar_inscricoes() -> list[Inscricao]:
    rows = _fetch_all(
        """
        SELECT i.id, i.idprova, i.numeroprocesso, i.estado, i.indicador_da,
               i.funcao, a.nome,
               CONCAT(p.escola, ' · ', DATE_FORMAT(p.data, '%d/%m/%Y')),
               i.data_inscricao
        FROM inscricao AS i
        JOIN aluno AS a ON a.numeroprocesso = i.numeroprocesso
        JOIN prova AS p ON p.idprova = i.idprova
        ORDER BY p.data DESC, a.nome, i.id
        """,
        (),
        "Unable to load registrations",
    )
    return [Inscricao(*row) for row in rows]


def listar_dorsais() -> list[Dorsal]:
    rows = _fetch_all(
        """
        SELECT d.id, d.inscricao_id, d.numero, d.estado, d.entregue_em,
               a.nome, a.numeroprocesso,
               CONCAT(p.escola, ' · ', DATE_FORMAT(p.data, '%d/%m/%Y'))
        FROM dorsal AS d
        JOIN inscricao AS i ON i.id = d.inscricao_id
        JOIN aluno AS a ON a.numeroprocesso = i.numeroprocesso
        JOIN prova AS p ON p.idprova = i.idprova
        ORDER BY p.data DESC, d.numero
        """,
        (),
        "Unable to load bibs",
    )
    return [Dorsal(*row) for row in rows]


def listar_chegadas() -> list[Chegada]:
    rows = _fetch_all(
        """
        SELECT c.id, c.inscricao_id, c.tempo_chegada, c.metodo, c.corrigido_de,
               a.nome, a.numeroprocesso,
               CONCAT(p.escola, ' · ', DATE_FORMAT(p.data, '%d/%m/%Y')),
               d.numero
        FROM chegada AS c
        JOIN inscricao AS i ON i.id = c.inscricao_id
        JOIN aluno AS a ON a.numeroprocesso = i.numeroprocesso
        JOIN prova AS p ON p.idprova = i.idprova
        LEFT JOIN dorsal AS d ON d.inscricao_id = i.id
        ORDER BY c.tempo_chegada IS NULL, c.tempo_chegada, c.id
        """,
        (),
        "Unable to load arrivals",
    )
    return [Chegada(*row) for row in rows]


def listar_classificacoes() -> list[Classificacao]:
    rows = _fetch_all(
        """
        SELECT c.id, c.inscricao_id, c.prova_id, c.escalao_id, c.posicao,
               a.nome, a.numeroprocesso,
               CONCAT(p.escola, ' · ', DATE_FORMAT(p.data, '%d/%m/%Y')),
               COALESCE(e.designacao, 'Geral')
        FROM classificacao AS c
        JOIN inscricao AS i ON i.id = c.inscricao_id
        JOIN aluno AS a ON a.numeroprocesso = i.numeroprocesso
        JOIN prova AS p ON p.idprova = c.prova_id
        LEFT JOIN escalao AS e ON e.id = c.escalao_id
        ORDER BY p.data DESC, e.designacao, c.posicao
        """,
        (),
        "Unable to load classifications",
    )
    return [Classificacao(*row) for row in rows]


def listar_escaloes() -> list[Escalao]:
    rows = _fetch_all(
        """
        SELECT e.id, e.prova_id, e.designacao, e.sexo,
               e.anonasc_min, e.anonasc_max, e.da,
               CONCAT(p.escola, ' · ', DATE_FORMAT(p.data, '%d/%m/%Y'))
        FROM escalao AS e
        JOIN prova AS p ON p.idprova = e.prova_id
        ORDER BY p.data DESC, e.designacao
        """,
        (),
        "Unable to load age groups",
    )
    return [Escalao(*row) for row in rows]


def listar_regras_apuramento() -> list[RegraApuramento]:
    rows = _fetch_all(
        """
        SELECT r.id, r.prova_origem_id, r.prova_destino_id, r.escalao_id,
               r.numero_apurados,
               CONCAT(po.escola, ' · ', DATE_FORMAT(po.data, '%d/%m/%Y')),
               CONCAT(pd.escola, ' · ', DATE_FORMAT(pd.data, '%d/%m/%Y')),
               e.designacao
        FROM regra_apuramento AS r
        JOIN prova AS po ON po.idprova = r.prova_origem_id
        JOIN prova AS pd ON pd.idprova = r.prova_destino_id
        JOIN escalao AS e ON e.id = r.escalao_id
        ORDER BY pd.data DESC, po.data DESC, e.designacao
        """,
        (),
        "Unable to load qualification rules",
    )
    return [RegraApuramento(*row) for row in rows]


def listar_apurados(prova_destino_id: int | None = None) -> list[Apurado]:
    query = """
        SELECT a.inscricao_id, a.prova_destino_id, a.classificacao_id, a.estado,
               al.nome, al.numeroprocesso,
               CONCAT(pd.escola, ' · ', DATE_FORMAT(pd.data, '%d/%m/%Y')),
               CONCAT(po.escola, ' · ', DATE_FORMAT(po.data, '%d/%m/%Y')),
               COALESCE(e.designacao, 'Geral'), c.posicao
        FROM apurado AS a
        JOIN inscricao AS i ON i.id = a.inscricao_id
        JOIN aluno AS al ON al.numeroprocesso = i.numeroprocesso
        JOIN prova AS pd ON pd.idprova = a.prova_destino_id
        JOIN classificacao AS c ON c.id = a.classificacao_id
        JOIN prova AS po ON po.idprova = c.prova_id
        LEFT JOIN escalao AS e ON e.id = c.escalao_id
    """
    parameters: tuple[object, ...] = ()
    if prova_destino_id is not None:
        _validar_id(prova_destino_id, "A prova de destino")
        query += " WHERE a.prova_destino_id = %s"
        parameters = (prova_destino_id,)
    query += " ORDER BY pd.data DESC, e.designacao, c.posicao, al.nome"
    rows = _fetch_all(query, parameters, "Unable to load qualified participants")
    return [Apurado(*row) for row in rows]


def criar_inscricao(
    idprova: int,
    numeroprocesso: int,
    estado: str,
    indicador_da: bool,
    funcao: str | None,
) -> None:
    funcao = _validar_inscricao(estado, funcao)
    _validar_id(idprova, "A prova")
    _validar_id(numeroprocesso, "O número de processo")
    _execute_write(
        """
        INSERT INTO inscricao (idprova, numeroprocesso, estado, indicador_da, funcao)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (idprova, numeroprocesso, estado, indicador_da, funcao),
        "Unable to create registration",
    )


def atualizar_inscricao(
    idinscricao: int,
    idprova: int,
    numeroprocesso: int,
    estado: str,
    indicador_da: bool,
    funcao: str | None,
) -> None:
    _validar_id(idinscricao, "A inscrição")
    _validar_id(idprova, "A prova")
    _validar_id(numeroprocesso, "O número de processo")
    funcao = _validar_inscricao(estado, funcao)
    _execute_write(
        """
        UPDATE inscricao
        SET idprova = %s, numeroprocesso = %s, estado = %s,
            indicador_da = %s, funcao = %s
        WHERE id = %s
        """,
        (idprova, numeroprocesso, estado, indicador_da, funcao, idinscricao),
        "Unable to update registration",
    )


def eliminar_inscricoes(ids: list[int]) -> None:
    _delete_many("inscricao", "id", ids, "Unable to delete registrations")


def criar_dorsal(
    inscricao_id: int,
    numero: int,
    estado: str,
    entregue_em: datetime | None,
) -> int:
    _validar_id(inscricao_id, "A inscrição")
    _validar_numero_dorsal(numero)
    entregue_em = _validar_dorsal(estado, entregue_em)
    connection = get_connection()
    cursor = None
    transaction_started = False

    try:
        connection.start_transaction()
        transaction_started = True
        cursor = connection.cursor()
        cursor.execute(
            "SELECT idprova FROM inscricao WHERE id = %s FOR UPDATE",
            (inscricao_id,),
        )
        registration = cursor.fetchone()
        if registration is None:
            raise ValueError("Selecione uma inscrição válida.")
        prova_id = int(registration[0])

        cursor.execute(
            "SELECT idprova FROM prova WHERE idprova = %s FOR UPDATE",
            (prova_id,),
        )
        if cursor.fetchone() is None:
            raise ValueError("A prova da inscrição já não existe.")

        cursor.execute(
            "SELECT id FROM dorsal WHERE inscricao_id = %s",
            (inscricao_id,),
        )
        if cursor.fetchone() is not None:
            raise ValueError("Esta inscrição já tem um dorsal atribuído.")

        cursor.execute(
            """
            SELECT d.id
            FROM dorsal AS d
            JOIN inscricao AS i ON i.id = d.inscricao_id
            WHERE i.idprova = %s AND d.numero = %s
            LIMIT 1
            """,
            (prova_id, numero),
        )
        if cursor.fetchone() is not None:
            raise ValueError("Este número de dorsal já está atribuído nesta prova.")

        cursor.execute(
            """
            INSERT INTO dorsal (inscricao_id, numero, estado, entregue_em)
            VALUES (%s, %s, %s, %s)
            """,
            (inscricao_id, numero, estado, entregue_em),
        )
        connection.commit()
        return numero
    except Error as exc:
        if transaction_started:
            connection.rollback()
        raise ConnectionError(f"Unable to assign bib in MySQL: {exc}") from exc
    except Exception:
        if transaction_started:
            connection.rollback()
        raise
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def atualizar_dorsal(
    iddorsal: int,
    numero: int,
    estado: str,
    entregue_em: datetime | None,
) -> None:
    _validar_id(iddorsal, "O dorsal")
    _validar_numero_dorsal(numero)
    entregue_em = _validar_dorsal(estado, entregue_em)
    connection = get_connection()
    cursor = None
    transaction_started = False

    try:
        connection.start_transaction()
        transaction_started = True
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT i.idprova
            FROM dorsal AS d
            JOIN inscricao AS i ON i.id = d.inscricao_id
            WHERE d.id = %s
            FOR UPDATE
            """,
            (iddorsal,),
        )
        dorsal = cursor.fetchone()
        if dorsal is None:
            raise ValueError("O dorsal selecionado já não existe.")
        prova_id = int(dorsal[0])

        cursor.execute(
            "SELECT idprova FROM prova WHERE idprova = %s FOR UPDATE",
            (prova_id,),
        )
        if cursor.fetchone() is None:
            raise ValueError("A prova do dorsal já não existe.")

        cursor.execute(
            """
            SELECT d.id
            FROM dorsal AS d
            JOIN inscricao AS i ON i.id = d.inscricao_id
            WHERE i.idprova = %s AND d.numero = %s AND d.id <> %s
            LIMIT 1
            """,
            (prova_id, numero, iddorsal),
        )
        if cursor.fetchone() is not None:
            raise ValueError("Este número de dorsal já está atribuído nesta prova.")

        cursor.execute(
            """
            UPDATE dorsal
            SET numero = %s, estado = %s, entregue_em = %s
            WHERE id = %s
            """,
            (numero, estado, entregue_em, iddorsal),
        )
        connection.commit()
    except Error as exc:
        if transaction_started:
            connection.rollback()
        raise ConnectionError(f"Unable to update bib in MySQL: {exc}") from exc
    except Exception:
        if transaction_started:
            connection.rollback()
        raise
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def eliminar_dorsais(ids: list[int]) -> None:
    _delete_many("dorsal", "id", ids, "Unable to delete bibs")


def criar_chegada(
    inscricao_id: int,
    tempo_chegada: timedelta,
    metodo: str,
    corrigido_de: int | None,
) -> None:
    _validar_id(inscricao_id, "A inscrição")
    _validar_chegada(tempo_chegada, metodo, corrigido_de)
    _validar_referencia_chegada(inscricao_id, corrigido_de)
    _execute_write(
        """
        INSERT INTO chegada (inscricao_id, tempo_chegada, metodo, corrigido_de)
        VALUES (%s, %s, %s, %s)
        """,
        (inscricao_id, tempo_chegada, metodo, corrigido_de),
        "Unable to create arrival",
    )


def atualizar_chegada(
    idchegada: int,
    inscricao_id: int,
    tempo_chegada: timedelta,
    metodo: str,
    corrigido_de: int | None,
) -> None:
    _validar_id(idchegada, "A chegada")
    _validar_id(inscricao_id, "A inscrição")
    _validar_chegada(tempo_chegada, metodo, corrigido_de)
    if corrigido_de == idchegada:
        raise ValueError("Uma chegada não pode corrigir a si própria.")
    _validar_referencia_chegada(inscricao_id, corrigido_de)
    _execute_write(
        """
        UPDATE chegada
        SET inscricao_id = %s, tempo_chegada = %s, metodo = %s, corrigido_de = %s
        WHERE id = %s
        """,
        (inscricao_id, tempo_chegada, metodo, corrigido_de, idchegada),
        "Unable to update arrival",
    )


def eliminar_chegadas(ids: list[int]) -> None:
    _delete_many("chegada", "id", ids, "Unable to delete arrivals")


def criar_classificacao(
    inscricao_id: int,
    prova_id: int,
    escalao_id: int | None,
    posicao: int,
) -> None:
    _validar_classificacao(inscricao_id, prova_id, escalao_id, posicao)
    _validar_relacoes_classificacao(
        inscricao_id,
        prova_id,
        escalao_id,
        excluding_id=None,
    )
    _execute_write(
        """
        INSERT INTO classificacao (inscricao_id, prova_id, escalao_id, posicao)
        VALUES (%s, %s, %s, %s)
        """,
        (inscricao_id, prova_id, escalao_id, posicao),
        "Unable to create classification",
    )


def atualizar_classificacao(
    idclassificacao: int,
    inscricao_id: int,
    prova_id: int,
    escalao_id: int | None,
    posicao: int,
) -> None:
    _validar_id(idclassificacao, "A classificação")
    _validar_classificacao(inscricao_id, prova_id, escalao_id, posicao)
    _validar_relacoes_classificacao(
        inscricao_id,
        prova_id,
        escalao_id,
        excluding_id=idclassificacao,
    )
    _execute_write(
        """
        UPDATE classificacao
        SET inscricao_id = %s, prova_id = %s, escalao_id = %s, posicao = %s
        WHERE id = %s
        """,
        (inscricao_id, prova_id, escalao_id, posicao, idclassificacao),
        "Unable to update classification",
    )


def eliminar_classificacoes(ids: list[int]) -> None:
    _delete_many("classificacao", "id", ids, "Unable to delete classifications")


def criar_escalao(
    prova_id: int,
    designacao: str,
    sexo: str,
    anonasc_min: int,
    anonasc_max: int,
    da: bool,
) -> None:
    designacao = designacao.strip()
    _validar_escalao(designacao, sexo, anonasc_min, anonasc_max)
    _validar_id(prova_id, "A prova")
    _execute_write(
        """
        INSERT INTO escalao (prova_id, designacao, sexo, anonasc_min, anonasc_max, da)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (prova_id, designacao, sexo, anonasc_min, anonasc_max, da),
        "Unable to create age group",
    )


def atualizar_escalao(
    idescalao: int,
    prova_id: int,
    designacao: str,
    sexo: str,
    anonasc_min: int,
    anonasc_max: int,
    da: bool,
) -> None:
    _validar_id(idescalao, "O escalão")
    _validar_id(prova_id, "A prova")
    designacao = designacao.strip()
    _validar_escalao(designacao, sexo, anonasc_min, anonasc_max)
    _execute_write(
        """
        UPDATE escalao
        SET prova_id = %s, designacao = %s, sexo = %s,
            anonasc_min = %s, anonasc_max = %s, da = %s
        WHERE id = %s
        """,
        (prova_id, designacao, sexo, anonasc_min, anonasc_max, da, idescalao),
        "Unable to update age group",
    )


def eliminar_escalaoes(ids: list[int]) -> None:
    _delete_many("escalao", "id", ids, "Unable to delete age groups")


def criar_regra_apuramento(
    prova_origem_id: int,
    prova_destino_id: int,
    escalao_id: int,
    numero_apurados: int,
) -> None:
    _validar_regra_apuramento(
        prova_origem_id,
        prova_destino_id,
        escalao_id,
        numero_apurados,
    )
    _execute_write(
        """
        INSERT INTO regra_apuramento
            (prova_origem_id, prova_destino_id, escalao_id, numero_apurados)
        VALUES (%s, %s, %s, %s)
        """,
        (prova_origem_id, prova_destino_id, escalao_id, numero_apurados),
        "Unable to create qualification rule",
    )


def atualizar_regra_apuramento(
    idregra: int,
    prova_origem_id: int,
    prova_destino_id: int,
    escalao_id: int,
    numero_apurados: int,
) -> None:
    _validar_id(idregra, "A regra de apuramento")
    _validar_regra_apuramento(
        prova_origem_id,
        prova_destino_id,
        escalao_id,
        numero_apurados,
    )
    _execute_write(
        """
        UPDATE regra_apuramento
        SET prova_origem_id = %s, prova_destino_id = %s,
            escalao_id = %s, numero_apurados = %s
        WHERE id = %s
        """,
        (
            prova_origem_id,
            prova_destino_id,
            escalao_id,
            numero_apurados,
            idregra,
        ),
        "Unable to update qualification rule",
    )


def eliminar_regras_apuramento(ids: list[int]) -> None:
    _delete_many("regra_apuramento", "id", ids, "Unable to delete qualification rules")


def gerar_apuramentos(prova_destino_id: int) -> int:
    _validar_id(prova_destino_id, "A prova de destino")
    connection = get_connection()
    cursor = None
    transaction_started = False

    try:
        connection.start_transaction()
        transaction_started = True
        cursor = connection.cursor()
        cursor.execute(
            "SELECT idprova FROM prova WHERE idprova = %s FOR UPDATE",
            (prova_destino_id,),
        )
        if cursor.fetchone() is None:
            raise ValueError("Selecione uma prova de destino válida.")

        cursor.execute(
            """
            DELETE a
            FROM apurado AS a
            LEFT JOIN classificacao AS c ON c.id = a.classificacao_id
            LEFT JOIN regra_apuramento AS r
              ON r.prova_destino_id = a.prova_destino_id
             AND r.prova_origem_id = c.prova_id
             AND r.escalao_id = c.escalao_id
            WHERE a.prova_destino_id = %s
              AND (r.id IS NULL OR c.id IS NULL OR c.posicao > r.numero_apurados)
            """,
            (prova_destino_id,),
        )
        cursor.execute(
            """
            UPDATE apurado AS a
            JOIN classificacao AS c
              ON c.inscricao_id = a.inscricao_id
            JOIN regra_apuramento AS r
              ON r.prova_destino_id = a.prova_destino_id
             AND r.prova_origem_id = c.prova_id
             AND r.escalao_id = c.escalao_id
            SET a.classificacao_id = c.id
            WHERE a.prova_destino_id = %s
              AND c.posicao <= r.numero_apurados
            """,
            (prova_destino_id,),
        )
        cursor.execute(
            """
            INSERT INTO apurado
                (inscricao_id, prova_destino_id, classificacao_id, estado)
            SELECT c.inscricao_id, r.prova_destino_id, MIN(c.id), 'apurado'
            FROM regra_apuramento AS r
            JOIN classificacao AS c
              ON c.prova_id = r.prova_origem_id
             AND c.escalao_id = r.escalao_id
            LEFT JOIN apurado AS a
              ON a.inscricao_id = c.inscricao_id
             AND a.prova_destino_id = r.prova_destino_id
            WHERE r.prova_destino_id = %s
              AND c.posicao <= r.numero_apurados
              AND a.inscricao_id IS NULL
            GROUP BY c.inscricao_id, r.prova_destino_id
            """,
            (prova_destino_id,),
        )
        cursor.execute(
            "SELECT COUNT(*) FROM apurado WHERE prova_destino_id = %s",
            (prova_destino_id,),
        )
        result = cursor.fetchone()
        if result is None:
            raise RuntimeError("The qualified participant count returned no result.")
        total = int(result[0])
        connection.commit()
        return total
    except Error as exc:
        if transaction_started:
            connection.rollback()
        raise ConnectionError(f"Unable to generate qualifiers in MySQL: {exc}") from exc
    except Exception:
        if transaction_started:
            connection.rollback()
        raise
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def atualizar_estado_apurado(
    inscricao_id: int,
    prova_destino_id: int,
    estado: str,
) -> None:
    _validar_id(inscricao_id, "A inscrição")
    _validar_id(prova_destino_id, "A prova de destino")
    if estado not in {"apurado", "confirmado", "desistiu"}:
        raise ValueError("Selecione um estado de apuramento válido.")
    _execute_write(
        """
        UPDATE apurado
        SET estado = %s
        WHERE inscricao_id = %s AND prova_destino_id = %s
        """,
        (estado, inscricao_id, prova_destino_id),
        "Unable to update qualifier status",
    )


def _validar_inscricao(estado: str, funcao: str | None) -> str | None:
    if estado not in {"nao_inscrito", "inscrito", "participante", "organizacao"}:
        raise ValueError("Selecione um estado de inscrição válido.")
    if estado == "organizacao":
        if funcao is None or not funcao.strip() or len(funcao.strip()) > 50:
            raise ValueError(
                "Indique uma função de organização com até 50 caracteres."
            )
        return funcao.strip()
    return None


def _validar_dorsal(estado: str, entregue_em: datetime | None) -> datetime | None:
    if estado not in {"atribuido", "entregue", "devolvido"}:
        raise ValueError("Selecione um estado de dorsal válido.")
    if estado == "entregue":
        if not isinstance(entregue_em, datetime):
            raise ValueError("Indique a data e hora de entrega do dorsal.")
        return entregue_em
    return None


def _validar_numero_dorsal(numero: int) -> None:
    if not isinstance(numero, int) or isinstance(numero, bool) or numero <= 0:
        raise ValueError("O número do dorsal deve ser um inteiro positivo.")


_MAX_TEMPO_CHEGADA = timedelta(hours=838, minutes=59, seconds=59, milliseconds=999)


def parse_tempo_chegada(value: str | None) -> timedelta:
    match = re.fullmatch(r"(\d{1,5}):([0-5]\d)\.(\d{1,3})", (value or "").strip())
    if match is None:
        raise ValueError("Introduza o tempo de chegada no formato MM:SS.mmm.")
    minutes, seconds, milliseconds = match.groups()
    tempo_chegada = timedelta(
        minutes=int(minutes),
        seconds=int(seconds),
        milliseconds=int(milliseconds.ljust(3, "0")),
    )
    if tempo_chegada > _MAX_TEMPO_CHEGADA:
        raise ValueError("O tempo de chegada excede o limite permitido.")
    return tempo_chegada


def _validar_chegada(
    tempo_chegada: timedelta,
    metodo: str,
    corrigido_de: int | None,
) -> None:
    if (
        not isinstance(tempo_chegada, timedelta)
        or tempo_chegada < timedelta(0)
        or tempo_chegada > _MAX_TEMPO_CHEGADA
        or tempo_chegada.microseconds % 1000 != 0
    ):
        raise ValueError("Introduza um tempo de chegada válido no formato MM:SS.mmm.")
    if metodo not in {"qrcode", "manual"}:
        raise ValueError("Selecione um método de registo válido.")
    if corrigido_de is not None:
        _validar_id(corrigido_de, "A chegada corrigida")


def _validar_referencia_chegada(
    inscricao_id: int,
    corrigido_de: int | None,
) -> None:
    registration = _fetch_all(
        "SELECT idprova FROM inscricao WHERE id = %s",
        (inscricao_id,),
        "Unable to validate arrival registration",
    )
    if not registration:
        raise ValueError("Selecione uma inscrição válida.")
    if corrigido_de is None:
        return

    previous_arrival = _fetch_all(
        """
        SELECT i.idprova
        FROM chegada AS c
        JOIN inscricao AS i ON i.id = c.inscricao_id
        WHERE c.id = %s
        """,
        (corrigido_de,),
        "Unable to validate corrected arrival",
    )
    if not previous_arrival:
        raise ValueError("Selecione uma chegada existente para corrigir.")
    if int(registration[0][0]) != int(previous_arrival[0][0]):
        raise ValueError("A chegada corrigida tem de pertencer à mesma prova.")


def _validar_classificacao(
    inscricao_id: int,
    prova_id: int,
    escalao_id: int | None,
    posicao: int,
) -> None:
    _validar_id(inscricao_id, "A inscrição")
    _validar_id(prova_id, "A prova")
    if escalao_id is not None:
        _validar_id(escalao_id, "O escalão")
    if posicao <= 0:
        raise ValueError("A posição deve ser um número positivo.")


def _validar_relacoes_classificacao(
    inscricao_id: int,
    prova_id: int,
    escalao_id: int | None,
    excluding_id: int | None,
) -> None:
    rows = _fetch_all(
        """
        SELECT i.idprova, e.prova_id
        FROM inscricao AS i
        LEFT JOIN escalao AS e ON e.id = %s
        WHERE i.id = %s
        """,
        (escalao_id, inscricao_id),
        "Unable to validate classification references",
    )
    if not rows:
        raise ValueError("Selecione uma inscrição existente.")
    if int(rows[0][0]) != prova_id:
        raise ValueError("A inscrição tem de pertencer à prova selecionada.")
    if escalao_id is not None and (
        rows[0][1] is None or int(rows[0][1]) != prova_id
    ):
        raise ValueError("O escalão tem de pertencer à prova selecionada.")
    if escalao_id is None:
        duplicate = _fetch_all(
            """
            SELECT id
            FROM classificacao
            WHERE inscricao_id = %s AND prova_id = %s AND escalao_id IS NULL
              AND (%s IS NULL OR id <> %s)
            """,
            (inscricao_id, prova_id, excluding_id, excluding_id),
            "Unable to validate general classification",
        )
        if duplicate:
            raise ValueError("Esta inscrição já tem uma classificação geral.")


def _validar_escalao(
    designacao: str,
    sexo: str,
    anonasc_min: int,
    anonasc_max: int,
) -> None:
    if not designacao or len(designacao) > 100:
        raise ValueError("A designação do escalão é obrigatória (até 100 caracteres).")
    if sexo not in {"M", "F"}:
        raise ValueError("Selecione um sexo válido.")
    if not 1900 <= anonasc_min <= 2100 or not 1900 <= anonasc_max <= 2100:
        raise ValueError("Os anos de nascimento devem estar entre 1900 e 2100.")
    if anonasc_min > anonasc_max:
        raise ValueError("O ano mínimo não pode ser superior ao ano máximo.")


def _validar_regra_apuramento(
    prova_origem_id: int,
    prova_destino_id: int,
    escalao_id: int,
    numero_apurados: int,
) -> None:
    _validar_id(prova_origem_id, "A prova de origem")
    _validar_id(prova_destino_id, "A prova de destino")
    _validar_id(escalao_id, "O escalão")
    if prova_origem_id == prova_destino_id:
        raise ValueError("As provas de origem e destino têm de ser diferentes.")
    if numero_apurados <= 0:
        raise ValueError("O número de apurados deve ser positivo.")
    rows = _fetch_all(
        "SELECT prova_id FROM escalao WHERE id = %s",
        (escalao_id,),
        "Unable to validate qualification category",
    )
    if not rows or int(rows[0][0]) != prova_origem_id:
        raise ValueError("O escalão tem de pertencer à prova de origem.")


def _validar_id(value: int, label: str) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} inválida.")


def _validar_ids(ids: list[int]) -> tuple[int, ...]:
    unique_ids = tuple(dict.fromkeys(ids))
    if not unique_ids or any(
        not isinstance(item, int) or item <= 0 for item in unique_ids
    ):
        raise ValueError("Selecione pelo menos um registo válido.")
    return unique_ids


def _delete_many(
    table: str,
    id_column: str,
    ids: list[int],
    operation: str,
) -> None:
    valid_ids = _validar_ids(ids)
    placeholders = ", ".join("%s" for _ in valid_ids)
    _execute_write(
        f"DELETE FROM {table} WHERE {id_column} IN ({placeholders})",
        valid_ids,
        operation,
    )


def _fetch_all(
    query: str,
    parameters: tuple[object, ...],
    operation: str,
) -> list[tuple]:
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(query, parameters)
        return cursor.fetchall()
    except Error as exc:
        raise ConnectionError(f"{operation} in MySQL: {exc}") from exc
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            close_connection(connection)


def _execute_write(
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
