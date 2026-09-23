import math
import random
import tempfile
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import Mock
import unittest

from test_lever_modes import load_methods, Var
from test_dmts_choices import harness
from test_dmts_protocol_generator import GeneratorHarness
import protocol_generator as pg


NAMES = {"start_active_dmts_trial", "choose_dmts_trial_sound_ids",
         "generate_sequence", "_parse_number_list", "consume_next_dmts_trial_type",
         "nwb_contract_trial_anchor_s", "nwb_contract_hmcf", "nwb_contract_trial_type"}
METHODS = load_methods("pyBEHAVIOR_v7.py", NAMES)
METHODS.update(math=math, random=random)


class DMTSBlankTests(unittest.TestCase):
    def test_blank_is_silent_records_licks_and_keeps_normal_timing(self):
        app, row = harness()
        for name in ("start_active_dmts_trial", "choose_dmts_trial_sound_ids"):
            setattr(app, name, MethodType(METHODS[name], app))
        app.sound_duration_s, app.delay_s = Var("0.2"), Var("1")
        app.response_window_s, app.reward_delay_s, app.pulse_ms = Var("1"), Var("0.1"), Var("40")
        app.parse_float = lambda var, default: float(var.get())
        app.trial_index = 1
        app.start_trial_state_interval = Mock()
        app.play_sound_on_crossing = Var(True)
        app.play_loaded_sound = Mock()
        row["TrialType"] = "0 DMTS-blank"
        self.assertEqual(app.choose_dmts_trial_sound_ids(0), (0, 0))
        app.start_active_dmts_trial(0, 2, 0, 0)
        app.update_active_dmts_trial(1.2, False, False, False)
        app.update_active_dmts_trial(1.5, False, False, False, ["left", "right"] * 3)
        self.assertEqual((row["left_lick_count"], row["right_lick_count"]), (3, 3))
        self.assertEqual(row["choice_side"], "")
        app.update_active_dmts_trial(2.5, False, False, False)
        self.assertEqual(row["ResultType"], "BLANK")
        self.assertEqual([row[key] for key in ("HIT", "MISS", "CR", "FA")], [0, 0, 0, 0])
        app.play_loaded_sound.assert_not_called()
        app.maybe_send_go_reward.assert_not_called()
        self.assertAlmostEqual(app.active_trial_end_s, 2.54)
        app.apply_trial_timeout(row, 2.54)
        self.assertAlmostEqual(app.next_trial_allowed_time_s, 4.54)

    def test_blank_irfork_does_not_abort_on_fork_release(self):
        app, row = harness(lick=False)
        app.active_dmts_sample_sound_id = app.active_dmts_test_sound_id = 0
        app.active_dmts_low_start_s = 0.1
        app.finish_active_dmts_miss = Mock()
        app.update_active_dmts_trial(0.9, False, False, False)
        app.finish_active_dmts_miss.assert_not_called()
        app.finish_active_dmts_reward_period(2.5)
        self.assertEqual(row["ResultType"], "BLANK")
        app.maybe_send_go_reward.assert_not_called()

    def test_runtime_weighted_sequences_and_legacy_zero_blank(self):
        for values, weights, expected in (
            ("1 2 0", "0 0 1", {0}),
            ("1 2 0", "1 0 0", {1}),
            ("1 2 0", "0 1 0", {2}),
            ("1 2", "1 1", {1, 2}),
            ("1 2 0", "1 1 1", {0, 1, 2}),
        ):
            with self.subTest(weights=weights):
                app = SimpleNamespace(
                    sequence_values=Var(values), sequence_weights=Var(weights),
                    sequence_length=Var("300"), random_seed=Var("0"),
                    is_dmts_task=lambda: True, parse_int=lambda var, default: int(var.get()),
                    update_sequence_display=Mock(), log=Mock(),
                    ensure_sequence_controls=Mock(),
                )
                for name in ("generate_sequence", "_parse_number_list"):
                    setattr(app, name, MethodType(METHODS[name], app))
                app.generate_sequence()
                self.assertEqual(set(app.sound_sequence), expected)
                self.assertEqual(app.sequence_values.get(), "1 2 0")
        self.assertEqual(METHODS["consume_next_dmts_trial_type"](SimpleNamespace(consume_next_sound_id=lambda: 0)), 0)

    def test_protocol_three_weights_round_trip(self):
        app = GeneratorHarness()
        for key, value in (("DMTSMatchWeight", "4"), ("DMTSNonMatchWeight", "4"), ("DMTSBlankWeight", "2")):
            app.variables[key].set(value)
        self.assertEqual(app.validate(), [])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "blanks.dat"
            app.save(path)
            self.assertEqual(pg.read_dat(path)["BlankWeight"], "2")
            loaded = GeneratorHarness()
            loaded.load(path)
            self.assertEqual(loaded.variables["DMTSBlankWeight"].get(), "2")
            loaded.load(Path(pg.APP_DIR) / "protocols/dmts_licks_parameters_matchonly_allsounds.dat")
            self.assertEqual(loaded.variables["DMTSBlankWeight"].get(), "0")

    def test_invalid_weights_rejected(self):
        for value in ("-1", "nan", "inf", "bad"):
            app = GeneratorHarness()
            app.variables["DMTSBlankWeight"].set(value)
            self.assertTrue(app.validate())
        app = GeneratorHarness()
        for key in ("DMTSMatchWeight", "DMTSNonMatchWeight", "DMTSBlankWeight"):
            app.variables[key].set("0")
        self.assertTrue(app.validate())

    def test_blank_export_uses_trial_start_not_nearby_sound(self):
        row = {"TrialType": "0 DMTS-blank", "ResultType": "BLANK", "sound_id": 0, "trigger_time_s": "2"}
        self.assertEqual(METHODS["nwb_contract_trial_anchor_s"](None, row, [{"sound_id": 1, "start_s": 2.1}]), 2)
        self.assertEqual(METHODS["nwb_contract_trial_type"](None, row), 0)
        self.assertEqual(METHODS["nwb_contract_hmcf"](None, row), "")


if __name__ == "__main__":
    unittest.main()
