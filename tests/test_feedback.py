import unittest
from typing import cast
from unittest.mock import AsyncMock, patch

import flet as ft

from View.feedback import (
    FEEDBACK_DURATION_SECONDS,
    dismiss_temporary_dialog,
    show_temporary_feedback,
)


class TemporaryFeedbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_latest_feedback_clears_after_three_seconds(self) -> None:
        class PageStub:
            def __init__(self) -> None:
                self.tasks = []
                self.update_count = 0

            def run_task(self, handler, *args) -> None:
                self.tasks.append((handler, args))

            def update(self) -> None:
                self.update_count += 1

        page = PageStub()
        feedback = ft.Text("", visible=False)
        typed_page = cast(ft.Page, page)
        show_temporary_feedback(typed_page, feedback, "First message")
        show_temporary_feedback(typed_page, feedback, "Latest message")

        self.assertTrue(feedback.visible)
        self.assertEqual(feedback.value, "Latest message")

        with patch("View.feedback.asyncio.sleep", new=AsyncMock()) as sleep:
            first_handler, first_args = page.tasks[0]
            await first_handler(*first_args)
            self.assertEqual(feedback.value, "Latest message")

            latest_handler, latest_args = page.tasks[1]
            await latest_handler(*latest_args)

        sleep.assert_awaited_with(FEEDBACK_DURATION_SECONDS)
        self.assertEqual(FEEDBACK_DURATION_SECONDS, 3)
        self.assertFalse(feedback.visible)
        self.assertEqual(feedback.value, "")
        self.assertEqual(page.update_count, 1)

    async def test_success_dialog_dismisses_after_three_seconds(self) -> None:
        class PageStub:
            def __init__(self) -> None:
                self.tasks = []

            def run_task(self, handler, *args) -> None:
                self.tasks.append((handler, args))

        class DialogStub:
            open = True

            def update(self) -> None:
                pass

        page = PageStub()
        dialog = DialogStub()
        dismiss_temporary_dialog(
            cast(ft.Page, page),
            cast(ft.AlertDialog, dialog),
        )

        with patch("View.feedback.asyncio.sleep", new=AsyncMock()) as sleep:
            handler, args = page.tasks[0]
            await handler(*args)

        sleep.assert_awaited_once_with(FEEDBACK_DURATION_SECONDS)
        self.assertFalse(dialog.open)


if __name__ == "__main__":
    unittest.main()
