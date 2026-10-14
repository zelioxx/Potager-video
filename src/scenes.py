"""Storyboard : une fonction par scène, temps absolus calés sur la voix off.

Chaque scène dessine sur deux calques : `w` (monde, légèrement zoomé) et `u` (UI fixe).
Les cues sonores sont déclarées à côté des animations qu'elles accompagnent.
"""
import math

import numpy as np
from PIL import Image

from gfx import (W, H, FLOOR_Y, YEL, RED, GREEN, CREAM, DARK, WHITE, background, spr, put, title, life, fade,
                 ease_out, ease_in, ease_io, ease_out_back, clamp, lerp, icon, num_badge, pills, tag, button_img,
                 magnifier_img, hl_ellipse, hline, measure, roots, shoots, water, particles, text_img, F_TITLE,
                 F_BLACK)

TABLE = FLOOR_Y + 70  # ligne de pose des objets sur la table

CUES = []


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


def new_layers(bg):
    return bg, Image.new("RGBA", (W, H), (0, 0, 0, 0))


def drop(t, t0, y_end, h=500, dur=0.42):
    """Chute avec rebond (y du bas de l'objet)."""
    if t < t0:
        return None
    x = (t - t0) / dur
    if x >= 1:
        return y_end
    if x < 0.62:
        return y_end - h * (1 - (x / 0.62) ** 2)
    b = (x - 0.62) / 0.38
    return y_end - 60 * math.sin(math.pi * b) * (1 - b)


def flies(c, t, t0, t1, cx, cy, r=170, n=3):
    a = fade(t, t0, t1)
    if a <= 0:
        return
    for i in range(n):
        ph = t * (2.3 + i * 0.4) + i * 2.1
        x = cx + math.cos(ph) * r * (0.8 + 0.2 * i) + math.sin(ph * 3.1) * 18
        y = cy + math.sin(ph * 1.3) * r * 0.45 + math.cos(ph * 2.7) * 14
        put(c, icon("fly", 40), x, y, 1, math.sin(ph * 9) * 25, a)


def sparkles(c, t, t0, cx, cy, rad=260, n=6, seed=1, dur=1.0):
    if t < t0 or t > t0 + dur:
        return
    r = np.random.default_rng(seed)
    for i in range(n):
        a = r.uniform(0, 2 * math.pi)
        d = rad * r.uniform(0.7, 1.1)
        tt = t - t0 - i * 0.05
        if tt < 0:
            continue
        s = math.sin(math.pi * clamp(tt / (dur * 0.7))) * r.uniform(0.5, 1)
        put(c, icon("star", 70), cx + math.cos(a) * d, cy + math.sin(a) * d * 0.8, s, tt * 120)


def falling(c, t, t0, t1, kind, n=16, seed=4, speed=900, size=46, top=-60, bottom=None, sway=0):
    a = fade(t, t0, t1, 0.2, 0.3)
    if a <= 0:
        return
    r = np.random.default_rng(seed)
    bottom = bottom or H
    span = bottom - top
    for i in range(n):
        x0 = r.uniform(40, W - 40)
        off = r.uniform(0, 1)
        sp = speed * r.uniform(0.8, 1.2)
        y = top + ((t - t0) * sp + off * span) % span
        x = x0 + math.sin(t * 2 + i) * sway
        put(c, icon(kind, size), x, y, r.uniform(0.6, 1), math.sin(t + i) * 20 * (sway > 0), a)


# =========================================================== SCÈNE A 0 → 7.1
def scene_intro(t):
    w, u = new_layers(background("table"))
    rot = clamp((t - 2.5) / 0.8)
    y = drop(t, 0.0, TABLE, 700)
    wob = math.sin(max(0, t - 6.3) * 14) * 4 * math.exp(-max(0, t - 6.3) * 3) if t > 6.3 else 0
    if y is not None:
        spr(w, "shallot_pair", 540, y, 680, rot=wob, rotten=rot)
    flies(w, t, 2.9, 5.0, 540, TABLE - 760, 280)
    pills(u, ["SEPT", "OCT", "NOV"], 1 if t > 1.3 else -1, t, 1.15, 2.2, y=430)
    title(u, "POURRIES !", t, 2.6, 4.0, y=430, color=RED)
    put(u, icon("question", 190), 540, 470, life(t, 4.6, 5.9), math.sin(t * 5) * 8)
    put(u, icon("lightbulb", 220), 540, 460, life(t, 5.95, 7.0), math.sin(t * 4) * 5)
    sparkles(u, t, 6.0, 540, 460, 170, 7, 2)
    return w, u


cue(0.18, "thud", 0.45)
cue(1.15, "pop", 0.35)
cue(1.32, "tick", 0.35)
cue(2.6, "pop_lo", 0.35)
cue(2.55, "squish", 0.35)
cue(2.95, "buzz", 0.22)
cue(4.6, "pop", 0.4)
cue(5.95, "sparkle", 0.35)
cue(5.95, "pop_hi", 0.3)


# =========================================================== SCÈNE B 7.1 → 13.65
def scene_autumn(t):
    soil_y = lerp(H, 1100, ease_out((t - 7.15) / 0.45))
    w, u = new_layers(background("none", soil_y))
    plant = ease_in((t - 10.6) / 0.3)
    out = 1 - clamp((t - 11.9) / 0.2)
    hg, hs = lerp(400, 290, plant), lerp(430, 310, plant)
    gy, sy_ = lerp(soil_y + 8, soil_y + 290 + 40, plant), lerp(soil_y + 8, soil_y + 310 + 40, plant)
    if out > 0:
        g = clamp((t - 10.9) / 1.0)
        roots(w, 330, gy - 20, g, 3)
        roots(w, 750, sy_ - 20, g, 5)
        sg = clamp((t - 11.0) / 0.9)
        shoots(w, 330, gy - hg + 30, sg, 330, 7)
        shoots(w, 750, sy_ - hs + 30, sg, 350, 8)
        spr(w, "garlic_bulb_a", 330, gy, hg, life(t, 7.98) * out, shadow=plant < 0.1)
        spr(w, "shallot_red", 750, sy_, hs, life(t, 8.34) * out, shadow=plant < 0.1)
    s_big = life(t, 11.98)
    if s_big > 0:
        spr(w, "garlic_open", 540, soil_y + 15, 640, s_big)
        sparkles(w, t, 12.0, 540, soil_y - 330, 360, 8, 4)
    pills(u, ["SEPT", "OCT", "NOV"], 1 if t > 9.0 else -1, t, 8.85, 10.55, y=430)
    put(u, icon("check", 190), 540, 720, life(t, 9.98, 10.6), math.sin(t * 6) * 4)
    title(u, "RACINES", t, 10.75, 11.9, y=430)
    pills(u, ["JUIN", "JUIL", "AOÛT"], 1 if t > 12.45 else -1, t, 12.3, 13.7, y=430)
    return w, u


cue(7.12, "whoosh_up", 0.35)
cue(7.98, "pop", 0.4)
cue(8.34, "pop_hi", 0.4)
cue(8.9, "tick", 0.35)
cue(9.98, "success", 0.4)
cue(10.65, "thud", 0.45)
cue(10.75, "pop", 0.3)
cue(11.98, "pop_lo", 0.45)
cue(12.0, "sparkle", 0.35)
cue(12.45, "tick", 0.35)


# =========================================================== SCÈNE C 13.65 → 15.5
def scene_traps(t):
    w, u = new_layers(background("table"))
    shake = math.sin(t * 40) * 3 * fade(t, 14.6, 15.0)
    spr(w, "garlic_bulb_a", 340 + shake, TABLE, 450, life(t, 13.7))
    spr(w, "shallot_red", 740 - shake, TABLE, 480, life(t, 13.8))
    title(u, "3 PIÈGES", t, 14.62, None, y=360, color=RED, size=170)
    for i in range(3):
        put(u, num_badge(str(i + 1), 140), 320 + i * 220, 610, life(t, 14.75 + i * 0.12))
    return w, u


cue(13.7, "pop", 0.3)
cue(14.62, "rise", 0.3)
for _i in range(3):
    cue(14.75 + _i * 0.12, "pop_hi", 0.32)


# =========================================================== SCÈNE D 15.5 → 26.25  (piège 1 : la terre)
def scene_trap1(t):
    soil_y = 1060
    clay = ease_io((t - 18.7) / 0.6)
    w, u = new_layers(background("none", soil_y, clay=clay))
    water_top = lerp(H + 30, soil_y + 40, ease_out((t - 19.75) / 1.0))
    bob = math.sin(t * 2.4) * 10 * clamp((t - 21.9) / 0.5)
    rot = clamp((t - 25.35) / 0.6)
    gy = 1430 + bob
    water(w, water_top, t, 0.38)
    roots(w, 540, gy - 18, clamp((t - 15.8) / 0.6), 9, length=150)
    spr(w, "garlic_bulb_a", 540, gy, 380, life(t, 15.7), rot=bob * 0.4, rotten=rot, shadow=False)
    hl_ellipse(w, 540, gy - 20, 230, 80, life(t, 23.1, 24.2))
    flies(w, t, 25.7, 26.5, 540, gy - 520, 240)
    title(u, "PIÈGE N°1", t, 15.62, 17.0, y=400)
    title(u, "TA TERRE", t, 17.14, 18.6, y=400)
    put(u, magnifier_img(), 540, 650, life(t, 18.7, 19.65))
    put(u, text_img("ARGILE", F_TITLE, 96, YEL, 10, DARK, 8, DARK), 540, 905, life(t, 18.85, 19.65), -3)
    falling(u, t, 19.6, 20.5, "drop", 14, 6, 1300, 46, bottom=soil_y)
    falling(u, t, 20.4, 21.9, "snow", 16, 7, 260, 56, bottom=soil_y, sway=30)
    act = -1 if t < 20.45 else (0 if t < 20.85 else (1 if t < 21.25 else 2))
    pills(u, ["DÉC", "JANV", "FÉV"], act, t, 20.35, 21.95, y=470)
    put(u, icon("drop", 110), 270, 900, life(t, 22.3, 24.1), math.sin(t * 4) * 8)
    put(u, icon("drop", 90), 810, 860, life(t, 22.45, 24.1), math.sin(t * 4 + 1) * 8)
    title(u, "HUMIDE", t, 23.7, 24.2, y=430, color=YEL)
    title(u, "IL POURRIT !", t, 25.62, None, y=430, color=RED)
    return w, u


cue(15.62, "rise", 0.3)
cue(15.7, "pop", 0.35)
cue(17.14, "pop_hi", 0.35)
cue(18.7, "pop_lo", 0.4)
cue(18.85, "pop", 0.3)
cue(19.6, "rain", 0.35)
cue(19.8, "plop", 0.35)
cue(20.47, "tick", 0.3)
cue(20.87, "tick", 0.3)
cue(21.27, "tick", 0.3)
cue(22.3, "plop", 0.3)
cue(22.45, "plop", 0.25)
cue(23.1, "pop_hi", 0.3)
cue(23.7, "pop", 0.3)
cue(25.35, "squish", 0.35)
cue(25.62, "fail", 0.35)
cue(25.75, "buzz", 0.18)


# =========================================================== SCÈNE E 26.25 → 33.1  (piège 2 : trop profond)
def scene_trap2(t):
    soil_y = 820
    deep = ease_in((t - 28.0) / 0.45)
    w, u = new_layers(background("none", soil_y, darken=0.35 * fade(t, 31.5, None, 0.5)))
    base = lerp(soil_y + 20, 1450, deep)
    sq = 1 + 0.06 * math.sin((t - 31.58) * 16) * fade(t, 31.58, 32.4) if t > 31.58 else 1
    rot = clamp((t - 32.45) / 0.5)
    spr(w, "clove_sprout", 540, base, 380, life(t, 26.5), sx=sq, sy=2 - sq, rotten=rot, shadow=deep < 0.05)
    if t > 28.45:
        particles(w, t, 28.0, 540, soil_y, 16, 5)
    put(u, icon("arrow_down", 150), 790, 600 + 40 * math.sin(t * 8), life(t, 27.75, 28.6))
    measure(u, 790, soil_y + 10, base - 380, "15 cm", life(t, 29.7))
    put(u, icon("cross", 150), 330, base - 300, life(t, 32.54))
    title(u, "PIÈGE N°2", t, 26.38, 27.7, y=400)
    title(u, "TROP PROFOND", t, 29.7, 31.4, y=400, size=135)
    title(u, "IL ÉTOUFFE", t, 31.58, None, y=400, color=RED, size=140)
    return w, u


cue(26.38, "rise", 0.3)
cue(26.5, "pop", 0.35)
cue(27.75, "whoosh", 0.25)
cue(28.42, "thud", 0.5)
cue(29.7, "pop_hi", 0.35)
cue(29.75, "tick", 0.3)
cue(31.58, "squish", 0.35)
cue(32.54, "fail", 0.3)


# =========================================================== SCÈNE F 33.1 → 36.85  (le bon geste)
def scene_good(t):
    soil_y = 1060
    w, u = new_layers(background("none", soil_y))
    y = drop(t, 33.25, soil_y + 360, 600, 0.45)
    if y is not None:
        roots(w, 540, y - 10, clamp((t - 33.8) / 0.8), 13, length=140, n=9)
        spr(w, "clove_sprout", 540, y, 390, shadow=False)
    tip_y = soil_y + 360 - 390 + 20
    hl_ellipse(w, 552, tip_y + 10, 95, 95, life(t, 34.5) * (1 + 0.05 * math.sin(t * 8)))
    hline(w, 60, W - 60, soil_y, ease_io((t - 35.58) / 0.5))
    title(u, "LE BON GESTE", t, 33.46, 34.4, y=400, color=YEL)
    title(u, "LA POINTE", t, 34.5, 35.5, y=400)
    title(u, "À FLEUR", t, 35.58, None, y=400)
    put(u, icon("check", 180), 840, 820, life(t, 36.18), math.sin(t * 5) * 5)
    return w, u


cue(33.46, "rise", 0.3)
cue(33.62, "thud", 0.4)
cue(34.5, "pop_hi", 0.35)
cue(35.58, "whoosh_up", 0.2)
cue(36.18, "success", 0.4)


# =========================================================== SCÈNE G1 36.85 → 43.95  (piège 3 : les oiseaux)
CLOVES = [(250, 0.0), (540, 0.08), (830, 0.16)]


def scene_birds(t):
    soil_y = 1260
    w, u = new_layers(background("none", soil_y))
    for i, (x, dt) in enumerate(CLOVES):
        t_out = 42.42 + dt
        if t < t_out:
            spr(w, "clove_sprout", x, soil_y + 230, 250, life(t, 37.0 + dt), shadow=False)
        else:
            k = t - t_out
            if k < 0.6:
                px = x + (i - 1) * 260 * k + 60
                py = soil_y - 30 - 900 * k + 1600 * k * k
            else:
                px = x + (i - 1) * 156 + 60
                py = soil_y + 10
            spr(w, "clove_sprout", px, min(py, soil_y + 10), 210, rot=-80 + (i - 1) * 30 + min(k, 0.6) * 500 * (1 if i % 2 else -1))
            particles(w, t, t_out, x, soil_y, 10, 20 + i, size=11)
    # merle : arrive en sautillant par la droite, picore
    if t > 40.2:
        k = clamp((t - 40.2) / 0.75)
        bx = lerp(1350, 760, ease_out(k))
        hop = abs(math.sin(k * math.pi * 3)) * 70 * (1 - k)
        peck = max(0, math.sin((t - 41.6) * 11)) * 22 if 41.6 < t < 42.6 else 0
        spr(w, "blackbird_c", bx, soil_y + 4 - hop, 520, rot=peck)
    if t > 40.75:
        k = clamp((t - 40.75) / 0.6)
        sx_ = lerp(-300, 290, ease_out(k))
        hop = abs(math.sin(k * math.pi * 2)) * 50 * (1 - k)
        peck = max(0, math.sin((t - 41.8) * 12 + 1)) * 18 if 41.8 < t < 42.6 else 0
        spr(w, "sparrow", sx_, soil_y + 4 - hop, 300, rot=-peck, flip=True)
    title(u, "PIÈGE N°3", t, 37.18, 38.75, y=400)
    title(u, "LES GOURMANDS", t, 39.1, 40.1, y=400, size=135)
    title(u, "PICORENT", t, 41.62, 42.4, y=400)
    title(u, "LES CAÏEUX", t, 43.0, None, y=400)
    return w, u


cue(36.98, "pop", 0.3)
cue(37.18, "rise", 0.3)
cue(39.1, "pop_lo", 0.35)
cue(40.3, "bird", 0.4)
cue(40.8, "bird", 0.3)
cue(41.65, "peck", 0.45)
cue(42.05, "peck", 0.4)
cue(42.42, "pop", 0.35)
cue(42.5, "pop_hi", 0.3)
cue(42.58, "pop", 0.3)
cue(43.0, "pop_hi", 0.3)


# =========================================================== SCÈNE G2 43.95 → 47.1  (nuisibles du sol)
def scene_grubs(t):
    soil_y = 1000
    w, u = new_layers(background("none", soil_y))
    shake = math.sin(t * 50) * 4 * fade(t, 46.2, 46.9)
    bite = clamp((t - 46.2) / 0.7)
    roots(w, 540, 1370, 1, 21, length=160)
    spr(w, "garlic_bulb_a", 540 + shake, 1390, 380, life(t, 44.0), bite=bite, shadow=False)
    k = ease_out((t - 45.0) / 0.9)
    gx1, gx2 = lerp(-250, 300, k), lerp(1330, 790, k)
    wig = math.sin(t * 9) * 4
    spr(w, "grub", gx1, 1440, 190, rot=wig, shadow=False, flip=True)
    spr(w, "grub", gx2, 1230, 170, rot=-wig, shadow=False)
    if t > 46.2:
        particles(w, t, 46.25, 540, 1250, 12, 31, col=(236, 228, 210), size=8, up=300)
    title(u, "NUISIBLES", t, 45.02, None, y=400, color=RED)
    return w, u


cue(44.0, "pop", 0.3)
cue(45.02, "pop_lo", 0.35)
cue(45.1, "squish", 0.2)
cue(46.26, "crunch", 0.55)


# =========================================================== SCÈNE H 47.1 → 53.85  (la solution : printemps)
def scene_spring(t):
    soil_y = lerp(H, 1250, ease_out((t - 49.85) / 0.45))
    w, u = new_layers(background("table" if t < 49.85 else "none", soil_y if t >= 49.85 else None,
                                 warm=fade(t, 51.26, None, 0.6)))
    out1 = life(t, 47.25, 48.6)
    spr(w, "garlic_bulb_a", 340, TABLE, 440, out1)
    spr(w, "shallot_red", 740, TABLE, 470, life(t, 47.35, 48.6))
    spr(w, "shallot_sprout", 540, TABLE, 720, life(t, 48.65, 49.75))
    if t > 49.85:
        drain = ease_out((t - 51.9) / 1.2)
        if t > 51.9:
            r = np.random.default_rng(9)
            for i in range(10):
                x = r.uniform(80, W - 80)
                y = soil_y + 120 + (t - 51.9) * r.uniform(500, 800) + r.uniform(0, 200)
                put(w, icon("drop", 50), x, y, 1, 0, 1 - drain)
        spr(w, "garlic_bulb_a", 340, soil_y + 230, 300, life(t, 50.6), shadow=False)
        spr(w, "shallot_red", 740, soil_y + 240, 320, life(t, 50.75), shadow=False)
        roots(w, 340, soil_y + 215, clamp((t - 50.9) / 0.8), 41, length=150)
        roots(w, 740, soil_y + 225, clamp((t - 51.0) / 0.8), 42, length=150)
    title(u, "LA SOLUTION", t, 47.66, 48.6, y=420)
    sparkles(u, t, 47.7, 540, 420, 330, 8, 11)
    title(u, "AU PRINTEMPS !", t, 49.18, 49.85, y=420, color=YEL, size=140)
    pills(u, ["FÉV", "MARS", "AVR"], 1 if t > 50.3 else -1, t, 50.0, None, y=400)
    put(u, icon("sun", 190), 850, 700, life(t, 51.26), t * 20)
    put(u, icon("thermo", 170), 220, 700, life(t, 51.4))
    put(u, text_img("VARIÉTÉS ADAPTÉES", F_TITLE, 82, YEL, 9, DARK, 7, DARK), 540, 950, life(t, 52.86), -2)
    return w, u


cue(47.25, "pop", 0.3)
cue(47.66, "sparkle", 0.35)
cue(47.66, "rise", 0.25)
cue(48.65, "pop_lo", 0.4)
cue(49.18, "pop_hi", 0.3)
cue(49.85, "whoosh_up", 0.35)
cue(50.0, "pop", 0.3)
cue(50.3, "tick", 0.35)
cue(50.6, "pop", 0.3)
cue(50.75, "pop_hi", 0.3)
cue(51.26, "rise", 0.3)
cue(51.95, "plop", 0.3)
cue(52.2, "plop", 0.25)
cue(52.86, "success", 0.35)


# =========================================================== SCÈNE I 53.85 → 57.6  (côté ail)
def scene_garlic(t):
    w, u = new_layers(background("table"))
    s1 = life(t, 54.9)
    spr(w, "garlic_bulb_a", 300, TABLE, 470, s1)
    spr(w, "garlic_pink", 770, TABLE, 470, life(t, 56.3))
    tag(u, "PRINTANOR", 300, 1420, t, 55.1, rot=-5, size=42)
    tag(u, "ROSE DE LAUTREC", 760, 1420, t, 56.6, rot=4, size=36)
    title(u, "CÔTÉ AIL", t, 54.0, None, y=400)
    return w, u


cue(54.0, "rise", 0.3)
cue(54.9, "pop", 0.4)
cue(55.1, "pop_hi", 0.3)
cue(56.3, "pop", 0.4)
cue(56.6, "pop_hi", 0.3)


# =========================================================== SCÈNE J 57.6 → 61.15  (côté échalote)
def scene_shallot(t):
    w, u = new_layers(background("table"))
    spr(w, "shallot_red", 200, TABLE, 420, life(t, 58.85))
    spr(w, "shallot_pile", 545, TABLE + 10, 330, life(t, 59.65))
    spr(w, "shallot_round", 885, TABLE, 340, life(t, 60.55))
    tag(u, "JERMOR", 220, 1440, t, 58.95, rot=-4, size=40)
    tag(u, "LONGOR", 545, 1440, t, 59.75, rot=3, size=40)
    tag(u, "MIKOR", 870, 1440, t, 60.65, rot=-3, size=40)
    title(u, "CÔTÉ ÉCHALOTE", t, 57.8, None, y=400, size=140)
    return w, u


cue(57.8, "rise", 0.3)
for _t0 in (58.85, 59.65, 60.55):
    cue(_t0, "pop", 0.4)
    cue(_t0 + 0.1, "pop_hi", 0.25)


# =========================================================== SCÈNE K 61.15 → 64.75  (bilan)
def scene_result(t):
    w, u = new_layers(background("table"))
    up = ease_io((t - 63.6) / 0.4)
    ys = lerp(680, 400, up)
    sc = lerp(1, 0.8, up)
    s1 = life(t, 61.5) * sc
    put(u, icon("drop", 200), 290, ys, s1)
    put(u, icon("nosign", 280), 290, ys + 10, s1)
    put(u, text_img("HUMIDITÉ", F_TITLE, 76, YEL, 9, DARK, 7, DARK), 290, ys + 200 * sc, s1, -3)
    s2 = life(t, 62.62) * sc
    if s2 > 0.01:
        spr(u, "garlic_dark", 790, ys + 115 * sc, 230 * sc, s2 / sc, rotten=1, shadow=False)
    put(u, icon("nosign", 280), 790, ys + 10, s2)
    put(u, text_img("POURRITURE", F_TITLE, 76, YEL, 9, DARK, 7, DARK), 790, ys + 200 * sc, s2, 3)
    y = drop(t, 63.8, TABLE + 20, 700)
    if y is not None:
        spr(w, "shallot_pile", 280, y - 10, 230)
        spr(w, "garlic_bowl", 600, y, 400)
        spr(w, "garlic_open", 900, y, 260)
    sparkles(w, t, 64.15, 560, 1050, 380, 9, 14)
    title(u, "MÊME RÉCOLTE", t, 64.18, None, y=740, size=130)
    return w, u


cue(61.5, "pop", 0.35)
cue(61.6, "plop", 0.25)
cue(62.62, "pop", 0.35)
cue(63.6, "whoosh_up", 0.2)
cue(64.0, "thud", 0.45)
cue(64.15, "sparkle", 0.4)
cue(64.18, "success", 0.35)


# =========================================================== SCÈNE L 64.75 → 67.2  (et toi ?)
def scene_you(t):
    w, u = new_layers(background("table"))
    spr(w, "garlic_bulb_a", 350, TABLE, 430, life(t, 64.85))
    spr(w, "shallot_red", 730, TABLE, 450, life(t, 64.95))
    title(u, "ET TOI ?", t, 65.0, None, y=380, size=170)
    put(u, button_img("AUTOMNE", (196, 110, 50), 56), 262, 700, life(t, 66.02), -4)
    put(u, text_img("OU", F_TITLE, 80, CREAM, 9, DARK, 7, DARK), 540, 700, life(t, 66.42))
    put(u, button_img("PRINTEMPS", GREEN, 56), 815, 700, life(t, 66.7), 4)
    return w, u


cue(64.85, "pop", 0.3)
cue(65.0, "rise", 0.3)
cue(66.02, "pop", 0.4)
cue(66.42, "tick", 0.3)
cue(66.7, "pop_hi", 0.4)


# =========================================================== SCÈNE M 67.2 → fin  (CTA)
def scene_cta(t):
    w, u = new_layers(background("table"))
    spr(w, "garlic_open", 260, TABLE, 340, life(t, 67.3))
    spr(w, "shallot_sprout", 540, TABLE, 470, life(t, 67.4))
    spr(w, "shallot_red", 830, TABLE, 340, life(t, 67.5))
    sb = life(t, 67.9)
    put(u, icon("bubble", 250), 540, 400, sb, math.sin(t * 3) * 3)
    if sb > 0.5:
        for i in range(3):
            yy = 405 - 12 * max(0, math.sin(t * 8 - i * 0.9))
            put(u, text_img("•", F_BLACK, 90, DARK), 475 + i * 65, yy - 10, sb)
    clicked = t > 69.35
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER",
                     (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 69.3) / 0.15))
    put(u, btn, 540, 650, life(t, 68.78) * press)
    if t > 68.95:
        k = ease_out((t - 68.95) / 0.35)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(950, 690, k), 1)
    sparkles(u, t, 69.4, 540, 650, 280, 8, 21)
    put(u, text_img("ASTUCES POTAGER", F_TITLE, 96, YEL, 10, DARK, 8, DARK), 540, 170, life(t, 70.1), -3)
    return w, u


cue(67.3, "pop", 0.3)
cue(67.9, "pop_hi", 0.4)
cue(68.78, "pop", 0.4)
cue(69.33, "click", 0.6)
cue(69.4, "bell", 0.4)
cue(70.1, "sparkle", 0.35)


SCENES = [
    (0.0, 7.12, scene_intro),
    (7.12, 13.65, scene_autumn),
    (13.65, 15.5, scene_traps),
    (15.5, 26.25, scene_trap1),
    (26.25, 33.1, scene_trap2),
    (33.1, 36.85, scene_good),
    (36.85, 43.95, scene_birds),
    (43.95, 47.1, scene_grubs),
    (47.1, 53.85, scene_spring),
    (53.85, 57.6, scene_garlic),
    (57.6, 61.15, scene_shallot),
    (61.15, 64.75, scene_result),
    (64.75, 67.2, scene_you),
    (67.2, 99.0, scene_cta),
]

# badge « piège » haut-droite : (numéro, début, fin)
TRAPS = [(1, 15.62, 26.3), (2, 26.38, 36.9), (3, 36.98, 47.15)]
