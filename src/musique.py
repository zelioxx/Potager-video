"""Petite musique de fond originale, synthétisée (aucun morceau sous droits) : guitare picking douce
(cordes pincées, algorithme de Karplus-Strong), basse ronde et nappe légère. Ambiance calme et joyeuse, 92 BPM,
en sol majeur (Sol – Ré – Mi m – Do).

    from musique import bed
    x = bed(duree_s, sr=48000)      # mono, crête ≈ 0,9
"""
import numpy as np

A4 = 440.0
NOTES = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}


def hz(name):
    """« G3 », « F#4 »… → fréquence."""
    n, octv = name[:-1], int(name[-1])
    semi = NOTES[n[0]] + (1 if "#" in n else 0) + 12 * (octv - 4)
    return A4 * 2 ** (semi / 12)


def pluck(f, dur, sr, bright=0.5, decay=0.996, seed=0):
    """Corde pincée (Karplus-Strong), calculée par blocs d'une période."""
    r = np.random.default_rng(seed)
    p = max(2, int(round(sr / f)))
    n = int(dur * sr)
    out = np.zeros(n + p, np.float64)
    buf = r.uniform(-1, 1, p)
    # attaque adoucie (pincé au doigt, pas au médiator)
    for _ in range(int(3 * (1 - bright)) + 1):
        buf = 0.5 * (buf + np.roll(buf, 1))
    out[:p] = buf
    i = p
    while i < n + p:
        prev = out[i - p:i]
        nxt = decay * 0.5 * (prev + np.concatenate([[prev[-1]], prev[:-1]]))
        m = min(p, n + p - i)
        out[i:i + m] = nxt[:m]
        i += p
    x = out[:n]
    x *= np.minimum(1, np.arange(n) / (0.004 * sr))
    return x


def pad(freqs, dur, sr):
    t = np.arange(int(dur * sr)) / sr
    x = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):      # léger chorus
            x += np.sin(2 * np.pi * f * (1 + det / 100) * t) * 0.33
    env = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.6)
    return x * env / len(freqs)


CHORDS = [("G", ["G2", "D3", "G3", "B3", "D4", "G4"]), ("D", ["D2", "A2", "D3", "F#3", "A3", "D4"]),
          ("Em", ["E2", "B2", "E3", "G3", "B3", "E4"]), ("C", ["C3", "G3", "C4", "E4", "G4", "C5"])]
PATTERN = [0, 2, 3, 4, 5, 4, 3, 2]          # picking : basse puis arpège, en croches


def _add(x, s, y):
    m = max(0, min(len(y), len(x) - s))
    x[s:s + m] += y[:m]


def bed(duration, sr=48000, bpm=92):
    beat = 60.0 / bpm
    bar = 4 * beat
    n = int(duration * sr)
    x = np.zeros(n + sr * 3)
    k = 0
    t0 = 0.0
    while t0 < duration:
        name, notes = CHORDS[k % 4]
        # picking en croches
        for j, idx in enumerate(PATTERN):
            t = t0 + j * beat / 2
            s = int(t * sr)
            note = pluck(hz(notes[idx]), 2.2, sr, bright=0.35, seed=k * 8 + j)
            g = 0.55 if j else 0.75
            _add(x, s, note * g)
        # basse ronde sur les temps 1 et 3
        for j in (0, 2):
            s = int((t0 + j * beat) * sr)
            f = hz(notes[0]) / 2 if hz(notes[0]) > 90 else hz(notes[0])
            tt = np.arange(int(beat * 1.8 * sr)) / sr
            b = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 2.2) * np.minimum(1, tt / 0.01)
            _add(x, s, b * 0.45)
        # nappe très douce
        pd = pad([hz(m) for m in notes[2:5]], bar + 0.4, sr)
        s = int(t0 * sr)
        _add(x, s, pd * 0.18)
        k += 1
        t0 += bar
    x = x[:n]
    # filtre doux (moins de piquant) et fondus
    from scipy.signal import butter, sosfilt
    x = sosfilt(butter(2, [70, 6000], btype="band", fs=sr, output="sos"), x)
    t = np.arange(n) / sr
    x *= np.minimum(1, t / 1.5) * np.minimum(1, (duration - t) / 2.0)
    return (x / (np.abs(x).max() + 1e-9) * 0.9).astype(np.float32)
