"""Storyboard « Patate douce dans un verre d'eau » (voix : assets/audio/patate_douce/voix.mp3).

Volume de la voix gardé tel qu'envoyé (render.py « af »).
0–4.0    la cuisine : un verre d'eau sur la planche, la patate douce arrive ; aperçu du résultat (tiges violettes).
4.0–11.75 trois cure-dents (photo fournie) se plantent un par un ; posée sur le verre, la moitié dans l'eau ;
          le côté pointu vers le bas : c'est là que sortent les racines.
11.75–15.1 le rebord de la fenêtre au-dessus du radiateur : au chaud, à la lumière, on change l'eau chaque semaine.
15.1–20.1 les semaines passent : des racines, puis des dizaines de tiges violettes.
20.1–23.8 le jardin au printemps : chaque tige devient un nouveau plant.
23.8–fin  la patate et ses tiges sur la planche + S'abonner + logo.
Photos : patate douce (nature, racines, tiges), tige, tige racinée, plant, verre (fournies) ; cure-dent (fourni).
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, DARK, WHITE, put, title, life, fade, ease_out, ease_io, ease_in, clamp,
                 lerp, icon, tag, button_img, hl_ellipse, particles, light_rays, pills, spr)
from scenes import sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp
from scenes_citron import shade, shadow, swap
from scenes_banane import ob
from scenes_eau_pates import Cam
from scenes_avocat2 import geom

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


B = "banque/"
FULL = (0, 0, 1024, 1024)
VERRE, PIC = B + "verre_eau_droit", B + "cure_dent_h"
CUISINE, REBORD, JARDIN = "decor_cuisine_planche_fenetre.jpg", "decor_rebord_fenetre_radiateur.jpg", \
    "tulipes_fond_sol_nu.png"
# corps de la patate dans chaque photo (cadre 1024) : centre x, haut, bas, largeur
BODY = {"patate_douce": (512, 60, 963, 330), "patate_douce_racines": (516, 59, 920, 330),
        "patate_douce_tiges": (504, 251, 905, 280)}
# verre (cadre 1024) : bas, bord, surface de l'eau, fond intérieur, demi-ouverture
G_BOT, G_TOP, G_RIM, G_WATER, G_FLOOR, G_HALF = 975, 65, 125, 285, 812, 285
P_LEN, P_BOT = 1000, 785                         # patate : longueur du corps et bas, en unités du verre


@lru_cache(None)
def pic_img():
    return Image.open(os.path.join(IMG, PIC + ".png")).convert("RGBA")


def pic(c, x0, x1, y, th, alpha=1.0):
    """Cure-dent horizontal de x0 à x1 (x0 > x1 = vers la gauche), épaisseur th."""
    ln = abs(x1 - x0)
    if ln < 4 or alpha <= 0.01:
        return
    im = pic_img().resize((int(ln), max(3, int(th))), Image.LANCZOS)
    if alpha < 1:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    c.alpha_composite(im, (int(min(x0, x1)), int(y - im.height / 2)))


def potato_glass(c, X, Ybot, Hg, name="patate_douce", picks=(1, 1, 1), lift=0.0, glass=True, water_q=1.0, sc=1.0):
    """Verre d'eau (photo transparente) avec la patate douce posée dessus, tenue par trois cure-dents.
    picks : avancement de chaque cure-dent (0 → 1 : il arrive et se plante) ; lift : patate soulevée (unités du
    verre) ; la partie sous l'eau est teintée et un peu floue, comme vue à travers l'eau."""
    k = Hg / (G_BOT - G_TOP)

    def G(gx, gy):
        return X + (gx - 512) * k, Ybot + (gy - G_BOT) * k

    cx, top, bot, bw = BODY[name]
    kp = P_LEN * k * sc / (bot - top)
    sx, sy = G(512, P_BOT - lift)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    place(lay, B + name, FULL, kp, cx, bot, sx, sy)
    a_ = lay.getchannel("A")                       # un peu plus net (racines fines)
    lay = lay.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.4, percent=80, threshold=2)).convert("RGBA")
    lay.putalpha(a_)
    # dans le verre : sous le bord, tout reste entre les parois (les racines ne traversent pas le verre) ;
    # sous l'eau, c'est teinté et un peu flou
    if glass:
        wl = G(0, G_WATER)[1]
        rim = G(0, G_RIM)[1]
        inner = [G(238, G_RIM), G(792, G_RIM), G(788, G_WATER), G(739, G_FLOOR - 10), G(300, G_FLOOR - 10),
                 G(246, G_WATER)]
        keep = Image.new("L", (W, H), 255)
        dk = ImageDraw.Draw(keep)
        dk.rectangle([0, rim, W, H], fill=0)
        dk.polygon(inner, fill=255)
        keep = keep.filter(ImageFilter.GaussianBlur(1.5))
        lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), keep))
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle([0, wl, W, H], fill=255)
        under = lay.filter(ImageFilter.GaussianBlur(0.35 * k + 0.25))
        tint = Image.new("RGBA", (W, H), (200, 222, 228, 0))
        tint.putalpha(under.getchannel("A").point(lambda v: int(v * 0.32)))
        under.alpha_composite(tint)
        under = Image.composite(under, Image.new("RGBA", (W, H), (0, 0, 0, 0)), m)
        over = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)), lay, m)
        lay = over
        lay.alpha_composite(under, (int(2 * k + 1), 0))
    body_a = lay.getchannel("A")
    c.alpha_composite(lay)
    if glass:
        place(c, VERRE, FULL, k, 512, G_BOT, X, Ybot)
    # cure-dents : plantés dans la patate (ils la suivent), la partie dans la chair est cachée par elle ;
    # posée sur le verre, ils reposent sur le bord. Le 3e part vers l'arrière, en biais.
    py = G(0, G_RIM - 8 - lift)[1]
    half = bw / 2 * kp * 0.98
    L = 460 * k
    th = max(6, 27 * k)
    tp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for side, p in zip((-1, 1), picks[:2]):
        if p <= 0:
            continue
        q = ease_out(p)
        edge = sx + side * half
        off = (1 - q) * L * 1.3
        pic(tp, edge - side * 0.25 * L + side * off, edge + side * 0.75 * L + side * off, py, th, min(1, p * 3))
    if len(picks) > 2 and picks[2] > 0:          # vers l'arrière : on le voit dépasser au-dessus de l'épaule
        q = ease_out(picks[2])
        back = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ln = 0.75 * L * q
        pic(back, sx, sx + ln, py, th * 0.85, min(1, picks[2] * 3))
        back = back.rotate(24, center=(sx, py), resample=Image.BICUBIC)
        back = back.filter(ImageFilter.GaussianBlur(0.5))
        tp.alpha_composite(back)
    tp.putalpha(Image.composite(Image.new("L", (W, H), 0), tp.getchannel("A"),
                                body_a.point(lambda v: 255 if v > 100 else 0)))
    c.alpha_composite(tp)
    return G


# ============================================================ A. LA CUISINE (0 → 11.75)
BD = (545, 1600)                                 # la planche (coordonnées de la photo)
KG = 300                                         # hauteur du verre (photo)
PICKS = (4.6, 4.8, 5.0)                          # « plante trois cure-dents »
DESCEND = (5.9, 6.6)                             # « pose-la sur un verre »


def s_kitchen(t):
    zk = ease_io((t - 9.8) / 0.8)
    cam = Cam(lerp(1.35, 2.0, zk), 545, lerp(1330, 1480, zk))
    w = cam.bg(CUISINE)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    gx, gy = cam.p(*BD)
    shadow(w, gx, gy, 240 * z, 70)
    teaser = 2.15 < t < 3.95
    if teaser:   # « regarde ce qui se passe » : aperçu du résultat
        which, sc = swap((t - 2.15) / 0.3)
        nm = "patate_douce" if which == 0 else "patate_douce_tiges"
        potato_glass(w, gx, gy, KG * z, nm, sc=sc)
    else:
        lift = 0.0
        picks = (1, 1, 1)
        if t < 2.15:          # la patate arrive au-dessus du verre
            lift = lerp(1700, 0, ease_out((t - 0.4) / 0.6))
            picks = (0, 0, 0)
        elif t < DESCEND[1]:  # tenue au-dessus du verre pendant qu'on plante les cure-dents, puis posée
            lift = 700 * (1 - ease_io((t - DESCEND[0]) / (DESCEND[1] - DESCEND[0])))
            picks = tuple(clamp((t - p0) / 0.25) for p0 in PICKS)
        potato_glass(w, gx, gy, KG * z, "patate_douce", picks, lift)
    if 3.95 < t < 4.15:   # retour au présent
        w.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(160 * (1 - (t - 3.95) / 0.2)))))
    w.alpha_composite(shade())
    k = KG * z / (G_BOT - G_TOP)
    if 7.15 < t < 9.8:   # la moitié dans l'eau
        wl = gy + (G_WATER - G_BOT) * k
        a = life(t, 7.2, 9.75)
        d = ImageDraw.Draw(u)
        for xx in range(int(gx - 330), int(gx + 330), 34):
            d.line([(xx, wl), (xx + 18, wl)], fill=WHITE + (int(240 * a),), width=6)
        tag(u, "MOITIÉ DANS L'EAU", 300, 640, t, 7.25, 9.75, rot=-5, size=50, string_to=(gx - 200, wl))
    if t > 8.4:          # le côté pointu vers le bas : c'est là que sortent les racines
        bx, by = gx, gy + (P_BOT - G_BOT) * k
        a = life(t, 8.45)
        d = ImageDraw.Draw(u)
        if a > 0.01:
            d.line([(bx + 230, by - 160), (bx + 40, by - 10)], fill=YEL + (int(255 * a),), width=12)
            d.polygon([(bx + 30, by + 5), (bx + 70, by - 10), (bx + 45, by - 45)], fill=YEL + (int(255 * a),))
        if t > 9.85:
            hl_ellipse(u, bx, by - 25, 90, 70, life(t, 9.9))
            tag(u, "RACINES ICI", 820, by - 220, t, 9.95, None, rot=-4, size=54)
    title(u, "UNE PATATE DOUCE", t, 0.05, 1.4, y=330, color=YEL, size=140)
    title(u, "DANS UN VERRE D'EAU", t, 1.45, 2.1, y=330, size=118)
    stamp(u, "REGARDE !", 540, 340, t, 2.15, 3.95, GREEN, 165, -7)
    title(u, "3 CURE-DENTS", t, 4.0, 5.8, y=330, color=YEL, size=165)
    title(u, "POSE-LA SUR UN VERRE", t, 5.85, 7.1, y=330, size=112)
    title(u, "MOITIÉ DANS L'EAU", t, 7.15, 8.35, y=330, color=YEL, size=130)
    title(u, "POINTE EN BAS !", t, 8.4, 9.8, y=330, size=150)
    stamp(u, "LES RACINES !", 540, 340, t, 9.85, None, GREEN, 140, -7)
    return w, u


cue(0.42, "whoosh", 0.16)
cue(0.95, "plop", 0.2)
cue(2.17, "sparkle", 0.25)
cue(3.97, "whoosh_up", 0.16)
for _p in PICKS:
    cue(_p + 0.18, "chop", 0.25)
cue(DESCEND[1] - 0.05, "splash", 0.3)
cue(7.25, "pop", 0.2)
cue(8.45, "pop_hi", 0.18)
cue(9.9, "ding", 0.25)


# ============================================================ B. LE REBORD DE LA FENÊTRE (11.75 → 20.1)
SILL = (540, 1290)                               # sur le rebord (coordonnées de la photo)
SG = 400


def s_window(t):
    cam = Cam(lerp(1.25, 1.4, ease_io((t - 15.1) / 1.0)), 540, 1060)
    w = cam.bg(REBORD)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    night = 0.0
    if 15.15 < t < 17.1:   # les semaines passent
        night = (0.5 + 0.5 * math.sin((t - 15.15) * 11)) * fade(t, 15.15, 17.1, 0.15, 0.15)
    light_rays(w, 300, 150, t, fade(t, 12.25, None, 0.4) * (1 - night))
    # chaleur du radiateur
    if t > 11.9:
        warm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rx, ry = cam.p(800, 1700)
        ImageDraw.Draw(warm).ellipse([rx - 500, ry - 380, rx + 500, ry + 300], fill=(255, 150, 60, int(60 * life(t, 11.95))))
        w.alpha_composite(warm.filter(ImageFilter.GaussianBlur(60)))
    gx, gy = cam.p(*SILL)
    shadow(w, gx, gy, 300 * z, 60)
    name = "patate_douce"
    if t > 17.15:
        name = "patate_douce_racines" if t < 18.1 else "patate_douce_tiges"
    sc = 1.0
    if 17.15 < t < 18.45:
        sc = swap(((t - 17.15) if t < 18.1 else (t - 18.1)) / 0.3)[1]
    # l'eau change : le niveau baisse puis remonte, plus claire
    refresh = 0.0
    if 13.35 < t < 14.9:
        refresh = math.sin(math.pi * clamp((t - 13.4) / 1.4))
    potato_glass(w, gx, gy, SG * z, name, sc=sc, water_q=1 - 0.5 * refresh)
    if refresh > 0.01:
        k = SG * z / (G_BOT - G_TOP)
        for i in range(8):
            tt = (t * 2.2 + i / 8) % 1.0
            put(w, icon("drop", 34), gx - 120 + i * 34, lerp(gy + (G_RIM - G_BOT) * k - 200, gy + (G_WATER - G_BOT) * k, tt),
                1, 0, refresh * (1 - tt))
    if night > 0.01:
        w.alpha_composite(Image.new("RGBA", (W, H), (18, 26, 66, int(110 * night))))
    w.alpha_composite(shade())
    if 11.95 < t < 15.1:
        put(u, icon("thermo", 150), 170, 640, life(t, 11.97, 15.0))
        put(u, icon("sun", 160), 900, 640, life(t, 12.6, 15.0), t * 25)
    if 13.4 < t < 15.1:
        pills(u, ["S1", "S2", "S3"], min(2, int((t - 13.45) / 0.45)), t, 13.4, 15.05, y=500, pw=170)
    if 15.2 < t < 17.1:
        pills(u, ["1 SEM.", "2 SEM.", "3 SEM."], min(2, int((t - 15.25) / 0.6)), t, 15.2, 17.05, y=500, pw=220)
    if t > 17.2:
        k = SG * z / (G_BOT - G_TOP)
        hl_ellipse(u, gx, gy + (G_FLOOR - G_BOT) * k - 60, 160, 110, life(t, 17.25, 18.05))
    if t > 18.15:
        sparkles(u, t, 18.2, gx, gy - 600, 300, 10, 7)
        tag(u, "TIGES VIOLETTES", 300, 600, t, 18.6, None, rot=-5, size=52, string_to=(gx - 90, gy - 640))
    title(u, "AU CHAUD", t, 11.8, 12.55, y=330, color=YEL, size=170)
    title(u, "À LA LUMIÈRE", t, 12.6, 13.3, y=330, size=160)
    title(u, "CHANGE L'EAU", t, 13.35, 14.4, y=330, color=YEL, size=160)
    title(u, "CHAQUE SEMAINE", t, 14.45, 15.1, y=330, size=145)
    title(u, "QUELQUES SEMAINES…", t, 15.15, 17.1, y=330, size=125)
    title(u, "DES RACINES…", t, 17.15, 18.05, y=330, color=YEL, size=160)
    stamp(u, "DES DIZAINES DE TIGES !", 540, 340, t, 18.1, None, GREEN, 100, -6)
    return w, u


cue(11.8, "whoosh", 0.16)
cue(11.97, "rise", 0.16)
cue(12.62, "sparkle", 0.18)
cue(13.4, "pour", 0.26)
for _k in range(3):
    cue(15.25 + _k * 0.6, "tick", 0.2)
cue(17.17, "pop_hi", 0.22)
cue(18.12, "pop_lo", 0.25)
cue(18.25, "success", 0.24)


# ============================================================ C. LE JARDIN : CHAQUE TIGE DEVIENT UN PLANT (20.1 → 23.8)
# plants espacés en quinconce : ceux du fond plus petits (perspective) ; dessinés du fond vers l'avant
ROW = [(220, 1140, 0.55, 21.0), (-330, 1190, 0.62, 20.85), (300, 1390, 0.84, 21.3), (-190, 1440, 0.95, 21.15)]
STAGE_T = (22.25, 22.85)                         # tige coupée → tige racinée → plant
ROOTS = {B + "pdouce_tige_coupee": 0.04, B + "pdouce_tige_racines": 0.53, B + "pdouce_plant": 0.44}   # part enterrée


def s_garden(t):
    cam = Cam(1.05, 540, 1150)
    w = cam.bg(JARDIN)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    for i, (dx, y, ps, t0) in enumerate(ROW):
        d = ease_out((t - t0) / 0.4)
        if d <= 0:
            continue
        x, yy = cam.p(540 + dx, y)
        if t < STAGE_T[0]:
            name, wd = B + "pdouce_tige_coupee", 300
        elif t < STAGE_T[1]:
            name, wd = B + "pdouce_tige_racines", 300
        else:
            name, wd = B + "pdouce_plant", 440
        wd *= ps
        sc = 1.0
        for ts in STAGE_T:
            if ts - 0.15 < t < ts + 0.15:
                sc = swap((t - ts + 0.15) / 0.3)[1]
        shadow(w, x, yy, wd * 0.5 * z, 70)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fr, bb = geom(name)
        below = ROOTS[name] * (bb[3] - bb[1]) * wd * z * sc / (bb[2] - bb[0])   # racines : sous la terre
        ob(lay, name, x, lerp(yy - 500, yy + below, d), wd * z * sc, anchor="bottom")
        # les racines sous la terre : on ne voit que la partie au-dessus du sol
        m = Image.new("L", (W, H), 255)
        ImageDraw.Draw(m).rectangle([0, yy, W, H], fill=0)
        m = m.filter(ImageFilter.GaussianBlur(4))
        lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
        w.alpha_composite(lay)
        if 0.6 < d < 1:
            particles(w, t, t0 + 0.3, x, yy, 10, i + 2, col=(55, 38, 26), size=8, up=160, dur=0.4)
    w.alpha_composite(shade())
    if 20.15 < t < 21.0:
        pills(u, ["MARS", "AVRIL", "MAI"], 2, t, 20.2, 20.95, y=560, pw=210)
    if t > STAGE_T[1]:
        sparkles(u, t, STAGE_T[1], 540, 1150, 420, 12, 7)
    title(u, "AU PRINTEMPS…", t, 20.15, 21.8, y=330, color=YEL, size=150)
    stamp(u, "1 TIGE = 1 PLANT !", 540, 340, t, 21.85, None, GREEN, 120, -6)
    return w, u


cue(20.17, "whoosh", 0.16)
for _d in ROW:
    cue(_d[3] + 0.35, "thud", 0.14)
cue(STAGE_T[0], "pop_hi", 0.2)
cue(STAGE_T[1], "pop", 0.22)
cue(STAGE_T[1] + 0.1, "sparkle", 0.2)


# ============================================================ D. ABONNE-TOI (23.8 → fin)
def s_end(t):
    cam = Cam(1.35, 545, 1330)
    w = cam.bg(CUISINE)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    gx, gy = cam.p(*BD)
    shadow(w, gx, gy, 240 * z, 70)
    potato_glass(w, gx, gy, KG * z, "patate_douce_tiges", sc=life(t, 23.85, dur=0.4))
    w.alpha_composite(shade())
    clicked = t > 25.4
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 25.35) / 0.15))
    put(u, btn, 540, 760, life(t, 24.0) * press)
    if t > 24.9:
        kk = ease_out((t - 24.9) / 0.4)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1000, 800, kk), 1)
    put(u, logo_img(230), 540, 560, life(t, 26.0, dur=0.45))
    sparkles(u, t, 26.1, 540, 560, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 23.9, None, y=330, color=YEL, size=135)
    return w, u


cue(23.9, "pop_lo", 0.26)
cue(25.38, "click", 0.45)
cue(26.1, "sparkle", 0.22)

SCENES = [
    (0.0, 11.75, s_kitchen),
    (11.75, 20.1, s_window),
    (20.1, 23.8, s_garden),
    (23.8, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
