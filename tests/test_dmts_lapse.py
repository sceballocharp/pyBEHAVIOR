"""Hardware-free checks of lapse recovery and automatic stop requests."""
import queue
import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import Mock

from test_lever_modes import load_methods
from test_dmts_pavlov import pavlov_harness

METHODS = load_methods("pyBEHAVIOR_v7.py", {
    "update_dmts_lapse_state", "consume_next_dmts_trial_type",
})


def harness():
    app = SimpleNamespace(
        is_lick_trigger=lambda: True, plot_queue=queue.Queue(), running=True,
        dmts_match_miss_streak=0, dmts_reminder_remaining=0,
        dmts_reminder_engaged=False, active_dmts_reminder=False,
        active_left_lick_count=0, active_right_lick_count=0,
        consume_next_sound_id=Mock(return_value=2),
    )
    for name in ("update_dmts_lapse_state", "consume_next_dmts_trial_type"):
        setattr(app, name, MethodType(METHODS[name], app))
    return app


def finish(app, result="MISS", trial_type="DMTS-match"):
    app.update_dmts_lapse_state({"trial": 1, "TrialType": trial_type, "ResultType": result})


class DMTSLapseTests(unittest.TestCase):
    def test_fifth_match_miss_starts_three_matches_without_consuming_sequence(self):
        app = harness()
        for _ in range(4):
            finish(app)
        self.assertEqual(app.dmts_reminder_remaining, 0)
        finish(app, "CR", "DMTS-nonmatch")
        finish(app, "BLANK", "DMTS-blank")
        finish(app)
        self.assertEqual(app.dmts_reminder_remaining, 3)
        self.assertEqual(app.consume_next_dmts_trial_type(), 1)
        app.consume_next_sound_id.assert_not_called()

    def test_match_response_resets_streak_and_irfork_is_unaffected(self):
        app = harness()
        finish(app)
        finish(app, "FA")
        self.assertEqual(app.dmts_match_miss_streak, 0)
        app.is_lick_trigger = lambda: False
        for _ in range(6):
            finish(app)
        self.assertEqual(app.dmts_reminder_remaining, 0)

    def test_stops_only_after_third_unresponsive_reminder(self):
        app = harness()
        app.active_dmts_reminder = True
        app.dmts_reminder_remaining = 3
        for _ in range(2):
            finish(app)
            self.assertTrue(app.running)
        finish(app)
        self.assertFalse(app.running)
        self.assertTrue(app.dmts_lapse_stop_requested)
        self.assertEqual(app.dmts_reminder_remaining, 0)

    def test_either_side_lick_resumes_normal_sequence_after_three_trials(self):
        for side in ("left", "right"):
            app = harness()
            app.active_dmts_reminder = True
            app.dmts_reminder_remaining = 3
            setattr(app, f"active_{side}_lick_count", 1)
            finish(app)
            setattr(app, f"active_{side}_lick_count", 0)
            finish(app)
            finish(app)
            self.assertTrue(app.running)
            self.assertEqual(app.consume_next_dmts_trial_type(), 2)
            self.assertEqual(app.dmts_match_miss_streak, 0)

    def test_reminder_overrides_zero_pavlov_without_duplicate_reward(self):
        app, row = pavlov_harness(probability=0)
        app.active_dmts_reminder = True
        app.finish_active_dmts_reward_period(2.5)
        app.finish_active_dmts_reward_period(2.6)
        app.send_output_pulse.assert_called_once_with(from_worker=True, start_s=2.5)
        self.assertEqual(row["ResultType"], "MISS")

    def test_reminder_respects_disabled_output(self):
        app, _ = pavlov_harness(probability=0)
        app.active_dmts_reminder = True
        app.trigger_output_on_crossing.set(False)
        app.finish_active_dmts_reward_period(2.5)
        app.send_output_pulse.assert_not_called()
