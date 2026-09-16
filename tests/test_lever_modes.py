"""Hardware-free checks of the actual runtime methods, without importing NI/Tk GUI dependencies."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, mock_open, patch

ROOT = Path(__file__).resolve().parents[1]


def load_methods(filename, names):
    source = (ROOT / filename).read_text(encoding="utf-8")
    compile(source, filename, "exec")
    tree = ast.parse(source)
    nodes = [node for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"os": os, "APP_DIR": str(ROOT)}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, "exec"), namespace)
    return namespace


class Var:
    def __init__(self, value="1"):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


NAMES = {
    "check_lever_trigger_sample", "evaluate_active_lever_trial",
    "finish_active_lever_trial", "is_lever_release_success",
    "get_lever_release_reward_count", "apply_imported_parameters",
    "select_lever_release_mode",
}
RUNTIME = load_methods("pyBEHAVIOR_v7.py", NAMES)


class LeverHarness:
    def __init__(self, mode):
        self.lever_require_release = Var(mode == "bonus")
        self.lever_req_rel_window = Var(mode == "window")
        self.active_high_start_s = 0.0
        self.active_trial_index = 1
        self.active_lever_low_start_s = None
        self.active_lever_release_armed = False
        self.irfork_was_high = True
        self.row = {"trial": 1, "HIT": 0, "MISS": 0}
        self.rewards = []
        self.plot_queue = Mock()
        self.reward_decided = False

    def __getattr__(self, name):
        if name.startswith("is_"):
            return lambda: name == "is_lever_task"
        if name.startswith(("update_", "write_", "store_", "end_", "play_", "apply_trial_", "set_trial_")) or name == "log":
            return Mock()
        value = Var()
        setattr(self, name, value)
        return value

    def get_active_trial_row(self):
        return self.row

    def get_lever_hold_time_s(self):
        return 1.0

    def get_lever_release_window_s(self):
        return 0.25

    def get_lever_release_debounce_s(self):
        return 0.05

    def maybe_send_go_reward(self, row, hold_s, start_s=None, reward_count=1):
        if not self.reward_decided:
            self.rewards.append(reward_count)
            self.reward_decided = True

    def clear_active_trial(self):
        self.active_trial_index = None

    def release(self, when):
        self.check_lever_trigger_sample(when, 0, 1)
        self.check_lever_trigger_sample(when + 0.051, 0, 1)


for name in NAMES:
    setattr(LeverHarness, name, RUNTIME[name])


class LeverModeTests(unittest.TestCase):
    def test_window_boundaries_and_single_reward(self):
        for release, hit in [(0.99, False), (1.0, True), (1.1, True), (1.25, True), (1.26, False), (3, False)]:
            with self.subTest(release=release):
                app = LeverHarness("window")
                app.evaluate_active_lever_trial(release - 0.001)
                self.assertEqual(app.rewards, [])
                app.release(release)
                self.assertEqual(app.row["HIT"], int(hit))
                self.assertEqual(app.row["MISS"], int(not hit))
                self.assertEqual(app.rewards, [1] if hit else [])
                self.assertIsNone(app.active_trial_index)

    def test_confirmation_after_window_and_brief_dip(self):
        app = LeverHarness("window")
        app.release(1.24)  # Confirmed at 1.291, but release began inside window.
        self.assertEqual(app.row["HIT"], 1)
        app = LeverHarness("window")
        app.check_lever_trigger_sample(0.8, 0, 1)
        app.check_lever_trigger_sample(0.82, 2, 1)
        self.assertEqual(app.active_trial_index, 1)
        app.release(1.1)
        self.assertEqual(app.row["HIT"], 1)

    def test_existing_modes(self):
        for mode, release, hit, rewards in [
            ("simple", 0.9, 0, []), ("simple", 1.5, 1, [1]),
            ("bonus", 0.74, 0, []), ("bonus", 0.75, 1, [3]),
            ("bonus", 1.25, 1, [3]), ("bonus", 1.5, 1, [1]),
        ]:
            with self.subTest(mode=mode, release=release):
                app = LeverHarness(mode)
                app.evaluate_active_lever_trial(min(1.0, release - 0.001))
                self.assertEqual(app.rewards, [1] if mode == "simple" and release >= 1 else [])
                app.release(release)
                self.assertEqual(app.row["HIT"], hit)
                self.assertEqual(app.rewards, rewards)

    def test_import_compatibility_and_conflicts(self):
        for params, bonus, window in [
            ({"LeverRequireRelease": "1"}, "1", "0"),
            ({"LeverRequireRelease": "1", "LeverReqRelBonus": "0"}, "0", "0"),
            ({"LeverReqRelBonus": "1", "LeverReqRelWindow": "1"}, "0", "1"),
            ({"LeverReqRelWindow": "1", "LeverReqRelBonus": "1"}, "0", "1"),
        ]:
            app = LeverHarness("window")
            app.apply_imported_parameters(params)
            self.assertEqual(app.lever_require_release.get(), bonus)
            self.assertEqual(app.lever_req_rel_window.get(), window)

    def test_gui_selection(self):
        app = LeverHarness("bonus")
        app.lever_req_rel_window.set(True)
        app.select_lever_release_mode("window")
        self.assertFalse(app.lever_require_release.get())
        app.lever_require_release.set(True)
        app.select_lever_release_mode("bonus")
        self.assertFalse(app.lever_req_rel_window.get())

    def test_generator_import_and_export(self):
        g = load_methods("protocol_generator.py", {"load_dat", "alias_for_loaded_key", "write_dat", "sync_lever_release_mode"})
        g["filedialog"] = SimpleNamespace(askopenfilename=lambda **kwargs: "check.dat")
        for values, expected in [
            ({"LeverRequireRelease": "1"}, ("1", "0")),
            ({"LeverReqRelBonus": "1", "LeverReqRelWindow": "1"}, ("0", "1")),
            ({"LeverReqRelWindow": "1", "LeverReqRelBonus": "1"}, ("0", "1")),
        ]:
            app = Mock()
            app.variables = {"LeverReqRelBonus": Var("0"), "LeverReqRelWindow": Var("1")}
            app.alias_for_loaded_key = lambda *args: g["alias_for_loaded_key"](app, *args)
            g["read_dat"] = lambda path: dict(TaskType="Lever", **values)
            g["load_dat"](app)
            self.assertEqual(tuple(v.get() for v in app.variables.values()), expected)
        app.variables["LeverReqRelBonus"].set("1")
        g["sync_lever_release_mode"](app, "LeverReqRelBonus")
        self.assertEqual(app.variables["LeverReqRelWindow"].get(), "0")
        with patch("builtins.open", mock_open()) as output, patch("os.makedirs"):
            g["write_dat"]("check.dat", {"LeverReqRelWindow": "1"}, [SimpleNamespace(key="LeverReqRelWindow", default="0")])
            output().write.assert_called_once_with("LeverReqRelWindow=1\n")


if __name__ == "__main__":
    unittest.main()
