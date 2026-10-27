"""Session restart checks using temporary folders, without NI hardware or Tk."""
from pathlib import Path
from datetime import datetime
import re
import tempfile
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock

from test_lever_modes import load_methods, Var


class SessionFolderTests(unittest.TestCase):
    def make_app(self, root):
        names = {'ensure_session_folder', 'prepare_session_folder',
                 'open_behavior_signal_file', 'close_behavior_signal_file', 'start_live',
                 'build_session_folder_path'}
        methods = load_methods('pyBEHAVIOR_v8.py', names)
        methods['datetime'] = Mock()
        methods['datetime'].now.return_value = datetime(2026, 10, 27, 12, 0, 0)
        methods['re'] = re
        app = SimpleNamespace(
            exp_folder='', trial_log_path='', parameters_log_path='',
            behavior_signal_file=None, left_lick_file=None, right_lick_file=None,
            soundcopy_file=None, trial_state_file=None,
            write_behavior_signal_bin=Var(True), uses_dual_lick_channels=lambda: True,
            save_root=Var(str(root)), user_name=Var('User'), mouse_id=Var('99'),
            project_name=Var('DMTS'),
            write_parameters_dat=Mock(), log=Mock(), running=False, acq_thread=None)
        for name in names:
            setattr(app, name, MethodType(methods[name], app))
        return app

    def test_restarts_preserve_previous_files_and_restore_log_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            app = self.make_app(Path(folder))
            sessions = []
            for run in range(3):
                # Start resets these paths before preparing the session folder.
                app.trial_log_path = app.parameters_log_path = ''
                app.prepare_session_folder()
                current = Path(app.exp_folder)
                sessions.append(current)
                self.assertEqual(Path(app.trial_log_path), current / 'TrialLog.csv')
                self.assertEqual(Path(app.parameters_log_path), current / 'Parameters.csv')
                app.open_behavior_signal_file()
                for name in ('behavior_signal_file', 'left_lick_file', 'right_lick_file',
                             'soundcopy_file', 'trial_state_file'):
                    getattr(app, name).write(bytes([run + 1]))
                app.close_behavior_signal_file()
                for name in ('TrialLog.csv', 'TrialLog.tsv', 'Parameters.csv',
                             'parameters.dat', 'session.nwb'):
                    (current / name).write_bytes(bytes([run + 1]))
            self.assertEqual(len(set(sessions)), 3)
            self.assertEqual([p.name for p in sessions],
                             ['120000_DMTS_Data', '120000_DMTS_001_Data', '120000_DMTS_002_Data'])
            for run, session in enumerate(sessions):
                for output in session.iterdir():
                    self.assertEqual(output.read_bytes(), bytes([run + 1]))

    def test_project_name_and_date_hierarchy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            app = self.make_app(root)
            _, path = app.build_session_folder_path()
            self.assertEqual(Path(path), root / 'User' / 'behavior_data' / 'M99' /
                             '20261027' / '120000_DMTS_Data')

    def test_project_name_is_safe_and_empty_name_has_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            app = self.make_app(Path(folder))
            for name, expected in (
                ('', 'UnnamedProject'), (' . ', 'UnnamedProject'),
                (' .DMTS:/\\<>"|?*\x00\x1f. ', 'DMTS' + '_' * 11),
                ('Training A', 'Training A'),
            ):
                with self.subTest(project=name):
                    app.project_name.set(name)
                    _, path = app.build_session_folder_path()
                    self.assertEqual(Path(path).name, f'120000_{expected}_Data')
                    app.prepare_session_folder()
                    self.assertTrue(Path(app.exp_folder).is_dir())

    def test_signal_open_refuses_to_truncate_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            app = self.make_app(Path(folder))
            app.prepare_session_folder()
            path = Path(app.exp_folder) / 'BehaviorSignal.bin'
            path.write_bytes(b'previous recording')
            with self.assertRaises(FileExistsError):
                app.open_behavior_signal_file()
            self.assertEqual(path.read_bytes(), b'previous recording')

    def test_auxiliary_folder_reuse_then_start_creates_new_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            app = self.make_app(Path(folder))
            first = app.ensure_session_folder()
            self.assertEqual(app.ensure_session_folder(), first)
            app.prepare_session_folder()
            self.assertNotEqual(app.exp_folder, first)

    def test_start_waits_for_previous_acquisition_thread(self):
        with tempfile.TemporaryDirectory() as folder:
            app = self.make_app(Path(folder))
            app.acq_thread = Mock()
            app.acq_thread.is_alive.return_value = True
            app._start_live_session = Mock()
            app.start_live()
            app._start_live_session.assert_not_called()


if __name__ == '__main__':
    unittest.main()
