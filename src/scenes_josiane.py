"""Storyboard « Josiane : faire vraiment rougir les tomates vertes » (voix : assets/audio/josiane/voix.wav).

Ouverture nouvelle (le salon, l'émoji qui rit aux larmes, la bêche barrée : « pas une jardinière »), puis
« plus sérieusement » le potager enneigé et son pied de tomates vertes ; la suite reprend les scènes de la vidéo
des tomates vertes (scenes_tomates_vertes), recalées mot à mot sur cette nouvelle voix (correspondance des temps
par interpolation entre les mots repères), avec leurs bruitages déplacés de la même façon.
0–5.2     le salon : 😂 « Josiane… super humoriste ! » puis la bêche barrée : « mais pas une jardinière ! ».
5.2–9.85  plus sérieusement : le potager, zoom sur la grappe ; une tomate verte qui devient rouge.
9.85–fin  cueillir avant le gel, journal, boîte au chaud, la banane, une à deux semaines, abonne-toi.
"""
import math

import numpy as np
from PIL import Image

from gfx import (W, H, YEL, RED, GREEN, WHITE, put, title, life, ease_out_back, ease_io, clamp, lerp, icon)
from scenes import sparkles
from scenes_hortensia import stamp
from scenes_citron import shade, swap
from scenes_fumier import Cam, decor, snowfall
from scenes_pothos_lumiere import sp, soft_shadow
import scenes_tomates_vertes as TV

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
SALON = "decor_salon_table_fenetre.jpg"
EMOJI, BECHE = B + "emoji_rire", B + "pelle_droite"

# mots repères : (temps dans cette voix, temps dans la voix des tomates vertes)
ANCH = [(9.85, 5.85), (9.92, 5.92), (10.56, 6.60), (12.16, 8.16), (12.84, 8.92), (13.52, 9.52), (14.08, 9.92),
        (15.80, 11.60), (16.48, 12.28), (17.20, 13.04), (18.00, 13.80), (18.40, 14.16), (19.60, 15.40),
        (20.16, 15.92), (21.44, 17.60), (22.64, 18.92), (23.68, 19.84), (25.12, 21.28), (25.64, 21.96),
        (26.28, 22.56), (28.72, 25.12), (31.0, 27.4)]
_N, _O = np.array([a for a, b in ANCH]), np.array([b for a, b in ANCH])


def to_old(t):
    return float(np.interp(t, _N, _O))


def to_new(t):
    return float(np.interp(t, _O, _N))


# ============================================================ A. JOSIANE : SUPER HUMORISTE, PAS JARDINIÈRE (0 → 5.2)
def s_salon(t):
    cam = Cam(lerp(1.05, 1.18, clamp(t / 5.2)), 540, 1050)
    w = decor(cam, SALON)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    # l'émoji qui rit aux larmes (il se secoue de rire), puis il se pousse dans un coin pour la bêche
    pop = ease_out_back(clamp((t - 0.25) / 0.35), 1.6)
    laugh = 1.0 if t < 1.4 else 0.45
    side = ease_io(clamp((t - 3.8) / 0.45))
    ex, ey = lerp(540, 850, side), lerp(980, 1180, side)
    es = lerp(560, 260, side) * pop
    if es > 2:
        rot = math.sin(t * 2 * math.pi * 4.2) * 9 * laugh
        hop = abs(math.sin(t * 2 * math.pi * 4.2)) * 22 * laugh * (1 - side)
        sp(u, EMOJI, ex, ey - hop, es * 0.89, 0.5, 0.5, rot=rot)
    sparkles(u, t, 0.35, 540, 980, 360, 8, 3, 0.9)
    # la bêche, barrée : pas une jardinière
    b = ease_out_back(clamp((t - 3.85) / 0.4), 1.5)
    if b > 0.01:
        soft_shadow(u, 470, 1500, 260, 90)
        sp(u, BECHE, 470, 1500, 860 * b, 0.5, 1.0, rot=-8 + 3 * math.sin(t * 3))
    if t > 4.3:
        put(u, icon("cross", 250), 640, 820, ease_out_back(clamp((t - 4.3) / 0.3), 1.7))
    title(u, "JOSIANE…", t, 1.3, 2.05, y=330, color=WHITE, size=170)
    title(u, "SUPER HUMORISTE !", t, 2.08, 3.8, y=330, color=YEL, size=130)
    stamp(u, "PAS JARDINIÈRE !", 540, 340, t, 3.85, None, RED, 125, -6)
    return w, u


cue(0.27, "pop", 0.2)
cue(0.35, "sparkle", 0.14)
cue(2.1, "whoosh_up", 0.1)
cue(3.87, "thud", 0.2)
cue(4.32, "fail", 0.16)


# ============================================================ B. PLUS SÉRIEUSEMENT : FAIRE ROUGIR TES TOMATES VERTES (5.2 → 9.85)
def s_serious(t):
    k = ease_io(clamp((t - 5.5) / 2.6))
    cam = Cam(*[lerp(a, b, k) for a, b in zip(TV.CAM_A0, TV.CAM_A1)])
    w = TV.garden(cam)
    snowfall(w, t, 0.7, 70)
    w = TV.november(w, 0.6, 0.45)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    # la tomate verte qui devient rouge (sans superposition : on tasse, on change, on rebondit)
    s = life(t, 6.75, 9.8)
    if s > 0.01:
        kk, sc = swap(clamp((t - 8.1) / 0.7))
        sp(u, TV.VERTE if kk == 0 else TV.ROUGE, 830, 840, 300 * s * sc, 0.5, 0.5)
        if t > 8.5:
            sparkles(u, t, 8.5, 830, 840, 220, 8, 7, 0.9)
    title(u, "PLUS SÉRIEUSEMENT…", t, 5.25, 6.7, y=330, color=WHITE, size=130)
    title(u, "FAIS VRAIMENT ROUGIR", t, 6.72, 8.6, y=330, color=RED, size=115)
    title(u, "TES TOMATES VERTES !", t, 8.62, None, y=330, color=GREEN, size=115)
    return w, u


cue(5.25, "whoosh", 0.12)
cue(5.6, "rustle", 0.12)
cue(6.75, "pop", 0.16)
cue(8.45, "sparkle", 0.16)


# ============================================================ la suite : scènes des tomates vertes, recalées
def _old(fn):
    return lambda t: fn(to_old(t + SHIFT))


for _t, _n, _g in TV.CUES:
    _to = _t + TV.SHIFT
    if _to >= 5.85:
        cue(to_new(_to), _n, _g)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 5.2 - SHIFT, _sh(s_salon)),
    (5.2 - SHIFT, 9.85 - SHIFT, _sh(s_serious)),
    (to_new(5.85) - SHIFT, to_new(9.45) - SHIFT, _old(TV.s_pick)),
    (to_new(9.45) - SHIFT, to_new(14.1) - SHIFT, _old(TV.s_wrap)),
    (to_new(14.1) - SHIFT, to_new(19.8) - SHIFT, _old(TV.s_banana)),
    (to_new(19.8) - SHIFT, to_new(22.5) - SHIFT, _old(TV.s_ripe)),
    (to_new(22.5) - SHIFT, 99.0, _old(TV.s_end)),
]

TRAPS = []
