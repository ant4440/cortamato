import unittest

from PIL import Image

from View.image_crop import create_square_crop_canvas, minimum_crop_zoom


class ImageCropTests(unittest.TestCase):
    def test_minimum_zoom_fits_the_full_image_inside_square_crop(self) -> None:
        self.assertEqual(minimum_crop_zoom((160, 90)), 90 / 160)
        self.assertEqual(minimum_crop_zoom((100, 100)), 1)

    def test_square_canvas_centers_wide_image_with_transparent_padding(self) -> None:
        source = Image.new("RGBA", (4, 2), (255, 0, 0, 255))

        canvas = create_square_crop_canvas(source)

        self.assertEqual(canvas.size, (4, 4))
        self.assertEqual(canvas.getpixel((0, 0))[3], 0)
        self.assertEqual(canvas.getpixel((0, 1)), (255, 0, 0, 255))
        self.assertEqual(canvas.getpixel((3, 2)), (255, 0, 0, 255))


if __name__ == "__main__":
    unittest.main()
