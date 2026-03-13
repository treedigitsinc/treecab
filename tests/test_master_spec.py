import unittest

from od_draw.catalog.master_catalog import get_full_code, is_valid_combo, lookup
from od_draw.models.master import PDFCalibration, Point2D, Rect


class MasterSpecTests(unittest.TestCase):
    def test_master_catalog_lookup_and_validation(self) -> None:
        entry = lookup("OW-W3036")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.width, 30)
        self.assertTrue(is_valid_combo("OW", "W3036"))
        self.assertEqual(get_full_code("OW", "W3036"), "OW-W3036")

    def test_pdf_calibration_derives_pixels_per_inch(self) -> None:
        calibration = PDFCalibration(
            pdf_point_a=Point2D(100, 100),
            pdf_point_b=Point2D(300, 100),
            model_point_a=Point2D(0, 0),
            model_point_b=Point2D(120, 0),
            known_distance=120,
        )
        self.assertAlmostEqual(calibration.pixels_per_inch, 200 / 120, places=6)
        self.assertEqual(len(calibration.transform_matrix), 6)

    def test_rect_contains_point(self) -> None:
        rect = Rect(0, 0, 24, 18)
        self.assertTrue(rect.contains_point(Point2D(12, 9)))
        self.assertFalse(rect.contains_point(Point2D(25, 9)))


if __name__ == "__main__":
    unittest.main()
