"""Read a standalone mono punishment WAV independently of task sound banks."""

from pathlib import Path
import numpy as np
from scipy.io import wavfile


def load_punishment_wav(path):
    path = Path(path).expanduser().resolve()
    rate, signal = wavfile.read(path)
    if rate <= 0 or signal.ndim != 1 or not signal.size:
        raise ValueError('FA noise must be a nonempty mono WAV')
    if np.issubdtype(signal.dtype, np.unsignedinteger):
        midpoint = (np.iinfo(signal.dtype).max + 1) / 2
        signal = (signal.astype(np.float64) - midpoint) / midpoint
    elif np.issubdtype(signal.dtype, np.signedinteger):
        scale = float(max(abs(np.iinfo(signal.dtype).min), np.iinfo(signal.dtype).max))
        signal = signal.astype(np.float64) / scale
    elif np.issubdtype(signal.dtype, np.floating):
        signal = signal.astype(np.float64)
    else:
        raise ValueError('Unsupported FA noise WAV format')
    if not np.all(np.isfinite(signal)):
        raise ValueError('FA noise WAV contains non-finite samples')
    return str(path), int(rate), signal
