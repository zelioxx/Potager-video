"""Storyboard « Tailler ses arbres fruitiers en hiver » (voix : assets/audio/taille/voix.wav, volume d'origine).

Décor fourni : la prairie (été) ; versions dérivées : la même prairie givrée (gel) et un jour d'hiver sans gel.
Images fournies (planches agrandies ×2 puis détourées) : un cerisier aux 4 saisons (fleurs, cerises, automne, nu),
un verger de pommiers (feuilles, pommes, nu, taillé) et un cerisier à droite, une branche (coupe arrachée, coupe nette, nette givrée, éclatée par le gel).
0–4.4     la prairie gelée, les deux arbres nus : tu tailles en plein gel ? ARRÊTE ! tu les abîmes.
4.4–7.3   (fond beige) la branche gèle : le bois devient cassant.
7.3–12.0  la coupe éclate, cicatrise mal, le froid entre dans la plaie.
12.0–16.4 jour d'hiver sans gel : le pommier se taille (nu → taillé) ; oui en hiver, mais un jour sans gel.
16.4–22.2 attention : le cerisier ne se taille jamais en hiver… attends la fin de l'été (la prairie verdit, cerises).
22.2–25.3 (fond beige) coupe arrachée (sécateur sale, émoussé) / coupe nette (propre et aiguisé).
25.3–fin  la prairie d'été, pommes et cerises ; bouton S'abonner et logo.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, put, title, life, fade, ease_out, ease_io, ease_in,
                 ease_out_back, clamp, lerp, icon, tag, button_img, text_img, F_TITLE, light_rays, particles)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade, swap
from scenes_fumier import Cam, decor, snowfall
from scenes_arrosage_soir import thermo_cold
from scenes_rotation import plant, beige, _img
from scenes_pothos_lumiere import soft_shadow, sp, _src

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
ETE, GIVRE, GRIS = "decor_prairie.webp", "decor_prairie_givree.webp", "decor_prairie_hiver.jpg"
CER = [B + f"cerisier_{k}" for k in range(1, 5)]      # fleurs, cerises, automne, nu
POM = [B + f"pommier_{k}" for k in range(1, 5)]       # feuilles, pommes, nu, taillé
BR = [B + f"branche_{k}" for k in range(1, 5)]        # arrachée, nette, nette givrée, éclatée givrée

P_SPOT, C_SPOT = (330, 1580), (775, 1540)       # pieds du pommier et du cerisier (prairie plein écran)
TREE_W = 640                                     # largeur du quart de planche à l'écran (zoom 1)


# le verger : rangées de pommiers derrière (du fond vers l'avant) ; (x, y du pied, largeur du cadre)
ORCHARD = [(280, 1175, 190), (420, 1172, 185), (560, 1170, 185), (700, 1172, 190),     # fond (dans l'herbe,
           (300, 1260, 260), (500, 1255, 255), (700, 1262, 260),                        # entre les haies)
           (560, 1380, 360)]


def orchard(c, cam, state, s=1.0, pruned=None):
    """Les pommiers du fond, tous au même stade (state : 1 feuilles, 2 pommes, 3 nu, 4 taillé)."""
    for i, (x, y, w) in enumerate(ORCHARD):
        st = state if pruned is None or i not in pruned else 4
        tree(c, cam, POM[st - 1], (x, y), w, s=s)


def tree(c, cam, name, spot, w=TREE_W, s=1.0, alpha=1.0):
    x, y = cam.p(*spot)
    soft_shadow(c, x, y, w * cam.z * 0.55, 80)
    plant(c, name, x, y, w * cam.z, alpha=alpha, s=s)


def tree_swap(c, cam, a, b, spot, q, w=TREE_W):
    k, s = swap(q)
    tree(c, cam, a if k == 0 else b, spot, w, s=s)


def branch(c, name, x, y, w, rot=0.0, s=1.0):
    """Branche horizontale (bout coupé à droite) de largeur w, centrée en (x, y)."""
    im = _src(name)
    sp(c, name, x, y, w * s * im.height / im.width, 0.5, 0.5, rot=rot)


def branch_swap(c, a, b, x, y, w, q, rot=0.0):
    k, s = swap(q)
    branch(c, a if k == 0 else b, x, y, w, rot, s)


def cut_pt(x, y, w, name=BR[3]):
    """Bout coupé (à droite) de la branche."""
    im = _src(name)
    h = w * im.height / im.width
    return x + 0.45 * w, y - 0.02 * h


# ============================================================ A. EN PLEIN GEL ? ARRÊTE ! (0 → 4.4)
def s_frost(t):
    cam = Cam(lerp(1.0, 1.12, ease_io(clamp(t / 4.4))), 540, 1150)
    w = decor(cam, GIVRE)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    orchard(lay, cam, 3, s=ease_out_back(clamp((t - 0.05) / 0.4), 1.3))
    tree(lay, cam, POM[2], P_SPOT, s=ease_out_back(clamp((t - 0.1) / 0.4), 1.4))
    tree(lay, cam, CER[3], C_SPOT, s=ease_out_back(clamp((t - 0.25) / 0.4), 1.4))
    w.alpha_composite(lay)
    snowfall(w, t, 0.6, 80)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    a = life(t, 0.8, 4.35)
    if a > 0.01:
        put(u, thermo_cold(170), 900, 640, a)
        put(u, text_img("-5 °C", F_TITLE, 90, BLUE, 7, DARK), 900, 790, a)
    if t > 3.5:
        put(u, icon("cross", 200), 540, 1000, ease_out_back(clamp((t - 3.5) / 0.3), 1.7))
    title(u, "TU TAILLES TES ARBRES", t, 0.05, 2.85, y=300, color=WHITE, size=110)
    title(u, "EN PLEIN GEL ?", t, 0.05, 2.85, y=430, color=BLUE, size=140)
    stamp(u, "ARRÊTE !", 540, 330, t, 2.9, 3.45, RED, 190, -6)
    title(u, "TU LES ABÎMES !", t, 3.47, None, y=330, color=RED, size=140)
    return w, u


cue(0.12, "pop_lo", 0.14)
cue(0.85, "crunch", 0.1)
cue(2.92, "thud", 0.22)
cue(2.95, "alert1", 0.16)
cue(3.52, "fail", 0.16)


# ============================================================ B. LE BOIS DEVIENT CASSANT (4.4 → 7.3)
BX, BY, BW = 470, 1000, 1060


def s_brittle(t):
    w = beige().copy()
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s = ease_out_back(clamp((t - 4.45) / 0.4), 1.4)
    branch_swap(lay, BR[1], BR[2], BX, BY, BW * s, clamp((t - 5.45) / 0.6), rot=4)
    w.alpha_composite(lay)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t > 5.5:
        sparkles(u, t, 5.55, BX, BY, 460, 10, 4, 0.9)
        put(u, icon("snow", 150), 870, 640, life(t, 5.5, None))
    if t > 6.3:
        tag(u, "CASSANT", 330, 1320, t, 6.35, None, rot=-5, size=72)
    title(u, "QUAND ILS GÈLENT…", t, 4.47, 6.25, y=330, color=BLUE, size=125)
    title(u, "LE BOIS DEVIENT CASSANT", t, 6.27, None, y=330, color=WHITE, size=100)
    return w, u


cue(4.48, "whoosh", 0.12)
cue(5.5, "crunch", 0.14)
cue(5.55, "sparkle", 0.12)
cue(6.35, "pop", 0.14)


# ============================================================ C. LA COUPE ÉCLATE, LE FROID ENTRE (7.3 → 12.0)
def cold_into(c, t, t0, x, y, a):
    """Des flocons et des traits de vent glacé convergent vers la plaie."""
    if a <= 0.01 or t < t0:
        return
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(6)
    for i in range(14):
        ang = r.uniform(-2.4, 0.9)
        dist0 = r.uniform(260, 520)
        ph = ((t - t0) * 0.9 + r.uniform(0, 1)) % 1
        dist = dist0 * (1 - ph)
        px, py = x + math.cos(ang) * dist, y + math.sin(ang) * dist
        al = a * math.sin(math.pi * ph)
        if i % 3 == 0:
            put(c, icon("snow", 70), px, py, al)
        else:
            L = 46
            d.line([(px, py), (px + math.cos(ang) * L, py + math.sin(ang) * L)],
                   fill=(220, 238, 255, int(230 * al)), width=6)


def s_crack(t):
    w = beige().copy()
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    q = clamp((t - 7.95) / 0.35)
    shake = math.sin(t * 70) * 14 * clamp((t - 8.05) / 0.05) * (1 - clamp((t - 8.1) / 0.45))
    if q < 1:
        branch(lay, BR[2], BX + shake, BY, BW, rot=4)
    else:
        branch(lay, BR[3], BX + shake, BY, BW, rot=4)
    w.alpha_composite(lay)
    cx, cy = cut_pt(BX, BY, BW)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if 8.0 < t < 8.9:      # éclats de bois
        particles(u, t, 8.05, cx, cy, 16, 4, col=(214, 176, 120), spread=380, up=420, size=14, dur=0.8)
    if t > 8.7:
        tag(u, "CICATRISE MAL", 330, 1330, t, 8.75, None, rot=-5, size=60)
        put(u, icon("cross", 120), 640, 1330, life(t, 8.8, None))
    cold_into(u, t, 10.0, cx, cy, fade(t, 10.0, None, 0.4))
    if t > 10.1:
        put(u, thermo_cold(150), 880, 640, life(t, 10.15, None))
    title(u, "TES COUPES ÉCLATENT…", t, 7.37, 9.9, y=330, color=RED, size=115)
    title(u, "LE FROID ENTRE DANS LA PLAIE", t, 9.95, None, y=330, color=BLUE, size=90)
    return w, u


cue(7.38, "whoosh", 0.12)
cue(8.05, "crunch", 0.22)
cue(8.08, "thud", 0.16)
cue(8.78, "fail", 0.14)
cue(10.0, "whoosh_up", 0.12)


# ============================================================ D. POMMIERS ET POIRIERS : EN HIVER, UN JOUR SANS GEL (12.0 → 16.4)
CUTS = (12.95, 13.2, 13.45)


def s_prune(t):
    cam = Cam(lerp(1.15, 1.25, clamp((t - 12.0) / 4.4)), P_SPOT[0] + 80, P_SPOT[1] - 520)
    w = decor(cam, GRIS)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    orchard(lay, cam, 3, pruned={4, 6, 7} if t > 13.6 else None)
    tree_swap(lay, cam, POM[2], POM[3], P_SPOT, clamp((t - 13.0) / 0.6))
    w.alpha_composite(lay)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    x, y = cam.p(*P_SPOT)
    for i, tc in enumerate(CUTS):    # petits éclats aux coupes
        particles(u, t, tc, x + (-120, 110, 10)[i] * cam.z, y - (650, 560, 860)[i] * cam.z, 6, 9 + i,
                  col=(150, 120, 90), spread=160, up=140, size=7, dur=0.5)
    if 14.3 < t < 15.2:
        put(u, icon("check", 150), 880, 760, ease_out_back(clamp((t - 14.3) / 0.3), 1.6))
    if t > 15.2:
        a = life(t, 15.25, None)
        put(u, icon("sun", 150), 880, 600, a)
        put(u, text_img("+5 °C", F_TITLE, 90, YEL, 7, DARK), 880, 740, a)
        put(u, icon("check", 130), 990, 600, ease_out_back(clamp((t - 15.4) / 0.3), 1.6))
    title(u, "TAILLE TES POMMIERS", t, 12.05, 14.25, y=300, color=WHITE, size=115)
    title(u, "ET TES POIRIERS", t, 12.05, 14.25, y=430, color=YEL, size=120)
    title(u, "EN HIVER, OUI…", t, 14.27, 15.15, y=330, color=WHITE, size=140)
    title(u, "MAIS UN JOUR SANS GEL !", t, 15.17, None, y=330, color=YEL, size=110)
    return w, u


cue(12.05, "whoosh", 0.12)
for _t in CUTS:
    cue(_t, "chop", 0.16)
cue(14.32, "ding", 0.14)
cue(15.3, "sparkle", 0.14)


# ============================================================ E. CERISIERS ET PRUNIERS : JAMAIS EN HIVER (16.4 → 22.2)
def s_cherry(t):
    summer = ease_io(clamp((t - 20.95) / 0.7))
    cam = Cam(lerp(1.15, 1.22, clamp((t - 16.4) / 5.8)), C_SPOT[0] - 80, C_SPOT[1] - 520)
    w = decor(cam, GRIS, ETE, summer)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t < 21.0:
        orchard(lay, cam, 4)
    else:
        orchard(lay, cam, 1)
    tree_swap(lay, cam, CER[3], CER[1], C_SPOT, clamp((t - 21.0) / 0.6))
    w.alpha_composite(lay)
    if summer > 0.01:
        light_rays(w, 860, 200, t, summer)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    x, y = cam.p(*C_SPOT)
    if 19.55 < t < 20.95:
        put(u, icon("nosign", 300), x, y - 600 * cam.z, ease_out_back(clamp((t - 19.6) / 0.3), 1.6) *
            life(t, 19.6, 20.9))
        put(u, icon("snow", 140), 180, 640, life(t, 19.6, 20.9))
    if t > 21.0:
        put(u, icon("sun", 170), 180, 640, life(t, 21.05, None))
        tag(u, "FIN AOÛT", 210, 820, t, 21.4, None, rot=-5, size=60)
        put(u, icon("check", 140), x + 260, y - 900 * cam.z, ease_out_back(clamp((t - 21.5) / 0.3), 1.6))
    stamp(u, "ATTENTION !", 540, 330, t, 16.6, 17.45, RED, 150, -6)
    title(u, "CERISIERS ET PRUNIERS…", t, 17.47, 19.55, y=330, color=WHITE, size=105)
    title(u, "JAMAIS EN HIVER !", t, 19.57, 20.95, y=330, color=RED, size=135)
    title(u, "ATTENDS LA FIN DE L'ÉTÉ", t, 20.97, None, y=330, color=YEL, size=105)
    return w, u


cue(16.45, "whoosh", 0.1)
cue(16.62, "alert2", 0.16)
cue(19.6, "thud", 0.18)
cue(21.0, "whoosh_up", 0.12)
cue(21.3, "sparkle", 0.14)


# ============================================================ F. UN SÉCATEUR PROPRE ET AIGUISÉ (22.2 → 25.3)
def s_tool(t):
    w = beige().copy()
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, (nm, y, good, lbl, t0) in enumerate(((BR[0], 700, False, "SALE, ÉMOUSSÉ", 22.45),
                                               (BR[1], 1110, True, "PROPRE ET AIGUISÉ", 23.3))):
        s = ease_out_back(clamp((t - t0) / 0.4), 1.4)
        if s > 0.01:
            branch(lay, nm, 470, y, 960 * s, rot=(-3, 3)[i])
            cx, cy = cut_pt(470, y, 960, nm)
            put(u, icon("check" if good else "cross", 130), cx, cy - 170, s)
            tag(u, lbl, 330, y + 170, t, t0 + 0.2, None, rot=(-5, 4)[i], size=52)
    if t > 24.0:
        cx, cy = cut_pt(470, 1110, 960, BR[1])
        sparkles(u, t, 24.0, cx, cy, 200, 9, 6, 1.0)
    w.alpha_composite(lay)
    title(u, "TOUJOURS UN SÉCATEUR…", t, 22.47, 23.85, y=330, color=WHITE, size=110)
    title(u, "PROPRE ET AIGUISÉ !", t, 23.87, None, y=330, color=GREEN, size=125)
    return w, u


cue(22.48, "whoosh", 0.1)
cue(22.5, "pop_lo", 0.14)
cue(23.35, "pop", 0.16)
cue(24.02, "sparkle", 0.16)


# ============================================================ G. ABONNE-TOI (25.3 → fin)
def s_end(t):
    cam = Cam(1.0, 540, 1100)
    w = decor(cam, ETE)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    orchard(lay, cam, 2)
    tree(lay, cam, POM[1], P_SPOT)
    tree(lay, cam, CER[1], C_SPOT)
    w.alpha_composite(lay)
    light_rays(w, 860, 150, t, 0.7)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    clicked = t > 26.95
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 26.9) / 0.15))
    put(u, btn, 540, 1400, life(t, 25.5) * press)
    if t > 26.4:
        kk = ease_out((t - 26.4) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 27.75, dur=0.45))
    sparkles(u, t, 27.85, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 25.4, 27.7, y=330, color=YEL, size=135)
    return w, u


cue(25.45, "pop_lo", 0.18)
cue(26.93, "click", 0.3)
cue(27.85, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 4.4 - SHIFT, _sh(s_frost)),
    (4.4 - SHIFT, 7.3 - SHIFT, _sh(s_brittle)),
    (7.3 - SHIFT, 12.0 - SHIFT, _sh(s_crack)),
    (12.0 - SHIFT, 16.4 - SHIFT, _sh(s_prune)),
    (16.4 - SHIFT, 22.2 - SHIFT, _sh(s_cherry)),
    (22.2 - SHIFT, 25.3 - SHIFT, _sh(s_tool)),
    (25.3 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
