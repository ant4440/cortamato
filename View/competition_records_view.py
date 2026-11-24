"""Management interfaces for competition records."""

import logging
from collections.abc import Callable, Hashable, Sequence
from datetime import datetime
from typing import TypeVar

import flet as ft

from Controllers.alunos_turmas_controller import AlunosTurmasController
from Controllers.competition_records_controller import CompetitionRecordsController
from Controllers.provas_controller import ProvasController
from Model.competition_records import (
    Apurado,
    Chegada,
    Classificacao,
    Dorsal,
    Escalao,
    Inscricao,
    RegraApuramento,
    parse_tempo_chegada,
)
from View.date_time_fields import add_date_time_pickers
from View.feedback import dismiss_temporary_dialog, show_temporary_feedback
from View.formatters import format_numeroprocesso, format_tempo_chegada


logger = logging.getLogger(__name__)
Record = TypeVar("Record")
RecordKey = TypeVar("RecordKey", bound=Hashable)


def _dropdown(
    label: str,
    options: Sequence[tuple[str, str]],
    value: str | None = None,
    width: int = 420,
) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        options=[
            ft.DropdownOption(key=key, text=text)
            for key, text in options
        ],
        width=width,
    )


def _build_prova_filter(
    page: ft.Page,
    provas_controller: ProvasController,
) -> ft.Dropdown:
    try:
        provas = provas_controller.listar_provas()
    except ConnectionError:
        logger.exception("Could not load events for the record filter")
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Não foi possível carregar as provas",
                content=ft.Text(
                    "Não foi possível carregar a lista de provas para o filtro."
                ),
                actions=[
                    ft.TextButton(
                        content="Fechar",
                        on_click=lambda _event: page.pop_dialog(),
                    )
                ],
            )
        )
        provas = []

    return _dropdown(
        "Filtrar por prova",
        [
            ("", "Todas as provas"),
            *[
                (
                    str(prova.idprova),
                    f"{prova.escola} · {prova.data.strftime('%d/%m/%Y')}",
                )
                for prova in provas
            ],
        ],
        value="",
        width=360,
    )


def _parse_int(value: str | None, label: str) -> int:
    try:
        return int(value or "")
    except ValueError:
        raise ValueError(f"Introduza {label} válido.") from None


def _parse_datetime(value: str | None, label: str) -> datetime:
    try:
        return datetime.fromisoformat(value or "")
    except ValueError:
        raise ValueError(f"Introduza {label} no formato AAAA-MM-DD HH:MM.") from None


def _show_form(
    page: ft.Page,
    title: str,
    controls: list[ft.Control],
    feedback: ft.Text,
    on_save: Callable[[object], None],
    width: int = 420,
) -> None:
    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=title,
            content=ft.Column(
                [*controls, feedback],
                tight=True,
                spacing=10,
                width=width,
            ),
            content_padding=ft.Padding.symmetric(horizontal=20, vertical=12),
            actions=[
                ft.TextButton(
                    content="Cancelar",
                    on_click=lambda _event: page.pop_dialog(),
                ),
                ft.FilledButton(content="Guardar", on_click=on_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
    )


def _show_options_error(page: ft.Page, entity: str) -> None:
    logger.exception("Could not load %s form options", entity)
    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title="Não foi possível abrir o formulário",
            content=ft.Text(
                f"Não foi possível carregar as opções de {entity}. "
                "Verifique a ligação à base de dados."
            ),
            actions=[
                ft.TextButton(
                    content="Fechar",
                    on_click=lambda _event: page.pop_dialog(),
                )
            ],
        )
    )


def _build_management_table(
    page: ft.Page,
    palette: dict[str, str],
    panel_builder: Callable[..., ft.Container],
    columns: Sequence[str],
    load_records: Callable[[], list[Record]],
    row_key: Callable[[Record], RecordKey],
    row_values: Callable[[Record], Sequence[str]],
    open_form: Callable[[Record | None, Callable[[], None]], None],
    delete_records: Callable[[list[RecordKey]], None] | None,
    entity: str,
    entity_plural: str,
    empty_message: str,
    delete_warning: str,
    allow_add: bool = True,
    extra_actions: Callable[[Callable[[], None]], list[ft.Control]] | None = None,
    read_only: bool = False,
    prova_filter: ft.Dropdown | None = None,
    record_prova_id: Callable[[Record], int] | None = None,
) -> ft.Control:
    records: list[Record] = []
    selected_ids: set[RecordKey] = set()
    selection_mode = False
    table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text(title, size=13, color=palette["muted"])) for title in columns]
        + [ft.DataColumn(ft.Text("", size=13, color=palette["muted"]))],
        rows=[],
        bgcolor=palette["surface"],
        column_spacing=22,
        horizontal_margin=12,
        heading_row_height=52,
        data_row_min_height=54,
        data_row_max_height=60,
        horizontal_lines=ft.BorderSide(0.5, palette["table_line"]),
    )
    message = ft.Text("", size=12, color=palette["error"], visible=False)
    empty = ft.Text(
        empty_message,
        size=13,
        color=palette["muted"],
        visible=False,
    )
    add_button = ft.IconButton(
        icon=ft.Icons.ADD,
        tooltip=f"Adicionar {entity}",
    )
    delete_button = ft.IconButton(
        icon=ft.Icons.DELETE_OUTLINE,
        tooltip="Selecionar para eliminar",
        visible=delete_records is not None and not read_only,
    )
    cancel_button = ft.IconButton(
        icon=ft.Icons.CLOSE,
        tooltip="Cancelar seleção",
        visible=False,
    )
    refresh_button = ft.IconButton(
        icon=ft.Icons.REFRESH,
        tooltip="Atualizar",
        visible=not read_only,
    )

    def update_selection_controls() -> None:
        add_button.visible = allow_add and not read_only and not selection_mode
        delete_button.visible = delete_records is not None and not read_only
        cancel_button.visible = selection_mode and not read_only
        delete_button.disabled = selection_mode and not selected_ids
        delete_button.tooltip = (
            "Eliminar selecionados"
            if selection_mode
            else "Selecionar para eliminar"
        )

    def visible_records() -> list[Record]:
        selected_prova = prova_filter.value if prova_filter is not None else None
        if not selected_prova or record_prova_id is None:
            return records
        return [
            record
            for record in records
            if str(record_prova_id(record)) == selected_prova
        ]

    def build_rows() -> list[ft.DataRow]:
        rows: list[ft.DataRow] = []
        for record in visible_records():
            action: ft.Control
            if read_only:
                action = ft.Container(width=40)
            elif selection_mode:
                action = ft.Checkbox(
                    value=row_key(record) in selected_ids,
                    overlay_color=ft.Colors.TRANSPARENT,
                    on_change=lambda event, item=row_key(record): toggle_selection(
                        event,
                        item,
                    ),
                )
            else:
                action = ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    tooltip=f"Editar {entity}",
                    on_click=lambda _event, item=record: open_form(item, refresh),
                )
            cells = [
                ft.DataCell(ft.Text(value, size=14, color=palette["text"]))
                for value in row_values(record)
            ]
            cells.append(ft.DataCell(action))
            rows.append(ft.DataRow(cells=cells))
        return rows

    def refresh(update_page: bool = True) -> None:
        nonlocal records
        try:
            records = load_records()
            selected_ids.intersection_update(row_key(record) for record in records)
            message.value = ""
            message.visible = False
            empty.visible = not visible_records()
        except ConnectionError:
            logger.exception("Could not load %s", entity)
            records = []
            selected_ids.clear()
            show_temporary_feedback(
                page,
                message,
                f"Não foi possível carregar {entity}.",
            )
            empty.visible = False
        table.rows = build_rows()
        if update_page:
            page.update()

    def update_prova_filter(_: object) -> None:
        nonlocal selection_mode
        selection_mode = False
        selected_ids.clear()
        update_selection_controls()
        table.rows = build_rows()
        empty.visible = not visible_records()
        page.update()

    def toggle_selection(
        event: ft.Event[ft.Checkbox],
        record_id: RecordKey,
    ) -> None:
        if event.control.value:
            selected_ids.add(record_id)
        else:
            selected_ids.discard(record_id)
        update_selection_controls()
        page.update()

    def begin_selection(_: object) -> None:
        nonlocal selection_mode
        if read_only:
            return
        selection_mode = True
        selected_ids.clear()
        update_selection_controls()
        table.rows = build_rows()
        page.update()

    def cancel_selection(_: object) -> None:
        nonlocal selection_mode
        selection_mode = False
        selected_ids.clear()
        update_selection_controls()
        table.rows = build_rows()
        page.update()

    def open_delete_confirmation() -> None:
        if delete_records is None or not selected_ids:
            return
        count = len(selected_ids)
        noun = entity if count == 1 else entity_plural
        feedback = ft.Text("", size=12, color=palette["error"], visible=False)

        def confirm_delete(_: object) -> None:
            nonlocal selection_mode
            try:
                delete_records(sorted(selected_ids))
            except ConnectionError:
                logger.exception("Could not delete selected %s", entity)
                show_temporary_feedback(
                    page,
                    feedback,
                    f"Não foi possível eliminar {entity}.",
                )
                page.update()
                return
            except ValueError as exc:
                show_temporary_feedback(page, feedback, str(exc))
                page.update()
                return

            page.pop_dialog()
            selection_mode = False
            selected_ids.clear()
            update_selection_controls()
            refresh()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Confirmar eliminação",
                content=ft.Column(
                    [
                        ft.Text(f"Deseja apagar {count} {noun}?", size=15),
                        ft.Text(delete_warning, size=12, color=palette["muted"]),
                        feedback,
                    ],
                    tight=True,
                    spacing=10,
                    width=380,
                ),
                actions=[
                    ft.TextButton(
                        content="Não",
                        on_click=lambda _event: page.pop_dialog(),
                    ),
                    ft.FilledButton(
                        content="Sim",
                        on_click=confirm_delete,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    add_button.visible = allow_add and not read_only
    add_button.on_click = lambda _event: open_form(None, refresh)
    delete_button.on_click = (
        lambda _event: open_delete_confirmation()
        if selection_mode
        else begin_selection(_event)
    )
    cancel_button.on_click = cancel_selection
    refresh_button.on_click = lambda _event: refresh()
    if prova_filter is not None:
        prova_filter.on_select = update_prova_filter
    actions = (
        extra_actions(refresh)
        if extra_actions is not None and not read_only
        else []
    )
    toolbar = ft.Row(
        [
            add_button,
            delete_button,
            cancel_button,
            *actions,
            ft.Container(expand=True),
            refresh_button,
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    content = ft.Column(
        [
            message,
            empty,
            ft.Row([table], scroll=ft.ScrollMode.AUTO),
        ],
        spacing=8,
        tight=True,
    )
    refresh(update_page=False)
    table_content: list[ft.Control] = []
    if prova_filter is not None:
        table_content.append(ft.Row([prova_filter]))
    table_content.extend(
        [
            toolbar,
            panel_builder(
                content,
                padding=18,
                bgcolor=palette["surface"],
            ),
        ]
    )
    return ft.Column(
        table_content,
        spacing=8,
        tight=True,
    )


def build_inscricoes_view(
    page: ft.Page,
    controller: CompetitionRecordsController,
    provas_controller: ProvasController,
    alunos_controller: AlunosTurmasController,
    palette: dict[str, str],
    panel_builder: Callable[..., ft.Container],
    read_only: bool = False,
) -> ft.Control:
    prova_filter = _build_prova_filter(page, provas_controller)
    states = [
        ("nao_inscrito", "Não inscrito"),
        ("inscrito", "Inscrito"),
        ("participante", "Participante"),
        ("organizacao", "Organização"),
    ]

    def open_form(
        inscricao: Inscricao | None,
        refresh: Callable[[], None],
    ) -> None:
        try:
            provas = provas_controller.listar_provas()
            alunos = alunos_controller.listar_alunos()
        except ConnectionError:
            _show_options_error(page, "provas e alunos")
            return

        if inscricao is None:
            prova_field: ft.Control = _dropdown(
                "Prova",
                [
                    (
                        str(prova.idprova),
                        f"{prova.escola} · {prova.data.strftime('%d/%m/%Y')}",
                    )
                    for prova in provas
                ],
            )
            student_field: ft.Control = _dropdown(
                "Aluno",
                [
                    (
                        str(aluno.numeroprocesso),
                        f"{aluno.nome} · {format_numeroprocesso(aluno.numeroprocesso)}",
                    )
                    for aluno in alunos
                ],
            )
        else:
            prova_field = ft.Text(
                f"Prova: {inscricao.prova_label}",
                size=14,
                color=palette["muted"],
            )
            student_field = ft.Text(
                f"Aluno: {inscricao.nome_aluno} · "
                f"{format_numeroprocesso(inscricao.numeroprocesso)}",
                size=14,
                color=palette["muted"],
            )
        state_field = _dropdown(
            "Estado",
            states,
            inscricao.estado if inscricao else "inscrito",
        )
        da_value = bool(inscricao.indicador_da if inscricao else False)
        da_checkbox = ft.IconButton(
            icon=(
                ft.Icons.CHECK_BOX
                if da_value
                else ft.Icons.CHECK_BOX_OUTLINE_BLANK
            ),
            icon_color=palette["primary"] if da_value else palette["muted"],
            tooltip="Alternar indicador de desporto adaptado",
        )

        def toggle_da(_event: object) -> None:
            nonlocal da_value
            da_value = not da_value
            da_checkbox.icon = (
                ft.Icons.CHECK_BOX
                if da_value
                else ft.Icons.CHECK_BOX_OUTLINE_BLANK
            )
            da_checkbox.icon_color = (
                palette["primary"] if da_value else palette["muted"]
            )
            page.update()

        da_checkbox.on_click = toggle_da
        da_field = ft.Row(
            [
                da_checkbox,
                ft.Text(
                    "Indicador de desporto adaptado",
                    size=14,
                    color=palette["text"],
                ),
            ],
            spacing=4,
            height=48,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        function_field = ft.TextField(
            label="Função (obrigatória para organização)",
            value=inscricao.funcao or "" if inscricao else "",
            width=420,
        )
        feedback = ft.Text("", size=12, color=palette["error"], visible=False)

        def save(_: object) -> None:
            feedback.value = ""
            feedback.visible = False
            try:
                prova_id = (
                    inscricao.idprova
                    if inscricao
                    else _parse_int(prova_field.value, "uma prova")
                )
                process_number = (
                    inscricao.numeroprocesso
                    if inscricao
                    else _parse_int(student_field.value, "um aluno")
                )
                values = (
                    prova_id,
                    process_number,
                    state_field.value or "",
                    da_value,
                    function_field.value or "",
                )
                if inscricao is None:
                    controller.criar_inscricao(*values)
                else:
                    controller.atualizar_inscricao(inscricao.id, *values)
            except ValueError as exc:
                show_temporary_feedback(
                    page,
                    feedback,
                    str(exc) or "Selecione uma prova e um aluno.",
                )
                page.update()
                return
            except ConnectionError:
                logger.exception("Could not save registration")
                show_temporary_feedback(
                    page,
                    feedback,
                    "Não foi possível guardar a inscrição. "
                    "Verifique se já existe para esta prova.",
                )
                page.update()
                return
            page.pop_dialog()
            refresh()

        _show_form(
            page,
            "Editar inscrição" if inscricao else "Adicionar inscrição",
            [prova_field, student_field, state_field, da_field, function_field],
            feedback,
            save,
        )

    return _build_management_table(
        page,
        palette,
        panel_builder,
        [
            "ID",
            "Prova",
            "Aluno",
            "N.º processo",
            "Estado",
            "DA",
            "Função",
            "Registada em",
        ],
        controller.listar_inscricoes,
        lambda item: item.id,
        lambda item: [
            str(item.id),
            item.prova_label,
            item.nome_aluno,
            format_numeroprocesso(item.numeroprocesso),
            dict(states).get(item.estado, item.estado),
            "Sim" if item.indicador_da else "Não",
            item.funcao or "—",
            item.data_inscricao.strftime("%d/%m/%Y %H:%M"),
        ],
        open_form,
        controller.eliminar_inscricoes,
        "inscrição",
        "inscrições",
        "Ainda não existem inscrições registadas.",
        "As dorsais, chegadas, desistências, desclassificações e "
        "classificações e apuramentos associados também serão eliminados.",
        read_only=read_only,
        prova_filter=prova_filter,
        record_prova_id=lambda item: item.idprova,
    )


def build_dorsais_view(
    page: ft.Page,
    controller: CompetitionRecordsController,
    provas_controller: ProvasController,
    palette: dict[str, str],
    panel_builder: Callable[..., ft.Container],
    read_only: bool = False,
) -> ft.Control:
    prova_filter = _build_prova_filter(page, provas_controller)
    prova_ids_by_inscricao: dict[int, int] = {}
    states = [
        ("atribuido", "Atribuído"),
        ("entregue", "Entregue"),
        ("devolvido", "Devolvido"),
    ]

    def open_form(dorsal: Dorsal | None, refresh: Callable[[], None]) -> None:
        try:
            inscricoes = controller.listar_inscricoes()
            dorsais = controller.listar_dorsais()
        except ConnectionError:
            _show_options_error(page, "inscrições")
            return

        used_registrations = {
            item.inscricao_id
            for item in dorsais
            if dorsal is None or item.id != dorsal.id
        }
        available_registrations = [
            item for item in inscricoes if item.id not in used_registrations
        ]
        registration_field = _dropdown(
            "Inscrição",
            [
                (
                    str(item.id),
                    f"{item.nome_aluno} · "
                    f"{format_numeroprocesso(item.numeroprocesso)} · "
                    f"{item.prova_label}",
                )
                for item in available_registrations
            ],
            str(dorsal.inscricao_id) if dorsal else None,
        )
        registrations_by_id = {item.id: item for item in inscricoes}
        numbers_by_prova: dict[int, list[int]] = {}
        for item in dorsais:
            registration = registrations_by_id.get(item.inscricao_id)
            if registration is not None:
                numbers_by_prova.setdefault(registration.idprova, []).append(
                    item.numero
                )

        def next_dorsal_number(registration_value: str | None) -> str:
            try:
                registration_id = int(registration_value or "")
            except ValueError:
                return ""
            registration = registrations_by_id.get(registration_id)
            if registration is None:
                return ""
            return str(
                max(numbers_by_prova.get(registration.idprova, []), default=0) + 1
            )

        state_field = _dropdown(
            "Estado",
            states,
            dorsal.estado if dorsal else "atribuido",
        )
        delivered_field = ft.TextField(
            label="Entregue em",
            hint_text="AAAA-MM-DD HH:MM",
            value=(
                dorsal.entregue_em.isoformat(sep=" ", timespec="minutes")
                if dorsal and dorsal.entregue_em
                else ""
            ),
            width=420,
        )
        add_date_time_pickers(page, delivered_field)
        number_field = ft.TextField(
            label="Número do dorsal",
            value=(
                str(dorsal.numero)
                if dorsal
                else next_dorsal_number(registration_field.value)
            ),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=420,
        )
        feedback = ft.Text("", size=12, color=palette["error"], visible=False)
        controls: list[ft.Control] = [
            ft.Text(
                (
                    f"Dorsal n.º {dorsal.numero}"
                    if dorsal
                    else "O próximo número disponível é sugerido automaticamente."
                ),
                size=12,
                color=palette["muted"],
            ),
            (
                ft.Text(
                    f"{dorsal.nome_aluno} · "
                    f"{format_numeroprocesso(dorsal.numeroprocesso)} · "
                    f"{dorsal.prova_label}",
                    size=14,
                    color=palette["text"],
                )
                if dorsal
                else registration_field
            ),
            state_field,
            delivered_field,
            number_field,
        ]

        def update_number_suggestion(_: object) -> None:
            number_field.value = next_dorsal_number(registration_field.value)
            page.update()

        registration_field.on_select = update_number_suggestion

        def save(_: object) -> None:
            feedback.value = ""
            feedback.visible = False
            try:
                registration_id = (
                    _parse_int(registration_field.value, "uma inscrição")
                    if dorsal is None
                    else dorsal.inscricao_id
                )
                number = _parse_int(number_field.value, "um número de dorsal")
                delivered_at = (
                    _parse_datetime(delivered_field.value, "a data de entrega")
                    if state_field.value == "entregue"
                    else None
                )
                if dorsal is None:
                    controller.criar_dorsal(
                        registration_id,
                        number,
                        state_field.value or "",
                        delivered_at,
                    )
                else:
                    controller.atualizar_dorsal(
                        dorsal.id,
                        number,
                        state_field.value or "",
                        delivered_at,
                    )
            except ValueError as exc:
                show_temporary_feedback(page, feedback, str(exc))
                page.update()
                return
            except ConnectionError:
                logger.exception("Could not save bib")
                show_temporary_feedback(
                    page,
                    feedback,
                    "Não foi possível guardar o dorsal. "
                    "Confirme se a inscrição já tem dorsal.",
                )
                page.update()
                return
            page.pop_dialog()
            refresh()

        _show_form(
            page,
            "Editar dorsal" if dorsal else "Atribuir dorsal",
            controls,
            feedback,
            save,
        )

    def load_dorsais() -> list[Dorsal]:
        nonlocal prova_ids_by_inscricao
        inscricoes = controller.listar_inscricoes()
        prova_ids_by_inscricao = {
            inscricao.id: inscricao.idprova for inscricao in inscricoes
        }
        return controller.listar_dorsais()

    return _build_management_table(
        page,
        palette,
        panel_builder,
        [
            "ID",
            "Dorsal",
            "Aluno",
            "N.º processo",
            "Prova",
            "Estado",
            "Entregue em",
        ],
        load_dorsais,
        lambda item: item.id,
        lambda item: [
            str(item.id),
            str(item.numero),
            item.nome_aluno,
            format_numeroprocesso(item.numeroprocesso),
            item.prova_label,
            dict(states).get(item.estado, item.estado),
            (
                item.entregue_em.strftime("%d/%m/%Y %H:%M")
                if item.entregue_em
                else "—"
            ),
        ],
        open_form,
        controller.eliminar_dorsais,
        "dorsal",
        "dorsais",
        "Ainda não existem dorsais atribuídos.",
        "Apenas a atribuição do dorsal será eliminada; a inscrição mantém-se.",
        read_only=read_only,
        prova_filter=prova_filter,
        record_prova_id=lambda item: prova_ids_by_inscricao.get(
            item.inscricao_id,
            0,
        ),
    )


def build_chegadas_view(
    page: ft.Page,
    controller: CompetitionRecordsController,
    provas_controller: ProvasController,
    palette: dict[str, str],
    panel_builder: Callable[..., ft.Container],
    read_only: bool = False,
) -> ft.Control:
    prova_filter = _build_prova_filter(page, provas_controller)
    prova_ids_by_inscricao: dict[int, int] = {}

    def open_form(chegada: Chegada | None, refresh: Callable[[], None]) -> None:
        try:
            inscricoes = controller.listar_inscricoes()
            arrivals = controller.listar_chegadas()
        except ConnectionError:
            _show_options_error(page, "inscrições e chegadas")
            return

        selected_prova = prova_filter.value
        filtered_inscricoes = [
            item
            for item in inscricoes
            if not selected_prova or str(item.idprova) == selected_prova
        ]
        used_registrations = {
            item.inscricao_id
            for item in arrivals
            if chegada is None or item.id != chegada.id
        }
        available_registrations = [
            item
            for item in filtered_inscricoes
            if item.id not in used_registrations
        ]
        registration_field = _dropdown(
            "Inscrição",
            [
                (
                    str(item.id),
                    f"{item.nome_aluno} · "
                    f"{format_numeroprocesso(item.numeroprocesso)} · "
                    f"{item.prova_label}",
                )
                for item in available_registrations
            ],
            str(chegada.inscricao_id) if chegada else None,
        )
        tempo_field = ft.TextField(
            label="Tempo de chegada",
            hint_text="MM:SS.mmm",
            value=(
                format_tempo_chegada(chegada.tempo_chegada)
                if chegada and chegada.tempo_chegada is not None
                else ""
            ),
            width=420,
        )
        feedback = ft.Text("", size=12, color=palette["error"], visible=False)
        controls: list[ft.Control] = [
            (
                ft.Text(
                    f"{chegada.nome_aluno} · "
                    f"{format_numeroprocesso(chegada.numeroprocesso)} · "
                    f"{chegada.prova_label}",
                    size=14,
                    color=palette["text"],
                )
                if chegada
                else registration_field
            ),
            tempo_field,
        ]

        def save(_: object) -> None:
            feedback.value = ""
            feedback.visible = False
            try:
                tempo_chegada = parse_tempo_chegada(tempo_field.value)
                correction_id = chegada.corrigido_de if chegada else None
                if chegada is None:
                    registration_id = _parse_int(
                        registration_field.value,
                        "uma inscrição",
                    )
                    controller.criar_chegada(
                        registration_id,
                        tempo_chegada,
                        "manual",
                        correction_id,
                    )
                else:
                    controller.atualizar_chegada(
                        chegada.id,
                        chegada.inscricao_id,
                        tempo_chegada,
                        chegada.metodo,
                        correction_id,
                    )
            except ValueError as exc:
                show_temporary_feedback(page, feedback, str(exc))
                page.update()
                return
            except ConnectionError:
                logger.exception("Could not save arrival")
                show_temporary_feedback(
                    page,
                    feedback,
                    "Não foi possível guardar a chegada. "
                    "Confirme se a inscrição já tem uma chegada.",
                )
                page.update()
                return
            page.pop_dialog()
            refresh()

        _show_form(
            page,
            "Editar chegada" if chegada else "Registar chegada",
            controls,
            feedback,
            save,
        )

    def load_chegadas() -> list[Chegada]:
        nonlocal prova_ids_by_inscricao
        inscricoes = controller.listar_inscricoes()
        prova_ids_by_inscricao = {
            inscricao.id: inscricao.idprova for inscricao in inscricoes
        }
        return controller.listar_chegadas()

    return _build_management_table(
        page,
        palette,
        panel_builder,
        [
            "ID",
            "Aluno",
            "N.º processo",
            "Dorsal",
            "Prova",
            "Tempo de chegada",
            "Método",
            "Correção",
        ],
        load_chegadas,
        lambda item: item.id,
        lambda item: [
            str(item.id),
            item.nome_aluno,
            format_numeroprocesso(item.numeroprocesso),
            str(item.dorsal) if item.dorsal is not None else "—",
            item.prova_label,
            format_tempo_chegada(item.tempo_chegada),
            {"manual": "Manual", "qrcode": "QR code"}.get(
                item.metodo,
                item.metodo,
            ),
            str(item.corrigido_de) if item.corrigido_de is not None else "—",
        ],
        open_form,
        controller.eliminar_chegadas,
        "chegada",
        "chegadas",
        "Ainda não existem chegadas registadas.",
        "As correções que apontam para as chegadas eliminadas ficarão sem referência.",
        read_only=read_only,
        prova_filter=prova_filter,
        record_prova_id=lambda item: prova_ids_by_inscricao.get(
            item.inscricao_id,
            0,
        ),
    )


def build_classificacoes_view(
    page: ft.Page,
    controller: CompetitionRecordsController,
    provas_controller: ProvasController,
    palette: dict[str, str],
    panel_builder: Callable[..., ft.Container],
    read_only: bool = False,
) -> ft.Control:
    prova_filter = _build_prova_filter(page, provas_controller)

    def open_form(
        classificacao: Classificacao | None,
        refresh: Callable[[], None],
    ) -> None:
        try:
            provas = provas_controller.listar_provas()
            inscricoes = controller.listar_inscricoes()
            escaloes = controller.listar_escaloes()
        except ConnectionError:
            _show_options_error(page, "provas, inscrições e escalões")
            return

        prova_options = [
            ("", "Todas as provas"),
            *[
                (
                    str(prova.idprova),
                    f"{prova.escola} · {prova.data.strftime('%d/%m/%Y')}",
                )
                for prova in provas
            ],
        ]
        prova_field = _dropdown(
            "Prova",
            prova_options,
            str(classificacao.prova_id) if classificacao else "",
        )
        inscricoes_por_id = {str(item.id): item for item in inscricoes}
        registration_field = _dropdown(
            "Inscrição",
            [
                (
                    str(item.id),
                    f"{item.nome_aluno} · "
                    f"{format_numeroprocesso(item.numeroprocesso)} · "
                    f"{item.prova_label}",
                )
                for item in inscricoes
            ],
            str(classificacao.inscricao_id) if classificacao else "",
        )
        category_field = _dropdown(
            "Escalão (opcional)",
            [("", "Geral")],
            str(classificacao.escalao_id or "") if classificacao else "",
        )

        def update_dependent_options(event: object | None = None) -> None:
            selected_prova = prova_field.value or ""
            current_prova_id = int(selected_prova) if selected_prova else None
            registration_field.options = [
                ft.DropdownOption(
                    key=str(item.id),
                    text=(
                        f"{item.nome_aluno} · "
                        f"{format_numeroprocesso(item.numeroprocesso)} · "
                        f"{item.prova_label}"
                    ),
                )
                for item in inscricoes
                if not selected_prova or str(item.idprova) == selected_prova
            ]
            valid_registration_ids = {
                option.key for option in registration_field.options
            }
            if (
                registration_field.value
                and registration_field.value not in valid_registration_ids
            ):
                registration_field.value = ""
            category_field.options = [
                ft.DropdownOption(key="", text="Geral"),
                *[
                    ft.DropdownOption(
                        key=str(item.id),
                        text=item.designacao,
                    )
                    for item in escaloes
                    if (
                        current_prova_id is None
                        or item.prova_id == current_prova_id
                    )
                ],
            ]
            valid_category_ids = {
                option.key for option in category_field.options if option.key
            }
            if category_field.value and category_field.value not in valid_category_ids:
                category_field.value = ""
            if event is not None:
                page.update()

        def select_registration(event: object | None = None) -> None:
            selected_inscricao = inscricoes_por_id.get(
                registration_field.value or ""
            )
            if not prova_field.value and selected_inscricao is not None:
                prova_field.value = str(selected_inscricao.idprova)
            update_dependent_options(event)

        prova_field.on_select = update_dependent_options
        registration_field.on_select = select_registration
        update_dependent_options()
        position_field = ft.TextField(
            label="Posição",
            value=str(classificacao.posicao) if classificacao else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=420,
        )
        feedback = ft.Text("", size=12, color=palette["error"], visible=False)

        def save(_: object) -> None:
            feedback.value = ""
            feedback.visible = False
            try:
                registration_id = _parse_int(
                    registration_field.value,
                    "uma inscrição",
                )
                inscricao = inscricoes_por_id.get(str(registration_id))
                if inscricao is None:
                    raise ValueError("Selecione uma inscrição válida.")
                prova_id = inscricao.idprova
                if prova_field.value and prova_field.value != str(prova_id):
                    raise ValueError(
                        "A inscrição selecionada não pertence à prova escolhida."
                    )
                category_id = (
                    _parse_int(category_field.value, "um escalão")
                    if category_field.value
                    else None
                )
                position = _parse_int(position_field.value, "uma posição")
                if classificacao is None:
                    controller.criar_classificacao(
                        registration_id,
                        prova_id,
                        category_id,
                        position,
                    )
                else:
                    controller.atualizar_classificacao(
                        classificacao.id,
                        registration_id,
                        prova_id,
                        category_id,
                        position,
                    )
            except ValueError as exc:
                show_temporary_feedback(page, feedback, str(exc))
                page.update()
                return
            except ConnectionError:
                logger.exception("Could not save classification")
                show_temporary_feedback(
                    page,
                    feedback,
                    "Não foi possível guardar a classificação. "
                    "Confirme a prova, inscrição e posição.",
                )
                page.update()
                return
            page.pop_dialog()
            refresh()

        _show_form(
            page,
            "Editar classificação" if classificacao else "Adicionar classificação",
            [prova_field, registration_field, category_field, position_field],
            feedback,
            save,
        )

    return _build_management_table(
        page,
        palette,
        panel_builder,
        ["ID", "Posição", "Aluno", "N.º processo", "Prova", "Escalão"],
        controller.listar_classificacoes,
        lambda item: item.id,
        lambda item: [
            str(item.id),
            str(item.posicao),
            item.nome_aluno,
            format_numeroprocesso(item.numeroprocesso),
            item.prova_label,
            item.escalao,
        ],
        open_form,
        controller.eliminar_classificacoes,
        "classificação",
        "classificações",
        "Ainda não existem classificações registadas.",
        "Os apuramentos associados às classificações eliminadas também serão eliminados.",
        read_only=read_only,
        prova_filter=prova_filter,
        record_prova_id=lambda item: item.prova_id,
    )


def build_categories_view(
    page: ft.Page,
    controller: CompetitionRecordsController,
    provas_controller: ProvasController,
    palette: dict[str, str],
    panel_builder: Callable[..., ft.Container],
    read_only: bool = False,
) -> ft.Control:
    selected_tab = "escaloes"
    tab_content = ft.Container(expand=True)
    tab_titles = {
        "escaloes": ft.Text("Escalões"),
        "rules": ft.Text("Regras de apuramento"),
        "qualified": ft.Text("Apurados"),
    }
    tabs = {
        key: ft.OutlinedButton(content=label)
        for key, label in tab_titles.items()
    }

    def build_escaloes_table() -> ft.Control:
        def open_form(
            escalao: Escalao | None,
            refresh: Callable[[], None],
        ) -> None:
            try:
                provas = provas_controller.listar_provas()
            except ConnectionError:
                _show_options_error(page, "provas")
                return

            prova_field = _dropdown(
                "Prova",
                [
                    (
                        str(prova.idprova),
                        f"{prova.escola} · {prova.data.strftime('%d/%m/%Y')}",
                    )
                    for prova in provas
                ],
                str(escalao.prova_id) if escalao else None,
            )
            name_field = ft.TextField(
                label="Designação",
                value=escalao.designacao if escalao else "",
                width=420,
            )
            sex_field = _dropdown(
                "Sexo",
                [("F", "Feminino"), ("M", "Masculino")],
                escalao.sexo if escalao else None,
            )
            min_year_field = ft.TextField(
                label="Ano de nascimento mínimo",
                value=str(escalao.anonasc_min) if escalao else "",
                keyboard_type=ft.KeyboardType.NUMBER,
                width=420,
            )
            max_year_field = ft.TextField(
                label="Ano de nascimento máximo",
                value=str(escalao.anonasc_max) if escalao else "",
                keyboard_type=ft.KeyboardType.NUMBER,
                width=420,
            )
            da_value = bool(escalao.da if escalao else False)
            da_checkbox = ft.IconButton(
                icon=(
                    ft.Icons.CHECK_BOX
                    if da_value
                    else ft.Icons.CHECK_BOX_OUTLINE_BLANK
                ),
                icon_color=palette["primary"] if da_value else palette["muted"],
                tooltip="Alternar escalão de desporto adaptado",
            )

            def toggle_da(_event: object) -> None:
                nonlocal da_value
                da_value = not da_value
                da_checkbox.icon = (
                    ft.Icons.CHECK_BOX
                    if da_value
                    else ft.Icons.CHECK_BOX_OUTLINE_BLANK
                )
                da_checkbox.icon_color = (
                    palette["primary"] if da_value else palette["muted"]
                )
                page.update()

            da_checkbox.on_click = toggle_da
            da_control = ft.Row(
                [
                    da_checkbox,
                    ft.Text(
                        "Escalão de desporto adaptado",
                        size=14,
                        color=palette["text"],
                    ),
                ],
                spacing=4,
                height=48,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            feedback = ft.Text("", size=12, color=palette["error"], visible=False)

            def save(_: object) -> None:
                feedback.value = ""
                feedback.visible = False
                try:
                    prova_id = _parse_int(prova_field.value, "uma prova")
                    min_year = _parse_int(
                        min_year_field.value,
                        "um ano de nascimento mínimo",
                    )
                    max_year = _parse_int(
                        max_year_field.value,
                        "um ano de nascimento máximo",
                    )
                    values = (
                        prova_id,
                        name_field.value or "",
                        sex_field.value or "",
                        min_year,
                        max_year,
                        da_value,
                    )
                    if escalao is None:
                        controller.criar_escalao(*values)
                    else:
                        controller.atualizar_escalao(escalao.id, *values)
                except ValueError as exc:
                    show_temporary_feedback(page, feedback, str(exc))
                    page.update()
                    return
                except ConnectionError:
                    logger.exception("Could not save age group")
                    show_temporary_feedback(
                        page,
                        feedback,
                        "Não foi possível guardar o escalão. "
                        "Confirme se já existe nessa prova.",
                    )
                    page.update()
                    return
                page.pop_dialog()
                refresh()

            _show_form(
                page,
                "Editar escalão" if escalao else "Adicionar escalão",
                [
                    prova_field,
                    name_field,
                    sex_field,
                    min_year_field,
                    max_year_field,
                    da_control,
                ],
                feedback,
                save,
            )

        return _build_management_table(
            page,
            palette,
            panel_builder,
            ["ID", "Prova", "Escalão", "Sexo", "Nascimentos", "DA"],
            controller.listar_escaloes,
            lambda item: item.id,
            lambda item: [
                str(item.id),
                item.prova_label,
                item.designacao,
                "Feminino" if item.sexo == "F" else "Masculino",
                f"{item.anonasc_min}–{item.anonasc_max}",
                "Sim" if item.da else "Não",
            ],
            open_form,
            controller.eliminar_escalaoes,
            "escalão",
            "escalões",
            "Ainda não existem escalões registados.",
            "As regras de apuramento e listas de partida associadas serão eliminadas; "
            "as classificações manter-se-ão sem escalão.",
            read_only=read_only,
        )

    def build_rules_table() -> ft.Control:
        def open_form(
            regra: RegraApuramento | None,
            refresh: Callable[[], None],
        ) -> None:
            try:
                provas = provas_controller.listar_provas()
                escaloes = controller.listar_escaloes()
            except ConnectionError:
                _show_options_error(page, "provas e escalões")
                return

            event_options = [
                (
                    str(prova.idprova),
                    f"{prova.escola} · {prova.data.strftime('%d/%m/%Y')}",
                )
                for prova in provas
            ]
            origin_field = _dropdown(
                "Prova de origem",
                event_options,
                str(regra.prova_origem_id) if regra else None,
            )
            destination_field = _dropdown(
                "Prova de destino",
                event_options,
                str(regra.prova_destino_id) if regra else None,
            )
            category_field = _dropdown(
                "Escalão",
                [],
                str(regra.escalao_id) if regra else None,
            )

            def update_category_options(event: object | None = None) -> None:
                origin_id = int(origin_field.value) if origin_field.value else None
                category_field.options = [
                    ft.DropdownOption(
                        key=str(item.id),
                        text=item.designacao,
                    )
                    for item in escaloes
                    if item.prova_id == origin_id
                ]
                valid_ids = {
                    option.key for option in category_field.options
                }
                if category_field.value and category_field.value not in valid_ids:
                    category_field.value = None
                if event is not None:
                    page.update()

            origin_field.on_select = update_category_options
            update_category_options()
            count_field = ft.TextField(
                label="Número de apurados",
                value=str(regra.numero_apurados) if regra else "",
                keyboard_type=ft.KeyboardType.NUMBER,
                width=420,
            )
            feedback = ft.Text("", size=12, color=palette["error"], visible=False)

            def save(_: object) -> None:
                feedback.value = ""
                feedback.visible = False
                try:
                    origin_id = _parse_int(origin_field.value, "uma prova de origem")
                    destination_id = _parse_int(
                        destination_field.value,
                        "uma prova de destino",
                    )
                    category_id = _parse_int(category_field.value, "um escalão")
                    number = _parse_int(count_field.value, "um número de apurados")
                    if regra is None:
                        controller.criar_regra_apuramento(
                            origin_id,
                            destination_id,
                            category_id,
                            number,
                        )
                    else:
                        controller.atualizar_regra_apuramento(
                            regra.id,
                            origin_id,
                            destination_id,
                            category_id,
                            number,
                        )
                except ValueError as exc:
                    show_temporary_feedback(page, feedback, str(exc))
                    page.update()
                    return
                except ConnectionError:
                    logger.exception("Could not save qualification rule")
                    show_temporary_feedback(
                        page,
                        feedback,
                        "Não foi possível guardar a regra. "
                        "Confirme as provas e o escalão selecionados.",
                    )
                    page.update()
                    return
                page.pop_dialog()
                refresh()

            _show_form(
                page,
                "Editar regra" if regra else "Adicionar regra",
                [
                    origin_field,
                    destination_field,
                    category_field,
                    count_field,
                ],
                feedback,
                save,
            )

        return _build_management_table(
            page,
            palette,
            panel_builder,
            ["ID", "Origem", "Destino", "Escalão", "Apurados"],
            controller.listar_regras_apuramento,
            lambda item: item.id,
            lambda item: [
                str(item.id),
                item.prova_origem,
                item.prova_destino,
                item.escalao,
                str(item.numero_apurados),
            ],
            open_form,
            controller.eliminar_regras_apuramento,
            "regra",
            "regras",
            "Ainda não existem regras de apuramento.",
            "Gere novamente os apuramentos do evento de destino para aplicar esta alteração.",
            read_only=read_only,
        )

    def build_qualified_table() -> ft.Control:
        states = [
            ("apurado", "Apurado"),
            ("confirmado", "Confirmado"),
            ("desistiu", "Desistiu"),
        ]

        def open_form(
            apurado: Apurado | None,
            refresh: Callable[[], None],
        ) -> None:
            if apurado is None:
                return
            state_field = _dropdown(
                "Estado",
                states,
                apurado.estado,
            )
            feedback = ft.Text("", size=12, color=palette["error"], visible=False)

            def save(_: object) -> None:
                feedback.value = ""
                feedback.visible = False
                try:
                    controller.atualizar_estado_apurado(
                        apurado.inscricao_id,
                        apurado.prova_destino_id,
                        state_field.value or "",
                    )
                except ValueError as exc:
                    show_temporary_feedback(page, feedback, str(exc))
                    page.update()
                    return
                except ConnectionError:
                    logger.exception("Could not update qualifier status")
                    show_temporary_feedback(
                        page,
                        feedback,
                        "Não foi possível atualizar o estado.",
                    )
                    page.update()
                    return
                page.pop_dialog()
                refresh()

            _show_form(
                page,
                "Atualizar estado do apurado",
                [
                    ft.Text(
                        f"{apurado.nome_aluno} · "
                        f"{format_numeroprocesso(apurado.numeroprocesso)}",
                        size=14,
                        color=palette["text"],
                    ),
                    ft.Text(
                        f"{apurado.prova_destino} · {apurado.escalao}",
                        size=12,
                        color=palette["muted"],
                    ),
                    state_field,
                ],
                feedback,
                save,
                width=380,
            )

        def generate_button(refresh: Callable[[], None]) -> list[ft.Control]:
            def open_generate_dialog(_: object) -> None:
                try:
                    provas = provas_controller.listar_provas()
                except ConnectionError:
                    _show_options_error(page, "provas")
                    return
                destination_field = _dropdown(
                    "Prova de destino",
                    [
                        (
                            str(prova.idprova),
                            f"{prova.escola} · {prova.data.strftime('%d/%m/%Y')}",
                        )
                        for prova in provas
                    ],
                    width=380,
                )
                feedback = ft.Text("", size=12, color=palette["error"], visible=False)

                def generate(_: object) -> None:
                    try:
                        destination_id = _parse_int(
                            destination_field.value,
                            "uma prova de destino",
                        )
                        total = controller.gerar_apuramentos(destination_id)
                    except ValueError as exc:
                        show_temporary_feedback(page, feedback, str(exc))
                        page.update()
                        return
                    except ConnectionError:
                        logger.exception("Could not generate qualifiers")
                        show_temporary_feedback(
                            page,
                            feedback,
                            "Não foi possível gerar os apuramentos.",
                        )
                        page.update()
                        return

                    page.pop_dialog()
                    refresh()
                    success_dialog = ft.AlertDialog(
                        modal=True,
                        title="Apuramentos atualizados",
                        content=ft.Text(
                            f"{total} participante(s) elegível(is) na prova de destino."
                        ),
                        actions=[
                            ft.TextButton(
                                content="Fechar",
                                on_click=lambda _event: page.pop_dialog(),
                            )
                        ],
                    )
                    page.show_dialog(success_dialog)
                    dismiss_temporary_dialog(page, success_dialog)

                page.show_dialog(
                    ft.AlertDialog(
                        modal=True,
                        title="Gerar apuramentos",
                        content=ft.Column(
                            [
                                destination_field,
                                ft.Text(
                                    "Os apurados são calculados pelas classificações "
                                    "e regras da prova. Os estados dos participantes "
                                    "que continuam elegíveis são preservados; quem já "
                                    "não cumprir as regras será removido.",
                                    size=12,
                                    color=palette["muted"],
                                ),
                                feedback,
                            ],
                            tight=True,
                            spacing=10,
                            width=380,
                        ),
                        actions=[
                            ft.TextButton(
                                content="Cancelar",
                                on_click=lambda _event: page.pop_dialog(),
                            ),
                            ft.FilledButton(
                                content="Gerar",
                                on_click=generate,
                            ),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                    )
                )

            return [
                ft.OutlinedButton(
                    content="Gerar apuramentos",
                    on_click=open_generate_dialog,
                )
            ]

        return _build_management_table(
            page,
            palette,
            panel_builder,
            ["Aluno", "Prova de destino", "Origem", "Escalão", "Posição", "Estado"],
            controller.listar_apurados,
            lambda item: (item.inscricao_id, item.prova_destino_id),
            lambda item: [
                f"{item.nome_aluno} · {format_numeroprocesso(item.numeroprocesso)}",
                item.prova_destino,
                item.prova_origem,
                item.escalao,
                str(item.posicao),
                dict(states).get(item.estado, item.estado),
            ],
            open_form,
            None,
            "apurado",
            "apurados",
            "Ainda não existem apuramentos. Configure as regras e gere-os.",
            "",
            allow_add=False,
            extra_actions=generate_button,
            read_only=read_only,
        )

    def select_tab(key: str, update_page: bool = True) -> None:
        nonlocal selected_tab
        selected_tab = key
        for tab_key, label in tab_titles.items():
            label.color = palette["text"] if tab_key == key else palette["muted"]
            label.weight = (
                ft.FontWeight.W_600 if tab_key == key else ft.FontWeight.NORMAL
            )
            tabs[tab_key].style = ft.ButtonStyle(
                color=label.color,
                bgcolor=ft.Colors.TRANSPARENT,
                side=ft.BorderSide(
                    1,
                    palette["primary"] if tab_key == key else palette["border"],
                ),
                shape=ft.RoundedRectangleBorder(radius=0),
            )
        table_builder = {
            "escaloes": build_escaloes_table,
            "rules": build_rules_table,
            "qualified": build_qualified_table,
        }[key]
        tab_content.content = table_builder()
        if update_page:
            page.update()

    for key, button in tabs.items():
        button.on_click = lambda _event, selected=key: select_tab(selected)
    select_tab(selected_tab, update_page=False)
    return ft.Column(
        [
            ft.Row(list(tabs.values()), spacing=8, wrap=True),
            tab_content,
        ],
        spacing=12,
        expand=True,
    )
