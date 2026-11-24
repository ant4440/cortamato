"""Helpers for short-lived action feedback."""

import asyncio

import flet as ft


FEEDBACK_DURATION_SECONDS = 3
_feedback_generations: dict[int, int] = {}


def show_temporary_feedback(
    page: ft.Page,
    control: ft.Text,
    message: str,
    *,
    color: str | None = None,
) -> None:
    control.value = message
    control.visible = bool(message)
    if color is not None:
        control.color = color
    if message:
        _schedule_clear(page, control)


def dismiss_temporary_dialog(
    page: ft.Page,
    dialog: ft.AlertDialog,
) -> None:
    page.run_task(_dismiss_after_delay, dialog)


def _schedule_clear(
    page: ft.Page,
    control: ft.Text,
) -> None:
    control_id = id(control)
    generation = _feedback_generations.get(control_id, 0) + 1
    _feedback_generations[control_id] = generation
    page.run_task(_clear_after_delay, page, control, generation)


async def _clear_after_delay(
    page: ft.Page,
    control: ft.Text,
    generation: int,
) -> None:
    await asyncio.sleep(FEEDBACK_DURATION_SECONDS)
    control_id = id(control)
    if _feedback_generations.get(control_id) != generation:
        return

    control.value = ""
    control.visible = False
    del _feedback_generations[control_id]
    page.update()


async def _dismiss_after_delay(dialog: ft.AlertDialog) -> None:
    await asyncio.sleep(FEEDBACK_DURATION_SECONDS)
    if dialog.open:
        dialog.open = False
        dialog.update()
