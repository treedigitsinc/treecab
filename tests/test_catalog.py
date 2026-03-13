import unittest

from od_draw.catalog.kcd_catalog import get_prefixed_code, lookup


class CatalogTests(unittest.TestCase):
    def test_lookup_returns_expected_entry(self) -> None:
        entry = lookup("BW-B30")
        self.assertEqual(entry.width, 30)
        self.assertEqual(entry.height, 34.5)

    def test_prefixed_code(self) -> None:
        self.assertEqual(get_prefixed_code("OW", "W2436"), "OW-W2436")


if __name__ == "__main__":
    unittest.main()
