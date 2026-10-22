import json
import tempfile
from pathlib import Path
import unittest

from session_history import SessionHistory


class SessionHistoryTests(unittest.TestCase):
    def test_updates_one_entry_and_preserves_previous_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'session_history.json'
            history = SessionHistory(path)
            history.start('Sebastian', '99', 'DMTS')
            history.update(10, 4)
            history.update(12, 5, stopped=True)
            history.update(100, 100, stopped=True)
            rows = json.loads(path.read_text())
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0]['trials'], rows[0]['rewards']), (12, 5))
            self.assertEqual((rows[0]['user'], rows[0]['animal_id'], rows[0]['project']),
                             ('Sebastian', '99', 'DMTS'))
            self.assertEqual(rows[0]['status'], 'stopped')
            self.assertIsNotNone(rows[0]['stopped_at'])
            history.start('Other', '100', 'Training', simulation=True)
            rows = json.loads(path.read_text())
            self.assertEqual(len(rows), 2)
            self.assertTrue(rows[1]['simulation'])
            self.assertEqual(rows[1]['status'], 'running')
            self.assertEqual(rows[0]['trials'], 12)

    def test_corrupt_history_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'session_history.json'
            for original in ('broken JSON', '{}', '[1]'):
                path.write_text(original)
                with self.assertRaises(ValueError):
                    SessionHistory(path).start('User', '1', 'Project')
                self.assertEqual(path.read_text(), original)
