import json
import os
import unittest

from xindi import netstrings

PAGES = os.path.join(os.path.dirname(__file__), "..", "..", "display_firmware", "pages")


class NetStringsTest(unittest.TestCase):
    def test_every_text_has_every_language(self):
        for key, row in netstrings.TEXT.items():
            self.assertEqual(len(row), len(netstrings.LANGUAGES), key)
            self.assertTrue(all(row), key)

    def test_order_matches_the_screen(self):
        self.assertEqual(netstrings.LANGUAGES[0], "zh")
        self.assertEqual(netstrings.LANGUAGES[1], "ru")
        self.assertEqual(netstrings.LANGUAGES[2], "en")

    def test_text_by_language(self):
        self.assertEqual(netstrings.text("cancel", 1), "Отмена")
        self.assertEqual(netstrings.text("cancel", 2), "Cancel")

    def test_unknown_language_is_english(self):
        self.assertEqual(netstrings.text("cancel", 99), "Cancel")
        self.assertEqual(netstrings.text("cancel", -1), "Cancel")

    def test_pages_of_the_screen_use_the_table(self):
        """tools/net_i18n.py has been run: the pages carry the texts of the table."""
        with open(os.path.join(PAGES, "net_info.json"), encoding="utf-8") as f:
            code = "\n".join(json.load(f)["root"]["events"]["codesload"])
        for text in netstrings.TEXT["network_info"]:
            self.assertIn('title.txt="%s"' % text, code)


if __name__ == "__main__":
    unittest.main()
