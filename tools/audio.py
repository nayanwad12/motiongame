"""Beat-grid analysis, UI sound design and the 14 s loop mix.

  python3 tools/audio.py SONG [--cues out/cues.json] [--out out/audio.wav]

1. Analyse SONG with numpy: onset envelope → tempo (autocorrelation) → beat phase
   (comb) → least-squares grid fit → downbeat (harmonic change per bar position).
2. Cut 7 bars starting on a downbeat (time-stretched to exactly 120 BPM if needed).
3. Synthesize every UI sound, measure its peak, and place it so the peak lands on
   the cue time exported from the scene. Tails wrap around so the loop is seamless.
"""
import argparse
import json
import numpy as np
from scipy.signal import butter, lfilter
from wav import SR, read_audio, write_wav

T = 14.0
TARGET_BPM = 120.0
HOP = 256
NFFT = 2048


# ── analysis ────────────────────────────────────────────────────────
def stft_mag(x):
    win = np.hanning(NFFT)
    n = 1 + (len(x) - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    return np.abs(np.fft.rfft(x[idx] * win, axis=1))


def analyse(song):
    mono = song.mean(1)
    M = stft_mag(mono)
    freqs = np.fft.rfftfreq(NFFT, 1 / SR)
    fps = SR / HOP
    logm = np.log1p(100 * M)
    flux = np.maximum(0, np.diff(logm, axis=0)).sum(1)
    flux = np.concatenate([[0], flux])
    # remove slow trend, normalize
    k = int(fps * .5)
    trend = np.convolve(flux, np.ones(k) / k, mode='same')
    onset = np.maximum(0, flux - trend)
    onset /= onset.max() + 1e-9

    # tempo: autocorrelation with a mild log-normal prior around 120 BPM
    ac = np.correlate(onset, onset, mode='full')[len(onset) - 1:]
    lags = np.arange(len(ac))
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 70)
    bpm_of = 60 * fps / np.maximum(lags, 1)
    prior = np.exp(-.5 * (np.log2(bpm_of / 120) / .9) ** 2)
    score = ac * prior
    L = lo + int(np.argmax(score[lo:hi]))
    a, b, c = score[L - 1], score[L], score[L + 1]
    period = L + .5 * (a - c) / (a - 2 * b + c)                  # parabolic refinement (frames)

    # phase: comb over the onset envelope
    phases = np.linspace(0, period, 200, endpoint=False)
    ks = np.arange(int(len(onset) / period) - 1)
    comb = [np.interp(p + ks * period, np.arange(len(onset)), onset).sum() for p in phases]
    phase = phases[int(np.argmax(comb))]

    # least-squares fit of the grid to local onset peaks (sub-frame precision)
    grid = phase + ks * period
    peaks = []
    for g in grid:
        i0, i1 = int(max(0, g - 3)), int(min(len(onset) - 1, g + 3))
        seg = onset[i0:i1 + 1]
        if seg.max() > .15:
            j = i0 + int(np.argmax(seg))
            if 0 < j < len(onset) - 1:
                y0, y1, y2 = onset[j - 1:j + 2]
                j = j + .5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-12)
            peaks.append((np.round((g - phase) / period), j))
    kk, pp = np.array(peaks).T
    slope, icpt = np.polyfit(kk, pp, 1)
    # onset frames are centred on the analysis window
    beat0 = (icpt * HOP + NFFT / 2) / SR
    beat_dur = slope * HOP / SR
    bpm = 60 / beat_dur
    # time-domain refinement: spectral flux reads early by up to half a window,
    # so snap the grid to the steepest rise of the transient envelope around each beat
    k1 = int(SR * .001)
    envl = np.convolve(np.abs(mono), np.ones(k1) / k1, mode='same')
    rise = np.diff(envl, prepend=envl[0])
    deltas = []
    for g in beat0 + beat_dur * kk:
        i0, i1 = int((g - .03) * SR), int((g + .03) * SR)
        if i0 > 0 and i1 < len(rise):
            deltas.append((i0 + np.argmax(rise[i0:i1])) / SR - g)
    beat0 += float(np.median(deltas))
    n_beats = int((len(mono) / SR - beat0) / beat_dur)
    beats = beat0 + beat_dur * np.arange(n_beats)
    residual_ms = 1000 * np.abs(pp - (icpt + slope * kk)).mean() * HOP / SR

    # downbeat: harmonic change (100 Hz–2 kHz spectrum, beat-synchronous) + low-end weight
    band = (freqs > 100) & (freqs < 2000)
    low = freqs < 150
    fr = lambda t: int(np.clip(t * fps - NFFT / 2 / HOP, 0, len(M) - 1))
    spec = np.array([M[fr(t):max(fr(t) + 1, fr(t + beat_dur)), :][:, band].mean(0) for t in beats])
    lowe = np.array([M[fr(t):fr(t) + 3, :][:, low].sum() for t in beats])
    spec /= np.linalg.norm(spec, axis=1, keepdims=True) + 1e-9
    nov = np.concatenate([[0], 1 - (spec[1:] * spec[:-1]).sum(1)])
    z = lambda v: (v - v.mean()) / (v.std() + 1e-9)
    s = z(nov) + .35 * z(lowe)
    bar_phase = int(np.argmax([s[m::4].mean() for m in range(4)]))
    downbeats = beats[bar_phase::4]

    # start: first downbeat whose 7-bar window carries (almost) full energy
    need = T * TARGET_BPM / bpm
    rms = lambda t: np.sqrt((mono[int(t * SR):int((t + need) * SR)] ** 2).mean())
    cands = [d for d in downbeats if d + need <= len(mono) / SR]
    energies = np.array([rms(d) for d in cands])
    start = cands[int(np.argmax(energies >= .95 * energies.max()))]
    return dict(bpm=float(bpm), beat0=float(beat0), beat_dur=float(beat_dur), bar_phase=bar_phase,
                start=float(start), fit_residual_ms=float(residual_ms), n_beats=int(n_beats),
                downbeats=[round(float(d), 4) for d in downbeats[:12]])


# ── UI sounds ───────────────────────────────────────────────────────
rng = np.random.default_rng(3)


def tvec(d):
    return np.arange(int(d * SR)) / SR


def bp(x, lo, hi):
    b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], 'band')
    return lfilter(b, a, x)


def dec(d, tau, att=.0006):
    t = tvec(d)
    return np.minimum(1, t / att) * np.exp(-t / tau)


def tone(f, d, tau, att=.0006):
    return np.sin(2 * np.pi * f * tvec(d)) * dec(d, tau, att)


def noise(d, tau, lo, hi, att=.0003):
    return bp(rng.standard_normal(int(d * SR)), lo, hi) * dec(d, tau, att)


def pad(*xs):
    n = max(len(x) for x in xs)
    return sum(np.pad(x, (0, n - len(x))) for x in xs)


def sfx(kind):
    if kind == 'click':
        return pad(tone(2400, .05, .010) * .5, noise(.02, .0025, 2000, 9000) * .9, tone(5200, .02, .003) * .2)
    if kind == 'grab':
        return pad(tone(1250, .06, .014) * .45, noise(.03, .004, 1200, 6000) * .7, tone(260, .06, .018) * .35)
    if kind == 'release':
        return pad(tone(1650, .05, .009) * .4, noise(.02, .003, 2000, 8000) * .6, tone(340, .08, .02) * .4)
    if kind == 'tick':
        return pad(tone(3300, .03, .005) * .3, noise(.012, .0015, 3000, 10000) * .45)
    if kind == 'toggle':
        return pad(tone(900, .07, .02) * .45, tone(1800, .05, .01) * .25, noise(.02, .003, 1500, 7000) * .8,
                   tone(180, .08, .025) * .4)
    if kind == 'pop':
        t = tvec(.07)
        f = 520 + 520 * np.exp(-t / .012)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * dec(.07, .022, .002) * .4
    if kind == 'key':
        return pad(noise(.03, .004, 1500, 6500) * .9, tone(190, .05, .014) * .45, tone(2600, .02, .004) * .12)
    if kind == 'enter':
        return pad(noise(.04, .006, 1000, 6000) * 1.0, tone(130, .09, .03) * .6, tone(1900, .03, .006) * .2)
    if kind == 'chime':
        d = .9
        return (tone(1318.5, d, .32, .003) * .22 + tone(1975.5, d, .22, .003) * .16 + tone(2637, d, .12, .003) * .08)
    if kind == 'whoosh':
        d = .3
        t = tvec(d)
        rise = (t / .19) ** 3 * (t < .19) + np.exp(-(t - .19) / .035) * (t >= .19)
        n = rng.standard_normal(len(t))
        lo = lfilter(*butter(2, 700 / (SR / 2)), n)
        hi = bp(n, 1500, 5000)
        mixk = np.clip(t / .19, 0, 1)
        return (lo * (1 - mixk) + hi * mixk * .6) * rise * .28
    raise ValueError(kind)


def peak_index(x):
    k = int(SR * .001)
    e = np.convolve(np.abs(x), np.ones(k) / k, mode='same')
    return int(np.argmax(e))


def place_cues(cues, n):
    out = np.zeros(n)
    report = []
    for t, kind in cues:
        s = sfx(kind)
        pk = peak_index(s)
        i0 = int(round(t * SR)) - pk
        idx = (i0 + np.arange(len(s))) % n              # wrap tails → seamless loop
        np.add.at(out, idx, s)
        report.append((t, kind, round(1000 * pk / SR, 2)))
    return out, report


# ── main ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song')
    ap.add_argument('--cues', default='out/cues.json')
    ap.add_argument('--out', default='out/audio.wav')
    a = ap.parse_args()

    song = read_audio(a.song)
    info = analyse(song)
    need = T * TARGET_BPM / info['bpm']
    speed = TARGET_BPM / info['bpm']
    af = f'atempo={speed:.6f}' if abs(speed - 1) > 1e-4 else None
    seg = read_audio(a.song, ss=info['start'], t=need, af=af)
    n = int(T * SR)
    seg = np.pad(seg, ((0, max(0, n - len(seg))), (0, 0)))[:n]

    # verify: re-analyse the cut segment (looped twice) → beats must sit on the 0.5 s grid
    chk = analyse(np.concatenate([seg, seg]))
    grid_err = 1000 * abs(((chk['beat0'] + .25) % .5) - .25)
    info.update(segment_bpm=chk['bpm'], segment_first_beat_ms=round(1000 * chk['beat0'], 2),
                segment_grid_error_ms=round(grid_err, 2), speed=speed)

    cues = json.load(open(a.cues))
    fx, rep = place_cues(cues, n)
    mix = seg * .62 + fx[:, None] * .85
    # gentle soft clip, then normalize to −1 dBFS
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix *= .89 / np.abs(mix).max()
    write_wav(a.out, mix)
    info['cues'] = rep
    json.dump(info, open(a.out.rsplit('.', 1)[0] + '_report.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in info.items() if k != 'cues'}, indent=1))
    print(f'{len(rep)} UI sounds placed by measured peak → {a.out}')


if __name__ == '__main__':
    main()
