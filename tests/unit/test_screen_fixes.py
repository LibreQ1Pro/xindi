"""Faults found in use: values that stayed "---", positions of axes that are not homed, a message lost on a page that is shown again."""
import unittest
import unittest.mock

from xindi import state as g
from xindi.pages import move, printing, refresh
from support import PortRecorder


class ScreenFixesTest(PortRecorder):
    def test_the_position_of_an_axis_that_is_not_homed_is_not_shown(self):
        g.klippy.homed_axes = "xy"
        g.klippy.x_position, g.klippy.y_position, g.klippy.z_position = 12.5, 30.0, 0.0
        move.move_page()
        sent = self.sent()
        self.assertIn('x_pos.txt="12.5"', " ".join(sent).replace("12.50", "12.5"))
        self.assertIn('z_pos.txt="%s"' % move.UNKNOWN_POSITION, sent)

    def test_nothing_is_homed_yet(self):
        g.klippy.homed_axes = ""
        move.move_page()
        self.assertEqual([c for c in self.sent() if c.endswith('_pos.txt="%s"' % move.UNKNOWN_POSITION)], ['x_pos.txt="---.--"', 'y_pos.txt="---.--"', 'z_pos.txt="---.--"'])

    def test_speed_and_flow_are_written_again_on_a_page_that_is_shown_anew(self):
        g.klippy.gcode_move_speed_factor, g.klippy.gcode_move_extrude_factor = 1.0, 0.95
        printing.printing_second_page()
        self.assertIn('speed_val.txt="100"', self.sent())
        self.assertIn('flow_val.txt="95"', self.sent())
        self.commands.clear()
        printing.printing_second_page()                                # nothing changed: nothing is sent
        self.assertNotIn('speed_val.txt="100"', self.sent())
        self.port.page("36")                                           # a page shown anew forgets its values
        self.commands.clear()
        printing.printing_second_page()
        self.assertIn('speed_val.txt="100"', self.sent())

    def test_the_failure_message_is_written_again_when_the_page_is_reopened(self):
        g.klippy.webhooks_state_message = "Printer is shutdown"
        refresh.show_failure_message()
        self.assertTrue(any(c.startswith("err_msg.txt=") for c in self.sent()))
        self.commands.clear()
        self.port.page("77")                                           # the page is opened again: its text is gone
        self.commands.clear()
        refresh.show_failure_message()
        self.assertTrue(any(c.startswith("err_msg.txt=") for c in self.sent()))


class CentredNameTest(PortRecorder):
    def lines(self, text):
        return text.split("\\r")

    def test_a_shorter_line_is_moved_to_the_middle_of_the_block_with_spaces(self):
        # the screen puts the block where the alignment says and starts every line at the left edge of the block
        from xindi.screen.text import fit_name, width
        lines = self.lines(fit_name("a_fairly_long_model_name_that_needs_two_lines.gcode", 108, lines=2, center=True))
        self.assertEqual(len(lines), 2)
        widths = [width(line.lstrip(" ")) for line in lines]
        pads = [len(line) - len(line.lstrip(" ")) for line in lines]
        widest = widths.index(max(widths))
        self.assertEqual(pads[widest], 0)                                     # the widest line starts the block
        other = 1 - widest
        self.assertAlmostEqual(pads[other] * width(" "), (widths[widest] - widths[other]) / 2, delta=width(" "))
        self.assertLessEqual(max(pads[i] * width(" ") + widths[i] for i in (0, 1)), 108)

    def test_without_center_nothing_is_added(self):
        from xindi.screen.text import fit_name
        self.assertNotIn("\\r ", fit_name("a_fairly_long_model_name_that_needs_two_lines.gcode", 108, lines=2))


class ListPictureTest(PortRecorder):
    def test_the_list_thumbnail_is_a_multiple_of_16_and_420(self):
        # the screen draws the rows of a JPEG whose width is not a multiple of 16 sheared (a staircase)
        import io
        from PIL import Image
        from xindi.screen import thumbnail
        png = io.BytesIO()
        Image.new("RGB", (160, 160), (200, 50, 50)).save(png, "PNG")
        thumb = thumbnail.Thumbnail("PNG", 160, 160, png.getvalue())
        with unittest.mock.patch.object(thumbnail, "get_thumbnails", return_value=[thumb]):
            data = thumbnail.jpeg("any.gcode", thumbnail.LIST_SIZE)
        image = Image.open(io.BytesIO(data))
        self.assertEqual(image.size, (thumbnail.LIST_SIZE, thumbnail.LIST_SIZE))
        self.assertEqual(thumbnail.LIST_SIZE % 16, 0)
        from PIL import JpegImagePlugin
        self.assertEqual(JpegImagePlugin.get_sampling(image), 2)        # 4:2:0


if __name__ == "__main__":
    unittest.main()
