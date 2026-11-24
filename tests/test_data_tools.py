import inspect
import unittest
from datetime import date

import cv2
import flet as ft
from Controllers.csv_tools_controller import (
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

<<<<<<< Updated upstream
=======
    def test_boolean_values_are_not_valid_positive_numbers(self) -> None:
        with self.assertRaisesRegex(ValueError, "inválida"):
            _validar_regra_apuramento(True, True, 1, 1)

>>>>>>> Stashed changes

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
        buttons = view.content.controls[1].controls
        self.assertEqual(
            [button.content for button in buttons],
            ["Selecionar imagem", "Usar câmara"],
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
            },
            lambda content, **kwargs: ft.Container(content=content, **kwargs),
        )

        self.assertEqual(len(view.controls), 2)
        import_controls = view.controls[0].content.controls
        class_import_row = import_controls[4]
        student_import_row = import_controls[8]
        export_row = view.controls[1].content.controls[3]
        self.assertEqual(class_import_row.controls[0].height, 48)
        self.assertEqual(class_import_row.controls[0].width, 520)
        self.assertEqual(class_import_row.controls[2].content, "Importar turmas")
        for button in (
            class_import_row.controls[1],
            class_import_row.controls[2],
            student_import_row.controls[1],
            student_import_row.controls[2],
        ):
            self.assertTrue(inspect.iscoroutinefunction(button.on_click))
        self.assertEqual(export_row.controls[2].content, "Exportar CSV")


if __name__ == "__main__":
    unittest.main()
