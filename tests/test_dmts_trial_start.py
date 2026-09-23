"""Hardware-free regression checks for DMTS initiation and timeout handling."""
import queue
from types import SimpleNamespace, MethodType
import unittest
from unittest.mock import Mock

from test_lever_modes import load_methods, Var


METHODS = load_methods("pyBEHAVIOR_v7.py", {
    "check_trigger", "apply_trial_timeout", "finish_active_dmts_timeline",
})


def harness(lick=True):
    app = SimpleNamespace(
        active_trial_index=None, active_trial_end_s=None,
        next_trial_allowed_time_s=-1e12, irfork_was_high=False,
        trigger_reset_seen_for_new_trial=False, trial_index=0,
        max_trials=Var("3"), trigger_type=Var("Lick" if lick else "IRFork"),
        plot_queue=queue.Queue(), active_trial_base_iti_s=2,
        active_dmts_scored=True,
    )
    for name, function in METHODS.items():
        if callable(function):
            setattr(app, name, MethodType(function, app))
    for name, result in {
        "get_current_trigger_threshold": 1, "is_lever_task": False,
        "is_tac_pretraining_task": False, "is_tac_task": False,
        "is_dmts_task": True, "is_lick_trigger": lick,
        "consume_next_dmts_trial_type": 1,
        "choose_dmts_trial_sound_ids": (4, 4), "draw_trial_iti_s": 2,
        "classify_trial_sound": (1, "DMTS-match"),
        "get_punish_no_go_fa_s": 3,
        "get_dmts_lick_crossings": (),
    }.items():
        setattr(app, name, Mock(return_value=result))
    app.parse_int = lambda var, default: int(var.get())
    for name in ("process_pending_go_reward", "update_active_dmts_trial",
                 "set_trial_end_time", "store_trial_crossing_duration",
                 "write_trial_log", "end_trial_state_interval"):
        setattr(app, name, Mock())
    def create(*args, **kwargs):
        app.trial_index += 1
    app.create_trial = Mock(side_effect=create)
    def start(*args):
        app.active_trial_index = app.trial_index
    app.start_active_dmts_trial = Mock(side_effect=start)
    def clear():
        app.active_trial_index = None
        app.active_trial_end_s = None
    app.clear_active_trial = clear
    return app


class DMTSTrialStartTests(unittest.TestCase):
    def test_first_sample_starts_without_lick_or_reset(self):
        for voltage in (0, 2):
            with self.subTest(voltage=voltage):
                app = harness()
                app.check_trigger([0], [voltage])
                app.start_active_dmts_trial.assert_called_once_with(0, 2, 4, 4)
                app.update_active_dmts_trial.assert_not_called()

    def test_end_of_trial_waits_for_iti_and_fa_timeout(self):
        for result, allowed in (("CR", 12), ("FA", 15)):
            with self.subTest(result=result):
                app = harness()
                app.active_trial_index = 1
                app.active_trial_end_s = 10
                app.get_active_trial_row = Mock(return_value={
                    "TrialType": "DMTS-nonmatch", "ResultType": result,
                })
                app.check_trigger([10, 11, allowed - 0.001], [0, 2, 0])
                self.assertEqual(app.next_trial_allowed_time_s, allowed)
                app.create_trial.assert_not_called()
                app.check_trigger([allowed], [0])
                app.start_active_dmts_trial.assert_called_once_with(allowed, 2, 4, 4)

    def test_high_signal_does_not_block_automatic_start(self):
        app = harness()
        app.irfork_was_high = True
        app.next_trial_allowed_time_s = 2
        app.check_trigger([1, 2], [2, 2])
        app.start_active_dmts_trial.assert_called_once_with(2, 2, 4, 4)

    def test_max_trials_blocks_start(self):
        app = harness()
        app.trial_index = 3
        app.check_trigger([0, 1], [0, 0])
        app.create_trial.assert_not_called()

    def test_irfork_still_needs_reset_and_crossing(self):
        app = harness(lick=False)
        app.next_trial_allowed_time_s = 2
        app.check_trigger([1, 2, 3], [0, 2, 2])
        app.create_trial.assert_not_called()
        app.check_trigger([4, 5], [0, 2])
        app.start_active_dmts_trial.assert_called_once_with(5, 2, 4, 4)


if __name__ == "__main__":
    unittest.main()
