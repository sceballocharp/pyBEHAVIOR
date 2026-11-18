"""Standalone punishment waveform loading and task-bank-independent playback."""
from pathlib import Path
import queue
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import numpy as np
from scipy.io import wavfile
from punishment_audio import load_punishment_wav
from test_lever_modes import load_methods, Var

ROOT = Path(__file__).resolve().parents[1]


class PunishmentAudioTests(unittest.TestCase):
    def test_default_asset_is_half_second_mono_at_192khz(self):
        path, rate, signal = load_punishment_wav(ROOT / 'Sounds/Punishment/white_noise.wav')
        self.assertEqual(rate, 192000)
        self.assertEqual(signal.shape, (96000,))
        self.assertTrue(np.all(np.isfinite(signal)))
        self.assertGreater(np.max(np.abs(signal)), 0)

    def test_pcm_is_converted_and_float_amplitude_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as folder:
            path = Path(folder) / 'noise.wav'
            wavfile.write(path, 48000, np.array([-32768, 0, 16384], dtype=np.int16))
            _, _, signal = load_punishment_wav(path)
            np.testing.assert_array_equal(signal, [-1, 0, 0.5])
            original = np.array([0.1, -1.2, 2.4], dtype=np.float64)
            wavfile.write(path, 192000, original)
            _, _, signal = load_punishment_wav(path)
            np.testing.assert_array_equal(signal, original)

    def test_invalid_wav_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as folder:
            path = Path(folder) / 'noise.wav'
            for signal in (np.ones((4, 2)), np.array([], dtype=float), np.array([np.nan])):
                wavfile.write(path, 48000, signal)
                with self.assertRaises(ValueError):
                    load_punishment_wav(path)

    def test_playback_uses_wav_and_three_repetitions_at_boosted_gain(self):
        methods = load_methods('pyBEHAVIOR_v8.py', {'play_fa_noise'})
        backend = SimpleNamespace(play=Mock())
        methods.update(np=np, nidaqmx=None, sd=backend)
        path = str(ROOT / 'Sounds/Punishment/white_noise.wav')
        app = SimpleNamespace(load_fa_noise=Mock(return_value=(path, 4, np.array([1.0, -1.0]))),
            get_sound_level_gain=lambda: 0.2, record_sound_output=Mock(), log=Mock(),
            get_sound_by_id=Mock(side_effect=AssertionError('Task bank must not be consulted')),
            plot_queue=queue.Queue())
        duration = methods['play_fa_noise'](app, from_worker=True, start_s=2.5)
        expected = np.array([0.25, -0.25] * 3)
        np.testing.assert_array_equal(backend.play.call_args.args[0], expected)
        self.assertEqual(backend.play.call_count, 1)
        self.assertEqual(duration, 1.5)
        self.assertEqual(app.record_sound_output.call_args.kwargs, {'sound_id': 0, 'start_s': 2.5})
        self.assertEqual(app._last_fa_noise_playback['path'], path)
        self.assertEqual(app._last_fa_noise_playback['gain'], 0.25)
        app.get_sound_by_id.assert_not_called()

    def test_light_only_noise_does_not_require_task_bank(self):
        methods = load_methods('pyBEHAVIOR_v8.py', {'session_requires_sound_file'})
        app = SimpleNamespace(is_dmts_task=lambda: True, dmts_light_client=Mock(),
            dmts_modality_probabilities=Var('0 1'), dmts_nonmatch_fa_noise=Var(True),
            get_dmts_modality_probabilities=lambda **kwargs: [0, 1])
        self.assertFalse(methods['session_requires_sound_file'](app))

    def test_test_button_does_not_interrupt_acquisition(self):
        methods = load_methods('pyBEHAVIOR_v8.py', {'play_fa_noise'})
        app = SimpleNamespace(running=True, log=Mock(), load_fa_noise=Mock())
        self.assertIsNone(methods['play_fa_noise'](app))
        app.load_fa_noise.assert_not_called()

    def test_cache_is_independent_of_mat_bank_and_reloads_selected_wav(self):
        methods = load_methods('pyBEHAVIOR_v8.py', {'load_fa_noise'})
        app = SimpleNamespace(fa_noise_file=Var('Sounds/Punishment/white_noise.wav'))
        original = methods['load_fa_noise'](app)
        self.assertTrue(Path(original[0]).is_absolute())
        app.sound_data = None
        app.sound_loaded = False
        app.sound_file = Var('a-different-task-bank.mat')
        self.assertIs(methods['load_fa_noise'](app), original)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests') as folder:
            path = Path(folder) / 'other.wav'
            wavfile.write(path, 48000, np.array([0.1, -0.1], dtype=np.float64))
            app.fa_noise_file.set(str(path))
            replacement = methods['load_fa_noise'](app)
            self.assertEqual(replacement[0], str(path.resolve()))
            self.assertEqual(replacement[1], 48000)
            np.testing.assert_array_equal(replacement[2], [0.1, -0.1])
