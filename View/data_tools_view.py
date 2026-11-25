"""QR reader and CSV import/export screens."""

import logging
import webbrowser
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

import flet as ft

from Controllers.alunos_turmas_controller import AlunosTurmasController
from Controllers.csv_tools_controller import (
    ImportSummary,
    export_classes_csv,
    export_students_csv,
    import_classes_csv,
    import_students_csv,
)
from Controllers.qr_reader_controller import (
    QRReaderError,
    decode_qr_image,
    scan_qr_with_camera,
)
from View.feedback import show_temporary_feedback


logger = logging.getLogger(__name__)


def normalize_http_url(value: str) -> str | None:
    candidate = value.strip()
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
        return None
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"}:
        if "://" in candidate:
            return None
        candidate = "https://" + candidate.lstrip("/")
        try:
            parsed = urlsplit(candidate)
        except ValueError:
            return None
    try:
        parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or any(character.isspace() for character in parsed.hostname)
    ):
        return None
    return candidate


def build_qr_reader_view(
    page: ft.Page,
    file_picker: ft.FilePicker,
    palette: dict[str, str],
    panel_builder: Callable[..., ft.Container],
    allow_camera: bool = True,
) -> ft.Control:
    selected_file_text = ft.Text("", size=12, color=palette["muted"])
    status_text = ft.Text("", size=13, color=palette["muted"])
    image_preview = ft.Image(
        src="",
        width=280,
        height=280,
        fit=ft.BoxFit.CONTAIN,
        visible=False,
    )

    def set_status(message: str, is_error: bool = False) -> None:
        show_temporary_feedback(
            page,
            status_text,
            message,
            color=palette["error"] if is_error else palette["muted"],
        )
        page.update()

    def open_decoded_site(value: str) -> None:
        url = normalize_http_url(value)
        if url is None:
            set_status("O QR não contém um endereço HTTP ou HTTPS válido.", True)
            return
        if not webbrowser.open_new_tab(url):
            set_status("Não foi possível abrir o navegador.", True)
            return
        set_status(f"Site aberto no navegador: {url}")

    async def choose_image(_event: object) -> None:
        files = await file_picker.pick_files(
            dialog_title="Selecionar imagem com código QR",
            file_type=ft.FilePickerFileType.IMAGE,
            allow_multiple=False,
            with_data=True,
        )
        if not files:
            return
        selected_file = files[0]
        try:
            image_bytes = selected_file.bytes
            if image_bytes is None and selected_file.path:
                image_bytes = Path(selected_file.path).read_bytes()
        except OSError:
            logger.exception("Could not read selected QR image")
            set_status("Não foi possível ler a imagem selecionada.", True)
            return
        if image_bytes is None:
            set_status("Não foi possível ler a imagem selecionada.", True)
            return

        show_temporary_feedback(
            page,
            selected_file_text,
            selected_file.path or selected_file.name,
        )
        image_preview.src = image_bytes
        image_preview.visible = True
        try:
            value = decode_qr_image(image_bytes)
        except QRReaderError as exc:
            set_status(str(exc), True)
            page.update()
            return
        open_decoded_site(value)

    async def finish_camera_scan(
        value: str | None,
        error: str | None = None,
    ) -> None:
        camera_button.disabled = False
        if error is not None:
            set_status(error, True)
        elif value is None:
            set_status("Leitura cancelada.")
        else:
            open_decoded_site(value)

    def start_camera_scan(_event: object) -> None:
        camera_button.disabled = True
        set_status("A câmara foi aberta. Prima Q ou Esc na janela para fechar.")

        def scan() -> None:
            try:
                value = scan_qr_with_camera()
            except QRReaderError as exc:
                page.run_task(finish_camera_scan, None, str(exc))
                return
            page.run_task(finish_camera_scan, value)

        page.run_thread(scan)


    image_button = ft.FilledButton(
        content="Selecionar imagem",
        on_click=choose_image,
    )
    action_controls: list[ft.Control] = [image_button]
    camera_button: ft.OutlinedButton | None = None
    if allow_camera:
        camera_button = ft.OutlinedButton(
            content="Usar câmara",
            on_click=start_camera_scan,
        )
        action_controls.append(camera_button)

    description = (
        "Selecione uma imagem para ler o respetivo QR code."
        if not allow_camera
        else "Selecione uma imagem para ler o respetivo QR code ou use a câmara."
    )

    content = panel_builder(
        ft.Column(
            [
                ft.Text(
                    description,
                    size=13,
                    color=palette["muted"],
                ),
                ft.Row(action_controls, wrap=True),

                selected_file_text,
                status_text,
                ft.Container(
                    content=image_preview,
                    alignment=ft.Alignment.CENTER_LEFT,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        padding=22,
        width=680,
    )
    return content


def build_csv_tools_view(
    page: ft.Page,
    controller: AlunosTurmasController,
    file_picker: ft.FilePicker,
    palette: dict[str, str],
    panel_builder: Callable[..., ft.Container],
    read_only: bool = False,
) -> ft.Control:
    import_notice = ft.Text("", size=13, color=palette["muted"])
    class_import_status = ft.Text("", size=13, color=palette["muted"])
    student_import_status = ft.Text("", size=13, color=palette["muted"])
    export_status = ft.Text("", size=13, color=palette["muted"])
    selected_import_files: dict[str, ft.FilePickerFile] = {}
    import_file_slots: dict[str, ft.Row] = {}
    import_browse_buttons: dict[str, ft.OutlinedButton] = {}

    def set_import_status(
        kind: str,
        message: str,
        is_error: bool = False,
    ) -> None:
        status = (
            class_import_status
            if kind == "classes"
            else student_import_status
        )
        show_temporary_feedback(
            page,
            status,
            message,
            color=palette["error"] if is_error else palette["muted"],
        )
        page.update()

    def reset_import_file(kind: str) -> None:
        selected_import_files.pop(kind, None)
        file_slot = import_file_slots.get(kind)
        browse_button = import_browse_buttons.get(kind)
        if file_slot is not None and browse_button is not None:
            file_slot.controls = [browse_button]

    def clear_import_file(kind: str) -> None:
        reset_import_file(kind)
        status = class_import_status if kind == "classes" else student_import_status
        status.value = ""
        status.visible = False
        page.update()

    def build_selected_file_chip(kind: str, file_name: str) -> ft.OutlinedButton:
        return ft.OutlinedButton(
            content=ft.Row(
                [
                    ft.Text(
                        file_name,
                        size=14,
                        color=palette["primary"],
                        no_wrap=True,
                    ),
                    ft.Container(
                        width=1,
                        height=20,
                        bgcolor=palette["divider"],
                    ),
                    ft.Icon(
                        ft.Icons.CLOSE,
                        size=14,
                        color=palette["muted"],
                    ),
                ],
                spacing=4,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=max(96, len(file_name) * 8 + 58),
            disabled=read_only,
            on_click=lambda _event: clear_import_file(kind),
        )

    def set_export_status(message: str, is_error: bool = False) -> None:
        show_temporary_feedback(
            page,
            export_status,
            message,
            color=palette["error"] if is_error else palette["muted"],
        )
        page.update()

    def feedback_slot(status: ft.Text, height: int) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [status],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
            height=height,
        )

    def display_import_summary(kind: str, summary: ImportSummary) -> None:
        message = (
            f"{summary.imported} importados; "
            f"{summary.duplicates} duplicados ignorados; "
            f"{len(summary.errors)} linhas com erro."
        )
        if summary.interrupted:
            message += " A importação foi interrompida por uma falha na base de dados."
        if summary.errors:
            message += "\n" + "\n".join(summary.errors[:5])
            if len(summary.errors) > 5:
                message += f"\n… e mais {len(summary.errors) - 5} erros."
        set_import_status(
            kind,
            message,
            bool(summary.errors) or summary.interrupted,
        )

    async def choose_import_file(kind: str, title: str) -> None:
        files = await file_picker.pick_files(
            dialog_title=title,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["csv"],
            allow_multiple=False,
            with_data=True,
        )
        if not files:
            return
        selected_import_files[kind] = files[0]
        import_file_slots[kind].controls = [
            build_selected_file_chip(kind, files[0].name)
        ]
        set_import_status(kind, "")

    async def import_selected_file(
        kind: str,
        importer: Callable[[bytes, AlunosTurmasController], ImportSummary],
    ) -> None:
        selected_file = selected_import_files.get(kind)
        if selected_file is None:
            set_import_status(kind, "Selecione primeiro um ficheiro CSV.", True)
            return
        try:
            content = selected_file.bytes
            if content is None and selected_file.path:
                try:
                    content = Path(selected_file.path).read_bytes()
                except OSError:
                    logger.exception("Could not read selected CSV file")
                    set_import_status(
                        kind,
                        "Não foi possível ler o ficheiro selecionado.",
                        True,
                    )
                    return
            if content is None:
                set_import_status(
                    kind,
                    "Não foi possível ler o ficheiro selecionado.",
                    True,
                )
                return
            try:
                summary = importer(content, controller)
            except ConnectionError:
                logger.exception("Could not import CSV data")
                set_import_status(
                    kind,
                    "Não foi possível importar. Verifique a ligação à base de dados.",
                    True,
                )
                return
            except ValueError as exc:
                set_import_status(kind, str(exc), True)
                return
            display_import_summary(kind, summary)
        finally:
            reset_import_file(kind)
            page.update()

    async def choose_classes_file(_event: object) -> None:
        await choose_import_file("classes", "Selecionar CSV de turmas")

    async def import_classes_file(_event: object) -> None:
        await import_selected_file("classes", import_classes_csv)

    async def choose_students_file(_event: object) -> None:
        await choose_import_file("students", "Selecionar CSV de alunos")

    async def import_students_file(_event: object) -> None:
        await import_selected_file("students", import_students_csv)

    def export_filename() -> str:
        return "alunos.csv" if export_kind.value == "students" else "turmas.csv"

    async def export_csv(_event: object) -> None:
        is_student_export = export_kind.value == "students"
        exporter = export_students_csv if is_student_export else export_classes_csv
        try:
            content = exporter(controller)
        except ConnectionError:
            logger.exception("Could not export CSV data")
            set_export_status(
                "Não foi possível exportar. Verifique a ligação à base de dados.",
                True,
            )
            return
        except ValueError as exc:
            set_export_status(str(exc), True)
            return

        try:
            saved_path = await file_picker.save_file(
                dialog_title="Exportar CSV",
                file_name=export_filename(),
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"],
                src_bytes=content,
            )
        except OSError:
            logger.exception("Could not write exported CSV file")
            set_export_status("Não foi possível guardar o ficheiro CSV.", True)
            return
        except ValueError as exc:
            set_export_status(str(exc), True)
            return

        if saved_path is not None:
            set_export_status("Ficheiro exportado com sucesso!")

    if read_only:
        import_notice.value = (
            "A importação e exportação estão disponíveis após iniciar sessão "
            "com uma base de dados ligada."
        )
        import_notice.color = palette["error"]

    class_browse_button = ft.OutlinedButton(
        content="Procurar...",
        disabled=read_only,
        on_click=choose_classes_file,
    )
    student_browse_button = ft.OutlinedButton(
        content="Procurar...",
        disabled=read_only,
        on_click=choose_students_file,
    )
    import_browse_buttons.update(
        {
            "classes": class_browse_button,
            "students": student_browse_button,
        }
    )
    class_file_slot = ft.Row([class_browse_button], tight=True)
    student_file_slot = ft.Row([student_browse_button], tight=True)
    import_file_slots.update(
        {
            "classes": class_file_slot,
            "students": student_file_slot,
        }
    )

    import_panel = panel_builder(
        ft.Column(
            [
                ft.Text(
                    "Importar CSV",
                    size=17,
                    weight=ft.FontWeight.W_600,
                    color=palette["text"],
                ),
                import_notice,
                ft.Text(
                    "Turmas",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=palette["text"],
                ),
                ft.Row(
                    [
                        class_file_slot,
                        ft.FilledButton(
                            content="Importar turmas",
                            disabled=read_only,
                            on_click=import_classes_file,
                        ),
                    ],
                    wrap=True,
                ),
                feedback_slot(class_import_status, 24),
                ft.Divider(color=palette["divider"]),
                ft.Text(
                    "Alunos",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=palette["text"],
                ),
                ft.Row(
                    [
                        student_file_slot,
                        ft.FilledButton(
                            content="Importar alunos",
                            disabled=read_only,
                            on_click=import_students_file,
                        ),
                    ],
                    wrap=True,
                ),
                feedback_slot(student_import_status, 24),
            ],
            spacing=12,
            tight=True,
        ),
        padding=22,
    )

    export_kind = ft.Dropdown(
        label="Relatório",
        value="students",
        width=260,
        options=[
            ft.DropdownOption(key="students", text="Alunos"),
            ft.DropdownOption(key="classes", text="Turmas"),
        ],
        disabled=read_only,
    )
    export_panel = panel_builder(
        ft.Column(
            [
                ft.Text(
                    "Exportar relatório",
                    size=17,
                    weight=ft.FontWeight.W_600,
                    color=palette["text"],
                ),
                export_kind,
                ft.FilledButton(
                    content="Exportar CSV",
                    disabled=read_only,
                    on_click=export_csv,
                ),
                feedback_slot(export_status, 24),
            ],
            spacing=12,
            tight=True,
        ),
        padding=22,
        width=760,
    )

    return ft.Column(
        [import_panel, export_panel],
        spacing=16,
        tight=True,
    )
