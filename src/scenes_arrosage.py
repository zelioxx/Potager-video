"""Storyboard « N'arrose pas trop tes plantes d'intérieur » (voix : assets/audio/arrosage/voix.mp3).

Monstera fourni (photo malade / en forme). Pour voir les racines, le vrai pot en terre cuite s'ouvre en deux
(pot_open.py) et laisse voir la coupe : terreau, racines épaisses de monstera, air, eau.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, background, spr, put, title, life, fade, ease_out, ease_in,
                 ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse, measure, particles,
                 text_img, F_TITLE, F_BLACK)
from scenes import TABLE, new_layers, flies, sparkles, falling
import pot_open as P

CUES = []


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


A = "arrosage/"
# cadrages : (échelle, x du bas du pot, y du bas du pot)
WIDE = (1.0, 540, 1250)
ZOOM = (1.6, 540, 1330)
MID = (1.25, 540, 1200)


def cam(t, t0, a, b, dur=0.6):
    k = ease_io((t - t0) / dur)
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def plant(c, t, view, open_=0.0, sick=True, healthy=0.0, **sec):
    s, px, py = view
    img = P.compose(open_, sick=sick, healthy_blend=healthy, t=t, **sec)
    P.place(c, img, px, py, s)


def scr(view, x, y):
    s, px, py = view
    return P.to_screen(x, y, px, py, s)


# ------------------------------------------------------------- éléments dessinés
def saucer(c, cx, y, w=330, water_lvl=0.0, t=0.0):
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.ellipse([cx - w / 2 - 8, y - w * 0.09, cx + w / 2 + 8, y + w * 0.14], fill=(60, 38, 25, 110))
    d.ellipse([cx - w / 2, y - w * 0.11, cx + w / 2, y + w * 0.09], fill=(176, 92, 58))
    d.ellipse([cx - w / 2 + 12, y - w * 0.095, cx + w / 2 - 12, y + w * 0.035], fill=(136, 68, 42))
    if water_lvl > 0.01:
        ww = (w - 34) * (0.55 + 0.45 * water_lvl)
        wave = 2 * math.sin(t * 5)
        d.ellipse([cx - ww / 2, y - w * 0.085 + wave, cx + ww / 2, y + w * 0.03 + wave],
                  fill=(110, 170, 210, int(220 * water_lvl)))
        d.arc([cx - ww / 2, y - w * 0.085 + wave, cx + ww / 2, y + w * 0.03 + wave], 190, 340,
              fill=(225, 242, 252, 240), width=4)
    c.alpha_composite(ov)


def stink(c, x, y, t, a=1.0):
    """Lignes d'odeur ondulées qui montent au-dessus du pot."""
    if a <= 0.01:
        return
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for k in range(3):
        ph = (t * 0.7 + k / 3) % 1
        x0 = x + (k - 1) * 110
        y0 = y - ph * 80
        pts = [(x0 + 24 * math.sin(i / 2.2 + t * 3 + k), y0 - i * 9) for i in range(13)]
        al = int(255 * a * math.sin(math.pi * ph))
        d.line(pts, fill=(40, 44, 22, al), width=20, joint="curve")
        d.line(pts, fill=(176, 168, 70, al), width=11, joint="curve")
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


# arrosoir : position du bec (pomme) dans la photo de l'arrosoir
CAN = "poireau/watering_can"
CAN_SIZE = (887, 703)
CAN_SPOUT = (780, 225)


def can_center_for_spout(sx, sy, h, angle_cw):
    k = h / CAN_SIZE[1]
    vx, vy = (CAN_SPOUT[0] - CAN_SIZE[0] / 2) * k, (CAN_SPOUT[1] - CAN_SIZE[1] / 2) * k
    a = math.radians(angle_cw)
    rx = vx * math.cos(a) - vy * math.sin(a)
    ry = vx * math.sin(a) + vy * math.cos(a)
    return sx - rx, sy - ry


def watering(c, t, t0, spout, target, h=300, angle=38, s=1.0, pour=True):
    """Arrosoir incliné dont le bec est exactement en `spout`, filet d'eau jusqu'à `target`."""
    if s <= 0.01:
        return
    cx, cy = can_center_for_spout(spout[0], spout[1], h * s, angle)
    spr(c, CAN, cx, cy, h, s, rot=-angle, shadow=False, anchor="center")
    if not pour or t < t0 + 0.2:
        return
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(2)
    for i in range(16):
        ph = ((t - t0) * 1.6 + i / 16) % 1
        x = lerp(spout[0], target[0], ph) + r.uniform(-14, 14)
        y = lerp(spout[1], target[1], ph ** 1.4)
        rad = r.uniform(5, 9)
        d.ellipse([x - rad, y - rad * 1.3, x + rad, y + rad * 1.3], fill=(90, 165, 225, 230),
                  outline=(225, 242, 252, 255), width=2)


# ============================================================ A. JAUNIT, RAMOLLIT… (0 → 4.15)
def s_intro(t):
    w, u = new_layers(background("table"))
    plant(w, t, WIDE)
    soil = scr(WIDE, 510, 470)
    if t > 2.8:
        k = ease_out((t - 2.8) / 0.4)
        spout = (lerp(1250, soil[0] + 60, k), soil[1] - 230)
        watering(w, t, 3.1, spout, (soil[0] + 30, soil[1] + 10), 360)
    title(u, "ELLE JAUNIT…", t, 1.18, 1.75, y=330, size=130)
    title(u, "ELLE RAMOLLIT…", t, 1.78, 2.75, y=330, size=130)
    title(u, "ENCORE PLUS D'EAU ?", t, 2.94, None, y=330, size=110)
    return w, u


cue(0.05, "pop_lo", 0.4)
cue(1.18, "pop", 0.3)
cue(1.78, "squish", 0.3)
cue(2.85, "whoosh", 0.25)
cue(3.1, "pour", 0.45)
cue(3.82, "pop_hi", 0.3)


# ============================================================ B. MAUVAISE IDÉE (4.15 → 8.65)
def s_bad(t):
    w, u = new_layers(background("table"))
    plant(w, t, WIDE)
    put(u, icon("cross", 230), 540, 560, life(t, 4.3, 7.4), math.sin(t * 7) * 6)
    title(u, "MAUVAISE IDÉE !", t, 4.3, 6.4, y=330, color=RED, size=135)
    title(u, "ÇA LA TUE", t, 6.58, None, y=330, color=RED)
    put(u, icon("lightbulb", 190), 540, 560, life(t, 7.86), math.sin(t * 4) * 5)
    sparkles(u, t, 7.9, 540, 560, 170, 7, 2)
    return w, u


cue(4.3, "fail", 0.4)
cue(6.58, "pop_lo", 0.4)
cue(7.86, "sparkle", 0.35)
cue(7.9, "pop_hi", 0.3)


# ============================================================ C. EAU + AIR (8.65 → 12.75)
def s_air(t):
    w, u = new_layers(background("table"))
    view = cam(t, 8.65, WIDE, ZOOM, 0.6)
    op = ease_io((t - 9.25) / 0.6)
    g = ease_out((t - 9.6) / 1.2)
    plant(w, t, view, op, g=g, air=fade(t, 11.2, None, 0.5))
    put(u, icon("drop", 150), 300, 330, life(t, 10.54))
    put(u, text_img("EAU", F_TITLE, 84, YEL, 10, DARK, 8, DARK), 300, 460, life(t, 10.6), -4)
    put(u, text_img("+", F_TITLE, 140, CREAM, 12, DARK, 10, DARK), 540, 380, life(t, 11.46))
    put(u, text_img("AIR", F_TITLE, 84, YEL, 10, DARK, 8, DARK), 780, 460, life(t, 12.14), 4)
    title(u, "LES RACINES", t, 9.25, 10.4, y=330)
    return w, u


cue(8.7, "whoosh_up", 0.35)
cue(9.25, "whoosh", 0.3)
cue(9.35, "thud", 0.3)
cue(10.54, "plop", 0.35)
cue(11.2, "sparkle", 0.25)
cue(11.46, "pop", 0.3)
cue(12.14, "pop_hi", 0.35)


# ============================================================ D. TROP SOUVENT → POURRISSENT (12.75 → 20.85)
def s_drown(t):
    w, u = new_layers(background("table"))
    wet = 0.85 * ease_io((t - 14.6) / 1.4)
    air = 1 - ease_in((t - 15.4) / 1.2)
    rot = ease_io((t - 19.6) / 1.0)
    plant(w, t, ZOOM, 1.0, water=wet, air=air, rot=rot, murky=rot * 0.6)
    top = scr(ZOOM, 510, 470)
    falling(u, t, 13.0, 14.9, "drop", 16, 6, 1400, 46, bottom=top[1])
    act = -1 if t < 13.3 else (0 if t < 13.55 else (1 if t < 13.8 else 2))
    pills(u, ["LUN", "MAR", "MER"], act, t, 13.2, 14.4, y=480)
    title(u, "TROP SOUVENT", t, 13.34, 14.5, y=330)
    title(u, "GORGÉE D'EAU", t, 15.26, 17.1, y=330)
    title(u, "ELLES ÉTOUFFENT", t, 17.22, 19.5, y=330, color=RED, size=120)
    title(u, "ELLES POURRISSENT", t, 20.0, None, y=330, color=RED, size=115)
    return w, u


cue(13.0, "rain", 0.35)
for _k in range(3):
    cue(13.3 + _k * 0.25, "tick", 0.3)
cue(14.6, "pour", 0.4)
cue(15.6, "pop_lo", 0.2)
cue(17.25, "squish", 0.35)
cue(20.0, "fail", 0.35)


# ============================================================ E. NE BOIT PLUS → MEURT DE SOIF (20.85 → 29.55)
def s_thirst(t):
    if t < 25.1:
        w, u = new_layers(background("table"))
        plant(w, t, ZOOM, 1.0, water=0.85, rot=1.0, murky=0.6)
        # gouttes qui rebondissent sur les racines pourries sans être absorbées
        for i, idx in enumerate(P.main_roots()[1:8:2]):
            tip = scr(ZOOM, *P.root_paths()[idx]["pts"][14])
            tt = (t - 22.0 - i * 0.3) % 1.3
            if t < 22.0 or tt > 0.95:
                continue
            if tt < 0.45:
                x, y = tip[0], tip[1] - 260 + 260 * (tt / 0.45) ** 2
            else:
                k = (tt - 0.45) / 0.5
                x, y = tip[0] + 90 * k * (1 if i % 2 else -1), tip[1] - 120 * math.sin(math.pi * k)
            put(w, icon("drop", 50), x, y, 1, 0, 1 - max(0, tt - 0.7) * 4)
        put(u, icon("nosign", 200), 860, 560, life(t, 23.66, 25.0))
        put(u, icon("drop", 110), 860, 560, life(t, 23.66, 25.0))
        title(u, "ELLE NE BOIT PLUS", t, 23.66, 25.0, y=330, color=RED, size=115)
        return w, u
    w, u = new_layers(background("table"))
    s, px, py = WIDE
    saucer(w, px, py + 4, 330, ease_out((t - 26.6) / 0.5), t)
    plant(w, t, WIDE)
    title(u, "LES PIEDS DANS L'EAU", t, 26.6, 28.25, y=330, size=105)
    title(u, "MAIS ELLE A SOIF !", t, 28.5, None, y=330, color=RED, size=120)
    put(u, icon("drop", 120), 870, 560, life(t, 28.7), math.sin(t * 5) * 6)
    put(u, icon("cross", 90), 915, 620, life(t, 28.9))
    return w, u


cue(22.0, "plop", 0.3)
cue(22.3, "plop", 0.25)
cue(22.6, "plop", 0.25)
cue(23.66, "pop_lo", 0.35)
cue(25.1, "whoosh", 0.2)
cue(26.6, "splash", 0.4)
cue(28.5, "fail", 0.3)


# ============================================================ F. LES SIGNES (29.55 → 37.45)
def s_signs(t):
    w, u = new_layers(background("table"))
    plant(w, t, WIDE)
    leaf = scr(WIDE, 250, 810)
    soil = scr(WIDE, 510, 475)
    hl_ellipse(w, leaf[0], leaf[1], 175, 150, life(t, 31.14, 32.7))
    hl_ellipse(w, soil[0], soil[1], 215, 95, life(t, 32.82, 36.0))
    if 33.0 < t < 36.0:
        falling(w, t, 33.0, 35.9, "drop", 6, 12, 260, 34, top=soil[1] - 40, bottom=soil[1] + 30)
    stink(w, soil[0], soil[1] - 110, t, fade(t, 36.0, None, 0.5))
    flies(w, t, 36.3, None, soil[0], soil[1] - 140, 170)
    put(u, icon("question", 170), 540, 520, life(t, 29.74, 30.9), math.sin(t * 5) * 8)
    title(u, "FEUILLES JAUNES & MOLLES", t, 31.14, 32.7, y=330, size=95)
    title(u, "TERRE TOUJOURS HUMIDE", t, 32.82, 35.9, y=330, size=100)
    title(u, "ODEUR DE MARÉCAGE", t, 36.14, None, y=330, size=110, color=RED)
    for i, t0 in enumerate([31.14, 32.82, 36.14]):
        put(u, num_badge(str(i + 1), 110, YEL if t >= t0 else CREAM), 380 + i * 160, 480, life(t, 31.0))
    return w, u


cue(29.74, "pop", 0.35)
cue(31.14, "pop_hi", 0.35)
cue(32.06, "squish", 0.25)
cue(32.82, "pop_hi", 0.35)
cue(33.1, "plop", 0.25)
cue(36.14, "pop_hi", 0.35)
cue(36.3, "buzz", 0.2)


# ============================================================ G. STOP + TEST DU DOIGT (37.45 → 47.8)
HAND = "arrosage/main"
HAND_SIZE = (553, 676)
HAND_TIP = (370, 660)


def s_stop(t):
    if t < 40.75:
        w, u = new_layers(background("table"))
        plant(w, t, WIDE)
        shake = math.sin(t * 50) * 6 * fade(t, 39.1, 39.6)
        spr(w, CAN, 820 + shake, 640, 260, life(t, 37.6), shadow=False, anchor="center")
        put(u, icon("nosign", 300), 820 + shake, 640, life(t, 39.65))
        title(u, "À TEMPS ?", t, 37.66, 39.0, y=330)
        title(u, "STOP !", t, 39.1, None, y=340, color=RED, size=200)
        return w, u
    w, u = new_layers(background("table"))
    view = cam(t, 40.75, WIDE, ZOOM, 0.6)
    op = ease_io((t - 41.0) / 0.6)
    dry = ease_io((t - 41.6) / 1.4)
    plant(w, t, view, op, dry=dry, air=dry)
    # la main : le bout du majeur s'enfonce de 2-3 cm dans la terre (vu en coupe)
    sx, sy = scr(ZOOM, 512, P.soil_front_y(512))
    depth = 60 * ZOOM[0]
    k = ease_io((t - 45.6) / 0.6)
    tip_y = lerp(sy - 330, sy + depth, k)
    hh = 560
    sc = hh / HAND_SIZE[1]
    cx = sx - (HAND_TIP[0] - HAND_SIZE[0] / 2) * sc
    cy = tip_y - (HAND_TIP[1] - HAND_SIZE[1] / 2) * sc
    spr(w, HAND, cx, cy, hh, life(t, 45.45), shadow=False, anchor="center")
    if k > 0.6:
        particles(w, t, 45.95, sx, sy, 14, 4, col=(150, 110, 70), size=9, up=380)
    mx = scr(ZOOM, 320, 0)[0] - 150
    measure(u, mx, sy, sy + depth, "2-3 cm", life(t, 44.18))
    put(u, icon("sun", 150), 880, 520, life(t, 40.98), t * 25)
    title(u, "LAISSE SÉCHER", t, 40.98, 44.1, y=340)
    title(u, "LE TEST DU DOIGT", t, 45.7, None, y=340, size=120)
    put(u, icon("check", 160), 880, 700, life(t, 47.02), math.sin(t * 5) * 5)
    return w, u


cue(37.66, "pop", 0.3)
cue(39.12, "thud", 0.5)
cue(39.65, "pop_lo", 0.45)
cue(40.75, "whoosh_up", 0.3)
cue(41.0, "whoosh", 0.25)
cue(40.98, "pop_hi", 0.3)
cue(41.6, "sparkle", 0.2)
cue(44.18, "tick", 0.35)
cue(45.45, "pop", 0.3)
cue(46.0, "crunch", 0.4)
cue(47.02, "success", 0.4)


# ============================================================ H. ON REMPOTE (47.8 → 56.1)
ROTTEN = [P.main_roots()[i] for i in (0, 2, 3, 5, 7, 8)]
CUT_T0, CUT_DT = 51.7, 0.27


def s_repot(t):
    w, u = new_layers(background("table"))
    view = cam(t, 50.3, WIDE, ZOOM, 0.6)
    op = ease_io((t - 50.6) / 0.6)
    hidden = tuple(idx for k, idx in enumerate(ROTTEN) if t > CUT_T0 + k * CUT_DT + 0.12)
    plant(w, t, view, op, rot_of=lambda i: 1.0 if i in ROTTEN else 0.05, hidden=hidden)
    # ciseaux : vont couper chaque racine pourrie
    if CUT_T0 - 0.3 < t < CUT_T0 + len(ROTTEN) * CUT_DT + 0.3:
        k = int(clamp((t - CUT_T0) / CUT_DT, 0, len(ROTTEN) - 1))
        tip = scr(ZOOM, *P.root_paths()[ROTTEN[k]]["pts"][10])
        snip = abs(math.sin((t - CUT_T0) * math.pi / CUT_DT)) * 14
        sc_w = 230
        spr(w, A + "ciseaux", tip[0] + sc_w * 0.62, tip[1], 130, rot=180 + snip, shadow=False, anchor="center")
    for k, idx in enumerate(ROTTEN):
        tc = CUT_T0 + k * CUT_DT + 0.12
        if tc < t < tc + 0.9:
            p = scr(ZOOM, *P.root_paths()[idx]["pts"][10])
            particles(w, t, tc, p[0], p[1], 9, 40 + k, col=(40, 28, 18), size=10, up=200, dur=0.9)
    title(u, "TROP TARD ?", t, 47.98, 49.5, y=340)
    title(u, "ON REMPOTE !", t, 49.82, 51.5, y=340, color=YEL)
    tag(u, "NOIRES & MOLLES", 590, 1440, t, 52.3, 53.8, rot=-3, size=46)
    put(u, icon("cross", 110), 270, 1440, life(t, 52.4, 53.8))
    tag(u, "FERMES & CLAIRES", 590, 1440, t, 54.86, rot=-3, size=46)
    put(u, icon("check", 110), 270, 1440, life(t, 55.0))
    return w, u


cue(47.98, "pop", 0.3)
cue(49.82, "rise", 0.3)
cue(50.3, "whoosh_up", 0.3)
cue(50.65, "whoosh", 0.25)
for _k in range(6):
    cue(CUT_T0 + _k * CUT_DT, "chop", 0.4)
cue(52.3, "pop", 0.3)
cue(54.86, "success", 0.35)


# ============================================================ I. LE MÉLANGE QUI RESPIRE (56.1 → 66.95)
def s_mix(t):
    if t < 64.3:
        w, u = new_layers(background("table"))
        xs = [210, 540, 870]
        perlite_pile(w, xs[0], TABLE + 30, 330, life(t, 59.42))
        spr(w, A + "coco", xs[1], TABLE + 30, 400, life(t, 61.58))
        spr(w, A + "terreau", xs[2], TABLE + 30, 210, life(t, 63.58))
        for i, (t0, lab) in enumerate([(58.82, "PERLITE"), (60.3, "COCO"), (62.94, "TERREAU")]):
            put(u, num_badge("1/3", 150), xs[i], 640, life(t, t0))
            put(u, text_img(lab, F_TITLE, 62, YEL, 8, DARK, 6, DARK), xs[i], 770, life(t, t0 + 0.1), -3)
        title(u, "UN MÉLANGE QUI RESPIRE", t, 57.34, None, y=340, size=100)
        return w, u
    w, u = new_layers(background("table"))
    mix = ease_out((t - 64.3) / 0.6)
    plant(w, t, ZOOM, 1.0, healthy=ease_io((t - 64.8) / 1.0), mix=mix, g=ease_out((t - 64.6) / 1.4),
          air=fade(t, 65.4, None, 0.5))
    title(u, "ELLES RESPIRENT !", t, 64.78, None, y=340, color=YEL, size=120)
    sparkles(u, t, 66.4, 540, 1050, 300, 9, 31)
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
cue(65.4, "sparkle", 0.3)
cue(66.42, "sparkle", 0.35)


# ============================================================ J. POT PERCÉ, PAS D'EAU DANS LA SOUCOUPE (66.95 → 71.35)
def s_pot(t):
    w, u = new_layers(background("table"))
    s, px, py = MID
    sw = life(t, 69.42)
    if sw > 0.01:
        saucer(w, px, TABLE + 20, 460 * sw, 1.0, t)
    plant(w, t, MID, 1.0, sick=False, mix=1.0, holes=life(t, 68.38), air=1.0)
    if t > 68.6:
        for i in range(6):
            hx, hy = scr(MID, P.BOT_C[0] + (i % 3 - 1) * 0.55 * P.BOT_R[0], P.BOT_C[1])
            tt = (t - 68.6 - i * 0.17) % 0.9
            put(w, icon("drop", 40), hx, hy + 10 + tt * (TABLE - hy), 1, 0, 1 - tt)
    if sw > 0.01:
        put(u, icon("nosign", 220), 880, TABLE - 60, sw)
    hx, hy = scr(MID, P.BOT_C[0], P.BOT_C[1])
    put(u, icon("arrow_down", 110), hx + 260, hy - 40, life(t, 68.38, 69.3))
    title(u, "UN POT PERCÉ", t, 68.14, 69.3, y=340)
    title(u, "SOUCOUPE VIDE !", t, 69.42, None, y=340, color=YEL)
    return w, u


cue(67.14, "pop", 0.3)
cue(68.38, "pop_hi", 0.35)
cue(68.7, "plop", 0.3)
cue(69.42, "pop_lo", 0.4)


# ============================================================ K. CTA (71.35 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    plant(w, t, WIDE, sick=False)
    sparkles(w, t, 71.5, 540, 900, 380, 9, 40)
    clicked = t > 72.05
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 72.0) / 0.15))
    put(u, btn, 540, 330, life(t, 71.54) * press)
    if t > 71.7:
        k = ease_out((t - 71.7) / 0.32)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(600, 370, k), 1)
    sb = life(t, 73.74)
    put(u, icon("bubble", 210), 850, 520, sb, math.sin(t * 3) * 3)
    if sb > 0.5:
        for i in range(3):
            yy = 497 - 12 * max(0, math.sin(t * 8 - i * 0.9))
            put(u, text_img("•", F_BLACK, 84, DARK), 790 + i * 60, yy - 10, sb)
    put(u, text_img("SAUVETAGE !", F_TITLE, 100, YEL, 11, DARK, 9, DARK), 540, 170, life(t, 75.86), -3)
    return w, u


cue(71.4, "pop_lo", 0.35)
cue(71.5, "sparkle", 0.35)
cue(71.54, "pop_hi", 0.35)
cue(72.03, "click", 0.6)
cue(72.1, "bell", 0.4)
cue(73.74, "pop", 0.4)
cue(75.86, "success", 0.4)

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
