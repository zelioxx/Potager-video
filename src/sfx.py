"""Synthèse des effets sonores (pas de banque externe) : whoosh, pop, ding, etc.

Chaque fonction renvoie un tableau mono float32 à SR Hz, amplitude ~[-1, 1].
"""
import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def _t(d):
    return np.arange(int(d * SR)) / SR


def _env(n, a=0.005, r=None, curve=4.0):
    """Enveloppe attaque linéaire + décroissance exponentielle."""
    t = np.arange(n) / SR
    d = n / SR
    a_n = max(1, int(a * SR))
    e = np.exp(-curve * t / (r if r else d))
    e[:a_n] *= np.linspace(0, 1, a_n)
    return e


def _lp(x, cutoff):
    """Passe-bas un pôle (cutoff scalaire ou tableau)."""
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    alpha = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha[i] * (x[i] - acc)
        y[i] = acc
    return y


def _bp(x, lo, hi):
    return _lp(x, hi) - _lp(x, lo)


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) + 1e-9
    return (x / m * peak).astype(np.float32)


def whoosh(d=0.42, up=False):
    n = int(d * SR)
    noise = rng.standard_normal(n)
    t = np.linspace(0, 1, n)
    sweep = (300 + 4200 * t) if up else (4500 - 3800 * t)
    x = _bp(noise, sweep * 0.35, sweep)
    env = np.sin(np.pi * np.clip(t, 0, 1)) ** 1.6
    return norm(x * env, 0.8)


def pop(f0=520, d=0.11):
    t = _t(d)
    f = f0 * np.exp(-t * 18) + f0 * 0.35
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * _env(len(t), 0.002, d * 0.5)
    click = rng.standard_normal(len(t)) * np.exp(-t * 400) * 0.3
    return norm(x + click, 0.9)


def tick(f=2400, d=0.05):
    t = _t(d)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 90) + rng.standard_normal(len(t)) * np.exp(-t * 500) * 0.4
    return norm(x, 0.7)


def ding(f=1318.5, d=1.1):
    t = _t(d)
    x = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (3 + k * 2.5))
            for k, a in [(1, 1.0), (2.01, 0.45), (3.02, 0.2), (4.2, 0.08)])
    x[: int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))
    return norm(x, 0.8)


def success():
    a = ding(1046.5, 0.9)
    b = ding(1568.0, 1.0)
    out = np.zeros(int(1.2 * SR), np.float32)
    out[: len(a)] += a * 0.7
    o = int(0.09 * SR)
    out[o: o + len(b)] += b * 0.8
    return norm(out, 0.85)


def thud(d=0.28):
    t = _t(d)
    f = 120 * np.exp(-t * 9) + 45
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.002, d * 0.6)
    dirt = _lp(rng.standard_normal(len(t)), 900) * np.exp(-t * 22) * 0.9
    return norm(x + dirt, 0.95)


def plop():
    t = _t(0.16)
    f = 380 + 1500 * (t / 0.16) ** 0.6
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.16) ** 0.7
    return norm(x, 0.8)


def chirp_bird():
    """Petit gazouillis de merle : 3 notes FM rapides."""
    out = np.zeros(int(0.65 * SR), np.float32)
    starts = [0.0, 0.17, 0.33]
    for i, s in enumerate(starts):
        d = 0.13 if i < 2 else 0.22
        t = _t(d)
        base = [3200, 3800, 2600][i]
        f = base + 900 * np.sin(2 * np.pi * (14 + 6 * i) * t) - (1400 if i == 2 else 0) * t / d
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 1.5
        o = int(s * SR)
        out[o: o + len(x)] += x
    return norm(out, 0.7)


def peck():
    out = np.zeros(int(0.45 * SR), np.float32)
    for k, s in enumerate([0.0, 0.14, 0.28]):
        t = _t(0.05)
        x = _bp(rng.standard_normal(len(t)), 900, 3500) * np.exp(-t * 120)
        o = int(s * SR)
        out[o: o + len(x)] += x * (1 - 0.15 * k)
    return norm(out, 0.8)


def buzz(d=1.6):
    t = _t(d)
    f = 210 + 25 * np.sin(2 * np.pi * 3.1 * t) + 12 * np.sin(2 * np.pi * 7.3 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
    x = _lp(saw, 1800) * (0.6 + 0.4 * np.sin(2 * np.pi * 11 * t))
    env = np.minimum(1, t / 0.15) * np.minimum(1, (d - t) / 0.3)
    return norm(x * env, 0.6)


def rain(d=2.2):
    n = int(d * SR)
    x = _bp(rng.standard_normal(n), 500, 6000) * 0.25
    for _ in range(int(d * 28)):
        o = rng.integers(0, n - 2000)
        t = _t(0.02)
        x[o: o + len(t)] += np.sin(2 * np.pi * rng.uniform(1500, 4000) * t) * np.exp(-t * 300) * rng.uniform(0.3, 0.9)
    t = np.arange(n) / SR
    env = np.minimum(1, t / 0.4) * np.minimum(1, (d - t) / 0.5)
    return norm(x * env, 0.6)


def crunch(d=0.5):
    n = int(d * SR)
    out = np.zeros(n, np.float32)
    for k in range(9):
        o = int(rng.uniform(0, d - 0.06) * SR)
        t = _t(0.05)
        out[o: o + len(t)] += _bp(rng.standard_normal(len(t)), 1200, 7000) * np.exp(-t * 80) * rng.uniform(0.4, 1)
    return norm(out, 0.8)


def sparkle():
    out = np.zeros(int(0.9 * SR), np.float32)
    for k, f in enumerate([2093, 2637, 3136, 4186]):
        t = _t(0.5)
        x = np.sin(2 * np.pi * f * t) * np.exp(-t * 9)
        o = int(k * 0.06 * SR)
        out[o: o + len(x)] += x * (0.9 - 0.12 * k)
    return norm(out, 0.6)


def fail():
    """Petit « wah-wah » descendant pour « il pourrit »."""
    out = np.zeros(int(0.85 * SR), np.float32)
    for k, (f0, s) in enumerate([(392, 0.0), (311, 0.3)]):
        d = 0.32 if k == 0 else 0.5
        t = _t(d)
        f = f0 * (1 - 0.06 * t / d)
        ph = 2 * np.pi * np.cumsum(f) / SR
        x = (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph))
        x = _lp(x, 900 + 1400 * np.sin(np.pi * t / d)) * np.sin(np.pi * t / d) ** 0.6
        o = int(s * SR)
        out[o: o + len(x)] += x
    return norm(out, 0.7)


def squish():
    t = _t(0.35)
    f = 260 * np.exp(-t * 6) + 60
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.01, 0.2)
    wet = _bp(rng.standard_normal(len(t)), 200, 1400) * np.exp(-t * 10) * 0.6
    return norm(x + wet, 0.8)


def mouse_click():
    t = _t(0.06)
    a = rng.standard_normal(len(t)) * np.exp(-t * 700)
    b = np.zeros_like(a)
    o = int(0.035 * SR)
    b[o:] = a[: len(a) - o] * 0.7
    return norm(_bp(a + b, 1500, 9000), 0.8)


def bell_notif():
    out = np.zeros(int(1.0 * SR), np.float32)
    for k, f in enumerate([1760, 2349]):
        x = ding(f, 0.8)
        o = int(k * 0.12 * SR)
        out[o: o + len(x)] += x * 0.7
    return norm(out, 0.7)


def rise(d=0.5):
    t = _t(d)
    f = 300 + 900 * (t / d) ** 2
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / d) * 0.5
    x += _bp(rng.standard_normal(len(t)), 1500, 6000) * (t / d) ** 2 * 0.5
    x *= np.minimum(1, (d - t) / 0.03)
    return norm(x, 0.6)


def page_slide():
    return whoosh(0.3, up=True)


def chop():
    """Coup de couteau sur planche : attaque claquée + petit bois."""
    t = _t(0.22)
    snap = _bp(rng.standard_normal(len(t)), 2000, 9000) * np.exp(-t * 90)
    knock = np.sin(2 * np.pi * (180 * np.exp(-t * 15) + 90) * t) * np.exp(-t * 28)
    return norm(snap * 0.8 + knock, 0.95)


def pour(d=1.1):
    n = int(d * SR)
    t = np.arange(n) / SR
    x = _bp(rng.standard_normal(n), 300, 2500) * 0.5
    for _ in range(int(d * 40)):
        o = rng.integers(0, n - 4000)
        tt = _t(0.04)
        f = rng.uniform(400, 1100)
        x[o: o + len(tt)] += np.sin(2 * np.pi * (f + 3000 * tt) * tt) * np.exp(-tt * 70) * rng.uniform(0.3, 0.8)
    env = np.minimum(1, t / 0.08) * np.minimum(1, (d - t) / 0.25)
    return norm(x * env, 0.7)


def splash():
    out = np.zeros(int(0.6 * SR), np.float32)
    p = plop()
    out[: len(p)] += p
    t = _t(0.5)
    out[: len(t)] += _bp(rng.standard_normal(len(t)), 800, 7000) * np.exp(-t * 9) * 0.6
    return norm(out, 0.85)


def alert(f0=330.0):
    """Petit jingle d'erreur (deux notes descendantes, timbre doux) — hauteur variable."""
    out = np.zeros(int(0.62 * SR), np.float32)
    for k, (mul, st, d) in enumerate([(1.5, 0.0, 0.16), (1.0, 0.17, 0.36)]):
        t = _t(d)
        f = f0 * mul
        x = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t))
        x *= np.exp(-t * (7 if k else 12)) * np.minimum(1, t / 0.006)
        o = int(st * SR)
        out[o: o + len(x)] += x
    return norm(out, 0.75)


def squeak():
    """Couinement de rat : deux petits cris aigus."""
    out = np.zeros(int(0.45 * SR), np.float32)
    for st, d in ((0.0, 0.11), (0.17, 0.15)):
        t = _t(d)
        f = 3200 + 900 * np.sin(np.pi * t / d) + 250 * np.sin(2 * np.pi * 38 * t)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 1.2
        o = int(st * SR)
        out[o: o + len(x)] += x
    return norm(out, 0.55)


def stir(d=0.55):
    """Fourche qui brasse le compost : bruit grave et granuleux."""
    n = int(d * SR)
    t = np.arange(n) / SR
    x = _bp(rng.standard_normal(n), 120, 1600) * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t))
    for _ in range(14):
        o = rng.integers(0, n - 3000)
        tt = _t(0.03)
        x[o: o + len(tt)] += _bp(rng.standard_normal(len(tt)), 600, 4000) * np.exp(-tt * 120) * 0.8
    env = np.sin(np.pi * t / d) ** 0.8
    return norm(x * env, 0.75)


BANK = {
    "whoosh": lambda: whoosh(0.42),
    "whoosh_up": lambda: whoosh(0.38, up=True),
    "pop": lambda: pop(520),
    "pop_hi": lambda: pop(760, 0.09),
    "pop_lo": lambda: pop(360, 0.14),
    "tick": tick,
    "ding": ding,
    "success": success,
    "thud": thud,
    "plop": plop,
    "bird": chirp_bird,
    "peck": peck,
    "buzz": buzz,
    "rain": rain,
    "crunch": crunch,
    "sparkle": sparkle,
    "fail": fail,
    "squish": squish,
    "click": mouse_click,
    "bell": bell_notif,
    "rise": rise,
    "chop": chop,
    "pour": pour,
    "splash": splash,
    "alert1": lambda: alert(392.0),
    "alert2": lambda: alert(349.2),
    "alert3": lambda: alert(311.1),
    "squeak": squeak,
    "stir": stir,
}


def render_track(cues, duration):
    """cues: liste (temps, nom, gain). Renvoie une piste mono."""
    out = np.zeros(int(duration * SR) + SR, np.float32)
    cache = {}
    for t, name, gain in cues:
        if name not in cache or name in ("pop", "pop_hi", "pop_lo", "tick"):
            snd = BANK[name]()
            if name.startswith("pop") or name == "tick":
                # légère variation de hauteur pour éviter l'effet mitraillette
                fac = rng.uniform(0.92, 1.08)
                idx = np.arange(0, len(snd) - 1, fac)
                snd = np.interp(idx, np.arange(len(snd)), snd).astype(np.float32)
            cache[name] = snd
        snd = cache[name]
        o = int(max(0, t) * SR)
        e = min(len(out), o + len(snd))
        out[o:e] += snd[: e - o] * gain
    return out[: int(duration * SR)]
