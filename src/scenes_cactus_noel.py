"""Storyboard « Cactus de Noël : pourquoi il ne fleurit pas » (voix : assets/audio/cactus_noel/voix.mp3).

Décors fournis : le salon (table en chêne au premier plan, lampes, canapé), l'établi de la grange.
Objets : planche fournie détourée (cactus de Noël vert / en boutons / en fleurs, sapin décoré).
Lumière : tout est éclairé « pour de vrai » par une carte de lumière (pénombre + halo chaud de la lampe).
0–4.4     le salon le soir, la lampe allumée ; le cactus sans fleurs ; « c'est la lampe » : elle brille plus fort.
4.4–8.7   il lui faut de longues nuits : clic, la lampe s'éteint, le salon plonge dans le noir complet.
8.7–14.9  la grange : pièce fraîche, sans lumière, 6 semaines (S1 → S6, lunes) ; on l'arrose très peu.
14.9–19.15 les boutons apparaissent ; ne le bouge plus, sinon ils tombent.
19.15–fin le salon de Noël : le cactus couvert de fleurs, le sapin qui scintille ; bouton S'abonner et logo.
"""
import json
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, put, title, life, fade, ease_out, ease_io,
                 ease_in, ease_out_back, clamp, lerp, icon, tag, button_img, particles, text_img, F_TITLE, pills,
                 hl_ellipse)
from scenes import sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp
from scenes_citron import shade, shadow, swap
from scenes_banane import ob
from scenes_fumier import Cam, decor
from scenes_arrosage_soir import thermo_cold

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)
SFX_GAIN = 0.27
DUCK = 0.45
TRANS_GAIN = 0.22
SHIFT = 0.25


def cue(t, name, gain=0.5):
    CUES.append((t - SHIFT, name, gain))


B = "banque/"
SALON, GRANGE = "decor_salon_table_bois.webp", "chrys_fond_etabli.png"
VERT, BOUT1, BOUT, FLEURI, SAPIN = (B + "cactus_noel", B + "cactus_noel_boutons1", B + "cactus_noel_boutons",
                                    B + "cactus_noel_fleuri", B + "sapin_noel")
META = json.load(open(os.path.join(IMG, "banque", "cactus_noel_meta.json")))
FULL = (0, 0, 1024, 1024)
LAMP = (955, 560)                                # abat-jour de la lampe (salon, plein écran)
CACTUS = (640, 1520)                             # bas de la soucoupe, sur la table du salon
POT_W = 300                                      # largeur de la soucoupe (zoom 1)
TREE = (215, 1060)                               # pied du sapin, au sol derrière la table
TREE_H = 560
BENCH = (520, 1330)                              # sur l'établi de la grange
LIGHTS = [(0.42, 0.25), (0.6, 0.33), (0.35, 0.42), (0.55, 0.47), (0.68, 0.55), (0.3, 0.6), (0.48, 0.66),
          (0.62, 0.72), (0.38, 0.78), (0.25, 0.82), (0.7, 0.8), (0.52, 0.86), (0.44, 0.36), (0.58, 0.6)]


def cactus(c, name, x, y, pot_w, s=1.0, rot=0.0):
    m = META[name.split("/")[-1]]
    place(c, name, FULL, pot_w / m["saucer_w"], m["cx"], m["bottom"], x, y, s, rot)


def sapin(c, cam, t, glow=1.0):
    x, y = cam.p(*TREE)
    hpx = TREE_H * cam.z
    m = META["sapin_noel"]
    place(c, SAPIN, FULL, hpx / 960, m["cx"], m["bottom"], x, y)
    if glow > 0.01:   # guirlande : petites lumières qui scintillent
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for i, (u, v) in enumerate(LIGHTS):
            px, py = x + (u - 0.47) * hpx * 0.75, y - hpx + v * hpx
            f = 0.5 + 0.5 * math.sin(t * 4 + i * 1.9)
            r = (4 + 3 * f) * cam.z * 0.6
            d.ellipse([px - r, py - r, px + r, py + r], fill=(255, 220, 140, int(255 * glow * (0.4 + 0.6 * f))))
        c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6)))
        c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.5)))


@lru_cache(None)
def _grid():
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    return xx, yy


def lighting(im, night, lamp=0.0, lamp_xy=(0, 0), sigma=520, warm=(1.0, 0.78, 0.5), tint=(0.62, 0.7, 1.0)):
    """Éclaire l'image : pénombre bleutée (night 0 → 1) et halo chaud d'une lampe (lamp 0 → 1)."""
    if night < 0.01 and lamp < 0.01:
        return im
    a = np.asarray(im.convert("RGB"), np.float32)
    xx, yy = _grid()
    amb = 1 - 0.82 * night
    m = np.empty_like(a)
    for k in range(3):
        m[..., k] = amb * (1 + night * (tint[k] - 1))
    if lamp > 0.01:
        lx, ly = lamp_xy
        g = np.exp(-((xx - lx) ** 2 + (yy - ly) ** 2) / (2 * sigma ** 2)) * lamp
        for k in range(3):
            m[..., k] += g * warm[k] * (0.35 + 0.75 * night)
    out = np.clip(a * m, 0, 255).astype(np.uint8)
    res = Image.fromarray(out).convert("RGBA")
    if lamp > 0.01:   # l'abat-jour lui-même rayonne
        lx, ly = lamp_xy
        b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(b).ellipse([lx - 90, ly - 90, lx + 90, ly + 90], fill=(255, 200, 120, int(150 * lamp)))
        res.alpha_composite(b.filter(ImageFilter.GaussianBlur(45)))
    return res


# ============================================================ A. LE SALON LE SOIR : C'EST LA LAMPE (0 → 4.4)
def s_salon(t):
    k = ease_io(clamp((t - 2.45) / 0.6)) * (1 - ease_io(clamp((t - 3.75) / 0.6)))
    cam = Cam(lerp(1.08, 1.7, k), lerp(600, LAMP[0] - 60, k), lerp(1150, LAMP[1] + 200, k))
    z = cam.z
    w = decor(cam, SALON)
    sapin(w, cam, t)
    x, y = cam.p(*CACTUS)
    shadow(w, x, y - 4, POT_W * z * 1.05, 90)
    cactus(w, VERT, x, y, POT_W * z)
    lamp = 0.55 + 0.45 * fade(t, 2.45, None, 0.3)
    w = lighting(w, 0.55, lamp, cam.p(*LAMP), sigma=520 * z)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if 2.5 < t < 3.9:
        lx, ly = cam.p(*LAMP)
        hl_ellipse(u, lx, ly + 20, 150, 170, life(t, 2.55, 3.8))
    title(u, "TON CACTUS DE NOËL…", t, 0.05, 1.35, y=330, color=YEL, size=120)
    title(u, "NE FLEURIT JAMAIS ?", t, 1.4, 2.35, y=330, color=WHITE, size=130)
    stamp(u, "C'EST LA LAMPE !", 540, 340, t, 2.4, None, RED, 130, -6)
    return w, u


cue(0.1, "bell", 0.12)
cue(1.42, "tick", 0.12)
cue(2.42, "alert1", 0.2)
cue(2.5, "whoosh", 0.1)


# ============================================================ B. IL LUI FAUT DE LONGUES NUITS (4.4 → 8.7)
def s_night(t):
    cam = Cam(lerp(1.15, 1.45, clamp((t - 4.4) / 4.3)), CACTUS[0] - 60, CACTUS[1] - 330)
    z = cam.z
    w = decor(cam, SALON)
    sapin(w, cam, t, glow=1 - fade(t, 6.45, None, 0.15))
    x, y = cam.p(*CACTUS)
    shadow(w, x, y - 4, POT_W * z * 1.05, 90)
    cactus(w, VERT, x, y, POT_W * z)
    off = fade(t, 6.45, None, 0.12)                       # clic : la lampe s'éteint
    night = lerp(0.55, 0.97, ease_io(clamp((t - 6.45) / 1.4)))
    w = lighting(w, night, 1 - off, cam.p(*LAMP), sigma=520 * z)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 6.5:
        r = np.random.default_rng(3)
        for i in range(10):   # quelques étoiles « nuit »
            a_ = fade(t, 6.6 + i * 0.05, None, 0.4) * (0.6 + 0.4 * math.sin(t * 3 + i))
            put(u, text_img("✦", F_TITLE, int(r.uniform(30, 55)), (230, 235, 255)), r.uniform(80, 1000),
                r.uniform(560, 1000), a_)
    title(u, "POUR FLEURIR…", t, 4.45, 5.75, y=330, color=WHITE, size=160)
    title(u, "DE LONGUES NUITS", t, 5.8, 7.45, y=330, color=YEL, size=140)
    title(u, "DANS LE NOIR COMPLET !", t, 7.5, None, y=330, color=WHITE, size=110)
    return w, u


cue(4.47, "whoosh", 0.1)
cue(6.45, "click", 0.35)
cue(7.55, "sparkle", 0.1)


# ============================================================ C. LA GRANGE : FRAIS, SANS LUMIÈRE, 6 SEMAINES (8.7 → 14.9)
WEEKS = [9.2 + i * 0.32 for i in range(6)]


def s_grange(t):
    cam = Cam(lerp(1.05, 1.2, clamp((t - 8.7) / 6.2)), 520, 1150)
    z = cam.z
    w = decor(cam, GRANGE)
    x, y = cam.p(*BENCH)
    shadow(w, x, y - 4, POT_W * z * 1.0, 100)
    s_in = ease_out_back(clamp((t - 8.75) / 0.35), 1.4)
    cactus(w, VERT, x, y, POT_W * z, s=max(0.01, s_in))
    night = 0.62 + 0.25 * fade(t, 9.8, None, 1.0)
    w = lighting(w, night, 0.0, tint=(0.6, 0.72, 1.05))
    # « très peu » d'eau : l'arrosoir verse trois gouttes
    if 12.8 < t < 14.8:
        cin = ease_out(clamp((t - 12.85) / 0.35))
        cout = ease_in(clamp((t - 14.4) / 0.3))
        tilt = -30 * ease_io(clamp((t - 13.2) / 0.25)) * (1 - cout)
        cx, cy = lerp(-300, x - 230 * z, cin) - 600 * cout, y - 520 * z
        can = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ob(can, "banque/arrosoir_zinc", cx, cy, 300 * z, rot=tilt, flip=True)
        w.alpha_composite(can)
        sx, sy = cx + 140 * z, cy + 10 * z
        for i in range(3):
            q = clamp((t - 13.45 - i * 0.28) / 0.35)
            if 0 < q < 1:
                gx, gy = lerp(sx, x - 20 * z, q), lerp(sy, y - 260 * z, q * q)
                ImageDraw.Draw(w).ellipse([gx - 6, gy - 9, gx + 6, gy + 9], fill=(190, 220, 245, 230))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 9.15:
        act = sum(1 for tw in WEEKS if t >= tw) - 1
        if act >= 0:
            pills(u, [f"S{i + 1}" for i in range(6)], act, t, 9.2, 12.75, y=560, pw=138)
    if 9.9 < t < 12.75:
        put(u, thermo_cold(140), 170, 760, life(t, 9.95, 12.7))
        tag(u, "PIÈCE FRAÎCHE", 360, 760, t, 10.0, 12.7, rot=-5, size=50)
    if t > 13.5:
        tag(u, "TRÈS PEU !", 760, 760, t, 13.55, None, rot=5, size=58)
    title(u, "METS-LE DANS LE NOIR", t, 8.75, 11.6, y=330, color=WHITE, size=112)
    title(u, "PENDANT 6 SEMAINES", t, 11.65, 12.75, y=330, color=YEL, size=120)
    title(u, "ARROSE TRÈS PEU", t, 12.8, None, y=330, color=BLUE, size=135)
    return w, u


cue(8.77, "whoosh", 0.12)
cue(8.8, "thud", 0.14)
for _tw in WEEKS:
    cue(_tw, "tick", 0.1)
cue(13.5, "plop", 0.1)
cue(13.78, "plop", 0.1)
cue(14.06, "plop", 0.1)


# ============================================================ D. LES BOUTONS : NE LE BOUGE PLUS (14.9 → 19.15)
def s_buds(t):
    cam = Cam(lerp(1.5, 1.6, clamp((t - 14.9) / 4.2)), BENCH[0], BENCH[1] - 330)
    z = cam.z
    w = decor(cam, GRANGE)
    x, y = cam.p(*BENCH)
    shadow(w, x, y - 4, POT_W * z * 1.0, 100)
    which, sc = swap((t - 15.95) / 0.3)
    nm = VERT if which == 0 else BOUT
    # « sinon ils tombent » : on le bouge, il tremble et perd ses boutons
    push = ease_io(clamp((t - 17.4) / 0.45))
    shake = math.sin(t * 45) * 10 * fade(t, 17.4, 18.3, 0.05, 0.2) if 17.4 < t < 18.3 else 0.0
    px = x + push * 140 * z + shake
    nm = BOUT1 if t > 18.0 else nm                  # moins de boutons après la secousse
    cactus(w, nm, px, y, POT_W * z * sc, rot=shake * 0.3)
    if t > 17.75:   # les boutons qui tombent sur l'établi
        r = np.random.default_rng(6)
        d = ImageDraw.Draw(w)
        for i in range(9):
            t0 = 17.75 + r.uniform(0, 0.5)
            q = clamp((t - t0) / 0.45)
            if q <= 0:
                continue
            bx = px + r.uniform(-120, 120) * z + r.uniform(-30, 30) * z * q
            by = lerp(y - r.uniform(330, 420) * z, y - r.uniform(0, 20) * z, q * q)
            rr = 9 * z
            d.ellipse([bx - rr * 1.5, by - rr * 0.8, bx + rr * 1.5, by + rr * 0.8], fill=(214, 70, 130, 255))
    w = lighting(w, 0.55, 0.0, tint=(0.75, 0.82, 1.0))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if 15.95 < t < 17.35:
        tag(u, "BOUTONS !", 780, 760, t, 16.0, 17.3, rot=6, size=60)
        sparkles(u, t, 16.0, x, y - 330 * z, 300, 10, 4)
    if t > 17.2:
        put(u, icon("nosign", 200), 870, 760, life(t, 17.25))
    title(u, "MAIS ATTENTION…", t, 14.95, 15.9, y=330, color=WHITE, size=160)
    title(u, "DÈS LES BOUTONS…", t, 15.95, 17.2, y=330, color=YEL, size=150)
    title(u, "NE LE BOUGE PLUS !", t, 17.25, 18.25, y=330, color=RED, size=135)
    stamp(u, "ILS TOMBENT !", 540, 340, t, 18.3, None, RED, 140, -6)
    return w, u


cue(14.97, "alert2", 0.16)
cue(16.0, "pop", 0.16)
cue(17.42, "whoosh", 0.1)
cue(17.8, "fail", 0.16)


# ============================================================ E. IL FLEURIT SUR L'ÉTABLI (19.15 → 20.8)
def s_bloom_grange(t):
    cam = Cam(lerp(1.6, 1.7, clamp((t - 19.15) / 1.65)), BENCH[0], BENCH[1] - 330)
    z = cam.z
    w = decor(cam, GRANGE)
    x, y = cam.p(*BENCH)
    shadow(w, x, y - 4, POT_W * z * 1.0, 100)
    which, sc = swap((t - 19.95) / 0.3)
    cactus(w, BOUT if which == 0 else FLEURI, x, y, POT_W * z * sc)
    w = lighting(w, lerp(0.55, 0.3, fade(t, 19.95, None, 0.4)), 0.0, tint=(0.75, 0.82, 1.0))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 20.0:
        sparkles(u, t, 20.02, x, y - 330 * z, 330, 14, 3, dur=0.8)
    title(u, "QUELQUES SEMAINES PLUS TARD…", t, 19.2, None, y=330, color=WHITE, size=92)
    return w, u


cue(19.22, "whoosh", 0.1)
cue(20.0, "sparkle", 0.18)


# ============================================================ F. LE SALON DE NOËL : COUVERT DE FLEURS (20.8 → fin)
def s_bloom(t, end=False):
    k = ease_io(clamp((t - 20.85) / 1.4))
    cam = Cam(lerp(1.35, 1.1, k), lerp(CACTUS[0] - 60, 600, k), lerp(CACTUS[1] - 330, 1150, k))
    z = cam.z
    w = decor(cam, SALON)
    sapin(w, cam, t)
    x, y = cam.p(*CACTUS)
    shadow(w, x, y - 4, POT_W * z * 1.05, 90)
    cactus(w, FLEURI, x, y, POT_W * z)
    w = lighting(w, 0.42, 1.0, cam.p(*LAMP), sigma=600 * z)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 20.85:
        sparkles(u, t, 20.87, x, y - 300 * z, 330, 14, 3, dur=1.4)
    if not end:
        stamp(u, "COUVERT DE FLEURS !", 540, 340, t, 20.85, None, GREEN, 105, -6)
        return w, u
    clicked = t > 23.95
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 23.9) / 0.15))
    put(u, btn, 540, 1400, life(t, 22.6) * press)
    if t > 23.35:
        kk = ease_out((t - 23.35) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 24.9, dur=0.45))
    sparkles(u, t, 25.0, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 22.45, 24.85, y=330, color=YEL, size=135)
    return w, u


cue(20.88, "bell", 0.14)
cue(20.9, "success", 0.2)
cue(22.5, "pop_lo", 0.16)
cue(23.93, "click", 0.3)
cue(25.0, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 4.4 - SHIFT, _sh(s_salon)),
    (4.4 - SHIFT, 8.7 - SHIFT, _sh(s_night)),
    (8.7 - SHIFT, 14.9 - SHIFT, _sh(s_grange)),
    (14.9 - SHIFT, 19.15 - SHIFT, _sh(s_buds)),
    (19.15 - SHIFT, 20.8 - SHIFT, _sh(s_bloom_grange)),
    (20.8 - SHIFT, 22.4 - SHIFT, _sh(s_bloom)),
    (22.4 - SHIFT, 99.0, _sh(lambda t: s_bloom(t, end=True))),
]

TRAPS = []
