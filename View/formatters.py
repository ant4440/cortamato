"""Formatting helpers for values displayed in the interface."""

from datetime import timedelta


def format_numeroprocesso(value: int) -> str:
    return f"{value:05d}"


def format_tempo_chegada(value: timedelta | None) -> str:
    if value is None:
        return "—"
    total_microseconds = (
        (value.days * 24 * 60 * 60 + value.seconds) * 1_000_000
        + value.microseconds
    )
    minutes, remaining_microseconds = divmod(total_microseconds, 60_000_000)
    seconds, remaining_microseconds = divmod(remaining_microseconds, 1_000_000)
    milliseconds = remaining_microseconds // 1_000
    return f"{minutes}:{seconds:02d}.{milliseconds:03d}"
