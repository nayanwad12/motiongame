"""Tiny audio I/O on top of ffmpeg + scipy (float32 stereo, 44.1 kHz)."""
import subprocess
import numpy as np
from scipy.io import wavfile

SR = 44100


def read_audio(path, ss=None, t=None, af=None):
    cmd = ['ffmpeg', '-v', 'error']
    if ss is not None:
        cmd += ['-ss', f'{ss:.6f}']
    cmd += ['-i', path]
    if t is not None:
        cmd += ['-t', f'{t:.6f}']
    if af:
        cmd += ['-af', af]
    cmd += ['-f', 'f32le', '-ac', '2', '-ar', str(SR), '-']
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def write_wav(path, x, sr=SR):
    wavfile.write(path, sr, np.clip(x, -1, 1).astype(np.float32))
