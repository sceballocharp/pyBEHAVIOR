import unittest

from types import SimpleNamespace

from unittest.mock import Mock

from test_lever_modes import load_methods



DRAW=load_methods('pyBEHAVIOR_v8.py', {'_draw_rate_panel'})['_draw_rate_panel']

def row(kind, result, ended=True):

    return {'TrialType':kind,'ResultType':result,'trial_end_s':'1' if ended else ''}

def curves(rows):

    app=SimpleNamespace(_draw_polyline=Mock(), _draw_smart_task_boundaries=Mock(),
                        _draw_trial_number_ticks=Mock()); canvas=Mock()

    DRAW(app,canvas,rows,0,100,0,100)

    return {c.args[2]:c.args[1] for c in app._draw_polyline.call_args_list},canvas



class MovingPerformanceTests(unittest.TestCase):

    def test_independent_windows_hold_between_each_type(self):

        lines,_=curves([row('GO','HIT')]*9+[row('noGo','FA')]*9+
                       [row('GO','HIT'),row('noGo','FA'),row('GO','MISS'),row('noGo','CR')])

        self.assertEqual(len(lines['#2ca02c']),4)
        for actual,expected in zip([p[1] for p in lines['#2ca02c']],[0,0,100/11,100/11]):
            self.assertAlmostEqual(actual,expected)

        for actual,expected in zip([p[1] for p in lines['#1f77b4']],[100,100,1000/11]):
            self.assertAlmostEqual(actual,expected)

        self.assertAlmostEqual(lines['#1f77b4'][0][0],1900/21)



    def test_only_last_25_of_each_type(self):

        rows=[row('GO','MISS')]*25+[row('GO','HIT')]*25+[row('noGo','CR')]*25

        lines,canvas=curves(rows)

        self.assertEqual(lines['#2ca02c'][-1][1],0)

        self.assertEqual(lines['#1f77b4'][-1][1],0)

        labels=[c.kwargs.get('text','') for c in canvas.create_text.call_args_list]

        self.assertIn('GO HIT 100% (n=25)',labels)

        self.assertIn('NoGo CR 100% (n=25)',labels)



    def test_unfinished_and_blank_do_not_enter_denominators(self):

        lines,_=curves([row('GO','HIT')]*10+[row('GO','MISS',False),row('BLANK','BLANK')])

        self.assertEqual([p[1] for p in lines['#2ca02c']],[0,0])

        self.assertNotIn('#1f77b4',lines)



    def test_dmts_wrong_match_choice_stays_in_match_rate(self):

        lines,_=curves([row('DMTS-match','HIT')]*9+[row('DMTS-match','FA'),row('DMTS-nonmatch','CR')])

        for point in lines['#2ca02c']:
            self.assertAlmostEqual(point[1],10)

        self.assertNotIn('#1f77b4',lines)


    def test_lines_wait_for_ten_trials_per_type(self):
        lines,canvas=curves([row('GO','HIT')]*9+[row('noGo','CR')]*9)
        self.assertEqual(lines,{})
        labels=[c.kwargs.get('text','') for c in canvas.create_text.call_args_list]
        self.assertIn('GO HIT waiting (9/10)',labels)
        self.assertIn('NoGo CR waiting (9/10)',labels)
        lines,_=curves([row('GO','HIT')]*10+[row('noGo','CR')]*9)
        self.assertIn('#2ca02c',lines)
        self.assertNotIn('#1f77b4',lines)
