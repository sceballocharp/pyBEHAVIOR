"""DMTS must observe one quiet second after the ITI when NoLick is enabled."""
import unittest
from types import MethodType
from unittest.mock import Mock

from test_lever_modes import load_methods, Var
from test_dmts_trial_start import harness


METHODS = load_methods("pyBEHAVIOR_v8.py", {"get_dmts_lick_crossings"})


def app(lick=True):
    result = harness(lick)
    result.no_lick_period = Var(True)
    result.next_trial_allowed_time_s = 2.0
    result.prepare_next_dmts_light_trial = Mock(return_value=True)
    result.get_tac_left_channel_name = lambda: 0
    result.get_tac_right_channel_name = lambda: 1
    result.get_tac_left_threshold = result.get_tac_right_threshold = lambda: 1.0
    result.get_row_channel_value = lambda row, channel, fallback: row[channel]
    result.get_dmts_lick_crossings = MethodType(METHODS["get_dmts_lick_crossings"], result)
    return result


class NoLickPeriodTests(unittest.TestCase):
    def test_quiet_iti_does_not_count_and_timer_spans_chunks(self):
        instance = app()
        instance.check_trigger([0, 1, 2, 2.999], [0] * 4, [[0, 0]] * 4)
        instance.create_trial.assert_not_called()
        instance.check_trigger([3], [0], [[0, 0]])
        instance.start_active_dmts_trial.assert_called_once_with(3, 2, 4, 4)

    def test_either_lick_channel_restarts_timer(self):
        for row in ([2, 0], [0, 2]):
            with self.subTest(row=row):
                instance = app()
                instance.check_trigger([2, 2.5, 2.6, 3.499], [0] * 4,
                                       [[0, 0], row, [0, 0], [0, 0]])
                instance.create_trial.assert_not_called()
                instance.check_trigger([3.5], [0], [[0, 0]])
                instance.create_trial.assert_called_once()

    def test_held_high_signal_cannot_satisfy_quiet_period(self):
        instance = app()
        instance.check_trigger([2, 3, 4], [0] * 3, [[2, 0]] * 3)
        instance.create_trial.assert_not_called()

    def test_unchecked_starts_at_iti_end(self):
        instance = app()
        instance.no_lick_period.set(False)
        instance.check_trigger([2], [0], [[0, 0]])
        instance.create_trial.assert_called_once()

    def test_first_trial_also_needs_one_quiet_second(self):
        instance = app()
        instance.next_trial_allowed_time_s = -1e12
        instance.check_trigger([0, 0.999], [0, 0], [[0, 0]] * 2)
        instance.create_trial.assert_not_called()
        instance.check_trigger([1], [0], [[0, 0]])
        instance.create_trial.assert_called_once()

    def test_fork_trigger_still_required_after_quiet_second(self):
        instance = app(lick=False)
        instance.check_trigger([2, 2.5, 3, 3.1], [0, 2, 0, 2], [[0, 0]] * 4)
        instance.start_active_dmts_trial.assert_called_once_with(3.1, 2, 4, 4)


if __name__ == "__main__":
    unittest.main()
