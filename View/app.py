"""Flet interface for the Cortamato school athletics app."""

import asyncio
import logging
from datetime import date, time, timedelta
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import flet as ft
import flet_video as ftv
from PIL import Image, ImageOps

from Controllers.alunos_turmas_controller import AlunosTurmasController
from Controllers.auth_controller import AuthController
from Controllers.competition_records_controller import (
    CompetitionRecordsController,
)
from Controllers.demo_controllers import (
    DemoAlunosTurmasController,
    DemoCompetitionRecordsController,
    DemoData,
    DemoProvasController,
)
from Controllers.provas_controller import ProvasController
from Model.auth import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, is_valid_email
from Model.provas import Prova
from View.alunos_turmas_view import build_alunos_turmas_view
from View.competition_records_view import (
    build_categories_view,
    build_chegadas_view,
    build_classificacoes_view,
    build_dorsais_view,
    build_inscricoes_view,
)
from View.date_time_fields import add_date_time_pickers
from View.data_tools_view import build_csv_tools_view, build_qr_reader_view
from View.feedback import dismiss_temporary_dialog, show_temporary_feedback

from View.image_crop import create_square_crop_canvas, minimum_crop_zoom


logger = logging.getLogger(__name__)

VIEW_DIRECTORY = Path(__file__).resolve().parent
PROFILE_PHOTOS_DIRECTORY = Path.home() / ".cortamato" / "profile_photos"
LOGIN_VIDEO_PATH = VIEW_DIRECTORY / "cortandoMato.mp4"
LOGIN_LOGO_PATH = VIEW_DIRECTORY / "AEPBS_Horizontal_Branco.png"


BACKGROUND = "#F7F8F9"
SURFACE = "#FCFCFB"
TEXT = "#252A2E"
MUTED = "#727B82"
PRIMARY = "#536B7B"
SIDEBAR = "#EFF1F3"

LIGHT_PALETTE = {
    "background": BACKGROUND,
    "surface": SURFACE,
    "text": TEXT,
    "muted": MUTED,
    "primary": PRIMARY,
    "sidebar": SIDEBAR,
    "selected": "#E3E9ED",
    "metric_label": "#59636B",
    "border": "#E1E5E8",
    "divider": "#DDE2E5",
    "table_line": "#E5E8EA",
    "error": "#B42318",
}
DARK_PALETTE = {
    "background": "#121416",
    "surface": "#1B1F22",
    "text": "#E6E8EA",
    "muted": "#A0A8AE",
    "primary": "#A7BAC7",
    "sidebar": "#171A1D",
    "selected": "#29343B",
    "metric_label": "#C2C8CD",
    "border": "#343B40",
    "divider": "#343B40",
    "table_line": "#30373B",
    "error": "#F2A29A",
}


def format_hora(value: time | timedelta) -> str:
    if isinstance(value, time):
        return value.strftime("%H:%M")

    total_minutes = int(value.total_seconds() // 60)
    sign = "-" if total_minutes < 0 else ""
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def nav_item(
    label: str,
    selected: bool = False,
    on_click: Callable[..., None] | None = None,
) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            label,
            size=15,
            weight=ft.FontWeight.W_600 if selected else ft.FontWeight.NORMAL,
            color=TEXT if selected else MUTED,
        ),
        padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        bgcolor=LIGHT_PALETTE["selected"] if selected else None,
        border_radius=8,
        on_click=on_click,
    )


def panel(
    content: ft.Control,
    padding: int = 20,
    width: int | None = None,
    expand: bool = False,
    bgcolor: str = SURFACE,
) -> ft.Container:
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=bgcolor,
        border=ft.Border.all(1, "#E9E8E2"),
        border_radius=12,
        width=width,
        expand=expand,
    )


def create_app(page: ft.Page) -> None:
    page.title = "Cortamato"
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("pt", "PT")],
        current_locale=ft.Locale("pt", "PT"),
    )
    page.bgcolor = BACKGROUND
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme_animation_style = ft.AnimationStyle.no_animation()

    def build_theme() -> ft.Theme:
        square_button_style = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=0),
        )
        return ft.Theme(
            color_scheme_seed=PRIMARY,
            splash_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=ft.Colors.TRANSPARENT,
            focus_color=ft.Colors.TRANSPARENT,
            page_transitions=ft.PageTransitionsTheme(
                android=ft.PageTransitionTheme.NONE,
                ios=ft.PageTransitionTheme.NONE,
                linux=ft.PageTransitionTheme.NONE,
                macos=ft.PageTransitionTheme.NONE,
                windows=ft.PageTransitionTheme.NONE,
            ),
            button_theme=ft.ButtonTheme(style=square_button_style),
            outlined_button_theme=ft.OutlinedButtonTheme(style=square_button_style),
            text_button_theme=ft.TextButtonTheme(style=square_button_style),
            filled_button_theme=ft.FilledButtonTheme(style=square_button_style),
            icon_button_theme=ft.IconButtonTheme(style=square_button_style),
        )

    page.theme = build_theme()
    page.dark_theme = build_theme()
    page.window.width = 1440
    page.window.height = 920
    page.window.resizable = True
    profile_photo_picker = ft.FilePicker()
    page.services.append(profile_photo_picker)
    data_tools_file_picker = ft.FilePicker()
    page.services.append(data_tools_file_picker)

    sections = [
        ("overview", "Dashboard"),
        ("provas", "Provas"),
        ("students", "Alunos e turmas"),
        ("registrations", "Inscrições"),
        ("bibs", "Dorsais"),
        ("arrivals", "Chegadas"),
        ("results", "Classificações"),
        ("categories", "Escalões e apuramentos"),
        ("qr-reader", "Leitor QR code"),
        ("csv-tools", "Importar e exportar"),
        ("settings", "Definições"),
    ]

    section_descriptions: dict[str, str] = {}

    section_content = ft.Column(expand=True, spacing=10, scroll=ft.ScrollMode.AUTO)
    page_title = ft.Text(
        "",
        size=25,
        weight=ft.FontWeight.W_600,
        color=TEXT,
        expand=True,
    )
    navigation_items: dict[str, list[ft.Container]] = {}
    navigation_open = True
    profile_menu_open = False
    login_page_active = False
    current_user_id: int | None = None
    current_user_email: str | None = None
    current_user_photo: str | None = None
    demo_mode = False
    demo_notice = ft.Text(
        "DADOS FICTÍCIOS",
        size=12,
        weight=ft.FontWeight.W_700,
        color=LIGHT_PALETTE["error"],
        text_align=ft.TextAlign.CENTER,
        opacity=1,
        visible=False,
    )
    demo_notice_container = ft.Container(
        content=demo_notice,
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.symmetric(horizontal=4, vertical=8),
        visible=False,
    )

    def create_menu_button(tooltip: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(width=18, height=2, bgcolor=TEXT, border_radius=1),
                    ft.Container(width=18, height=2, bgcolor=TEXT, border_radius=1),
                    ft.Container(width=18, height=2, bgcolor=TEXT, border_radius=1),
                ],
                spacing=4,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=44,
            height=44,
            alignment=ft.Alignment.CENTER,
            border_radius=8,
            tooltip=tooltip,
            on_click=None,
        )

    sidebar_menu_button = create_menu_button("Fechar menu")
    content_menu_button = create_menu_button("Abrir menu")
    content_menu_button.visible = False

    def create_navigation_item(key: str, label: str) -> ft.Container:
        item = nav_item(
            label,
            on_click=lambda _event, selected_key=key: show_section(selected_key),
        )
        navigation_items.setdefault(key, []).append(item)
        return item

    mobile_navigation = ft.Column(
        [
            create_navigation_item(key, label)
            for key, label in sections
        ],
        visible=False,
        spacing=4,
    )

    sidebar_contents = ft.Column(
        [
            *[
                create_navigation_item(key, label)
                for key, label in sections[:-1]
            ],
            ft.Container(expand=True),
            demo_notice_container,
            ft.Divider(color="#E1E0D9"),
            *[
                create_navigation_item(key, label)
                for key, label in sections[-1:]
            ],
        ],
        spacing=8,
        expand=True,
    )
    profile_name = ft.Text("Administrador", size=12, color=TEXT)
    profile_avatar_initial = ft.Text("A", size=12, color="#FFFFFF")
    profile_sidebar_avatar = ft.CircleAvatar(
        content=profile_avatar_initial,
        bgcolor=PRIMARY,
        radius=16,
    )
    profile_button = ft.Container(
        content=ft.Row(
            [
                profile_sidebar_avatar,
                profile_name,
            ],
            spacing=10,
        ),
        width=220,
        height=48,
        alignment=ft.Alignment.CENTER_LEFT,
        border_radius=8,
    )
    collapsed_sidebar_spacer = ft.Container(expand=True, visible=False)

    sidebar = ft.Container(
        content=ft.Column(
            [
                sidebar_menu_button,
                sidebar_contents,
                collapsed_sidebar_spacer,
                profile_button,
            ],
            spacing=8,
            expand=True,
        ),
        width=260,
        padding=20,
        bgcolor=SIDEBAR,
        visible=False,
    )

    content_container = ft.Container(
        content=ft.Row([section_content], expand=True),
        padding=ft.Padding.symmetric(horizontal=32, vertical=28),
        expand=True,
    )

    event_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID", size=13, color=MUTED)),
            ft.DataColumn(ft.Text("Ano letivo", size=13, color=MUTED)),
            ft.DataColumn(ft.Text("Data", size=13, color=MUTED)),
            ft.DataColumn(ft.Text("Horário", size=13, color=MUTED)),
            ft.DataColumn(ft.Text("Concelho", size=13, color=MUTED)),
            ft.DataColumn(ft.Text("Escola", size=13, color=MUTED)),
            ft.DataColumn(ft.Text("", size=13, color=MUTED)),
        ],
        rows=[],
        column_spacing=22,
        horizontal_margin=12,
        heading_row_height=52,
        data_row_min_height=54,
        data_row_max_height=60,
        horizontal_lines=ft.BorderSide(0.5, "#ECEBE5"),
    )
    provas_cache: list[Prova] = []
    selected_prova_ids: set[int] = set()
    prova_selection_mode = False
    compact_table = False
    page_size = 10
    current_page = 0
    empty_provas_text = ft.Text(
        "Ainda não existem provas registadas.",
        size=13,
        color=MUTED,
        visible=False,
    )

    def total_pages() -> int:
        return max(1, (len(provas_cache) + page_size - 1) // page_size)

    def prova_row_action(prova: Prova) -> ft.Control:
        if demo_mode:
            return ft.Container(width=24)
        if prova_selection_mode:
            return ft.Checkbox(
                value=prova.idprova in selected_prova_ids,
                overlay_color=ft.Colors.TRANSPARENT,
                on_change=lambda event, item=prova.idprova: toggle_prova_selection(
                    event,
                    item,
                ),
            )
        return ft.IconButton(
            icon=ft.Icons.EDIT_OUTLINED,
            tooltip="Editar prova",
            on_click=lambda _event, item=prova: open_prova_form(item),
        )

    def build_table_rows(compact: bool) -> list[ft.DataRow]:
        start = current_page * page_size
        current_provas = provas_cache[start : start + page_size]

        if compact:
            return [
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(prova.data.strftime("%d/%m/%Y"), size=13, color=TEXT)
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"{format_hora(prova.horainicio)}–{format_hora(prova.horafinal)}",
                                size=13,
                                color=TEXT,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"{prova.escola} · {prova.concelho}",
                                size=13,
                                color=TEXT,
                            )
                        ),
                        ft.DataCell(prova_row_action(prova)),
                    ]
                )
                for prova in current_provas
            ]

        return [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(prova.idprova), size=14, color=TEXT)),
                    ft.DataCell(ft.Text(prova.anolectivo, size=14, color=TEXT)),
                    ft.DataCell(
                        ft.Text(prova.data.strftime("%d/%m/%Y"), size=14, color=TEXT)
                    ),
                    ft.DataCell(
                        ft.Text(
                            f"{format_hora(prova.horainicio)}–{format_hora(prova.horafinal)}",
                            size=14,
                            color=TEXT,
                        )
                    ),
                    ft.DataCell(ft.Text(prova.concelho, size=14, color=TEXT)),
                    ft.DataCell(ft.Text(prova.escola, size=14, color=TEXT)),
                    ft.DataCell(prova_row_action(prova)),
                ]
            )
            for prova in current_provas
        ]

    def set_table_layout(compact: bool) -> None:
        nonlocal compact_table
        compact_table = compact
        event_table.column_spacing = 18 if compact else 24
        if compact:
            event_table.columns = [
                ft.DataColumn(ft.Text("Data", size=13, color=MUTED)),
                ft.DataColumn(ft.Text("Horário", size=13, color=MUTED)),
                ft.DataColumn(ft.Text("Escola / concelho", size=13, color=MUTED)),
                ft.DataColumn(ft.Text("", size=13, color=MUTED)),
            ]
        else:
            event_table.columns = [
                ft.DataColumn(ft.Text("ID", size=13, color=MUTED)),
                ft.DataColumn(ft.Text("Ano letivo", size=13, color=MUTED)),
                ft.DataColumn(ft.Text("Data", size=13, color=MUTED)),
                ft.DataColumn(ft.Text("Horário", size=13, color=MUTED)),
                ft.DataColumn(ft.Text("Concelho", size=13, color=MUTED)),
                ft.DataColumn(ft.Text("Escola", size=13, color=MUTED)),
                ft.DataColumn(ft.Text("", size=13, color=MUTED)),
            ]
        event_table.rows = build_table_rows(compact)

    result_message = ft.Text("", size=12, color=MUTED, visible=False)
    refresh_button = ft.IconButton(
        icon=ft.Icons.REFRESH,
        tooltip="Atualizar",
    )
    add_prova_button = ft.IconButton(
        icon=ft.Icons.ADD,
        tooltip="Adicionar prova",
    )
    delete_provas_button = ft.IconButton(
        icon=ft.Icons.DELETE_OUTLINE,
        tooltip="Selecionar para eliminar",
    )
    cancel_prova_selection_button = ft.IconButton(
        icon=ft.Icons.CLOSE,
        tooltip="Cancelar seleção",
        visible=False,
    )
    page_indicator = ft.Text("", size=13, color=MUTED)
    light_theme_button = ft.OutlinedButton(
        content="Claro",
        width=120,
    )
    dark_theme_button = ft.OutlinedButton(
        content="Escuro",
        width=120,
    )
    change_email_button = ft.OutlinedButton(
        content="Alterar email",
        width=220,
    )
    change_password_button = ft.OutlinedButton(
        content="Alterar palavra-passe",
        width=220,
    )
    profile_settings_initial = ft.Text(
        "A",
        size=24,
        color=ft.Colors.WHITE,
        text_align=ft.TextAlign.CENTER,
    )
    profile_settings_avatar = ft.CircleAvatar(
        content=profile_settings_initial,
        bgcolor=PRIMARY,
        radius=38,
    )
    profile_photo_edit_button = ft.IconButton(
        icon=ft.Icons.EDIT_OUTLINED,
        icon_color=ft.Colors.WHITE,
        tooltip="Editar foto de perfil",
        on_click=None,
    )
    profile_photo_edit_overlay = ft.Container(
        content=profile_photo_edit_button,
        width=76,
        height=76,
        alignment=ft.Alignment.CENTER,
        bgcolor="#99000000",
        border_radius=38,
        visible=False,
    )
    profile_settings_avatar_hover = ft.Container(
        content=ft.Stack(
            [
                profile_settings_avatar,
                profile_photo_edit_overlay,
            ],
            width=76,
            height=76,
        ),
        width=76,
        height=76,
        on_hover=None,
    )
    profile_settings_name = ft.Text(
        "Administrador",
        size=16,
        weight=ft.FontWeight.W_600,
        color=TEXT,
    )
    edit_profile_name_button = ft.OutlinedButton(
        content="Editar",
        width=100,
    )
    profile_edit_feedback = ft.Text(
        "",
        size=12,
        color=MUTED,
        visible=False,
    )
    logout_label = ft.Text(
        "Terminar sessão",
        size=13,
        color=LIGHT_PALETTE["error"],
    )
    logout_button = ft.Container(
        content=logout_label,
        padding=ft.Padding.symmetric(horizontal=8, vertical=8),
        border_radius=6,
        on_click=None,
    )
    profile_menu_profile_action = ft.Container(
        content=ft.Text("Perfil", size=13, color=TEXT),
        padding=ft.Padding.symmetric(horizontal=8, vertical=8),
        border_radius=6,
        on_click=None,
    )
    dismiss_profile_overlay = ft.Container(
        left=0,
        right=0,
        top=0,
        bottom=0,
        bgcolor=ft.Colors.TRANSPARENT,
        visible=False,
        on_click=None,
    )
    profile_menu = ft.Container(
        content=ft.Column(
            [
                profile_menu_profile_action,
                ft.Divider(height=1, color=LIGHT_PALETTE["divider"]),
                logout_button,
            ],
            spacing=6,
            tight=True,
        ),
        width=174,
        padding=10,
        bgcolor=SURFACE,
        border=ft.Border.all(1, LIGHT_PALETTE["border"]),
        border_radius=8,
        left=90,
        bottom=20,
        visible=False,
    )
    first_page_button = ft.IconButton(
        icon=ft.Icons.FIRST_PAGE,
        tooltip="Primeira página",
    )
    previous_page_button = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT,
        tooltip="Página anterior",
    )
    next_page_button = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT,
        tooltip="Página seguinte",
    )
    last_page_button = ft.IconButton(
        icon=ft.Icons.LAST_PAGE,
        tooltip="Última página",
    )

    def update_pagination() -> None:
        page_count = total_pages()
        page_indicator.value = f"{current_page + 1}/{page_count}"
        first_page_button.disabled = current_page == 0
        previous_page_button.disabled = current_page == 0
        next_page_button.disabled = current_page >= page_count - 1
        last_page_button.disabled = current_page >= page_count - 1

    def update_prova_selection_controls() -> None:
        add_prova_button.visible = not demo_mode and not prova_selection_mode
        delete_provas_button.visible = not demo_mode
        refresh_button.visible = not demo_mode
        cancel_prova_selection_button.visible = (
            not demo_mode and prova_selection_mode
        )
        delete_provas_button.disabled = (
            prova_selection_mode and not selected_prova_ids
        )
        delete_provas_button.tooltip = (
            "Eliminar selecionadas"
            if prova_selection_mode
            else "Selecionar para eliminar"
        )

    def toggle_prova_selection(
        event: ft.Event[ft.Checkbox],
        idprova: int,
    ) -> None:
        if event.control.value:
            selected_prova_ids.add(idprova)
        else:
            selected_prova_ids.discard(idprova)
        update_prova_selection_controls()
        page.update()

    def begin_prova_selection() -> None:
        nonlocal prova_selection_mode
        prova_selection_mode = True
        selected_prova_ids.clear()
        update_prova_selection_controls()
        set_table_layout(compact_table)
        page.update()

    def cancel_prova_selection() -> None:
        nonlocal prova_selection_mode
        prova_selection_mode = False
        selected_prova_ids.clear()
        update_prova_selection_controls()
        set_table_layout(compact_table)
        page.update()

    def go_to_page(page_number: int) -> None:
        nonlocal current_page
        current_page = max(0, min(page_number, total_pages() - 1))
        set_table_layout(compact_table)
        update_pagination()
        apply_theme_colors(dark_theme_active, update_page=False)
        page.update()

    first_page_button.on_click = lambda _event: go_to_page(0)
    previous_page_button.on_click = lambda _event: go_to_page(current_page - 1)
    next_page_button.on_click = lambda _event: go_to_page(current_page + 1)
    last_page_button.on_click = lambda _event: go_to_page(total_pages() - 1)

    provas_controller = ProvasController()
    alunos_turmas_controller = AlunosTurmasController()
    competition_records_controller = CompetitionRecordsController()
    demo_data = DemoData()
    demo_provas_controller = DemoProvasController(demo_data)
    demo_alunos_turmas_controller = DemoAlunosTurmasController(demo_data)
    demo_competition_records_controller = DemoCompetitionRecordsController(demo_data)
    auth_controller = AuthController()

    def current_provas_controller() -> ProvasController | DemoProvasController:
        return demo_provas_controller if demo_mode else provas_controller

    def current_alunos_turmas_controller(
    ) -> AlunosTurmasController | DemoAlunosTurmasController:
        return (
            demo_alunos_turmas_controller
            if demo_mode
            else alunos_turmas_controller
        )

    def current_competition_records_controller(
    ) -> CompetitionRecordsController | DemoCompetitionRecordsController:
        return (
            demo_competition_records_controller
            if demo_mode
            else competition_records_controller
        )

    def load_provas(_: object | None = None) -> None:
        nonlocal provas_cache, current_page
        refresh_button.disabled = True
        page.update()

        try:
            provas_cache = current_provas_controller().listar_provas()
            selected_prova_ids.intersection_update(
                prova.idprova for prova in provas_cache
            )
            current_page = min(current_page, total_pages() - 1)
        except ConnectionError as exc:
            provas_cache = []
            selected_prova_ids.clear()
            current_page = 0
            event_table.rows = []
            empty_provas_text.visible = False
            show_temporary_feedback(
                page,
                result_message,
                f"Erro ao carregar provas: {exc}",
                color="#B42318",
            )
        else:
            set_table_layout(compact_table)
            empty_provas_text.visible = not provas_cache
            result_message.value = ""
            result_message.color = MUTED
            result_message.visible = False
        finally:
            update_pagination()
            update_prova_selection_controls()
            refresh_button.disabled = False
            apply_theme_colors(dark_theme_active, update_page=False)
            page.update()

    refresh_button.on_click = load_provas

    def open_prova_form(prova: Prova | None = None) -> None:
        anolectivo = ft.TextField(
            label="Ano letivo",
            hint_text="2026/2027",
            value=prova.anolectivo if prova else "",
            width=420,
            autofocus=prova is None,
        )
        concelho = ft.TextField(
            label="Concelho",
            value=prova.concelho if prova else "",
            width=420,
        )
        escola = ft.TextField(
            label="Escola",
            value=prova.escola if prova else "",
            width=420,
        )
        data_prova = ft.TextField(
            label="Data",
            hint_text="AAAA-MM-DD",
            value=prova.data.isoformat() if prova else "",
            width=420,
        )
        add_date_time_pickers(
            page,
            data_prova,
            include_time=False,
            minimum_date=date.today(),
        )
        hora_inicio = ft.TextField(
            label="Hora de início",
            hint_text="HH:MM",
            value=format_hora(prova.horainicio) if prova else "",
            width=420,
        )
        add_date_time_pickers(
            page,
            hora_inicio,
            include_date=False,
        )
        hora_final = ft.TextField(
            label="Hora final",
            hint_text="HH:MM",
            value=format_hora(prova.horafinal) if prova else "",
            width=420,
        )
        add_date_time_pickers(
            page,
            hora_final,
            include_date=False,
        )
        feedback = ft.Text("", size=12, color="#B42318", visible=False)

        def save_prova(_event: object) -> None:
            feedback.value = ""
            feedback.visible = False
            try:
                parsed_date = date.fromisoformat(data_prova.value or "")
            except ValueError:
                show_temporary_feedback(
                    page,
                    feedback,
                    "Introduza uma data válida no formato AAAA-MM-DD.",
                )
                page.update()
                return

            try:
                parsed_start = time.fromisoformat(hora_inicio.value or "")
                parsed_end = time.fromisoformat(hora_final.value or "")
            except ValueError:
                show_temporary_feedback(
                    page,
                    feedback,
                    "Introduza horas válidas no formato HH:MM.",
                )
                page.update()
                return

            values = (
                anolectivo.value or "",
                concelho.value or "",
                escola.value or "",
                parsed_date,
                parsed_start,
                parsed_end,
            )
            try:
                if prova is None:
                    current_provas_controller().criar_prova(*values)
                else:
                    current_provas_controller().atualizar_prova(prova.idprova, *values)
            except ValueError as exc:
                show_temporary_feedback(
                    page,
                    feedback,
                    str(exc) or "Verifique os dados introduzidos.",
                )
                page.update()
                return
            except ConnectionError:
                logger.exception("Could not save event")
                show_temporary_feedback(
                    page,
                    feedback,
                    "Não foi possível guardar a prova. "
                    "Verifique os dados e tente novamente.",
                )
                page.update()
                return

            page.pop_dialog()
            load_provas()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Editar prova" if prova else "Adicionar prova",
                content=ft.Column(
                    [
                        anolectivo,
                        concelho,
                        escola,
                        data_prova,
                        hora_inicio,
                        hora_final,
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
                        on_click=save_prova,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def open_delete_provas_confirmation() -> None:
        count = len(selected_prova_ids)
        noun = "prova" if count == 1 else "provas"
        feedback = ft.Text("", size=12, color="#B42318", visible=False)

        def confirm_delete(_event: object) -> None:
            nonlocal prova_selection_mode
            try:
                current_provas_controller().eliminar_provas(sorted(selected_prova_ids))
            except ConnectionError:
                logger.exception("Could not delete selected events")
                show_temporary_feedback(
                    page,
                    feedback,
                    "Não foi possível eliminar as provas selecionadas.",
                )
                page.update()
                return

            page.pop_dialog()
            prova_selection_mode = False
            selected_prova_ids.clear()
            update_prova_selection_controls()
            load_provas()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Confirmar eliminação",
                content=ft.Column(
                    [
                        ft.Text(f"Deseja apagar {count} {noun}?", size=15),
                        ft.Text(
                            "As inscrições e todos os dados associados (dorsais, "
                            "chegadas, escalões, listas de partida, classificações e "
                            "apuramentos) também serão eliminados.",
                            size=12,
                            color=MUTED,
                        ),
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

    def handle_delete_provas_click(_event: object) -> None:
        if not prova_selection_mode:
            begin_prova_selection()
        elif selected_prova_ids:
            open_delete_provas_confirmation()

    add_prova_button.on_click = lambda _event: open_prova_form()
    delete_provas_button.on_click = handle_delete_provas_click
    cancel_prova_selection_button.on_click = (
        lambda _event: cancel_prova_selection()
    )

    dark_theme_active = False

    def theme_button_style(selected: bool, dark: bool) -> ft.ButtonStyle:
        palette = DARK_PALETTE if dark else LIGHT_PALETTE
        return ft.ButtonStyle(
            color=palette["text"],
            bgcolor=palette["selected"] if selected else palette["surface"],
            overlay_color=ft.Colors.TRANSPARENT,
            animation_duration=0,
            side=ft.BorderSide(1, palette["primary"] if selected else palette["border"]),
            shape=ft.RoundedRectangleBorder(radius=0),
        )

    def apply_theme_colors(dark: bool, update_page: bool = True) -> None:
        nonlocal dark_theme_active
        dark_theme_active = dark
        next_palette = DARK_PALETTE if dark else LIGHT_PALETTE
        page.bgcolor = next_palette["background"]
        for menu_button in (sidebar_menu_button, content_menu_button):
            if isinstance(menu_button.content, ft.Column):
                for line in menu_button.content.controls:
                    if isinstance(line, ft.Container):
                        line.bgcolor = next_palette["text"]
        light_theme_button.style = theme_button_style(not dark, dark)
        dark_theme_button.style = theme_button_style(dark, dark)
        change_email_button.style = theme_button_style(False, dark)
        change_password_button.style = theme_button_style(False, dark)
        edit_profile_name_button.style = theme_button_style(False, dark)
        logout_label.color = next_palette["error"]
        visited: set[int] = set()

        def update_control(control: object) -> None:
            if id(control) in visited:
                return
            visited.add(id(control))

            if isinstance(control, ft.Text):
                for palette_key in (
                    "text",
                    "muted",
                    "primary",
                    "error",
                    "metric_label",
                ):
                    if control.color in (
                        LIGHT_PALETTE[palette_key],
                        DARK_PALETTE[palette_key],
                    ):
                        control.color = next_palette[palette_key]
                        break
            elif isinstance(control, ft.Container):
                for palette_key in ("surface", "sidebar", "selected"):
                    if control.bgcolor in (
                        LIGHT_PALETTE[palette_key],
                        DARK_PALETTE[palette_key],
                    ):
                        control.bgcolor = next_palette[palette_key]
                        break
                if control.border is not None:
                    control.border = ft.Border.all(1, next_palette["border"])
            elif isinstance(control, ft.Divider):
                if control.color in (
                    LIGHT_PALETTE["divider"],
                    DARK_PALETTE["divider"],
                ):
                    control.color = next_palette["divider"]
            elif isinstance(control, ft.DataTable):
                if control.bgcolor in (
                    LIGHT_PALETTE["surface"],
                    DARK_PALETTE["surface"],
                ):
                    control.bgcolor = next_palette["surface"]
                control.horizontal_lines = ft.BorderSide(
                    0.5, next_palette["table_line"]
                )

            for attribute in (
                "content",
                "controls",
                "columns",
                "rows",
                "cells",
                "items",
                "label",
            ):
                children = getattr(control, attribute, None)
                if isinstance(children, (list, tuple)):
                    for child in children:
                        update_control(child)
                elif children is not None and not isinstance(
                    children, (str, bytes, int, float, bool)
                ):
                    update_control(children)

        for root_control in page.controls:
            update_control(root_control)
        for items in navigation_items.values():
            for item in items:
                selected = item.bgcolor is not None
                item.bgcolor = next_palette["selected"] if selected else None
                text = item.content
                if isinstance(text, ft.Text):
                    text.color = (
                        next_palette["text"] if selected else next_palette["muted"]
                    )
                    text.weight = (
                        ft.FontWeight.W_600 if selected else ft.FontWeight.NORMAL
                    )
        if update_page:
            page.update()

    def set_theme(dark: bool) -> None:
        page.theme_mode = ft.ThemeMode.DARK if dark else ft.ThemeMode.LIGHT
        apply_theme_colors(dark)

    light_theme_button.on_click = lambda _event: set_theme(False)
    dark_theme_button.on_click = lambda _event: set_theme(True)

    def profile_photo_source(photo_path: str | None) -> str | None:
        if not photo_path:
            return None
        path = Path(photo_path)
        if not path.is_absolute():
            path = PROFILE_PHOTOS_DIRECTORY / path.name
        return str(path) if path.is_file() else None

    def update_profile_display(name: str, photo_path: str | None) -> None:
        initial = name[:1].upper() or "?"
        profile_name.value = name
        profile_settings_name.value = name
        profile_avatar_initial.value = initial
        profile_settings_initial.value = initial
        photo_source = profile_photo_source(photo_path)
        profile_sidebar_avatar.foreground_image_src = photo_source
        profile_settings_avatar.foreground_image_src = photo_source

    def set_profile_feedback(message: str, is_error: bool = False) -> None:
        color = (
            (DARK_PALETTE if dark_theme_active else LIGHT_PALETTE)["error"]
            if is_error
            else (DARK_PALETTE if dark_theme_active else LIGHT_PALETTE)["muted"]
        )
        show_temporary_feedback(
            page,
            profile_edit_feedback,
            message,
            color=color,
        )

    def dismiss_profile_menu(_event: object | None = None) -> None:
        nonlocal profile_menu_open
        profile_menu_open = False
        profile_menu.visible = False
        dismiss_profile_overlay.visible = False
        page.update()

    def open_profile_dialog(_event: object | None = None) -> None:
        dismiss_profile_menu()
        if demo_mode or current_user_id is None:
            return
        palette = DARK_PALETTE if dark_theme_active else LIGHT_PALETTE
        profile_settings_name.color = palette["text"]
        profile_settings_avatar.bgcolor = palette["primary"]
        set_profile_feedback("")
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Perfil",
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                profile_settings_avatar_hover,
                                ft.Row(
                                    [
                                        profile_settings_name,
                                        edit_profile_name_button,
                                    ],
                                    spacing=8,
                                    wrap=True,
                                ),
                            ],
                            spacing=20,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        profile_edit_feedback,
                    ],
                    tight=True,
                    spacing=12,
                    width=420,
                ),
                actions=[
                    ft.TextButton(
                        content="Fechar",
                        on_click=lambda _event: page.pop_dialog(),
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def open_profile_name_dialog() -> None:
        user_id = current_user_id
        if demo_mode or user_id is None:
            return

        name_field = ft.TextField(
            label="Nome",
            value=profile_settings_name.value,
            autofocus=True,
            width=360,
        )
        feedback = ft.Text("", size=12, color="#B42318", visible=False)
        save_button = ft.FilledButton(content="Guardar")

        def save_name(_event: object) -> None:
            name = (name_field.value or "").strip()
            if name == profile_settings_name.value:
                page.pop_dialog()
                return
            save_button.disabled = True
            page.update()
            try:
                updated = auth_controller.update_profile_name(user_id, name)
            except ValueError as exc:
                show_temporary_feedback(page, feedback, str(exc))
                save_button.disabled = False
                page.update()
                return
            except ConnectionError:
                logger.exception("Could not update the account name")
                show_temporary_feedback(
                    page,
                    feedback,
                    "Não foi possível guardar o nome.",
                )
                save_button.disabled = False
                page.update()
                return

            if not updated:
                show_temporary_feedback(
                    page,
                    feedback,
                    "Não foi encontrada uma conta ativa para alterar.",
                )
                save_button.disabled = False
                page.update()
                return

            update_profile_display(name, current_user_photo)
            set_profile_feedback("Nome atualizado.")
            page.pop_dialog()
            page.update()

        save_button.on_click = save_name
        name_field.on_submit = save_name
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Editar nome",
                content=ft.Column([name_field, feedback], tight=True, spacing=10),
                actions=[
                    ft.TextButton(
                        content="Cancelar",
                        on_click=lambda _event: page.pop_dialog(),
                    ),
                    save_button,
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    async def choose_profile_photo(_event: object) -> None:
        user_id = current_user_id
        if demo_mode or user_id is None:
            return

        files = await profile_photo_picker.pick_files(
            dialog_title="Selecionar fotografia de perfil",
            file_type=ft.FilePickerFileType.IMAGE,
            allow_multiple=False,
        )
        if not files:
            return

        selected_file = files[0]
        extension = Path(selected_file.name).suffix.lower()
        if extension not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
            set_profile_feedback(
                "Selecione uma imagem JPG, PNG, WEBP, BMP ou GIF.",
                True,
            )
            page.update()
            return
        if selected_file.size > 5 * 1024 * 1024:
            set_profile_feedback("A imagem deve ter no máximo 5 MB.", True)
            page.update()
            return
        if not selected_file.path:
            set_profile_feedback(
                "Não foi possível aceder ao ficheiro selecionado.",
                True,
            )
            page.update()
            return

        try:
            with Image.open(selected_file.path) as selected_image:
                source_image = ImageOps.exif_transpose(selected_image).convert("RGBA")
        except (OSError, ValueError):
            logger.exception("Could not open the selected profile photo")
            set_profile_feedback("Não foi possível abrir a imagem selecionada.", True)
            page.update()
            return

        image_width, image_height = source_image.size
        if not image_width or not image_height:
            set_profile_feedback("A imagem selecionada não é válida.", True)
            page.update()
            return

        minimum_dimension = min(image_width, image_height)
        crop_canvas = create_square_crop_canvas(source_image)
        crop_canvas_size = crop_canvas.width
        minimum_zoom = minimum_crop_zoom(source_image.size)

=======
        minimum_zoom = minimum_crop_zoom(source_image.size)
>>>>>>> Stashed changes
>>>>>>> 485d34971cc9224dcbdb2c5ec73a08faf8a63ea2
        preview_size = 220
        output_size = 512
        crop_center_x = crop_canvas_size / 2
        crop_center_y = crop_canvas_size / 2
        crop_error = ft.Text("", size=12, color="#B42318", visible=False)
        crop_preview = ft.CircleAvatar(
            radius=preview_size / 2,
            foreground_image_src=b"",
            bgcolor=LIGHT_PALETTE["surface"],
        )
        zoom_slider = ft.Slider(
            min=minimum_zoom,

=======
            min=minimum_zoom,
>>>>>>> Stashed changes
>>>>>>> 485d34971cc9224dcbdb2c5ec73a08faf8a63ea2
            max=3,
            value=minimum_zoom,
            divisions=20,
            label="{value}x",
            active_color=PRIMARY,
        )

        def crop_side() -> int:
            zoom = float(zoom_slider.value or 1)
            return max(1, round(minimum_dimension / zoom))

        def clamp_crop_center() -> None:
            nonlocal crop_center_x, crop_center_y
            half_side = crop_side() / 2
            crop_center_x = min(
                max(crop_center_x, half_side),
                crop_canvas_size - half_side,
            )
            crop_center_y = min(
                max(crop_center_y, half_side),
                crop_canvas_size - half_side,
            )

        def render_crop(size: int) -> bytes:
            clamp_crop_center()
            side = crop_side()
            left = round(crop_center_x - side / 2)
            top = round(crop_center_y - side / 2)
            left = min(max(left, 0), crop_canvas_size - side)
            top = min(max(top, 0), crop_canvas_size - side)
            cropped_image = crop_canvas.crop(
                (left, top, left + side, top + side)
            ).resize((size, size), Image.Resampling.LANCZOS)
            image_data = BytesIO()
            cropped_image.save(image_data, format="PNG")
            return image_data.getvalue()

        def refresh_crop_preview(_event: object | None = None) -> None:
            crop_preview.foreground_image_src = render_crop(preview_size)
            page.update()

        def move_crop(event: ft.DragUpdateEvent) -> None:
            nonlocal crop_center_x, crop_center_y
            if event.local_delta is None:
                return
            scale = crop_side() / preview_size
            crop_center_x -= event.local_delta.x * scale
            crop_center_y -= event.local_delta.y * scale
            refresh_crop_preview()

        def set_crop_error(message: str) -> None:
            show_temporary_feedback(page, crop_error, message)
            page.update()

        def save_cropped_photo(_event: object) -> None:
            nonlocal current_user_photo
            stored_filename = f"{uuid4().hex}.png"
            stored_path = PROFILE_PHOTOS_DIRECTORY / stored_filename

            def remove_stored_photo() -> None:
                try:
                    stored_path.unlink()
                except FileNotFoundError:
                    return
                except OSError:
                    logger.exception("Could not remove an unsaved profile photo")

            try:
                PROFILE_PHOTOS_DIRECTORY.mkdir(parents=True, exist_ok=True)
                with Image.open(BytesIO(render_crop(output_size))) as cropped_image:
                    cropped_image.save(
                        stored_path,
                        format="PNG",
                        optimize=True,
                    )
                updated = auth_controller.update_profile_photo(
                    user_id,
                    stored_filename,
                )
            except ValueError as exc:
                remove_stored_photo()
                set_crop_error(str(exc))
                return
            except ConnectionError:
                remove_stored_photo()
                logger.exception("Could not update the account profile photo")
                set_crop_error("Não foi possível guardar a fotografia.")
                return
            except OSError:
                remove_stored_photo()
                logger.exception("Could not save the cropped profile photo")
                set_crop_error("Não foi possível guardar a fotografia.")
                return

            if not updated:
                remove_stored_photo()
                set_crop_error(
                    "Não foi encontrada uma conta ativa para alterar."
                )
                return

            current_user_photo = stored_filename
            page.pop_dialog()
            update_profile_display(profile_settings_name.value, current_user_photo)
            set_profile_feedback("Fotografia de perfil atualizada.")
            page.update()

        zoom_slider.on_change = refresh_crop_preview
        crop_preview.foreground_image_src = render_crop(preview_size)
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Ajustar fotografia",
                content=ft.Column(
                    [
                        ft.Text(
                            "Arraste a imagem e use o controlo para aproximar ou afastar.",
                            size=13,
                            color=MUTED,
                        ),
                        ft.GestureDetector(
                            content=crop_preview,
                            on_pan_update=move_crop,
                        ),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.ZOOM_OUT, color=MUTED),
                                ft.Container(content=zoom_slider, expand=True),
                                ft.Icon(ft.Icons.ZOOM_IN, color=MUTED),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        crop_error,
                    ],
                    tight=True,
                    spacing=16,
                    width=360,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                actions=[
                    ft.TextButton(
                        content="Cancelar",
                        on_click=lambda _event: page.pop_dialog(),
                    ),
                    ft.TextButton(
                        content="Guardar",
                        on_click=save_cropped_photo,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    edit_profile_name_button.on_click = lambda _event: open_profile_name_dialog()
    profile_photo_edit_button.on_click = choose_profile_photo

    def toggle_profile_photo_edit_overlay(event: ft.Event[ft.Container]) -> None:
        profile_photo_edit_overlay.visible = bool(event.data)
        page.update()

    profile_settings_avatar_hover.on_hover = toggle_profile_photo_edit_overlay
    profile_menu_profile_action.on_click = open_profile_dialog

    def open_change_email_dialog() -> None:
        email = current_user_email
        if demo_mode or email is None:
            return

        current_password_field = ft.TextField(
            label="Palavra-passe atual",
            password=True,
            can_reveal_password=True,
            autofocus=True,
        )
        feedback = ft.Text("", size=12, color="#B42318", visible=False)

        def open_new_email_dialog(current_password: str) -> None:
            new_email_field = ft.TextField(
                label="Novo email",
                keyboard_type=ft.KeyboardType.EMAIL,
                autofocus=True,
            )
            new_feedback = ft.Text("", size=12, color="#B42318", visible=False)
            save_button = ft.FilledButton(content="Guardar")

            def save_new_email(_event: object) -> None:
                nonlocal current_user_email
                new_email = (new_email_field.value or "").strip()
                if not is_valid_email(new_email):
                    show_temporary_feedback(
                        page,
                        new_feedback,
                        "Introduza um email válido.",
                    )
                    page.update()
                    return

                save_button.disabled = True
                page.update()
                try:
                    changed = auth_controller.change_email(
                        email,
                        current_password,
                        new_email,
                    )
                except ValueError as exc:
                    show_temporary_feedback(page, new_feedback, str(exc))
                    save_button.disabled = False
                    page.update()
                    return
                except ConnectionError:
                    logger.exception("Could not change the account email")
                    show_temporary_feedback(
                        page,
                        new_feedback,
                        "Não foi possível alterar o email. "
                        "Verifique a ligação à base de dados.",
                    )
                    save_button.disabled = False
                    page.update()
                    return

                if not changed:
                    show_temporary_feedback(
                        page,
                        new_feedback,
                        "Não foi encontrada uma conta ativa para alterar.",
                    )
                    save_button.disabled = False
                    page.update()
                    return

                current_user_email = new_email
                page.pop_dialog()
                success_dialog = ft.AlertDialog(
                    modal=True,
                    title="Email alterado",
                    content=ft.Text("O email foi atualizado."),
                    actions=[
                        ft.FilledButton(
                            content="Fechar",
                            on_click=lambda _event: page.pop_dialog(),
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                page.show_dialog(success_dialog)
                dismiss_temporary_dialog(page, success_dialog)

            save_button.on_click = save_new_email
            new_email_field.on_submit = save_new_email
            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title="Alterar email",
                    content=ft.Column(
                        [new_email_field, new_feedback],
                        tight=True,
                        spacing=10,
                        width=360,
                    ),
                    actions=[
                        ft.TextButton(
                            content="Cancelar",
                            on_click=lambda _event: page.pop_dialog(),
                        ),
                        save_button,
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
            )

        def verify_current_password(_event: object) -> None:
            current_password = current_password_field.value or ""
            if not current_password:
                show_temporary_feedback(
                    page,
                    feedback,
                    "Introduza a palavra-passe atual.",
                )
                page.update()
                return

            try:
                user = auth_controller.authenticate(email, current_password)
            except ConnectionError:
                logger.exception("Could not verify the current account password")
                show_temporary_feedback(
                    page,
                    feedback,
                    "Não foi possível verificar a palavra-passe atual.",
                )
                page.update()
                return

            if user is None:
                show_temporary_feedback(
                    page,
                    feedback,
                    "A palavra-passe atual está incorreta.",
                )
                page.update()
                return

            page.pop_dialog()
            open_new_email_dialog(current_password)

        current_password_field.on_submit = verify_current_password
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Alterar email",
                content=ft.Column(
                    [current_password_field, feedback],
                    tight=True,
                    spacing=10,
                    width=360,
                ),
                actions=[
                    ft.TextButton(
                        content="Cancelar",
                        on_click=lambda _event: page.pop_dialog(),
                    ),
                    ft.FilledButton(
                        content="Continuar",
                        on_click=verify_current_password,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def open_change_password_dialog() -> None:
        email = current_user_email
        if demo_mode or email is None:
            return

        current_password_field = ft.TextField(
            label="Palavra-passe atual",
            password=True,
            can_reveal_password=True,
            autofocus=True,
        )
        feedback = ft.Text("", size=12, color="#B42318", visible=False)

        def open_new_password_dialog(current_password: str) -> None:
            new_password_field = ft.TextField(
                label="Nova palavra-passe",
                password=True,
                can_reveal_password=True,
                autofocus=True,
            )
            new_feedback = ft.Text("", size=12, color="#B42318", visible=False)
            save_button = ft.FilledButton(content="Guardar")

            def save_new_password(_event: object) -> None:
                new_password = new_password_field.value or ""
                if len(new_password) < MIN_PASSWORD_LENGTH:
                    show_temporary_feedback(
                        page,
                        new_feedback,
                        "A palavra-passe deve ter pelo menos 8 caracteres.",
                    )
                    page.update()
                    return
                if len(new_password) > MAX_PASSWORD_LENGTH:
                    show_temporary_feedback(
                        page,
                        new_feedback,
                        "A palavra-passe excede o limite de 128 caracteres.",
                    )
                    page.update()
                    return

                save_button.disabled = True
                page.update()
                try:
                    changed = auth_controller.change_password(
                        email,
                        current_password,
                        new_password,
                    )
                except ConnectionError:
                    logger.exception("Could not change the account password")
                    show_temporary_feedback(
                        page,
                        new_feedback,
                        "Não foi possível alterar a palavra-passe. "
                        "Verifique a ligação à base de dados.",
                    )
                    save_button.disabled = False
                    page.update()
                    return

                if not changed:
                    show_temporary_feedback(
                        page,
                        new_feedback,
                        "A palavra-passe atual já não é válida. Tente novamente.",
                    )
                    save_button.disabled = False
                    page.update()
                    return

                page.pop_dialog()
                success_dialog = ft.AlertDialog(
                    modal=True,
                    title="Palavra-passe alterada",
                    content=ft.Text("A palavra-passe foi atualizada."),
                    actions=[
                        ft.FilledButton(
                            content="Fechar",
                            on_click=lambda _event: page.pop_dialog(),
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                page.show_dialog(success_dialog)
                dismiss_temporary_dialog(page, success_dialog)

            save_button.on_click = save_new_password
            new_password_field.on_submit = save_new_password
            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title="Alterar palavra-passe",
                    content=ft.Column(
                        [new_password_field, new_feedback],
                        tight=True,
                        spacing=10,
                        width=360,
                    ),
                    actions=[
                        ft.TextButton(
                            content="Cancelar",
                            on_click=lambda _event: page.pop_dialog(),
                        ),
                        save_button,
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
            )

        def verify_current_password(_event: object) -> None:
            current_password = current_password_field.value or ""
            if not current_password:
                show_temporary_feedback(
                    page,
                    feedback,
                    "Introduza a palavra-passe atual.",
                )
                page.update()
                return

            try:
                user = auth_controller.authenticate(email, current_password)
            except ConnectionError:
                logger.exception("Could not verify the current account password")
                show_temporary_feedback(
                    page,
                    feedback,
                    "Não foi possível verificar a palavra-passe atual.",
                )
                page.update()
                return

            if user is None:
                show_temporary_feedback(
                    page,
                    feedback,
                    "A palavra-passe atual está incorreta.",
                )
                page.update()
                return

            page.pop_dialog()
            open_new_password_dialog(current_password)

        current_password_field.on_submit = verify_current_password
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Alterar palavra-passe",
                content=ft.Column(
                    [current_password_field, feedback],
                    tight=True,
                    spacing=10,
                    width=360,
                ),
                actions=[
                    ft.TextButton(
                        content="Cancelar",
                        on_click=lambda _event: page.pop_dialog(),
                    ),
                    ft.FilledButton(
                        content="Continuar",
                        on_click=verify_current_password,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    change_email_button.on_click = lambda _event: open_change_email_dialog()
    change_password_button.on_click = lambda _event: open_change_password_dialog()

    def build_dashboard_content() -> ft.Control:
        try:
            provas = current_provas_controller().listar_provas()
        except ConnectionError as exc:
            return panel(
                ft.Column(
                    [
                        ft.Text(
                            "Não foi possível carregar o dashboard.",
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=TEXT,
                        ),
                        ft.Text(str(exc), size=13, color="#B42318"),
                    ],
                    spacing=10,
                    tight=True,
                ),
                padding=22,
            )

        today = date.today()
        upcoming_provas = [prova for prova in provas if prova.data >= today]
        next_prova = upcoming_provas[0] if upcoming_provas else None
        try:
            enrolled_students = (
                current_provas_controller().contar_alunos_inscritos(
                    next_prova.idprova
                )
                if next_prova is not None
                else 0
            )
            profile_count = (
                auth_controller.contar_utilizadores()
                if not demo_mode
                else None
            )
        except ConnectionError as exc:
            return panel(
                ft.Column(
                    [
                        ft.Text(
                            "Não foi possível carregar o dashboard.",
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=TEXT,
                        ),
                        ft.Text(str(exc), size=13, color="#B42318"),
                    ],
                    spacing=10,
                    tight=True,
                ),
                padding=22,
            )

        palette = DARK_PALETTE if dark_theme_active else LIGHT_PALETTE

        def metric_card(
            title: str,
            value: str,
            tooltip: str | None = None,
        ) -> ft.Container:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text(title, size=13, color=palette["metric_label"]),
                        ft.Text(
                            value,
                            size=28,
                            weight=ft.FontWeight.W_600,
                            color=TEXT,
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
                width=190,
                padding=18,
                bgcolor=palette["surface"],
                border=ft.Border.all(1, palette["border"]),
                border_radius=12,
                tooltip=tooltip,
            )

        next_prova_date = (
            next_prova.data.strftime("%d/%m/%Y") if next_prova is not None else "—"
        )
        metrics = ft.Row(
            [
                metric_card("Provas registadas", str(len(provas))),
                metric_card("Provas futuras", str(len(upcoming_provas))),
                metric_card("Próxima prova", next_prova_date),
                metric_card("Alunos inscritos", str(enrolled_students)),
                metric_card(
                    "Responsáveis",
                    str(profile_count) if profile_count is not None else "—",
                ),
            ],
            spacing=12,
            run_spacing=12,
            wrap=True,
        )

        upcoming_rows: list[ft.Control] = []
        for prova in upcoming_provas[:5]:
            upcoming_rows.extend(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        prova.data.strftime("%d/%m/%Y"),
                                        size=14,
                                        weight=ft.FontWeight.W_600,
                                        color=TEXT,
                                    ),
                                    ft.Text(
                                        f"{format_hora(prova.horainicio)}–{format_hora(prova.horafinal)}",
                                        size=12,
                                        color=MUTED,
                                    ),
                                ],
                                spacing=4,
                                width=125,
                            ),
                            ft.Column(
                                [
                                    ft.Text(prova.escola, size=14, color=TEXT),
                                    ft.Text(prova.concelho, size=12, color=MUTED),
                                ],
                                spacing=4,
                                expand=True,
                            ),
                        ],
                        spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Divider(color="#E1E5E8"),
                ]
            )

        if upcoming_rows:
            upcoming_rows.pop()
        else:
            upcoming_rows.append(
                ft.Text(
                    "Não existem provas futuras agendadas.",
                    size=13,
                    color=MUTED,
                )
            )

        return ft.Column(
            [
                metrics,
                panel(
                    ft.Column(
                        [
                            ft.Text(
                                "Próximas provas",
                                size=17,
                                weight=ft.FontWeight.W_600,
                                color=TEXT,
                            ),
                            *upcoming_rows,
                        ],
                        spacing=12,
                        tight=True,
                    ),
                    padding=20,
                ),
            ],
            spacing=16,
            tight=True,
        )

    def show_section(key: str) -> None:
        nonlocal profile_menu_open
        profile_menu_open = False
        profile_menu.visible = False
        dismiss_profile_overlay.visible = False
        selected_section = next(section for section in sections if section[0] == key)
        _, label = selected_section
        palette = DARK_PALETTE if dark_theme_active else LIGHT_PALETTE
        update_prova_selection_controls()
        section_content.scroll = ft.ScrollMode.AUTO
        page_title.value = label

        for section_key, _ in sections:
            for item in navigation_items.get(section_key, []):
                selected = section_key == key
                item.bgcolor = palette["selected"] if selected else None
                text = item.content
                if isinstance(text, ft.Text):
                    text.color = (
                        palette["text"] if selected else palette["muted"]
                    )
                    text.weight = ft.FontWeight.W_600 if selected else ft.FontWeight.NORMAL

        if key == "overview":
            content = build_dashboard_content()
        elif key == "provas":
            content = panel(
                ft.Column(
                    [
                        result_message,
                        empty_provas_text,
                        ft.Row(
                            [event_table],
                            scroll=ft.ScrollMode.AUTO,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                    ],
                    spacing=6,
                    tight=True,
                ),
                padding=18,
            )
            content = ft.Column(
                [
                    ft.Row(
                        [
                            add_prova_button,
                            delete_provas_button,
                            cancel_prova_selection_button,
                            ft.Container(expand=True),
                            refresh_button,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    content,
                    ft.Row(
                        [
                            first_page_button,
                            previous_page_button,
                            page_indicator,
                            next_page_button,
                            last_page_button,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    ),
                ],
                spacing=4,
                tight=True,
            )
        elif key == "students":
            content = build_alunos_turmas_view(
                page,
                current_alunos_turmas_controller(),
                DARK_PALETTE if dark_theme_active else LIGHT_PALETTE,
                panel,
                read_only=demo_mode,
            )
        elif key == "registrations":
            content = build_inscricoes_view(
                page,
                current_competition_records_controller(),
                current_provas_controller(),
                current_alunos_turmas_controller(),
                palette,
                panel,
                read_only=demo_mode,
            )
        elif key == "bibs":
            content = build_dorsais_view(
                page,
                current_competition_records_controller(),
                current_provas_controller(),
                palette,
                panel,
                read_only=demo_mode,
            )
        elif key == "arrivals":
            content = build_chegadas_view(
                page,
                current_competition_records_controller(),
                current_provas_controller(),
                palette,
                panel,
                read_only=demo_mode,
            )
        elif key == "results":
            content = build_classificacoes_view(
                page,
                current_competition_records_controller(),
                current_provas_controller(),
                palette,
                panel,
                read_only=demo_mode,
            )
        elif key == "categories":
            content = build_categories_view(
                page,
                current_competition_records_controller(),
                current_provas_controller(),
                palette,
                panel,
                read_only=demo_mode,
            )
        elif key == "qr-reader":
            content = build_qr_reader_view(
                page,
                data_tools_file_picker,
                palette,
                panel,
            )
        elif key == "csv-tools":
            content = build_csv_tools_view(
                page,
                alunos_turmas_controller,
                data_tools_file_picker,
                palette,
                panel,
                read_only=demo_mode,
            )
        elif key == "settings":
            change_email_button.visible = not demo_mode
            change_password_button.visible = not demo_mode
            content = ft.Column(
                [
                    panel(
                        ft.Column(
                            [
                                ft.Text(
                                    "Tema",
                                    size=16,
                                    weight=ft.FontWeight.W_600,
                                    color=TEXT,
                                ),
                                ft.Row(
                                    [light_theme_button, dark_theme_button],
                                    spacing=12,
                                    wrap=True,
                                ),
                            ],
                            spacing=12,
                            tight=True,
                        ),
                        padding=22,
                    ),
                    *(
                        []
                        if demo_mode
                        else [
                            panel(
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Segurança",
                                            size=16,
                                            weight=ft.FontWeight.W_600,
                                            color=TEXT,
                                        ),
                                        change_email_button,
                                        change_password_button,
                                    ],
                                    spacing=12,
                                    tight=True,
                                ),
                                padding=22,
                            )
                        ]
                    ),
                ],
                spacing=12,
                tight=True,
            )
        else:
            content = panel(
                ft.Column(
                    [
                        ft.Icon(ft.Icons.CONSTRUCTION_OUTLINED, size=30, color=PRIMARY),
                        ft.Text(
                            "Secção indisponível.",
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=TEXT,
                        ),
                        ft.Text(
                            section_descriptions.get(
                                key,
                                "Esta secção não existe na navegação atual.",
                            ),
                            size=12,
                            color=MUTED,
                        ),
                    ],
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=22,
            )

        section_content.controls = [
            ft.Row([content_menu_button, page_title], spacing=8),
            mobile_navigation,
            content,
        ]
        apply_theme_colors(dark_theme_active, update_page=False)
        page.update()
        if key == "provas":
            load_provas()

    async def blink_demo_notice() -> None:
        while demo_mode:
            await asyncio.sleep(0.5)
            if not demo_mode:
                break
            demo_notice.opacity = 0 if demo_notice.opacity else 1
            page.update()
        demo_notice.opacity = 1
        page.update()

    def enter_demo_mode() -> None:
        nonlocal demo_mode, login_page_active, profile_menu_open
        nonlocal prova_selection_mode, current_user_id, current_user_email
        nonlocal current_user_photo
        demo_mode = True
        profile_menu_open = False
        profile_menu.visible = False
        dismiss_profile_overlay.visible = False
        profile_menu_profile_action.visible = False
        current_user_id = None
        current_user_email = None
        current_user_photo = None
        login_page_active = False
        prova_selection_mode = False
        selected_prova_ids.clear()
        demo_notice.opacity = 1
        update_profile_display("test", None)
        set_profile_feedback("")
        update_prova_selection_controls()
        content_container.padding = ft.Padding.symmetric(
            horizontal=32,
            vertical=28,
        )
        apply_responsive_layout(page.width or page.window.width or 1440)
        page.run_task(blink_demo_notice)
        show_section("overview")

    def show_login_page(_: ft.Event[ft.Container] | None = None) -> None:
        nonlocal demo_mode, login_page_active, profile_menu_open
        nonlocal current_user_id, current_user_email
        nonlocal current_user_photo
        demo_mode = False
        profile_menu_open = False
        profile_menu.visible = False
        dismiss_profile_overlay.visible = False
        profile_menu_profile_action.visible = True
        current_user_id = None
        current_user_email = None
        current_user_photo = None
        update_profile_display("Administrador", None)
        set_profile_feedback("")
        demo_notice_container.visible = False
        demo_notice.visible = False
        demo_notice.opacity = 1
        login_page_active = True
        section_content.scroll = None
        sidebar.visible = False
        content_menu_button.visible = False
        mobile_navigation.visible = False
        content_container.padding = 0
        white = ft.Colors.WHITE
        transparent = ft.Colors.TRANSPARENT
        login_border = {
            ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                side=ft.BorderSide(color=white),
                border_radius=10,
            ),
            ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                side=ft.BorderSide(color=white, width=2),
                border_radius=10,
            ),
            ft.ControlState.ERROR: ft.OutlineInputBorder(
                side=ft.BorderSide(color=white),
                border_radius=10,
            ),
        }
        email_field = ft.TextField(
            label="Email",
            keyboard_type=ft.KeyboardType.EMAIL,
            border=login_border,
            color=white,
            focused_color=white,
            label_style=ft.TextStyle(color=white),
            cursor_color=white,
            selection_color="#66FFFFFF",
            filled=True,
            fill_color=transparent,
            focused_bgcolor=transparent,
            autofocus=True,
        )
        password_field = ft.TextField(
            label="Palavra-passe",
            password=True,
            can_reveal_password=True,
            border=login_border,
            color=white,
            focused_color=white,
            label_style=ft.TextStyle(color=white),
            cursor_color=white,
            selection_color="#66FFFFFF",
            filled=True,
            fill_color=transparent,
            focused_bgcolor=transparent,
        )
        login_feedback = ft.Text(
            "",
            size=12,
            color=white,
            text_align=ft.TextAlign.CENTER,
        )
        demo_letter_positions = {3, 8, 11, 12}
        clicked_demo_letters: set[int] = set()
        demo_letter_spans: dict[int, ft.TextSpan] = {}

        def click_demo_letter(position: int) -> None:
            clicked_demo_letters.add(position)
            demo_letter_spans[position].style = ft.TextStyle(color="#E53935")
            page.update()
            if clicked_demo_letters == demo_letter_positions:
                enter_demo_mode()

        def submit_login(_: object | None = None) -> None:
            nonlocal login_page_active, current_user_id, current_user_email
            nonlocal current_user_photo
            if not login_page_active:
                return

            email = (email_field.value or "").strip()
            password = password_field.value or ""
            email_field.error_text = None
            password_field.error_text = None
            login_feedback.value = ""

            if not is_valid_email(email):
                show_temporary_feedback(
                    page,
                    login_feedback,
                    "Introduza um email válido.",
                )
                page.update()
                return
            if not password:
                show_temporary_feedback(
                    page,
                    login_feedback,
                    "Introduza a palavra-passe.",
                )
                page.update()
                return
            if len(password) > MAX_PASSWORD_LENGTH:
                show_temporary_feedback(
                    page,
                    login_feedback,
                    "A palavra-passe excede o limite permitido.",
                )
                page.update()
                return

            login_button.disabled = True
            page.update()
            try:
                user = auth_controller.authenticate(email, password)
            except ConnectionError:
                logger.exception("Could not authenticate against MySQL")
                show_temporary_feedback(
                    page,
                    login_feedback,
                    "Não foi possível ligar à base de dados.",
                )
                login_button.disabled = False
                page.update()
                return

            login_button.disabled = False
            if user is None:
                show_temporary_feedback(
                    page,
                    login_feedback,
                    "Email ou palavra-passe incorretos.",
                )
                page.update()
                return

            current_user_id = user.id
            current_user_email = user.email
            current_user_photo = user.foto_perfil
            update_profile_display(user.nome, current_user_photo)
            set_profile_feedback("")
            login_page_active = False
            content_container.padding = ft.Padding.symmetric(
                horizontal=32,
                vertical=28,
            )
            apply_responsive_layout(page.width or page.window.width or 1440)
            show_section("overview")

        password_field.on_submit = submit_login

        login_button = ft.FilledButton(
            content="Entrar",
            width=336,
            height=48,
            bgcolor=transparent,
            color=ft.Colors.WHITE,
            on_click=submit_login,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=0),
            ),
        )
        login_title = ft.Text(
            spans=[
                ft.TextSpan(
                    text=letter,
                    style=ft.TextStyle(color=white),
                    on_click=lambda _event, index=index: click_demo_letter(index),
                )
                if index in demo_letter_positions
                else ft.TextSpan(text=letter)
                for index, letter in enumerate("CORTA-MATO ESCOLAR")
            ],
            size=40,
            weight=ft.FontWeight.W_700,
            color=white,
            text_align=ft.TextAlign.CENTER,
            no_wrap=True,
        )
        demo_letter_spans.update(
            {
                index: span
                for index, span in enumerate(login_title.spans)
                if index in demo_letter_positions
            }
        )
        login_form = ft.Container(
            content=ft.Column(
                [
                    login_title,
                    ft.Text(
                        "Iniciar sessão",
                        size=25,
                        weight=ft.FontWeight.W_600,
                        color=white,
                    ),
                    email_field,
                    password_field,
                    ft.Container(
                        content=login_feedback,
                        alignment=ft.Alignment.CENTER,
                        height=24,
                        width=336,
                    ),
                    login_button,
                ],
                spacing=12,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=26,
            width=520,
        )
        login_video = ftv.Video(
            playlist=[ftv.VideoMedia(str(LOGIN_VIDEO_PATH))],
            fit=ft.BoxFit.COVER,
            autoplay=True,
            muted=True,
            controls=None,
            playlist_mode=ftv.PlaylistMode.LOOP,
            on_error=lambda event: logger.error(
                "Login background video failed: %s",
                event.data,
            ),
            fill_color=ft.Colors.BLACK,
            expand=True,
        )
        section_content.controls = [
            ft.Stack(
                [
                    login_video,
                    ft.Container(
                        expand=True,
                        bgcolor=ft.Colors.BLACK,
                        opacity=0.28,
                    ),
                    ft.Container(
                        content=login_form,
                        alignment=ft.Alignment.CENTER,
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Image(
                            src=LOGIN_LOGO_PATH.read_bytes(),
                            width=190,
                            height=70,
                            fit=ft.BoxFit.CONTAIN,
                        ),
                        right=28,
                        bottom=28,
                        padding=10,
                    ),
                ],
                fit=ft.StackFit.EXPAND,
                expand=True,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ),
        ]
        apply_theme_colors(dark_theme_active, update_page=False)
        page.update()

    def toggle_profile_menu(_: object) -> None:
        nonlocal profile_menu_open
        if login_page_active or not sidebar.visible:
            return
        profile_menu_open = not profile_menu_open
        profile_menu.visible = profile_menu_open
        dismiss_profile_overlay.visible = profile_menu_open
        if profile_menu_open:
            profile_menu.left = max(60, sidebar.width - profile_menu.width)
        page.update()

    def apply_responsive_layout(width: float) -> None:
        nonlocal profile_menu_open
        is_narrow = width < 900
        if is_narrow:
            profile_menu_open = False
            profile_menu.visible = False
            dismiss_profile_overlay.visible = False
        sidebar.visible = not is_narrow and not login_page_active
        sidebar.width = 260 if navigation_open else 84
        profile_menu.left = max(60, sidebar.width - profile_menu.width)
        sidebar_contents.visible = navigation_open
        sidebar_contents.expand = navigation_open
        collapsed_sidebar_spacer.visible = not navigation_open
        demo_notice_container.visible = (
            demo_mode and navigation_open and not is_narrow and not login_page_active
        )
        demo_notice.visible = demo_notice_container.visible
        profile_name.visible = navigation_open
        profile_button.width = 220 if navigation_open else 44
        content_menu_button.visible = is_narrow and not login_page_active
        mobile_navigation.visible = (
            is_narrow and navigation_open and not login_page_active
        )
        content_container.padding = (
            0
            if login_page_active
            else ft.Padding.symmetric(
                horizontal=14 if is_narrow else 32,
                vertical=16 if is_narrow else 28,
            )
        )
        sidebar_width = sidebar.width if sidebar.visible else 0
        table_width = max(
            280,
            width
            - sidebar_width
            - (28 if is_narrow else 64)
            - 38,
        )
        event_table.width = table_width
        if (width < 1050) != compact_table:
            set_table_layout(width < 1050)
            apply_theme_colors(dark_theme_active, update_page=False)
        page.update()

    def toggle_navigation(_: ft.Event[ft.Container]) -> None:
        nonlocal navigation_open, profile_menu_open
        navigation_open = not navigation_open
        profile_menu_open = False
        profile_menu.visible = False
        dismiss_profile_overlay.visible = False
        sidebar_menu_button.tooltip = (
            "Fechar menu" if navigation_open else "Abrir menu"
        )
        content_menu_button.tooltip = (
            "Fechar menu" if navigation_open else "Abrir menu"
        )
        apply_responsive_layout(page.width or page.window.width or 1440)

    sidebar_menu_button.on_click = toggle_navigation
    content_menu_button.on_click = toggle_navigation
    profile_button.on_click = toggle_profile_menu
    dismiss_profile_overlay.on_click = dismiss_profile_menu
    logout_button.on_click = show_login_page

    def handle_resize(event: ft.PageResizeEvent) -> None:
        apply_responsive_layout(event.width)

    page.on_resize = handle_resize
    page.add(
        ft.Stack(
            [
                ft.Row(
                    [
                        sidebar,
                        content_container,
                    ],
                    spacing=0,
                    expand=True,
                ),
                dismiss_profile_overlay,
                profile_menu,
            ],
            expand=True,
            clip_behavior=ft.ClipBehavior.NONE,
        )
    )
    initial_width = page.width or page.window.width or 1440
    apply_responsive_layout(initial_width)
    show_login_page()