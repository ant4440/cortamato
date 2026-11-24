"""Application entry point."""

import flet as ft  # type: ignore[import-not-found]

from View.app import create_app


if __name__ == "__main__":
    ft.run(create_app)
