"""Storyboard « Refaire pousser un ananas avec sa tête » (voix : assets/audio/ananas/voix.mp3).

Photos fournies : tête d'ananas avec racines, ananas entier, plant d'ananas en pot (fruit) ; pomme (Open Images).
La tête nue et la couronne sont découpées dans ces photos. Si assets/video/intro_ananas.mp4 existe, la
première phrase montre cette vidéo brute (sans texte, son coupé) avant le motion design.
"""
import math
import os
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (ROOT, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, spr, put, paste, title, life, fade,
                 ease_out, ease_in, ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse,
                 measure, particles, text_img, asset, aa, glass_back, glass_front, water, F_TITLE, F_BLACK)
from scenes import TABLE, new_layers, flies, sparkles, falling
from scenes_aromatiques import pot
from scenes_arrosage import can_center_for_spout

CUES = []
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


A = "ananas/"
VIDEO = os.path.join(ROOT, "assets", "video", "intro_ananas.mp4")
HAS_VIDEO = os.path.exists(VIDEO)


def video_duration():
    if not HAS_VIDEO:
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                         capture_output=True, text=True).stdout
    return min(2.2, float(out.strip() or 0))


VID_END = video_duration()
NO_CAPTION_UNTIL = VID_END


@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_ananas_intro")
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

# ------------------------------------------------------------- géométrie des photos (coordonnées d'origine 1024)
TETE_BOX = (278, 46, 765, 561)          # tete.png
TR_BOX = (207, 45, 788, 939)            # tete_racines.png
AN_BOX = (289, 33, 731, 986)            # ananas.png
CROWN_BOX = (289, 33, 731, 468)         # couronne.png (approx.)
FRUIT_TOP = 452                         # haut de fruit.png dans l'ananas
STEM_Y = 561                            # base de la tige (début des racines)


def place(c, name, box, k, ax, ay, X, Y, s=1.0, rot=0.0, rotten=0.0, alpha=1.0):
    """Pose `name` (recadré sur `box`) à l'échelle k de sorte que le point d'origine (ax, ay) tombe en (X, Y)."""
    if s <= 0.01:
        return
    w, h = box[2] - box[0], box[3] - box[1]
    cx = X + ((box[0] + box[2]) / 2 - ax) * k * s
    cy = Y + ((box[1] + box[3]) / 2 - ay) * k * s
    spr(c, name, cx, cy, h * k, s, rot=rot, rotten=rotten, alpha=alpha, shadow=False, anchor="center")


def head(c, X, Y, k, s=1.0, rot=0.0, rotten=0.0):
    """Tête nue : base de la tige en (X, Y)."""
    place(c, A + "tete", TETE_BOX, k, 521, STEM_Y, X, Y, s, rot, rotten)


@lru_cache(None)
def roots_reveal(g_q):
    """tete_racines.png avec les racines dévoilées progressivement (g quantifié)."""
    im = asset(A + "tete_racines").copy()
    a = np.asarray(im).copy()
    cut = int((STEM_Y - TR_BOX[1]) + (TR_BOX[3] - STEM_Y) * g_q / 20)
    a[cut:, :, 3] = 0
    return Image.fromarray(a)


def head_roots(c, X, Y, k, g=1.0, s=1.0, rotten=0.0):
    img = roots_reveal(int(round(clamp(g) * 20)))
    w, h = TR_BOX[2] - TR_BOX[0], TR_BOX[3] - TR_BOX[1]
    im = img.resize((max(1, int(w * k * s)), max(1, int(h * k * s))), Image.BICUBIC)
    if rotten > 0.01:
        from gfx import rot_effect
        im = rot_effect(im, A + "tete_racines", rotten)
    x0 = X - (521 - TR_BOX[0]) * k * s
    y0 = Y - (STEM_Y - TR_BOX[1]) * k * s
    paste(c, im, x0, y0)


# ============================================================ A. TU JETTES LA TÊTE ? (0 → 3.0)
def s_throw(t):
    w, u = new_layers(background("table"))
    spr(w, "poireau/trash", 830, TABLE + 10, 420, life(t, 0.3))
    k = 0.85
    if t < 0.75:
        place(w, A + "ananas", AN_BOX, k, 510, 986, 360, TABLE + 30, life(t, 0.0))
    else:
        place(w, A + "fruit", (300, 452, 731, 986), k, 510, 986, 360, TABLE + 30)
        q = clamp((t - 0.75) / 0.9)
        X = lerp(360, 830, q)
        Y = lerp(TABLE + 30 - (986 - 468) * k, TABLE - 380, q) - 380 * math.sin(math.pi * q)
        if q < 1:
            place(w, A + "couronne", CROWN_BOX, k, 510, 468, X, Y, 1 - 0.6 * q, rot=-300 * q)
    if t > 2.26:
        put(u, icon("nosign", 320), 830, TABLE - 220, life(t, 2.26), math.sin(t * 8) * 4)
    title(u, "TU LA JETTES ?", t, 0.46, 2.2, y=330, size=140)
    title(u, "ERREUR !", t, 2.26, None, y=330, color=RED, size=200)
    return w, u


cue(0.05, "pop_lo", 0.35)
cue(0.8, "whoosh", 0.3)
cue(1.65, "thud", 0.4)
cue(2.26, "alert1", 0.45)


def s_error(t):
    """Variante quand la vidéo d'intro existe : juste « ERREUR ! »."""
    w, u = new_layers(background("table"))
    spr(w, "poireau/trash", 540, TABLE + 10, 460, life(t, VID_END))
    put(u, icon("nosign", 360), 540, TABLE - 240, life(t, 2.26), math.sin(t * 8) * 4)
    title(u, "ERREUR !", t, 2.26, None, y=330, color=RED, size=200)
    return w, u


# ============================================================ B. UN NOUVEL ANANAS (3.0 → 6.9)
def s_new(t):
    w, u = new_layers(background("table"))
    head_roots(w, 270, 860, 0.62, 1.0, life(t, 3.1))
    put(u, icon("arrow_down", 140), 540, 860, life(t, 4.06), 90)
    spr(w, A + "plant", 790, TABLE + 40, 820, life(t, 4.26))
    sparkles(w, t, 4.4, 790, 760, 300, 9, 4)
    title(u, "UN NOUVEL ANANAS !", t, 3.54, None, y=330, color=YEL, size=120)
    return w, u


cue(3.1, "pop", 0.35)
cue(4.06, "whoosh_up", 0.25)
cue(4.26, "pop_lo", 0.4)
cue(4.4, "sparkle", 0.35)


# ============================================================ C. CHOISIS BIEN TON ANANAS (6.9 → 13.5)
AN_K = 0.95


def big_pineapple(c, t, s=1.0):
    place(c, A + "ananas", AN_BOX, AN_K, 510, 986, 540, TABLE + 40, s)


def scr_an(x, y):
    return 540 + (x - 510) * AN_K, TABLE + 40 + (y - 986) * AN_K


def s_choose(t):
    w, u = new_layers(background("table"))
    big_pineapple(w, t, life(t, 7.0))
    cx, cy = scr_an(510, 250)
    hl_ellipse(w, cx, cy, 300, 260, life(t, 9.62, 11.8))
    put(u, icon("check", 140), 880, cy - 120, life(t, 10.42, 11.8))
    tag(u, "SANS TACHES", 830, cy + 120, t, 10.9, 11.8, rot=-4, size=44)
    fx, fy = scr_an(510, 720)
    hl_ellipse(w, fx, fy, 290, 320, life(t, 12.1))
    act = -1 if t < 12.4 else 1
    pills(u, ["VERT", "MÛR", "TROP MÛR"], act, t, 12.1, None, y=470, pw=230)
    title(u, "CHOISIS BIEN", t, 6.98, 9.5, y=330)
    title(u, "FEUILLES BIEN VERTES", t, 9.62, 12.0, y=330, size=110)
    title(u, "MÛR, MAIS PAS TROP", t, 12.02, None, y=330, size=115)
    return w, u


cue(7.0, "pop_lo", 0.35)
cue(9.62, "pop_hi", 0.3)
cue(10.42, "ding", 0.3)
cue(10.9, "pop", 0.25)
cue(12.1, "pop_hi", 0.3)
cue(12.5, "tick", 0.3)


# ============================================================ D. ÉTAPE 1 : TOURNE LA TOUFFE (13.5 → 17.3)
def s_step1(t):
    w, u = new_layers(background("table"))
    place(w, A + "fruit", (300, 452, 731, 986), AN_K, 510, 986, 540, TABLE + 40)
    twist = math.sin(max(0, t - 14.66) * 12) * 18 * (1 - clamp((t - 16.2) / 0.3)) if t > 14.66 else 0
    lift = ease_out((t - 16.18) / 0.6) * 260
    X, Y = scr_an(510, 468)
    place(w, A + "couronne", CROWN_BOX, AN_K, 510, 468, X, Y - lift, rot=twist)
    if 14.66 < t < 16.3:
        # flèches circulaires = « tourne »
        d = ImageDraw.Draw(u)
        a0 = (t * 400) % 360
        for r_ in (150,):
            d.arc([X - r_, Y - 90 - r_ * 0.4, X + r_, Y - 90 + r_ * 0.4], a0, a0 + 230, fill=DARK, width=18)
            d.arc([X - r_, Y - 90 - r_ * 0.4, X + r_, Y - 90 + r_ * 0.4], a0, a0 + 230, fill=YEL, width=10)
    put(u, num_badge("1", 160), 190, 560, life(t, 13.62, 14.6))
    title(u, "ÉTAPE 1", t, 13.62, 14.6, y=330)
    title(u, "TOURNE LA TOUFFE", t, 14.66, None, y=330, size=125)
    return w, u


cue(13.62, "rise", 0.25)
cue(14.7, "stir", 0.35)
cue(15.4, "stir", 0.3)
cue(16.2, "pop_lo", 0.4)


# ============================================================ E. ÉTAPE 2 : RETIRE LES PETITES FEUILLES (17.3 → 22.4)
HK = 1.05     # échelle de la tête dans les gros plans
HX, HY = 540, 1200


def s_step2(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("2", 160), 190, 560, life(t, 17.42, 18.3))
    title(u, "ÉTAPE 2", t, 17.42, 18.2, y=330)
    if t < 18.9:
        place(w, A + "couronne", CROWN_BOX, HK, 510, 468, HX, HY, life(t, 17.35))
    else:
        head(w, HX, HY, HK)
        # petites feuilles qui tombent
        k = t - 18.9
        if k < 1.2:
            r = np.random.default_rng(3)
            im = asset(A + "couronne")
            strip = im.crop((0, im.height - 70, im.width, im.height))
            for i in range(6):
                piece = strip.crop((i * strip.width // 6, 0, (i + 1) * strip.width // 6, strip.height))
                piece = piece.resize((int(piece.width * HK), int(piece.height * HK)))
                piece = piece.rotate(r.uniform(-200, 200) * k, expand=True)
                x = HX - 200 * HK + i * 75 * HK + (i - 2.5) * 140 * k
                y = HY - 60 + 1100 * k * k - 120 * k
                paste(w, piece, x - piece.width / 2, y - piece.height / 2)
        base_top = HY - 45 * HK
        measure(u, HX + 260, base_top - 40, HY + 4, "2-3 cm", life(t, 20.62))
        hl_ellipse(w, HX, HY - 30, 170, 80, life(t, 20.0))
    title(u, "RETIRE LES PETITES FEUILLES", t, 18.26, None, y=330, size=90)
    return w, u


cue(17.42, "rise", 0.25)
cue(18.9, "crunch", 0.35)
cue(20.0, "pop_hi", 0.3)
cue(20.62, "tick", 0.3)


# ============================================================ F. PETIT SECRET : SÉCHER 2-3 JOURS (22.4 → 26.4)
def s_dry(t):
    w, u = new_layers(background("table"))
    rot = clamp((t - 25.5) / 0.6)
    head(w, 540, TABLE - 40, 0.9, life(t, 22.5), rot=90 if False else 0, rotten=rot)
    put(u, icon("lightbulb", 150), 190, 560, life(t, 22.54, 23.4), math.sin(t * 4) * 5)
    act = -1 if t < 24.4 else (0 if t < 24.6 else (1 if t < 24.8 else 2))
    pills(u, ["J1", "J2", "J3"], act, t, 24.3, 25.3, y=520, pw=150)
    put(u, icon("sun", 150), 880, 560, life(t, 23.94, 25.3), t * 25)
    put(u, icon("cross", 170), 840, 640, life(t, 25.8))
    if t > 25.9:
        flies(w, t, 25.9, None, 540, TABLE - 420, 200)
    title(u, "PETIT SECRET", t, 22.54, 23.4, y=330)
    title(u, "LAISSE SÉCHER", t, 23.5, 25.25, y=330)
    title(u, "SINON ELLE POURRIT", t, 25.3, None, y=330, color=RED, size=115)
    return w, u


cue(22.5, "sparkle", 0.3)
cue(24.4, "tick", 0.3)
cue(24.6, "tick", 0.3)
cue(24.8, "tick", 0.3)
cue(25.5, "squish", 0.3)


# ============================================================ G. ÉTAPE 3 : VERRE D'EAU (26.4 → 32.2)
GX, GW, GH, GWATER = 540, 470, 640, 0.55
HEAD_K = 0.78


def glass_head(c, t, roots_g=None, rotten=0.0, water_lvl=GWATER, s=1.0):
    glass_back(c, GX, TABLE, GW, GH, s)
    base = TABLE - 26 - (GH - 26) * GWATER + 50   # la tête reste fixe, seule l'eau bouge
    if roots_g is None:
        head(c, GX, base, HEAD_K, s)
    else:
        head_roots(c, GX, base, HEAD_K, roots_g, s, rotten)
    glass_front(c, GX, TABLE, water_lvl, t, GW, GH, s)


def s_step3(t):
    w, u = new_layers(background("table"))
    lvl = GWATER
    if 30.98 < t < 32.0:
        lvl = GWATER * (1 - 0.8 * math.sin(math.pi * (t - 30.98) / 1.02))
    glass_head(w, t, water_lvl=lvl, s=life(t, 26.5))
    put(u, num_badge("3", 160), 190, 560, life(t, 26.5, 27.3))
    put(u, icon("thermo", 150), 190, 620, life(t, 29.74))
    put(u, icon("sun", 160), 890, 600, life(t, 30.18), t * 25)
    title(u, "ÉTAPE 3", t, 26.5, 27.3, y=330)
    title(u, "LA BASE DANS L'EAU", t, 27.34, 29.6, y=330, size=115)
    title(u, "AU CHAUD & À LA LUMIÈRE", t, 29.74, 30.9, y=330, size=95)
    title(u, "CHANGE L'EAU", t, 30.98, None, y=330)
    return w, u


cue(26.5, "rise", 0.25)
cue(26.6, "pop", 0.3)
cue(27.6, "splash", 0.35)
cue(29.74, "pop_hi", 0.3)
cue(30.18, "sparkle", 0.25)
cue(31.0, "pour", 0.35)


# ============================================================ H. DES RACINES (32.2 → 35.1)
def s_roots(t):
    w, u = new_layers(background("table"))
    glass_head(w, t, roots_g=ease_out((t - 33.6) / 1.2))
    act = -1 if t < 32.6 else (0 if t < 32.9 else (1 if t < 33.2 else 2))
    pills(u, ["S1", "S2", "S3"], act, t, 32.4, None, y=520, pw=150)
    sparkles(w, t, 34.4, GX, TABLE - 220, 220, 8, 5)
    title(u, "DES RACINES !", t, 33.86, None, y=330, color=YEL, size=150)
    return w, u


cue(32.6, "tick", 0.3)
cue(32.9, "tick", 0.3)
cue(33.2, "tick", 0.3)
cue(33.86, "rise", 0.3)
cue(34.42, "success", 0.35)


# ============================================================ I. ÉTAPE 4 : EN POT (35.1 → 43.5)
POT_TOP = TABLE - 330


def potted(c, s=1.0, k=0.8, sink=0.0):
    head(c, 540, POT_TOP + 40 + sink, k, s)
    pot(c, 540, POT_TOP, 420, 330)


def s_step4(t):
    w, u = new_layers(background("table"))
    dropin = ease_out((t - 36.06) / 0.5)
    if t < 36.06:
        pot(w, 540, POT_TOP, 420, 330)
    else:
        head(w, 540, lerp(POT_TOP - 400, POT_TOP + 40, dropin), 0.8)
        pot(w, 540, POT_TOP, 420, 330)
    put(u, num_badge("4", 160), 190, 560, life(t, 35.2, 36.0))
    put(u, icon("sun", 150), 200, 620, life(t, 40.62), t * 25)
    put(u, icon("thermo", 150), 880, 620, life(t, 41.54))
    if t > 42.3:
        spout = (380, POT_TOP - 200)
        cx_, cy_ = can_center_for_spout(spout[0], spout[1], 280, 38)
        spr(w, "poireau/watering_can", cx_, cy_, 280, life(t, 42.3), rot=-38, shadow=False, anchor="center")
        for i in range(2):
            tt = t - 42.6 - i * 0.35
            if 0 < tt < 0.5:
                put(w, icon("drop", 44), spout[0] + 10 + 150 * tt / 0.5, spout[1] + 20 + 200 * (tt / 0.5) ** 2, 1)
    title(u, "ÉTAPE 4", t, 35.2, 36.0, y=330)
    title(u, "TERRE DRAINANTE", t, 36.06, 39.0, y=330, size=125)
    title(u, "LUMIÈRE & CHALEUR", t, 40.14, 42.3, y=330, size=115)
    title(u, "ARROSAGE LÉGER", t, 42.38, None, y=330, size=125)
    return w, u


cue(35.2, "rise", 0.25)
cue(36.1, "whoosh", 0.25)
cue(36.55, "thud", 0.4)
cue(40.62, "sparkle", 0.25)
cue(41.54, "pop_hi", 0.3)
cue(42.6, "plop", 0.25)


# ============================================================ J. ATTENTION : TROP D'EAU (43.5 → 46.7)
SOIL = 900


def s_too_wet(t):
    w, u = new_layers(background("none", SOIL, darken=0.3 * fade(t, 44.6, None, 0.6)))
    wet = ease_io((t - 44.66) / 1.0)
    rot = ease_io((t - 45.46) / 0.8)
    head_roots(w, 540, SOIL + 30, 0.85, 1.0, 1.0, rotten=rot)
    water(w, lerp(H + 40, SOIL + 60, wet), t, 0.42)
    put(u, icon("nosign", 200), 860, 560, life(t, 44.66))
    put(u, icon("drop", 110), 860, 560, life(t, 44.66))
    title(u, "ATTENTION !", t, 43.66, 44.6, y=330, color=RED)
    title(u, "TROP D'EAU = POURRITURE", t, 44.66, None, y=330, color=RED, size=95)
    return w, u


cue(43.66, "alert2", 0.4)
cue(44.66, "pour", 0.3)
cue(45.5, "squish", 0.3)


# ============================================================ K. PAS DE FLEUR AU BOUT DE 2 ANS ? (46.7 → 53.8)
def bag(c, x0, x1, top, bottom, a=1.0):
    if a <= 0.01:
        return
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([x0, top, x1, bottom], radius=120, fill=(230, 240, 248, int(70 * a)),
                        outline=(255, 255, 255, int(220 * a)), width=6)
    d.line([(x0 + 40, top + 80), (x0 + 60, bottom - 120)], fill=(255, 255, 255, int(150 * a)), width=14)
    d.line([(x1 - 50, top + 140), (x1 - 40, top + 360)], fill=(255, 255, 255, int(110 * a)), width=8)
    c.alpha_composite(ov)


def gas(c, x, y, t, a=1.0):
    if a <= 0.01:
        return
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for k in range(3):
        ph = (t * 0.8 + k / 3) % 1
        x0 = x + (k - 1) * 60 - ph * 160
        pts = [(x0 - i * 10, y - ph * 200 - i * 6 + 14 * math.sin(i / 2 + t * 4 + k)) for i in range(12)]
        al = int(230 * a * math.sin(math.pi * ph))
        d.line(pts, fill=(29, 43, 31, al), width=14, joint="curve")
        d.line(pts, fill=(170, 220, 120, al), width=7, joint="curve")
    c.alpha_composite(ov)


def s_bloom(t):
    w, u = new_layers(background("table"))
    potted(w, 1.0, 1.0)
    if t > 49.4:
        spr(w, A + "pomme", 860, TABLE + 20, 230, life(t, 49.42))
    bag(w, 250, 1010, POT_TOP - 560, TABLE + 30, fade(t, 51.18, None, 0.5))
    gas(w, 850, TABLE - 230, t, fade(t, 53.9, None, 0.4))
    put(u, icon("question", 170), 860, 620, life(t, 47.0, 49.3), math.sin(t * 5) * 8)
    act = -1 if t < 48.9 else 1
    pills(u, ["1 AN", "2 ANS"], act, t, 48.7, 49.4, y=520, pw=170)
    title(u, "PAS DE FLEUR ?", t, 47.26, 49.3, y=330)
    title(u, "UNE POMME MÛRE", t, 49.42, 51.1, y=330, size=125)
    title(u, "+ UN SAC TRANSPARENT", t, 51.18, None, y=330, size=100)
    return w, u


cue(47.26, "pop", 0.3)
cue(48.9, "tick", 0.3)
cue(49.42, "pop_lo", 0.4)
cue(51.18, "whoosh", 0.25)


# ============================================================ L. LE GAZ DÉCLENCHE LA FLORAISON (53.8 → 57.6)
def s_gas(t):
    w, u = new_layers(background("table"))
    grow = ease_io((t - 55.8) / 0.6)
    if grow < 1:
        potted(w, 1.0, 1.0)
        spr(w, A + "pomme", 860, TABLE + 20, 230, 1 - grow)
        bag(w, 250, 1010, POT_TOP - 560, TABLE + 30, 1 - grow)
        gas(w, 850, TABLE - 230, t, 1 - grow)
    if grow > 0:
        spr(w, A + "plant", 540, TABLE + 40, 1050, grow)
        sparkles(w, t, 56.0, 540, 600, 340, 10, 9)
    put(u, text_img("GAZ", F_TITLE, 90, YEL, 10, DARK, 8, DARK), 780, 560, life(t, 54.06, 55.7), -6)
    title(u, "LE GAZ DE LA POMME", t, 53.9, 55.7, y=330, size=115)
    title(u, "FLORAISON !", t, 55.82, None, y=330, color=YEL, size=150)
    return w, u


cue(54.06, "pop_hi", 0.3)
cue(55.82, "rise", 0.3)
cue(56.0, "success", 0.35)


# ============================================================ M. PATIENCE : 2-3 ANS (57.6 → 62.8)
def s_patience(t):
    w, u = new_layers(background("table"))
    spr(w, A + "plant", 540, TABLE + 40, 1050)
    act = -1 if t < 59.9 else (0 if t < 60.2 else (1 if t < 60.5 else 2))
    pills(u, ["1 AN", "2 ANS", "3 ANS"], act, t, 59.7, None, y=500, pw=170)
    title(u, "PATIENCE…", t, 57.74, 59.6, y=330)
    title(u, "LE PREMIER FRUIT", t, 61.26, None, y=330, size=125, color=YEL)
    hl_ellipse(w, 540 + (612 - 627) * 1050 / 1241, TABLE + 40 - (1247 - 465) * 1050 / 1241, 120, 150, life(t, 61.3))
    return w, u


cue(57.74, "pop", 0.25)
cue(59.9, "tick", 0.3)
cue(60.2, "tick", 0.3)
cue(60.5, "tick", 0.3)
cue(61.3, "pop_hi", 0.3)


# ============================================================ N. QUELLE FIERTÉ (62.8 → 65.95)
def s_proud(t):
    w, u = new_layers(background("table"))
    name = A + ("ananas_croque" if t > 64.25 else "ananas")
    spr(w, name, 540, TABLE + 40, 1000, life(t, 62.9))
    if t > 64.2:
        particles(w, t, 64.2, 720, 700, 12, 3, col=(240, 200, 80), size=10, up=400)
    sparkles(u, t, 63.6, 540, 700, 380, 10, 6)
    title(u, "QUELLE FIERTÉ !", t, 63.58, None, y=300, color=YEL, size=150)
    return w, u


cue(62.9, "pop_lo", 0.35)
cue(63.6, "sparkle", 0.3)
cue(64.2, "crunch", 0.5)


# ============================================================ O. CTA (65.95 → fin)
@lru_cache(None)
def logo_img(size=400):
    im = Image.open(os.path.join(ROOT, "assets", "images", "ananas", "logo.jpg")).convert("RGBA").resize((size, size), Image.LANCZOS)
    m = aa(size, size, lambda d, k, _: d.rounded_rectangle([0, 0, size * k - 1, size * k - 1], radius=44 * k, fill=WHITE))
    im.putalpha(m.getchannel("A"))
    S = size + 16
    out = aa(S, S, lambda d, k, _: d.rounded_rectangle([0, 0, S * k - 1, S * k - 1], radius=50 * k, fill=DARK))
    out.alpha_composite(im, (8, 8))
    return out


def s_cta(t):
    w, u = new_layers(background("table"))
    spr(w, A + "ananas", 540, TABLE + 40, 420, life(t, 66.0))
    clicked = t > 66.6
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 66.55) / 0.15))
    put(u, btn, 540, 300, life(t, 66.1) * press)
    if t > 66.25:
        k = ease_out((t - 66.25) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(360), 540, 590, life(t, 66.74, dur=0.45))
    sparkles(u, t, 66.8, 540, 590, 240, 10, 12)
    return w, u


cue(66.0, "pop_lo", 0.3)
cue(66.1, "pop_hi", 0.3)
cue(66.58, "click", 0.55)
cue(66.65, "bell", 0.35)
cue(66.8, "sparkle", 0.3)

if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video), (VID_END, 3.0, s_error)]
else:
    _intro = [(0.0, 3.0, s_throw)]

SCENES = _intro + [
    (3.0, 6.9, s_new),
    (6.9, 13.5, s_choose),
    (13.5, 17.3, s_step1),
    (17.3, 22.4, s_step2),
    (22.4, 26.4, s_dry),
    (26.4, 32.2, s_step3),
    (32.2, 35.1, s_roots),
    (35.1, 43.5, s_step4),
    (43.5, 46.7, s_too_wet),
    (46.7, 53.8, s_bloom),
    (53.8, 57.6, s_gas),
    (57.6, 62.8, s_patience),
    (62.8, 65.95, s_proud),
    (65.95, 99.0, s_cta),
]

TRAPS = [(1, 13.6, 17.3), (2, 17.4, 26.4), (3, 26.5, 35.1), (4, 35.2, 46.7)]

if HAS_VIDEO:
    CUES[:] = [c for c in CUES if c[0] >= VID_END - 0.05]
