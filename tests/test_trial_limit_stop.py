"""Hardware-free checks of trial-limit stopping in the shared acquisition loop."""
import queue
import time
import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

from test_lever_modes import load_methods, Var


METHODS = load_methods("pyBEHAVIOR_v8.py", {"stop_at_trial_limit", "acquisition_loop"})
METHODS["time"] = time


def harness(limit=300, trial=300, active=None):
    app = SimpleNamespace(
        running=True, max_trials=Var(str(limit)), trial_index=trial,
        active_trial_index=active, plot_queue=queue.Queue(),
        parse_int=lambda var, default: int(var.get()),
    )
    for name in ("stop_at_trial_limit", "acquisition_loop"):
        setattr(app, name, MethodType(METHODS[name], app))
    return app


class TrialLimitStopTests(unittest.TestCase):
    def test_completed_limit_requests_gui_stop_once(self):
        app = harness()
        app.stop_at_trial_limit()
        app.stop_at_trial_limit()
        self.assertFalse(app.running)
        events = list(app.plot_queue.queue)
        self.assertEqual([kind for kind, _ in events], ["log", "stop_session"])

    def test_final_trial_must_finish_before_stopping(self):
        app = harness(active=299)
        app.stop_at_trial_limit()
        self.assertTrue(app.running)
        self.assertTrue(app.plot_queue.empty())
        app.active_trial_index = None
        app.stop_at_trial_limit()
        self.assertFalse(app.running)

    def test_unlimited_or_below_limit_keeps_recording(self):
        for limit, trial in ((0, 300), (-1, 300), (300, 299)):
            with self.subTest(limit=limit, trial=trial):
                app = harness(limit, trial)
                app.stop_at_trial_limit()
                self.assertTrue(app.running)
                self.assertTrue(app.plot_queue.empty())

    def test_pending_reminders_do_not_extend_limit(self):
        app = harness()
        app.dmts_reminder_remaining = 3
        app.stop_at_trial_limit()
        self.assertFalse(app.running)

    def test_acquisition_finishes_writing_before_requesting_stop(self):
        app = harness(active=299)
        app.rate_hz, app.callback_s = Var("1000"), Var("0.1")
        app.parse_float = lambda var, default: float(var.get())
        app.simulation_mode = Var(True)
        app.ai_task = None
        app.simulate_data = Mock(return_value=([[0]], [1.0]))
        writes = []

        def handle_data(times, rows):
            self.assertTrue(app.running)
            self.assertFalse(any(kind == "stop_session" for kind, _ in app.plot_queue.queue))
            writes.append(rows)
            if len(writes) == 2:
                app.active_trial_index = None

        app.handle_data = Mock(side_effect=handle_data)
        with patch.object(time, "sleep"):
            app.acquisition_loop()
        self.assertEqual(len(writes), 2)
        self.assertFalse(app.running)
        self.assertEqual(sum(kind == "stop_session" for kind, _ in app.plot_queue.queue), 1)


if __name__ == "__main__":
    unittest.main()
