"""Ananas — VERSION 2 : même voix, mêmes photos fournies, mise en scène différente.

Différences avec la v1 : tampon « ERREUR », chronologie tête → racines → plant, comparaison bon / mauvais
ananas, couronne qui pivote en 3D, avant / après, 3 têtes qui sèchent (J1-J3), gros plan sur la base dans
l'eau, compteur de semaines, coupe du pot avec racines visibles, barre de progression 0 → 3 ans.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, spr, put, paste, title, life, fade,
                 ease_out, ease_in, ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse,
                 measure, particles, text_img, asset, aa, glass_back, glass_front, water, shadow_blob, F_TITLE, F_BLACK)
from scenes import TABLE, new_layers, flies, sparkles, falling
from scenes_aromatiques import pot
from scenes_arrosage import can_center_for_spout
import scenes_ananas as V1
from scenes_ananas import (A, AN_BOX, CROWN_BOX, TETE_BOX, TR_BOX, STEM_Y, place, head, head_roots, bag, gas,
                           logo_img, mound)

CUES = []
HAS_VIDEO = V1.HAS_VIDEO
VID_END = V1.VID_END
NO_CAPTION_UNTIL = VID_END
s_video = V1.s_video


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


FRUIT_BOX = (300, 452, 731, 986)


def stamp(c, txt, x, y, t, t0, color=RED, size=150, rot=-12):
    """Tampon qui s'écrase (grand → taille normale) avec un cadre."""
    if t < t0:
        return
    k = clamp((t - t0) / 0.18)
    s = lerp(2.2, 1.0, ease_out(k))
    ti = text_img(txt, F_TITLE, size, color, 0)
    w, h = ti.width + 70, ti.height + 40
    im = aa(w, h, lambda d, kk, _: (
        d.rounded_rectangle([0, 0, w * kk - 1, h * kk - 1], radius=24 * kk, outline=color, width=int(12 * kk)),))
    im.alpha_composite(ti, (35, 20))
    put(c, im, x, y, s, rot, alpha=clamp(k * 1.5))


def progress_bar(c, x0, x1, y, p, labels, t, t0):
    s = life(t, t0)
    if s <= 0.01:
        return
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([x0 - 8, y - 30, x1 + 8, y + 30], radius=30, fill=DARK)
    d.rounded_rectangle([x0, y - 22, x1, y + 22], radius=22, fill=CREAM)
    if p > 0.01:
        d.rounded_rectangle([x0, y - 22, x0 + (x1 - x0) * clamp(p), y + 22], radius=22, fill=YEL)
    for i, lab in enumerate(labels):
        x = x0 + (x1 - x0) * i / (len(labels) - 1)
        put(c, text_img(lab, F_BLACK, 40, DARK), x, y + 70, s)


# ============================================================ A. ERREUR (0 → 3.0)
BIN = A + "poubelle"
BIN_RIM = 218            # bas du couvercle dans poubelle.png
BIN_HINGE = (432, 212)   # charnière du couvercle (côté droit)
BIN_X, BIN_H = 730, 540
IN_K = 0.62              # échelle de la couronne lancée


@lru_cache(64)
def _bin_parts(h):
    im = asset(BIN)
    k = h / im.height
    sz = lambda c: c.resize((max(1, int(c.width * k)), max(1, int(c.height * k))), Image.BICUBIC)
    return k, sz(im.crop((0, 0, im.width, BIN_RIM + 2))), sz(im.crop((0, BIN_RIM - 4, im.width, im.height)))


def trash_bin(c, cx, base, h, lid=0.0, s=1.0, inside=None):
    """Poubelle photo dont le couvercle bascule (lid en degrés) ; inside(c) est dessiné DANS la poubelle."""
    if s <= 0.01:
        return
    k, lid_im, body = _bin_parts(int(h * s))
    im_w = asset(BIN).width
    x0, y0 = cx - im_w * k / 2, base - asset(BIN).height * k
    P = lambda px, py: (x0 + px * k, y0 + py * k)
    sb = shadow_blob().resize((int(im_w * k * 1.2), max(2, int(im_w * k * 0.28))))
    c.alpha_composite(sb, (int(cx - sb.width / 2), int(base - sb.height * 0.55)))
    if lid > 2:
        d = ImageDraw.Draw(c)
        d.polygon([P(28, 192), P(420, 192), P(416, 226), P(32, 226)], fill=(26, 24, 22))
        d.polygon([P(40, 196), P(408, 196), P(404, 206), P(44, 206)], fill=(52, 49, 46))
    if inside:
        inside(c)
    paste(c, body, *P(0, BIN_RIM - 4))
    hx, hy = BIN_HINGE[0] * k, BIN_HINGE[1] * k
    D = int(2 * max(lid_im.width, lid_im.height)) + 4
    can = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    can.alpha_composite(lid_im, (int(D / 2 - hx), int(D / 2 - hy)))
    if lid > 0.5:
        can = can.rotate(-lid, center=(D / 2, D / 2), resample=Image.BICUBIC)
    X, Y = P(*BIN_HINGE)
    paste(c, can, X - D / 2, Y - D / 2)


def bin_rim_y():
    return TABLE + 10 - (asset(BIN).height - BIN_RIM) * BIN_H / asset(BIN).height


def crown_path(t):
    """Position (x, y du centre), rotation et visibilité de la couronne lancée."""
    ch = (CROWN_BOX[3] - CROWN_BOX[1]) * IN_K
    sx, sy = 270, TABLE + 40 - (986 - 468) * 0.8 - ch / 2          # posée sur le fruit
    ex, ey = BIN_X, bin_rim_y() + ch * 0.5 - 135                     # au fond de la poubelle
    if t < 0.62:
        return sx, sy, 0.0
    if t < 1.12:                                                    # vol en cloche + 1 tour
        p = ease_io((t - 0.62) / 0.5)
        return lerp(sx, ex, p), lerp(sy, ey - 40, p) - math.sin(math.pi * p) * 330, -360 * p
    if t < 2.5:                                                     # tombe dedans
        p = ease_out((t - 1.12) / 0.18)
        return ex, lerp(ey - 40, ey, p), 0.0
    # « non ! » : elle ressort de la poubelle et revient à gauche
    p = ease_io((t - 2.5) / 0.45)
    return lerp(ex, 190, p), lerp(ey, TABLE + 20 - ch / 2, p) - math.sin(math.pi * p) * 300, 360 * p


def s_intro(t):
    w, u = new_layers(background("table"))
    lid = 68 * ease_out((t - 0.5) / 0.22)
    shake = math.sin(t * 55) * 9 * fade(t, 1.14, 1.5) if t > 1.14 else 0.0
    cx, cy, rot = crown_path(t)
    ch = (CROWN_BOX[3] - CROWN_BOX[1]) * IN_K
    crown = lambda c: spr(c, A + "couronne", cx, cy, ch, life(t, 0.0, dur=0.35), rot=rot, shadow=False,
                          anchor="center")
    inside = 1.12 <= t < 2.5
    place(w, A + "fruit", FRUIT_BOX, 0.8, 510, 986, 270, TABLE + 40, life(t, 0.0, dur=0.35))
    trash_bin(w, BIN_X + shake, TABLE + 10, BIN_H, lid, life(t, 0.12, dur=0.35), crown if inside else None)
    if not inside:
        crown(w)
    if 0.62 < t < 2.5:                                             # traînée pointillée
        d = ImageDraw.Draw(u)
        for i in range(14):
            q = i / 13
            if q > clamp((t - 0.62) / 0.5):
                break
            px = lerp(270, BIN_X, ease_io(q))
            py = lerp(crown_path(0)[1], bin_rim_y() - 60, ease_io(q)) - math.sin(math.pi * ease_io(q)) * 330
            a = int(235 * (1 - clamp((t - 1.95) / 0.3)))
            if a > 0:
                d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=YEL + (a,))
    if t > 1.14:
        particles(w, t, 1.14, BIN_X, bin_rim_y() - 10, 10, 9, col=(120, 100, 70), size=9, up=260)
    title(u, "TU LA JETTES ?", t, 0.46, 2.0, y=330, size=140)
    if 2.26 <= t < 2.55:
        put(u, icon("cross", 260), BIN_X, TABLE - 260, life(t, 2.26))
    stamp(u, "ERREUR !", 540, 360, t, 2.26)
    return w, u


cue(0.05, "pop_lo", 0.35)
cue(0.5, "click", 0.4)
cue(0.62, "whoosh", 0.35)
cue(1.12, "thud", 0.5)
cue(2.26, "alert1", 0.45)
cue(2.5, "whoosh_up", 0.35)


def s_error(t):
    w, u = new_layers(background("table"))
    spr(w, "poireau/trash", 540, TABLE + 10, 440, life(t, VID_END))
    stamp(u, "ERREUR !", 540, 420, t, 2.26)
    return w, u


# ============================================================ B. CHRONOLOGIE TÊTE → PLANT (3.0 → 6.9)
def s_timeline(t):
    w, u = new_layers(background("table"))
    head(w, 190, TABLE + 20, 0.5, life(t, 3.14))
    head_roots(w, 540, TABLE - 160, 0.46, 1.0, life(t, 3.9))
    spr(w, A + "plant", 880, TABLE + 30, 600, life(t, 4.86))
    for x, t0 in ((365, 3.7), (715, 4.66)):
        put(u, icon("arrow_down", 90), x, TABLE - 160, life(t, t0), 90)
    hline_y = TABLE + 75
    d = ImageDraw.Draw(u)
    p = ease_io((t - 3.14) / 2.2)
    if p > 0:
        d.line([(120, hline_y), (120 + 840 * p, hline_y)], fill=DARK, width=14)
        d.line([(120, hline_y), (120 + 840 * p, hline_y)], fill=YEL, width=7)
    for x, lab, t0 in ((190, "TÊTE", 3.2), (540, "RACINES", 3.95), (880, "ANANAS", 4.9)):
        put(u, text_img(lab, F_TITLE, 50, YEL, 7, DARK, 6, DARK), x, hline_y, life(t, t0))
    title(u, "UN NOUVEL ANANAS", t, 3.14, None, y=330, size=130)
    put(u, icon("lightbulb", 150), 540, 560, life(t, 5.9), math.sin(t * 4) * 5)
    return w, u


cue(3.14, "pop", 0.3)
cue(3.9, "pop", 0.28)
cue(4.86, "pop_lo", 0.35)
cue(5.9, "sparkle", 0.3)


# ============================================================ C. BON / MAUVAIS ANANAS (6.9 → 13.5)
def s_compare(t):
    w, u = new_layers(background("table"))
    k = 0.66
    place(w, A + "ananas", AN_BOX, k, 510, 986, 300, TABLE + 40, life(t, 7.0))
    place(w, A + "ananas", AN_BOX, k, 510, 986, 790, TABLE + 40, life(t, 7.15),
          rotten=0.75 * clamp((t - 10.9) / 0.5))
    if t > 9.6:
        put(u, icon("check", 150), 300, 560, life(t, 9.62))
    if t > 10.9:
        put(u, icon("cross", 150), 790, 560, life(t, 11.1))
        tag(u, "TACHES BRUNES", 790, 700, t, 11.1, 12.0, rot=4, size=40)
    if t > 12.0:
        # jauge de maturité
        x0, x1, y = 160, 920, 1405
        d = ImageDraw.Draw(u)
        cols = [(110, 170, 70), (247, 199, 52), (196, 110, 50)]
        for i, col in enumerate(cols):
            a = x0 + (x1 - x0) * i / 3
            b = x0 + (x1 - x0) * (i + 1) / 3
            d.rectangle([a, y - 24, b, y + 24], fill=col)
        d.rounded_rectangle([x0 - 6, y - 30, x1 + 6, y + 30], radius=10, outline=DARK, width=8)
        px = lerp(x0, (x0 + x1) / 2, ease_out((t - 12.1) / 0.9))
        d.polygon([(px - 24, y - 64), (px + 24, y - 64), (px, y - 30)], fill=DARK)
        for i, lab in enumerate(["VERT", "MÛR", "TROP"]):
            put(u, text_img(lab, F_BLACK, 34, WHITE, 5, DARK), x0 + (x1 - x0) * (i + 0.5) / 3, y, life(t, 12.1))
    title(u, "CHOISIS BIEN", t, 6.98, 9.5, y=330)
    title(u, "BIEN VERT", t, 9.62, 10.85, y=330, color=GREEN if False else YEL)
    title(u, "PAS DE TACHES", t, 10.9, 12.0, y=330, color=RED)
    title(u, "MÛR, PAS TROP", t, 12.02, None, y=330, size=135)
    return w, u


cue(7.0, "pop", 0.3)
cue(7.15, "pop", 0.25)
cue(9.62, "ding", 0.3)
cue(11.1, "pop_lo", 0.3)
cue(12.1, "rise", 0.25)


# ============================================================ D. ÉTAPE 1 : LA COURONNE PIVOTE EN 3D (13.5 → 17.3)
def s_step1(t):
    w, u = new_layers(background("table"))
    k = 0.92
    p = ease_io((t - 16.18) / 0.8)
    place(w, A + "fruit", FRUIT_BOX, k, 510, 986, 540 - 215 * p, TABLE + 40)
    spin = 0.0
    if t > 14.66:
        spin = (t - 14.66) * 9
    sx = 0.55 + 0.45 * abs(math.cos(spin)) if 14.66 < t < 16.4 else 1.0
    # la couronne se soulève puis atterrit à droite, posée sur la table
    X = 540 + 245 * p
    Y = lerp(TABLE + 40 - (986 - 468) * k, TABLE + 40, p) - math.sin(math.pi * p) * 170
    ch = CROWN_BOX[3] - CROWN_BOX[1]
    spr(w, A + "couronne", X, Y - ch * k / 2, ch * k, sx=sx, shadow=False, anchor="center",
        flip=math.cos(spin) < 0, rot=-14 * math.sin(math.pi * p))
    if t > 16.2:
        sparkles(w, t, 16.2, 540, TABLE + 40 - (986 - 468) * k, 200, 8, 3)
    put(u, num_badge("1", 160), 190, 560, life(t, 13.62, 14.6))
    title(u, "ÉTAPE 1", t, 13.62, 14.6, y=330)
    title(u, "TOURNE…", t, 14.66, 16.1, y=330, size=170)
    title(u, "…ET DÉTACHE", t, 16.18, None, y=330, size=128, color=YEL)
    return w, u


cue(13.62, "rise", 0.25)
cue(14.7, "stir", 0.35)
cue(15.4, "stir", 0.3)
cue(16.2, "pop_lo", 0.4)


# ============================================================ E. ÉTAPE 2 : AVANT / APRÈS (17.3 → 22.4)
def s_step2(t):
    w, u = new_layers(background("table"))
    k = 0.78
    place(w, A + "couronne", CROWN_BOX, k, 510, 468, 290, TABLE - 40, life(t, 17.42))
    if t > 18.9:
        head(w, 790, TABLE - 40, k, life(t, 18.9))
        hl_ellipse(w, 790, TABLE - 70, 140, 70, life(t, 20.0))
        if t > 20.62:
            tag(u, "2-3 CM", 905, TABLE - 190, t, 20.62, None, rot=-6, size=48, string_to=(840, TABLE - 90))
    put(u, text_img("AVANT", F_TITLE, 70, CREAM, 8, DARK, 7, DARK), 290, TABLE + 130, life(t, 17.6), -4)
    put(u, text_img("APRÈS", F_TITLE, 70, YEL, 8, DARK, 7, DARK), 790, TABLE + 130, life(t, 19.0), 4)
    put(u, icon("arrow_down", 110), 540, TABLE - 250, life(t, 18.7), 90)
    put(u, num_badge("2", 160), 190, 560, life(t, 17.42, 18.3))
    title(u, "ÉTAPE 2", t, 17.42, 18.2, y=330)
    title(u, "DÉGAGE LA TIGE", t, 18.26, None, y=330, size=135)
    return w, u


cue(17.42, "rise", 0.25)
cue(18.9, "crunch", 0.35)
cue(19.0, "pop", 0.25)
cue(20.62, "tick", 0.3)


# ============================================================ F. SÉCHER J1 → J3 (22.4 → 26.4)
def s_dry(t):
    w, u = new_layers(background("table"))
    for i, x in enumerate((220, 540, 860)):
        t0 = 24.34 + i * 0.2
        rot = 0.0
        if i == 2:
            rot = clamp((t - 25.5) / 0.6)
        head(w, x, TABLE - 40, 0.5, life(t, 22.5 if i == 0 else t0), rotten=rot)
        put(u, num_badge(f"J{i + 1}", 120), x, TABLE + 120, life(t, t0))
    put(u, icon("sun", 160), 880, 560, life(t, 23.94, 25.3), t * 25)
    if t > 25.3:
        put(u, icon("cross", 150), 860, TABLE - 360, life(t, 25.5))
        flies(w, t, 25.8, None, 860, TABLE - 300, 140)
    put(u, icon("lightbulb", 150), 190, 560, life(t, 22.54, 23.4), math.sin(t * 4) * 5)
    title(u, "PETIT SECRET", t, 22.54, 23.4, y=330)
    title(u, "2-3 JOURS AU SEC", t, 23.5, 25.25, y=330, size=130)
    title(u, "SINON… POURRIE !", t, 25.3, None, y=330, color=RED, size=130)
    return w, u


cue(22.54, "sparkle", 0.3)
for _i in range(3):
    cue(24.34 + _i * 0.2, "tick", 0.3)
cue(25.5, "squish", 0.25)
cue(25.74, "fail", 0.32)


# ============================================================ G. ÉTAPE 3 : GROS PLAN BASE DANS L'EAU (26.4 → 32.2)
GX, GW, GH, GWATER = 540, 470, 640, 0.55
HEAD_K = 0.78


def glass_scene(c, t, roots_g=None, lvl=GWATER, rotten=0.0):
    glass_back(c, GX, TABLE, GW, GH)
    base = TABLE - 26 - (GH - 26) * GWATER + 50
    if roots_g is None:
        head(c, GX, base, HEAD_K)
    else:
        head_roots(c, GX, base, HEAD_K, roots_g, rotten=rotten)
    glass_front(c, GX, TABLE, lvl, t, GW, GH)
    return base


def zoomed(img, z, cy):
    """Zoom caméra centré horizontalement, point vertical cy conservé."""
    if z <= 1.001:
        return img
    cw, ch = W / z, H / z
    y0 = clamp(cy - ch / 2, 0, H - ch)
    return img.crop((int((W - cw) / 2), int(y0), int((W + cw) / 2), int(y0 + ch))).resize((W, H), Image.BICUBIC)


def s_step3(t):
    w, u = new_layers(background("table"))
    lvl = GWATER
    if 30.98 < t < 32.0:
        lvl = GWATER * (1 - 0.8 * math.sin(math.pi * (t - 30.98) / 1.02))
    base = glass_scene(w, t, lvl=lvl)
    z = 1 + 0.45 * ease_io((t - 27.4) / 0.6) * (1 - ease_io((t - 29.6) / 0.5))
    w = zoomed(w, z, base)
    if 27.6 < t < 29.6:
        put(u, text_img("JUSTE LA BASE", F_TITLE, 70, YEL, 8, DARK, 7, DARK), 540, 1380, life(t, 27.7, 29.5), -3)
    put(u, num_badge("3", 160), 190, 560, life(t, 26.5, 27.3))
    put(u, icon("thermo", 150), 190, 640, life(t, 29.74))
    put(u, icon("sun", 160), 890, 620, life(t, 30.18), t * 25)
    title(u, "ÉTAPE 3", t, 26.5, 27.3, y=330)
    title(u, "UN VERRE D'EAU", t, 27.34, 29.6, y=330, size=130)
    title(u, "CHAUD & LUMIÈRE", t, 29.74, 30.9, y=330, size=125)
    title(u, "CHANGE L'EAU", t, 30.98, None, y=330)
    return w, u


cue(26.5, "rise", 0.25)
cue(27.4, "whoosh_up", 0.2)
cue(27.6, "splash", 0.35)
cue(29.74, "pop_hi", 0.3)
cue(30.18, "sparkle", 0.25)
cue(31.0, "pour", 0.35)


# ============================================================ H. COMPTEUR DE SEMAINES (32.2 → 35.1)
def s_roots(t):
    w, u = new_layers(background("table"))
    glass_scene(w, t, roots_g=ease_out((t - 32.6) / 2.0))
    n = 1 + int(clamp((t - 32.5) / 1.2) * 2.99)
    put(u, num_badge(f"S{n}", 190), 860, 620, life(t, 32.4), math.sin(t * 3) * 4)
    sparkles(w, t, 34.4, GX, TABLE - 200, 220, 8, 5)
    title(u, "2-3 SEMAINES", t, 32.3, 33.8, y=330)
    title(u, "DES RACINES !", t, 33.86, None, y=330, color=YEL, size=150)
    return w, u


cue(32.5, "tick", 0.3)
cue(32.9, "tick", 0.3)
cue(33.3, "tick", 0.3)
cue(33.86, "rise", 0.3)
cue(34.42, "success", 0.35)


# ============================================================ I. ÉTAPE 4 : COUPE DU POT (35.1 → 43.5)
SOIL = 960


@lru_cache(None)
def perlite():
    r = np.random.default_rng(7)
    im = Image.new("RGBA", (W, H - SOIL), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(700):
        x, y = r.uniform(0, W), r.uniform(20, H - SOIL)
        rad = r.uniform(5, 10)
        g = int(r.uniform(210, 248))
        d.ellipse([x - rad, y - rad * 0.8, x + rad, y + rad * 0.8], fill=(g, g, g - 6), outline=(150, 150, 145), width=2)
    return im


def s_step4(t):
    w, u = new_layers(background("none", SOIL))
    mix = ease_out((t - 37.66) / 0.6)
    if mix > 0.01:
        p = perlite().copy()
        p.putalpha(p.getchannel("A").point(lambda v: int(v * mix)))
        w.alpha_composite(p, (0, SOIL))
    sink = ease_out((t - 36.06) / 0.5)
    head_roots(w, 540, lerp(SOIL - 420, SOIL + 20, sink), 0.8, 1.0, life(t, 36.06))
    if sink > 0.9:
        particles(w, t, 36.55, 540, SOIL, 12, 4, col=(150, 110, 70), size=9, up=340)
    if t > 37.9:
        for i in range(6):
            tt = (t - 37.9 - i * 0.15) % 1.0
            put(w, icon("drop", 38), 180 + i * 140, SOIL + 80 + tt * 700, 1, 0, 1 - tt)
    for i, (ic, t0, lab) in enumerate((("sun", 40.62, "LUMIÈRE"), ("thermo", 41.54, "CHALEUR"), ("drop", 42.5, "PEU D'EAU"))):
        y = 530 + i * 150
        put(u, icon(ic, 90), 150, y, life(t, t0), t * 25 if ic == "sun" else 0)
        put(u, text_img(lab, F_TITLE, 40, YEL, 6, DARK, 5, DARK), 150, y + 66, life(t, t0 + 0.08), -3)
    put(u, num_badge("4", 160), 190, 560, life(t, 35.2, 36.0))
    title(u, "ÉTAPE 4", t, 35.2, 36.0, y=330)
    title(u, "TERRE DRAINANTE", t, 36.06, 39.9, y=330, size=125)
    title(u, "ET ENSUITE…", t, 40.0, None, y=330)
    return w, u


cue(35.2, "rise", 0.25)
cue(36.1, "whoosh", 0.25)
cue(36.55, "crunch", 0.4)
cue(37.9, "plop", 0.25)
cue(40.62, "pop", 0.25)
cue(41.54, "pop", 0.25)
cue(42.5, "pop", 0.25)


# ============================================================ J. TROP D'EAU (43.5 → 46.7)
def s_too_wet(t):
    w, u = new_layers(background("none", SOIL, darken=0.3 * fade(t, 44.6, None, 0.6)))
    wet = ease_io((t - 44.66) / 1.0)
    rot = ease_io((t - 45.46) / 0.8)
    head_roots(w, 540, SOIL + 20, 0.8, 1.0, 1.0, rotten=rot)
    water(w, lerp(H + 40, SOIL + 40, wet), t, 0.42)
    stamp(u, "STOP !", 540, 560, t, 44.66, RED, 120, 8)
    title(u, "ATTENTION !", t, 43.66, None, y=330, color=RED)
    return w, u


cue(43.66, "alert2", 0.4)
cue(44.66, "pour", 0.3)
cue(44.7, "thud", 0.35)
cue(45.5, "squish", 0.25)
cue(45.98, "fail", 0.32)


# ============================================================ K. LA POMME QUI ROULE + SAC QUI TOMBE (46.7 → 53.8)
POT_TOP = TABLE - 330


def potted(c, k=1.0):
    pot(c, 540, POT_TOP, 420, 330)
    head(c, 540, POT_TOP + 14, k)
    mound(c)


def s_bloom(t):
    w, u = new_layers(background("table"))
    potted(w)
    if t > 49.4:
        q = ease_out((t - 49.42) / 0.7)
        spr(w, A + "pomme", lerp(1250, 860, q), TABLE + 20, 230, rot=lerp(-360, 0, q))
    if t > 51.18:
        drop_y = lerp(-900, 0, ease_out((t - 51.18) / 0.45))
        bag(w, 250, 1010, POT_TOP - 560 + drop_y, TABLE + 30 + drop_y, 1.0)
    progress_bar(u, 200, 880, 560, ease_out((t - 47.3) / 1.6) * 0.66, ["0", "1 AN", "2 ANS", "3 ANS"], t, 47.26)
    put(u, icon("question", 150), 920, 760, life(t, 48.9, 49.4))
    title(u, "TOUJOURS PAS DE FLEUR ?", t, 47.26, 49.3, y=330, size=95)
    title(u, "UNE POMME MÛRE", t, 49.42, 51.1, y=330, size=125)
    title(u, "SOUS UN SAC", t, 51.18, None, y=330, size=140)
    return w, u


cue(47.26, "pop", 0.3)
cue(49.42, "whoosh", 0.25)
cue(50.0, "pop_lo", 0.35)
cue(51.2, "whoosh", 0.25)
cue(51.6, "thud", 0.3)


# ============================================================ L. GAZ → FLASH → FLORAISON (53.8 → 57.6)
def s_gas(t):
    w, u = new_layers(background("table"))
    if t < 55.82:
        potted(w)
        spr(w, A + "pomme", 860, TABLE + 20, 230)
        bag(w, 250, 1010, POT_TOP - 560, TABLE + 30, 1.0)
        gas(w, 850, TABLE - 230, t, fade(t, 54.0, None, 0.3))
        put(u, text_img("ÉTHYLÈNE", F_TITLE, 70, YEL, 8, DARK, 7, DARK), 700, 620, life(t, 54.62), -6)
    else:
        spr(w, A + "plant", 540, TABLE + 40, 1050, life(t, 55.82))
        sparkles(w, t, 55.9, 540, 600, 360, 12, 9)
    flash = max(0.0, 1 - abs(t - 55.82) / 0.18)
    if flash > 0:
        u.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 240, int(230 * flash))))
    title(u, "LE GAZ DE LA POMME", t, 53.9, 55.7, y=330, size=115)
    title(u, "FLORAISON !", t, 55.9, None, y=330, color=YEL, size=160)
    return w, u


cue(54.06, "buzz", 0.12)
cue(54.62, "pop_hi", 0.3)
cue(55.82, "rise", 0.3)
cue(55.9, "success", 0.35)


# ============================================================ M. PATIENCE : BARRE 0 → 3 ANS (57.6 → 62.8)
def s_patience(t):
    w, u = new_layers(background("table"))
    g = ease_io((t - 59.7) / 1.8)
    if g < 0.5:
        potted(w, lerp(0.9, 1.1, g * 2))
    else:
        spr(w, A + "plant", 540, TABLE + 40, lerp(800, 1000, (g - 0.5) * 2))
    if g < 0.5:
        progress_bar(u, 200, 880, 560, lerp(0.66, 1.0, g), ["0", "1 AN", "2 ANS", "3 ANS"], t, 57.74)
    if t > 61.3:
        fx, fy = 540 + (612 - 627) * 1000 / 1241, TABLE + 40 - (1247 - 465) * 1000 / 1241
        hl_ellipse(w, fx, fy, 115, 145, life(t, 61.3))
    title(u, "PATIENCE…", t, 57.74, 61.2, y=330)
    title(u, "LE 1ER FRUIT !", t, 61.26, None, y=330, color=YEL, size=150)
    return w, u


cue(57.74, "pop", 0.25)
cue(59.9, "rise", 0.25)
cue(61.3, "ding", 0.3)


# ============================================================ N. MIAM (62.8 → 65.95)
def s_proud(t):
    w, u = new_layers(background("table"))
    name = A + ("ananas_croque" if t > 64.25 else "ananas")
    wob = math.sin(max(0, t - 64.25) * 20) * 4 * math.exp(-max(0, t - 64.25) * 4) if t > 64.25 else 0
    spr(w, name, 540, TABLE + 40, 1000, life(t, 62.9), rot=wob)
    if t > 64.2:
        particles(w, t, 64.2, 720, 700, 14, 3, col=(240, 200, 80), size=10, up=420)
    stamp(u, "MIAM !", 820, 640, t, 64.3, GREEN, 110, 10)
    title(u, "QUELLE FIERTÉ !", t, 63.58, None, y=300, color=YEL, size=150)
    return w, u


cue(62.9, "pop_lo", 0.35)
cue(63.6, "sparkle", 0.3)
cue(64.2, "crunch", 0.5)
cue(64.35, "pop_hi", 0.25)


# ============================================================ O. CTA (65.95 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    head_roots(w, 300, TABLE - 150, 0.44, 1.0, life(t, 66.0))
    spr(w, A + "ananas", 780, TABLE + 40, 420, life(t, 66.08))
    clicked = t > 66.6
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 66.55) / 0.15))
    put(u, btn, 540, 300, life(t, 66.1) * press)
    if t > 66.25:
        k = ease_out((t - 66.25) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(330), 540, 590, life(t, 66.74, dur=0.45))
    sparkles(u, t, 66.8, 540, 590, 230, 10, 12)
    return w, u


cue(66.0, "pop_lo", 0.3)
cue(66.1, "pop_hi", 0.3)
cue(66.58, "click", 0.55)
cue(66.65, "bell", 0.35)
cue(66.8, "sparkle", 0.3)

if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video), (VID_END, 3.0, s_error)]
else:
    _intro = [(0.0, 3.0, s_intro)]

SCENES = _intro + [
    (3.0, 6.9, s_timeline),
    (6.9, 13.5, s_compare),
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
