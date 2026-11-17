"""Read-only Go/No-Go sequence preview and Canvas positions."""
import unittest
from types import SimpleNamespace, MethodType
from unittest.mock import Mock
from test_lever_modes import load_methods, Var

METHODS = load_methods('pyBEHAVIOR_v8.py', {'get_upcoming_gonogo_trials', '_draw_upcoming_trials'})

def harness():
    app = SimpleNamespace(is_dmts_task=lambda:False, is_lever_task=lambda:False,
        is_tac_family_task=lambda:False, max_trials=Var('0'), trial_index=0,
        trial_stimulus_sequence=[], sound_sequence=[3,10,3,10],
        sound_sequence_index=1, trial_stimulus_index=0,
        play_sound_on_crossing=Var(True), sound_id=Var('3'),
        parse_int=lambda var, default:int(var.get()),
        classify_trial_sound=lambda value:(1 if value==3 else 2 if value==10 else 0, ''))
    for name in ('get_upcoming_gonogo_trials','_draw_upcoming_trials'):
        setattr(app,name,MethodType(METHODS[name],app))
    return app

class UpcomingTests(unittest.TestCase):
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
