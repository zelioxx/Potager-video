"""Storyboard « Le sapin qui perd ses aiguilles avant Noël » (voix : assets/audio/sapin/voix.wav, volume d'origine).

Nouveau style (inspiré des vidéos de référence) : plans larges presque fixes avec lente avancée, transitions
« coup de zoom » floutées, gros plans sur fond beige pour les gestes, peu de titres (un mot-clé fort), repère
① ② ③ en haut pour les 3 gestes, ambiance de pièce continue sous la voix, bruitages d'actions.
Décors fournis : deux vues d'un salon au soleil couchant. Images fournies (agrandies ×2, détourées) : sapin
emballé dans son filet, sapin dans son pied, sapin desséché, sapin décoré ; pied à réserve d'eau, scie, rondelle
de bois, carafe d'eau ; radiateur (planche précédente).
0–4.25    le salon : le sapin à côté du radiateur perd ses aiguilles (elles s'entassent au sol).
4.25–8.1  fond beige : un sapin coupé, c'est comme un bouquet de fleurs — il a besoin d'eau.
8.1–14.1  coup de zoom sur le radiateur : l'air chaud le dessèche, ses aiguilles tombent par poignées.
14.1–17.0 ① recoupe le pied de 2 cm (la scie, la rondelle qui tombe).
17.0–20.9 ② un pied avec réserve d'eau, remplis-le chaque jour (la carafe verse).
20.9–24.0 ③ loin de toute source de chaleur (l'autre vue du salon, coin au soleil).
24.0–fin  le sapin décoré ; bouton S'abonner et logo.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, IMG, put, paste, title, life, fade, ease_out,
                 ease_io, ease_in, ease_out_back, clamp, lerp, icon, tag, button_img, text_img, aa, F_TITLE,
                 F_BLACK, light_rays)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_citron import shade, swap
from scenes_fumier import Cam, decor
from scenes_rotation import beige
from scenes_pothos_lumiere import soft_shadow, sp, _src
from scenes_pigeons_choux import day_card

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=80)
SFX_GAIN = 0.27
DUCK = 0.45
TRANS_GAIN = 0.16
SHIFT = 0.25


def cue(t, name, gain=0.5):
    CUES.append((t - SHIFT, name, gain))


B = "banque/"
SALON_B, SALON_A = "decor_salon_soleil_table.webp", "decor_salon_soleil_canape.webp"
FILET, SAPIN, SEC, DECO = B + "sapin_1", B + "sapin_2", B + "sapin_3", B + "sapin_4"
PIED, SCIE, RONDELLE, CARAFE, RADIATEUR = (B + "pied_sapin", B + "scie", B + "rondelle_bois", B + "carafe_eau",
                                           B + "radiateur_panneau")

TREE_B = (520, 1050)            # pied du sapin à côté du radiateur (salon vue table, plein écran)
RAD_B = (765, 950)              # bas-milieu du radiateur, contre le mur
TREE_A = (630, 990)             # coin au soleil, loin de toute chaleur (salon vue canapé)
TREE_H = 600                    # hauteur du sapin à l'écran (zoom 1)


# ------------------------------------------------------------ sapins (même échelle pour les 4 étapes)
@lru_cache(None)
def _img(name):
    return Image.open(os.path.join(IMG, name + ".png")).convert("RGBA")


@lru_cache(None)
def _ref_h():
    """Hauteur de la silhouette du sapin dans son pied (sapin_2) : la référence d'échelle des 4 images."""
    bb = _img(SAPIN).getchannel("A").point(lambda v: 255 if v > 60 else 0).getbbox()
    return bb[3] - bb[1]


@lru_cache(None)
def _foot(name):
    a = np.asarray(_img(name))[..., 3] > 100
    ys, xs = np.nonzero(a)
    yb = ys.max()
    # le pied : milieu des pixels des 4 % du bas (sans les aiguilles éparpillées au sol)
    rows = xs[ys > yb - 0.04 * a.shape[0]]
    lo, hi = np.percentile(rows, 30), np.percentile(rows, 70)
    return float((lo + hi) / 2), float(yb)


@lru_cache(256)
def _sized(name, hpx):
    im = _img(name)
    k = hpx / _ref_h()
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS), k


def tree(c, name, x, y, h, s=1.0, rot=0.0, alpha=1.0):
    """Sapin (étape name), bas du pied en (x, y), h = hauteur du sapin en pied à l'écran."""
    if s <= 0.01 or alpha <= 0.01:
        return
    im, k = _sized(name, int(h * s))
    fx, fy = _foot(name)
    if abs(rot) > 0.05:
        im = im.rotate(rot, resample=Image.BICUBIC, center=(fx * k, fy * k))
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    paste(c, im, x - fx * k, y - fy * k)


def tree_swap(c, a, b, q, x, y, h, rot=0.0):
    k, s = swap(clamp(q))
    tree(c, a if k == 0 else b, x, y, h, s=s, rot=rot)


# ------------------------------------------------------------ aiguilles qui tombent et s'entassent au sol
def needles(c, t, t0, x, y, h, rate, seed=3, spread=0.5, z=1.0):
    """Aiguilles qui se détachent à `rate` par seconde à partir de t0, tombent en virevoltant et restent au sol."""
    if t < t0:
        return
    r = np.random.default_rng(seed)
    n = int(min(500, (t - t0) * rate))
    d = ImageDraw.Draw(c)
    for i in range(n):
        st = t0 + i / rate + r.uniform(0, 0.3)
        sx = x + r.uniform(-spread, spread) * h * 0.55 * (1 - r.uniform(0, 1) ** 2)
        sy = y - h * r.uniform(0.15, 0.9)
        gx = sx + r.uniform(-50, 50) * z
        gy = y + r.uniform(-14, 26) * z
        q = clamp((t - st) / r.uniform(0.7, 1.1))
        if t < st:
            continue
        px = lerp(sx, gx, q) + math.sin(q * 9 + i) * 10 * z * (1 - q)
        py = lerp(sy, gy, ease_in(q))
        ang = r.uniform(0, math.pi) + q * 6 * (1 - q)
        L = r.uniform(9, 15) * z
        col = (int(r.uniform(120, 160)), int(r.uniform(90, 115)), int(r.uniform(40, 60)), 255)
        d.line([(px - math.cos(ang) * L / 2, py - math.sin(ang) * L / 2),
                (px + math.cos(ang) * L / 2, py + math.sin(ang) * L / 2)], fill=col, width=max(2, int(2.5 * z)))


def heat(c, cam, t, a, rx, ry, w):
    """Air chaud qui monte du radiateur."""
    if a <= 0.01:
        return
    d = ImageDraw.Draw(c)
    X, Y = cam.p(rx, ry)
    for i in range(4):
        x0 = X + (i - 1.5) * w * 0.22 * cam.z
        ph = (t * 0.9 + i * 0.27) % 1
        pts = [(x0 + math.sin((Y - k * 14 * cam.z) / (30 * cam.z) + t * 5 + i) * 12 * cam.z,
                Y - 170 * cam.z - k * 14 * cam.z - ph * 50 * cam.z) for k in range(16)]
        d.line(pts, fill=(255, 170, 90, int(150 * a)), width=max(3, int(5 * cam.z)))


# ------------------------------------------------------------ coup de zoom flouté (transition)
def whip(im, q, amount=0.35):
    """Entrée en « coup de zoom » : l'image arrive grossie et floue (flou de mouvement radial), puis se pose."""
    s = 1 - ease_out(clamp(q))
    if s <= 0.01:
        return im
    acc = None
    for j in range(5):
        k = 1 + amount * s * (0.6 + 0.1 * j)
        cw, ch = W / k, H / k
        frame = im.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
        a = np.asarray(frame.convert("RGB"), np.float32)
        acc = a if acc is None else acc + a
    return Image.fromarray((acc / 5).astype(np.uint8)).convert("RGBA")


# ------------------------------------------------------------ repère des 3 gestes, en haut à gauche
@lru_cache(None)
def step_chip(n, active, done):
    S = 74

    def f(d, k, _):
        fill = YEL if active else (CREAM if not done else (255, 238, 170))
        d.ellipse([0, 0, (S - 1) * k, (S - 1) * k], fill=DARK)
        d.ellipse([5 * k, 5 * k, (S - 6) * k, (S - 6) * k], fill=fill)
    im = aa(S, S, f, 3)
    t_ = text_img(str(n), F_TITLE, 46, DARK)
    im.alpha_composite(t_, ((S - t_.width) // 2, (S - t_.height) // 2 + 2))
    return im


def steps(u, t, cur, t0=14.15):
    a = life(t, t0, None)
    if a <= 0.01:
        return
    for i in range(3):
        pop = 1 + 0.15 * math.sin(math.pi * clamp((t - (14.2, 17.05, 20.95)[i]) / 0.25)) if i + 1 == cur else 1
        put(u, step_chip(i + 1, i + 1 == cur, i + 1 < cur), 70 + i * 84, 640, a * pop * (1.12 if i + 1 == cur else 0.9))


def keyword(u, txt, t, t0, t1, color=YEL, size=130, y=330):
    title(u, txt, t, t0, t1, y=y, color=color, size=size)


# ============================================================ A. LE SALON : IL PERD SES AIGUILLES (0 → 4.25)
def salon_b(cam, t, stage_fn, needles_t0=None, rate=0, heat_a=0.0):
    w = decor(cam, SALON_B)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rx, ry = cam.p(*RAD_B)
    sp(lay, RADIATEUR, rx, ry, 215 * cam.z, 0.5, 1.0)
    x, y = cam.p(*TREE_B)
    soft_shadow(lay, x, y, 260 * cam.z, 90)
    if needles_t0 is not None:
        needles(lay, t, needles_t0, x, y, TREE_H * cam.z, rate, z=cam.z)
    stage_fn(lay, x, y, TREE_H * cam.z)
    w.alpha_composite(lay)
    heat(w, cam, t, heat_a, *RAD_B, 300)
    return w


def s_open(t):
    k = ease_io(clamp((t - 1.0) / 1.6))
    cam = Cam(lerp(1.0, 1.75, k), lerp(600, TREE_B[0] + 20, k), lerp(900, TREE_B[1] - 230, k))
    w = salon_b(cam, t, lambda c, x, y, h: tree(c, SAPIN, x, y, h, rot=math.sin(t * 0.8) * 0.4), 0.6, 45, 0.6)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    keyword(u, "AVANT NOËL ?", t, 0.3, 2.6, color=YEL, size=150)
    keyword(u, "MAUVAIS ENDROIT !", t, 3.1, None, color=RED, size=125)
    if t > 3.3:
        x, y = cam.p(*RAD_B)
        put(u, icon("arrow_down", 110), x + 10, y - 290 * cam.z + 10 * math.sin(t * 8), life(t, 3.35, None))
    return w, u


cue(0.0, "room", 0.1)              # ambiance de pièce, continue sous toute la vidéo
cue(0.6, "needles", 0.12)
cue(2.0, "needles", 0.1)
cue(3.15, "alert1", 0.14)


# ============================================================ B. COMME UN BOUQUET : IL A BESOIN D'EAU (4.25 → 8.1)
def s_bouquet(t):
    w = beige().copy()
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s = ease_out_back(clamp((t - 4.35) / 0.4), 1.3)
    soft_shadow(lay, 540, 1500, 380, 80)
    tree(lay, FILET, 540, 1500, 900, s=s)
    w.alpha_composite(lay)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t > 6.0:     # le bouquet : la carafe d'eau à côté (le sapin boit comme des fleurs coupées)
        s2 = ease_out_back(clamp((t - 6.05) / 0.35), 1.5)
        soft_shadow(w, 860, 1500, 200, 80)
        sp(w, CARAFE, 860, 1500, 420 * s2, 0.5, 1.0)
    if t > 7.05:
        for i in range(6):
            ph = ((t - 7.05) * 0.9 + i / 6) % 1
            put(u, icon("drop", 54), 540 + math.sin(i * 2.1) * 20, 1480 - ph * 520, math.sin(math.pi * ph))
    w = whip(w, (t - 4.25) / 0.3)
    keyword(u, "COMME UN BOUQUET", t, 5.6, 7.0, color=WHITE, size=110)
    keyword(u, "BESOIN D'EAU !", t, 7.05, None, color=BLUE, size=140)
    return w, u


cue(4.28, "whoosh", 0.08)
cue(4.4, "rustle", 0.12)
cue(6.08, "toc", 0.14)
cue(7.1, "plop", 0.14)
cue(7.5, "pour", 0.1)


# ============================================================ C. PRÈS DU RADIATEUR : IL SE DESSÈCHE (8.1 → 14.1)
def s_heat(t):
    k = ease_io(clamp((t - 8.1) / 0.5))
    cam = Cam(lerp(1.7, 1.55, k), 680, 830)
    dry = clamp((t - 10.45) / 1.0)
    w = salon_b(cam, t, lambda c, x, y, h: tree_swap(c, SAPIN, SEC, dry, x, y, h), 12.0, 160, 1.0)
    w = whip(w, (t - 8.1) / 0.3)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 8.6:
        x, y = cam.p(*RAD_B)
        put(u, icon("thermo", 140), x + 40, y - 380 * cam.z, life(t, 8.65, None))
    keyword(u, "À TOUTE VITESSE", t, 10.5, 11.9, color=RED, size=120)
    keyword(u, "PAR POIGNÉES !", t, 12.8, None, color=YEL, size=135)
    return w, u


cue(8.12, "whoosh_up", 0.1)
cue(8.7, "feu", 0.05)
cue(10.5, "crunch", 0.12)
cue(10.6, "fail", 0.12)
cue(12.1, "needles", 0.16)
cue(12.9, "needles", 0.16)
cue(13.3, "rustle", 0.1)


# ============================================================ D. ① RECOUPE LE PIED DE 2 CM (14.1 → 17.0)
CUT_Y = 1240                     # bas du tronc sur le gros plan


def s_cut(t):
    w = beige().copy()
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # gros plan : le bas du sapin emballé, le tronc nu dépasse ; le sapin est cadré très grand
    s_up = 0 if t < 16.05 else ease_out(clamp((t - 16.05) / 0.25)) * 24
    tree(lay, FILET, 540, CUT_Y - s_up, 2600)
    w.alpha_composite(lay)
    sx = 540 + 120 + math.sin((t - 15.0) * 2 * math.pi * 2.2) * 120 if 15.0 < t < 16.05 else 820
    a_saw = fade(t, 14.7, 16.3, 0.25, 0.25)
    if a_saw > 0.01:
        sp(w, SCIE, sx - 120, CUT_Y - 32, 150, 0.35, 0.86, rot=0, alpha=a_saw)
    if 15.1 < t < 16.1:      # sciure
        d = ImageDraw.Draw(w)
        r = np.random.default_rng(int(t * 30))
        for _ in range(14):
            px, py = 540 + r.uniform(-50, 50), CUT_Y - 25 + r.uniform(0, 140)
            d.ellipse([px - 4, py - 3, px + 4, py + 3], fill=(205, 165, 110, 230))
    if t > 16.05:            # la rondelle de 2 cm tombe et roule
        q = clamp((t - 16.05) / 0.5)
        sp(w, RONDELLE, 540 + 120 * q, lerp(CUT_Y - 10, 1420, ease_in(q)), 70, 0.5, 0.5, rot=-30 * q)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    steps(u, t, 1)
    if t > 15.6:
        d = ImageDraw.Draw(u)
        x0 = 430
        d.line([(x0, CUT_Y - 45), (x0, CUT_Y)], fill=WHITE, width=8)
        d.line([(x0 - 20, CUT_Y - 45), (x0 + 20, CUT_Y - 45)], fill=WHITE, width=8)
        d.line([(x0 - 20, CUT_Y), (x0 + 20, CUT_Y)], fill=WHITE, width=8)
        put(u, text_img("2 CM", F_TITLE, 90, YEL, 8, DARK), x0 - 150, CUT_Y - 25, life(t, 15.65, None))
    w = whip(w, (t - 14.1) / 0.3)
    keyword(u, "RECOUPE LE PIED", t, 14.2, None, color=WHITE, size=125)
    return w, u


cue(14.12, "whoosh", 0.08)
cue(14.25, "pop", 0.12)
cue(15.0, "saw", 0.3)
cue(16.08, "toc", 0.2)


# ============================================================ E. ② UN PIED AVEC RÉSERVE D'EAU (17.0 → 20.9)
BASE_Y = 1430


def s_stand(t):
    w = beige().copy()
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    soft_shadow(lay, 540, BASE_Y, 460, 90)
    if t < 17.95:
        s = ease_out_back(clamp((t - 17.1) / 0.35), 1.4)
        sp(lay, PIED, 540, BASE_Y, 480 * s, 0.5, 1.0)
    else:
        q = ease_out(clamp((t - 17.95) / 0.45))
        tree(lay, SAPIN, 540, lerp(BASE_Y - 700, BASE_Y, q), 1050, alpha=clamp(q * 3))
    w.alpha_composite(lay)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # la carafe remplit la réserve, chaque jour
    if t > 19.5:
        tilt = 62 * ease_io(clamp((t - 19.5) / 0.3))
        mx, my = 700, BASE_Y - 300          # le goulot, au-dessus du bord du pied
        sp(w, CARAFE, mx, my, 330, 0.5, 0.03, rot=tilt)
        if t > 19.75:
            d = ImageDraw.Draw(w)
            pts = [(mx - 8 - 40 * (k / 10) ** 2 * 1.5, my + 12 + k * 13) for k in range(11)]
            d.line(pts, fill=(160, 205, 240, 210), width=11, joint="curve")
            d.line([(p[0] - 3, p[1]) for p in pts], fill=(235, 248, 255, 200), width=3)
        for i, t0 in enumerate((19.75, 20.05, 20.35)):
            s = life(t, t0, None if i == 2 else t0 + 0.3, dur=0.1, out=0.08)
            if s > 0.01:
                put(u, day_card(i + 1, 210), 880, 790, s, rot=-4 + i * 4)
    steps(u, t, 2)
    w = whip(w, (t - 17.0) / 0.3)
    keyword(u, "RÉSERVE D'EAU", t, 18.4, 19.6, color=BLUE, size=130)
    keyword(u, "CHAQUE JOUR !", t, 19.65, None, color=YEL, size=140)
    return w, u


cue(17.02, "whoosh", 0.08)
cue(17.12, "pop_lo", 0.14)
cue(18.35, "thud", 0.14)
cue(19.75, "pour", 0.2)
for _t in (19.75, 20.05, 20.35):
    cue(_t, "tick", 0.12)


# ============================================================ F. ③ LOIN DE TOUTE SOURCE DE CHALEUR (20.9 → 24.0)
def s_far(t):
    cam = Cam(lerp(1.05, 1.13, clamp((t - 20.9) / 3.1)), 640, 900)
    w = decor(cam, SALON_A)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x, y = cam.p(*TREE_A)
    soft_shadow(lay, x, y, 270 * cam.z, 90)
    s = ease_out_back(clamp((t - 21.3) / 0.45), 1.3)
    tree(lay, SAPIN, x, y, TREE_H * 1.05 * cam.z, s=s)
    w.alpha_composite(lay)
    w = whip(w, (t - 20.9) / 0.3)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    steps(u, t, 3)
    if t > 22.5:
        put(u, icon("thermo", 120), 170, 800, life(t, 22.55, None))
        put(u, icon("nosign", 180), 170, 800, ease_out_back(clamp((t - 22.6) / 0.3), 1.6))
        put(u, icon("check", 130), x + 230 * cam.z, y - 560 * cam.z, ease_out_back(clamp((t - 22.8) / 0.3), 1.6))
    keyword(u, "LOIN DE LA CHALEUR", t, 22.4, None, color=GREEN, size=110)
    return w, u


cue(20.92, "whoosh", 0.08)
cue(21.35, "thud", 0.12)
cue(22.62, "ding", 0.15)


# ============================================================ G. ABONNE-TOI (24.0 → fin)
def lights(c, t, x, y, h, z):
    """Les guirlandes qui scintillent sur le sapin décoré."""
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(12)
    for i in range(46):
        v = r.uniform(0.08, 0.9)
        px = x + r.uniform(-1, 1) * h * 0.4 * v
        py = y - h * (1 - v) - h * 0.08
        a = 0.5 + 0.5 * math.sin(t * r.uniform(3, 6) + i)
        rr = 5 * z * (0.6 + 0.6 * a)
        d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=(255, 226, 150, int(220 * a)))


def s_end(t):
    cam = Cam(1.13, 640, 900)
    w = decor(cam, SALON_A)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x, y = cam.p(*TREE_A)
    soft_shadow(lay, x, y, 270 * cam.z, 90)
    tree_swap(lay, SAPIN, DECO, clamp((t - 24.05) / 0.5), x, y, TREE_H * 1.05 * cam.z)
    w.alpha_composite(lay)
    if t > 24.4:
        lights(w, t, x, y, TREE_H * 1.05 * cam.z, cam.z)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    clicked = t > 25.85
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 25.8) / 0.15))
    put(u, btn, 540, 1400, life(t, 24.6) * press)
    if t > 25.3:
        kk = ease_out((t - 25.3) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 26.5, dur=0.45))
    sparkles(u, t, 26.6, 540, 330, 200, 10, 12)
    sparkles(u, t, 24.2, x, y - 320 * cam.z, 300, 10, 4, 1.0)
    title(u, "PLUS D'ASTUCES ?", t, 24.3, 26.45, y=330, color=YEL, size=135)
    return w, u


cue(24.1, "sparkle", 0.14)
cue(24.65, "pop_lo", 0.14)
cue(25.83, "click", 0.28)
cue(26.6, "sparkle", 0.14)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 4.25 - SHIFT, _sh(s_open)),
    (4.25 - SHIFT, 8.1 - SHIFT, _sh(s_bouquet)),
    (8.1 - SHIFT, 14.1 - SHIFT, _sh(s_heat)),
    (14.1 - SHIFT, 17.0 - SHIFT, _sh(s_cut)),
    (17.0 - SHIFT, 20.9 - SHIFT, _sh(s_stand)),
    (20.9 - SHIFT, 24.0 - SHIFT, _sh(s_far)),
    (24.0 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
