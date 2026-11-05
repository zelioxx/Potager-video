#!/usr/bin/env python3
"""Bruitages synthétisés + mixage sous la voix off.

Usage :
  python3 tools/sfx.py projets/<nom>/bruitages.json      → écrit projets/<nom>/mix.wav
  python3 tools/sfx.py --banque assets/sfx               → exporte chaque bruitage en .wav (pour écouter)

bruitages.json :
  { "voix": "voix.mp3", "sfx_db": -16,
    "cues": [ {"t": 0.0, "son": "pop", "db": 0, "dur": 1.0, "seed": 1}, ... ] }
  t = instant (s), son = nom dans BANQUE, db = gain relatif, dur = durée pour les sons continus.
"""
import json, os, subprocess, sys
import numpy as np
from scipy import signal

SR = 44100


def t_axis(d):
    return np.arange(int(d * SR)) / SR


def env_ad(n, a=0.005, d=0.1):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)


def fade(x, fi=0.02, fo=0.05):
    n = len(x); i = min(n, int(fi * SR)); o = min(n, int(fo * SR))
    x = x.copy()
    if i: x[:i] *= np.linspace(0, 1, i)
    if o: x[-o:] *= np.linspace(1, 0, o)
    return x


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], 'bandpass', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'highpass', fs=SR, output='sos'), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'lowpass', fs=SR, output='sos'), x)


def sweep(f0, f1, d, curve='exp'):
    t = t_axis(d)
    f = f0 * (f1 / f0) ** (t / d) if curve == 'exp' else f0 + (f1 - f0) * t / d
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


# ---------------- Banque de sons ----------------

def pop(rng, **_):  # apparition d'un gros titre
    d = 0.16
    x = sweep(1100, 260, d) * env_ad(int(d * SR), 0.002, 0.045)
    x += 0.25 * hp(rng.standard_normal(len(x)), 3000) * env_ad(len(x), 0.001, 0.008)
    return norm(x)


def bloop(rng, f0=320, f1=1100, d=0.12, **_):  # goutte / bulle
    x = sweep(f0, f1, d) * env_ad(int(d * SR), 0.003, d / 3)
    return norm(x)


def plop(rng, **_):  # légume qui tombe dans l'eau
    f0 = 180 + rng.random() * 80
    x = bloop(rng, f0, f0 * 3.2, 0.1)
    s = bp(rng.standard_normal(int(0.25 * SR)), 1500, 6000) * env_ad(int(0.25 * SR), 0.004, 0.05) * 0.35
    y = np.zeros(int(0.25 * SR)); y[:len(x)] += x; y += s
    return norm(y)


def bubble(rng, **_):  # bulle minéraux qui apparaît
    f0 = 500 + rng.random() * 200
    return bloop(rng, f0, f0 * 2.4, 0.09)


def whoosh(rng, dur=0.35, **_):  # changement de plan
    n = int(dur * SR); noise = rng.standard_normal(n)
    out = np.zeros(n); blk = 512
    for i in range(0, n, blk):
        k = i / n; fc = 500 + 3500 * np.sin(np.pi * k) ** 2
        out[i:i + blk] = bp(noise[max(0, i - 2048):i + blk], fc * 0.7, min(fc * 1.4, 20000))[-len(out[i:i + blk]):]
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return norm(out * e)


def pour(rng, dur=0.8, **_):  # eau qui coule
    n = int(dur * SR)
    x = bp(rng.standard_normal(n), 700, 4500)
    gurg = np.zeros(n)
    for _ in range(int(dur * 25)):
        p = int(rng.random() * (n - 4000)); f = 400 + rng.random() * 900
        b = sweep(f, f * 1.6, 0.04) * env_ad(int(0.04 * SR), 0.002, 0.012)
        gurg[p:p + len(b)] += b * 0.5
    am = 0.7 + 0.3 * lp(rng.standard_normal(n), 12) * 8
    return norm(fade(x * np.clip(am, 0.2, 1.3) * 0.6 + gurg, 0.08, 0.15))


def boil(rng, dur=1.5, **_):  # frémissement de casserole
    n = int(dur * SR)
    x = lp(rng.standard_normal(n), 900) * 0.25
    for _ in range(int(dur * 18)):
        p = int(rng.random() * (n - 5000)); f = 150 + rng.random() * 350
        b = sweep(f, f * 2, 0.05) * env_ad(int(0.05 * SR), 0.002, 0.015)
        x[p:p + len(b)] += b * (0.3 + rng.random() * 0.4)
    return norm(fade(x, 0.15, 0.25))


def shaker(rng, dur=0.8, **_):  # salière secouée
    n = int(dur * SR); x = np.zeros(n)
    for k in range(int(dur / 0.16)):
        p = int(k * 0.16 * SR); g = int(0.07 * SR)
        x[p:p + g] += hp(rng.standard_normal(g), 4000) * env_ad(g, 0.01, 0.025)
    return norm(x)


def sprinkle(rng, dur=1.0, density=22, **_):  # grains / cristaux qui tombent
    n = int(dur * SR); x = np.zeros(n)
    for _ in range(int(dur * density)):
        p = int(rng.random() * (n - 800)); f = 3000 + rng.random() * 4000
        b = np.sin(2 * np.pi * f * t_axis(0.015)) * env_ad(int(0.015 * SR), 0.0005, 0.003)
        x[p:p + len(b)] += b * (0.4 + rng.random() * 0.6)
    return norm(x)


def crackle(rng, dur=1.5, **_):  # racines qui sèchent
    n = int(dur * SR); x = np.zeros(n)
    for _ in range(int(dur * 60)):
        p = int(rng.random() * (n - 400)); L = int(SR * (0.001 + rng.random() * 0.004))
        x[p:p + L] += rng.standard_normal(L) * rng.random()
    return norm(fade(bp(x, 800, 7000), 0.1, 0.2))


def sad(rng, **_):  # plante qui fane (sifflet descendant)
    d = 0.75; t = t_axis(d)
    f = 720 * (230 / 720) ** (t / d) * (1 + 0.015 * np.sin(2 * np.pi * 7 * t))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.2 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    return norm(fade(x, 0.03, 0.2))


def nope(rng, **_):  # interdit
    out = []
    for f in (330, 247):
        d = 0.13; t = t_axis(d)
        s = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(2 * np.pi * f * t)
        out.append(lp(s, 2500) * env_ad(len(t), 0.004, 0.08)); out.append(np.zeros(int(0.03 * SR)))
    return norm(np.concatenate(out))


def ticks_down(rng, dur=0.7, **_):  # thermomètre qui descend
    n = int(dur * SR); x = np.zeros(n); k = 9
    for i in range(k):
        f = 1800 * (600 / 1800) ** (i / (k - 1)); p = int(i * (n - 3000) / (k - 1))
        b = np.sin(2 * np.pi * f * t_axis(0.03)) * env_ad(int(0.03 * SR), 0.001, 0.008)
        x[p:p + len(b)] += b
    return norm(x)


def page(rng, **_):  # page de calendrier
    d = 0.09; n = int(d * SR)
    x = bp(rng.standard_normal(n), 1800, 9000) * env_ad(n, 0.004, 0.025)
    return norm(x)


def click(rng, **_):  # bouton
    n = int(0.06 * SR)
    x = np.sin(2 * np.pi * 2200 * t_axis(0.06)) * env_ad(n, 0.0005, 0.006)
    x += 0.7 * np.sin(2 * np.pi * 140 * t_axis(0.06)) * env_ad(n, 0.001, 0.02)
    return norm(x)


def ding(rng, **_):  # validation
    d = 1.2; t = t_axis(d); x = np.zeros(len(t))
    for f, a, dec in ((1318.5, 1, 0.5), (1318.5 * 2.01, 0.35, 0.25), (1975.5, 0.5, 0.4), (1318.5 * 3.9, 0.12, 0.12)):
        x += a * np.sin(2 * np.pi * f * t) * np.exp(-t / dec)
    return norm(x * np.minimum(1, t / 0.003))


def shimmer(rng, **_):  # loupe / détail
    d = 0.6; t = t_axis(d); x = np.zeros(len(t))
    for i, f in enumerate((1568, 1976, 2349, 3136)):
        s = int(i * 0.06 * SR)
        x[s:] += np.sin(2 * np.pi * f * t[:len(t) - s]) * np.exp(-t[:len(t) - s] / 0.18)
    return norm(x)


BANQUE = dict(pop=pop, plop=plop, bubble=bubble, whoosh=whoosh, pour=pour, boil=boil, shaker=shaker,
              sprinkle=sprinkle, crackle=crackle, sad=sad, nope=nope, ticks_down=ticks_down, page=page,
              click=click, ding=ding, shimmer=shimmer)


def render_cue(c):
    rng = np.random.default_rng(c.get('seed', int(c['t'] * 1000)))
    kw = {k: v for k, v in c.items() if k in ('dur', 'density')}
    return BANQUE[c['son']](rng, **kw) * 10 ** (c.get('db', 0) / 20)


def load_audio(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    if x.ndim == 1: x = np.stack([x, x], 1)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', path],
                   input=x.astype(np.float32).tobytes(), check=True)


def main():
    if sys.argv[1] == '--banque':
        os.makedirs(sys.argv[2], exist_ok=True)
        for name in BANQUE:
            write_wav(os.path.join(sys.argv[2], name + '.wav'), 0.8 * render_cue({'t': 0, 'son': name, 'seed': 1}))
        return
    cfg_path = sys.argv[1]; base = os.path.dirname(cfg_path)
    cfg = json.load(open(cfg_path))
    voice = load_audio(os.path.join(base, cfg['voix']))
    # niveau de référence : RMS de la voix pendant la parole
    rms = np.sqrt(np.mean(voice[np.abs(voice[:, 0]) > 0.02] ** 2))
    bus = np.zeros(len(voice) + SR)
    for c in cfg['cues']:
        x = render_cue(c); p = int(c['t'] * SR)
        n = min(len(x), len(bus) - p)
        if n > 0: bus[p:p + n] += x[:n]
    bus = bus[:len(voice)] * rms * 3 * 10 ** (cfg.get('sfx_db', -16) / 20)
    # léger élargissement stéréo des bruitages
    sfx = np.stack([bus, np.concatenate([np.zeros(int(0.008 * SR)), bus])[:len(bus)]], 1)
    mix = voice + sfx
    out = os.path.join(base, cfg.get('sortie', 'mix.wav'))
    write_wav(out, mix / max(1, np.max(np.abs(mix)) / 0.98))
    print('OK →', out)


if __name__ == '__main__':
    main()
