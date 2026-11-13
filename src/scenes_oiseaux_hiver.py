"""Storyboard « Les oiseaux au jardin en hiver » (voix : assets/audio/oiseaux_hiver/voix.mp3).

Décors fournis : le jardin sous la neige (maisons du village au fond), le potager ensoleillé (printemps).
Oiseaux et objets : planches fournies, détourées (mésanges charbonnières et bleue, merle, tournesols, pommes,
mangeoires, graines, pain). Les oiseaux reçoivent la lumière froide de la neige pour se fondre dans la photo.
0–4.6     le jardin enneigé : une mésange arrive en vol et se pose sur le massif, une mésange bleue la rejoint.
4.6–9.3   au printemps, dans le potager : la famille de mésanges plonge sur les chenilles (compteur qui grimpe).
9.3–12.8  quand il gèle : la mésange ébouriffée dans le froid, picore la neige… rien à manger.
12.8–18.4 comme les anciens : un tournesol séché dans le jardin (une mésange s'y pose), des pommes abîmées au
          pied de l'arbre (un merle vient les picorer).
18.4–22.35 par grand froid : la mangeoire en bois accrochée à l'arbre, les graines de tournesol, les mésanges.
22.35–26.1 jamais de pain : ça les gonfle sans les nourrir.
26.1–fin  le jardin, la mangeoire et les oiseaux ; bouton S'abonner et logo.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, put, title, life, fade, ease_out, ease_io, ease_in,
                 ease_out_back, clamp, lerp, icon, tag, button_img, particles, text_img, F_TITLE, background,
                 light_rays)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade, shadow
from scenes_banane import ob
from scenes_fumier import Cam, decor, snowfall
from scenes_arrosage_soir import snow_badge, thermo_cold

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
NEIGE, PRINTEMPS = "decor_jardin_neige.jpg", "decor_potager_ensoleille_salades.webp"
VOL, PROFIL, BLEUE, FACE = B + "mesange_vol", B + "mesange_profil", B + "mesange_bleue", B + "mesange_face"
PICORE, GRAINE_B, MARCHE, PLONGE = B + "mesange_picore", B + "mesange_graine", B + "mesange_marche", B + "mesange_plonge"
MERLE = B + "merle_sol"
TOURNESOL_SEC, POMME, POMME2 = B + "tournesol_sec", B + "pomme_rouge", B + "pomme_rouge2"
MANGEOIRE, GRAINES, PAIN = B + "mangeoire_toit", B + "graines_tournesol", B + "pain"
CHENILLE = B + "chenille"
COLD = np.array([0.9, 0.96, 1.07], np.float32)
BUSH = (235, 1380)                               # sommet du massif enneigé (photo plein écran)
TREE = (340, 1335)                               # pied du grand arbre
BRANCH = (560, 760)                              # branche où l'on accroche la mangeoire


def cold(lay, k=1.0):
    """Lumière froide et un peu ternie de la neige sur les objets ajoutés."""
    a = np.asarray(lay).astype(np.float32)
    rgb = a[..., :3]
    lum = rgb.mean(2, keepdims=True)
    rgb = rgb * (1 - 0.15 * k) + lum * 0.15 * k
    a[..., :3] = np.clip(rgb * (1 + k * (COLD - 1)), 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def bird(c, name, x, y, w, flip=False, t=0.0, hop=0.0, rot=0.0, alpha=1.0, bottom=True):
    """Oiseau posé (pieds en (x, y)) avec de petits sautillements / mouvements de tête."""
    b = abs(math.sin(t * 7.0)) * hop
    ob(c, name, x, y - b * w * 0.12, w, rot=rot + math.sin(t * 3.1) * 2, alpha=alpha,
       anchor="bottom" if bottom else "center", flip=flip)


def flight(c, x0, y0, x1, y1, q, w, t, flip=False):
    """Vol en arc de (x0, y0) à (x1, y1) (q ∈ [0, 1]), battements d'ailes."""
    x = lerp(x0, x1, ease_io(q))
    y = lerp(y0, y1, ease_io(q)) - math.sin(math.pi * q) * 120
    flap = 1 + 0.12 * math.sin(t * 40)
    ob(c, VOL, x, y, w * flap, rot=(-8 if flip else 8) * (1 - q), flip=flip)


def shadow_on_snow(c, x, y, w, a=60):
    shadow(c, x, y, w, a)


# ============================================================ A. LE JARDIN SOUS LA NEIGE (0 → 4.6)
def s_garden(t):
    k = ease_io(clamp((t - 1.9) / 1.8))
    cam = Cam(lerp(1.05, 2.1, k), lerp(540, BUSH[0] + 120, k), lerp(1100, BUSH[1] - 160, k))
    z = cam.z
    w = decor(cam, NEIGE)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bx, by = cam.p(*BUSH)
    # 1re mésange : arrive en vol et se pose sur le massif
    if 0.9 < t < 2.0:
        q = clamp((t - 0.9) / 1.1)
        flight(lay, 1200, 300, bx + 30 * z, by - 30 * z, q, lerp(120, 95 * z, q), t, flip=True)
    elif t >= 2.0:
        sq = 1 - 0.1 * math.sin(math.pi * clamp((t - 2.0) / 0.2))
        shadow_on_snow(lay, bx + 30 * z, by + 2, 60 * z)
        bird(lay, PROFIL, bx + 30 * z, by, 115 * z * sq, flip=False, t=t, hop=0.25 if t > 2.3 else 0)
    # mésange bleue qui la rejoint
    if 3.0 < t < 3.7:
        q = clamp((t - 3.0) / 0.7)
        flight(lay, -200, 600, bx - 70 * z, by - 10 * z, q, lerp(110, 80 * z, q), t)
    elif t >= 3.7:
        shadow_on_snow(lay, bx - 70 * z, by + 6, 50 * z)
        bird(lay, BLEUE, bx - 75 * z, by + 6 * z, 92 * z, flip=True, t=t + 1, hop=0.3)
    w.alpha_composite(cold(lay))
    snowfall(w, t, 1.0)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    put(u, snow_badge(), 900, 600, life(t, 0.3, 2.5))
    title(u, "TON JARDIN…", t, 0.05, 1.7, y=330, color=WHITE, size=170)
    title(u, "A BESOIN DES OISEAUX !", t, 1.75, 2.95, y=330, color=YEL, size=112)
    stamp(u, "ET EUX DE TOI !", 540, 340, t, 3.0, None, RED, 135, -6)
    return w, u


cue(0.08, "whoosh", 0.1)
cue(0.35, "pop_hi", 0.1)
cue(0.95, "bird", 0.22)
cue(2.0, "peck", 0.12)
cue(3.05, "bird", 0.18)
cue(3.02, "alert1", 0.16)


# ============================================================ B. AU PRINTEMPS : DES MILLIERS DE CHENILLES (4.6 → 9.3)
CATS = [(340, 1250, 20), (520, 1330, -15), (640, 1430, 30), (300, 1480, -25), (470, 1560, 10), (660, 1650, -30),
        (380, 1720, 15)]
DIVES = [5.9, 6.4, 6.9, 7.3, 7.7, 8.1, 8.5]       # une mésange plonge sur chaque chenille


def s_spring(t):
    cam = Cam(lerp(1.05, 1.15, clamp((t - 4.6) / 4.7)), 500, 1250)
    z = cam.z
    w = decor(cam, PRINTEMPS)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    eaten = 0
    for i, (x, y, rot) in enumerate(CATS):
        X, Y = cam.p(x, y)
        td = DIVES[i]
        if t < td + 0.25:   # la chenille rampe sur la salade
            a_ = life(t, 4.8 + i * 0.08, dur=0.25)
            ob(w, CHENILLE, X + math.sin(t * 2 + i) * 6, Y, 90 * z, rot=rot + 6 * math.sin(t * 5 + i), alpha=a_)
        else:
            eaten += 1
        if td - 0.35 < t < td + 0.55:   # la mésange plonge, attrape, repart
            q = (t - (td - 0.35)) / 0.9
            if q < 0.4:
                qq = q / 0.4
                ob(w, PLONGE, lerp(X + 380, X, ease_in(qq)), lerp(Y - 700, Y - 30, ease_in(qq)), 230 * z,
                   flip=True)
            else:
                qq = (q - 0.4) / 0.6
                ob(w, VOL, lerp(X, X - 420, ease_in(qq)), lerp(Y - 30, Y - 800, ease_in(qq)),
                   230 * z * (1 + 0.1 * math.sin(t * 40)))
                ob(w, CHENILLE, lerp(X, X - 420, ease_in(qq)) - 10, lerp(Y - 30, Y - 800, ease_in(qq)) + 30, 60 * z,
                   rot=70)
            if abs(t - td) < 0.25:
                particles(w, t, td - 0.02, X, Y, 8, i, col=(120, 170, 70), size=6, up=160, spread=180, dur=0.3)
    w.alpha_composite(shade())
    if t > 5.8:   # le compteur
        n = int(lerp(0, 5000, ease_in(clamp((t - 5.85) / 3.0))))
        lbl = f"{n:,}".replace(",", " ")
        box = text_img(lbl, F_TITLE, 120, YEL, stroke=8, stroke_fill=DARK)
        put(u, box, 540, 640, life(t, 5.85))
        put(u, text_img("CHENILLES MANGÉES", F_TITLE, 52, WHITE, stroke=5, stroke_fill=DARK), 540, 735, life(t, 5.9))
    title(u, "AU PRINTEMPS…", t, 4.65, 5.7, y=330, color=YEL, size=165)
    title(u, "UNE FAMILLE DE MÉSANGES", t, 5.75, 7.0, y=330, color=WHITE, size=100)
    stamp(u, "DES MILLIERS !", 540, 340, t, 7.05, None, GREEN, 140, -6)
    return w, u


cue(4.67, "bird", 0.18)
for _td in DIVES:
    cue(_td - 0.3, "whoosh_up", 0.07)
    cue(_td, "peck", 0.14)
cue(7.07, "success", 0.16)


# ============================================================ C. QUAND IL GÈLE : RIEN À MANGER (9.3 → 12.8)
SPOT = (620, 1560)                               # la mésange sur la neige


def s_frost(t):
    cam = Cam(lerp(2.5, 2.75, clamp((t - 9.3) / 3.5)), SPOT[0], SPOT[1] - 130)
    z = cam.z
    w = decor(cam, NEIGE)
    w.alpha_composite(Image.new("RGBA", (W, H), (170, 200, 255, int(55 * fade(t, 10.6, None, 0.6)))))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    X, Y = cam.p(*SPOT)
    shadow_on_snow(lay, X, Y + 4, 70 * z)
    if t < 11.6:   # ébouriffée, elle grelotte
        shiver = math.sin(t * 60) * 3 * fade(t, 10.65, None, 0.2)
        puff = 1 + 0.08 * fade(t, 10.65, None, 0.4)
        bird(lay, FACE, X + shiver, Y, 70 * z * puff, t=t)
    else:          # elle picore la neige… rien
        peck = abs(math.sin((t - 11.6) * 6))
        bird(lay, PICORE, X, Y + 4 * z * peck, 110 * z, flip=False, t=t, rot=-6 * peck)
        if peck > 0.85:
            particles(lay, t, t - 0.02, X - 45 * z, Y, 6, int(t * 10), col=(245, 248, 255), size=4 * z, up=80,
                      spread=90, dur=0.2)
    w.alpha_composite(cold(lay, 1.2))
    snowfall(w, t, 1.0)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 10.65:
        put(u, thermo_cold(150), 160, 720, life(t, 10.7))
        put(u, text_img("-5 °C", F_TITLE, 100, BLUE, stroke=7, stroke_fill=DARK), 300, 720, life(t, 10.75))
    if t > 11.7:
        put(u, icon("cross", 150), 900, 720, life(t, 11.75))
    title(u, "MAIS EN HIVER…", t, 9.35, 10.6, y=330, color=WHITE, size=165)
    title(u, "QUAND IL GÈLE…", t, 10.65, 11.6, y=330, color=BLUE, size=165)
    title(u, "RIEN À MANGER !", t, 11.65, None, y=330, color=RED, size=150)
    return w, u


cue(9.37, "whoosh", 0.1)
cue(10.7, "sparkle", 0.12)
cue(11.75, "fail", 0.16)
for _i in range(4):
    cue(11.7 + _i * 0.52, "peck", 0.08)


# ============================================================ D. COMME LES ANCIENS : TOURNESOLS ET POMMES (12.8 → 18.4)
SUN = (150, 1470)                                # pied du tournesol séché (à côté du massif)
SUN_H = 600                                      # tournesol séché : hauteur à l'écran (zoom 1)


def s_ancients(t):
    k = ease_io(clamp((t - 16.3) / 0.9))
    cam = Cam(lerp(1.3, 1.6, k), lerp(330, TREE[0] + 60, k), lerp(1150, TREE[1] - 160, k))
    z = cam.z
    w = decor(cam, NEIGE)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # le tournesol séché qui « pousse » hors de la neige
    g = ease_out_back(clamp((t - 14.4) / 0.5), 1.4)
    sx, sy = cam.p(*SUN)
    head = (sx + 4 * z * g, sy - SUN_H * 0.9 * z * g)
    if g > 0.01:
        ob(lay, TOURNESOL_SEC, sx, sy, SUN_H / 3.75 * z, s=g, anchor="bottom")
    if 15.2 < t < 15.75:
        q = clamp((t - 15.2) / 0.55)
        flight(lay, W + 100, 300, head[0] + 40 * z, head[1] - 10 * z, q, lerp(140, 90 * z, q), t, flip=True)
    elif t >= 15.75:
        peck = abs(math.sin((t - 15.75) * 5))
        bird(lay, PICORE, head[0] + 45 * z, head[1] + 8 * z, 90 * z, t=t, rot=-8 * peck)
    # les pommes abîmées tombent au pied de l'arbre ; un merle vient les picorer
    tx, ty = cam.p(*TREE)
    for i, (dx, nm, rot) in enumerate([(-60, POMME, -15), (70, POMME2, 20)]):
        q = clamp((t - 16.6 - i * 0.18) / 0.35)
        if q > 0:
            y = lerp(ty - 900, ty + 20 * z, ease_in(q)) - (25 * z * math.sin(math.pi * clamp((t - 16.95 - i * 0.18) / 0.2))
                                                          if q >= 1 else 0)
            shadow_on_snow(lay, tx + dx * z, ty + 22 * z, 60 * z * q)
            ob(lay, nm, tx + dx * z, y, 76 * z, rot=rot + (1 - q) * 120, rotten=0.55)
    if t > 17.3:
        q = ease_out(clamp((t - 17.3) / 0.45))
        mx = lerp(W + 200, tx + 200 * z, q)
        peck = abs(math.sin((t - 17.75) * 6)) if t > 17.75 else 0
        shadow_on_snow(lay, mx, ty + 40 * z, 120 * z)
        bird(lay, MERLE, mx, ty + 40 * z, 235 * z, flip=False, t=t, rot=-6 * peck, hop=0.3 * (1 - q))
    w.alpha_composite(cold(lay))
    snowfall(w, t, 0.8)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    title(u, "FAIS COMME LES ANCIENS !", t, 12.85, 14.3, y=330, color=YEL, size=100)
    title(u, "LES TOURNESOLS SÉCHÉS", t, 14.35, 16.5, y=330, color=WHITE, size=112)
    title(u, "LES POMMES ABÎMÉES", t, 16.55, None, y=330, color=WHITE, size=118)
    if t > 14.5:
        tag(u, "GRAINES", 820, 760, t, 14.6, 16.4, rot=-6, size=56)
    if t > 17.5:
        tag(u, "FESTIN !", 820, 760, t, 17.55, None, rot=5, size=60)
    return w, u


cue(12.87, "whoosh", 0.1)
cue(14.42, "pop", 0.14)
cue(15.22, "bird", 0.18)
cue(16.95, "thud", 0.16)
cue(17.13, "thud", 0.14)
cue(17.35, "bird", 0.14)


# ============================================================ E. PAR GRAND FROID : LA MANGEOIRE (18.4 → 22.35)
FEED_W = 230


def s_feeder(t):
    k = ease_io(clamp((t - 19.8) / 1.0))
    cam = Cam(lerp(1.2, 1.9, k), lerp(520, BRANCH[0], k), lerp(1000, BRANCH[1] + 120, k))
    z = cam.z
    w = decor(cam, NEIGE)
    w.alpha_composite(Image.new("RGBA", (W, H), (170, 200, 255, int(45 * fade(t, 18.45, None, 0.5)))))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fx, fy = cam.p(*BRANCH)
    drop = ease_out_back(clamp((t - 19.75) / 0.45), 1.3)
    swing = math.sin((t - 19.75) * 5) * 6 * math.exp(-max(0, t - 19.75) * 1.5) if t > 19.75 else 0
    if drop > 0.01:   # accrochée à la branche (le haut de la photo de la mangeoire = sa branche)
        top = lerp(-400, fy, drop)
        ob(lay, MANGEOIRE, fx, top + FEED_W * z * 0.5, FEED_W * z, rot=swing)
    birds = [(21.0, -70, PROFIL, False), (21.4, 75, GRAINE_B, True), (21.8, 0, MARCHE, False)]
    perch_y = fy + FEED_W * z * 0.86
    for i, (t0, dx, nm, fl) in enumerate(birds):
        if t0 < t < t0 + 0.5:
            q = (t - t0) / 0.5
            flight(lay, W + 150 if i % 2 == 0 else -150, 200, fx + dx * z, perch_y, q, lerp(140, 70 * z, q), t,
                   flip=i % 2 == 0)
        elif t >= t0 + 0.5:
            bird(lay, nm, fx + dx * z, perch_y, 85 * z, flip=fl, t=t + i, hop=0.2)
    w.alpha_composite(cold(lay, 0.8))
    snowfall(w, t, 1.0, 160)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 21.1:
        gi = Image.new("RGBA", (360, 360), (0, 0, 0, 0))
        ob(gi, GRAINES, 180, 180, 300)
        put(u, gi, 220, 1250, life(t, 21.15))
    title(u, "PAR GRAND FROID…", t, 18.45, 19.65, y=330, color=BLUE, size=150)
    title(u, "UNE MANGEOIRE EN BOIS", t, 19.7, 21.05, y=330, color=YEL, size=108)
    title(u, "GRAINES DE TOURNESOL", t, 21.1, None, y=330, color=WHITE, size=110)
    return w, u


cue(18.47, "whoosh", 0.1)
cue(19.78, "whoosh_up", 0.1)
cue(20.15, "chop", 0.12)
for _t0 in (21.0, 21.4, 21.8):
    cue(_t0, "bird", 0.12)
cue(21.15, "pop", 0.14)


# ============================================================ F. JAMAIS DE PAIN (22.35 → 26.1)
def s_bread(t):
    w = background("table")
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s_in = ease_out_back(clamp((t - 22.45) / 0.4), 1.5)
    shadow(w, 360, 1300, 460 * s_in, 80)
    ob(w, PAIN, 360, 1300, 480, s=max(0.01, s_in), anchor="bottom")
    # la mésange : elle grossit (gonflée) sans être nourrie
    puff = 1 + 0.35 * ease_out_back(clamp((t - 24.5) / 0.5), 2.0)
    shadow(w, 790, 1305, 200 * puff, 80)
    bird(w, FACE, 790, 1300, 190 * puff, t=t)
    if t > 23.45:
        put(u, icon("nosign", 360), 360, 1120, life(t, 23.5))
    if t > 25.3:
        put(u, icon("cross", 140), 960, 900, life(t, 25.35))
    title(u, "MAIS SURTOUT…", t, 22.4, 23.4, y=330, color=WHITE, size=170)
    stamp(u, "JAMAIS DE PAIN !", 540, 340, t, 23.45, 24.45, RED, 130, -6)
    title(u, "ÇA LES GONFLE…", t, 24.5, 25.3, y=330, color=YEL, size=150)
    title(u, "SANS LES NOURRIR !", t, 25.35, None, y=330, color=RED, size=130)
    return w, u


cue(22.47, "pop", 0.16)
cue(23.5, "alert1", 0.2)
cue(24.55, "squeak", 0.14)
cue(25.37, "fail", 0.16)


# ============================================================ G. ABONNE-TOI (26.1 → fin)
def s_end(t):
    cam = Cam(1.2, 520, 1000)
    z = cam.z
    w = decor(cam, NEIGE)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fx, fy = cam.p(*BRANCH)
    ob(lay, MANGEOIRE, fx, fy + FEED_W * z * 0.5, FEED_W * z)
    perch_y = fy + FEED_W * z * 0.86
    for i, (dx, nm, fl) in enumerate([(-70, PROFIL, False), (75, GRAINE_B, True)]):
        bird(lay, nm, fx + dx * z, perch_y, 72 * z, flip=fl, t=t + i, hop=0.2)
    bx, by = cam.p(*BUSH)
    bird(lay, BLEUE, bx, by + 6 * z, 80 * z, flip=True, t=t, hop=0.3)
    w.alpha_composite(cold(lay, 0.8))
    snowfall(w, t, 0.8)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    clicked = t > 27.55
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 27.5) / 0.15))
    put(u, btn, 540, 1400, life(t, 26.3) * press)
    if t > 26.95:
        kk = ease_out((t - 26.95) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 28.6, dur=0.45))
    sparkles(u, t, 28.7, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 26.2, 28.55, y=330, color=YEL, size=135)
    return w, u


cue(26.25, "pop_lo", 0.18)
cue(27.53, "click", 0.3)
cue(28.7, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 4.6 - SHIFT, _sh(s_garden)),
    (4.6 - SHIFT, 9.3 - SHIFT, _sh(s_spring)),
    (9.3 - SHIFT, 12.8 - SHIFT, _sh(s_frost)),
    (12.8 - SHIFT, 18.4 - SHIFT, _sh(s_ancients)),
    (18.4 - SHIFT, 22.35 - SHIFT, _sh(s_feeder)),
    (22.35 - SHIFT, 26.1 - SHIFT, _sh(s_bread)),
    (26.1 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
