"""Classic Go/No-Go fork crossings need one continuous second low."""
import unittest
from unittest.mock import Mock
from test_dmts_trial_start import harness

class ClassicForkQuietTests(unittest.TestCase):
    def app(self):
        app = harness(lick=False)
        app.is_dmts_task.return_value = False
        app.start_classic_trial = Mock(return_value=True)
        return app

    def test_first_trial_requires_full_second_and_preserves_state_between_chunks(self):
        app = self.app()
        app.check_trigger([0, 0.2, 0.9], [0, 0, 2])
        app.start_classic_trial.assert_not_called()
        app.check_trigger([1.0, 1.5], [0, 0])
        app.check_trigger([2.0], [2])
        app.start_classic_trial.assert_called_once()
        self.assertEqual(app.start_classic_trial.call_args.args[0], 2.0)

    def test_high_interrupts_low_period_and_held_high_does_not_trigger(self):
        app = self.app()
        app.check_trigger([0, 0.8, 1.0, 1.9, 3.0], [0, 2, 0, 2, 2])
        app.start_classic_trial.assert_not_called()
        app.check_trigger([3.1, 4.1], [0, 2])
        app.start_classic_trial.assert_called_once()

    def test_low_during_iti_counts_but_high_during_iti_resets_it(self):
        app = self.app()
        app.next_trial_allowed_time_s = 2.0
        app.check_trigger([0, 1.9, 2.0, 2.5], [0, 2, 0, 2])
        app.start_classic_trial.assert_not_called()
        app.check_trigger([3.0, 4.0], [0, 2])
        app.start_classic_trial.assert_called_once()
        app = self.app()
        app.next_trial_allowed_time_s = 2.0
        app.check_trigger([0, 2.0, 2.1], [0, 0, 2])
        app.start_classic_trial.assert_called_once()

    def test_threshold_value_resets_quiet_timer(self):
        app = self.app()
        app.check_trigger([0, 0.8, 1.0, 1.5], [0, 1, 0, 2])
        app.start_classic_trial.assert_not_called()
