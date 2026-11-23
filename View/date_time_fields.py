"""Date and time picker buttons for text fields."""

from datetime import date, datetime, time

import flet as ft


def _parse_datetime(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value or "")
    except ValueError:
        return None


def _current_date(value: str | None) -> datetime:
    return _parse_datetime(value) or datetime.now()


def _current_time(value: str | None) -> time:
    parsed_datetime = _parse_datetime(value)
    if parsed_datetime is not None:
        return parsed_datetime.time()
    try:
        return time.fromisoformat(value or "")
    except ValueError:
        return datetime.now().time()


def add_date_time_pickers(
    page: ft.Page,
    field: ft.TextField,
    *,
    include_date: bool = True,
    include_time: bool = True,
    minimum_date: date | None = None,
) -> None:
    buttons: list[ft.Control] = []

    if include_date:
        def picker_date() -> datetime:
            current = _current_date(field.value)
            if minimum_date is not None and current.date() < minimum_date:
                return datetime.combine(minimum_date, time.min)
            return current

        date_picker = ft.DatePicker(
            value=picker_date(),
            first_date=datetime.combine(minimum_date or date(1900, 1, 1), time.min),
            last_date=datetime(9999, 12, 31),
            on_change=lambda event: update_date(event),
        )

        def open_date_picker(_: object) -> None:
            date_picker.value = picker_date()
            page.show_dialog(date_picker)

        def update_date(event: ft.Event[ft.DatePicker]) -> None:
            selected = event.control.value
            if selected is None:
                return
            selected_date = selected.date() if isinstance(selected, datetime) else selected
            if include_time:
                current = _parse_datetime(field.value)
                selected_time = current.time() if current else time.min
                field.value = datetime.combine(
                    selected_date,
                    selected_time,
                ).isoformat(sep=" ", timespec="minutes")
            else:
                field.value = selected_date.isoformat()
            page.update()

        buttons.append(
            ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                icon_size=18,
                tooltip="Selecionar data",
                width=36,
                height=36,
                on_click=open_date_picker,
            )
        )

    if include_time:
        time_picker = ft.TimePicker(
            value=_current_time(field.value),
            hour_format=ft.TimePickerHourFormat.H24,
            on_change=lambda event: update_time(event),
        )

        def open_time_picker(_: object) -> None:
            time_picker.value = _current_time(field.value)
            page.show_dialog(time_picker)

        def update_time(event: ft.Event[ft.TimePicker]) -> None:
            selected_time = event.control.value
            if selected_time is None:
                return
            if include_date:
                current = _parse_datetime(field.value)
                selected_date = current.date() if current else date.today()
                field.value = datetime.combine(
                    selected_date,
                    selected_time,
                ).isoformat(sep=" ", timespec="minutes")
            else:
                field.value = selected_time.strftime("%H:%M")
            page.update()

        buttons.append(
            ft.IconButton(
                icon=ft.Icons.ACCESS_TIME,
                icon_size=18,
                tooltip="Selecionar hora",
                width=36,
                height=36,
                on_click=open_time_picker,
            )
        )

    field.suffix_icon = ft.Row(
        buttons,
        spacing=0,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
