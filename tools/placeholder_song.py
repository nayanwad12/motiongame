"""Synthesized 120 BPM placeholder groove (royalty-free by construction).

Stands in for the licensed song until one can be downloaded. It deliberately starts
with 0.37 s of silence and a hats-only intro bar so the beat/downbeat analysis in
audio.py has something real to find.

usage: python3 tools/placeholder_song.py out/placeholder_song.wav
"""
import sys
import numpy as np
from scipy.signal import lfilter
from wav import write_wav

SR = 44100
BPM = 120.0
BEAT = 60.0 / BPM
LEAD = 0.37                      # silence before the first downbeat
BARS = 16
N = int(SR * (LEAD + BARS * 4 * BEAT + 2))
rng = np.random.default_rng(7)
L = np.zeros(N)
R = np.zeros(N)


def at(t):
    return int(round((LEAD + t) * SR))


def add(sig, t, pan=0.0, g=1.0):
    i = at(t)
    j = min(N, i + len(sig))
    L[i:j] += sig[: j - i] * g * (1 - max(0, pan))
    R[i:j] += sig[: j - i] * g * (1 + min(0, pan))


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    return lfilter([1 - a], [1, -a], x)


def kick():
    n = int(.42 * SR)
    t = np.arange(n) / SR
    f = 46 + 110 * np.exp(-t / .035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / .16) * 0.95 + rng.standard_normal(n) * env(n, .0005, .004) * .25


def hat(open_=False):
    n = int((.16 if open_ else .05) * SR)
    x = rng.standard_normal(n)
    x = x - onepole_lp(x, 7000)
    return x * env(n, .0008, .06 if open_ else .014) * .32


def clap():
    n = int(.25 * SR)
    x = rng.standard_normal(n)
    x = onepole_lp(x - onepole_lp(x, 900), 5000)
    e = sum(env(n, .0005, .008) * (np.arange(n) >= int(k * SR)) for k in (0, .011, .022)) + env(n, .012, .09) * .8
    return x * e * .5


def saw(f, n):
    t = np.arange(n) / SR
    return 2 * ((t * f) % 1) - 1


def bass(f, dur):
    n = int(dur * SR)
    return onepole_lp(saw(f, n) * .7 + np.sin(2 * np.pi * f * np.arange(n) / SR) * .6, 380) * env(n, .004, .18) * .55


def chord(freqs, dur):
    n = int(dur * SR)
    x = sum(saw(f * d, n) for f in freqs for d in (0.997, 1.003)) / (2 * len(freqs))
    return onepole_lp(x, 1400) * env(n, .01, .5) * .42


# A minor: Am7 – Fmaj7 – Cmaj7 – G6
PROG = [
    (110.0, [220.0, 261.63, 329.63, 392.0]),
    (87.31, [174.61, 220.0, 261.63, 329.63]),
    (130.81, [261.63, 329.63, 392.0, 493.88]),
    (98.0, [196.0, 246.94, 293.66, 329.63]),
]

k, c, hh, oh = kick(), clap(), hat(), hat(True)
for bar in range(BARS):
    t0 = bar * 4 * BEAT
    root, notes = PROG[bar % 4]
    for b in range(4):
        tb = t0 + b * BEAT
        for s in range(4):
            add(hh, tb + s * BEAT / 4, pan=.35, g=.55 if s % 2 else .9)
        if bar == 0:
            continue                                   # hats-only intro bar
        add(k, tb)
        add(oh, tb + BEAT / 2, pan=-.3)
        if b in (1, 3):
            add(c, tb, g=.9)
        add(bass(root, BEAT * .45), tb + BEAT / 2)
        if b == 3:
            add(bass(root * 1.5, BEAT * .2), tb + BEAT * .75, g=.7)
    if bar:
        add(chord(notes, 1.8), t0 + BEAT * .5, pan=-.15)
        add(chord(notes, 0.9), t0 + BEAT * 2.5, pan=.15, g=.7)

mix = np.stack([L, R], 1)
mix /= np.abs(mix).max() / .89
write_wav(sys.argv[1] if len(sys.argv) > 1 else 'out/placeholder_song.wav', mix, SR)
print('placeholder song written')
