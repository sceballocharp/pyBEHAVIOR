import ast
import json
import importlib.util
from pathlib import Path
import unittest



ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "simple_pattern_generator", ROOT / "braincodec/simple_pattern_generator.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class PatternGeneratorTests(unittest.TestCase):
    def config(self, **overrides):
        values = dict(mouse="332", device="H2-190", patches=[(1, 8), (4, 4)],
                      irradiance=2, nogo_p=8, nogo_n=1, nogo_irradiance=2,
                      duration=25, frequency=20, pulses=10)
        values.update(overrides)
        return generator.build_config(**values)

    def test_yaml_roundtrip_and_legacy_fields(self):
        config = {key: json.loads(value) for key, value in
                  (line.split(': ', 1) for line in generator.dump_yaml(self.config()).splitlines())}
        self.assertEqual(config["GO stimuli"], ["STIM1", "STIM2"])
        self.assertEqual(config["GO"], config["STIM1"])
        self.assertEqual(config["STIM1"],
                         "P1N8 P2N8 P3N8 P1N9 P2N9 P3N9 P1N10 P2N10 P3N10")
        self.assertEqual(len(set(config["STIM2"].split())), 9)
        self.assertEqual(config["GO stimulus selection"], "random")
        self.assertEqual(self.config(selection="cycle")["GO stimulus selection"], "cycle")

    def test_bounds(self):
        for coordinates in ((0, 1), (9, 1), (1, 9)):
            with self.assertRaises(ValueError):
                generator.patch_labels(*coordinates)
        self.assertIn("P10N10", generator.patch_labels(8, 8))

    def test_invalid_settings(self):
        for override in (dict(patches=[]), dict(irradiance=float("nan")),
                         dict(frequency=0), dict(duration=51), dict(pulses=0),
                         dict(selection="invalid")):
            with self.subTest(override=override), self.assertRaises(ValueError):
                self.config(**override)

    def test_driver_syntax(self):
        ast.parse((ROOT / "braincodec/driver.pyw").read_text(encoding="utf-8"))

    def test_dmts_mode_marks_library_and_requires_multiple_patterns(self):
        config = self.config(mode='dmts_patterns')
        self.assertEqual(config['experiment_mode'], 'dmts_patterns')
        self.assertEqual(config['DMTS stimuli'], ['STIM1', 'STIM2'])
        with self.assertRaises(ValueError):
            self.config(mode='dmts_patterns', patches=[(1, 8)])


if __name__ == "__main__":
    unittest.main()
