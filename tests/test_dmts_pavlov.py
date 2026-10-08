"""Exercise DMTS scoring together with the actual Pavlov reward decision."""
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock

from test_dmts_choices import harness
from test_lever_modes import load_methods, Var


METHODS = load_methods("pyBEHAVIOR_v7.py", {
    "get_pavlov_probability", "maybe_send_pavlov_reward",
})
METHODS["random"] = SimpleNamespace(random=lambda: 0.4)


def pavlov_harness(probability=1, **kwargs):
    app, row = harness(**kwargs)
    app.pavlov = Var(probability)
    app.parse_float = lambda var, default: float(var.get())
    app.trigger_output_on_crossing = Var(True)
    app.active_reward_sent = False
    app.active_pending_reward_due_s = None
    app.send_output_pulse = Mock()
    for name in ("get_pavlov_probability", "maybe_send_pavlov_reward"):
        setattr(app, name, MethodType(METHODS[name], app))
    return app, row


class DMTSPavlovTests(unittest.TestCase):
    def test_match_miss_reward_probability_in_both_response_modes(self):
        for lick in (True, False):
            for probability, rewarded in ((0, False), (0.3, False), (0.5, True), (1, True)):
                with self.subTest(lick=lick, probability=probability):
                    app, row = pavlov_harness(probability, lick=lick)
                    app.finish_active_dmts_reward_period(2.5)
                    app.finish_active_dmts_reward_period(2.6)
                    self.assertEqual(row["ResultType"], "MISS")
                    self.assertEqual(app.send_output_pulse.call_count, int(rewarded))
                    if rewarded:
                        app.send_output_pulse.assert_called_once_with(from_worker=True, start_s=2.5)

    def test_nonmatch_and_blank_never_get_pavlov_reward(self):
        for blank in (False, True):
            app, _ = pavlov_harness(match=False)
            if blank:
                app.active_dmts_sample_sound_id = app.active_dmts_test_sound_id = 0
            app.finish_active_dmts_reward_period(2.5)
            app.send_output_pulse.assert_not_called()

    def test_output_disabled_or_existing_reward_blocks_pavlov(self):
        for condition in ("disabled", "sent", "pending"):
            app, _ = pavlov_harness()
            app.trigger_output_on_crossing.set(condition != "disabled")
            app.active_reward_sent = condition == "sent"
            app.active_pending_reward_due_s = 2.6 if condition == "pending" else None
            app.finish_active_dmts_reward_period(2.5)
            app.send_output_pulse.assert_not_called()

    def test_wrong_choice_still_scores_fa_with_left_pavlov_reward(self):
        app, row = pavlov_harness()
        app.record_dmts_lick_choices(["right", "right"])
        app.finish_active_dmts_reward_period(2.5)
        self.assertEqual(row["ResultType"], "FA")
        app.send_output_pulse.assert_called_once_with(from_worker=True, start_s=2.5)


if __name__ == "__main__":
    unittest.main()
