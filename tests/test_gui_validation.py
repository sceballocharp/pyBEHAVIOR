"""Inline validation rules and last-valid runtime values, without hardware."""
import unittest
import tkinter as tk
from types import SimpleNamespace, MethodType
from pathlib import Path
import math
import random
import ast
from unittest.mock import Mock
from gui_validation import EntryValidation, ValidatedSettings, validate_setting
from test_lever_modes import load_methods


class ValidationTests(unittest.TestCase):
    def test_bad_numeric_drafts_keep_last_valid_value(self):
        settings = ValidatedSettings()
        settings.external('rate_hz', '1000')
        for draft in ('', '-', '.', 'nan', 'inf', '-1', '0', 'oops'):
            settings.edit('rate_hz', draft)
            self.assertTrue(settings.errors['rate_hz'])
            self.assertEqual(settings.drafts['rate_hz'], draft)
            self.assertEqual(settings.active['rate_hz'], '1000')
        settings.edit('rate_hz', '2000')
        self.assertEqual(settings.active['rate_hz'], '2000')
        self.assertFalse(settings.errors['rate_hz'])

    def test_two_probabilities_are_committed_together(self):
        settings = ValidatedSettings()
        settings.external('dmts_modality_probabilities', '0.5 0.5')
        for text in ('0.8 0.5', '0.8', '1 1', '-0.1 1.1'):
            settings.edit('dmts_modality_probabilities', text)
            self.assertEqual(settings.active['dmts_modality_probabilities'], '0.5 0.5')
        settings.edit('dmts_modality_probabilities', '0.8, 0.2')
        self.assertEqual(settings.active['dmts_modality_probabilities'], '0.8 0.2')

    def test_sequence_ids_and_weights_update_as_a_valid_pair(self):
        settings = ValidatedSettings()
        settings.external('sequence_values', '1 10')
        settings.external('sequence_weights', '0.5 0.5')
        settings.edit('sequence_values', '1 10 0')
        self.assertEqual(settings.active['sequence_values'], '1 10')
        settings.edit('sequence_weights', '0.4 0.4 0.2')
        self.assertEqual(settings.active['sequence_values'], '1 10 0')
        self.assertEqual(settings.active['sequence_weights'], '0.4 0.4 0.2')
        settings.edit('sequence_weights', '0 0 0')
        self.assertEqual(settings.active['sequence_weights'], '0.4 0.4 0.2')

    def test_axis_limits_preserve_valid_pair_during_edits(self):
        settings = ValidatedSettings()
        settings.external('left_y_min', '-1')
        settings.external('left_y_max', '5')
        settings.edit('left_y_min', '8')
        self.assertEqual(settings.active['left_y_min'], '-1')
        settings.edit('left_y_max', '10')
        self.assertEqual(settings.active['left_y_min'], '8')
        self.assertEqual(settings.active['left_y_max'], '10')

    def test_counts_probabilities_and_signed_thresholds(self):
        for name, text in [('max_trials', '1.5'), ('dmts_reminder_trials', '0'),
                           ('reward_go', '1.1'), ('pavlov', '-0.1'), ('hit_threshold_s', '101')]:
            self.assertTrue(validate_setting(name, text, {}), (name, text))
        for name, text in [('max_trials', '0'), ('threshold_v', '-0.3'),
                           ('hit_threshold_s', '100'), ('reward_go', '0.5')]:
            self.assertFalse(validate_setting(name, text, {}), (name, text))

    def test_optional_defaults_and_string_seeds_are_preserved(self):
        for name in ('reward_go', 'min_lick_count', 'iti_rand_min_s', 'random_seed', 'task_type'):
            self.assertFalse(validate_setting(name, '', {}))
        self.assertFalse(validate_setting('random_seed', 'experiment-A', {}))

    def test_channel_lists_and_ranges(self):
        for text in ('ai0,ai1', 'ai0:ai6', 'ai0; ai1'):
            self.assertFalse(validate_setting('channels', text, {}), text)
        for text in ('ai6:ai0', 'ai0:ai3,ai5', 'ai', 'Dev1/ai0'):
            self.assertTrue(validate_setting('channels', text, {}), text)
        self.assertTrue(validate_setting('tac_left_channel', 'ai0', {'tac_right_channel': 'ai0'}))

    def test_sound_ranges_and_dmts_codes(self):
        self.assertFalse(validate_setting('dmts_sound_ids', '1:16, 20-25; 30', {}))
        for text in ('1:', '0:10', 'one', '1::5'):
            self.assertTrue(validate_setting('dmts_sound_ids', text, {}), text)
        self.assertTrue(validate_setting('sequence_values', '1 10', {'task_type': 'DMTS'}))

    def test_path_validation_does_not_probe_network(self):
        self.assertFalse(validate_setting('save_root', r'\\server\data', {}))
        self.assertTrue(validate_setting('save_root', '', {}))
        self.assertTrue(validate_setting('sound_file', 'bad?.mat', {}))

    def test_programmatic_changes_refresh_the_next_valid_baseline(self):
        settings = ValidatedSettings()
        settings.external('sound_level', '1')
        settings.external('sound_level', '2')
        settings.edit('sound_level', 'oops')
        self.assertEqual(settings.active['sound_level'], '2')


class EntryBindingTests(unittest.TestCase):
    def setUp(self):
        self.interpreter = tk.Tcl()
        self.manager = EntryValidation()

    def field(self, name, value):
        manager = self.manager
        field = SimpleNamespace(source=tk.StringVar(self.interpreter, value),
                                draft=tk.StringVar(self.interpreter, value), show_error=Mock())
        manager.fields[name] = field
        manager.model.external(name, value)
        field.draft.trace_add('write', lambda *_: manager.refresh(name, field.draft.get()))
        field.source.trace_add('write', lambda *_: manager.refresh(name, field.source.get(), external=True))
        return field

    def test_invalid_draft_never_reaches_runtime_variable(self):
        field = self.field('sound_level', '1')
        field.draft.set('oops')
        self.assertEqual(field.source.get(), '1')
        self.assertEqual(field.draft.get(), 'oops')
        self.assertTrue(field.show_error.call_args.args[0])
        field.draft.set('0.75')
        self.assertEqual(field.source.get(), '0.75')
        self.assertFalse(field.show_error.call_args.args[0])

    def test_smarttask_source_update_refreshes_display(self):
        self.field('sequence_values', '1 10')
        weights = self.field('sequence_weights', '0.5 0.5')
        weights.source.set('0.2 0.8')
        self.assertEqual(weights.draft.get(), '0.2 0.8')
        weights.draft.set('0.2')
        self.assertEqual(weights.source.get(), '0.2 0.8')

    def test_grouped_edit_updates_runtime_only_when_both_fields_valid(self):
        values = self.field('sequence_values', '1 10')
        weights = self.field('sequence_weights', '0.5 0.5')
        values.draft.set('1 10 0')
        self.assertEqual(values.source.get(), '1 10')
        weights.draft.set('0.4 0.4 0.2')
        self.assertEqual(values.source.get(), '1 10 0')
        self.assertEqual(weights.source.get(), '0.4 0.4 0.2')

    def test_imported_nogo_id_survives_nested_validation_and_sequence_generation(self):
        methods = load_methods('pyBEHAVIOR_v8.py', {
            'sync_classic_sound_ids', 'generate_sequence', '_parse_number_list',
            'read_parameters_file', 'classify_trial_sound', 'apply_imported_parameters'})
        methods.update(math=math, random=random)
        app = SimpleNamespace(is_lever_task=lambda: False, is_dmts_task=lambda: False,
                              is_tac_family_task=lambda: False, is_tac_task=lambda: False,
                              is_tac_pretraining_task=lambda: False,
                              ensure_sequence_controls=Mock(), update_sequence_display=Mock(),
                              update_task_parameter_visibility=Mock(), update_trial_duration=Mock(), log=Mock(),
                              parse_int=lambda var, default: int(var.get()),
                              sequence_length=tk.StringVar(self.interpreter, '100'),
                              random_seed=tk.StringVar(self.interpreter, '0'))
        for name, value in [('sequence_values', '1 10'), ('sequence_weights', '0.5 0.5'),
                            ('classic_go_sound_id', '1'), ('classic_nogo_sound_id', '10')]:
            setattr(app, name, self.field(name, value).source)
        for name in ('sync_classic_sound_ids', 'generate_sequence', '_parse_number_list',
                     'read_parameters_file', 'classify_trial_sound', 'apply_imported_parameters'):
            setattr(app, name, MethodType(methods[name], app))
        app._entry_validation = self.manager
        source = Path(__file__).resolve().parents[1] / 'pyBEHAVIOR_v8.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        importer = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'apply_imported_parameters')
        mapping = next(n.value for n in ast.walk(importer) if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'mapping' for t in n.targets))
        for value in mapping.values:
            if isinstance(value, ast.Attribute) and not hasattr(app, value.attr):
                setattr(app, value.attr, tk.StringVar(self.interpreter, ''))
        app.sound_id = tk.StringVar(self.interpreter, '1')
        app.sequence_values.trace_add('write', lambda *_: app.sync_classic_sound_ids())
        for var in (app.classic_go_sound_id, app.classic_nogo_sound_id):
            var.trace_add('write', lambda *_: app.sync_classic_sound_ids(from_fields=True))
        protocol = Path(__file__).resolve().parents[1] / 'protocols' / 'go_nogo_parameters.dat'
        params = app.read_parameters_file(protocol)
        # A stale, incomplete UI draft must not override the imported protocol.
        self.manager.fields['sequence_weights'].draft.set('0.9')
        app.apply_imported_parameters(params)
        self.assertEqual(app.classic_nogo_sound_id.get(), params['NoGoSoundId'])
        self.assertEqual(app.sequence_values.get(), '1 15')
        self.assertEqual(set(app.sound_sequence), {1, 15})
        self.assertEqual(app.classify_trial_sound(15), (2, 'noGo'))
        self.assertNotIn(10, app.sound_sequence)
        self.assertEqual(app.sequence_weights.get(), '0.5 0.5')
        self.assertEqual(self.manager.fields['sequence_weights'].draft.get(), '0.5 0.5')
        self.assertFalse(app._importing_protocol)
        self.assertFalse(self.manager.updating)
        previous = list(app.sound_sequence)
        for invalid in ({'NoGoSoundId': 'oops'}, {'GoWeight': '0', 'NoGoWeight': '0'}):
            with self.assertRaises(ValueError):
                app.apply_imported_parameters(invalid)
            self.assertEqual(app.sound_sequence, previous)
        # Editing either UI direction must also preserve the linked values.
        self.manager.fields['classic_nogo_sound_id'].draft.set('20')
        self.assertEqual(app.sequence_values.get(), '1 20')
        app.sequence_values.set('2 25')
        self.assertEqual(app.classic_go_sound_id.get(), '2')
        self.assertEqual(app.classic_nogo_sound_id.get(), '25')
