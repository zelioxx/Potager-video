"""Storyboard « La nouvelle plante qui meurt en 2 semaines » (voix : assets/audio/maranta/voix.wav, volume d'origine).

Décors fournis : la jardinerie (table de plantes vertes), un salon jamais utilisé (bibliothèque, radiateurs,
table devant la fenêtre). Images fournies (agrandies ×2, détourées) : un maranta en 4 étapes (en forme → mourant),
un pot en terre cuite, un calendrier (traduit en français), un radiateur, un petit arrosoir inox.
0–3.65    le salon : la plante achetée dépérit en deux semaines… ce n'est pas ta faute !
3.65–9.05 la jardinerie : elle vivait dans une serre — lumière, chaleur, humidité.
9.05–12.8 chez toi : plus sombre, air sec à cause du chauffage (le radiateur souffle de l'air chaud).
12.8–15.5 le choc : elle perd ses feuilles.
15.5–19.2 près d'une fenêtre lumineuse, loin du radiateur.
19.2–23.0 (fond beige) ne la rempote pas tout de suite ; attends 2 ou 3 semaines (calendrier).
23.0–25.85 elle s'habitue… et elle repart.
25.85–fin bouton S'abonner et logo.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, IMG, put, paste, title, life, fade, ease_out,
                 ease_io, ease_in, ease_out_back, clamp, lerp, icon, tag, button_img, text_img, pills, F_TITLE,
                 F_BLACK, light_rays)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade, swap
from scenes_fumier import Cam, decor
from scenes_rotation import beige
from scenes_pothos_lumiere import soft_shadow, sp, _src
from scenes_pigeons_choux import day_card

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
SALON, JARD = "decor_salon_table_fenetre2.jpg", "decor_jardinerie_plantes.webp"
MAR = [B + f"maranta_{k}" for k in range(1, 5)]       # en forme → mourant
POT_TC, CAL, CAN = B + "pot_terre_cuite", B + "calendrier_fr", B + "arrosoir_inox"

FLOOR = (400, 1250)             # au pied du radiateur (salon plein écran)
TABLE = (765, 1012)             # sur la table devant la fenêtre
RADIATORS = [(345, 860)]             # haut du radiateur derrière la bibliothèque
JARD_SPOT = (850, 1255)         # sur la table de la jardinerie, à côté des autres marantas
FRAME_W = 380                   # largeur du quart de planche à l'écran (zoom 1)


# ------------------------------------------------------------ le maranta : pied du pot dans chaque étape
@lru_cache(None)
def _img(name):
    return Image.open(os.path.join(IMG, name + ".png")).convert("RGBA")


@lru_cache(None)
def pot_foot(name):
    """Bas et milieu du pot noir (pas la feuille tombée) dans le cadre de l'image."""
    a = np.asarray(_img(name)).astype(np.float32)
    rgb = a[..., :3]
    dark = (rgb.max(2) < 70) & (a[..., 3] > 200)
    ys, xs = np.nonzero(dark)
    yb = np.percentile(ys, 99.5)
    row = xs[ys > yb - 40]
    return float(np.median(row)), float(yb)


@lru_cache(256)
def _sized(name, w):
    im = _img(name)
    k = w / im.width
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS), k


def maranta(c, stage, x, y, w, s=1.0, rot=0.0, alpha=1.0):
    """Étape 1–4 du maranta, bas du pot en (x, y) ; w = largeur du cadre à l'écran."""
    if s <= 0.01 or alpha <= 0.01:
        return
    name = MAR[stage - 1]
    im, k = _sized(name, int(w * s))
    fx, fy = pot_foot(name)
    if abs(rot) > 0.05:
        im = im.rotate(rot, resample=Image.BICUBIC, center=(fx * k, fy * k))
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    paste(c, im, x - fx * k, y - fy * k)


def maranta_q(c, q, x, y, w, rot=0.0):
    """q ∈ [1, 4] : passe d'une étape à la suivante sans superposition (on tasse, on change, on rebondit)."""
    q = clamp(q, 1, 4)
    i = int(min(3, math.floor(q)))
    if q >= 4:
        maranta(c, 4, x, y, w, rot=rot)
        return
    k, s = swap(q - i)
    maranta(c, i + k, x, y, w, s=s, rot=rot)


def maranta_back(c, q, x, y, w):
    """Remonte de l'étape 3 à l'étape 1 (elle repart)."""
    q = clamp(q, 0, 2)
    i = int(min(1, math.floor(q)))
    if q >= 2:
        maranta(c, 1, x, y, w)
        return
    k, s = swap(q - i)
    maranta(c, 3 - i - k, x, y, w, s=s)


def plant_at(c, cam, stage_fn, spot, w=FRAME_W):
    x, y = cam.p(*spot)
    soft_shadow(c, x, y, w * cam.z * 0.42, 90)
    stage_fn(c, x, y, w * cam.z)


# ------------------------------------------------------------ ambiances
def dim(im, k):
    """Pièce plus sombre, un peu jaunie (lumière d'hiver à l'intérieur)."""
    if k <= 0.01:
        return im
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    d = a * np.array([0.98, 0.9, 0.8], np.float32) * 0.55
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.4 * np.clip(((xx - W / 2) / (W * 0.8)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2, 0, 1)
    d *= vig[..., None]
    out = a * (1 - k) + d * k
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert("RGBA")


def bright(im, k):
    if k <= 0.01:
        return im
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    b = np.clip(a * 1.12 + 0.03, 0, 1)
    return Image.fromarray((np.clip(a * (1 - k) + b * k, 0, 1) * 255).astype(np.uint8)).convert("RGBA")


def heat(c, cam, t, a, xs=None):
    """Air chaud qui monte des radiateurs (ondulations orangées)."""
    if a <= 0.01:
        return
    d = ImageDraw.Draw(c)
    for rx, ry in (xs or RADIATORS):
        X, Y = cam.p(rx, ry)
        for i in range(4):
            x0 = X + (i - 1.5) * 26 * cam.z
            ph = (t * 0.9 + i * 0.27) % 1
            pts = []
            for k in range(16):
                yy = Y - k * 13 * cam.z - ph * 50 * cam.z
                pts.append((x0 + math.sin(yy / (30 * cam.z) + t * 5 + i) * 12 * cam.z, yy))
            d.line(pts, fill=(255, 170, 90, int(150 * a)), width=max(3, int(5 * cam.z)))


def mist(c, t, x, y, a, n=26, seed=3):
    """Brume d'humidité (serre) : petites gouttelettes qui flottent."""
    if a <= 0.01:
        return
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(seed)
    for _ in range(n):
        ph = (t * 0.35 + r.uniform(0, 1)) % 1
        px = x + r.uniform(-360, 360) + math.sin(t * 1.5 + ph * 6) * 20
        py = y - ph * 520 + r.uniform(-60, 60)
        rr = r.uniform(4, 9)
        al = int(160 * a * math.sin(math.pi * ph))
        d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=(220, 240, 255, al))


def leaves_fall(c, t, t0, x, y, w, n=6, seed=2):
    if t < t0:
        return
    r = np.random.default_rng(seed)
    d = ImageDraw.Draw(c)
    for i in range(n):
        st = t0 + r.uniform(0, 0.9)
        q = (t - st) / 1.1
        if not 0 < q < 1:
            continue
        px = x + r.uniform(-0.4, 0.4) * w + math.sin(q * 6 + i) * 30
        py = y - w * r.uniform(0.6, 0.9) + q * w * 0.75
        s = r.uniform(22, 34) * w / 500
        ang = q * 4 + i
        col = (int(r.uniform(150, 190)), int(r.uniform(120, 150)), int(r.uniform(40, 70)), int(255 * (1 - q ** 3)))
        d.polygon([(px + math.cos(ang + k * 1.57) * s * (1 if k % 2 == 0 else 0.45),
                    py + math.sin(ang + k * 1.57) * s * (1 if k % 2 == 0 else 0.45)) for k in range(4)], fill=col)


# ============================================================ A. TA NOUVELLE PLANTE MEURT EN 2 SEMAINES ? (0 → 3.65)
def s_intro(t):
    cam = Cam(lerp(1.15, 1.32, ease_io(clamp(t / 3.6))), FLOOR[0] + 80, FLOOR[1] - 300)
    w = decor(cam, SALON)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    q = 1 + ease_io(clamp((t - 0.9) / 1.4)) * 2.3
    plant_at(lay, cam, lambda c, x, y, ww: maranta_q(c, q, x, y, ww), FLOOR)
    w.alpha_composite(lay)
    w = dim(w, 0.35)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    act = 0 if t < 1.6 else 1
    pills(u, ["1 SEMAINE", "2 SEMAINES"], act, t, 1.0, 2.5, y=560, pw=330)
    title(u, "TA NOUVELLE PLANTE", t, 0.05, 2.5, y=300, color=WHITE, size=120)
    title(u, "MEURT EN 2 SEMAINES ?", t, 0.05, 2.5, y=430, color=YEL, size=105)
    stamp(u, "CE N'EST PAS TA FAUTE !", 540, 340, t, 2.58, None, GREEN, 95, -6)
    return w, u


cue(0.08, "pop_lo", 0.14)
cue(1.05, "pop", 0.12)
cue(1.6, "tick", 0.16)
cue(1.8, "fail", 0.12)
cue(2.6, "thud", 0.2)
cue(2.65, "success", 0.12)


# ============================================================ B. LA JARDINERIE : UNE SERRE (3.65 → 9.05)
def s_shop(t):
    k = ease_io(clamp((t - 3.65) / 2.2))
    cam = Cam(lerp(1.0, 1.45, k), lerp(540, JARD_SPOT[0] - 60, k), lerp(980, JARD_SPOT[1] - 280, k))
    w = decor(cam, JARD)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    plant_at(lay, cam, lambda c, x, y, ww: maranta(c, 1, x, y, ww, rot=math.sin(t * 1.3) * 0.8), JARD_SPOT, 300)
    w.alpha_composite(lay)
    w = bright(w, 0.6)
    light_rays(w, 860, 0, t, 0.9)
    mist(w, t, 600, 1300, fade(t, 8.2, None, 0.4))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    for t0, ic, lbl, x, y, rot in ((6.62, "sun", "LUMIÈRE", 200, 700, -5), (7.48, "thermo", "CHALEUR", 860, 820, 5),
                                   (8.25, "drop", "HUMIDITÉ", 230, 1000, -4)):
        s = ease_out_back(clamp((t - t0) / 0.3), 1.6)
        if s > 0.01:
            put(u, icon(ic, 130), x, y - 95, s)
            tag(u, lbl, x, y + 20, t, t0 + 0.05, None, rot=rot, size=50)
    title(u, "EN JARDINERIE…", t, 3.7, 4.8, y=330, color=WHITE, size=150)
    title(u, "ELLE VIVAIT DANS UNE SERRE", t, 4.82, 6.6, y=330, color=YEL, size=92)
    title(u, "LE PARADIS DES PLANTES !", t, 6.62, None, y=330, color=GREEN, size=100)
    return w, u


cue(3.7, "whoosh", 0.12)
cue(4.85, "sparkle", 0.12)
for _t in (6.62, 7.48, 8.25):
    cue(_t, "pop", 0.15)
cue(8.3, "plop", 0.12)


# ============================================================ C. CHEZ TOI : PLUS SOMBRE, AIR SEC (9.05 → 12.8)
def s_home(t):
    cam = Cam(lerp(1.05, 1.15, clamp((t - 9.05) / 3.7)), 360, 1050)
    w = decor(cam, SALON)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    plant_at(lay, cam, lambda c, x, y, ww: maranta(c, 1, x, y, ww), FLOOR)
    w.alpha_composite(lay)
    w = dim(w, ease_io(clamp((t - 9.9) / 0.8)) * 0.85)
    heat(w, cam, t, fade(t, 11.2, None, 0.4))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 10.4:
        tag(u, "PLUS SOMBRE", 760, 760, t, 10.45, None, rot=5, size=56)
    if t > 11.3:
        tag(u, "AIR SEC", 760, 900, t, 11.35, None, rot=-4, size=56)
        put(u, icon("thermo", 120), 600, 900, life(t, 11.4, None))
    title(u, "MAIS CHEZ TOI…", t, 9.1, 10.4, y=330, color=WHITE, size=150)
    title(u, "LE CHAUFFAGE ASSÈCHE L'AIR", t, 11.95, None, y=330, color=RED, size=92)
    title(u, "IL FAIT PLUS SOMBRE", t, 10.42, 11.93, y=330, color=YEL, size=115)
    return w, u


cue(9.12, "whoosh", 0.12)
cue(10.45, "pop", 0.13)
cue(11.35, "pop_hi", 0.13)
cue(11.6, "feu", 0.07)


# ============================================================ D. ELLE PREND UN CHOC (12.8 → 15.5)
def s_shock(t):
    cam = Cam(lerp(1.5, 1.6, clamp((t - 12.8) / 2.7)), FLOOR[0] + 40, FLOOR[1] - 260)
    w = decor(cam, SALON)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shake = math.sin(t * 60) * 10 * clamp((t - 13.62) / 0.05) * (1 - clamp((t - 13.7) / 0.4))
    q = 1 + ease_io(clamp((t - 14.4) / 0.95)) * 3
    x, y = cam.p(*FLOOR)
    soft_shadow(lay, x, y, FRAME_W * cam.z * 0.42, 90)
    maranta_q(lay, q, x + shake, y, FRAME_W * cam.z, rot=shake * 0.3)
    leaves_fall(lay, t, 14.5, x, y, FRAME_W * cam.z, 7, 4)
    w.alpha_composite(lay)
    w = dim(w, 0.85)
    heat(w, cam, t, 0.7)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    title(u, "ALORS…", t, 12.85, 13.62, y=330, color=WHITE, size=170)
    stamp(u, "CHOC !", 540, 340, t, 13.65, 14.45, RED, 190, -8)
    title(u, "ELLE PERD SES FEUILLES", t, 14.47, None, y=330, color=RED, size=105)
    return w, u


cue(12.86, "whoosh", 0.1)
cue(13.66, "thud", 0.24)
cue(13.7, "fail", 0.16)
cue(14.5, "rustle", 0.16)


# ============================================================ E. PRÈS D'UNE FENÊTRE, LOIN DU RADIATEUR (15.5 → 19.2)
def s_window(t):
    cam = Cam(lerp(1.05, 1.12, clamp((t - 15.5) / 3.7)), 560, 1060)
    w = decor(cam, SALON)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m = ease_io(clamp((t - 16.0) / 1.1))
    gx, gy = lerp(FLOOR[0], TABLE[0], m), lerp(FLOOR[1], TABLE[1], m) - math.sin(math.pi * m) * 160
    plant_at(lay, cam, lambda c, x, y, ww: maranta(c, 3, x, y, ww, rot=math.sin(math.pi * m) * 6), (gx, gy))
    w.alpha_composite(lay)
    w = dim(w, 0.85 * (1 - ease_io(clamp((t - 16.6) / 0.8))))
    w = bright(w, ease_io(clamp((t - 16.8) / 0.8)) * 0.6)
    light_rays(w, 860, 300, t, fade(t, 16.9, None, 0.5) * 0.9)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 17.3:
        x, y = cam.p(*TABLE)
        put(u, icon("check", 140), x + 170, y - 380, ease_out_back(clamp((t - 17.35) / 0.3), 1.6))
    if t > 18.05:
        for rx, ry in RADIATORS[:1]:
            x, y = cam.p(rx, ry)
            put(u, icon("cross", 150), x, y + 140 * cam.z, ease_out_back(clamp((t - 18.1) / 0.3), 1.6))
    title(u, "PRÈS D'UNE FENÊTRE", t, 15.55, 18.0, y=300, color=WHITE, size=120)
    title(u, "LUMINEUSE !", t, 15.55, 18.0, y=430, color=YEL, size=140)
    title(u, "LOIN DU RADIATEUR !", t, 18.02, None, y=330, color=RED, size=115)
    return w, u


cue(15.55, "whoosh", 0.12)
cue(16.0, "whoosh_up", 0.12)
cue(17.1, "thud", 0.12)
cue(17.35, "ding", 0.15)
cue(18.12, "alert2", 0.14)


# ============================================================ F. NE LA REMPOTE PAS ; ATTENDS 2 OU 3 SEMAINES (19.2 → 23.0)
CAL_DAYS = 21                    # on raye trois semaines


def s_repot(t):
    w = beige().copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    part1 = t < 21.55
    if part1:
        s = ease_out_back(clamp((t - 19.3) / 0.4), 1.4)
        soft_shadow(lay, 330, 1450, 260, 90)
        maranta(lay, 3, 330, 1450, 560, s=s)
        s2 = ease_out_back(clamp((t - 19.9) / 0.4), 1.4)
        if s2 > 0.01:
            soft_shadow(lay, 790, 1450, 300, 90)
            sp(lay, POT_TC, 790, 1450, 330 * s2, 0.5, 1.0)
        if t > 20.35:
            put(u, icon("nosign", 300), 790, 1290, ease_out_back(clamp((t - 20.4) / 0.3), 1.6))
    else:
        s = ease_out_back(clamp((t - 21.6) / 0.4), 1.3)
        im = calendar_img()
        put(lay, im, 540, 1030, s * 0.95, rot=-2)
        if s > 0.5:
            cells = calendar_cells()
            n = int(clamp((t - 21.95) / 0.85) * CAL_DAYS)
            d = ImageDraw.Draw(lay)
            k = s * 0.95
            cx0, cy0 = 540 - im.width * k / 2, 1030 - im.height * k / 2
            for i in range(n):
                x, y = cells[i]
                x, y = cx0 + x * k, cy0 + y * k
                r = 26 * k
                d.line([(x - r, y - r), (x + r, y + r)], fill=(214, 60, 50, 255), width=int(9 * k))
                d.line([(x - r, y + r), (x + r, y - r)], fill=(214, 60, 50, 255), width=int(9 * k))
        if t > 22.4:
            tag(u, "2 À 3 SEMAINES", 540, 1640, t, 22.45, None, rot=-4, size=64)
    w.alpha_composite(lay)
    title(u, "ET SURTOUT…", t, 19.3, 20.3, y=300, color=WHITE, size=150)
    title(u, "NE LA REMPOTE PAS", t, 20.32, 21.55, y=300, color=RED, size=120)
    title(u, "TOUT DE SUITE !", t, 20.32, 21.55, y=430, color=RED, size=120)
    title(u, "ATTENDS 2 OU 3 SEMAINES", t, 21.58, None, y=330, color=WHITE, size=100)
    return w, u


cue(19.32, "whoosh", 0.12)
cue(19.92, "pop_lo", 0.14)
cue(20.42, "alert1", 0.15)
cue(21.6, "whoosh", 0.1)
for _i in range(0, CAL_DAYS, 3):
    cue(21.95 + 0.85 * _i / CAL_DAYS, "tick", 0.12)


# ------------------------------------------------------------ le calendrier traduit en français
CAL_GEOM = {}                   # rempli par calendar_img : positions des cases (cadre de l'image)


@lru_cache(None)
def calendar_img():
    """Le calendrier de la planche (AVRIL, en français), à 760 px de large."""
    im = _src(CAL)
    k = 760 / im.width
    im = im.resize((760, int(im.height * k)), Image.LANCZOS)
    return im


@lru_cache(None)
def calendar_cells():
    """Centres des 30 cases (repérées sur l'image : grille 7 colonnes, mois commençant le mardi)."""
    im = calendar_img()
    a = np.asarray(im.convert("L")).astype(np.float32)
    # lignes de la grille : rangées et colonnes sombres fines
    al = np.asarray(im.getchannel("A")) > 128
    dark = (a < 175) & al
    cols = dark.mean(0)
    rows = dark.mean(1)
    gx0, gx1 = CAL_BOX[0] * im.width, CAL_BOX[2] * im.width
    gy0, gy1 = CAL_BOX[1] * im.height, CAL_BOX[3] * im.height
    cw, ch = (gx1 - gx0) / 7, (gy1 - gy0) / 5
    out = []
    for dday in range(30):
        i = dday + 1                       # le 1er est un mardi (colonne 1)
        col, row = i % 7, i // 7
        out.append((gx0 + (col + 0.5) * cw, gy0 + (row + 0.5) * ch))
    return out


CAL_BOX = (0.0798, 0.3198, 0.9188, 0.8426)       # zone des 35 cases (fractions de calendrier_fr)


# ============================================================ G. ELLE S'HABITUE… ET ELLE REPART (23.0 → 25.85)
def s_back(t):
    cam = Cam(lerp(1.25, 1.35, clamp((t - 23.0) / 2.85)), TABLE[0] - 40, TABLE[1] - 300)
    w = decor(cam, SALON)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    q = ease_io(clamp((t - 23.7) / 1.6)) * 2
    plant_at(lay, cam, lambda c, x, y, ww: maranta_back(c, q, x, y, ww), TABLE)
    w.alpha_composite(lay)
    w = bright(w, 0.5)
    light_rays(w, 900, 250, t, 0.9)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    x, y = cam.p(*TABLE)
    if t > 25.0:
        sparkles(u, t, 25.05, x, y - 260 * cam.z, 300, 12, 8, 1.0)
        put(u, icon("check", 150), x + 220, y - 520 * cam.z, ease_out_back(clamp((t - 25.1) / 0.3), 1.6))
    for i, t0 in enumerate((23.1, 23.45)):
        s = life(t, t0, 24.9, dur=0.12, out=0.08)
        if s > 0.01:
            put(u, day_card(7 * (i + 2), 230), 880, 640, s, rot=-4 + i * 6)
    title(u, "LE TEMPS QU'ELLE S'HABITUE…", t, 23.05, 25.0, y=330, color=WHITE, size=92)
    stamp(u, "ET ELLE REPART !", 540, 340, t, 25.05, None, GREEN, 120, -6)
    return w, u


cue(23.06, "whoosh", 0.1)
cue(23.12, "tick", 0.14)
cue(23.47, "tick", 0.14)
cue(24.2, "rise", 0.14)
cue(25.07, "success", 0.16)


# ============================================================ H. ABONNE-TOI (25.85 → fin)
def s_end(t):
    cam = Cam(1.12, 600, 1060)
    w = decor(cam, SALON)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    plant_at(lay, cam, lambda c, x, y, ww: maranta(c, 1, x, y, ww, rot=math.sin(t * 1.2) * 0.6), TABLE)
    w.alpha_composite(lay)
    w = bright(w, 0.5)
    light_rays(w, 900, 250, t, 0.8)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    clicked = t > 27.45
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 27.4) / 0.15))
    put(u, btn, 540, 1400, life(t, 26.0) * press)
    if t > 26.9:
        kk = ease_out((t - 26.9) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 28.25, dur=0.45))
    sparkles(u, t, 28.35, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 25.9, 28.2, y=330, color=YEL, size=135)
    return w, u


cue(25.95, "pop_lo", 0.18)
cue(27.43, "click", 0.3)
cue(28.35, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 3.65 - SHIFT, _sh(s_intro)),
    (3.65 - SHIFT, 9.05 - SHIFT, _sh(s_shop)),
    (9.05 - SHIFT, 12.8 - SHIFT, _sh(s_home)),
    (12.8 - SHIFT, 15.5 - SHIFT, _sh(s_shock)),
    (15.5 - SHIFT, 19.2 - SHIFT, _sh(s_window)),
    (19.2 - SHIFT, 21.55 - SHIFT, _sh(s_repot)),
    (21.55 - SHIFT, 23.0 - SHIFT, _sh(s_repot)),
    (23.0 - SHIFT, 25.85 - SHIFT, _sh(s_back)),
    (25.85 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
