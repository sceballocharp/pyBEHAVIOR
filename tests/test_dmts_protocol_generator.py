import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import protocol_generator as pg


class Variable:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class GeneratorHarness:
    """Exercise the generator's import/export logic without opening Tk windows."""

    active_parameters = pg.ProtocolGenerator.active_parameters
    get_parameter = pg.ProtocolGenerator.get_parameter
    alias_for_loaded_key = pg.ProtocolGenerator.alias_for_loaded_key
    load_dat = pg.ProtocolGenerator.load_dat
    validate = pg.ProtocolGenerator.validate
    parse_float = pg.ProtocolGenerator.parse_float
    parse_int = pg.ProtocolGenerator.parse_int
    parse_dmts_sound_ids = pg.ProtocolGenerator.parse_dmts_sound_ids

    def __init__(self):
        self.variables = {p.key: Variable(p.default) for p in pg.PARAMETERS}
        self.variables["TriggerTypeDropDown"].set("Lick")
        self.notebook = Mock()
        self.current_path = Variable("")
        self.status_var = Variable("")
        self.sync_trial_duration = Mock()
        self.sync_tac_trial_duration = Mock()
        self.update_response_visibility = Mock()

    def active_behavior(self):
        return "DMTS"

    def save(self, path):
        parameters = self.active_parameters()
        values = {p.key: self.variables[p.key].get() for p in parameters}
        pg.write_dat(path, values, parameters)

    def load(self, path):
        with patch.object(pg.filedialog, "askopenfilename", return_value=str(path)):
            self.load_dat()


class DMTSProtocolTests(unittest.TestCase):
    def test_custom_lick_values_round_trip(self):
        app = GeneratorHarness()
        app.variables["DMTSMinlickcount"].set("3")
        app.variables["DMTSLeftThreshold"].set("0.75")
        app.variables["DMTSRightThreshold"].set("1.5")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "protocol.dat"
            app.save(path)
            values = pg.read_dat(path)
            self.assertEqual(values["Minlickcount"], "3")
            self.assertEqual(values["TACLeftThreshold"], "0.75")
            self.assertEqual(values["TACRightThreshold"], "1.5")
            self.assertNotIn("HITThreshold_percent", values)
            loaded = GeneratorHarness()
            loaded.load(path)
            self.assertEqual(loaded.variables["DMTSMinlickcount"].get(), "3")
            self.assertEqual(loaded.variables["DMTSLeftThreshold"].get(), "0.75")
            self.assertEqual(loaded.variables["DMTSRightThreshold"].get(), "1.5")
            self.assertEqual(loaded.validate(), [])

    def test_old_protocol_resets_missing_lick_fields(self):
        app = GeneratorHarness()
        app.variables["DMTSMinlickcount"].set("8")
        app.variables["DMTSLeftThreshold"].set("4")
        app.variables["DMTSRightThreshold"].set("5")
        app.load(Path(pg.APP_DIR) / "protocols/dmts_licks_parameters_matchonly_allsounds.dat")
        self.assertEqual(app.variables["DMTSMinlickcount"].get(), "1")
        self.assertEqual(app.variables["DMTSLeftThreshold"].get(), "1")
        self.assertEqual(app.variables["DMTSRightThreshold"].get(), "1")

    def test_invalid_lick_inputs(self):
        for key, values in {
            "DMTSMinlickcount": ["0", "-1", "1.5", "abc", "nan", "inf"],
            "DMTSLeftThreshold": ["abc", "nan", "inf", "-inf"],
            "DMTSRightThreshold": ["abc", "nan", "inf", "-inf"],
        }.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    app = GeneratorHarness()
                    app.variables[key].set(value)
                    self.assertTrue(app.validate())

    def test_legacy_threshold_import_and_independent_channels(self):
        app = GeneratorHarness()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy.dat"
            path.write_text("TaskType=DMTS\nTriggerTypeDropDown=Lick\nLickthreshold=0.6\nTACRightThreshold=1.2\n", encoding="utf-8")
            app.load(path)
            self.assertEqual(app.variables["DMTSLeftThreshold"].get(), "0.6")
            self.assertEqual(app.variables["DMTSRightThreshold"].get(), "1.2")
            app.variables["DMTSLeftChannel"].set("ai2")
            app.variables["DMTSRightChannel"].set("ai3")
            app.save(path)
            loaded = GeneratorHarness()
            loaded.load(path)
            self.assertEqual(loaded.variables["DMTSLeftChannel"].get(), "ai2")
            self.assertEqual(loaded.variables["DMTSRightChannel"].get(), "ai3")
            loaded.variables["DMTSRightChannel"].set("ai2")
            self.assertTrue(loaded.validate())

    def test_irfork_export_uses_percentage(self):
        app = GeneratorHarness()
        app.variables["TriggerTypeDropDown"].set("IRFork")
        app.variables["DMTSHITThreshold_percent"].set("65")
        app.variables["DMTSMinlickcount"].set("invalid unused value")
        self.assertEqual(app.validate(), [])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "protocol.dat"
            app.save(path)
            values = pg.read_dat(path)
            self.assertEqual(values["HITThreshold_percent"], "65")
            self.assertNotIn("Minlickcount", values)
            self.assertNotIn("Lickthreshold", values)


if __name__ == "__main__":
    unittest.main()
