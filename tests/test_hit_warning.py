"""Match/Go warning excludes nonmatches and unfinished trials."""
import unittest
from types import MethodType, SimpleNamespace

from test_lever_modes import load_methods


METHODS = load_methods("pyBEHAVIOR_v8.py", {"get_match_go_hit_rate"})


class HitWarningTests(unittest.TestCase):
    def rate(self, rows):
        app = SimpleNamespace(trial_rows=rows)
        return MethodType(METHODS["get_match_go_hit_rate"], app)()

    def row(self, trial_type, result, end="1.0"):
        return dict(TrialType=trial_type, ResultType=result, trial_end_s=end)

    def test_match_false_alarm_counts_as_failure_and_nonmatch_is_excluded(self):
        rows = [self.row("DMTS-match", result) for result in ("HIT", "MISS", "FA")]
        rows += [self.row("DMTS-nonmatch", "FA")] * 10
        self.assertAlmostEqual(self.rate(rows), 1 / 3)

    def test_no_completed_go_trials_has_no_rate(self):
        self.assertIsNone(self.rate([self.row("GO", "HIT", ""), self.row("noGo", "CR")]))

    def test_exact_threshold_and_classic_go(self):
        rows = [self.row("GO", "HIT")] * 13 + [self.row("GO", "MISS")] * 7
        self.assertEqual(self.rate(rows), 0.65)


if __name__ == "__main__":
    unittest.main()
