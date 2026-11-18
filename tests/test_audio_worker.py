"""Cancellable audio, acquisition heartbeat, trial gating and event handling."""
import queue
import threading
import time
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import numpy as np
from audio_worker import AudioBusyError, AudioJob, AudioWorker, play_audio
from test_lever_modes import load_methods, Var
from test_dmts_trial_start import harness as trial_harness


class AudioWorkerTests(unittest.TestCase):
    def test_acquisition_keeps_processing_while_audio_is_blocked(self):
        started, release = threading.Event(), threading.Event()
        def player(job, cancel, on_start):
            on_start(time.perf_counter())
            started.set()
            while not release.is_set() and not cancel.wait(0.001):
                pass
        audio = AudioWorker(player=player)
        try:
            audio.submit(AudioJob(np.ones(1500), 1000))
            self.assertTrue(started.wait(1))
            self.assertTrue(audio.busy)
            with self.assertRaises(AudioBusyError):
                audio.submit(AudioJob(np.ones(100), 1000))
            methods = load_methods('pyBEHAVIOR_v8.py', {'acquisition_loop', '_process_audio_events'})
            methods.update(time=time, queue=queue)
            app = SimpleNamespace(rate_hz=Var('1000'), callback_s=Var('0.001'),
                parse_float=lambda var, default: float(var.get()),
                simulation_mode=Var(True), ai_task=None, running=True,
                simulate_data=lambda count, rate: ([[0]], [0]),
                stop_at_trial_limit=Mock(), plot_queue=queue.Queue(),
                _audio_worker=audio, _audio_requests={})
            app._process_audio_events = MethodType(methods['_process_audio_events'], app)
            app.processed = 0
            def handle(times, rows):
                app.processed += 1
                if app.processed == 20:
                    app.running = False
            app.handle_data = handle
            acquisition = threading.Thread(target=lambda: methods['acquisition_loop'](app))
            acquisition.start()
            acquisition.join(2)
            self.assertFalse(acquisition.is_alive())
            self.assertEqual(app.processed, 20)
            self.assertTrue(audio.busy)  # Playback was not allowed to finish.
            release.set()
            self.assertTrue(audio.wait_idle(1))
        finally:
            release.set()
            self.assertTrue(audio.stop())

    def test_stop_cancels_active_playback_and_closes_worker(self):
        entered, owner = threading.Event(), []
        def player(job, cancel, started):
            owner.append(threading.current_thread().name)
            started(time.perf_counter())
            entered.set()
            cancel.wait(10)
        audio = AudioWorker(player=player)
        audio.submit(AudioJob(np.ones(1500), 1000))
        self.assertTrue(entered.wait(1))
        self.assertTrue(audio.stop(1))
        self.assertEqual(owner, ['pyBEHAVIOR-audio'])
        events = list(audio.events.queue)
        self.assertEqual(events[-1]['status'], 'cancelled')
        with self.assertRaises(RuntimeError):
            audio.submit(AudioJob(np.ones(100), 1000))

    def test_output_conflict_is_reported_instead_of_delayed(self):
        output = threading.Lock()
        output.acquire()
        player = Mock()
        audio = AudioWorker(player=player, output_lock=output)
        try:
            audio.submit(AudioJob(np.ones(100), 1000))
            self.assertTrue(audio.wait_idle(1))
            event = audio.events.get_nowait()
            self.assertEqual(event['status'], 'error')
            self.assertIn('occupied', event['error'])
            player.assert_not_called()
        finally:
            output.release()
            self.assertTrue(audio.stop())

    def test_next_trial_waits_for_busy_and_buffered_playback_end(self):
        app = trial_harness()
        app._audio_worker = SimpleNamespace(busy=True)
        app.check_trigger([0, 1], [0, 0])
        app.start_active_dmts_trial.assert_not_called()
        app._audio_worker.busy = False
        app._audio_block_until_s = 3
        app.check_trigger([2.9], [0])
        app.start_active_dmts_trial.assert_not_called()
        app.check_trigger([3.0], [0])
        app.start_active_dmts_trial.assert_called_once()

    def test_actual_start_is_recorded_and_playback_failure_requests_stop(self):
        method = load_methods('pyBEHAVIOR_v8.py', {'_process_audio_events'})
        method.update(queue=queue)
        events = queue.Queue()
        events.put({'kind': 'started', 'token': 'one', 'started_at': 102.7})
        events.put({'kind': 'finished', 'token': 'one', 'started_at': 102.7,
                    'ended_at': 103.2, 'status': 'error', 'error': 'device failed'})
        row = {}
        app = SimpleNamespace(_audio_worker=SimpleNamespace(events=events),
            _audio_requests={'one': {'row': row, 'origin': 100,
                'path': 'noise.wav', 'job': AudioJob(np.ones(1500), 1000)}},
            _audio_block_until_s=-1e12, record_sound_output=Mock(),
            write_trial_log=Mock(), plot_queue=queue.Queue(), running=True)
        method['_process_audio_events'](app)
        self.assertAlmostEqual(row['punishment_sound_start_s'], 2.7)
        self.assertAlmostEqual(app.record_sound_output.call_args.kwargs['start_s'], 2.7)
        self.assertEqual(row['punishment_sound_status'], 'error')
        self.assertEqual(row['punishment_sound_error'], 'device failed')
        self.assertFalse(app.running)
        self.assertIn(('stop_session', None), list(app.plot_queue.queue))
        self.assertAlmostEqual(app._audio_block_until_s, 3.2)

    def test_normal_sound_is_rejected_during_punishment(self):
        method = load_methods('pyBEHAVIOR_v8.py', {'play_loaded_sound'})['play_loaded_sound']
        app = SimpleNamespace(_audio_worker=SimpleNamespace(busy=True),
                              plot_queue=queue.Queue(), get_sound_by_id=Mock())
        self.assertIsNone(method(app, sound_id=1))
        app.get_sound_by_id.assert_not_called()

    def test_simulated_audio_never_imports_or_opens_hardware(self):
        started = Mock()
        with patch.dict('sys.modules', {'nidaqmx': None, 'sounddevice': None}):
            play_audio(AudioJob(np.ones(1), 1000, simulation=True), threading.Event(), started)
        started.assert_called_once()

    def test_stop_defers_resource_cleanup_until_workers_finish(self):
        method = load_methods('pyBEHAVIOR_v8.py', {'stop_live'})['stop_live']
        audio = SimpleNamespace(request_stop=Mock(), is_alive=lambda: True)
        app = SimpleNamespace(_audio_worker=audio, acq_thread=None,
            cancel_reward_train=Mock(), set_status=Mock(), after=Mock(return_value='poll'),
            _poll_stop_live=Mock(), close_tasks=Mock(), close_behavior_signal_file=Mock(), running=True)
        method(app)
        audio.request_stop.assert_called_once()
        app.close_tasks.assert_not_called()
        app.close_behavior_signal_file.assert_not_called()
        self.assertFalse(app.running)
        self.assertEqual(app._stop_after_id, 'poll')

    def test_final_stop_drains_audio_before_closing_files_and_window(self):
        method = load_methods('pyBEHAVIOR_v8.py', {'stop_live'})['stop_live']
        order = []
        app = SimpleNamespace(_audio_worker=SimpleNamespace(request_stop=Mock(), is_alive=lambda: False),
            acq_thread=SimpleNamespace(is_alive=lambda: False), running=False,
            _close_after_stop=True, cancel_reward_train=Mock(), active_trial_index=None,
            _process_audio_events=lambda: order.append('audio'),
            close_behavior_signal_file=lambda: order.append('files'),
            close_tasks=lambda: order.append('tasks'),
            update_session_history=Mock(), output_format=Var('BIDS'),
            set_status=Mock(), update_health_readouts=Mock(), log=Mock(),
            destroy=lambda: order.append('window'))
        method(app)
        self.assertEqual(order, ['audio', 'files', 'tasks', 'window'])

    def test_ni_cancel_stops_closes_and_zeros_output_on_audio_thread(self):
        entered = threading.Event()
        calls = []
        class Task:
            def __init__(self):
                self.ao_channels = SimpleNamespace(add_ao_voltage_chan=lambda *a: mark('channel'))
                self.timing = SimpleNamespace(cfg_samp_clk_timing=lambda *a, **k: mark('timing'))
                mark('create')
            def write(self, values, **kwargs):
                mark('zero' if isinstance(values, float) and values == 0 else 'write')
            def start(self):
                mark('start'); entered.set()
            def is_task_done(self):
                mark('poll'); return False
            def stop(self):
                mark('stop')
            def close(self):
                mark('close')
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.close()
        def mark(name):
            calls.append((name, threading.current_thread().name))
        ni = SimpleNamespace(Task=Task)
        constants = SimpleNamespace(AcquisitionType=SimpleNamespace(FINITE='finite'))
        with patch.dict('sys.modules', {'nidaqmx': ni, 'nidaqmx.constants': constants}):
            audio = AudioWorker()
            try:
                audio.submit(AudioJob(np.ones(1500), 1000))
                self.assertTrue(entered.wait(1))
                self.assertTrue(audio.stop(1))
            finally:
                audio.stop()
        names = [name for name, owner in calls]
        self.assertIn('stop', names)
        self.assertIn('zero', names)
        self.assertLess(names.index('stop'), names.index('zero'))
        self.assertTrue(all(owner == 'pyBEHAVIOR-audio' for _, owner in calls))
