"""Standalone QR reader application."""

import argparse
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import flet as ft

from View.data_tools_view import build_qr_reader_view


PROJECT_DIRECTORY = Path(__file__).resolve().parent
PROJECT_WEB_DIRECTORY = PROJECT_DIRECTORY / "web"
STANDALONE_WEB_DIRECTORY = PROJECT_DIRECTORY.parent / "cortamato-web"
WEB_DIRECTORY = Path(
    os.getenv(
        "QR_WEB_DIRECTORY",
        str(
            STANDALONE_WEB_DIRECTORY
            if STANDALONE_WEB_DIRECTORY.is_dir()
            else PROJECT_WEB_DIRECTORY
        ),
    )
).expanduser()

PALETTE = {
    "background": "#F7F8F9",
    "surface": "#FCFCFB",
    "text": "#252A2E",
    "muted": "#727B82",
    "primary": "#536B7B",
    "error": "#B42318",
}


def create_qr_app(page: ft.Page, allow_camera: bool = True) -> None:
    page.title = "Cortamato — Leitor QR"
    page.bgcolor = PALETTE["background"]
    page.padding = 12
    page.theme_mode = ft.ThemeMode.LIGHT

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    mobile = page.platform in {
        ft.PagePlatform.IOS,
        ft.PagePlatform.ANDROID,
    }
    allow_camera = allow_camera and not mobile
    viewer = build_qr_reader_view(
        page,
        file_picker,
        PALETTE,
        lambda content, **kwargs: ft.Container(
            content=content,
            bgcolor=PALETTE["surface"],
            border=ft.Border.all(1, "#E1E5E8"),
            border_radius=12,
            padding=kwargs.pop("padding", 16),
            width=None,
        ),
        allow_camera=allow_camera,
    )

    page.add(
        ft.Column(
            [
                ft.Text(
                    "Leitor QR code",
                    size=25,
                    weight=ft.FontWeight.W_600,
                    color=PALETTE["text"],
                ),
                ft.Text(
                    "Aplicação autónoma do Cortamato",
                    size=13,
                    color=PALETTE["muted"],
                ),
                viewer,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=10,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Leitor QR standalone do Cortamato")
    parser.add_argument(
        "--web",
        action="store_true",
        help="Alojar a versão web móvel.",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Interface de rede a escutar (padrão: HOST ou 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8550")),
        help="Porta HTTP (padrão: PORT ou 8550).",
    )
    arguments = parser.parse_args()

    if arguments.web:
        if not (WEB_DIRECTORY / "qr-mobile.html").is_file():
            raise SystemExit(
                "Não foi encontrada a aplicação web. Coloque os ficheiros em "
                f"'{WEB_DIRECTORY}' ou defina QR_WEB_DIRECTORY."
            )
        with ThreadingHTTPServer(
            (arguments.host, arguments.port),
            lambda *args, **kwargs: SimpleHTTPRequestHandler(
                *args,
                directory=str(WEB_DIRECTORY),
                **kwargs,
            ),
        ) as server:
            print(
                f"Leitor QR disponível em http://{arguments.host}:{server.server_port}/qr-mobile.html"
            )
            server.serve_forever()
    else:
        ft.run(create_qr_app)


if __name__ == "__main__":
    main()
