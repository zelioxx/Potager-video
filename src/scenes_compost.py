"""Storyboard « Compost : les 3 erreurs » (voix : assets/audio/compost/voix.mp3).

Intro : la vidéo fournie (assets/video/intro_compost.mp4) brute, sans texte, son coupé (seule la voix).
Puis motion design : composteur fourni (ouvert / fermé), épluchures, feuilles mortes, carton, brindilles,
viande, poisson, fromage, lait, rat, fourche (Open Images), logo « Les Potagers de Louis ».
"""
import math
import os
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from gfx import (ROOT, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, spr, put, paste, title, life, fade,
                 ease_out, ease_in, ease_io, clamp, lerp, icon, num_badge, tag, button_img, hl_ellipse, particles,
                 text_img, asset, aa, F_TITLE, F_BLACK)
from scenes import TABLE, new_layers, flies, sparkles, falling

CUES = []
VID_END = 2.11
NO_CAPTION_UNTIL = VID_END
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


C = "compost/"
VIDEO = os.path.join(ROOT, "assets", "video", "intro_compost.mp4")
IMG_DIR = os.path.join(ROOT, "assets", "images", "compost")


# ------------------------------------------------------------- vidéo d'intro (brute)
@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_compost_intro")
    if not os.path.isdir(d) or not os.listdir(d):
        os.makedirs(d, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", VIDEO, "-an", "-vf",
                        f"fps={FPS},scale={W}:{H}:flags=lanczos", os.path.join(d, "%04d.png")], check=True)
    return sorted(os.path.join(d, f) for f in os.listdir(d))


def s_video(t):
    fr = video_frames()
    i = min(len(fr) - 1, max(0, int(round(t * FPS))))
    return Image.open(fr[i]).convert("RGBA"), Image.new("RGBA", (W, H), (0, 0, 0, 0))


s_video.raw = True


# ------------------------------------------------------------- composteur
BIN_X = 540
BIN_H = 880                       # hauteur affichée du composteur ouvert
OPEN = "composteur_ouvert"         # 461 x 969 (couvercle ouvert)
OPEN_SIZE = (461, 969)
MOUTH_Y = 0.305                    # hauteur de l'ouverture (fraction depuis le haut)
MOUTH_W = 0.62                     # largeur de l'ouverture (fraction de la largeur)


def bin_open(c, x=BIN_X, base=TABLE + 40, h=BIN_H, s=1.0, rot=0.0):
    spr(c, C + OPEN, x, base, h, s, rot=rot)
    return mouth(x, base, h)


def mouth(x=BIN_X, base=TABLE + 40, h=BIN_H):
    """(x centre, y, demi-largeur) de l'ouverture du composteur à l'écran."""
    w = OPEN_SIZE[0] * h / OPEN_SIZE[1]
    return x, base - h + h * MOUTH_Y, w * MOUTH_W / 2


def drop_in(c, name, t, t0, mx, my, start, h=200, rot0=0.0, dur=0.55):
    """Un objet (photo) tombe de `start` dans l'ouverture puis disparaît dedans."""
    if t < t0:
        return
    k = (t - t0) / dur
    if k > 1.25:
        return
    kk = clamp(k)
    x = lerp(start[0], mx, kk)
    y = lerp(start[1], my, kk ** 2)
    sc = 1.0 if k < 1 else max(0.0, 1 - (k - 1) * 4)
    spr(c, name, x, y, h, sc, rot=rot0 + 160 * kk, shadow=False, anchor="center")


def stink(c, x, y, t, a=1.0, spread=110):
    if a <= 0.01:
        return
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for k in range(3):
        ph = (t * 0.7 + k / 3) % 1
        x0 = x + (k - 1) * spread
        y0 = y - ph * 90
        pts = [(x0 + 24 * math.sin(i / 2.2 + t * 3 + k), y0 - i * 9) for i in range(13)]
        al = int(255 * a * math.sin(math.pi * ph))
        d.line(pts, fill=(40, 44, 22, al), width=20, joint="curve")
        d.line(pts, fill=(176, 168, 70, al), width=11, joint="curve")
    c.alpha_composite(ov)


def pile(c, mx, my, half, items, t0, t, rotten=0.0):
    """Petit tas d'objets posés dans l'ouverture (dessus du compost)."""
    for i, (name, dx, h, rot) in enumerate(items):
        s = life(t, t0 + i * 0.05)
        spr(c, name, mx + dx * half * 0.85, my + 34, h * 0.8, s, rot=rot, shadow=False, rotten=rotten)


@lru_cache(None)
def card_img(name, size=300):
    pad = 16
    S = size + pad * 2
    card = aa(S, S + 10, lambda d, k, _: (
        d.rounded_rectangle([0, 6 * k, S * k - 1, (S + 10) * k - 1], radius=20 * k, fill=(60, 40, 25, 90)),
        d.rounded_rectangle([0, 0, S * k - 1, S * k - 1], radius=20 * k, fill=DARK),
        d.rounded_rectangle([5 * k, 5 * k, (S - 5) * k, (S - 5) * k], radius=16 * k, fill=WHITE)))
    ph = Image.open(os.path.join(IMG_DIR, name)).convert("RGBA").resize((size, size), Image.LANCZOS)
    m = aa(size, size, lambda d, k, _: d.rounded_rectangle([0, 0, size * k - 1, size * k - 1], radius=12 * k, fill=WHITE))
    ph.putalpha(m.getchannel("A"))
    card.alpha_composite(ph, (pad, pad))
    return card


# ============================================================ A. 3 ERREURS (2.11 → 6.3)
def s_intro(t):
    w, u = new_layers(background("table"))
    spr(w, C + "composteur_ferme", 540, TABLE + 40, 640, life(t, 2.15, dur=0.4))
    title(u, "BONNE IDÉE !", t, 2.38, 4.6, y=330, size=150)
    put(u, icon("check", 170), 870, 640, life(t, 3.9, 4.6))
    title(u, "ÉVITE 3 ERREURS", t, 4.7, None, y=330, color=RED, size=130)
    for i in range(3):
        put(u, num_badge(str(i + 1), 130, RED, WHITE), 340 + i * 200, 510, life(t, 5.38 + i * 0.1))
    return w, u




# ============================================================ B. ERREUR 1 : QUE DES ÉPLUCHURES (6.3 → 13.1)
PEELS = [(C + "epluchure_orange", -0.45, 120, -15), (C + "epluchure_banane", 0.1, 130, 20),
         (C + "epluchure_orange", 0.5, 110, 40)]


def s_err1(t):
    w, u = new_layers(background("table"))
    mx, my, half = bin_open(w)
    # épluchures qui tombent dedans, puis forment un tas mouillé
    for i, (name, dx, h, rot) in enumerate(PEELS):
        drop_in(w, name, t, 7.9 + i * 0.3, mx + dx * half, my, (mx + dx * half + (i - 1) * 260, 380), h * 1.8, rot)
    rot = clamp((t - 11.5) / 0.8)
    if t > 9.4:
        pile(w, mx, my, half, PEELS, 9.4, t, rotten=rot)
    if t > 10.4:
        falling(w, t, 10.4, 11.5, "drop", 10, 7, 900, 44, top=my - 500, bottom=my)
    stink(w, mx, my - 120, t, fade(t, 12.2, None, 0.4))
    flies(w, t, 12.4, None, mx, my - 200, 200)
    title(u, "ERREUR N°1", t, 6.42, 7.8, y=330, color=RED)
    title(u, "QUE DES ÉPLUCHURES", t, 7.86, 10.3, y=330, size=115)
    title(u, "TROP HUMIDE", t, 10.42, 11.45, y=330)
    title(u, "ÇA POURRIT…", t, 11.54, 12.3, y=330, color=RED)
    title(u, "ÇA SENT MAUVAIS", t, 12.34, None, y=330, color=RED, size=125)
    return w, u




# ============================================================ C. AJOUTE DU SEC (13.1 → 17.05)
DRY = [(C + "feuille1", 14.34, "FEUILLES MORTES", 170), (C + "carton", 15.18, "CARTON BRUN", 165),
       (C + "brindilles", 15.98, "PETITES BRANCHES", 190)]


def s_dry(t):
    w, u = new_layers(background("table"))
    mx, my, half = bin_open(w, 540, TABLE + 40, 560)
    xs = [190, 540, 890]
    merge_t = 16.55
    for i, (name, t0, lab, h) in enumerate(DRY):
        if t < merge_t + i * 0.12:
            spr(w, name, xs[i], 530, h, life(t, t0), shadow=False, anchor="center", rot=[-8, 4, 8][i])
            put(u, text_img(lab, F_TITLE, 42, YEL, 6, DARK, 5, DARK), xs[i], 670, life(t, t0 + 0.08), -3)
        else:
            drop_in(w, name, t, merge_t + i * 0.12, mx, my, (xs[i], 530), h * 0.7, [-8, 4, 8][i])
    title(u, "AJOUTE DU SEC !", t, 13.26, None, y=330, color=YEL, size=140)
    return w, u




# ============================================================ D. ERREUR 2 : VIANDE, POISSON, LAITIERS (17.05 → 24.15)
BAD = [(C + "viande", 18.94, 360, 280, 660), (C + "poisson", 19.66, 330, 800, 660),
       (C + "fromage", 20.38, 280, 300, 1070), (C + "lait", 20.6, 400, 790, 1060)]


def s_err2(t):
    w, u = new_layers(background("table"))
    if t < 21.5:
        for name, t0, h, x, y in BAD:
            spr(w, name, x, y, h, life(t, t0), shadow=False, anchor="center")
            put(u, icon("cross", 120), x + 150, y - 130, life(t, t0 + 0.15))
        title(u, "ERREUR N°2", t, 17.18, 18.6, y=330, color=RED)
        title(u, "VIANDE, POISSON…", t, 18.7, 20.3, y=330, size=125)
        title(u, "PRODUITS LAITIERS", t, 20.38, None, y=330, size=115)
        return w, u
    mx, my, half = bin_open(w, 680, TABLE + 40, 860)
    stink(w, mx, my - 100, t, fade(t, 22.6, None, 0.4), 120)
    flies(w, t, 22.8, None, mx, my - 220, 220)
    k = ease_out((t - 23.55) / 0.45)
    spr(w, C + "rat", lerp(-300, 300, k), TABLE + 60, 300)
    title(u, "BONJOUR LES ODEURS…", t, 22.54, 23.6, y=330, color=RED, size=115)
    title(u, "ET LES RATS !", t, 23.74, None, y=330, color=RED, size=150)
    return w, u




# ============================================================ E. ERREUR 3 : NE JAMAIS LE REMUER (24.15 → 31.9)
FORK = C + "fourche"


def s_err3(t):
    w, u = new_layers(background("table"))
    shake = math.sin(t * 40) * 5 * fade(t, 27.42, 28.6)
    mx, my, half = bin_open(w, 500 + shake, TABLE + 40, BIN_H)
    pile(w, mx, my, half, [(C + "feuille1", -0.4, 80, 20), (C + "carton", 0.2, 80, -10),
                            (C + "epluchure_orange", 0.5, 70, 30)], 24.2, t, rotten=0.6 if t < 29.1 else 0.0)
    if t < 28.9:
        spr(w, FORK, 850, 760, 640, life(t, 25.58), rot=-12, shadow=False, anchor="center")
        put(u, icon("nosign", 300), 840, 760, life(t, 25.86))
        stink(w, mx, my - 80, t, fade(t, 27.42, None, 0.3))
        title(u, "ERREUR N°3", t, 24.22, 25.5, y=330, color=RED)
        title(u, "NE JAMAIS REMUER", t, 25.58, 27.3, y=330, size=125)
        title(u, "IL ÉTOUFFE !", t, 27.42, None, y=330, color=RED, size=150)
    else:
        # la fourche plonge dans l'ouverture et remue
        k = ease_out((t - 28.95) / 0.35)
        stir = math.sin((t - 29.3) * 9) * 14 if t > 29.3 else 0
        fx = lerp(1100, mx + 40, k) + stir * 2
        fy = lerp(300, my - 230, k) + abs(stir)
        spr(w, FORK, fx, fy, 640, rot=12 + stir, shadow=False, anchor="center")
        if t > 29.3:
            particles(w, t, 29.3 + ((t - 29.3) // 0.5) * 0.5, mx, my, 10, int(t * 2), col=(90, 64, 40), size=9,
                      up=420, dur=0.5)
        sparkles(w, t, 30.6, mx, my - 120, 260, 9, 4)
        title(u, "UN COUP DE FOURCHE", t, 29.14, 30.5, y=330, size=115)
        title(u, "C'EST REPARTI !", t, 30.6, None, y=330, color=YEL, size=140)
        put(u, icon("check", 160), 880, 520, life(t, 30.7))
    return w, u




# ============================================================ F. CTA + LOGO (31.9 → fin)
@lru_cache(None)
def logo_img(size=480):
    im = Image.open(os.path.join(IMG_DIR, "logo.jpg")).convert("RGBA").resize((size, size), Image.LANCZOS)
    m = aa(size, size, lambda d, k, _: d.rounded_rectangle([0, 0, size * k - 1, size * k - 1], radius=48 * k, fill=WHITE))
    im.putalpha(m.getchannel("A"))
    S = size + 16
    out = aa(S, S, lambda d, k, _: d.rounded_rectangle([0, 0, S * k - 1, S * k - 1], radius=54 * k, fill=DARK))
    out.alpha_composite(im, (8, 8))
    return out


def s_cta(t):
    w, u = new_layers(background("table"))
    spr(w, C + "composteur_ferme", 540, TABLE + 40, 440, life(t, 31.95))
    if t < 34.2:
        title(u, "TU SAIS TOUT !", t, 31.98, None, y=330, color=YEL, size=140)
        put(u, icon("check", 170), 540, 600, life(t, 32.98))
    clicked = t > 34.85
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 34.8) / 0.15))
    put(u, btn, 540, 300, life(t, 34.3) * press)
    if t > 34.5:
        k = ease_out((t - 34.5) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(400), 540, 600, life(t, 36.02, dur=0.45), math.sin((t - 36.0) * 2) * 1.5)
    sparkles(u, t, 36.1, 540, 600, 270, 10, 12)
    return w, u



# ------------------------------------------------------------- plan sonore (sobre, sans répétitions)
for _c in [
    (2.2, "thud", 0.4), (2.38, "pop", 0.25), (3.9, "ding", 0.3), (4.7, "rise", 0.25),
    (5.38, "pop_hi", 0.2), (5.48, "pop_hi", 0.2), (5.58, "pop_hi", 0.2),
    # erreur 1
    (6.42, "alert1", 0.45), (7.95, "whoosh", 0.2), (8.55, "plop", 0.3), (9.15, "plop", 0.22),
    (10.42, "rain", 0.25), (11.54, "squish", 0.3), (12.34, "buzz", 0.16),
    # ajoute du sec
    (13.3, "ding", 0.3), (14.34, "pop", 0.3), (15.18, "pop", 0.28), (15.98, "pop", 0.26), (16.6, "whoosh", 0.22),
    # erreur 2
    (17.18, "alert2", 0.45), (18.94, "pop", 0.3), (19.66, "pop", 0.28), (20.38, "pop", 0.26), (20.6, "pop_hi", 0.2),
    (22.6, "buzz", 0.16), (23.7, "squeak", 0.4),
    # erreur 3
    (24.22, "alert3", 0.45), (25.6, "pop", 0.28), (25.86, "tick", 0.3), (27.42, "squish", 0.28),
    (28.95, "whoosh", 0.25), (29.35, "stir", 0.45), (30.0, "stir", 0.38), (30.6, "success", 0.35),
    # fin
    (31.95, "pop_lo", 0.3), (32.98, "sparkle", 0.3), (34.3, "pop_hi", 0.3), (34.83, "click", 0.55),
    (34.9, "bell", 0.35), (36.1, "success", 0.35),
]:
    cue(*_c)

SCENES = [
    (0.0, VID_END, s_video),
    (VID_END, 6.3, s_intro),
    (6.3, 13.1, s_err1),
    (13.1, 17.05, s_dry),
    (17.05, 24.15, s_err2),
    (24.15, 31.9, s_err3),
    (31.9, 99.0, s_cta),
]

TRAPS = [(1, 6.4, 17.05), (2, 17.1, 24.15), (3, 24.2, 31.9)]
