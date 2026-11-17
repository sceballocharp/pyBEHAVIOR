"""Go/No-Go SmartTask thresholds and 25 + 25 trial blocks."""
import queue
import unittest
from types import MethodType, SimpleNamespace
from unittest.mock import Mock
from test_lever_modes import load_methods, Var

METHODS = load_methods('pyBEHAVIOR_v8.py', {'update_smart_task', 'update_gonogo_smart_task'})

def row(kind, outcome):
    return {'TrialType': kind, 'ResultType': outcome, 'trial_end_s': '1'}

def harness():
    app = SimpleNamespace(smart_task=Var(True), active_trial_index=None,
        is_dmts_task=lambda: False, is_lever_task=lambda: False,
        is_tac_family_task=lambda: False, sequence_weights=Var('0.5 0.5'),
        sequence_values=Var('3 10'), pavlov=Var('0.3'),
        trial_rows=[row('1 GO', 'HIT') for _ in range(10)] + [row('2 noGo', 'FA')],
        generate_sequence=Mock(), plot_queue=queue.Queue())
    for name in ('update_smart_task', 'update_gonogo_smart_task'):
        setattr(app, name, MethodType(METHODS[name], app))
    return app

class GoNoGoSmartTaskTests(unittest.TestCase):
    def test_full_blocks_and_protected_balanced_period(self):
        app = harness()
        app.update_smart_task()
        self.assertEqual(app.sequence_weights.get(), '0.2 0.8')
        self.assertEqual(app._smart_gonogo_phase, 'nogo')
        for i in range(24):
            app.trial_rows.append(row('2 noGo', 'FA'))
            app.update_smart_task()
            self.assertEqual(app._smart_gonogo_phase, 'nogo')
        app.trial_rows.append(row('2 noGo', 'FA'))
        app.update_smart_task()
        self.assertEqual(app.sequence_weights.get(), '0.5 0.5')
        self.assertEqual(app._smart_gonogo_phase, 'balanced')
        for i in range(24):
            app.trial_rows.append(row('2 noGo', 'FA'))
            app.update_smart_task()
            app.update_smart_task()  # repeated polling must not consume a trial
            self.assertEqual(app.sequence_weights.get(), '0.5 0.5')
        app.trial_rows.append(row('2 noGo', 'FA'))
        app.update_smart_task()
        self.assertEqual(app._smart_gonogo_phase, 'nogo')
        self.assertEqual(app.sequence_weights.get(), '0.2 0.8')
        self.assertEqual(app.generate_sequence.call_count, 3)
        self.assertEqual(app.sequence_values.get(), '3 10')
        self.assertEqual(app.pavlov.get(), '0.3')

    def test_strict_thresholds_and_both_categories_required(self):
        for hits, misses, crs, fas in ((9,1,0,10), (10,0,1,9), (10,0,0,0), (0,0,0,10)):
            app = harness()
            app.trial_rows = ([row('GO','HIT')]*hits + [row('GO','MISS')]*misses
                              + [row('noGo','CR')]*crs + [row('noGo','FA')]*fas)
            app.update_smart_task()
            app.generate_sequence.assert_not_called()

    def test_disabled_and_active_trial_do_not_trigger(self):
        app = harness()
        app.smart_task.set(False)
        app.update_smart_task()
        app.generate_sequence.assert_not_called()
        app.smart_task.set(True)
        app.active_trial_index = 1
        app.update_smart_task()
        app.generate_sequence.assert_not_called()

    def test_disabling_restores_balance_and_resets_cycle(self):
        app = harness()
        app.update_smart_task()
        app.smart_task.set(False)
        app.update_smart_task()
        self.assertEqual(app.sequence_weights.get(), '0.5 0.5')
        self.assertEqual(app._smart_gonogo_phase, 'idle')

    def test_unfinished_trials_do_not_count_and_improved_rates_release_cycle(self):
        app = harness()
        app.update_smart_task()
        app.trial_rows.extend(dict(row('noGo', 'FA'), trial_end_s='') for _ in range(30))
        app.update_smart_task()
        self.assertEqual(app._smart_gonogo_phase, 'nogo')
        app.trial_rows.extend(row('noGo', 'CR') for _ in range(25))
        app.update_smart_task()
        self.assertEqual(app._smart_gonogo_phase, 'balanced')
        app.trial_rows.extend(row('GO', 'HIT') for _ in range(25))
        app.update_smart_task()
        self.assertEqual(app._smart_gonogo_phase, 'idle')
        self.assertEqual(app.sequence_weights.get(), '0.5 0.5')
