import csv
from pathlib import Path
import tempfile
from types import MethodType, SimpleNamespace
import unittest

from test_lever_modes import load_methods


class TrialLogColumnsTests(unittest.TestCase):
    def test_csv_and_excel_table_preserve_fields_and_values(self):
        methods = load_methods('pyBEHAVIOR_v7.py', {'write_trial_log', 'write_csv'})
        methods['csv'] = csv
        with tempfile.TemporaryDirectory() as folder:
            app = SimpleNamespace(trial_log_path=str(Path(folder) / 'TrialLog.csv'),
                trial_rows=[{'trial': 1, 'TrialType': '1 DMTS-match', 'sample_light_id': 5,
                             'test_light_id': 5, 'note': 'contains, comma and\ttab',
                             'dmts_light_trial_id': 'session-1'}])
            for name in ('write_trial_log', 'write_csv'):
                setattr(app, name, MethodType(methods[name], app))
            app.write_trial_log()
            with open(app.trial_log_path, newline='', encoding='utf-8') as handle:
                original = list(csv.DictReader(handle))
            table_path = Path(folder) / 'TrialLog.tsv'
            with table_path.open(newline='', encoding='utf-8-sig') as handle:
                table = list(csv.DictReader(handle, delimiter='\t'))
            self.assertEqual(table, original)
            self.assertEqual(len(table[0]), 6)


if __name__ == '__main__':
    unittest.main()
