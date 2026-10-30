"""Hardware-free checks of SmartTask transitions and its five-match Pavlov block."""
import queue
import random
import math
import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import Mock

from test_lever_modes import load_methods, Var
from test_dmts_pavlov import pavlov_harness


METHODS = load_methods("pyBEHAVIOR_v8.py", {
    "update_smart_task", "prepare_smart_task_trial", "update_dmts_lapse_state", "generate_sequence",
})
METHODS["random"] = random
METHODS["math"] = math


def harness():
    app = SimpleNamespace(
        smart_task=Var(True), smart_task_active=False, smart_task_pavlov_remaining=0,
        active_trial_index=None, is_dmts_task=lambda: True,
        get_match_go_hit_rate=Mock(return_value=0.6),
        pavlov=Var("0"), sequence_values=Var("1 2 0"),
        sequence_weights=Var("0.5 0.5 0"),
        sound_sequence=[1, 2] * 150, sound_sequence_index=20,
        update_sequence_display=Mock(), plot_queue=queue.Queue(),
        dmts_reminder_remaining=3, dmts_match_miss_streak=5,
        sequence_length=Var("300"), random_seed=Var("42"),
        ensure_sequence_controls=Mock(), get_dmts_modality_probabilities=lambda: [1, 0],
        parse_int=lambda var, default: int(var.get()),
        _parse_number_list=lambda text, default, cast: [cast(value) for value in text.split()],
    )
    for name in ("update_smart_task", "prepare_smart_task_trial", "update_dmts_lapse_state", "generate_sequence"):
        setattr(app, name, MethodType(METHODS[name], app))
    return app


class SmartTaskTests(unittest.TestCase):
    def test_drop_starts_recovery_and_does_not_rearm_while_low(self):
        app = harness()
        app.update_smart_task()
        self.assertTrue(app.smart_task_active)
        self.assertEqual(app.sequence_weights.get(), "0.8 0.2 0.0")
        self.assertEqual(app.sound_sequence_index, 0)
        expected = random.Random(42).choices([1, 2, 0], weights=[0.8, 0.2, 0], k=300)
        self.assertEqual(app.sound_sequence, expected)
        self.assertEqual(app.pavlov.get(), "1")
        self.assertEqual(app.dmts_reminder_remaining, 0)
        app.smart_task_pavlov_remaining = 2
        app.update_smart_task()
        self.assertEqual(app.smart_task_pavlov_remaining, 2)

    def test_only_next_five_matches_get_pavlov_including_fifth(self):
        app = harness()
        app.update_smart_task()
        for index in range(6):
            nonmatch = {"TrialType": "DMTS-nonmatch"}
            app.prepare_smart_task_trial(nonmatch)
            self.assertEqual(nonmatch["smart_task_pavlov"], 0)
            row = {"TrialType": "DMTS-match"}
            app.prepare_smart_task_trial(row)
            self.assertEqual(row["smart_task_pavlov"], int(index < 5))
            reward_app, reward_row = pavlov_harness(probability=0)
            reward_row.update(row)
            reward_app.maybe_send_pavlov_reward(reward_row, 2.5)
            self.assertEqual(reward_app.send_output_pulse.call_count, int(index < 5))
        self.assertEqual(app.smart_task_pavlov_remaining, 0)

    def test_recovery_at_exact_threshold_restores_balance_and_can_retrigger(self):
        app = harness()
        app.update_smart_task()
        app.get_match_go_hit_rate.return_value = 0.65
        app.update_smart_task()
        self.assertFalse(app.smart_task_active)
        self.assertTrue(app.smart_task.get())
        self.assertEqual(app.sequence_weights.get(), "0.5 0.5 0.0")
        self.assertEqual(app.pavlov.get(), "0")
        expected = random.Random(42).choices([1, 2, 0], weights=[0.5, 0.5, 0], k=300)
        self.assertEqual(app.sound_sequence, expected)
        app.get_match_go_hit_rate.return_value = 0.64
        app.update_smart_task()
        self.assertEqual(app.smart_task_pavlov_remaining, 5)

    def test_disabled_non_dmts_no_data_or_active_trial_does_not_activate(self):
        for condition in ("disabled", "other_task", "no_data", "active"):
            app = harness()
            if condition == "disabled":
                app.smart_task.set(False)
            elif condition == "other_task":
                app.is_dmts_task = lambda: False
            elif condition == "no_data":
                app.get_match_go_hit_rate.return_value = None
            else:
                app.active_trial_index = 1
            app.update_smart_task()
            self.assertFalse(app.smart_task_active)

    def test_unchecking_restores_balance(self):
        app = harness()
        app.update_smart_task()
        app.smart_task.set(False)
        app.update_smart_task()
        self.assertFalse(app.smart_task_active)
        self.assertEqual(app.sequence_weights.get(), "0.5 0.5 0.0")

    def test_transition_discards_pair_prepared_with_old_weights(self):
        app = harness()
        app._dmts_trial_pending = {"trial_type": 2}
        app._dmts_light_pending = {"trial_type": 2}
        app.dmts_light_client = Mock()
        app.update_smart_task()
        app.dmts_light_client.reset.assert_called_once()
        self.assertIsNone(app._dmts_trial_pending)
        self.assertIsNone(app._dmts_light_pending)

    def test_legacy_reminders_do_not_override_smart_task(self):
        app = harness()
        app.update_dmts_lapse_state({"TrialType": "DMTS-match", "ResultType": "MISS"})
        self.assertEqual(app.dmts_match_miss_streak, 5)


if __name__ == "__main__":
    unittest.main()
