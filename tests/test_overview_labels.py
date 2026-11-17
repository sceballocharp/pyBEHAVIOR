import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

class TaskLabelTests(unittest.TestCase):
    def test_sequence_labels_follow_selected_task(self):
        path=Path(__file__).resolve().parents[1]/'pyBEHAVIOR_v8.py'
        tree=ast.parse(path.read_text(encoding='utf-8'))
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='update_task_parameter_visibility')
        namespace={}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
        for task,words in [('classic','GO / NoGo'),('dmts','Match / Non-match / Blank'),('tac','Left / Right')]:
            app=SimpleNamespace(**{n.attr:MagicMock(name=n.attr) for n in ast.walk(node)
                if isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=='self'})
            app.is_lever_task.return_value=False
            app.is_dmts_task.return_value=task=='dmts'
            app.is_tac_task.return_value=task=='tac'
            app.is_tac_pretraining_task.return_value=False
            app.is_tac_family_task.return_value=task=='tac'
            app.is_lick_trigger.return_value=False
            namespace['update_task_parameter_visibility'](app)
            label=app.sequence_weights_widgets[0].configure.call_args.kwargs['text']
            self.assertIn(words,label)

    def test_button_and_header_scope_are_explicit(self):
        source=(Path(__file__).resolve().parents[1]/'pyBEHAVIOR_v8.py').read_text(encoding='utf-8')
        self.assertNotIn('text="Results Figure"',source)
        self.assertIn('text="Session Overview", command=self.open_results_window',source)
        self.assertNotIn('Session-wide:',source)
        self.assertIn('Moving rates: last 25 per type (min 10)',source)
