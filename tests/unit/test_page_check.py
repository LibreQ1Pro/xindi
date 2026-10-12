"""The service asks the screen which page it shows and switches again when it is not the one it works for."""
import unittest
from unittest.mock import patch

from xindi import state as g
from xindi.screen import navigation
from support import PortRecorder


class PageCheckTest(PortRecorder):
    def setUp(self):
        super().setUp()
        self.now = [100.0]
        clock = patch.object(navigation.time, "monotonic", side_effect=lambda: self.now[0])
        clock.start()
        self.addCleanup(clock.stop)
        g.screen.page, g.screen.page_mismatch, g.screen.page_switched_at = 17, 0, 90.0

    def test_the_right_page_is_left_alone(self):
        self.assertFalse(navigation.page_reported(17))
        self.assertEqual(self.sent(), [])

    def test_a_wrong_page_is_asked_about_again_and_then_switched(self):
        self.assertFalse(navigation.page_reported(29))           # once may be a switch in progress
        self.assertEqual(self.sent(), ["sendme"])
        self.assertTrue(navigation.page_reported(29))             # twice: the screen is on the wrong page
        self.assertEqual(self.sent()[-1], "page 17")

    def test_the_answer_right_after_a_switch_is_about_the_old_page(self):
        navigation.page_to(36)
        self.commands.clear()
        self.now[0] += 0.5
        self.assertFalse(navigation.page_reported(17))
        self.assertFalse(navigation.page_reported(17))
        self.assertEqual(self.sent(), [])

    def test_one_right_answer_forgets_the_wrong_ones(self):
        navigation.page_reported(29)
        navigation.page_reported(17)
        self.assertFalse(navigation.page_reported(29))            # starts counting again
        self.assertEqual(g.screen.page_mismatch, 1)


if __name__ == "__main__":
    unittest.main()
