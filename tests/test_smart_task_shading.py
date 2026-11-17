"""Recorded Go/No-Go phases are shaded independently of current SmartTask state."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace, MethodType
from unittest.mock import Mock
from test_lever_modes import load_methods

METHODS = load_methods('pyBEHAVIOR_v8.py', {'_draw_smart_task_shading', '_draw_recent_trial_strip', '_draw_trial_number_ticks', '_draw_smart_task_boundaries'})

class SmartTaskShadingTests(unittest.TestCase):
    def app(self):
        app=SimpleNamespace()
        for name in ('_draw_smart_task_shading','_draw_recent_trial_strip','_draw_trial_number_ticks','_draw_smart_task_boundaries'):
            setattr(app,name,MethodType(METHODS[name],app))
        return app

    def test_colors_and_historical_phase_are_preserved(self):
        app=self.app(); app._smart_gonogo_phase='idle'; canvas=Mock()
        rows=[{'smart_task_phase':'nogo'},{'smart_task_phase':'balanced'},{}]
        app._draw_smart_task_shading(canvas,rows,0,300,20,120)
        rectangles=canvas.create_rectangle.call_args_list
        self.assertEqual(len(rectangles),2)
        self.assertEqual(rectangles[0].args,(0,20,100,120))
        self.assertEqual(rectangles[0].kwargs['fill'],'#ffe6bf')
        self.assertEqual(rectangles[1].args,(100,20,200,120))
        self.assertEqual(rectangles[1].kwargs['fill'],'#e5dafa')
        labels=[c.kwargs['text'] for c in canvas.create_text.call_args_list]
        self.assertIn('Orange: NoGo emphasis',labels)
        self.assertIn('Purple: Balanced protected',labels)

    def test_only_last_80_trials_are_shaded_before_outcome_markers(self):
        app=self.app();canvas=Mock()
        app._draw_recent_trial_strip(canvas,[{'smart_task_phase':'nogo','ResultType':'HIT'}]*81,0,800,30,240)
        rectangles=canvas.create_rectangle.call_args_list
        shaded=[i for i,c in enumerate(rectangles) if c.kwargs.get('fill')=='#ffe6bf']
        outcomes=[i for i,c in enumerate(rectangles) if c.kwargs.get('fill')=='#2ca02c']
        self.assertEqual(len(shaded),80)
        self.assertEqual(len(outcomes),80)
        self.assertLess(max(shaded),min(outcomes))

    def test_phase_snapshot_is_classic_only_and_remains_after_transition(self):
        source=Path(__file__).resolve().parents[1]/'pyBEHAVIOR_v8.py'
        tree=ast.parse(source.read_text(encoding='utf-8'))
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='create_trial')
        value=next(v for n in ast.walk(method) if isinstance(n,ast.Dict)
                   for k,v in zip(n.keys,n.values) if isinstance(k,ast.Constant) and k.value=='smart_task_phase')
        code=compile(ast.Expression(body=value),'phase','eval')
        app=SimpleNamespace(_smart_gonogo_phase='nogo')
        saved=eval(code,{'self':app,'trial_type':'GO'})
        app._smart_gonogo_phase='balanced'
        self.assertEqual(saved,'nogo')
        self.assertEqual(eval(code,{'self':app,'trial_type':'noGo'}),'balanced')
        self.assertEqual(eval(code,{'self':app,'trial_type':'DMTS-match'}),'idle')

    def test_trial_ticks_use_recorded_trial_numbers_and_endpoints(self):
        app=self.app();canvas=Mock()
        rows=[{'trial':81+i} for i in range(80)]
        app._draw_trial_number_ticks(canvas,rows,0,400,100)
        labels=[c.kwargs['text'] for c in canvas.create_text.call_args_list]
        self.assertEqual(labels[0],'81')
        self.assertEqual(labels[-1],'160')
        self.assertLessEqual(len(labels),6)

    def test_transition_markers_only_at_phase_changes(self):
        app=self.app();canvas=Mock()
        rows=[{'smart_task_phase':phase} for phase in ('idle','nogo','nogo','balanced','balanced','idle')]
        app._draw_smart_task_boundaries(canvas,rows,0,500,0,100)
        calls=canvas.create_line.call_args_list
        self.assertEqual([c.args[0] for c in calls],[100,300,500])
        self.assertTrue(all(c.kwargs['dash']==(4,3) for c in calls))

    def test_all_four_outcome_rows_fit_compact_strip(self):
        app=self.app();canvas=Mock()
        rows=[{'ResultType':outcome,'trial':i+1} for i,outcome in enumerate(('HIT','MISS','CR','FA'))]
        app._draw_recent_trial_strip(canvas,rows,60,460,100,208)
        colors={'#2ca02c','#ff7f0e','#1f77b4','#d62728'}
        markers=[c for c in canvas.create_rectangle.call_args_list if c.kwargs.get('fill') in colors]
        self.assertEqual(len(markers),4)
        self.assertTrue(all(100<=c.args[1] and c.args[3]<=182 for c in markers))
