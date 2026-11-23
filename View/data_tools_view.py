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
        status_text.value = message
        status_text.color = palette["error"] if is_error else palette["muted"]
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

        selected_file_text.value = selected_file.path or selected_file.name
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

    camera_button = ft.OutlinedButton(
        content="Usar câmara",
        on_click=start_camera_scan,
    )
    image_button = ft.FilledButton(
        content="Selecionar imagem",
        on_click=choose_image,
    )

    content = panel_builder(
        ft.Column(
            [
                ft.Text(
                    "Selecione uma imagem para ler o respetivo QR code ou use a câmara.",
                    size=13,
                    color=palette["muted"],
                ),
                ft.Row([image_button, camera_button], wrap=True),
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
    import_status = ft.Text("", size=13, color=palette["muted"])
    export_status = ft.Text("", size=13, color=palette["muted"])
    selected_import_files: dict[str, ft.FilePickerFile] = {}
    class_file_path = ft.TextField(
        hint_text="Ficheiro CSV de turmas",
        read_only=True,
        width=520,
        height=48,
    )
    student_file_path = ft.TextField(
        hint_text="Ficheiro CSV de alunos",
        read_only=True,
        width=520,
        height=48,
    )
    export_directory: str | None = None
    export_file_path = ft.TextField(
        label="Destino do ficheiro CSV",
        read_only=True,
        width=520,
        height=48,
    )

    def set_import_status(message: str, is_error: bool = False) -> None:
        import_status.value = message
        import_status.color = palette["error"] if is_error else palette["muted"]
        page.update()

    def set_export_status(message: str, is_error: bool = False) -> None:
        export_status.value = message
        export_status.color = palette["error"] if is_error else palette["muted"]
        page.update()

    def display_import_summary(summary: ImportSummary) -> None:
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
        set_import_status(message, bool(summary.errors) or summary.interrupted)

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
        field = class_file_path if kind == "classes" else student_file_path
        field.value = files[0].path or files[0].name
        set_import_status("")

    async def import_selected_file(
        kind: str,
        importer: Callable[[bytes, AlunosTurmasController], ImportSummary],
    ) -> None:
        selected_file = selected_import_files.get(kind)
        if selected_file is None:
            set_import_status("Selecione primeiro um ficheiro CSV.", True)
            return
        content = selected_file.bytes
        if content is None and selected_file.path:
            try:
                content = Path(selected_file.path).read_bytes()
            except OSError:
                logger.exception("Could not read selected CSV file")
                set_import_status("Não foi possível ler o ficheiro selecionado.", True)
                return
        if content is None:
            set_import_status("Não foi possível ler o ficheiro selecionado.", True)
            return
        try:
            summary = importer(content, controller)
        except ConnectionError:
            logger.exception("Could not import CSV data")
            set_import_status(
                "Não foi possível importar. Verifique a ligação à base de dados.",
                True,
            )
            return
        except ValueError as exc:
            set_import_status(str(exc), True)
            return
        display_import_summary(summary)

    async def choose_export_directory(_event: object) -> None:
        nonlocal export_directory
        directory = await file_picker.get_directory_path(
            dialog_title="Selecionar pasta para exportação",
        )
        if directory is None:
            return
        export_directory = directory
        export_file_path.value = str(Path(directory) / export_filename())
        set_export_status("")

    def export_filename() -> str:
        return "alunos.csv" if export_kind.value == "students" else "turmas.csv"

    def update_export_path(_event: object) -> None:
        if export_directory is not None:
            export_file_path.value = str(Path(export_directory) / export_filename())
            page.update()

    async def export_csv(_event: object) -> None:
        if export_directory is None:
            set_export_status("Escolha primeiro a pasta de destino.", True)
            return
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

        target_path = Path(export_directory) / export_filename()
        try:
            if target_path.exists():
                saved_path = await file_picker.save_file(
                    dialog_title="Exportar CSV",
                    file_name=target_path.name,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["csv"],
                    initial_directory=export_directory,
                    src_bytes=content,
                )
                if saved_path is None:
                    return
                target_path = Path(saved_path)
            else:
                target_path.write_bytes(content)
        except OSError:
            logger.exception("Could not write exported CSV file")
            set_export_status("Não foi possível guardar o ficheiro CSV.", True)
            return
        except ValueError as exc:
            set_export_status(str(exc), True)
            return

        export_file_path.value = str(target_path)
        set_export_status(f"Ficheiro exportado: {target_path}")

    if read_only:
        import_status.value = (
            "A importação e exportação estão disponíveis após iniciar sessão "
            "com uma base de dados ligada."
        )
        import_status.color = palette["error"]

    import_panel = panel_builder(
        ft.Column(
            [
                ft.Text(
                    "Importar CSV",
                    size=17,
                    weight=ft.FontWeight.W_600,
                    color=palette["text"],
                ),
                ft.Text(
                    "Separador ';' ou ','. Importe primeiro as turmas e só depois "
                    "os alunos.",
                    size=12,
                    color=palette["muted"],
                ),
                ft.Text(
                    "Turmas",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=palette["text"],
                ),
                ft.Text(
                    "Colunas: ano_escolar; letra",
                    size=12,
                    color=palette["muted"],
                ),
                ft.Row(
                    [
                        class_file_path,
                        ft.OutlinedButton(
                            content="Procurar...",
                            disabled=read_only,
                            on_click=lambda _event: choose_import_file(
                                "classes",
                                "Selecionar CSV de turmas",
                            ),
                        ),
                        ft.FilledButton(
                            content="Importar turmas",
                            disabled=read_only,
                            on_click=lambda _event: import_selected_file(
                                "classes",
                                import_classes_csv,
                            ),
                        ),
                    ],
                    wrap=True,
                ),
                ft.Divider(color=palette["divider"]),
                ft.Text(
                    "Alunos",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=palette["text"],
                ),
                ft.Text(
                    "Colunas: numeroprocesso; nome; datanasc; sexo; "
                    "ano_escolar; letra. Data em AAAA-MM-DD; turma opcional.",
                    size=12,
                    color=palette["muted"],
                ),
                ft.Row(
                    [
                        student_file_path,
                        ft.OutlinedButton(
                            content="Procurar...",
                            disabled=read_only,
                            on_click=lambda _event: choose_import_file(
                                "students",
                                "Selecionar CSV de alunos",
                            ),
                        ),
                        ft.FilledButton(
                            content="Importar alunos",
                            disabled=read_only,
                            on_click=lambda _event: import_selected_file(
                                "students",
                                import_students_csv,
                            ),
                        ),
                    ],
                    wrap=True,
                ),
                import_status,
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
        on_select=update_export_path,
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
                ft.Text(
                    "O ficheiro é guardado em UTF-8 com separador ';' "
                    "(abre bem no Excel).",
                    size=12,
                    color=palette["muted"],
                ),
                export_kind,
                ft.Row(
                    [
                        export_file_path,
                        ft.OutlinedButton(
                            content="Procurar...",
                            disabled=read_only,
                            on_click=choose_export_directory,
                        ),
                        ft.FilledButton(
                            content="Exportar CSV",
                            disabled=read_only,
                            on_click=export_csv,
                        ),
                    ],
                    wrap=True,
                ),
                export_status,
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
