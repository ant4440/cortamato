import unittest
from datetime import date
from pathlib import Path

import cv2
import flet as ft
from Controllers.csv_tools_controller import (
    export_classes_csv,
    export_students_csv,
    import_classes_csv,
    import_students_csv,
)
from Controllers.qr_reader_controller import QRReaderError, decode_qr_image
from Model.alunos_turmas import Aluno, Turma
from Model.competition_records import _validar_regra_apuramento
from View.data_tools_view import (
    build_csv_tools_view,
    build_qr_reader_view,
    normalize_http_url,
)


class FakeAlunosTurmasController:
    def __init__(self) -> None:
        self.classes = [Turma(1, 7, "A", 1)]
        self.students = [
            Aluno(111, "Ana", date(2012, 4, 3), "F", 1, "7.º A")
        ]

    def listar_turmas(self) -> list[Turma]:
        return list(self.classes)

    def listar_alunos(self, pesquisa: str = "", turma_id: int | None = None) -> list[Aluno]:
        return list(self.students)

    def criar_turma(self, ano_escolar: int, letra: str) -> None:
        if not 1 <= ano_escolar <= 12:
            raise ValueError("O ano escolar deve estar entre 1 e 12.")
        if len(letra) != 1 or not "A" <= letra.upper() <= "Z":
            raise ValueError("A letra da turma deve ser uma letra de A a Z.")
        self.classes.append(
            Turma(len(self.classes) + 1, ano_escolar, letra, 0)
        )

    def criar_aluno(
        self,
        numeroprocesso: int,
        nome: str,
        datanasc: date,
        sexo: str,
        turma_id: int | None,
    ) -> None:
        turma = next(
            (item for item in self.classes if item.id == turma_id),
            None,
        )
        turma_name = turma.designacao if turma else "Sem turma"
        self.students.append(
            Aluno(numeroprocesso, nome, datanasc, sexo, turma_id, turma_name)
        )


class CsvToolsTests(unittest.TestCase):
    def test_import_accepts_windows_1252_csv(self) -> None:
        controller = FakeAlunosTurmasController()
        content = (
            "numeroprocesso,nome,datanasc,sexo,ano_escolar,letra\n"
            "112,João,2012-04-03,F,7,A"
        ).encode("cp1252")

        result = import_students_csv(content, controller)

        self.assertEqual(result.imported, 1)
        self.assertEqual(controller.students[-1].nome, "João")

    def test_import_classes_ignores_existing_and_repeated_rows(self) -> None:
        controller = FakeAlunosTurmasController()
        content = (
            b"ano_escolar;letra\r\n"
            b"7;A\r\n"
            b"8;b\r\n"
            b"8;B\r\n"
            b"0;C\r\n"
        )

        result = import_classes_csv(content, controller)

        self.assertEqual(result.imported, 1)
        self.assertEqual(result.duplicates, 2)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(controller.classes[-1].designacao, "8.º B")

    def test_exported_students_csv_can_be_imported_and_duplicates_are_skipped(self) -> None:
        source = FakeAlunosTurmasController()
        content = export_students_csv(source)
        target = FakeAlunosTurmasController()
        target.students.clear()

        first_import = import_students_csv(content, target)
        second_import = import_students_csv(content, target)

        self.assertEqual(first_import.imported, 1)
        self.assertEqual(target.students[0].nome, "Ana")
        self.assertEqual(second_import.imported, 0)
        self.assertEqual(second_import.duplicates, 1)

    def test_student_import_reports_invalid_date_and_unknown_class(self) -> None:
        controller = FakeAlunosTurmasController()
        content = (
            b"numeroprocesso,nome,datanasc,sexo,ano_escolar,letra\n"
            b"112,Beatriz,2012-04-03,F,7,A\n"
            b"113,Carlos,03/04/2012,M,7,A\n"
            b"114,Diana,2012-04-03,F,8,C\n"
        )

        result = import_students_csv(content, controller)

        self.assertEqual(result.imported, 1)
        self.assertEqual(len(result.errors), 2)


class QualificationRuleTests(unittest.TestCase):
    def test_origin_and_destination_must_be_different(self) -> None:
        with self.assertRaisesRegex(ValueError, "diferentes"):
            _validar_regra_apuramento(1, 1, 1, 1)

    def test_boolean_values_are_not_valid_positive_numbers(self) -> None:
        with self.assertRaisesRegex(ValueError, "inválida"):
            _validar_regra_apuramento(True, True, 1, 1)


class QRUrlTests(unittest.TestCase):
    def test_only_http_and_https_urls_are_accepted(self) -> None:
        self.assertEqual(
            normalize_http_url(" https://example.com/path "),
            "https://example.com/path",
        )
        self.assertEqual(
            normalize_http_url("qrto.org/z11YoJ"),
            "https://qrto.org/z11YoJ",
        )
        self.assertEqual(
            normalize_http_url("www.example.com/path"),
            "https://www.example.com/path",
        )
        self.assertIsNone(normalize_http_url("javascript:alert(1)"))
        self.assertIsNone(normalize_http_url("file:///C:/secret.txt"))
        self.assertIsNone(normalize_http_url("https://example.com:invalid"))
        self.assertIsNone(normalize_http_url("https://example.com/\nheader"))

    def test_invalid_image_is_reported_as_a_reader_error(self) -> None:
        with self.assertRaises(QRReaderError):
            decode_qr_image(b"not an image")

    def test_small_qr_image_is_decoded(self) -> None:
        image = cv2.QRCodeEncoder_create().encode("qrto.org/z11YoJ")
        encoded, image_bytes = cv2.imencode(".png", image)
        self.assertTrue(encoded)

        decoded = decode_qr_image(image_bytes.tobytes())
        self.assertEqual(decoded, "qrto.org/z11YoJ")
        self.assertEqual(
            normalize_http_url(decoded),
            "https://qrto.org/z11YoJ",
        )

class DataToolsViewTests(unittest.TestCase):
    def test_mobile_reader_uses_local_qr_decoder_without_backend(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        page = (project_root / "web" / "qr-mobile.html").read_text(
            encoding="utf-8"
        )

        self.assertIn('<script src="vendor/jsQR.js"></script>', page)
        self.assertIn("decodePixels(image)", page)
        self.assertNotIn('fetch("./decode"', page)

    def test_qr_reader_view_can_hide_camera_action(self) -> None:
        class PageStub:
            def update(self) -> None:
                pass

            def run_task(self, *args, **kwargs) -> None:
                pass

            def run_thread(self, *args, **kwargs) -> None:
                pass

        view = build_qr_reader_view(
            PageStub(),
            ft.FilePicker(),
            {"muted": "#727B82", "error": "#B42318", "text": "#252A2E"},
            lambda content, **kwargs: ft.Container(content=content, **kwargs),
            allow_camera=False,
        )

        buttons = view.content.controls[1].controls
        self.assertEqual([button.content for button in buttons], ["Selecionar imagem"])

    def test_qr_reader_view_has_visible_image_and_camera_actions(self) -> None:

        class PageStub:
            def update(self) -> None:
                pass

            def run_task(self, *args, **kwargs) -> None:
                pass

            def run_thread(self, *args, **kwargs) -> None:
                pass

        view = build_qr_reader_view(
            PageStub(),
            ft.FilePicker(),
            {"muted": "#727B82", "error": "#B42318", "text": "#252A2E"},
            lambda content, **kwargs: ft.Container(content=content, **kwargs),
        )

        self.assertIsInstance(view, ft.Container)
        self.assertIsInstance(view.content, ft.Column)
        buttons = view.content.controls[0].controls
        self.assertEqual(
            [button.content for button in buttons],
            ["Selecionar imagem"],
        )

    def test_csv_view_has_file_picker_and_import_export_actions(self) -> None:
        class PageStub:
            def update(self) -> None:
                pass

        view = build_csv_tools_view(
            PageStub(),
            FakeAlunosTurmasController(),
            ft.FilePicker(),
            {
                "muted": "#727B82",
                "error": "#B42318",
                "text": "#252A2E",
                "divider": "#DDE2E5",
                "primary": "#536B7B",
            },
            lambda content, **kwargs: ft.Container(content=content, **kwargs),
        )

        self.assertEqual(len(view.controls), 2)
        class_import_row = view.controls[0].content.controls[4]
        export_row = view.controls[1].content.controls[3]
        self.assertEqual(class_import_row.controls[0].height, 48)
        self.assertEqual(class_import_row.controls[0].width, 520)
        self.assertEqual(class_import_row.controls[2].content, "Importar turmas")
        self.assertEqual(export_row.controls[2].content, "Exportar CSV")

    def test_class_csv_buttons_select_and_import_file(self) -> None:
        class PageStub:
            def run_task(self, *_args, **_kwargs) -> None:
                pass

            def update(self) -> None:
                pass

        class FilePickerStub:
            async def pick_files(self, **kwargs):
                if "turmas" in kwargs["dialog_title"]:
                    name = "turmas.csv"
                    content = b"ano_escolar;letra\n8;B"
                else:
                    name = "alunos_2026.csv"
                    content = (
                        b"numeroprocesso,nome,datanasc,sexo,ano_escolar,letra\n"
                        b"112,Beatriz,2012-04-03,F,7,A"
                    )
                selected_file = ft.FilePickerFile(
                    id=0,
                    name=name,
                    size=len(content),
                )
                selected_file.bytes = content
                return [selected_file]

        controller = FakeAlunosTurmasController()
        view = build_csv_tools_view(
            PageStub(),
            controller,
            FilePickerStub(),
            {
                "muted": "#727B82",
                "error": "#B42318",
                "text": "#252A2E",
                "divider": "#DDE2E5",
                "primary": "#536B7B",
            },
            lambda content, **kwargs: ft.Container(content=content, **kwargs),
        )
        class_controls = view.controls[0].content.controls
        class_row_index = next(
            index
            for index, control in enumerate(class_controls)
            if isinstance(control, ft.Row)
            and any(
                getattr(item, "content", None) == "Importar turmas"
                for item in control.controls
            )
        )
        class_row = class_controls[class_row_index]
        class_file_slot = class_row.controls[0]
        class_import_status = class_controls[class_row_index + 1].content.controls[0]
        browse_button = class_file_slot.controls[0]
        self.assertIsInstance(browse_button, ft.OutlinedButton)

        asyncio.run(browse_button.on_click(None))
        chip = class_file_slot.controls[0]
        self.assertIsInstance(chip, ft.OutlinedButton)
        self.assertEqual(chip.disabled, browse_button.disabled)
        self.assertEqual(chip.height, browse_button.height)
        self.assertEqual(chip.style, browse_button.style)
        self.assertEqual(
            chip.content.controls[0].value,
            "turmas.csv",
        )
        self.assertEqual(chip.width, max(96, len("turmas.csv") * 8 + 58))
        class_chip_width = chip.width
        self.assertTrue(chip.content.controls[0].no_wrap)
        separator = chip.content.controls[1]
        self.assertIsInstance(separator, ft.Container)
        self.assertEqual(separator.width, 1)
        self.assertIsInstance(chip.content.controls[2], ft.Icon)

        chip.on_click(None)
        self.assertIsInstance(class_file_slot.controls[0], ft.OutlinedButton)
        self.assertEqual(class_import_status.value, "")

        asyncio.run(class_row.controls[1].on_click(None))
        self.assertEqual(
            class_import_status.value,
            "Selecione primeiro um ficheiro CSV.",
        )

        student_controls = view.controls[0].content.controls
        student_row_index = next(
            index
            for index, control in enumerate(student_controls)
            if isinstance(control, ft.Row)
            and any(
                getattr(item, "content", None) == "Importar alunos"
                for item in control.controls
            )
        )
        student_row = student_controls[student_row_index]
        student_file_slot = student_row.controls[0]
        student_import_status = student_controls[
            student_row_index + 1
        ].content.controls[0]

        asyncio.run(student_file_slot.controls[0].on_click(None))
        student_chip = student_file_slot.controls[0]
        self.assertIsInstance(student_chip, ft.OutlinedButton)
        self.assertEqual(
            student_chip.content.controls[0].value,
            "alunos_2026.csv",
        )
        self.assertGreater(student_chip.width, class_chip_width)
        asyncio.run(student_row.controls[1].on_click(None))

        self.assertEqual(controller.students[-1].nome, "Beatriz")
        self.assertIn("1 importados", student_import_status.value)
        self.assertIsInstance(student_file_slot.controls[0], ft.OutlinedButton)

        asyncio.run(class_file_slot.controls[0].on_click(None))
        self.assertIsInstance(class_file_slot.controls[0], ft.OutlinedButton)

        asyncio.run(class_row.controls[1].on_click(None))

        self.assertEqual(controller.classes[-1].designacao, "8.º B")
        self.assertIn("1 importados", class_import_status.value)
        self.assertIsInstance(class_file_slot.controls[0], ft.OutlinedButton)

        asyncio.run(class_row.controls[1].on_click(None))

        self.assertEqual(len(controller.classes), 2)
        self.assertEqual(
            class_import_status.value,
            "Selecione primeiro um ficheiro CSV.",
        )


if __name__ == "__main__":
    unittest.main()
