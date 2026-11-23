"""Student and class management interface."""

import logging
import unicodedata
from collections.abc import Callable
from datetime import date

import flet as ft

from Controllers.alunos_turmas_controller import AlunosTurmasController
from Model.alunos_turmas import Aluno, Turma
from View.date_time_fields import add_date_time_pickers
from View.formatters import format_numeroprocesso


logger = logging.getLogger(__name__)


def _alphabetical_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def build_alunos_turmas_view(
    page: ft.Page,
    controller: AlunosTurmasController,
    palette: dict[str, str],
    panel_builder: Callable[..., ft.Container],
    read_only: bool = False,
) -> ft.Control:
    classes: list[Turma] = []
    selection_mode = False
    active_view = "students"
    selected_student_ids: set[int] = set()
    selected_class_ids: set[int] = set()
    students_list = ft.Column(spacing=8, tight=True)
    classes_list = ft.Column(spacing=8, tight=True)
    status_text = ft.Text("", size=13, color=palette["error"], visible=False)
    empty_students_text = ft.Text(
        "Não foram encontrados alunos.",
        size=13,
        color=palette["muted"],
        visible=False,
    )
    empty_classes_text = ft.Text(
        "Ainda não existem turmas.",
        size=13,
        color=palette["muted"],
        visible=False,
    )
    search_field = ft.TextField(
        label="Pesquisar por nome ou número",
        width=310,
        on_submit=lambda _event: refresh_students(),
    )
    class_filter = ft.Dropdown(
        label="Turma",
        width=210,
        options=[ft.DropdownOption(key="", text="Todas as turmas")],
        value="",
        on_select=lambda _event: refresh_students(),
    )
    sort_dropdown = ft.Dropdown(
        label="Ordenar",
        width=170,
        value="asc",
        options=[
            ft.DropdownOption(key="asc", text="A–Z"),
            ft.DropdownOption(key="desc", text="Z–A"),
        ],
        on_select=lambda _event: refresh_active_list(),
    )
    students_panel = panel_builder(
        ft.Column(
            [
                students_list,
                empty_students_text,
            ],
            spacing=14,
            tight=True,
        ),
        padding=18,
    )
    classes_panel = panel_builder(
        ft.Column(
            [
                classes_list,
                empty_classes_text,
            ],
            spacing=14,
            tight=True,
        ),
        padding=18,
    )
    classes_panel.visible = False
    filters_row = ft.Row(
        [search_field, class_filter, sort_dropdown],
        spacing=12,
        wrap=True,
    )

    def show_error(message: str) -> None:
        status_text.value = message
        status_text.visible = True

    def clear_error() -> None:
        status_text.value = ""
        status_text.visible = False

    def refresh_classes() -> None:
        nonlocal classes
        try:
            classes = controller.listar_turmas()
            class_filter.options = [
                ft.DropdownOption(key="", text="Todas as turmas"),
                *[
                    ft.DropdownOption(
                        key=str(turma.id),
                        text=turma.designacao,
                    )
                    for turma in classes
                ],
            ]
            selected_class = class_filter.value
            if selected_class and not any(
                str(turma.id) == selected_class for turma in classes
            ):
                class_filter.value = ""
        except ConnectionError:
            logger.exception("Could not load classes")
            show_error("Não foi possível carregar as turmas.")
            classes = []
            class_filter.options = [
                ft.DropdownOption(key="", text="Todas as turmas")
            ]
            class_filter.value = ""

        classes.sort(
            key=lambda turma: (
                turma.ano_escolar,
                _alphabetical_key(turma.letra),
            ),
            reverse=sort_dropdown.value == "desc",
        )
        classes_list.controls = [_class_row(turma) for turma in classes]
        empty_classes_text.visible = not classes

    def refresh_students(
        clear_status: bool = True,
        update_page: bool = True,
    ) -> None:
        if clear_status:
            clear_error()
        class_id = int(class_filter.value) if class_filter.value else None
        try:
            students = controller.listar_alunos(
                search_field.value or "",
                class_id,
            )
            students.sort(
                key=lambda student: _alphabetical_key(student.nome),
                reverse=sort_dropdown.value == "desc",
            )
            students_list.controls = [_student_row(student) for student in students]
            empty_students_text.visible = not students
        except ConnectionError:
            logger.exception("Could not load students")
            students_list.controls = []
            empty_students_text.visible = False
            show_error("Não foi possível carregar os alunos.")
        if update_page:
            page.update()

    def load_records() -> None:
        clear_error()
        refresh_classes()
        refresh_students(clear_status=False, update_page=False)

    def selected_count() -> int:
        return (
            len(selected_student_ids)
            if active_view == "students"
            else len(selected_class_ids)
        )

    def update_selection_controls() -> None:
        add_button.visible = not read_only and not selection_mode
        delete_button.visible = not read_only
        cancel_selection_button.visible = not read_only and selection_mode
        delete_button.disabled = selection_mode and selected_count() == 0
        delete_button.tooltip = (
            "Eliminar selecionados"
            if selection_mode
            else "Selecionar para eliminar"
        )
        search_field.disabled = selection_mode
        class_filter.disabled = selection_mode
        sort_dropdown.disabled = selection_mode

    def refresh_active_list(update_page: bool = True) -> None:
        clear_error()
        if active_view == "students":
            refresh_students(clear_status=False, update_page=update_page)
        else:
            refresh_classes()
            if update_page:
                page.update()

    def toggle_student_selection(
        event: ft.Event[ft.Checkbox],
        student_id: int,
    ) -> None:
        if event.control.value:
            selected_student_ids.add(student_id)
        else:
            selected_student_ids.discard(student_id)
        update_selection_controls()
        page.update()

    def toggle_class_selection(
        event: ft.Event[ft.Checkbox],
        class_id: int,
    ) -> None:
        if event.control.value:
            selected_class_ids.add(class_id)
        else:
            selected_class_ids.discard(class_id)
        update_selection_controls()
        page.update()

    def begin_selection_mode() -> None:
        nonlocal selection_mode
        selection_mode = True
        selected_student_ids.clear()
        selected_class_ids.clear()
        update_selection_controls()
        refresh_active_list(update_page=False)
        page.update()

    def cancel_selection_mode() -> None:
        nonlocal selection_mode
        selection_mode = False
        selected_student_ids.clear()
        selected_class_ids.clear()
        update_selection_controls()
        refresh_active_list(update_page=False)
        page.update()

    def _student_row(student: Aluno) -> ft.Container:
        action: ft.Control
        if read_only:
            action = ft.Container(width=32)
        elif selection_mode:
            action = ft.Checkbox(
                value=student.numeroprocesso in selected_student_ids,
                overlay_color=ft.Colors.TRANSPARENT,
                on_change=lambda event, item=student.numeroprocesso: (
                    toggle_student_selection(event, item)
                ),
            )
        else:
            action = ft.IconButton(
                icon=ft.Icons.EDIT_OUTLINED,
                tooltip="Editar aluno",
                on_click=lambda _event, item=student: open_student_form(item),
            )

        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                student.nome,
                                size=15,
                                weight=ft.FontWeight.W_600,
                                color=palette["text"],
                            ),
                            ft.Text(
                                f"N.º {format_numeroprocesso(student.numeroprocesso)} · "
                                f"{'Feminino' if student.sexo == 'F' else 'Masculino'}",
                                size=12,
                                color=palette["muted"],
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Column(
                        [
                            ft.Text(student.turma, size=13, color=palette["text"]),
                            ft.Text(
                                student.datanasc.strftime("%d/%m/%Y"),
                                size=12,
                                color=palette["muted"],
                            ),
                        ],
                        spacing=4,
                        width=135,
                    ),
                    action,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            padding=12,
            bgcolor=palette["surface"],
            border=ft.Border.all(1, palette["border"]),
        )

    def _class_row(turma: Turma) -> ft.Container:
        action: ft.Control
        if read_only:
            action = ft.Container(width=32)
        elif selection_mode:
            action = ft.Checkbox(
                value=turma.id in selected_class_ids,
                overlay_color=ft.Colors.TRANSPARENT,
                on_change=lambda event, item=turma.id: toggle_class_selection(
                    event,
                    item,
                ),
            )
        else:
            action = ft.IconButton(
                icon=ft.Icons.EDIT_OUTLINED,
                tooltip="Editar turma",
                on_click=lambda _event, item=turma: open_class_form(item),
            )
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                turma.designacao,
                                size=15,
                                weight=ft.FontWeight.W_600,
                                color=palette["text"],
                            ),
                            ft.Text(
                                f"{turma.total_alunos} alunos",
                                size=12,
                                color=palette["muted"],
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    action,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor=palette["surface"],
            border=ft.Border.all(1, palette["border"]),
        )

    def open_student_form(student: Aluno | None = None) -> None:
        process_number = ft.TextField(
            label="N.º de processo",
            value=format_numeroprocesso(student.numeroprocesso) if student else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=420,
            read_only=student is not None,
            autofocus=student is None,
        )
        name = ft.TextField(
            label="Nome completo",
            value=student.nome if student else "",
            width=420,
        )
        birth_date = ft.TextField(
            label="Data de nascimento",
            hint_text="AAAA-MM-DD",
            value=student.datanasc.isoformat() if student else "",
            width=420,
        )
        add_date_time_pickers(
            page,
            birth_date,
            include_time=False,
        )
        sex = ft.Dropdown(
            label="Sexo",
            value=student.sexo if student else None,
            options=[
                ft.DropdownOption(key="F", text="Feminino"),
                ft.DropdownOption(key="M", text="Masculino"),
            ],
            width=420,
        )
        student_class = ft.Dropdown(
            label="Turma",
            value=str(student.turma_id) if student and student.turma_id else "",
            options=[
                ft.DropdownOption(key="", text="Sem turma"),
                *[
                    ft.DropdownOption(
                        key=str(turma.id),
                        text=turma.designacao,
                    )
                    for turma in classes
                ],
            ],
            width=420,
        )
        feedback = ft.Text("", size=12, color=palette["error"], visible=False)

        def save_student(_event: object) -> None:
            try:
                number = int(process_number.value or "")
                parsed_birth_date = date.fromisoformat(birth_date.value or "")
                turma_id = int(student_class.value) if student_class.value else None
                values = (
                    number,
                    name.value or "",
                    parsed_birth_date,
                    sex.value or "",
                    turma_id,
                )
                if student is None:
                    controller.criar_aluno(*values)
                else:
                    controller.atualizar_aluno(*values)
            except ValueError as exc:
                feedback.value = str(exc) or "Verifique os dados introduzidos."
                feedback.visible = True
                page.update()
                return
            except ConnectionError:
                logger.exception("Could not save student")
                feedback.value = (
                    "Não foi possível guardar. Verifique os dados e tente novamente."
                )
                feedback.visible = True
                page.update()
                return

            page.pop_dialog()
            load_records()
            page.update()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Editar aluno" if student else "Adicionar aluno",
                content=ft.Column(
                    [
                        process_number,
                        name,
                        birth_date,
                        sex,
                        student_class,
                        feedback,
                    ],
                    tight=True,
                    spacing=10,
                    width=420,
                ),
                content_padding=ft.Padding.symmetric(
                    horizontal=20,
                    vertical=12,
                ),
                actions=[
                    ft.TextButton(
                        content="Cancelar",
                        on_click=lambda _event: page.pop_dialog(),
                    ),
                    ft.FilledButton(
                        content="Guardar",
                        on_click=save_student,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def open_class_form(turma: Turma | None = None) -> None:
        school_year = ft.TextField(
            label="Ano escolar",
            value=str(turma.ano_escolar) if turma else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=turma is None,
        )
        class_letter = ft.TextField(
            label="Letra",
            value=turma.letra if turma else "",
            capitalization=ft.TextCapitalization.CHARACTERS,
        )
        feedback = ft.Text("", size=12, color=palette["error"], visible=False)

        def save_class(_event: object) -> None:
            try:
                year = int(school_year.value or "")
                letter = class_letter.value or ""
                if turma is None:
                    controller.criar_turma(year, letter)
                else:
                    controller.atualizar_turma(turma.id, year, letter)
            except ValueError as exc:
                feedback.value = str(exc) or "Verifique os dados introduzidos."
                feedback.visible = True
                page.update()
                return
            except ConnectionError:
                logger.exception("Could not save class")
                feedback.value = (
                    "Não foi possível guardar. Verifique se a turma já existe."
                )
                feedback.visible = True
                page.update()
                return

            page.pop_dialog()
            load_records()
            page.update()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Editar turma" if turma else "Adicionar turma",
                content=ft.Column(
                    [school_year, class_letter, feedback],
                    tight=True,
                    spacing=12,
                    width=340,
                ),
                actions=[
                    ft.TextButton(
                        content="Cancelar",
                        on_click=lambda _event: page.pop_dialog(),
                    ),
                    ft.FilledButton(
                        content="Guardar",
                        on_click=save_class,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def open_delete_confirmation() -> None:
        count = selected_count()
        is_student_view = active_view == "students"
        noun = (
            ("aluno" if count == 1 else "alunos")
            if is_student_view
            else ("turma" if count == 1 else "turmas")
        )
        warning = (
            "As inscrições e os dados associados também serão apagados."
            if is_student_view
            else "Os alunos continuarão registados, mas ficarão sem turma."
        )
        feedback = ft.Text("", size=12, color=palette["error"], visible=False)

        def confirm_delete(_event: object) -> None:
            nonlocal selection_mode
            try:
                if is_student_view:
                    controller.eliminar_alunos(sorted(selected_student_ids))
                else:
                    controller.eliminar_turmas(sorted(selected_class_ids))
            except ConnectionError:
                logger.exception("Could not delete selected records")
                feedback.value = "Não foi possível eliminar os registos."
                feedback.visible = True
                page.update()
                return

            page.pop_dialog()
            selection_mode = False
            selected_student_ids.clear()
            selected_class_ids.clear()
            update_selection_controls()
            load_records()
            page.update()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Confirmar eliminação",
                content=ft.Column(
                    [
                        ft.Text(f"Deseja apagar {count} {noun}?", size=15),
                        ft.Text(warning, size=12, color=palette["muted"]),
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

    def handle_delete_click(_event: object) -> None:
        if not selection_mode:
            begin_selection_mode()
        elif selected_count():
            open_delete_confirmation()

    add_button = ft.IconButton(
        icon=ft.Icons.ADD,
        tooltip="Adicionar aluno",
        style=ft.ButtonStyle(
            overlay_color=ft.Colors.TRANSPARENT,
        ),
        splash_color=ft.Colors.TRANSPARENT,
    )
    delete_button = ft.IconButton(
        icon=ft.Icons.DELETE_OUTLINE,
        tooltip="Selecionar para eliminar",
        on_click=handle_delete_click,
        style=ft.ButtonStyle(
            overlay_color=ft.Colors.TRANSPARENT,
        ),
        splash_color=ft.Colors.TRANSPARENT,
    )
    cancel_selection_button = ft.IconButton(
        icon=ft.Icons.CLOSE,
        tooltip="Cancelar seleção",
        visible=False,
        on_click=lambda _event: cancel_selection_mode(),
        style=ft.ButtonStyle(
            overlay_color=ft.Colors.TRANSPARENT,
        ),
        splash_color=ft.Colors.TRANSPARENT,
    )
    students_tab_label = ft.Text("Alunos", color=palette["text"])
    classes_tab_label = ft.Text("Turmas", color=palette["muted"])
    students_tab = ft.OutlinedButton(content=students_tab_label)
    classes_tab = ft.OutlinedButton(content=classes_tab_label)

    def select_tab(show_classes: bool, update_page: bool = True) -> None:
        nonlocal active_view, selection_mode
        active_view = "classes" if show_classes else "students"
        selection_mode = False
        selected_student_ids.clear()
        selected_class_ids.clear()
        students_panel.visible = not show_classes
        classes_panel.visible = show_classes
        search_field.visible = not show_classes
        class_filter.visible = not show_classes
        add_button.tooltip = "Adicionar turma" if show_classes else "Adicionar aluno"
        if show_classes:
            add_button.on_click = lambda _event: open_class_form()
        else:
            add_button.on_click = lambda _event: open_student_form()
        students_tab_label.color = (
            palette["muted"] if show_classes else palette["text"]
        )
        students_tab_label.weight = (
            ft.FontWeight.NORMAL if show_classes else ft.FontWeight.W_600
        )
        classes_tab_label.color = (
            palette["text"] if show_classes else palette["muted"]
        )
        classes_tab_label.weight = (
            ft.FontWeight.W_600 if show_classes else ft.FontWeight.NORMAL
        )
        update_selection_controls()
        if update_page:
            refresh_active_list(update_page=False)
        if update_page:
            page.update()

    students_tab.on_click = lambda _event: select_tab(False)
    classes_tab.on_click = lambda _event: select_tab(True)

    content = ft.Column(
        [
            status_text,
            ft.Row(
                [
                    ft.Row([students_tab, classes_tab], spacing=8),
                    ft.Row(
                        [
                            add_button,
                            delete_button,
                            cancel_selection_button,
                        ],
                        spacing=0,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=8,
            ),
            filters_row,
            students_panel,
            classes_panel,
        ],
        spacing=12,
        tight=True,
    )
    select_tab(False, update_page=False)
    load_records()
    return content
