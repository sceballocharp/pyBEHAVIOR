"""Hardware-free regression checks for the NWB timing export payload."""
from datetime import datetime, timezone
import math
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import MagicMock

from test_lever_modes import load_methods


class NWBTrialTimingTests(unittest.TestCase):
    def test_timing_values_preserve_zero_precision_and_missing_rows(self):
        methods = load_methods("pyBEHAVIOR_v8.py", {"write_nwb_contract_hdf5"})
        h5py = MagicMock()
        methods.update(h5py=h5py, datetime=datetime, timezone=timezone)
        saved = {}
        app = SimpleNamespace(
            replace_hdf5_dataset=lambda parent, name, data, dtype=None: saved.update({name: (data, dtype)}),
            nwb_contract_hmcf=lambda row: "Hit",
            nwb_contract_trial_type=lambda row: 1,
            build_nwb_contract_parameters=lambda rate, count: [],
        )
        export = MethodType(methods["write_nwb_contract_hdf5"], app)
        rows = [
            {"trigger_time_s": "0.000000", "crossing_duration_s": "1.123456", "trial_end_s": "1.173456",
             "punishment_sound_file": "noise.wav", "punishment_sound_gain": 0.25,
             "punishment_sound_repeats": 3, "punishment_sound_duration_s": 1.5,
             "punishment_sound_start_s": 2.7, "punishment_sound_end_s": 4.2,
             "punishment_sound_status": "completed"},
            {"trigger_time_s": "2.000000", "crossing_duration_s": "", "trial_end_s": None},
            {},
        ]
        export("unused.nwb", 1000, rows)
        self.assertEqual(saved["trigger_time_s"][0][:2], [0.0, 2.0])
        self.assertEqual(saved["crossing_duration_s"][0][0], 1.123456)
        self.assertEqual(saved["trial_end_s"][0][0], 1.173456)
        self.assertEqual(saved['punishment_sound_file'][0], ['noise.wav', '', ''])
        self.assertEqual(saved['punishment_sound_gain'][0], [0.25, 0.0, 0.0])
        self.assertEqual(saved['punishment_sound_repeats'][0], [3, 0, 0])
        self.assertEqual(saved['punishment_sound_duration_s'][0], [1.5, 0.0, 0.0])
        self.assertEqual(saved['punishment_sound_start_s'][0][0], 2.7)
        self.assertEqual(saved['punishment_sound_end_s'][0][0], 4.2)
        self.assertEqual(saved['punishment_sound_status'][0], ['completed', '', ''])
        for column in ("trigger_time_s", "crossing_duration_s", "trial_end_s"):
            values, dtype = saved[column]
            self.assertEqual(len(values), len(rows))
            self.assertEqual(dtype, "float64")
            self.assertTrue(math.isnan(values[-1]))
        self.assertTrue(math.isnan(saved["trial_end_s"][0][1]))
        self.assertTrue(math.isnan(saved["crossing_duration_s"][0][1]))
        export("empty.nwb", 1000, [])
        self.assertEqual(saved["trial_end_s"], ([], "float64"))


if __name__ == "__main__":
    unittest.main()
