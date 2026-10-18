"""Storyboard « Bouturer les aromatiques » (voix : assets/audio/aromatiques/voix.mp3).

Intro : la vidéo fournie (assets/video/intro_thym.mp4) telle quelle, sans texte, son coupé (seule la voix).
Puis motion design : romarin fourni (tige), thym (image de la vidéo fournie), lavande, sauge, sarriette, menthe
(Open Images), logo « Les Potagers de Louis » fourni pour la fin.
"""
import math
import os
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (ROOT, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, spr, put, paste, title, life, fade,
                 ease_out, ease_in, ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse,
                 measure, roots, particles, text_img, asset, aa, glass_back, glass_front, window_img, F_TITLE,
                 F_BLACK)
from scenes import TABLE, new_layers, drop, sparkles, falling
from scenes_arrosage import can_center_for_spout

CUES = []
NO_CAPTION_UNTIL = 2.2   # pas de sous-titres pendant la vidéo d'intro


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


A = "aromatiques/"
IMG_DIR = os.path.join(ROOT, "assets", "images", "aromatiques")
VIDEO = os.path.join(ROOT, "assets", "video", "intro_thym.mp4")
VID_END = 2.2
FPS = 30


# ------------------------------------------------------------- vidéo d'intro (brute)
@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_aromatiques_intro")
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


# ------------------------------------------------------------- vignettes photo
@lru_cache(None)
def card_img(name, size=300):
    path = os.path.join(IMG_DIR, name)
    pad, bottom = 16, 16
    S = size + pad * 2
    card = aa(S, S + bottom, lambda d, k, _: (
        d.rounded_rectangle([0, 6 * k, S * k - 1, (S + bottom) * k - 1], radius=20 * k, fill=(60, 40, 25, 90)),
        d.rounded_rectangle([0, 0, S * k - 1, (S + bottom - 6) * k - 1], radius=20 * k, fill=DARK),
        d.rounded_rectangle([5 * k, 5 * k, (S - 5) * k, (S + bottom - 11) * k], radius=16 * k, fill=WHITE)))
    if path.endswith(".png"):
        ph = Image.new("RGBA", (size, size), (238, 230, 214, 255))
        im = Image.open(path).convert("RGBA")
        im.thumbnail((int(size * 0.92), int(size * 0.92)), Image.LANCZOS)
        ph.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    else:
        ph = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
    m = aa(size, size, lambda d, k, _: d.rounded_rectangle([0, 0, size * k - 1, size * k - 1], radius=12 * k, fill=WHITE))
    ph.putalpha(m.getchannel("A"))
    card.alpha_composite(ph, (pad, pad))
    return card


def card(c, name, x, y, t, t0, t1=None, rot=0.0, size=300, label=None):
    s = life(t, t0, t1)
    if s <= 0.01:
        return
    put(c, card_img(name, size), x, y, s, rot + math.sin((t - t0) * 2) * 1.5)
    if label:
        put(c, text_img(label, F_TITLE, 58, YEL, 8, DARK, 6, DARK), x, y + size / 2 + 40, s, -3)


# ------------------------------------------------------------- tige de romarin
ROM_H = 1172           # hauteur de romarin.png
STRIP = 720            # début de la partie effeuillée


def sprig(c, cx, bottom, h, s=1.0, stripped=0.0, shadow=False, rot=0.0):
    """Tige de romarin (photo) posée par sa base. stripped : 0 = entière, 1 = feuilles du bas retirées."""
    if s <= 0.01:
        return
    if stripped < 1:
        spr(c, A + "romarin", cx, bottom, h, s, shadow=shadow, rot=rot)
    else:
        spr(c, A + "romarin_effeuille", cx, bottom, h, s, shadow=shadow, rot=rot)


def stripped_leaves_fall(c, cx, bottom, h, t, t0):
    """Les aiguilles du bas se détachent (moitié gauche / droite) et tombent."""
    k = t - t0
    if k < 0 or k > 1.2:
        return
    im = asset(A + "romarin_feuilles_bas")
    sc = h / ROM_H
    img = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
    left0 = cx - img.width / 2
    top0 = bottom - img.height
    half = img.width // 2
    for part, sg, ox in ((img.crop((0, 0, half, img.height)), -1, 0), (img.crop((half, 0, img.width, img.height)), 1, half)):
        r = part.rotate(sg * -50 * k, expand=True, resample=Image.BICUBIC)
        if k > 0.6:
            r.putalpha(r.getchannel("A").point(lambda v, f=max(0.0, 1 - (k - 0.6) / 0.6): int(v * f)))
        px = left0 + ox + part.width / 2 + sg * 420 * k
        py = top0 + img.height / 2 - 120 * k + 1300 * k * k
        paste(c, r, px - r.width / 2, py - r.height / 2)


# ============================================================ 0. VIDÉO (0 → 2.2)

# ============================================================ A. UNE PLANTE = 10 (2.2 → 5.8)
def s_ten(t):
    w, u = new_layers(background("table"))
    if t < 4.0:
        sprig(w, 540, TABLE + 40, 980, life(t, 2.25, dur=0.4), shadow=True)
        title(u, "1 SEULE PLANTE", t, 2.86, 4.0, y=300, size=125)
    else:
        for i in range(10):
            col, row = i % 5, i // 5
            x = 150 + col * 195
            y = 1000 + row * 360
            sprig(w, x, y + 40, 330, life(t, 4.05 + i * 0.07), shadow=True)
        title(u, "= 10 PLANTS !", t, 4.58, None, y=300, color=YEL, size=150)
        sparkles(u, t, 5.05, 540, 820, 420, 10, 3)
    return w, u


cue(2.25, "whoosh_up", 0.35)
cue(2.3, "pop_lo", 0.4)
cue(2.86, "pop", 0.3)
for _i in range(10):
    cue(4.05 + _i * 0.07, "pop_hi" if _i % 2 else "pop", 0.25)
cue(5.02, "success", 0.4)


# ============================================================ B. THYM, ROMARIN, LAVANDE, SAUGE, SARRIETTE (5.8 → 11.0)
CARDS = [("thym.jpg", "THYM", 5.94), ("romarin.png", "ROMARIN", 6.34), ("lavande.jpg", "LAVANDE", 7.22),
         ("sauge.png", "SAUGE", 7.98), ("sarriette.jpg", "SARRIETTE", 8.5)]


def s_herbs(t):
    """Les photos s'empilent une à une au centre, le titre change avec chaque plante."""
    w, u = new_layers(background("table"))
    out = 9.3
    rots = [-6, 5, -3, 6, -2]
    offs = [(-40, 30), (35, 0), (-25, -20), (30, 25), (0, -10)]
    for i, (name, lab, t0) in enumerate(CARDS):
        t1 = out
        card(w, name, 540 + offs[i][0], 880 + offs[i][1], t, t0, t1, rots[i], 560)
        nxt = CARDS[i + 1][2] if i + 1 < len(CARDS) else out
        title(u, lab, t, t0, nxt, y=300, size=170)
    if t > 9.3:
        pills(u, ["SEPT", "OCT", "NOV"], 1 if t > 9.7 else -1, t, 9.45, None, y=800)
        title(u, "C'EST MAINTENANT !", t, 9.42, None, y=560, color=YEL, size=125)
        put(u, icon("check", 170), 540, 1100, life(t, 10.42), math.sin(t * 5) * 5)
    return w, u


for _n, _l, _t0 in CARDS:
    cue(_t0, "pop", 0.4)
cue(9.35, "whoosh", 0.25)
cue(9.45, "pop_hi", 0.3)
cue(9.7, "tick", 0.35)
cue(10.42, "success", 0.4)


# ============================================================ C. LA MENTHE : UN VERRE D'EAU (11.0 → 16.4)
MINT_W, MINT_H = 775, 690
MINT_STEM = (560, 690)   # point d'attache de la tige dans menthe_top.png


def mint_in_glass(c, t, gx, base, root_g, s=1.0):
    gw, gh = 420, 520
    glass_back(c, gx, base, gw, gh)
    if root_g > 0.01:
        roots(c, gx, base - 130, root_g, 7, spread=80, length=170, n=12)
    d = ImageDraw.Draw(c)
    top = base - gh - 60
    d.line([(gx, top), (gx + 3, base - 110)], fill=(60, 96, 40), width=18)
    d.line([(gx, top), (gx + 3, base - 110)], fill=(116, 160, 74), width=11)
    mh = 380 * s
    k = mh / MINT_H
    cx = gx - (MINT_STEM[0] - MINT_W / 2) * k
    spr(c, A + "menthe_top", cx, top + 30 + (MINT_H - MINT_STEM[1]) * k, mh, shadow=False)
    glass_front(c, gx, base, 0.55, t, gw, gh)


def s_mint(t):
    w, u = new_layers(background("table"))
    if t < 13.85:
        spr(w, A + "menthe_top", 540, TABLE - 40, 700, life(t, 11.22, dur=0.4), shadow=True)
        title(u, "ET LA MENTHE ?", t, 11.38, 12.6, y=300)
        title(u, "ENCORE PLUS SIMPLE", t, 12.7, None, y=300, size=115)
    else:
        mint_in_glass(w, t, 540, TABLE + 10, ease_out((t - 15.0) / 1.0), life(t, 13.9))
        title(u, "UN VERRE D'EAU", t, 13.9, 15.1, y=300, size=125)
        title(u, "DES RACINES !", t, 15.18, None, y=300, color=YEL, size=135)
        sparkles(u, t, 15.3, 540, TABLE - 160, 220, 8, 6)
    return w, u


cue(11.0, "whoosh_up", 0.3)
cue(11.22, "pop_lo", 0.4)
cue(12.7, "pop_hi", 0.3)
cue(13.85, "whoosh", 0.25)
cue(13.95, "splash", 0.4)
cue(15.18, "rise", 0.3)
cue(15.3, "sparkle", 0.35)


# ============================================================ D. ÉTAPE 1 : 10 CM SANS FLEURS (16.4 → 20.05)
SP_X, SP_B, SP_H = 540, TABLE + 20, 1000


def s_step1(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("1", 160), 200, 560, life(t, 16.5, 17.6))
    title(u, "ÉTAPE 1", t, 16.5, 17.4, y=300)
    if t < 19.15:
        sprig(w, SP_X, SP_B, SP_H, life(t, 16.55), shadow=True)
        if 17.4 < t < 18.3:
            snip = abs(math.sin((t - 17.4) * 9)) * 14
            spr(w, "bouture/secateur", SP_X + 117, SP_B - 150 + 74, 230, rot=-snip, shadow=False,
                anchor="center")
        measure(u, 820, SP_B - SP_H + 20, SP_B - 10, "10 cm", life(t, 18.38))
        title(u, "UNE TIGE DE 10 CM", t, 17.46, None, y=350, size=115)
    else:
        sprig(w, 330, SP_B, 760, shadow=True)
        card(w, "lavande.jpg", 780, 900, t, 19.2, None, 5, 300)
        put(u, icon("nosign", 340), 780, 900, life(t, 19.35))
        put(u, icon("check", 150), 330, 540, life(t, 19.5))
        title(u, "SANS FLEURS", t, 19.22, None, y=350, color=RED)
    return w, u


cue(16.5, "rise", 0.3)
cue(16.55, "pop", 0.3)
cue(17.5, "chop", 0.55)
cue(18.38, "tick", 0.35)
cue(19.15, "whoosh", 0.25)
cue(19.25, "pop", 0.35)
cue(19.35, "fail", 0.3)


# ============================================================ E. ÉTAPE 2 : RETIRE LES FEUILLES DU BAS (20.05 → 22.2)
def s_step2(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("2", 160), 200, 560, life(t, 20.14, 21.0))
    title(u, "ÉTAPE 2", t, 20.14, 20.9, y=300)
    stripped = 1.0 if t > 21.0 else 0.0
    sprig(w, SP_X, SP_B, SP_H, 1.0, stripped, shadow=True)
    stripped_leaves_fall(w, SP_X, SP_B, SP_H, t, 21.0)
    by = SP_B - SP_H * (ROM_H - STRIP) / ROM_H / 2
    hl_ellipse(w, SP_X, by, 200, SP_H * (ROM_H - STRIP) / ROM_H / 2 + 30, life(t, 21.42))
    title(u, "FEUILLES DU BAS", t, 21.0, None, y=350, size=120)
    return w, u


cue(20.14, "rise", 0.3)
cue(21.0, "crunch", 0.45)
cue(21.05, "whoosh", 0.2)
cue(21.42, "pop_hi", 0.3)


# ============================================================ F. ÉTAPE 3 : TERREAU DRAINANT (22.2 → 25.3)
SOIL = 1000


@lru_cache(None)
def perlite_layer():
    r = np.random.default_rng(5)
    im = Image.new("RGBA", (W, H - SOIL), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(900):
        x, y = r.uniform(0, W), r.uniform(20, H - SOIL)
        rad = r.uniform(5, 11)
        g = int(r.uniform(210, 248))
        d.ellipse([x - rad, y - rad * 0.8, x + rad, y + rad * 0.8], fill=(g, g, g - 6), outline=(150, 150, 145), width=2)
    return im


def soil_scene(t, mix=1.0, warm=0.0):
    w, u = new_layers(background("none", SOIL, warm=warm))
    if mix > 0.01:
        p = perlite_layer().copy()
        p.putalpha(p.getchannel("A").point(lambda v: int(v * mix)))
        w.alpha_composite(p, (0, SOIL))
    return w, u


def planted(c, cx, h=900, k=1.0, s=1.0, root_g=0.0, seed=2):
    """Tige effeuillée plantée : la partie nue est sous terre."""
    bury = h * (ROM_H - STRIP) / ROM_H * 0.6
    bottom = lerp(SOIL - 40, SOIL + bury, k)
    if root_g > 0.01:
        roots(c, cx, bottom - 4, root_g, seed, spread=50, length=200 * s, n=11)
    sprig(c, cx, bottom, h, s, 1.0)
    # partie enterrée de la tige rendue visible dans la coupe (sinon brun sur brun)
    if s > 0.5 and bottom > SOIL + 6:
        sw = max(6, 26 * h / ROM_H * s)
        d = ImageDraw.Draw(c)
        x = cx + 4 * h / ROM_H
        d.line([(x, SOIL + 6), (x, bottom - 2)], fill=(70, 46, 28), width=int(sw + 5))
        d.line([(x, SOIL + 6), (x, bottom - 2)], fill=(206, 168, 118), width=int(sw))
        d.line([(x - sw * 0.2, SOIL + 6), (x - sw * 0.2, bottom - 4)], fill=(232, 204, 160), width=max(1, int(sw * 0.25)))
    return bottom


def s_step3(t):
    w, u = soil_scene(t, mix=ease_out((t - 24.18) / 0.5))
    put(u, num_badge("3", 160), 200, 560, life(t, 22.34, 23.2))
    title(u, "ÉTAPE 3", t, 22.34, 23.2, y=300)
    k = ease_io((t - 23.3) / 0.6)
    planted(w, 540, 900, k, life(t, 22.4))
    if k > 0.5:
        particles(w, t, 23.75, 540, SOIL, 12, 4, col=(150, 110, 70), size=9, up=340)
    if t > 24.6:
        for i in range(8):
            tt = (t - 24.6 - i * 0.12) % 1.0
            x = 200 + i * 95
            put(w, icon("drop", 40), x, SOIL + 60 + tt * 800, 1, 0, 1 - tt)
        put(u, icon("arrow_down", 120), 900, 1300 + 25 * math.sin(t * 7), life(t, 24.62))
    title(u, "TERREAU DRAINANT", t, 23.9, None, y=350, size=120)
    return w, u


cue(22.34, "rise", 0.3)
cue(22.4, "pop", 0.3)
cue(23.35, "whoosh", 0.25)
cue(23.75, "crunch", 0.45)
cue(24.18, "pop_hi", 0.3)
cue(24.6, "plop", 0.25)


# ============================================================ G. PETIT SECRET : ARROSE À PEINE (25.3 → 30.0)
CAN = "poireau/watering_can"


def s_secret(t):
    w, u = soil_scene(t, mix=1.0)
    foot = planted(w, 540, 900, 1.0)
    if t < 28.3:
        put(u, icon("lightbulb", 160), 540, 520, life(t, 25.42, 26.3), math.sin(t * 4) * 5)
        title(u, "PETIT SECRET", t, 25.42, 26.4, y=350)
        if t > 26.3:
            k = ease_out((t - 26.3) / 0.35)
            spout = (lerp(-200, 400, k), SOIL - 260)
            cx_, cy_ = can_center_for_spout(spout[0], spout[1], 300, 38)
            spr(w, CAN, cx_, cy_, 300, rot=-38, shadow=False, anchor="center")
            for i in range(3):
                tt = t - 26.7 - i * 0.35
                if 0 < tt < 0.55:
                    y = spout[1] + 20 + (SOIL - spout[1] - 10) * (tt / 0.55) ** 2
                    put(w, icon("drop", 46), spout[0] + 10 + 120 * (tt / 0.55), y, 1, 0, 1)
        title(u, "ARROSE À PEINE", t, 26.46, None, y=350, color=YEL, size=125)
    else:
        # pieds mouillés : flaque autour de la base
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        a = int(170 * fade(t, 28.4, None, 0.4))
        d.ellipse([400, foot - 70, 690, foot + 60], fill=(80, 150, 210, a))
        d.ellipse([414, foot - 60, 676, foot + 50], outline=(210, 236, 250, a), width=4)
        w.alpha_composite(ov)
        planted(w, 540, 900, 1.0)
        put(u, icon("nosign", 260), 545, foot, life(t, 28.6))
        title(u, "PIEDS MOUILLÉS", t, 28.42, None, y=350, color=RED, size=125)
    return w, u


cue(25.42, "sparkle", 0.3)
cue(25.5, "pop", 0.3)
cue(26.3, "whoosh", 0.2)
cue(26.7, "plop", 0.25)
cue(27.05, "plop", 0.2)
cue(28.42, "splash", 0.3)
cue(28.6, "fail", 0.35)


def pot(c, cx, top, w=360, h=330):
    """Pot en terre cuite vu de face, terreau visible en haut."""
    d = ImageDraw.Draw(c)
    bw = w * 0.74
    d.ellipse([cx - w / 2 - 6, top + h - 18, cx + w / 2 + 6, top + h + 30], fill=(80, 52, 32, 110))
    d.polygon([(cx - w / 2, top + 30), (cx + w / 2, top + 30), (cx + bw / 2, top + h), (cx - bw / 2, top + h)],
              fill=(186, 100, 62))
    d.polygon([(cx + w * 0.18, top + 30), (cx + w / 2, top + 30), (cx + bw / 2, top + h), (cx + bw * 0.2, top + h)],
              fill=(160, 84, 52))
    d.ellipse([cx - w / 2 + 8, top - 4, cx + w / 2 - 8, top + 50], fill=(52, 36, 26))
    d.rounded_rectangle([cx - w / 2 - 18, top + 4, cx + w / 2 + 18, top + 62], radius=12, fill=(200, 112, 72))
    d.ellipse([cx - w / 2 + 6, top - 14, cx + w / 2 - 6, top + 30], fill=(56, 38, 27))


# ============================================================ H. ÉTAPE 4 : À L'ABRI DU FROID (30.0 → 34.0)
def snow_window(c, t, x0, y0, w_, h_):
    r = np.random.default_rng(4)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(40):
        x = x0 + r.uniform(0, w_) + 12 * math.sin(t * 2 + i)
        y = y0 + (r.uniform(0, h_) + t * r.uniform(60, 120)) % h_
        rad = r.uniform(4, 8)
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(255, 255, 255, 230))
    c.alpha_composite(ov)


def s_step4(t):
    w, u = new_layers(background("table"))
    put(w, window_img(), 540, 760, life(t, 30.1))
    if t > 30.3:
        snow_window(w, t, 270, 410, 540, 620)
    sprig(w, 540, TABLE - 300 + 150, 560, life(t, 30.2), 1.0)
    pot(w, 540, TABLE - 300, 360, 300)
    put(u, icon("snow", 150), 180, 520, life(t, 30.9))
    put(u, icon("thermo", 150), 900, 520, life(t, 31.0))
    put(u, num_badge("4", 160), 830, 1430, life(t, 30.1, 31.0))
    title(u, "ÉTAPE 4", t, 30.1, 30.85, y=300)
    title(u, "À L'ABRI DU FROID", t, 30.9, 32.3, y=350, size=120)
    act = -1 if t < 32.6 else min(3, int((t - 32.6) / 0.3))
    pills(u, ["DÉC", "JANV", "FÉV", "MARS"], act, t, 32.4, None, y=1440, pw=170)
    title(u, "PATIENCE…", t, 32.38, None, y=350)
    return w, u


cue(30.06, "rise", 0.3)
cue(30.1, "pop", 0.3)
cue(30.9, "pop_hi", 0.3)
cue(32.4, "pop", 0.25)
for _k in range(4):
    cue(32.6 + _k * 0.3, "tick", 0.3)


# ============================================================ I. NOUVEAUX PLANTS GRATUITS (34.0 → 37.05)
def s_new(t):
    w, u = soil_scene(t, mix=1.0, warm=fade(t, 34.1, None, 0.5))
    for i, x in enumerate((220, 540, 860)):
        planted(w, x, 620, 1.0, life(t, 34.2 + i * 0.15), root_g=ease_out((t - 34.4 - i * 0.15) / 0.9), seed=3 + i)
    put(u, icon("sun", 170), 880, 520, life(t, 34.1), t * 25)
    title(u, "AU PRINTEMPS…", t, 34.02, 34.85, y=300)
    title(u, "DES PLANTS GRATUITS !", t, 34.94, None, y=300, color=YEL, size=105)
    tag(u, "GRATUITS !", 560, 760, t, 36.18, rot=-4, size=58)
    sparkles(u, t, 36.2, 540, 800, 400, 9, 9)
    return w, u


cue(34.02, "whoosh_up", 0.3)
cue(34.1, "sparkle", 0.3)
for _i in range(3):
    cue(34.2 + _i * 0.15, "pop", 0.35)
cue(36.18, "success", 0.4)


# ============================================================ J. CTA + LOGO (37.05 → fin)
@lru_cache(None)
def logo_img(size=560):
    im = Image.open(os.path.join(IMG_DIR, "logo.jpg")).convert("RGBA").resize((size, size), Image.LANCZOS)
    m = aa(size, size, lambda d, k, _: d.rounded_rectangle([0, 0, size * k - 1, size * k - 1], radius=48 * k, fill=WHITE))
    im.putalpha(m.getchannel("A"))
    S = size + 16
    out = aa(S, S, lambda d, k, _: d.rounded_rectangle([0, 0, S * k - 1, S * k - 1], radius=54 * k, fill=DARK))
    out.alpha_composite(im, (8, 8))
    return out


def s_cta(t):
    w, u = new_layers(background("table"))
    for i, x in enumerate((230, 540, 850)):
        sprig(w, x, TABLE + 30, 420, life(t, 37.1 + i * 0.08), shadow=True)
    clicked = t > 37.65
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 37.6) / 0.15))
    put(u, btn, 540, 300, life(t, 37.14) * press)
    if t > 37.3:
        k = ease_out((t - 37.3) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(480), 540, 650, life(t, 39.38, dur=0.45), math.sin((t - 39.4) * 2) * 1.5)
    sparkles(u, t, 39.5, 540, 650, 300, 10, 12)
    return w, u


cue(37.1, "pop_lo", 0.3)
cue(37.14, "pop_hi", 0.35)
cue(37.62, "click", 0.6)
cue(37.7, "bell", 0.4)
cue(39.38, "rise", 0.3)
cue(39.5, "success", 0.45)

SCENES = [
    (0.0, VID_END, s_video),
    (VID_END, 5.8, s_ten),
    (5.8, 11.0, s_herbs),
    (11.0, 16.4, s_mint),
    (16.4, 20.05, s_step1),
    (20.05, 22.2, s_step2),
    (22.2, 25.3, s_step3),
    (25.3, 30.0, s_secret),
    (30.0, 34.0, s_step4),
    (34.0, 37.05, s_new),
    (37.05, 99.0, s_cta),
]

TRAPS = [(1, 16.5, 20.05), (2, 20.1, 22.2), (3, 22.25, 30.0), (4, 30.05, 34.0)]
