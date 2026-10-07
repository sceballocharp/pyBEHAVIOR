import asyncio
import importlib.util
from pathlib import Path
import queue
import threading
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock

from test_lever_modes import load_methods
from test_dmts_trial_start import harness

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'braincodec' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


driver = load_module('dmts_driver', 'dmts_driver.py')
client_module = load_module('dmts_client', 'dmts_client.py')
runner = load_module('remote_runner', 'remote_runner.py')


def config():
    return {'device_id': 'H2-190', 'DMTS stimuli': ['STIM1', 'STIM7', 'STIM10'],
            'STIM1': 'P1N8 P2N8', 'STIM7': 'P5N5', 'STIM10': 'P10N1',
            'GO irradiance (mW/mm2)': 2, 'Pulse duration (ms)': 10,
            'Pulse frequency (Hz)': 50, 'Number of pulses': 1}


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.library = driver.DMTSLibrary(config())
        self.state = driver.DMTSPairState(self.library)

    def prepare(self, sample=7, test=10, token='session-1'):
        return self.state.prepare(token, sample, test, self.library.fingerprint)

    def test_two_triggers_and_no_third_presentation(self):
        self.prepare()
        sample = self.state.claim_trigger()
        self.assertEqual(sample[2:], ('sample', 7))
        self.assertIsNone(self.state.claim_trigger())
        self.state.complete(sample)
        test = self.state.claim_trigger()
        self.assertEqual(test[2:], ('test', 10))
        self.state.complete(test)
        self.assertEqual(self.state.snapshot()['phase'], 'idle')
        self.assertEqual(len(self.state.snapshot()['presentations']), 2)
        self.assertIsNone(self.state.claim_trigger())

    def test_reject_unknown_mixed_blank_duplicate_or_pending(self):
        for sample, test in ((2, 7), (0, 7), (7, 0), (1.0, 7)):
            with self.assertRaises(ValueError):
                self.prepare(sample, test)
        self.prepare(0, 0)
        with self.assertRaises(ValueError):
            self.prepare(token='session-2')
        self.state.reset()
        with self.assertRaises(ValueError):
            self.prepare()

    def test_reset_cancels_inflight_completion(self):
        self.prepare()
        claim = self.state.claim_trigger()
        self.state.reset()
        self.prepare(1, 1, 'session-2')
        self.state.complete(claim)
        self.assertEqual(self.state.snapshot()['phase'], 'waiting_sample')
        self.assertEqual(self.state.snapshot()['presentations'], [])

    def test_fingerprint_catches_intensity_and_cable_difference(self):
        changed = config()
        changed['STIM7 irradiance (mW/mm2)'] = 3
        for library in (driver.DMTSLibrary(changed), driver.DMTSLibrary(config(), False)):
            with self.assertRaises(ValueError):
                self.state.prepare('session-1', 7, 10, library.fingerprint)

    def test_invalid_libraries(self):
        for override in ({'DMTS stimuli': ['STIM1', 'STIM1']}, {'STIM7': 'P11N1'},
                         {'Number of pulses': 1.2}, {'Pulse duration (ms)': 1000}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                driver.DMTSLibrary(dict(config(), **override))


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.library = driver.DMTSLibrary(config())
        self.protocol = driver.DMTSPairState(self.library)
        state = runner.BraincodecRunnerState()
        state.experiment = SimpleNamespace(protocol=self.protocol, stopped=False,
            prepare_pair=lambda p: self.protocol.prepare(p['trial_id'], p['sample_id'],
                                                         p['test_id'], p['fingerprint']),
            reset_pair=self.protocol.reset)
        handler = type('QuietHandler', (runner.BraincodecRequestHandler,),
                       {'runner_state': state, 'log_message': lambda *args: None})
        self.server = runner.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = client_module.DMTSLightClient(
            f'http://127.0.0.1:{self.server.server_port}', self.library)
        self.client.connect()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def finish_pair(self):
        for _ in range(2):
            claim = self.protocol.claim_trigger()
            self.protocol.complete(claim)

    def test_match_nonmatch_and_blank_over_actual_http(self):
        for trial_type in (1, 2, 0):
            pair = self.client.prepare(trial_type)
            if trial_type == 1:
                self.assertEqual(pair['sample_id'], pair['test_id'])
            elif trial_type == 2:
                self.assertNotEqual(pair['sample_id'], pair['test_id'])
            else:
                self.assertEqual((pair['sample_id'], pair['test_id']), (0, 0))
            self.client.require_phase(pair, 'waiting_sample')
            self.finish_pair()
            self.client.require_phase(pair, 'idle')

    def test_missing_trigger_and_reset_are_detected(self):
        pair = self.client.prepare(2)
        with self.assertRaises(RuntimeError):
            self.client.require_phase(pair, 'waiting_test')
        self.client.reset()
        with self.assertRaises(RuntimeError):
            self.client.require_phase(pair, 'waiting_sample')


class DriverLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_held_high_is_one_trigger_and_stop_clears_pair(self):
        exp = driver.ExpDMTSPatterns.__new__(driver.ExpDMTSPatterns)
        exp.library = driver.DMTSLibrary(config())
        exp.protocol = driver.DMTSPairState(exp.library)
        exp.hardware = SimpleNamespace(trig=[0], stop_=Mock())
        exp.control_panel = SimpleNamespace(set_status=Mock())
        exp._stop_requested = False
        exp.stopped = False
        exp._low_seen = False
        exp._observed_generation = -1
        exp._reset_requested = False
        exp._reset_complete = threading.Event()
        exp._log = Mock()
        presented = []

        async def apply(stimulus):
            presented.append(stimulus)
            await asyncio.sleep(0)
        exp._apply = apply
        task = asyncio.create_task(exp.run())
        try:
            exp.prepare_pair({'trial_id': '1', 'sample_id': 7, 'test_id': 10,
                              'fingerprint': exp.library.fingerprint})
            exp.hardware.trig[0] = 1
            await asyncio.sleep(0.03)
            self.assertEqual(exp.protocol.snapshot()['phase'], 'waiting_test')
            self.assertEqual(presented, [7, 0])
            exp.hardware.trig[0] = 0
            await asyncio.sleep(0.005)
            exp.hardware.trig[0] = 1
            await asyncio.sleep(0.03)
            self.assertEqual(presented, [7, 0, 10, 0])
            self.assertEqual(exp.protocol.snapshot()['phase'], 'idle')
            exp.hardware.trig[0] = 0
            await asyncio.to_thread(exp.reset_pair)
            self.assertIsNone(exp.protocol.snapshot()['pair'])
        finally:
            exp.stop_()
            await task
        exp.hardware.stop_.assert_called()


class BehaviorTests(unittest.TestCase):
    def attach(self, app):
        names = {'prepare_next_dmts_light_trial', 'trigger_dmts_light_phase', 'fail_dmts_light_trial'}
        for name, method in load_methods('pyBEHAVIOR_v7.py', names).items():
            if name in names:
                setattr(app, name, MethodType(method, app))
        app._dmts_light_pending = None
        app._dmts_light_active = None
        app.dmts_light_client = Mock()
        app.dmts_light_client.prepare.return_value = {
            'trial_id': 'one', 'sample_id': 7, 'test_id': 10, 'trial_type': 2, 'fingerprint': 'abc'}
        return app

    def test_prepare_during_iti_and_use_same_ids_at_start(self):
        app = self.attach(harness())
        app.next_trial_allowed_time_s = 2
        app.consume_next_dmts_trial_type.return_value = 2
        app.check_trigger([0, 1], [0, 0])
        app.dmts_light_client.prepare.assert_called_once_with(2)
        app.start_active_dmts_trial.assert_not_called()
        app.check_trigger([2], [0])
        app.start_active_dmts_trial.assert_called_once_with(2, 2, 7, 10)
        app.choose_dmts_trial_sound_ids.assert_not_called()

    def test_ni_failure_marks_error_and_stops(self):
        app = self.attach(harness())
        row = {'trial': 1}
        app.get_active_trial_row = Mock(return_value=row)
        app.send_light_trigger_pulse = Mock(return_value=False)
        app._dmts_light_active = {'trial_id': 'one'}
        self.assertFalse(app.trigger_dmts_light_phase('sample'))
        self.assertEqual(row['ResultType'], 'ERROR')
        self.assertTrue(app.dmts_lapse_stop_requested)
        self.assertIn(('stop_session', None), list(app.plot_queue.queue))

    def test_reward_is_withheld_until_both_presentations_are_confirmed(self):
        from test_dmts_choices import harness as choices_harness
        app, row = choices_harness()
        app = self.attach(app)
        app._dmts_light_test_confirmed = False
        app.finish_active_dmts_reward_period(4)
        app.maybe_send_go_reward.assert_not_called()
        app.maybe_send_pavlov_reward.assert_not_called()
        self.assertEqual(row['ResultType'], 'ERROR')

    def test_generator_yaml_loads_without_pyyaml(self):
        import json
        methods = load_methods('braincodec/tk_panel.py',
            {'_load_simple_yaml', '_strip_inline_comment', '_parse_scalar_value'})
        methods['_parse_scalar_value'].__func__.__globals__['json'] = json
        panel = SimpleNamespace()
        for name in ('_strip_inline_comment', '_parse_scalar_value'):
            setattr(panel, name, methods[name])
        parsed = methods['_load_simple_yaml'](panel,
            'DMTS stimuli: ["STIM1", "STIM7"]\nPulse duration (ms): 25\n')
        self.assertEqual(parsed['DMTS stimuli'], ['STIM1', 'STIM7'])


class GUITests(unittest.TestCase):
    def panel_harness(self, stop_pending=False):
        from braincodec.tk_panel import BraincodecTkPanel
        panel = SimpleNamespace(_remote_stop_pending=stop_pending,
            _is_waiting_for_trigger=BraincodecTkPanel._is_waiting_for_trigger,
            _remote_status_text=BraincodecTkPanel._remote_status_text)
        for name in ('set_status', 'set_progress', 'set_info', 'add_log_line',
                     '_stop_remote_status_polling', '_schedule_remote_status_poll',
                     '_download_remote_log_if_available', '_download_health_scan_files_if_available'):
            setattr(panel, name, Mock())
        return panel

    def test_ready_states_stop_background_polling(self):
        from braincodec.tk_panel import BraincodecTkPanel
        for message in ('Waiting for trigger', 'DMTS ready; waiting for pair',
                        'DMTS waiting_sample', 'DMTS waiting_test', 'DMTS idle'):
            panel = self.panel_harness()
            BraincodecTkPanel._handle_remote_response(panel,
                {'status': {'state': 'running', 'last_message': message}}, log_response=False)
            panel._stop_remote_status_polling.assert_called_once()
            panel._schedule_remote_status_poll.assert_not_called()

    def test_loading_and_stop_request_continue_polling(self):
        from braincodec.tk_panel import BraincodecTkPanel
        for state, message, stop_pending in (
                ('loading', 'Loading hardware and driver', False),
                ('running', 'DMTS ready; waiting for pair', True),
                ('stopping', 'Stop requested', True)):
            panel = self.panel_harness(stop_pending)
            BraincodecTkPanel._handle_remote_response(panel,
                {'status': {'state': state, 'last_message': message}}, log_response=False)
            panel._schedule_remote_status_poll.assert_called_once()
            panel._stop_remote_status_polling.assert_not_called()

    def test_automatic_status_reports_error_and_traceback_once(self):
        from braincodec.tk_panel import BraincodecTkPanel
        panel = self.panel_harness()
        body = {'status': {'state': 'error', 'last_message': 'Experiment failed',
                          'error': 'ModuleNotFoundError: dmts_driver',
                          'traceback': 'Traceback: missing driver', 'started_at': 'one'}}
        for _ in range(2):
            BraincodecTkPanel._handle_remote_response(panel, body, log_response=False)
        self.assertEqual(panel.add_log_line.call_count, 2)
        panel.set_info.assert_called_with('ModuleNotFoundError: dmts_driver')

    def test_dmts_panel_config_upload_and_mode_switch(self):
        import tkinter as tk
        from braincodec.tk_panel import BraincodecTkPanel, MODE_DMTS, MODE_SIMPLE
        root = tk.Tk()
        root.withdraw()
        try:
            panel = BraincodecTkPanel(root)
            panel.set_mode(MODE_DMTS)
            panel.config_file_var.set(str(ROOT / 'braincodec/configurations/config_DMTS_example.yaml'))
            panel.trials_file_var.set('')
            self.assertTrue(panel.validate_config_flow())
            self.assertEqual(len(panel._build_upload_payload()['files']), 1)
            self.assertEqual(panel._build_remote_payload()['trials_file'], '')
            self.assertFalse(panel.generate_trials_file())
            self.assertTrue(panel.generated_secondary_entry.instate(['disabled']))
            panel.set_mode(MODE_SIMPLE)
            self.assertFalse(panel.generated_secondary_entry.instate(['disabled']))
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
