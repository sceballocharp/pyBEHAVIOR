"""DMTS modality probabilities and exclusive sound/LED routing."""
import math
import random
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_lever_modes import load_methods, Var
from test_dmts_trial_start import harness

NAMES = {'get_dmts_modality_probabilities', 'prepare_next_dmts_light_trial',
         'start_active_dmts_trial', 'session_requires_sound_file'}
METHODS = load_methods('pyBEHAVIOR_v8.py', NAMES)
METHODS.update(math=math, random=random)

class ModalityTests(unittest.TestCase):
    def app(self, probabilities='0.5 0.5', trial_type=1):
        app = harness()
        for name in NAMES:
            setattr(app, name, MethodType(METHODS[name], app))
        app.dmts_modality_probabilities = Var(probabilities)
        app.dmts_light_client = Mock()
        app._dmts_light_active = None
        app._dmts_light_pending = None
        app.fail_dmts_light_trial = Mock()
        app.consume_next_dmts_trial_type.return_value = trial_type
        app.dmts_light_client.prepare.return_value = {'sample_id': 7, 'test_id': 7}
        return app

    def test_probabilities_require_two_finite_numbers_summing_to_one(self):
        for text in ('0.5 0.5', '1 0', '0 1', '0.75 0.25'):
            self.assertAlmostEqual(sum(self.app(text).get_dmts_modality_probabilities()), 1)
        for text in ('1 1', '0 0', '-0.1 1.1', 'nan 1', 'inf 0', '0.5', 'x y', '0.2 0.3'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.app(text).get_dmts_modality_probabilities()

    def test_sound_never_prepares_led_and_blank_has_no_stimulus(self):
        for trial_type in (0, 1, 2):
            app = self.app('1 0', trial_type)
            app._dmts_light_active = {'trial_id': 'previous-light'}
            self.assertTrue(app.prepare_next_dmts_light_trial())
            app.dmts_light_client.reset.assert_called_once()
            app.dmts_light_client.prepare.assert_not_called()
            self.assertIsNone(app._dmts_light_pending)
            self.assertEqual(app._dmts_trial_modality, 'blank' if trial_type == 0 else 'sound')
            app.prepare_next_dmts_light_trial()
            app.consume_next_dmts_trial_type.assert_called_once()

    def test_light_preserves_match_nonmatch_and_blank_skips_driver(self):
        for trial_type in (0, 1, 2):
            app = self.app('0 1', trial_type)
            self.assertTrue(app.prepare_next_dmts_light_trial())
            if trial_type:
                app.dmts_light_client.prepare.assert_called_once_with(trial_type)
                self.assertEqual(app._dmts_trial_modality, 'light')
            else:
                app.dmts_light_client.prepare.assert_not_called()
                self.assertEqual(app._dmts_trial_modality, 'blank')

    def test_modality_draw_uses_probabilities_after_trial_type(self):
        app = self.app('0.75 0.25', 2)
        with patch.object(random, 'choices', return_value=['sound']) as draw:
            self.assertTrue(app.prepare_next_dmts_light_trial())
        draw.assert_called_once_with(['sound', 'light'], weights=[0.75, 0.25], k=1)
        self.assertEqual(app._dmts_trial_pending['trial_type'], 2)
        app.dmts_light_client.prepare.assert_not_called()

    def test_mixed_session_still_requires_sound_file(self):
        app = self.app()
        app.play_sound_on_crossing = Var(True)
        app.is_tac_pretraining_task = lambda: False
        app.sequence_has_sound = lambda: True
        self.assertTrue(app.session_requires_sound_file())
        app.dmts_modality_probabilities.set('0 1')
        self.assertFalse(app.session_requires_sound_file())

    def test_both_sample_and_test_use_only_selected_output(self):
        from test_dmts_choices import harness as choice_harness
        for modality in ('sound', 'light', 'blank'):
            with self.subTest(modality=modality):
                app, row = choice_harness()
                app.start_active_dmts_trial = MethodType(METHODS['start_active_dmts_trial'], app)
                app.sound_duration_s, app.delay_s = Var('0.2'), Var('1')
                app.response_window_s, app.reward_delay_s = Var('1'), Var('0.1')
                app.window_s = Var('10')
                app.get_reward_pulse_s = lambda side: 0.04
                app.dmts_plot_windows = []
                app.parse_float = lambda var, default: float(var.get())
                app.start_trial_state_interval = Mock()
                app.trial_index = 1
                app.play_sound_on_crossing = Var(True)
                app.play_loaded_sound = Mock()
                app.trigger_dmts_light_phase = Mock(return_value=True)
                app.dmts_light_client = Mock()
                app._dmts_trial_modality = modality
                ids = (0, 0) if modality == 'blank' else (7, 7)
                app.start_active_dmts_trial(0, 2, *ids)
                app.update_active_dmts_trial(1.2, False, False, False)
                if modality == 'sound':
                    self.assertEqual(app.play_loaded_sound.call_count, 2)
                    app.trigger_dmts_light_phase.assert_not_called()
                elif modality == 'light':
                    app.play_loaded_sound.assert_not_called()
                    self.assertEqual([c.args[0] for c in app.trigger_dmts_light_phase.call_args_list], ['sample', 'test'])
                else:
                    app.play_loaded_sound.assert_not_called()
                    app.trigger_dmts_light_phase.assert_not_called()
