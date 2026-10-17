"""Storyboard « Bouturer les petits fruitiers » (voix : assets/audio/bouture/voix.mp3).

Photos : groseillier en pot et branche de groseillier fournis (la bouture est la vraie tige de la branche,
avec ses bourgeons), cassis, figues, sécateur, crayon (Open Images). Même direction artistique que les autres.
"""
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from gfx import (paste, W, H, YEL, RED, GREEN, CREAM, DARK, background, spr, put, title, life, fade, ease_out, ease_in,
                 ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse, hline, measure, roots,
                 particles, text_img, asset, F_TITLE, F_BLACK)
from scenes import TABLE, new_layers, drop, sparkles, falling

CUES = []


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


B = "bouture/"

# --- repères dans la photo de la tige (tige_longue.png, 68 x 425)
TIGE_H = 425
BUD_TOP, BUD_BOT = 103, 296          # centres des bourgeons
CUT_TOP = 65                          # coupe droite au-dessus du bourgeon du haut
CUT_BL, CUT_BR = 340, 365             # coupe en biais sous le bourgeon du bas


@lru_cache(None)
def tige_parts():
    """(haut coupé, bouture, bas coupé) à partir de la vraie tige."""
    a = np.asarray(asset(B + "tige_longue"))
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    slant = CUT_BL + (CUT_BR - CUT_BL) * xx / w
    parts = []
    for m in (yy < CUT_TOP, (yy >= CUT_TOP) & (yy <= slant), yy > slant):
        b = a.copy()
        b[..., 3] = np.where(m, b[..., 3], 0)
        parts.append(Image.fromarray(b))
    return parts


def stick(c, cx, top, hgt, cut_top=0.0, cut_bot=0.0, flip=False, s=1.0, only_mid=False, alpha=1.0):
    """Tige verticale (haut en `top`, hauteur `hgt`). cut_* = progression de la chute des bouts coupés."""
    if s <= 0.01:
        return
    k = hgt / TIGE_H
    up, mid, lo = tige_parts()
    pieces = [(mid, 0, 0, 0)]
    if not only_mid:
        if cut_top < 1:
            pieces.append((up, -380 * ease_in(cut_top) - 60 * cut_top, -260 * cut_top + 900 * cut_top ** 2, -70 * cut_top))
        if cut_bot < 1:
            pieces.append((lo, 260 * cut_bot, 1100 * ease_in(cut_bot), 80 * cut_bot))
    for im, dx, dy, rot in pieces:
        img = im.resize((max(1, int(im.width * k * s)), max(1, int(im.height * k * s))), Image.BICUBIC)
        if flip:
            img = img.rotate(180)
        if abs(rot) > 0.1:
            img = img.rotate(rot, expand=True, resample=Image.BICUBIC)
        if alpha < 1:
            img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
        cy = top + hgt * s / 2
        paste(c, img, cx + dx - img.width / 2, cy + dy - img.height / 2)


def tige_y(top, hgt, local):
    return top + local * hgt / TIGE_H


def bouture_img_h(hgt):
    """Hauteur d'affichage de la bouture recoupée pour une tige de hauteur hgt."""
    return hgt * (CUT_BR - CUT_TOP) / TIGE_H


def cutting(c, cx, bottom, h, s=1.0, leaves=0.0, root_g=0.0, seed=1, flip=False):
    """Bouture (photo) posée par sa base, avec feuilles qui débourrent et racines."""
    if s <= 0.01:
        return
    if root_g > 0.01:
        roots(c, cx, bottom - 10 * s, root_g, seed, spread=60, length=170 * s, n=9)
    spr(c, B + "bouture", cx, bottom, h, s, shadow=False, rot=180 if flip else 0)
    if leaves > 0.01:
        top = bottom - h * s
        # feuilles (photo) qui partent du bourgeon du haut, en éventail
        for k, (ang, sc) in enumerate([(135, 1.0), (45, 0.95), (95, 0.8)]):
            g = clamp(leaves * 1.4 - k * 0.2)
            if g <= 0.01:
                continue
            L = 130 * sc * g * s
            im = asset(B + "feuille")
            im = im.resize((max(1, int(L)), max(1, int(L * im.height / im.width))), Image.BICUBIC)
            if ang < 90:
                im = im.transpose(Image.FLIP_LEFT_RIGHT).rotate(ang, expand=True, resample=Image.BICUBIC)
            else:
                im = im.rotate(ang - 180, expand=True, resample=Image.BICUBIC)
            r = math.radians(ang)
            px, py = cx + math.cos(r) * L * 0.45, top + 14 * s - math.sin(r) * L * 0.45
            paste(c, im, px - im.width / 2, py - im.height / 2)


def wind(c, t, x0, y0, a=1.0):
    if a <= 0.01:
        return
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(4):
        ph = (t * 1.3 + i * 0.27) % 1
        y = y0 + i * 70
        x = x0 + 300 - ph * 600
        pts = [(x + k * 18, y + 14 * math.sin(k / 3 + t * 6)) for k in range(14)]
        al = int(255 * a * math.sin(math.pi * ph))
        d.line(pts, fill=(29, 43, 31, al), width=14, joint="curve")
        d.line(pts, fill=(235, 245, 255, al), width=7, joint="curve")
    c.alpha_composite(ov)


# ============================================================ A. TU TAILLES… TU JETTES ? (0 → 2.8)
def s_prune(t):
    w, u = new_layers(background("table"))
    spr(w, B + "groseillier_pot", 470, TABLE + 40, 900, life(t, 0.0, dur=0.4))
    spr(w, "poireau/trash", 880, TABLE, 360, life(t, 1.4))
    if 0.55 < t < 1.6:
        snip = abs(math.sin((t - 0.55) * 9)) * 16
        spr(w, B + "secateur", 820, 640, 220, life(t, 0.55, 1.5), rot=-20 + snip, shadow=False, anchor="center")
    if t > 1.45:
        k = clamp((t - 1.45) / 0.9)
        x = lerp(760, 880, k)
        y = lerp(640, TABLE - 300, ease_in(k))
        spr(w, B + "branche", x, y, lerp(380, 200, k), 1 - clamp((t - 2.25) / 0.2), rot=-60 * k, shadow=False,
            anchor="center")
    title(u, "TU TAILLES ?", t, 0.17, 1.4, y=300)
    title(u, "TU JETTES ?", t, 1.74, None, y=300)
    return w, u


cue(0.05, "pop_lo", 0.4)
cue(0.17, "pop", 0.3)
cue(0.7, "chop", 0.5)
cue(1.0, "chop", 0.4)
cue(1.4, "pop", 0.3)
cue(1.5, "whoosh", 0.3)
cue(2.3, "thud", 0.45)


# ============================================================ B. NON ! DES PLANTS GRATUITS (2.8 → 6.55)
def s_free(t):
    w, u = new_layers(background("table"))
    if t < 4.0:
        spr(w, "poireau/trash", 540, TABLE, 460)
        shake = math.sin(t * 45) * 8 * fade(t, 2.87, 3.3)
        put(u, icon("cross", 260), 540 + shake, 900, life(t, 2.87, 3.9))
        title(u, "NON !", t, 2.87, 3.9, y=340, color=RED, size=230)
        return w, u
    for i, x in enumerate((250, 540, 830)):
        t0 = 5.11 + i * 0.15
        cutting(w, x, TABLE - 120, 330, life(t, t0), leaves=ease_out((t - t0 - 0.2) / 0.6), root_g=ease_out((t - t0) / 0.7),
                seed=3 + i)
    tag(u, "GRATUITS !", 560, 1000, t, 5.59, rot=-4, size=58)
    title(u, "TU JETTES…", t, 4.1, 5.0, y=340)
    title(u, "DES PLANTS !", t, 5.11, None, y=340, color=YEL, size=150)
    sparkles(u, t, 5.6, 540, 820, 380, 9, 3)
    return w, u


cue(2.87, "fail", 0.4)
cue(2.9, "pop_lo", 0.4)
cue(4.0, "whoosh_up", 0.3)
for _i in range(3):
    cue(5.11 + _i * 0.15, "pop", 0.35)
cue(5.59, "success", 0.4)


# ============================================================ C. GROSEILLIERS, CASSISSIERS, FIGUIERS (6.55 → 9.35)
def s_trio(t):
    w, u = new_layers(background("table"))
    spr(w, B + "branche", 230, TABLE, 400, life(t, 6.65))
    spr(w, B + "cassis", 560, TABLE, 470, life(t, 7.67))
    spr(w, B + "figues", 870, TABLE, 280, life(t, 8.46))
    tag(u, "GROSEILLIER", 230, 1420, t, 6.75, rot=-5, size=40)
    tag(u, "CASSISSIER", 560, 1420, t, 7.77, rot=4, size=40)
    tag(u, "FIGUIER", 870, 1420, t, 8.56, rot=-4, size=40)
    title(u, "LES PETITS FRUITIERS", t, 6.65, None, y=340, size=110)
    return w, u


for _t0 in (6.65, 7.67, 8.46):
    cue(_t0, "pop", 0.4)
    cue(_t0 + 0.1, "pop_hi", 0.25)


# ============================================================ D. DÈS QUE LES FEUILLES TOMBENT (9.35 → 12.8)
def s_fall(t):
    w, u = new_layers(background("table"))
    spr(w, B + "groseillier_pot", 540, TABLE + 40, 900)
    if t > 9.9:
        r = np.random.default_rng(8)
        for i in range(16):
            t0 = 9.9 + r.uniform(0, 1.6)
            if t < t0:
                continue
            k = t - t0
            x0 = r.uniform(180, 900)
            y = 520 + r.uniform(-100, 150) + 260 * k
            x = x0 + 50 * math.sin(k * 3 + i)
            if y > TABLE + 60:
                y = TABLE + 60
            spr(w, B + f"feuille_automne{i % 3}", x, y, 60, rot=math.sin(k * 4 + i) * 60, shadow=False, anchor="center")
    act = -1 if t < 10.4 else (0 if t < 10.7 else (1 if t < 11.0 else 2))
    pills(u, ["OCT", "NOV", "DÉC"], act, t, 10.3, None, y=470)
    title(u, "LES FEUILLES TOMBENT", t, 9.97, 11.5, y=320, size=110)
    title(u, "SUPER FACILE !", t, 11.57, None, y=320, color=YEL)
    put(u, icon("check", 170), 880, 700, life(t, 11.98), math.sin(t * 5) * 5)
    return w, u


cue(9.9, "whoosh", 0.2)
cue(10.3, "pop", 0.3)
for _k in range(3):
    cue(10.4 + _k * 0.3, "tick", 0.3)
cue(11.57, "pop_hi", 0.35)
cue(11.98, "success", 0.4)


# ============================================================ E. ÉTAPE 1 : BRANCHE DE L'ANNÉE (12.8 → 16.5)
def s_step1(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("1", 170), 540, 560, life(t, 12.98, 14.0))
    title(u, "ÉTAPE 1", t, 12.98, 14.0, y=340)
    if t > 13.9 and t < 15.15:
        spr(w, B + "branche", 540, TABLE, 760, life(t, 13.9, 15.1))
        title(u, "BRANCHE DE L'ANNÉE", t, 14.22, 15.1, y=340, size=105)
    if t > 15.15:
        stick(w, 420, 420, 860, only_mid=False, s=life(t, 15.15))
        cr = asset(B + "crayon").rotate(-45.5, expand=True, resample=Image.BICUBIC)
        cr = cr.crop(cr.getbbox())
        put(w, cr, 660, 850, life(t, 15.6) * 780 / cr.height)
        title(u, "= UN CRAYON", t, 15.62, None, y=290, color=YEL)
        put(u, text_img("≈ 1 cm", F_TITLE, 70, CREAM, 8, DARK, 6, DARK), 540, 1380, life(t, 15.9))
    return w, u


cue(12.98, "rise", 0.3)
cue(13.0, "pop", 0.35)
cue(13.9, "pop_lo", 0.35)
cue(15.15, "whoosh", 0.25)
cue(15.6, "pop", 0.35)
cue(15.9, "pop_hi", 0.3)


# ============================================================ F. ÉTAPE 2 : COUPE 20 CM, BIAIS / DROIT (16.5 → 26.2)
ST_X, ST_TOP, ST_H = 540, 330, 960


def s_step2(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("2", 170), 820, 560, life(t, 16.62, 17.9))
    title(u, "ÉTAPE 2", t, 16.62, 17.4, y=300)
    cut_bot = clamp((t - 20.3) / 0.8)
    cut_top = clamp((t - 22.45) / 0.8)
    if t < 23.9:
        stick(w, ST_X, ST_TOP, ST_H, cut_top, cut_bot, s=life(t, 16.7))
        yt, yb = tige_y(ST_TOP, ST_H, CUT_TOP), tige_y(ST_TOP, ST_H, (CUT_BL + CUT_BR) / 2)
        measure(u, 760, yt, yb, "20 cm", life(t, 17.9, 19.0))
        # bas : en biais sous un bourgeon
        hl_ellipse(w, ST_X + 12, tige_y(ST_TOP, ST_H, BUD_BOT), 70, 70, life(t, 20.4, 21.3))
        if 19.6 < t < 20.6:
            snip = abs(math.sin((t - 19.6) * 8)) * 14
            spr(w, B + "secateur", ST_X + 117, tige_y(ST_TOP, ST_H, CUT_BR) + 74, 230, rot=-snip,
                shadow=False, anchor="center")
        # haut : droit au-dessus d'un bourgeon
        hl_ellipse(w, ST_X + 12, tige_y(ST_TOP, ST_H, BUD_TOP), 70, 70, life(t, 22.6, 23.8))
        if 21.8 < t < 22.8:
            snip = abs(math.sin((t - 21.8) * 8)) * 14
            spr(w, B + "secateur", ST_X + 117, tige_y(ST_TOP, ST_H, CUT_TOP) + 74, 230, rot=-snip,
                shadow=False, anchor="center")
        title(u, "EN BIAIS EN BAS", t, 20.14, 21.3, y=300, size=120)
        title(u, "DROIT EN HAUT", t, 22.3, 23.85, y=300, size=120)
        return w, u
    # jamais à l'envers : la bouture, avec ses repères
    flip = 24.86 < t < 25.55
    hb = bouture_img_h(ST_H)
    bottom = 1300
    cutting(w, 540, bottom, hb, life(t, 23.95), flip=flip)
    top = bottom - hb
    put(u, text_img("HAUT = DROIT", F_TITLE, 66, YEL, 8, DARK, 6, DARK), 790, top + 60, life(t, 24.3), -3)
    put(u, text_img("BAS = BIAIS", F_TITLE, 66, YEL, 8, DARK, 6, DARK), 790, bottom - 60, life(t, 24.5), 3)
    hline(w, 470, 610, top + 4, ease_out((t - 24.3) / 0.3), 8)
    put(u, icon("cross", 170), 300, 800, fade(t, 24.9, 25.5, 0.1, 0.1))
    put(u, icon("check", 170), 300, 800, life(t, 25.62))
    title(u, "JAMAIS À L'ENVERS", t, 24.4, None, y=300, size=115)
    return w, u


cue(16.62, "rise", 0.3)
cue(16.7, "pop", 0.35)
cue(17.9, "tick", 0.35)
cue(18.14, "pop_hi", 0.3)
cue(19.66, "whoosh", 0.25)
cue(20.3, "chop", 0.6)
cue(20.4, "pop_hi", 0.25)
cue(21.94, "whoosh", 0.25)
cue(22.45, "chop", 0.6)
cue(22.6, "pop_hi", 0.25)
cue(23.95, "whoosh_up", 0.3)
cue(24.9, "fail", 0.3)
cue(25.62, "success", 0.4)


# ============================================================ G. ÉTAPE 3 : 2/3 EN TERRE, TERRE LÉGÈRE, ABRI DU VENT (26.2 → 31.0)
SOIL = 1000
HB = 600


def s_step3(t):
    w, u = new_layers(background("none", SOIL))
    put(u, num_badge("3", 170), 830, 600, life(t, 26.42, 27.3))
    title(u, "ÉTAPE 3", t, 26.42, 27.3, y=300)
    k = ease_io((t - 27.4) / 0.8)
    bottom = lerp(SOIL - 40, SOIL + HB * 2 / 3, k)
    cutting(w, 540, bottom, HB, life(t, 26.5))
    if k > 0.5:
        particles(w, t, 27.8, 540, SOIL, 12, 5, col=(150, 110, 70), size=9, up=360)
    measure(u, 760, SOIL + 6, SOIL + HB * 2 / 3, "2/3", life(t, 28.3))
    measure(u, 760, SOIL - HB / 3, SOIL - 6, "1/3", life(t, 28.5))
    title(u, "ENFONCE AUX 2/3", t, 27.34, 29.0, y=300, size=120)
    title(u, "TERRE LÉGÈRE", t, 29.1, 29.85, y=300)
    title(u, "À L'ABRI DU VENT", t, 30.0, None, y=300, size=115)
    wind(u, t, 680, 560, fade(t, 30.0, None, 0.3))
    put(u, icon("nosign", 230), 840, 650, life(t, 30.3))
    return w, u


cue(26.42, "rise", 0.3)
cue(26.5, "pop", 0.3)
cue(27.45, "whoosh", 0.25)
cue(27.85, "crunch", 0.45)
cue(28.3, "tick", 0.3)
cue(29.1, "pop_hi", 0.3)
cue(30.0, "whoosh_up", 0.3)
cue(30.3, "pop_lo", 0.4)


# ============================================================ H. ÉTAPE 4 : TU L'OUBLIES TOUT L'HIVER (31.0 → 33.6)
def s_step4(t):
    w, u = new_layers(background("none", SOIL, darken=0.15))
    cutting(w, 540, SOIL + HB * 2 / 3, HB)
    falling(u, t, 31.3, None, "snow", 18, 9, 240, 56, bottom=SOIL, sway=30)
    put(u, num_badge("4", 170), 830, 640, life(t, 31.18, 32.1))
    title(u, "ÉTAPE 4", t, 31.18, 32.1, y=300)
    act = -1 if t < 32.3 else (0 if t < 32.6 else (1 if t < 32.9 else 2))
    pills(u, ["DÉC", "JANV", "FÉV"], act, t, 32.2, None, y=470)
    title(u, "TU L'OUBLIES !", t, 32.22, None, y=300)
    for i in range(3):
        ph = (t * 0.8 + i / 3) % 1
        put(u, text_img("z", F_TITLE, 60 + 20 * i, CREAM, 8, DARK, 6, DARK), 640 + 40 * i + 20 * ph,
            760 - 90 * i - 40 * ph, life(t, 32.6 + i * 0.12), 0, 1 - ph * 0.6)
    return w, u


cue(31.18, "rise", 0.3)
cue(31.3, "sparkle", 0.2)
cue(32.3, "tick", 0.3)
cue(32.6, "tick", 0.3)
cue(32.9, "tick", 0.3)
cue(32.22, "pop", 0.3)


# ============================================================ I. AU PRINTEMPS : RACINES ET NOUVEAUX PLANTS (33.6 → 37.3)
def s_spring(t):
    w, u = new_layers(background("none", SOIL, warm=fade(t, 33.9, None, 0.6)))
    if t < 36.2:
        cutting(w, 540, SOIL + HB * 2 / 3, HB, leaves=ease_out((t - 34.1) / 1.4), root_g=ease_out((t - 35.1) / 1.0))
        put(u, icon("sun", 190), 860, 520, life(t, 33.85), t * 25)
        title(u, "AU PRINTEMPS", t, 33.85, 35.0, y=300)
        title(u, "DES RACINES !", t, 35.15, None, y=300, color=YEL)
    else:
        for i, x in enumerate((250, 540, 830)):
            cutting(w, x, SOIL + 260, 380, life(t, 36.2 + i * 0.12), leaves=1.0, root_g=1.0, seed=10 + i)
        title(u, "DE NOUVEAUX PLANTS !", t, 36.3, None, y=300, color=YEL, size=110)
        sparkles(u, t, 36.8, 540, 820, 400, 9, 8)
    return w, u


cue(33.85, "sparkle", 0.35)
cue(33.9, "pop", 0.3)
cue(35.15, "rise", 0.3)
cue(36.2, "whoosh_up", 0.3)
cue(36.3, "pop", 0.3)
cue(36.42, "pop_hi", 0.3)
cue(36.54, "pop", 0.3)
cue(36.8, "success", 0.4)


# ============================================================ J. CTA (37.3 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    spr(w, B + "groseillier_pot", 540, TABLE + 40, 860, life(t, 37.35))
    sparkles(w, t, 37.5, 540, 900, 380, 9, 40)
    clicked = t > 38.0
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 37.95) / 0.15))
    put(u, btn, 540, 330, life(t, 37.46) * press)
    if t > 37.65:
        k = ease_out((t - 37.65) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(600, 370, k), 1)
    put(u, text_img("ASTUCES POTAGER", F_TITLE, 96, YEL, 10, DARK, 8, DARK), 540, 170, life(t, 38.54), -3)
    return w, u


cue(37.35, "pop_lo", 0.35)
cue(37.46, "pop_hi", 0.35)
cue(37.98, "click", 0.6)
cue(38.05, "bell", 0.4)
cue(38.54, "sparkle", 0.35)

SCENES = [
    (0.0, 2.8, s_prune),
    (2.8, 6.55, s_free),
    (6.55, 9.35, s_trio),
    (9.35, 12.8, s_fall),
    (12.8, 16.5, s_step1),
    (16.5, 26.2, s_step2),
    (26.2, 31.0, s_step3),
    (31.0, 33.6, s_step4),
    (33.6, 37.3, s_spring),
    (37.3, 99.0, s_cta),
]

TRAPS = [(1, 12.9, 16.5), (2, 16.55, 26.2), (3, 26.25, 31.0), (4, 31.05, 33.6)]
