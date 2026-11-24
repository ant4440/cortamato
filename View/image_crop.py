"""Image helpers for square profile-photo cropping."""

from PIL import Image


def minimum_crop_zoom(image_size: tuple[int, int]) -> float:
    width, height = image_size
    if width <= 0 or height <= 0:
        raise ValueError("A imagem selecionada não é válida.")
    return min(width, height) / max(width, height)


def create_square_crop_canvas(image: Image.Image) -> Image.Image:
    width, height = image.size
    canvas_size = max(width, height)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    canvas.paste(
        image.convert("RGBA"),
        ((canvas_size - width) // 2, (canvas_size - height) // 2),
    )
    return canvas
