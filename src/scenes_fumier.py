"""Storyboard « Le fumier en hiver » (voix : assets/audio/fumier/voix.mp3).

Le volume de la voix est gardé tel qu'envoyé (aucun mastering, cf. render.py « af ») ; bruitages sous la voix
(réglés comme pour le gland : voix envoyée à -17,7 LUFS).
Décors fournis : les carrés potagers sous la neige / au printemps (terre nue) / plantés, même cadrage.
0–4.5    le potager sous la neige : « fais ça cet hiver… sinon gare au printemps ! »
4.5–11.85 « étale du fumier » : la fourche arrive et lance des fourchées de fumier sur le grand carré, qui se
          couvre peu à peu ; « pas besoin de l'enterrer » (fourche barrée) ; « en surface, quelques cm » (règle).
11.85–16.25 la pluie, le gel et les vers de terre : le fumier se décompose et rentre dans la terre.
16.25–20.35 attention aux carottes : elles détestent ça.
20.35–24.3 au printemps : la neige laisse place à une terre riche, souple, puis au potager planté.
24.3–fin  bouton S'abonner et logo.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, put, title, life, fade, ease_out, ease_io,
                 ease_in, ease_out_back, clamp, lerp, icon, tag, button_img, particles, measure, pills, light_rays)
from scenes import sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp
from scenes_citron import photo, shade, zoomed, shadow
from scenes_banane import ob
from scenes_arrosage_soir import snow_badge

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)

SFX_GAIN = 0.19                                  # bruitages baissés (≈ -3 dB) : la voix reste bien devant
DUCK = 0.6
TRANS_GAIN = 0.26
SHIFT = 0.25                                     # les temps ci-dessous suivent la reconnaissance vocale (~0,25 s en retard)


def cue(t, name, gain=0.5):
    CUES.append((t - SHIFT, name, gain))


B = "banque/"
NEIGE, VIDES, PLANTES = "decor_potager_bacs_neige.png", "decor_potager_bacs_vides.webp", "decor_potager_bacs_plantes.webp"
FUMIER, FUMIER_GROS, FOURCHE, FOURCHE_D = B + "fumier_tas", B + "fumier_gros_tas", B + "fourche_biais2", B + "fourche_droite"
VER, CAROTTES = "feuilles/ver", B + "carottes_botte"
FULL = (0, 0, 1024, 1024)
BED = [(392, 848), (778, 848), (1012, 1612), (92, 1612)]      # terre du grand carré du premier plan (plein écran)


class Cam:
    def __init__(self, z, fx, fy):
        self.z = z
        cw, ch = W / z, H / z
        self.x0 = min(max(fx - cw / 2, 0), W - cw)
        self.y0 = min(max(fy - ch / 2, 0), H - ch)
        self.fx, self.fy = fx, fy

    def p(self, x, y):
        return (x - self.x0) * self.z, (y - self.y0) * self.z


@lru_cache(64)
def _mix(a, b, q):
    """Fondu entre deux décors (même cadrage)."""
    return Image.blend(photo(a).convert("RGB"), photo(b).convert("RGB"), q / 32).convert("RGBA")


def decor(cam, a, b=None, q=0.0):
    im = photo(a) if b is None or q <= 0.001 else (photo(b) if q >= 0.999 else _mix(a, b, int(round(q * 32))))
    return zoomed(im, cam.z, cam.fx, cam.fy).copy()


def bed_pt(u, v):
    """(u, v) ∈ [0, 1]² → point du grand carré (u : gauche → droite, v : fond → devant)."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = BED
    lx, ly = lerp(x0, x3, v), lerp(y0, y3, v)
    rx, ry = lerp(x1, x2, v), lerp(y1, y2, v)
    return lerp(lx, rx, u), lerp(ly, ry, u)


# ------------------------------------------------------------ les mottes de fumier étalées sur le carré
@lru_cache(None)
def _fumier_src():
    im = Image.open(os.path.join(IMG, FUMIER + ".png")).convert("RGBA")
    return im.crop(im.getbbox())


@lru_cache(512)
def clump_img(w, rot, flat=0.55):
    src = _fumier_src()
    h = max(2, int(w * src.height / src.width * flat))
    im = src.resize((max(2, w), h), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    a[..., :3] *= 0.78                    # un fumier bien brun (la photo est très orangée)
    im = Image.fromarray(a.astype(np.uint8), "RGBA")
    return im.rotate(rot, resample=Image.BICUBIC, expand=True) if rot else im


def _stamps():
    r = np.random.default_rng(21)
    st = []
    for i in range(230):
        u, v = r.uniform(0.03, 0.97), r.uniform(0.02, 0.98)
        st.append((u, v, r.uniform(0.75, 1.25), int(r.choice([0, 0, 8, -8, 180])), r.uniform(0, 1)))
    st.sort(key=lambda s: s[1])          # du fond vers le devant
    return st


STAMPS = _stamps()
THROWS = [(6.0, 0.62, 0.55), (6.55, 0.35, 0.35), (7.1, 0.5, 0.8)]   # (temps, u, v) des fourchées


def stamp_t(u, v, rnd):
    """Quand chaque motte apparaît : d'abord autour des points de chute, puis le reste (on étale)."""
    best = min(t0 + 0.12 + 0.55 * math.hypot(u - tu, (v - tv) * 0.8) for t0, tu, tv in THROWS)
    return best + rnd * 0.25


def manure(c, cam, t, amount=1.0, decomp=0.0):
    """Le fumier posé sur le carré ; `decomp` : il se décompose et rentre dans la terre."""
    if amount <= 0.01:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for u, v, s, rot, rnd in STAMPS:
        t0 = stamp_t(u, v, rnd)
        q = clamp((t - t0) / 0.18)
        if q <= 0:
            continue
        x, y = cam.p(*bed_pt(u, v))
        persp = lerp(0.42, 1.0, v)
        w = int(150 * s * persp * cam.z * lerp(0.6, 1.0, ease_out(q)))
        im = clump_img(max(4, w // 4 * 4), rot)
        lay.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2 - 18 * (1 - q) * cam.z)))
    # découpé à la terre du carré (les mottes ne débordent pas sur les planches)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon([cam.p(*p) for p in BED], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(2))
    a = np.asarray(lay.getchannel("A")).astype(np.float32) * (np.asarray(m) / 255.0) * amount * (1 - 0.85 * decomp)
    lay.putalpha(Image.fromarray(a.astype(np.uint8)))
    if decomp > 0.01:   # il fonce et se mêle à la terre
        dark = Image.new("RGBA", (W, H), (40, 28, 18, 0))
        dark.putalpha(Image.fromarray((a * 0.5 * decomp).astype(np.uint8)))
        lay.alpha_composite(dark)
    c.alpha_composite(lay)


def snowfall(c, t, a, n=110):
    if a <= 0.01:
        return
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(13)
    for _ in range(n):
        sp = r.uniform(90, 200)
        x = r.uniform(0, W) + math.sin(t * 1.4 + r.uniform(0, 6)) * 20
        y = (r.uniform(0, H) + t * sp) % H
        s = r.uniform(2.5, 7)
        d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 255, 255, int(220 * a)))


def rainfall(c, t, a):
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (30, 40, 60, int(75 * a)))
    d = ImageDraw.Draw(ov)
    r = np.random.default_rng(17)
    for _ in range(160):
        sp = r.uniform(1800, 2600)
        x = r.uniform(-100, W + 100)
        y = (r.uniform(0, H) + t * sp) % (H + 200) - 100
        ln = r.uniform(40, 80)
        d.line([(x, y), (x - ln * 0.25, y + ln)], fill=(225, 236, 248, int(220 * a)), width=3)
    c.alpha_composite(ov)


def frost(c, a):
    if a <= 0.01:
        return
    c.alpha_composite(Image.new("RGBA", (W, H), (170, 205, 255, int(70 * a))))


# ============================================================ A. LE POTAGER SOUS LA NEIGE (0 → 4.5)
def s_snow(t):
    cam = Cam(lerp(1.0, 1.08, clamp(t / 4.5)), 540, 1000)
    w = decor(cam, NEIGE)
    snowfall(w, t, 1.0)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 0.4:
        put(u, snow_badge(), 880, 610, life(t, 0.45, 2.2))
    title(u, "FAIS ÇA CET HIVER…", t, 0.05, 2.25, y=330, color=WHITE, size=125)
    title(u, "SINON…", t, 2.28, 3.4, y=330, color=YEL, size=180)
    stamp(u, "GARE AU PRINTEMPS !", 540, 340, t, 3.5, None, RED, 92, -6)
    return w, u


cue(0.08, "whoosh", 0.12)
cue(0.47, "pop_hi", 0.12)
cue(2.3, "tick", 0.14)
cue(3.52, "alert1", 0.2)


# ============================================================ B. ON ÉTALE LE FUMIER, EN SURFACE (4.5 → 11.85)
CAM_WIDE = (1.08, 540, 1000)
CAM_EDGE = (1.75, 300, 1500)                     # coin avant-gauche du carré : l'épaisseur du fumier
EDGE_T = (8.9, 9.7)
FORK_W = 560


def fork_pos(t):
    """La fourche (photo, dents en bas à droite) : arrive de la droite, plonge vers chaque point de chute."""
    base = (900, 900)
    if t < 5.65:
        k = ease_out((t - 5.1) / 0.55)
        return lerp(1600, base[0], k), lerp(500, base[1], k)
    for t0, uu, vv in THROWS:
        if t0 - 0.35 <= t < t0 + 0.25:
            tx, ty = bed_pt(uu, vv)
            k = math.sin(math.pi * clamp((t - (t0 - 0.35)) / 0.6))
            return lerp(base[0], tx + 160, k), lerp(base[1], ty - 330, k)
    if t > THROWS[-1][0] + 0.25:
        k = ease_in((t - THROWS[-1][0] - 0.25) / 0.4)
        return lerp(base[0], 1700, k), lerp(base[1], 400, k)
    return base


def s_spread(t):
    if t < EDGE_T[0]:
        cam = Cam(*CAM_WIDE)
    elif t < 11.0:
        k = ease_io((t - EDGE_T[0]) / (EDGE_T[1] - EDGE_T[0]))
        cam = Cam(*[lerp(a, b, k) for a, b in zip(CAM_WIDE, CAM_EDGE)])
    else:
        k = ease_io((t - 11.0) / 0.85)
        cam = Cam(*[lerp(a, b, k) for a, b in zip(CAM_EDGE, CAM_WIDE)])
    z = cam.z
    w = decor(cam, NEIGE)
    snowfall(w, t, 0.5, 60)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    manure(w, cam, t)
    # la fourche chargée de fumier
    if 5.1 < t < 7.8:
        fx, fy = fork_pos(t)
        X, Y = cam.p(fx, fy)
        carrying = any(t0 - 0.9 < t < t0 for t0, _, _ in THROWS) or t < THROWS[0][0]
        ob(w, FOURCHE, X, Y, FORK_W * z)
        if carrying:   # la fourchée sur les dents
            k = FORK_W * z / 960
            ob(w, FUMIER, X + 300 * k, Y + 230 * k, 260 * k * 1.6)
        for t0, uu, vv in THROWS:   # la motte vole jusqu'au carré
            if t0 - 0.05 < t < t0 + 0.3:
                q = clamp((t - t0 + 0.05) / 0.3)
                tx, ty = cam.p(*bed_pt(uu, vv))
                k = FORK_W * z / 960
                sx, sy = X + 300 * k, Y + 230 * k
                ob(w, FUMIER, lerp(sx, tx, q), lerp(sy, ty, q) - 160 * z * math.sin(math.pi * q), 180 * z * (1 - 0.3 * q))
            if t0 + 0.2 < t < t0 + 0.6:
                tx, ty = cam.p(*bed_pt(uu, vv))
                particles(w, t, t0 + 0.22, tx, ty, 12, int(t0 * 10), col=(90, 60, 35), size=6 * z, up=220, spread=260,
                          dur=0.4)
    # « pas besoin de l'enterrer » : la fourche plantée, barrée
    if 7.75 < t < 8.95:
        k = ease_out((t - 7.78) / 0.3)
        X, Y = cam.p(*bed_pt(0.5, 0.55))
        ob(w, FOURCHE_D, X, lerp(Y - 900, Y - 300 * z, k), 300 * z)
        put(u, icon("nosign", 260), X, Y - 520, life(t, 8.05, 8.9))
    # « en surface, sur quelques centimètres » : la règle sur le bord avant du carré
    if t > 9.7 and t < 11.3:
        x0, y0 = cam.p(140, 1612)
        measure(u, x0 - 40, y0 - 40 * z, y0, "QUELQUES CM", life(t, 10.4, 11.2))
        put(u, icon("check", 150), 860, 700, life(t, 9.75, 11.2))
    w.alpha_composite(shade())
    title(u, "EN HIVER…", t, 4.6, 5.9, y=330, color=WHITE, size=180)
    title(u, "ÉTALE DU FUMIER !", t, 5.92, 7.72, y=330, color=YEL, size=140)
    title(u, "PAS BESOIN D'ENTERRER", t, 7.76, 8.84, y=330, color=WHITE, size=110)
    title(u, "POSE-LE EN SURFACE", t, 8.88, None, y=330, color=GREEN, size=118)
    return w, u


cue(5.15, "whoosh", 0.12)
for _t0, _u, _v in THROWS:
    cue(_t0 - 0.05, "whoosh_up", 0.1)
    cue(_t0 + 0.22, "thud", 0.22)
    cue(_t0 + 0.24, "rustle", 0.14)
cue(7.8, "chop", 0.2)
cue(8.07, "fail", 0.18)
cue(8.95, "whoosh", 0.1)
cue(9.77, "ding", 0.18)


# ============================================================ C. LA PLUIE, LE GEL, LES VERS (11.85 → 16.25)
WORMS = [(0.3, 0.45, 15), (0.62, 0.62, -20), (0.45, 0.8, 30), (0.75, 0.35, -40)]


def s_nature(t):
    cam = Cam(*CAM_WIDE)
    z = cam.z
    rain_a = fade(t, 12.75, 13.45, 0.15, 0.2)
    gel_a = fade(t, 13.4, 14.15, 0.15, 0.25)
    w = decor(cam, NEIGE)
    decomp = ease_io(clamp((t - 14.4) / 1.6))
    manure(w, cam, 99.0, 1.0, decomp)
    # les vers de terre sortent et remuent
    if t > 14.1:
        for i, (uu, vv, rot) in enumerate(WORMS):
            a_ = life(t, 14.15 + i * 0.12, 16.2)
            if a_ <= 0.01:
                continue
            X, Y = cam.p(*bed_pt(uu + 0.03 * math.sin(t * 1.3 + i), vv))
            ob(w, VER, X, Y, 280 * z * lerp(0.6, 1.0, vv), rot=rot + 10 * math.sin(t * 5 + i), alpha=a_,
               flip=i % 2 == 1)
    rainfall(w, t, rain_a)
    frost(w, gel_a)
    if gel_a > 0.01:
        sparkles(w, t, 13.45, 540, 1200, 450, 14, 6)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    act = 0 if t < 13.4 else (1 if t < 14.1 else 2)
    pills(u, ["PLUIE", "GEL", "VERS"], act, t, 12.75, 15.0, y=560, pw=230)
    title(u, "ENSUITE…", t, 11.9, 12.75, y=330, color=WHITE, size=180)
    title(u, "LA NATURE TRAVAILLE", t, 12.8, 14.75, y=330, color=YEL, size=112)
    title(u, "POUR TOI !", t, 14.8, None, y=330, color=GREEN, size=170)
    return w, u


cue(11.9, "pop", 0.14)
cue(12.75, "rain", 0.25)
cue(13.45, "sparkle", 0.16)
cue(14.18, "squish", 0.16)
cue(14.5, "squish", 0.12)
cue(14.85, "success", 0.16)


# ============================================================ D. ATTENTION AUX CAROTTES (16.25 → 20.35)
def s_carrots(t):
    cam = Cam(lerp(1.08, 1.15, clamp((t - 16.25) / 4)), 540, 1000)
    w = decor(cam, VIDES)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    X, Y = cam.p(*bed_pt(0.5, 0.55))
    s_in = ease_out_back(clamp((t - 17.6) / 0.35), 1.6)
    shake = math.sin(t * 40) * 10 * fade(t, 19.25, 19.9, 0.05, 0.2) if t > 19.25 else 0.0
    shadow(w, X, Y + 150, 600 * s_in, 80)
    ob(w, CAROTTES, X + shake, Y, 700 * max(0.01, s_in), rot=-8 + shake * 0.4)
    # le fumier, barré, à côté
    if t > 18.4:
        a_ = life(t, 18.45)
        fx_, fy_ = cam.p(*bed_pt(0.2, 0.15))
        ob(w, FUMIER, fx_ + 40, fy_ + 10, 380, alpha=a_)
        put(u, icon("nosign", 170), fx_ + 200, fy_ - 110, a_)
    w.alpha_composite(shade())
    title(u, "MAIS ATTENTION !", t, 16.3, 17.55, y=330, color=RED, size=150)
    title(u, "PAS POUR LES CAROTTES", t, 17.6, 19.25, y=330, color=YEL, size=108)
    stamp(u, "ELLES DÉTESTENT ÇA !", 540, 340, t, 19.3, None, RED, 92, -6)
    return w, u


cue(16.32, "alert2", 0.18)
cue(17.62, "pop", 0.16)
cue(18.47, "fail", 0.16)
cue(19.32, "alert1", 0.2)


# ============================================================ E. AU PRINTEMPS : RICHE, SOUPLE, PRÊTE (20.35 → 24.3)
def s_spring(t):
    cam = Cam(lerp(1.08, 1.0, clamp((t - 20.35) / 3.9)), 540, 1000)
    q1 = ease_io(clamp((t - 20.45) / 0.8))           # la neige et le fumier → la terre riche du printemps
    q2 = ease_io(clamp((t - 23.3) / 0.6))            # → le potager planté
    if q2 > 0:
        w = decor(cam, VIDES, PLANTES, q2)
    else:
        w = decor(cam, NEIGE, VIDES, q1)
        if q1 < 1:
            manure(w, cam, 99.0, 1.0 - q1, 1.0)
    light_rays(w, 860, 0, t, q1)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 20.9:
        put(u, icon("sun", 190), 900, 600, life(t, 20.95))
    labels = ["RICHE", "SOUPLE", "PRÊTE"]
    act = 0 if t < 22.62 else (1 if t < 23.34 else 2)
    if t > 21.95:
        pills(u, labels, act, t, 22.0, None, y=1380, pw=230)
    if t > 23.36:
        sparkles(u, t, 23.38, 540, 1100, 420, 14, 3)
    title(u, "AU PRINTEMPS…", t, 20.4, 21.95, y=330, color=YEL, size=150)
    title(u, "UNE TERRE AU TOP !", t, 22.0, None, y=330, color=GREEN, size=130)
    return w, u


cue(20.42, "whoosh_up", 0.12)
cue(20.97, "bird", 0.14)
cue(22.05, "pop", 0.14)
cue(22.66, "pop", 0.14)
cue(23.38, "success", 0.2)


# ============================================================ F. ABONNE-TOI (24.3 → fin)
def s_end(t):
    cam = Cam(1.0, 540, 1000)
    w = decor(cam, PLANTES)
    light_rays(w, 860, 0, t, 1.0)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    clicked = t > 25.75
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 25.7) / 0.15))
    put(u, btn, 540, 1400, life(t, 24.45) * press)
    if t > 25.15:
        kk = ease_out((t - 25.15) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 26.85, dur=0.45))
    sparkles(u, t, 26.95, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 24.35, 26.8, y=330, color=YEL, size=135)
    return w, u


cue(24.4, "pop_lo", 0.18)
cue(25.73, "click", 0.3)
cue(26.95, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 4.5 - SHIFT, _sh(s_snow)),
    (4.5 - SHIFT, 11.85 - SHIFT, _sh(s_spread)),
    (11.85 - SHIFT, 16.25 - SHIFT, _sh(s_nature)),
    (16.25 - SHIFT, 20.35 - SHIFT, _sh(s_carrots)),
    (20.35 - SHIFT, 24.3 - SHIFT, _sh(s_spring)),
    (24.3 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
