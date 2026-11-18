"""Read-only Go/No-Go sequence preview and Canvas positions."""
import unittest
from types import SimpleNamespace, MethodType
from unittest.mock import Mock
from test_lever_modes import load_methods, Var

METHODS = load_methods('pyBEHAVIOR_v8.py', {'get_upcoming_gonogo_trials', 'get_upcoming_dmts_trials', '_draw_upcoming_trials'})

def harness():
    app = SimpleNamespace(is_dmts_task=lambda:False, is_lever_task=lambda:False,
        is_tac_family_task=lambda:False, max_trials=Var('0'), trial_index=0,
        trial_stimulus_sequence=[], sound_sequence=[3,10,3,10],
        sound_sequence_index=1, trial_stimulus_index=0,
        play_sound_on_crossing=Var(True), sound_id=Var('3'),
        parse_int=lambda var, default:int(var.get()),
        classify_trial_sound=lambda value:(1 if value==3 else 2 if value==10 else 0, ''))
    for name in ('get_upcoming_gonogo_trials', 'get_upcoming_dmts_trials', '_draw_upcoming_trials'):
        setattr(app,name,MethodType(METHODS[name],app))
    return app

class UpcomingTests(unittest.TestCase):
    def dmts(self):
        app = harness()
        app.is_dmts_task = lambda: True
        app.is_lick_trigger = lambda: True
        app.sound_sequence = [1, 2, 0]
        app.sound_sequence_index = 1
        return app

    def test_dmts_prepared_trial_precedes_wrapped_queue_without_mutation(self):
        import random
        app = self.dmts()
        app._dmts_trial_pending = {'trial_type': 1}
        state = random.getstate()
        self.assertEqual(app.get_upcoming_dmts_trials(5),
                         ['Match', 'NonMatch', 'Blank', 'Match', 'NonMatch'])
        self.assertEqual(app.sound_sequence_index, 1)
        self.assertEqual(app.sound_sequence, [1, 2, 0])
        self.assertEqual(app._dmts_trial_pending, {'trial_type': 1})
        self.assertEqual(random.getstate(), state)

    def test_dmts_light_pending_and_max_trials(self):
        app = self.dmts()
        app._dmts_light_pending = {'trial_type': 0}
        app.max_trials.set('5'); app.trial_index = 3
        self.assertEqual(app.get_upcoming_dmts_trials(), ['Blank', 'NonMatch'])
        app.trial_index = 5
        self.assertEqual(app.get_upcoming_dmts_trials(), [])

    def test_dmts_reminders_do_not_advance_normal_queue(self):
        app = self.dmts()
        app.dmts_reminder_remaining = 3
        app._dmts_trial_pending = {'trial_type': 1}
        self.assertEqual(app.get_upcoming_dmts_trials(5),
                         ['Match', 'Match', 'Match', 'NonMatch', 'Blank'])
        app._dmts_trial_pending = None
        app.active_trial_index = 1; app.active_dmts_reminder = True
        self.assertEqual(app.get_upcoming_dmts_trials(3), ['Match', 'Match', 'NonMatch'])
        app.smart_task = Var(True)
        self.assertEqual(app.get_upcoming_dmts_trials(2), ['NonMatch', 'Blank'])

    def test_dmts_drawing_labels_colors_and_blank(self):
        app = self.dmts(); canvas = Mock()
        app.sound_sequence_index = 0
        app._draw_upcoming_trials(canvas, 80, 480, 100, 200)
        blocks = canvas.create_rectangle.call_args_list[1:]
        self.assertEqual(blocks[0].kwargs['fill'], '#2ca02c')
        self.assertEqual(blocks[1].kwargs['fill'], '#1f77b4')
        self.assertGreater(blocks[0].args[1], blocks[1].args[1])
        labels = [c.kwargs.get('text') for c in canvas.create_text.call_args_list]
        for label in ('0 Match', '1 NonMatch', 'B', 'T', 'T+9'):
            self.assertIn(label, labels)

    def test_peek_wraps_without_changing_sequence_or_index(self):
        app=harness()
        self.assertEqual(app.get_upcoming_gonogo_trials(5),['NoGo','GO','NoGo','GO','NoGo'])
        self.assertEqual(app.sound_sequence_index,1)
        self.assertEqual(app.sound_sequence,[3,10,3,10])

    def test_limit_excludes_started_trials(self):
        app=harness();app.max_trials.set('5');app.trial_index=3
        self.assertEqual(len(app.get_upcoming_gonogo_trials()),2)
        app.trial_index=5
        self.assertEqual(app.get_upcoming_gonogo_trials(),[])

    def test_external_sequence_and_blank(self):
        app=harness();app.trial_stimulus_sequence=[{'trial_type_id':1},{'trial_type_id':2},{'trial_type_id':0}]
        app.trial_stimulus_index=1
        self.assertEqual(app.get_upcoming_gonogo_trials(3),['NoGo','Blank','GO'])
        self.assertEqual(app.trial_stimulus_index,1)

    def test_empty_and_other_tasks(self):
        app=harness();app.sound_sequence=[]
        self.assertEqual(app.get_upcoming_gonogo_trials(),[])
        app.is_dmts_task=lambda:True
        self.assertEqual(app.get_upcoming_gonogo_trials(),[])

    def test_drawing_places_go_below_nogo_and_labels_offsets(self):
        app=harness();canvas=Mock()
        app._draw_upcoming_trials(canvas,60,460,100,200)
        blocks=canvas.create_rectangle.call_args_list[1:]
        self.assertEqual(len(blocks),10)
        self.assertLess(blocks[0].args[1],blocks[1].args[1])
        labels=[c.kwargs.get('text') for c in canvas.create_text.call_args_list]
        self.assertIn('T',labels);self.assertIn('T+9',labels)
