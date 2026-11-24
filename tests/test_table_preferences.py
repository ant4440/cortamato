import unittest
from types import SimpleNamespace

import flet as ft

from View.competition_records_view import _build_management_table


class TablePreferenceTests(unittest.TestCase):
    def build_table(self, hide_ids: bool) -> ft.Control:
        class PageStub:
            def update(self) -> None:
                pass

        record = SimpleNamespace(id=12, name="Ana")
        return _build_management_table(
            PageStub(),
            {
                "muted": "#727B82",
                "error": "#B42318",
                "text": "#252A2E",
                "surface": "#FFFFFF",
                "table_line": "#DDE2E5",
            },
            lambda content, **kwargs: ft.Container(content=content, **kwargs),
            ["ID", "Nome"],
            lambda: [record],
            lambda item: item.id,
            lambda item: [str(item.id), item.name],
            lambda *_args: None,
            None,
            "registo",
            "registos",
            "Sem registos",
            "",
            read_only=True,
            hide_ids=hide_ids,
        )

    def test_hide_ids_removes_id_header_and_cells(self) -> None:
        view = self.build_table(hide_ids=True)
        table = view.controls[1].content.controls[2].controls[0]

        self.assertEqual(
            [column.label.value for column in table.columns],
            ["Nome", ""],
        )
        self.assertEqual(len(table.rows[0].cells), 2)
        self.assertEqual(table.rows[0].cells[0].content.value, "Ana")

    def test_ids_remain_visible_when_preference_is_off(self) -> None:
        view = self.build_table(hide_ids=False)
        table = view.controls[1].content.controls[2].controls[0]

        self.assertEqual(
            [column.label.value for column in table.columns],
            ["ID", "Nome", ""],
        )
        self.assertEqual(len(table.rows[0].cells), 3)
        self.assertEqual(table.rows[0].cells[0].content.value, "12")


if __name__ == "__main__":
    unittest.main()
