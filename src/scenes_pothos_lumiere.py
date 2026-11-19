"""Storyboard « Plante d'intérieur qui jaunit en hiver : c'est la lumière » (voix : assets/audio/pothos/voix.wav).

Décors fournis : le salon (meuble en chêne et sa lampe, comme pour l'orchidée), le rebord de fenêtre.
Objets (planches fournies, agrandies ×4 puis détourées) : pothos en pot (sain, qui jaunit), pots en coupe
(racines saines / racines pourries dans l'eau qui stagne), feuilles (verte, jaune, noire), mains qui pointent.
Jeu de lumière : la journée passe au soir dans le salon (la pièce s'assombrit, la lampe prend le relais).
0–4.45    le pothos sur le meuble jaunit d'un coup. Ce n'est pas l'eau (barrée)… c'est la lumière !
4.45–8.85 en hiver, les jours raccourcissent : le soleil se couche vite, la pièce s'assombrit, jauge de lumière.
8.85–11.1 dans la pénombre : elle pousse moins, elle boit moins.
11.1–13.4 mais toi (la main te montre du doigt), tu continues d'arroser pareil.
13.4–16.8 en coupe : l'eau stagne au fond du pot, les racines pourrissent ; la feuille verte → jaune → noire.
16.8–20.25 rapproche-la de la fenêtre… mais pas contre la vitre (givre sur les feuilles) : on la recule.
20.25–24.35 espace les arrosages (semaine) ; le doigt dans la terre : sèche sur 2 cm.
24.35–fin la fenêtre au coucher du soleil, le pothos en pleine forme ; bouton S'abonner et logo.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, IMG, put, paste, title, life, fade, ease_out,
                 ease_io, ease_in, ease_out_back, clamp, lerp, icon, tag, button_img, text_img, aa, F_TITLE, F_BLACK,
                 light_rays)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade, swap
from scenes_fumier import Cam, decor
from scenes_arrosage_soir import watering

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
SALON, FENETRE = "decor_salon_meuble_lampe.jpg", "decor_rebord_fenetre_radiateur.jpg"
POT, POT_J = B + "pothos_pot_sain", B + "pothos_pot_jaune"
COUPE, COUPE_P = B + "pothos_coupe_saine", B + "pothos_coupe_pourrie"
F_VERTE, F_JAUNE, F_NOIRE = B + "feuille_pothos_verte", B + "feuille_pothos_jaune", B + "feuille_pothos_noire"
MAIN_FACE, MAIN_BAS = B + "main_pointe_face", B + "main_pointe_bas"
CAN = B + "arrosoir_zinc"

POT_AT = (600, 1400)            # bas du pot, sur le meuble (salon plein écran)
POT_H = 760                     # hauteur du pothos en pot (zoom 1)
LAMP = (300, 330)               # abat-jour (salon plein écran)
SOIL_Y = 0.56                   # dessus de la terre, en fraction de la hauteur de l'image du pot (depuis le haut)
SILL_BACK, SILL_FRONT = (560, 1190), (600, 1345)       # pot contre la vitre / pot reculé (fenêtre plein écran)


# ------------------------------------------------------------ sprites (cache par taille)
@lru_cache(None)
def _src(name):
    im = Image.open(os.path.join(IMG, name + ".png")).convert("RGBA")
    return im.crop(im.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox())


@lru_cache(1024)
def _sized(name, h, flip):
    im = _src(name)
    w = max(1, round(im.width * h / im.height))
    im = im.resize((w, max(1, h)), Image.LANCZOS)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


def sp(c, name, x, y, h, ax=0.5, ay=1.0, rot=0.0, flip=False, alpha=1.0):
    """Objet de hauteur h, point d'ancrage (ax, ay) de sa boîte posé en (x, y), rotation autour de ce point."""
    if h < 2 or alpha <= 0.01:
        return
    im = _sized(name, int(round(h)), flip)
    axp, ayp = (1 - ax if flip else ax) * im.width, ay * im.height
    if abs(rot) > 0.05:
        r = int(math.hypot(max(axp, im.width - axp), max(ayp, im.height - ayp))) + 2
        big = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0))
        big.paste(im, (int(r - axp), int(r - ayp)))
        im, axp, ayp = big.rotate(rot, resample=Image.BICUBIC), r, r
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    paste(c, im, x - axp, y - ayp)


def soft_shadow(c, x, y, w, a=90, flat=0.12):
    pad = int(w * 0.3) + 8
    im = Image.new("RGBA", (int(w + 2 * pad), int(w * flat * 2 + 2 * pad)), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([pad, pad, pad + w, pad + w * flat * 2], fill=(30, 20, 12, a))
    im = im.filter(ImageFilter.GaussianBlur(max(2, w * 0.05)))
    paste(c, im, x - im.width / 2, y - im.height / 2)


def pothos(c, x, y, h, q_yellow=0.0, flip=False, sway=0.0):
    """Le pothos en pot, bas du pot en (x, y). q_yellow : passe du pot sain au pot qui jaunit
    (on tasse, on change d'image au plus petit, on rebondit : jamais deux images superposées)."""
    soft_shadow(c, x, y - h * 0.01, h * 0.55, 100)
    k, s_ = swap(q_yellow)
    sp(c, POT if k == 0 else POT_J, x, y, h * s_, 0.5, 1.0, rot=sway, flip=flip)


# ------------------------------------------------------------ lumière : la journée passe au soir
def light(im, cam, ev, lamp=1.0):
    """ev = 0 : plein jour (pièce claire, lumière froide de l'hiver) ; ev = 1 : soirée (sombre, chaud,
    vignette), la lampe éclaire autour d'elle."""
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    lum = a.mean(2, keepdims=True)
    day = np.clip((a * 0.75 + lum * 0.25) * 1.3 + 0.06, 0, 1) * np.array([0.97, 1.0, 1.07], np.float32)
    eve = a * np.array([1.0, 0.84, 0.66], np.float32) * 0.36
    out = day * (1 - ev) + eve * ev
    if ev > 0.01:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        lx, ly = cam.p(*LAMP)
        r = 700 * cam.z
        glow = np.exp(-((xx - lx) ** 2 + (yy - ly) ** 2) / (2 * r * r))
        out += a * glow[..., None] * np.array([0.95, 0.72, 0.42], np.float32) * ev * lamp
        vig = 1 - 0.45 * ev * np.clip(((xx - W / 2) ** 2 / (W * 0.75) ** 2 + (yy - H / 2) ** 2 / (H * 0.7) ** 2), 0, 1)
        out *= vig[..., None]
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert("RGBA")


def sunset(im, k):
    """Fenêtre au coucher du soleil : lumière orangée qui descend, pièce un peu plus sombre."""
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    tint = a * np.array([1.08, 0.88, 0.7], np.float32) * 0.82
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    glow = np.exp(-((yy - 0.3) ** 2) / 0.05) * np.array([0.22, 0.1, 0.0], np.float32)
    out = a * (1 - k) + (tint + glow * a) * k
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert("RGBA")


def salon(cam, ev, lamp=1.0, draw=None):
    w = decor(cam, SALON)
    if draw:
        draw(w)
    return light(w, cam, ev, lamp)


def pot_cam(z, dy=0):
    return Cam(z, POT_AT[0], POT_AT[1] - POT_H * 0.48 + dy)


def soil_pt(cam, h=POT_H):
    x, y = cam.p(*POT_AT)
    return x, y - h * cam.z * (1 - SOIL_Y)


# ------------------------------------------------------------ petites cartes
@lru_cache(None)
def gauge_img(p_int, w=520):
    """Jauge de lumière : soleil + barre jaune qui se vide."""
    p = p_int / 100
    h = 96

    def f(d, k, _):
        d.rounded_rectangle([8 * k, 14 * k, (w - 2) * k, (h - 2) * k], radius=40 * k, fill=(0, 0, 0, 90))
        d.rounded_rectangle([0, 0, (w - 10) * k, (h - 14) * k], radius=40 * k, fill=CREAM, outline=DARK, width=6 * k)
        x0, x1 = 112 * k, (w - 34) * k
        d.rounded_rectangle([x0, 22 * k, x1, (h - 36) * k], radius=20 * k, fill=(214, 204, 186))
        if p > 0.02:
            d.rounded_rectangle([x0, 22 * k, x0 + (x1 - x0) * p, (h - 36) * k], radius=20 * k,
                                fill=YEL if p > 0.45 else (236, 140, 50))
    im = aa(w, h, f, 3)
    sun = icon("sun", 84)
    im.alpha_composite(sun, (14, (h - 14 - sun.height) // 2))
    return im


@lru_cache(None)
def day_chip(lbl, size=118):
    def f(d, k, _):
        d.rounded_rectangle([5 * k, 9 * k, (size - 1) * k, (size * 1.25 - 1) * k], radius=20 * k, fill=(0, 0, 0, 80))
        d.rounded_rectangle([0, 0, (size - 6) * k, (size * 1.25 - 10) * k], radius=20 * k, fill=CREAM, outline=DARK,
                            width=5 * k)
        d.rounded_rectangle([0, 0, (size - 6) * k, int(size * 0.34) * k], radius=20 * k, fill=RED)
        d.rectangle([0, int(size * 0.2) * k, (size - 6) * k, int(size * 0.34) * k], fill=RED)
    im = aa(size, int(size * 1.25), f, 3)
    t_ = text_img(lbl, F_BLACK, int(size * 0.22), WHITE)
    im.alpha_composite(t_, ((size - 6 - t_.width) // 2, int(size * 0.17 - t_.height / 2)))
    return im


def frost(c, x, y, rx, ry, a, seed=2):
    """Givre sur la vitre : taches blanches cristallines, plus denses au centre."""
    if a <= 0.01:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    r = np.random.default_rng(seed)
    for _ in range(140):
        ang, rad = r.uniform(0, 2 * math.pi), r.uniform(0, 1) ** 0.7
        px, py = x + math.cos(ang) * rx * rad, y + math.sin(ang) * ry * rad
        s = r.uniform(3, 11) * (1.2 - rad)
        al = int(255 * a * r.uniform(0.4, 0.9) * (1 - rad * 0.6))
        d.line([(px - s, py), (px + s, py)], fill=(240, 248, 255, al), width=2)
        d.line([(px, py - s), (px, py + s)], fill=(240, 248, 255, al), width=2)
        d.line([(px - s * 0.7, py - s * 0.7), (px + s * 0.7, py + s * 0.7)], fill=(240, 248, 255, al), width=1)
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(veil).ellipse([x - rx, y - ry, x + rx, y + ry], fill=(235, 244, 252, int(110 * a)))
    c.alpha_composite(veil.filter(ImageFilter.GaussianBlur(rx * 0.25)))
    c.alpha_composite(lay)


# ============================================================ A. TA PLANTE JAUNIT ? C'EST LA LUMIÈRE (0 → 4.45)
def s_intro(t):
    k = ease_io(clamp(t / 4.3))
    cam = pot_cam(lerp(1.15, 1.45, k), dy=-40)
    x, y = cam.p(*POT_AT)
    q = clamp((t - 1.15) / 0.8)

    def draw(w):
        pothos(w, x, y, POT_H * cam.z, q)
    w = salon(cam, lerp(0.0, 0.15, k), draw=draw)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    title(u, "TA PLANTE JAUNIT ?", t, 0.05, 2.35, y=330, color=YEL, size=135)
    if 2.4 < t < 3.85:
        a = life(t, 2.42, 3.8)
        put(u, icon("drop", 170), 540, 700, a)
        if t > 2.75:
            put(u, icon("nosign", 250), 540, 700, ease_out_back(clamp((t - 2.75) / 0.3), 1.6) * a)
    title(u, "CE N'EST PAS L'EAU…", t, 2.4, 3.85, y=330, color=WHITE, size=120)
    if t > 3.85:
        light_rays(u, 860, 260, t, fade(t, 3.85, None, 0.3) * 0.8)
        put(u, icon("sun", 200), 860, 640, ease_out_back(clamp((t - 3.9) / 0.35), 1.6))
    stamp(u, "C'EST LA LUMIÈRE !", 540, 340, t, 3.88, None, RED, 115, -6)
    return w, u


cue(0.05, "whoosh", 0.1)
cue(1.4, "fail", 0.14)
cue(2.45, "pop", 0.16)
cue(2.8, "alert1", 0.14)
cue(3.9, "thud", 0.2)
cue(4.0, "sparkle", 0.14)


# ============================================================ B. EN HIVER, LES JOURS RACCOURCISSENT (4.45 → 8.85)
def s_days(t):
    cam = pot_cam(lerp(1.0, 1.08, clamp((t - 4.45) / 4.4)), dy=-120)
    ev = ease_io(clamp((t - 5.7) / 2.6))          # le soir tombe dans la pièce
    x, y = cam.p(*POT_AT)

    def draw(w):
        pothos(w, x, y, POT_H * cam.z, 1.0)
    w = salon(cam, ev, draw=draw)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    # le soleil fait une toute petite course et se couche (8 h → 17 h, en accéléré)
    s = life(t, 5.7, 7.2)
    if s > 0.01:
        q = ease_io(clamp((t - 5.75) / 1.35))
        cx, cy, R = 540, 780, 330
        ang = math.radians(lerp(160, 20, q))
        d = ImageDraw.Draw(u)
        d.arc([cx - R, cy - R, cx + R, cy + R], 200, 340, fill=(255, 255, 255, int(160 * s)), width=6)
        put(u, icon("sun", 130), cx + math.cos(ang) * R, cy - math.sin(ang) * R, s)
        put(u, text_img("8 H", F_TITLE, 70, WHITE, 6, DARK), cx - R * 0.95, cy - 40, s)
        put(u, text_img("17 H", F_TITLE, 70, WHITE, 6, DARK), cx + R * 0.95, cy - 40, s)
    g = life(t, 7.25, None)
    if g > 0.01:
        p = lerp(1.0, 0.22, ease_io(clamp((t - 7.4) / 1.2)))
        put(u, gauge_img(int(p * 100), 640), 540, 640, g)
    title(u, "EN HIVER…", t, 4.47, 5.7, y=330, color=WHITE, size=150)
    title(u, "LES JOURS RACCOURCISSENT", t, 5.72, 7.2, y=330, color=YEL, size=96)
    title(u, "BEAUCOUP MOINS DE LUMIÈRE", t, 7.25, None, y=330, color=YEL, size=92)
    return w, u


cue(4.48, "whoosh", 0.1)
cue(5.75, "whoosh_up", 0.1)
cue(7.27, "pop", 0.14)
cue(7.5, "fail", 0.12)


# ============================================================ C. ELLE POUSSE MOINS, ELLE BOIT MOINS (8.85 → 11.1)
def s_less(t):
    cam = pot_cam(lerp(1.35, 1.5, clamp((t - 8.85) / 2.25)), dy=-60)
    x, y = cam.p(*POT_AT)

    def draw(w):
        pothos(w, x, y, POT_H * cam.z, 1.0, sway=math.sin(t * 1.3) * 0.6)
    w = salon(cam, 1.0, draw=draw)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    for t0, lbl, ic, px, py, rot in ((9.4, "POUSSE MOINS", "arrow_down", 300, 760, -5),
                                    (10.5, "BOIT MOINS", "drop", 780, 1040, 5)):
        s = life(t, t0, None)
        if s > 0.01:
            put(u, icon(ic, 120), px - 170 if px < 540 else px + 170, py, s)
            tag(u, lbl, px, py, t, t0, None, rot=rot, size=56)
    title(u, "ALORS…", t, 8.87, 9.38, y=330, color=WHITE, size=150)
    title(u, "ELLE SE MET AU RALENTI", t, 9.4, None, y=330, color=YEL, size=100)
    return w, u


cue(8.9, "whoosh", 0.1)
cue(9.42, "pop", 0.16)
cue(10.52, "pop_hi", 0.16)


# ============================================================ D. MAIS TOI, TU ARROSES PAREIL (11.1 → 13.4)
def s_water(t):
    cam = pot_cam(1.3, dy=-40)
    x, y = cam.p(*POT_AT)
    sx, sy = soil_pt(cam)
    s = 0.85 * cam.z

    def draw(w):
        pothos(w, x, y, POT_H * cam.z, 1.0)
        # l'arrosoir arrive, verse, repart (« tu continues d'arroser pareil »)
        if 11.6 < t < 13.4:
            cin = ease_out(clamp((t - 11.6) / 0.35))
            cout = ease_in(clamp((t - 13.0) / 0.3))
            tilt = -28 * ease_io(clamp((t - 11.85) / 0.25)) * (1 - cout)
            cx = lerp(-400, sx - 300 * s, cin) - 700 * cout
            cy = sy - 260 * s
            sp(w, CAN, cx, cy, 300 * s, 0.5, 0.5, rot=tilt, flip=True)
            watering(w, t, fade(t, 12.05, 12.95, 0.06, 0.1), (cx + 165 * s, cy - 30 * s), sy - 4, s)
    w = salon(cam, 1.0, draw=draw)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    # la main qui te montre du doigt
    if 11.2 < t < 12.4:
        k = ease_out_back(clamp((t - 11.25) / 0.35), 1.5)
        out = ease_in(clamp((t - 12.1) / 0.3))
        sp(u, MAIN_FACE, lerp(1300, 760, k) + 600 * out, 1300 + math.sin(t * 9) * 8, 560, 0.5, 0.5,
           rot=6 * math.sin(t * 7))
    stamp(u, "TOI !", 540, 340, t, 11.42, 11.95, RED, 170, -6)
    title(u, "TU ARROSES PAREIL ?", t, 11.97, None, y=330, color=YEL, size=125)
    tag(u, "COMME EN ÉTÉ", 780, 760, t, 12.4, None, rot=5, size=56)
    return w, u


cue(11.15, "whoosh", 0.1)
cue(11.42, "thud", 0.2)
cue(12.05, "pour", 0.2)
cue(12.42, "pop", 0.14)


# ============================================================ E. L'EAU STAGNE, LES FEUILLES JAUNISSENT (13.4 → 16.8)
CUT_AT = (540, 1440)
CUT_H = 1000


def s_rot(t):
    w = salon(Cam(1.0, 540, 960), 1.0)
    w = w.filter(ImageFilter.GaussianBlur(14))
    w.alpha_composite(Image.new("RGBA", (W, H), (20, 14, 8, 90)))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sec = life(t, 13.45, 15.45, dur=0.3, out=0.25)
    if sec > 0.01:
        k, s_ = swap(clamp((t - 14.2) / 0.8))
        soft_shadow(lay, CUT_AT[0], CUT_AT[1], CUT_H * 0.6, 110)
        sp(lay, COUPE if k == 0 else COUPE_P, CUT_AT[0], CUT_AT[1], CUT_H * s_ * sec, 0.5, 1.0)
        if t > 14.7:          # l'eau qui stagne au fond : reflets qui ondulent
            d = ImageDraw.Draw(lay)
            for i in range(5):
                yy = CUT_AT[1] - CUT_H * 0.075 + i * 6
                xx = CUT_AT[0] - 170 + ((t * 90 + i * 70) % 340)
                d.line([(xx - 30, yy), (xx + 30, yy)], fill=(210, 230, 240, int(150 * sec)), width=3)
    w.alpha_composite(lay)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if sec > 0.01 and t > 14.6:
        tag(u, "L'EAU STAGNE", 760, CUT_AT[1] - CUT_H * 0.06, t, 14.6, 15.45, rot=4, size=56,
            string_to=(CUT_AT[0] + 150, CUT_AT[1] - CUT_H * 0.06))
    # « les feuilles jaunissent » : verte → jaune → noire
    for i, (nm, t0) in enumerate(((F_VERTE, 15.45), (F_JAUNE, 15.75), (F_NOIRE, 16.05))):
        s = ease_out_back(clamp((t - t0) / 0.35), 1.5)
        if s > 0.01:
            sp(u, nm, 200 + i * 340, 1150, 420 * s, 0.5, 0.5, rot=(-8, 0, 8)[i])
            if i:
                put(u, icon("arrow_down", 90), 30 + i * 340, 1150, s, rot=90)
    w.alpha_composite(shade())
    title(u, "RÉSULTAT…", t, 13.45, 14.5, y=330, color=WHITE, size=150)
    title(u, "L'EAU STAGNE", t, 14.52, 15.45, y=330, color=BLUE, size=150)
    title(u, "LES FEUILLES JAUNISSENT", t, 15.47, None, y=330, color=YEL, size=96)
    return w, u


cue(13.47, "whoosh", 0.12)
cue(14.55, "splash", 0.14)
cue(14.6, "fail", 0.14)
for _t in (15.48, 15.78, 16.08):
    cue(_t, "pop", 0.15)


# ============================================================ F. RAPPROCHE-LA D'UNE FENÊTRE… PAS CONTRE LA VITRE (16.8 → 20.25)
def s_window(t):
    cam = Cam(lerp(1.05, 1.15, clamp((t - 16.8) / 3.4)), 560, 1000)
    w = decor(cam, FENETRE)
    z = cam.z
    # le pot glisse sur le rebord, d'abord contre la vitre, puis on le recule
    arrive = ease_out(clamp((t - 17.0) / 0.6))
    back = ease_io(clamp((t - 19.0) / 0.6))
    gx, gy = lerp(SILL_BACK[0], SILL_FRONT[0], back), lerp(SILL_BACK[1], SILL_FRONT[1], back)
    gx = lerp(-300, gx, arrive)
    hh = lerp(640, 720, back)
    X, Y = cam.p(gx, gy)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pothos(lay, X, Y, hh * z, 0.0)
    fr = fade(t, 18.4, 19.1, 0.3, 0.4)
    if fr > 0.01:    # contre la vitre froide : le givre gagne les feuilles
        frost(lay, X, Y - hh * z * 0.78, 230 * z, 150 * z, fr)
    w.alpha_composite(lay)
    light_rays(w, 700, 200, t, 0.6)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if 18.6 < t < 19.3:
        put(u, icon("cross", 150), X + 260, Y - hh * z * 0.9, ease_out_back(clamp((t - 18.65) / 0.3), 1.6))
        put(u, icon("snow", 110), X - 260, Y - hh * z * 0.8, life(t, 18.5, 19.25))
    if t > 19.6:
        put(u, icon("check", 150), X + 280, Y - hh * z * 0.95, ease_out_back(clamp((t - 19.6) / 0.3), 1.6))
    title(u, "PRÈS D'UNE FENÊTRE…", t, 16.82, 18.4, y=330, color=YEL, size=120)
    title(u, "PAS CONTRE LA VITRE !", t, 18.42, None, y=330, color=RED, size=115)
    tag(u, "QUELQUES CM", X - 250, Y - 330, t, 19.65, None, rot=-5, size=52)
    return w, u


cue(16.85, "whoosh", 0.12)
cue(17.0, "whoosh", 0.08)
cue(18.45, "crunch", 0.12)
cue(18.65, "alert2", 0.14)
cue(19.0, "whoosh", 0.07)
cue(19.62, "ding", 0.16)


# ============================================================ G. ESPACE LES ARROSAGES : SÈCHE SUR 2 CM (20.25 → 24.35)
DAYS = ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"]
KEEP = (0, 4)                   # on n'arrose plus que deux fois


def s_spacing(t):
    w = decor(Cam(1.0, 540, 960), FENETRE)
    w = w.filter(ImageFilter.GaussianBlur(12))
    w.alpha_composite(Image.new("RGBA", (W, H), (248, 242, 229, 90)))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cal = life(t, 20.3, 21.75, dur=0.3, out=0.25)
    if cal > 0.01:          # la semaine : une goutte chaque jour… puis seulement deux
        for i, dname in enumerate(DAYS):
            x = 115 + i * 142
            s = ease_out_back(clamp((t - 20.3 - i * 0.04) / 0.3), 1.5) * cal
            put(lay, day_chip(dname), x, 820, s)
            gone = i not in KEEP and t > 20.9 + 0.05 * i
            if not gone:
                put(lay, icon("drop", 70), x, 845, s)
            elif t < 21.3 + 0.05 * i:
                put(lay, icon("drop", 70), x, 845 - 120 * clamp((t - 20.9 - 0.05 * i) / 0.3), s * (1 - clamp((t - 20.9 - 0.05 * i) / 0.3)))
    sec = life(t, 21.75, None, dur=0.35)
    if sec > 0.01:          # le doigt dans la terre
        cx, cy, ch = 540, 1660, 980
        sp(lay, COUPE, cx, cy, ch * sec, 0.5, 1.0)
        top = cy - ch * (1 - 0.53)               # dessus de la terre dans la coupe
        if t > 22.2:          # 2 cm du dessus : terre sèche, plus claire
            d = ImageDraw.Draw(lay)
            band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(band).rectangle([cx - 270, top, cx + 270, top + 70], fill=(200, 170, 130, 110))
            lay.alpha_composite(band)
        dip = ease_io(clamp((t - 22.1) / 0.45)) * (1 - ease_io(clamp((t - 23.4) / 0.4)))
        sp(lay, MAIN_BAS, cx + 30, top + 70 * dip + 4, 640, 0.835, 1.0, alpha=sec)
    w.alpha_composite(lay)
    if sec > 0.01 and t > 22.5:
        d = ImageDraw.Draw(u)
        x0 = 540 + 330
        top = 1660 - 980 * (1 - 0.53)
        d.line([(x0, top), (x0, top + 70)], fill=WHITE, width=8)
        d.line([(x0 - 22, top), (x0 + 22, top)], fill=WHITE, width=8)
        d.line([(x0 - 22, top + 70), (x0 + 22, top + 70)], fill=WHITE, width=8)
        put(u, text_img("2 CM", F_TITLE, 90, YEL, 8, DARK), x0 + 10, top - 70, life(t, 22.5, None))
    if t > 22.85:
        put(u, icon("check", 140), 540 - 330, 1660 - 980 * 0.47 - 60, ease_out_back(clamp((t - 22.85) / 0.3), 1.6))
    title(u, "ESPACE TES ARROSAGES", t, 20.3, 21.75, y=330, color=YEL, size=105)
    title(u, "ATTENDS QUE LA TERRE", t, 21.77, None, y=300, color=WHITE, size=100)
    title(u, "SOIT SÈCHE SUR 2 CM", t, 21.77, None, y=430, color=YEL, size=105)
    return w, u


cue(20.32, "whoosh", 0.1)
for _i in range(7):
    if _i not in KEEP:
        cue(20.9 + 0.05 * _i, "pop_hi", 0.08)
cue(21.78, "whoosh", 0.1)
cue(22.2, "squish", 0.14)
cue(22.55, "tick", 0.2)
cue(22.87, "ding", 0.16)


# ============================================================ H. ABONNE-TOI (24.35 → fin)
def s_end(t):
    cam = Cam(1.1, 560, 1000)
    w = decor(cam, FENETRE)
    X, Y = cam.p(*SILL_FRONT)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pothos(lay, X, Y, 720 * cam.z, 0.0, sway=math.sin(t * 1.2) * 0.6)
    w.alpha_composite(lay)
    w = sunset(w, ease_io(clamp((t - 24.4) / 2.5)))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    clicked = t > 26.25
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 26.2) / 0.15))
    put(u, btn, 540, 1400, life(t, 24.6) * press)
    if t > 25.7:
        kk = ease_out((t - 25.7) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 27.2, dur=0.45))
    sparkles(u, t, 27.3, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 24.45, 27.15, y=330, color=YEL, size=135)
    return w, u


cue(24.5, "pop_lo", 0.18)
cue(26.23, "click", 0.3)
cue(27.3, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 4.45 - SHIFT, _sh(s_intro)),
    (4.45 - SHIFT, 8.85 - SHIFT, _sh(s_days)),
    (8.85 - SHIFT, 11.1 - SHIFT, _sh(s_less)),
    (11.1 - SHIFT, 13.4 - SHIFT, _sh(s_water)),
    (13.4 - SHIFT, 16.8 - SHIFT, _sh(s_rot)),
    (16.8 - SHIFT, 20.25 - SHIFT, _sh(s_window)),
    (20.25 - SHIFT, 24.35 - SHIFT, _sh(s_spacing)),
    (24.35 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
