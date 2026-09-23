import queue
from types import SimpleNamespace, MethodType
import unittest
from unittest.mock import Mock

from test_lever_modes import load_methods


NAMES = {
    "get_dmts_lick_crossings", "record_dmts_lick_choices", "update_active_dmts_trial",
    "finish_active_dmts_response", "finish_active_dmts_reward_period",
    "get_reward_output_side", "apply_trial_timeout",
    "is_active_dmts_blank",
}
METHODS = load_methods("pyBEHAVIOR_v7.py", NAMES)


def harness(match=True, lick=True, minimum=2):
    row = {"trial": 1, "TrialType": "DMTS-match" if match else "DMTS-nonmatch"}
    app = SimpleNamespace(
        active_dmts_sample_sound_id=1, active_dmts_test_sound_id=1 if match else 2,
        active_dmts_test_sound_time_s=1.2, active_dmts_low_start_s=None,
        active_dmts_test_sound_played=True, active_dmts_scored=False,
        active_dmts_response_start_s=1.4, active_dmts_response_end_s=2.4,
        active_dmts_reward_start_s=2.5, active_trial_end_s=2.54,
        active_dmts_response_started=False, active_dmts_response_evaluated=False,
        active_left_lick_count=0, active_right_lick_count=0, active_lick_count=0,
        active_choice_side="", active_high_start_s=None, active_crossing_total_s=0,
        active_trial_base_iti_s=2, plot_queue=queue.Queue(),
        is_lick_trigger=lambda: lick, get_min_lick_count=lambda: minimum,
        get_tac_left_channel_name=lambda: "ai0", get_tac_right_channel_name=lambda: "ai1",
        get_tac_left_threshold=lambda: 1, get_tac_right_threshold=lambda: 2,
        get_row_channel_value=lambda values, channel, default: values[int(channel[-1])],
        get_active_trial_row=lambda: row, get_punish_no_go_fa_s=lambda: 3,
        get_hit_threshold_s=lambda: 0.5,
    )
    for name in NAMES:
        setattr(app, name, MethodType(METHODS[name], app))
    for name in ("write_trial_log", "set_trial_end_time", "store_trial_crossing_duration", "maybe_send_go_reward"):
        setattr(app, name, Mock())
    return app, row


class DMTSChoiceTests(unittest.TestCase):
    def test_counts_are_independent_and_first_choice_locks(self):
        app, row = harness()
        app.record_dmts_lick_choices(["left", "right"])
        self.assertEqual(app.active_choice_side, "")  # 1+1 is not 2 on either side.
        app.record_dmts_lick_choices(["right"])
        self.assertEqual(app.active_choice_side, "right")
        app.record_dmts_lick_choices(["left", "left"])
        self.assertEqual(app.active_choice_side, "right")
        self.assertEqual((row["left_lick_count"], row["right_lick_count"]), (3, 2))

    def test_same_sample_tie_matches_tac_left_priority(self):
        app, _ = harness(minimum=1)
        app.record_dmts_lick_choices(["left", "right"])
        self.assertEqual(app.active_choice_side, "left")

    def test_independent_thresholds_and_window_boundaries(self):
        app, _ = harness()
        def sample(time, left, right):
            edges = app.get_dmts_lick_crossings([left, right])
            app.update_active_dmts_trial(time, False, False, False, edges)
        sample(0, 1.5, 2.5)
        sample(1.4, 1.5, 2.5)  # Signals already high at window onset do not count.
        self.assertEqual((app.active_left_lick_count, app.active_right_lick_count), (0, 0))
        sample(1.5, 0, 0)
        sample(1.6, 1.5, 1.5)  # Only left crosses its own threshold.
        sample(1.7, 1.5, 2.5)  # Only right crosses.
        sample(1.8, 1.5, 2.5)  # Held signals count once.
        sample(2.3, 0, 0)
        sample(2.4, 3, 3)  # End boundary excluded.
        self.assertEqual((app.active_left_lick_count, app.active_right_lick_count), (1, 1))
        self.assertEqual(app.active_choice_side, "")

    def test_outcomes_rewards_and_timeouts(self):
        for match in (True, False):
            for choice in ("left", "right", ""):
                with self.subTest(match=match, choice=choice):
                    app, row = harness(match=match)
                    if choice:
                        app.record_dmts_lick_choices([choice, choice])
                    app.finish_active_dmts_response(2.4)
                    app.maybe_send_go_reward.assert_not_called()
                    app.finish_active_dmts_reward_period(2.5)
                    expected = (
                        ("HIT" if choice == "left" else "FA" if choice == "right" else "MISS")
                        if match else ("FA" if choice == "left" else "CR")
                    )
                    rewarded = expected in {"HIT", "CR"}
                    self.assertEqual(row["ResultType"], expected)
                    self.assertEqual(row["CR"], int(expected == "CR"))
                    if rewarded:
                        app.maybe_send_go_reward.assert_called_once()
                        self.assertEqual(app.maybe_send_go_reward.call_args.kwargs["start_s"], 2.5)
                        self.assertEqual(app.get_reward_output_side(row), "left" if match else "right")
                    else:
                        app.maybe_send_go_reward.assert_not_called()
                    app.apply_trial_timeout(row, 2.54)
                    self.assertAlmostEqual(app.next_trial_allowed_time_s, 7.54 if expected == "FA" else 4.54)

    def test_nonmatch_below_criterion_is_cr_despite_right_licks(self):
        app, row = harness(match=False, minimum=3)
        app.record_dmts_lick_choices(["right"] * 5 + ["left"] * 2)
        self.assertEqual(app.active_choice_side, "")
        app.finish_active_dmts_response(2.4)
        app.maybe_send_go_reward.assert_not_called()
        app.finish_active_dmts_reward_period(2.5)
        self.assertEqual(row["ResultType"], "CR")
        self.assertEqual(row["left_lick_count"], 2)
        self.assertEqual(row["right_lick_count"], 5)
        self.assertEqual(app.get_reward_output_side(row), "right")
        app.maybe_send_go_reward.assert_called_once()

    def test_nonmatch_right_criterion_does_not_lock_out_later_left_fa(self):
        app, row = harness(match=False)
        app.record_dmts_lick_choices(["right", "right"])
        app.record_dmts_lick_choices(["left", "left"])
        app.finish_active_dmts_reward_period(2.5)
        self.assertEqual(row["ResultType"], "FA")
        app.maybe_send_go_reward.assert_not_called()

    def test_match_first_side_locks_without_early_end(self):
        for first, expected in (("left", "HIT"), ("right", "FA")):
            with self.subTest(first=first):
                app, row = harness()
                second = "right" if first == "left" else "left"
                app.update_active_dmts_trial(1.5, False, False, False, [first, first])
                self.assertEqual(app.active_trial_end_s, 2.54)
                self.assertFalse(app.active_dmts_scored)
                app.set_trial_end_time.assert_not_called()
                app.update_active_dmts_trial(1.6, False, False, False, [second, second])
                app.finish_active_dmts_reward_period(2.5)
                self.assertEqual(row["ResultType"], expected)
                self.assertEqual(app.active_trial_end_s, 2.54)

    def test_cr_reward_is_not_sent_twice(self):
        app, _ = harness(match=False)
        app.update_active_dmts_trial(2.4, False, False, False)
        app.maybe_send_go_reward.assert_not_called()
        app.update_active_dmts_trial(2.49, False, False, False)
        app.maybe_send_go_reward.assert_not_called()
        app.update_active_dmts_trial(2.5, False, False, False)
        app.update_active_dmts_trial(2.51, False, False, False)
        app.maybe_send_go_reward.assert_called_once()
        self.assertEqual(app.maybe_send_go_reward.call_args.kwargs["start_s"], 2.5)

    def test_irfork_nonmatch_remains_correct_rejection_without_response(self):
        app, row = harness(match=False, lick=False)
        app.finish_active_dmts_reward_period(2.5)
        self.assertEqual(row["ResultType"], "CR")
        app.maybe_send_go_reward.assert_not_called()


if __name__ == "__main__":
    unittest.main()
