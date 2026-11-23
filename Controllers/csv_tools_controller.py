"""CSV import and export for students and classes."""

import csv
import logging
import re
from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from io import StringIO
from typing import TypeVar

from Controllers.alunos_turmas_controller import AlunosTurmasController


logger = logging.getLogger(__name__)

CLASS_FIELDS = ("ano_escolar", "letra")
STUDENT_FIELDS = (
    "numeroprocesso",
    "nome",
    "datanasc",
    "sexo",
    "ano_escolar",
    "letra",
)

Identity = TypeVar("Identity", bound=Hashable)


@dataclass(frozen=True)
class ImportSummary:
    imported: int
    duplicates: int
    errors: tuple[str, ...]
    interrupted: bool = False


def export_classes_csv(controller: AlunosTurmasController) -> bytes:
    classes = controller.listar_turmas()
    return _write_csv(
        CLASS_FIELDS,
        ((turma.ano_escolar, turma.letra) for turma in classes),
    )


def export_students_csv(controller: AlunosTurmasController) -> bytes:
    classes = controller.listar_turmas()
    class_by_id = {turma.id: turma for turma in classes}
    students = controller.listar_alunos()
    rows: list[tuple[object, ...]] = []
    for student in students:
        turma = (
            class_by_id.get(student.turma_id)
            if student.turma_id is not None
            else None
        )
        if student.turma_id is not None and turma is None:
            raise ValueError(
                f"A turma do aluno {student.numeroprocesso} não foi encontrada."
            )
        rows.append(
            (
                student.numeroprocesso,
                student.nome,
                student.datanasc.isoformat(),
                student.sexo,
                turma.ano_escolar if turma else "",
                turma.letra if turma else "",
            )
        )
    return _write_csv(STUDENT_FIELDS, rows)


def import_classes_csv(
    content: bytes,
    controller: AlunosTurmasController,
) -> ImportSummary:
    rows = _read_csv(content, CLASS_FIELDS)
    existing = {
        (turma.ano_escolar, turma.letra.upper())
        for turma in controller.listar_turmas()
    }
    return _import_rows(
        rows,
        existing,
        lambda row: _import_class_row(row, controller),
        lambda row: (
            _integer(row, "ano_escolar"),
            _required(row, "letra").upper(),
        ),
    )


def import_students_csv(
    content: bytes,
    controller: AlunosTurmasController,
) -> ImportSummary:
    rows = _read_csv(content, STUDENT_FIELDS)
    classes = controller.listar_turmas()
    class_ids = {
        (turma.ano_escolar, turma.letra.upper()): turma.id for turma in classes
    }
    existing_students = {
        (student.numeroprocesso,) for student in controller.listar_alunos()
    }
    return _import_rows(
        rows,
        existing_students,
        lambda row: _import_student_row(row, controller, class_ids),
        lambda row: (_integer(row, "numeroprocesso"),),
    )


def _import_class_row(
    row: dict[str, str | None],
    controller: AlunosTurmasController,
) -> None:
    controller.criar_turma(
        _integer(row, "ano_escolar"),
        _required(row, "letra").upper(),
    )


def _import_student_row(
    row: dict[str, str | None],
    controller: AlunosTurmasController,
    class_ids: dict[tuple[int, str], int],
) -> None:
    class_year = _value(row, "ano_escolar")
    class_letter = _value(row, "letra").upper()
    if bool(class_year) != bool(class_letter):
        raise ValueError("Indique o ano e a letra da turma.")

    class_id = None
    if class_year:
        try:
            year = int(class_year)
        except ValueError as exc:
            raise ValueError("O ano escolar deve ser um número inteiro.") from exc
        designation = (year, class_letter)
        class_id = class_ids.get(designation)
        if class_id is None:
            raise ValueError(
                f"A turma {designation[0]}.º {designation[1]} não existe."
            )

    birth_date_text = _required(row, "datanasc")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", birth_date_text) is None:
        raise ValueError("A data de nascimento deve usar o formato AAAA-MM-DD.")
    try:
        birth_date = date.fromisoformat(birth_date_text)
    except ValueError as exc:
        raise ValueError("A data de nascimento deve usar o formato AAAA-MM-DD.") from exc

    controller.criar_aluno(
        _integer(row, "numeroprocesso"),
        _required(row, "nome"),
        birth_date,
        _required(row, "sexo").upper(),
        class_id,
    )


def _import_rows(
    rows: list[tuple[int, dict[str, str | None]]],
    existing: set[Identity],
    import_row: Callable[[dict[str, str | None]], None],
    get_identity: Callable[[dict[str, str | None]], Identity],
) -> ImportSummary:
    imported = 0
    duplicates = 0
    errors: list[str] = []
    for line_number, row in rows:
        try:
            identity = get_identity(row)
            if identity in existing:
                duplicates += 1
                continue
            import_row(row)
        except ValueError as exc:
            errors.append(f"Linha {line_number}: {exc}")
            continue
        except ConnectionError:
            logger.exception("CSV import stopped after a database connection error")
            return ImportSummary(imported, duplicates, tuple(errors), interrupted=True)
        existing.add(identity)
        imported += 1
    return ImportSummary(imported, duplicates, tuple(errors))


def _read_csv(
    content: bytes,
    required_fields: tuple[str, ...],
) -> list[tuple[int, dict[str, str | None]]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("O ficheiro deve estar codificado em UTF-8.") from exc
    if not text.strip():
        raise ValueError("O ficheiro CSV está vazio.")

    try:
        delimiter = csv.Sniffer().sniff(
            text[:8192],
            delimiters=";,\t",
        ).delimiter
    except csv.Error:
        delimiter = ";"

    reader = csv.DictReader(StringIO(text, newline=""), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("O CSV não contém cabeçalhos.")
    normalized_fields = [
        str(field or "").strip().lower() for field in reader.fieldnames
    ]
    if any(not field for field in normalized_fields):
        raise ValueError("O CSV contém um cabeçalho vazio.")
    if len(set(normalized_fields)) != len(normalized_fields):
        raise ValueError("O CSV contém cabeçalhos repetidos.")
    reader.fieldnames = normalized_fields
    missing_fields = [
        field for field in required_fields if field not in normalized_fields
    ]
    if missing_fields:
        raise ValueError(
            "Faltam colunas obrigatórias: " + ", ".join(missing_fields) + "."
        )

    rows: list[tuple[int, dict[str, str | None]]] = []
    for row in reader:
        if not any(_value(row, field) for field in normalized_fields):
            continue
        rows.append((reader.line_num, row))
    return rows


def _write_csv(
    fields: tuple[str, ...],
    rows: Iterable[Sequence[object]],
) -> bytes:
    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(fields)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def _value(row: dict[str, str | None], field: str) -> str:
    value = row.get(field)
    return value.strip() if value is not None else ""


def _required(row: dict[str, str | None], field: str) -> str:
    value = _value(row, field)
    if not value:
        raise ValueError(f"A coluna {field} é obrigatória.")
    return value


def _integer(row: dict[str, str | None], field: str) -> int:
    value = _required(row, field)
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"A coluna {field} deve conter um número inteiro.") from exc
