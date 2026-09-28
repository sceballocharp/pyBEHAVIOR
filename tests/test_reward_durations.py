"""Verify valve pulse timing without sending hardware outputs."""
from types import MethodType, SimpleNamespace
from unittest.mock import Mock
import unittest

from test_lever_modes import load_methods, Var, LeverHarness


METHODS = load_methods("pyBEHAVIOR_v7.py", {"get_reward_pulse_s", "send_output_pulse", "send_reward_pulses"})


class RewardDurationTests(unittest.TestCase):
    def test_each_valve_uses_its_own_duration(self):
        sleeper = Mock()
        METHODS.update(time=SimpleNamespace(sleep=sleeper), nidaqmx=None)
        app = SimpleNamespace(
            pulse_ms=Var("30"), right_pulse_ms=Var("80"),
            parse_float=lambda var, default: float(var.get()),
            reward_task=Mock(), right_reward_task=Mock(),
            record_trigger_pulse=Mock(), log=Mock(), update_health_readouts=Mock(),
            reward_pulse_count=0,
        )
        for name in ("get_reward_pulse_s", "send_output_pulse", "send_reward_pulses"):
            setattr(app, name, MethodType(METHODS[name], app))
        for side, duration in (("left", 0.03), ("right", 0.08)):
            sleeper.reset_mock()
            app.send_reward_pulses(2, start_s=1, reward_side=side)
            self.assertEqual([call.args[0] for call in sleeper.call_args_list], [duration] * 3)
            self.assertAlmostEqual(app.record_trigger_pulse.call_args.kwargs["start_s"], 1 + 2 * duration)
        for task in (app.reward_task, app.right_reward_task):
            self.assertEqual([call.args[0] for call in task.write.call_args_list], [True, False, True, False])

    def test_legacy_import_resets_both_sides_and_explicit_right_wins(self):
        app = LeverHarness("bonus")
        app.pulse_ms = Var("30")
        app.right_pulse_ms = Var("80")
        app.apply_imported_parameters({"Rewardduration_ms": "45"})
        self.assertEqual((app.pulse_ms.get(), app.right_pulse_ms.get()), ("45", "45"))
        app.apply_imported_parameters({"Rewardduration_ms": "30", "RightRewardduration_ms": "80"})
        self.assertEqual((app.pulse_ms.get(), app.right_pulse_ms.get()), ("30", "80"))


if __name__ == "__main__":
    unittest.main()
