"""Storyboard « N'arrose pas trop tes plantes d'intérieur » (voix : assets/audio/arrosage/voix.mp3).

Même direction artistique que les vidéos ail & échalote / poireau : fond beige, table ou terre en coupe,
photos réelles détourées (monstera fourni, main, ciseaux, coco, racines), titres jaunes, badge d'étape.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, background, spr, put, title, life, fade,
                 ease_out, ease_in, ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse,
                 hline, measure, particles, text_img, water, F_TITLE, F_BLACK, aa)
from scenes import TABLE, new_layers, drop, flies, sparkles, falling

CUES = []


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


A = "arrosage/"
PLANT_H = 880
POT_X, POT_Y = 0.523, 0.84      # bas du pot dans la photo (fraction largeur / hauteur)


def plant(c, x, ground, h=PLANT_H, s=1.0, sick=True, rot=0.0, rotten=0.0, shadow=True):
    name = A + ("monstera_malade" if sick else "monstera_mieux")
    return spr(c, name, x, ground, h, s, rot=rot, rotten=rotten, shadow=shadow)


def pot_bottom(x, ground, h=PLANT_H):
    w = 824 * h / 834
    return x + (POT_X - 0.5) * w, ground - h * (1 - POT_Y)


# ------------------------------------------------------------- petits éléments dessinés
def saucer(c, cx, y, w=330, water_lvl=0.0, t=0.0):
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.ellipse([cx - w / 2 - 6, y - 34, cx + w / 2 + 6, y + 40], fill=(60, 38, 25, 120))
    d.ellipse([cx - w / 2, y - 40, cx + w / 2, y + 30], fill=(176, 92, 58))
    d.ellipse([cx - w / 2 + 14, y - 34, cx + w / 2 - 14, y + 14], fill=(140, 70, 44))
    if water_lvl > 0.01:
        ww = (w - 40) * (0.6 + 0.4 * water_lvl)
        wave = 3 * math.sin(t * 5)
        d.ellipse([cx - ww / 2, y - 28 + wave, cx + ww / 2, y + 8 + wave], fill=(110, 170, 210, int(210 * water_lvl)))
        d.arc([cx - ww / 2, y - 28 + wave, cx + ww / 2, y + 8 + wave], 190, 340, fill=(220, 240, 250, 230), width=4)
    c.alpha_composite(ov)


def air_bubbles(c, cx, cy, t, a=1.0, n=12, spread=260, seed=5):
    if a <= 0.01:
        return
    r = np.random.default_rng(seed)
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(n):
        x = cx + r.uniform(-spread, spread) + 10 * math.sin(t * 2 + i)
        y = cy + r.uniform(-spread * 0.7, spread * 0.7) + 8 * math.cos(t * 1.7 + i)
        rad = r.uniform(10, 24) * (0.85 + 0.15 * math.sin(t * 4 + i))
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(235, 245, 255, int(110 * a)),
                  outline=(255, 255, 255, int(240 * a)), width=4)
        d.ellipse([x - rad * 0.5, y - rad * 0.6, x - rad * 0.1, y - rad * 0.2], fill=(255, 255, 255, int(230 * a)))
    c.alpha_composite(ov)


def stink(c, x, y, t, a=1.0):
    if a <= 0.01:
        return
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for k in range(3):
        ph = (t * 0.8 + k / 3) % 1
        x0 = x + (k - 1) * 90
        pts = [(x0 + 22 * math.sin(i / 4 + t * 4 + k), y - i * 9 - ph * 60) for i in range(24)]
        al = int(230 * a * math.sin(math.pi * ph))
        d.line(pts, fill=(60, 90, 40, al), width=16, joint="curve")
        d.line(pts, fill=(140, 180, 80, al), width=9, joint="curve")
    c.alpha_composite(ov)


def perlite_pile(c, cx, base, w=300, s=1.0, seed=3):
    if s <= 0.01:
        return
    r = np.random.default_rng(seed)
    S = int(w * 1.1)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(420):
        u = r.uniform(-1, 1)
        hgt = (1 - u * u) * S * 0.62
        x = S / 2 + u * S * 0.47
        y = S - 6 - r.uniform(0, 1) ** 0.7 * hgt
        rad = r.uniform(6, 13)
        g = int(r.uniform(205, 250))
        d.ellipse([x - rad, y - rad * 0.8, x + rad, y + rad * 0.8], fill=(g, g, g - 6), outline=(150, 150, 145), width=2)
        d.ellipse([x - rad * 0.4, y - rad * 0.5, x, y - rad * 0.1], fill=(255, 255, 255))
    put(c, im, cx, base - S / 2 * s, s)


def pot_section(c, cx, top, w=520, h=520, t=0.0, holes=0.0, mix=0.0):
    """Pot en terre cuite vu en coupe (pour le mélange qui respire et le pot percé)."""
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    bw = w * 0.74
    d.polygon([(cx - w / 2, top), (cx + w / 2, top), (cx + bw / 2, top + h), (cx - bw / 2, top + h)], fill=(190, 104, 66))
    d.polygon([(cx - w / 2 + 26, top + 40), (cx + w / 2 - 26, top + 40), (cx + bw / 2 - 22, top + h - 26),
               (cx - bw / 2 + 22, top + h - 26)], fill=(96, 64, 42))
    d.rounded_rectangle([cx - w / 2 - 22, top - 10, cx + w / 2 + 22, top + 50], radius=12, fill=(204, 116, 76))
    if mix > 0.01:
        r = np.random.default_rng(8)
        for i in range(int(260 * mix)):
            y = r.uniform(top + 60, top + h - 30)
            fr = (y - top) / h
            half = (w / 2 - 26) * (1 - fr) + (bw / 2 - 22) * fr - 10
            x = cx + r.uniform(-half, half)
            rad = r.uniform(5, 10)
            col = (240, 240, 235) if i % 3 == 0 else ((170, 120, 70) if i % 3 == 1 else (58, 38, 26))
            d.ellipse([x - rad, y - rad * 0.8, x + rad, y + rad * 0.8], fill=col)
    if holes > 0.01:
        for k in (-0.5, 0, 0.5):
            hx = cx + k * bw * 0.6
            d.rectangle([hx - 16, top + h - 30, hx + 16, top + h + 2], fill=(232, 220, 198, int(255 * holes)))
    c.alpha_composite(ov)


# ============================================================ A. JAUNIT, RAMOLLIT… (0 → 4.15)
def s_intro(t):
    w, u = new_layers(background("table"))
    droop = 4 * math.sin(clamp((t - 1.78) / 0.6) * math.pi) * fade(t, 1.78, 2.6)
    plant(w, 540, TABLE + 60, PLANT_H, life(t, 0.0, dur=0.4), rot=droop)
    if t > 2.8:
        k = ease_out((t - 2.8) / 0.35)
        spr(w, "poireau/watering_can", lerp(1300, 880, k), 640, 300, rot=lerp(0, 30, k), shadow=False)
        falling(w, t, 3.1, None, "drop", 9, 3, 900, 40, top=680, bottom=1100)
    title(u, "ELLE JAUNIT…", t, 1.18, 1.75, y=230, size=130)
    title(u, "ELLE RAMOLLIT…", t, 1.78, 2.75, y=230, size=130)
    title(u, "ENCORE PLUS D'EAU ?", t, 2.94, None, y=230, size=110)
    return w, u


cue(0.05, "pop_lo", 0.4)
cue(1.18, "pop", 0.3)
cue(1.78, "squish", 0.3)
cue(2.85, "whoosh", 0.25)
cue(3.0, "pour", 0.4)
cue(3.82, "pop_hi", 0.3)


# ============================================================ B. MAUVAISE IDÉE (4.15 → 8.65)
def s_bad(t):
    w, u = new_layers(background("table"))
    plant(w, 540, TABLE + 60, PLANT_H, rotten=0.35 * clamp((t - 6.5) / 0.6))
    put(u, icon("cross", 230), 540, 640, life(t, 4.3, 7.4), math.sin(t * 7) * 6)
    title(u, "MAUVAISE IDÉE !", t, 4.3, 6.4, y=230, color=RED, size=135)
    title(u, "ÇA LA TUE", t, 6.58, None, y=230, color=RED)
    put(u, icon("lightbulb", 190), 540, 600, life(t, 7.86), math.sin(t * 4) * 5)
    sparkles(u, t, 7.9, 540, 600, 170, 7, 2)
    return w, u


cue(4.3, "fail", 0.4)
cue(6.58, "pop_lo", 0.4)
cue(7.86, "sparkle", 0.35)
cue(7.9, "pop_hi", 0.3)


# ============================================================ racines en coupe (C, D, E)
SOIL_Y = 760
ROOT_H = 560


def roots_scene(t, wet=0.0, rotten=0.0, air=1.0, t_in=None):
    w, u = new_layers(background("none", SOIL_Y, darken=0.45 * wet))
    if t_in is not None:
        s = life(t, t_in, dur=0.4)
    else:
        s = 1.0
    spr(w, A + "racines", 540, SOIL_Y + 20 + ROOT_H, ROOT_H, s, rotten=rotten, shadow=False)
    air_bubbles(w, 540, SOIL_Y + 330, t, air, n=14, spread=330)
    if wet > 0.01:
        water(w, lerp(H + 40, SOIL_Y + 30, wet), t, 0.42)
    return w, u


# ============================================================ C. EAU + AIR (8.65 → 12.75)
def s_air(t):
    w, u = roots_scene(t, air=fade(t, 11.0, None, 0.5), t_in=8.7)
    put(u, icon("drop", 170), 300, 420, life(t, 10.54))
    put(u, text_img("EAU", F_TITLE, 90, YEL, 10, DARK, 8, DARK), 300, 560, life(t, 10.6), -4)
    put(u, text_img("+", F_TITLE, 150, CREAM, 12, DARK, 10, DARK), 540, 430, life(t, 11.46))
    put(u, text_img("AIR", F_TITLE, 90, YEL, 10, DARK, 8, DARK), 780, 560, life(t, 12.14), 4)
    air_bubbles(u, 780, 420, t, life(t, 12.1), n=5, spread=70, seed=9)
    title(u, "LES RACINES", t, 8.8, 10.4, y=230)
    return w, u


cue(8.7, "whoosh_up", 0.35)
cue(8.8, "pop", 0.3)
cue(10.54, "plop", 0.35)
cue(11.0, "sparkle", 0.2)
cue(11.46, "pop", 0.3)
cue(12.14, "pop_hi", 0.35)


# ============================================================ D. TROP SOUVENT → POURRISSENT (12.75 → 20.85)
def s_drown(t):
    wet = ease_io((t - 14.6) / 1.4)
    air = 1 - ease_in((t - 16.4) / 0.9)
    rot = ease_io((t - 19.6) / 1.0)
    w, u = roots_scene(t, wet, rot, air)
    falling(u, t, 13.0, 14.9, "drop", 18, 6, 1400, 48, bottom=SOIL_Y)
    act = -1 if t < 13.3 else (0 if t < 13.55 else (1 if t < 13.8 else 2))
    pills(u, ["LUN", "MAR", "MER"], act, t, 13.2, 14.4, y=420)
    title(u, "TROP SOUVENT", t, 13.34, 14.5, y=230)
    title(u, "GORGÉE D'EAU", t, 15.26, 17.1, y=230)
    title(u, "ELLES ÉTOUFFENT", t, 17.22, 19.5, y=230, color=RED, size=120)
    title(u, "ELLES POURRISSENT", t, 20.0, None, y=230, color=RED, size=115)
    flies(w, t, 20.2, 21.2, 540, SOIL_Y - 120, 200)
    return w, u


cue(13.0, "rain", 0.35)
for _k in range(3):
    cue(13.3 + _k * 0.25, "tick", 0.3)
cue(15.26, "pour", 0.4)
cue(16.6, "pop_lo", 0.25)
cue(17.22, "fail", 0.0)
cue(17.25, "squish", 0.35)
cue(20.0, "fail", 0.35)
cue(20.3, "buzz", 0.15)


# ============================================================ E. NE BOIT PLUS → MEURT DE SOIF (20.85 → 29.55)
def s_thirst(t):
    if t < 25.1:
        w, u = roots_scene(t, 0.6, 1.0, 0.0)
        # gouttes qui rebondissent sur la racine pourrie
        for i in range(4):
            tt = (t - 22.2 - i * 0.35) % 1.4
            if t < 22.2 or tt > 1.0:
                continue
            x = 400 + i * 95
            y = 500 + 1200 * tt * tt if tt < 0.5 else 800 - 300 * (tt - 0.5) + 900 * (tt - 0.5) ** 2
            put(w, icon("drop", 52), x, y, 1, 0, 1 - max(0, tt - 0.6) * 2.5)
        put(u, icon("nosign", 210), 540, 470, life(t, 23.66, 25.0))
        title(u, "ELLE NE BOIT PLUS", t, 23.66, 25.0, y=230, color=RED, size=115)
        return w, u
    w, u = new_layers(background("table"))
    px, py = pot_bottom(540, TABLE + 60)
    saucer(w, px, py + 6, 360, ease_out((t - 26.6) / 0.5), t)
    plant(w, 540, TABLE + 60, PLANT_H, rotten=0.35)
    title(u, "LES PIEDS DANS L'EAU", t, 26.6, 28.25, y=230, size=105)
    title(u, "MAIS ELLE A SOIF !", t, 28.5, None, y=230, color=RED, size=120)
    put(u, icon("drop", 120), 860, 520, life(t, 28.7), math.sin(t * 5) * 6)
    put(u, icon("cross", 90), 905, 580, life(t, 28.9))
    return w, u


cue(22.2, "plop", 0.3)
cue(22.55, "plop", 0.25)
cue(22.9, "plop", 0.25)
cue(23.66, "pop_lo", 0.35)
cue(25.1, "whoosh", 0.2)
cue(26.6, "splash", 0.4)
cue(28.5, "fail", 0.3)


# ============================================================ F. LES SIGNES (29.55 → 37.45)
def s_signs(t):
    w, u = new_layers(background("table"))
    plant(w, 540, TABLE + 60, PLANT_H, rotten=0.2)
    # 1 : feuilles jaunes (feuille du bas à gauche) — 2 : terre humide — 3 : odeur
    hl_ellipse(w, 260, 1170, 170, 140, life(t, 31.14, 32.5))
    hl_ellipse(w, 545, 620, 215, 70, life(t, 32.82, 34.4))
    if t > 33.0:
        falling(w, t, 33.0, 34.4, "drop", 5, 12, 300, 34, top=600, bottom=660)
    stink(w, 545, 560, t, fade(t, 36.0, None, 0.5))
    flies(w, t, 36.3, None, 545, 470, 170)
    put(u, icon("question", 170), 540, 400, life(t, 29.74, 30.9), math.sin(t * 5) * 8)
    title(u, "FEUILLES JAUNES & MOLLES", t, 31.14, 32.7, y=230, size=95)
    title(u, "TERRE TOUJOURS HUMIDE", t, 32.82, 35.9, y=230, size=100)
    title(u, "ODEUR DE MARÉCAGE", t, 36.14, None, y=230, size=110, color=RED)
    for i, t0 in enumerate([31.14, 32.82, 36.14]):
        put(u, num_badge(str(i + 1), 110, YEL if t >= t0 else CREAM), 380 + i * 160, 380, life(t, 31.0))
    return w, u


cue(29.74, "pop", 0.35)
cue(31.14, "pop_hi", 0.35)
cue(32.06, "squish", 0.25)
cue(32.82, "pop_hi", 0.35)
cue(33.1, "plop", 0.25)
cue(36.14, "pop_hi", 0.35)
cue(36.3, "buzz", 0.2)


# ============================================================ G. STOP + TEST DU DOIGT (37.45 → 47.8)
def s_stop(t):
    if t < 40.75:
        w, u = new_layers(background("table"))
        plant(w, 540, TABLE + 60, PLANT_H, rotten=0.2)
        shake = math.sin(t * 50) * 6 * fade(t, 39.1, 39.6)
        spr(w, "poireau/watering_can", 820 + shake, 560, 300, life(t, 37.6), rot=20, shadow=False)
        put(u, icon("nosign", 300), 820 + shake, 420, life(t, 39.65))
        title(u, "À TEMPS ?", t, 37.66, 39.0, y=340)
        title(u, "STOP !", t, 39.1, None, y=340, color=RED, size=200)
        return w, u
    soil_y = 980
    dry = ease_io((t - 41.6) / 1.2)
    w, u = new_layers(background("none", soil_y))
    # couche du dessus qui sèche (2-3 cm) : bande claire
    if dry > 0.01:
        ov = Image.new("RGBA", (W, 170), (214, 182, 140, int(170 * dry)))
        w.alpha_composite(ov, (0, soil_y + 8))
    k = ease_io((t - 45.6) / 0.6)
    hand_tip = lerp(soil_y - 380, soil_y + 150, k)
    spr(w, A + "main", 600, hand_tip, 560, life(t, 45.5), shadow=False)
    if k > 0.02:
        # la terre recouvre le bout des doigts
        cover = background("none", soil_y).crop((0, soil_y + 10, W, H))
        if dry > 0.01:
            cover.alpha_composite(Image.new("RGBA", (W, 160), (214, 182, 140, int(170 * dry))), (0, 0))
        w.alpha_composite(cover, (0, soil_y + 10))
        particles(w, t, 45.95, 600, soil_y, 14, 4, col=(150, 110, 70), size=10, up=400)
    measure(u, 190, soil_y + 10, soil_y + 175, "2-3 cm", life(t, 44.18))
    put(u, icon("sun", 160), 860, 420, life(t, 40.98), t * 25)
    title(u, "LAISSE SÉCHER", t, 40.98, 44.1, y=340)
    title(u, "LE TEST DU DOIGT", t, 45.7, None, y=340, size=125)
    put(u, icon("check", 170), 860, 700, life(t, 47.02), math.sin(t * 5) * 5)
    return w, u


cue(37.66, "pop", 0.3)
cue(39.1, "fail", 0.0)
cue(39.12, "thud", 0.5)
cue(39.65, "pop_lo", 0.45)
cue(40.75, "whoosh_up", 0.3)
cue(40.98, "pop_hi", 0.3)
cue(41.6, "sparkle", 0.2)
cue(44.18, "tick", 0.35)
cue(45.5, "pop", 0.3)
cue(46.0, "crunch", 0.4)
cue(47.02, "success", 0.4)


# ============================================================ H. ON REMPOTE (47.8 → 56.1)
def s_repot(t):
    w, u = new_layers(background("table"))
    lift = ease_io((t - 50.58) / 0.6)
    gy = TABLE + 60 - 380 * lift
    px, py = pot_bottom(540, gy)
    if t < 50.58:
        plant(w, 540, gy, PLANT_H)
    else:
        # la motte sort du pot : racines visibles sous le pot
        cut = clamp((t - 51.7) / 0.5)
        rot_part = 1.0 if t < 53.6 else 1 - clamp((t - 53.6) / 0.4)
        spr(w, A + "racines", px, py + 330, 360, rotten=rot_part, shadow=False)
        plant(w, 540, gy, PLANT_H, shadow=False)
        if 51.6 < t < 53.4:
            snip = abs(math.sin((t - 51.6) * 12)) * 10
            spr(w, A + "ciseaux", px + 230, py + 170, 120, rot=180 + snip, shadow=False)
        if t > 52.0:
            for i in range(4):
                tt = t - 52.0 - i * 0.25
                if tt > 0:
                    yy = py + 200 + 900 * tt * tt
                    spr(w, A + "racines", px - 120 + i * 80, yy, 90, rotten=1, shadow=False, rot=30 * i)
    title(u, "TROP TARD ?", t, 47.98, 49.5, y=340)
    title(u, "ON REMPOTE !", t, 49.82, 51.5, y=340, color=YEL)
    tag(u, "NOIRES & MOLLES", 560, 1400, t, 52.66, 53.6, rot=-4, size=46)
    put(u, icon("cross", 110), 250, 1400, life(t, 52.8, 53.6))
    tag(u, "FERMES & CLAIRES", 560, 1400, t, 54.86, rot=-4, size=46)
    put(u, icon("check", 110), 250, 1400, life(t, 55.0))
    return w, u


cue(47.98, "pop", 0.3)
cue(49.82, "rise", 0.3)
cue(50.6, "whoosh_up", 0.3)
cue(51.0, "thud", 0.3)
cue(51.7, "chop", 0.45)
cue(52.1, "chop", 0.4)
cue(52.5, "chop", 0.35)
cue(52.66, "pop", 0.3)
cue(54.86, "success", 0.35)


# ============================================================ I. LE MÉLANGE QUI RESPIRE (56.1 → 66.95)
def s_mix(t):
    w, u = new_layers(background("table"))
    merge = ease_io((t - 64.3) / 0.6)
    xs = [210, 540, 870]
    if merge < 1:
        perlite_pile(w, lerp(xs[0], 540, merge), TABLE + 30, 330, life(t, 59.42) * (1 - merge))
        spr(w, A + "coco", lerp(xs[1], 540, merge), TABLE + 30, 400, life(t, 61.58) * (1 - merge))
        spr(w, A + "terreau", lerp(xs[2], 540, merge), TABLE + 30, 210, life(t, 63.58) * (1 - merge))
        for i, (t0, lab) in enumerate([(58.82, "PERLITE"), (60.3, "COCO"), (62.94, "TERREAU")]):
            put(u, num_badge("1/3", 150), xs[i], 640, life(t, t0, 64.2))
            put(u, text_img(lab, F_TITLE, 62, YEL, 8, DARK, 6, DARK), xs[i], 770, life(t, t0 + 0.1, 64.2), -3)
    if t > 64.3:
        top = 760
        pot_section(w, 540, top, 560, 500, t, mix=ease_out((t - 64.4) / 0.6))
        spr(w, A + "racines", 540, top + 380, 300, life(t, 64.78), shadow=False)
        air_bubbles(w, 540, top + 280, t, fade(t, 65.6, None, 0.5), n=10, spread=190)
    title(u, "UN MÉLANGE QUI RESPIRE", t, 57.34, None, y=340, size=100)
    sparkles(u, t, 66.4, 540, 1000, 300, 9, 31)
    return w, u


cue(56.3, "whoosh_up", 0.3)
cue(57.34, "pop", 0.3)
cue(58.82, "pop_hi", 0.3)
cue(59.42, "pop", 0.35)
cue(60.3, "pop_hi", 0.3)
cue(61.58, "pop", 0.35)
cue(62.94, "pop_hi", 0.3)
cue(63.58, "pop", 0.35)
cue(64.3, "whoosh", 0.3)
cue(64.5, "crunch", 0.3)
cue(66.42, "sparkle", 0.4)


# ============================================================ J. POT PERCÉ, PAS D'EAU DANS LA SOUCOUPE (66.95 → 71.35)
def s_pot(t):
    w, u = new_layers(background("table"))
    top = 640
    pot_section(w, 540, top, 560, 500, t, holes=life(t, 68.38), mix=1.0)
    if t > 68.6:
        for i in range(6):
            tt = (t - 68.6 - i * 0.18) % 1.0
            put(w, icon("drop", 44), 540 + (i % 3 - 1) * 125, top + 500 + tt * 260, 1, 0, 1 - tt)
    sw = life(t, 69.42)
    if sw > 0.01:
        saucer(w, 540, TABLE + 40, 520 * sw, 1.0, t)
        put(u, icon("nosign", 230), 860, TABLE - 40, sw)
    put(u, icon("arrow_down", 120), 830, top + 420, life(t, 68.38, 69.3), 0)
    title(u, "UN POT PERCÉ", t, 68.14, 69.3, y=340)
    title(u, "SOUCOUPE VIDE !", t, 69.42, None, y=340, color=YEL)
    return w, u


cue(67.14, "pop", 0.3)
cue(68.38, "pop_hi", 0.35)
cue(68.7, "plop", 0.3)
cue(69.42, "pop_lo", 0.4)
cue(70.1, "fail", 0.0)


# ============================================================ K. CTA (71.35 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    plant(w, 540, TABLE + 60, PLANT_H, life(t, 71.4), sick=False)
    sparkles(w, t, 71.5, 540, 800, 380, 9, 40)
    clicked = t > 72.05
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 72.0) / 0.15))
    put(u, btn, 540, 320, life(t, 71.54) * press)
    if t > 71.7:
        k = ease_out((t - 71.7) / 0.32)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(600, 360, k), 1)
    sb = life(t, 73.74)
    put(u, icon("bubble", 230), 820, 520, sb, math.sin(t * 3) * 3)
    if sb > 0.5:
        for i in range(3):
            yy = 495 - 12 * max(0, math.sin(t * 8 - i * 0.9))
            put(u, text_img("•", F_BLACK, 90, DARK), 755 + i * 65, yy - 10, sb)
    put(u, text_img("SAUVETAGE !", F_TITLE, 100, YEL, 11, DARK, 9, DARK), 540, 160, life(t, 75.86), -3)
    return w, u


cue(71.4, "pop_lo", 0.35)
cue(71.5, "sparkle", 0.35)
cue(71.54, "pop_hi", 0.35)
cue(72.03, "click", 0.6)
cue(72.1, "bell", 0.4)
cue(73.74, "pop", 0.4)
cue(75.86, "success", 0.4)

CUES[:] = [c for c in CUES if c[2] > 0]

SCENES = [
    (0.0, 4.15, s_intro),
    (4.15, 8.65, s_bad),
    (8.65, 12.75, s_air),
    (12.75, 20.85, s_drown),
    (20.85, 29.55, s_thirst),
    (29.55, 37.45, s_signs),
    (37.45, 47.8, s_stop),
    (47.8, 56.1, s_repot),
    (56.1, 66.95, s_mix),
    (66.95, 71.35, s_pot),
    (71.35, 99.0, s_cta),
]

# badge d'étape (sauvetage) : (numéro, début, fin)
TRAPS = [(1, 37.6, 47.8), (2, 47.9, 56.1), (3, 56.2, 66.95), (4, 67.0, 71.35)]
