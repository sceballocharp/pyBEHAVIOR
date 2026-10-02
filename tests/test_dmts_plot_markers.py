"""Check visible timing boundaries without GUI or acquisition hardware."""
from types import SimpleNamespace, MethodType
from unittest.mock import Mock
import unittest

from test_lever_modes import load_methods


DRAW = load_methods("pyBEHAVIOR_v7.py", {"draw_dmts_window_markers"})["draw_dmts_window_markers"]


class DMTSPlotMarkerTests(unittest.TestCase):
    def app(self, windows, dmts=True):
        app = SimpleNamespace(dmts_plot_windows=windows, plot_canvas=Mock(),
                              is_dmts_task=lambda: dmts)
        app.draw = MethodType(DRAW, app)
        return app

    def test_clips_shading_and_only_draws_visible_boundaries(self):
        app = self.app([(1, 4, 5), (-10, -8, -7), (12, 14, 15)])
        app.draw(2, 6, 40, 12, 400, 200)
        app.plot_canvas.create_rectangle.assert_called_once_with(
            40, 12, 240, 200, fill="#fff0db", outline="", tags=("plot_dynamic",))
        self.assertEqual(app.plot_canvas.create_line.call_count, 2)
        self.assertEqual(app.plot_canvas.create_line.call_args_list[0].args, (240, 12, 240, 200))
        self.assertEqual(app.plot_canvas.create_line.call_args_list[1].args, (340, 182, 340, 191))

    def test_other_tasks_and_zero_time_span_draw_nothing(self):
        for dmts, end in ((False, 6), (True, 2)):
            app = self.app([(1, 4, 5)], dmts)
            app.draw(2, end, 40, 12, 400, 200)
            self.assertEqual(app.plot_canvas.mock_calls, [])


if __name__ == "__main__":
    unittest.main()
