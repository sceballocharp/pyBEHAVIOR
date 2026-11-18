"""Real SmartTask -> sequence -> overview code, with strict GUI-thread checks.

No Tk window, sound output, NI hardware or experimental data is used.
"""
import math
import queue
import random
import statistics
import threading
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock
from test_lever_modes import load_methods, Var


NAMES = {'update_smart_task', 'update_gonogo_smart_task', 'generate_sequence',
         '_parse_number_list', 'update_sequence_display', 'redraw_results_window',
         'get_upcoming_gonogo_trials', 'classify_trial_sound', '_drain_plot_queue',
         '_draw_recent_trial_strip', '_draw_rate_panel', '_draw_condition_panel',
         '_draw_crossing_duration_panel', '_draw_polyline', '_draw_upcoming_trials',
         '_draw_smart_task_shading', '_draw_smart_task_boundaries', '_draw_trial_number_ticks'}
METHODS = load_methods('pyBEHAVIOR_v8.py', NAMES)
METHODS.update(math=math, random=random, statistics=statistics, threading=threading, queue=queue)


class StrictCanvas:
    def __init__(self, open_window=True):
        self.draw_calls = 0
        self.open_window = open_window

    def __getattr__(self, name):
        def call(*args, **kwargs):
            if threading.current_thread() is not threading.main_thread():
                raise RuntimeError('Canvas accessed outside the GUI thread: ' + name)
            if name == 'winfo_width':
                return 1100
            if name == 'winfo_height':
                return 700
            self.draw_calls += 1
        return call


def row(kind, result, number):
    return {'TrialType': kind, 'ResultType': result, 'trial_end_s': '1',
            'trial': number, 'sound_id': 3 if kind.endswith('GO') else 15,
            'smart_task_phase': 'idle'}


def harness(overview=True):
    app = SimpleNamespace(smart_task=Var(True), smart_nogo_emphasis_trials=Var('25'),
        active_trial_index=None, is_dmts_task=lambda: False, is_lever_task=lambda: False,
        is_tac_family_task=lambda: False, is_tac_task=lambda: False,
        is_tac_pretraining_task=lambda: False,
        sequence_weights=Var('0.5 0.5'), sequence_values=Var('3 15'),
        sequence_length=Var('300'), random_seed=Var('42'),
        sequence_index_var=Var('0'), sequence_next_var=Var('3'), sound_id=Var('3'),
        max_trials=Var('0'), trial_index=20, sound_sequence=[3, 15], sound_sequence_index=0,
        trial_stimulus_sequence=[], trial_stimulus_index=0, play_sound_on_crossing=Var(True),
        ensure_sequence_controls=Mock(), parse_int=lambda var, default: int(var.get()),
        trial_rows=[row('1 GO', 'HIT', i+1) for i in range(10)]
                   + [row('2 noGo', 'FA', i+11) for i in range(10)],
        plot_queue=queue.Queue(), dict_across_trials={},
        results_canvas=StrictCanvas() if overview else None,
        results_window=SimpleNamespace(winfo_exists=lambda: overview),
        update_hit_performance_background=Mock(), update_health_readouts=Mock(),
        log=Mock(), set_status=Mock(), after=Mock())
    for name in NAMES:
        setattr(app, name, MethodType(METHODS[name], app))
    return app


class SmartTaskIntegrationTests(unittest.TestCase):
    def test_worker_transition_queues_overview_refresh_for_gui_thread(self):
        app = harness()
        errors = []
        def worker():
            try:
                app.update_smart_task()
            except BaseException as exc:
                errors.append(exc)
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(app._smart_gonogo_phase, 'nogo')
        self.assertEqual(app.sequence_weights.get(), '0.2 0.8')
        self.assertEqual(set(app.sound_sequence), {3, 15})
        self.assertEqual(app.results_canvas.draw_calls, 0)
        app._drain_plot_queue()
        self.assertGreater(app.results_canvas.draw_calls, 0)

    def test_two_thousand_trials_with_overview_open_and_closed(self):
        for overview in (True, False):
            with self.subTest(overview=overview):
                app = harness(overview)
                transitions, errors = [], []
                def worker():
                    try:
                        for i in range(2000):
                            before = getattr(app, '_smart_gonogo_phase', 'idle')
                            app.update_smart_task()
                            phase = app._smart_gonogo_phase
                            if phase != before:
                                transitions.append(phase)
                            kind, result = ('1 GO', 'HIT') if i % 2 else ('2 noGo', 'FA')
                            app.trial_index += 1
                            entry = row(kind, result, app.trial_index)
                            entry['smart_task_phase'] = phase
                            app.trial_rows.append(entry)
                    except BaseException as exc:
                        errors.append(exc)
                thread = threading.Thread(target=worker)
                thread.start()
                thread.join(15)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertGreaterEqual(len(transitions), 70)
                self.assertEqual(transitions[:4], ['nogo', 'balanced', 'nogo', 'balanced'])
                self.assertEqual(app.sequence_values.get(), '3 15')
                app._drain_plot_queue()
                if overview:
                    self.assertGreater(app.results_canvas.draw_calls, 0)
