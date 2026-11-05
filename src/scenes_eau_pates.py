"""Storyboard « Eau de cuisson des pâtes : engrais ou poison ? » (voix : assets/audio/eau_pates/voix.mp3).

Le volume de la voix est gardé tel qu'envoyé (aucun mastering, cf. render.py « af »).
0–4.1   coin du salon (photo fournie) : le pothos en pleine forme, une casserole de pâtes fumante verse son eau…
        « ou les tuer » : BIM, la plante sèche d'un coup (photo fournie du même pothos desséché).
4.1–7.4 fond beige : la casserole de pâtes ; « le sel » : la boîte de sel arrive et sale l'eau.
7.4–11.2 le pot coupé en deux (photos fournies) : le sel tombe sur la terre, descend, et les racines blanches
        pourrissent au passage (racines saines → racines pourries, de haut en bas) ; le sel s'accumule dans la terre.
11.2–14.2 sans sel et refroidie : la casserole ne fume plus, la boîte de sel est barrée ; « oui, de temps en temps ».
14.2–18.1 le meilleur : l'eau de cuisson des légumes, pleine de minéraux (K, Ca, Mg).
18.1–fin le pothos de nouveau en forme dans le salon, bouton S'abonner et logo.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, background, put, title, life, fade, ease_out,
                 ease_io, ease_in, clamp, lerp, icon, pills, tag, button_img, hl_ellipse, particles, light_rays,
                 text_img, F_TITLE, F_BLACK)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp
from scenes_citron import photo, shade, zoomed, shadow, swap
from scenes_banane import ob

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


SAIN, SEC = "banque/pothos_sain", "banque/pothos_sec"
COUPE_OK, COUPE_KO = "banque/pothos_coupe_racines_saines", "banque/pothos_coupe_racines_pourries"
CASS, CASS_HOT, SEL = "banque/casserole_pates", "banque/casserole_pates_ebullition", "banque/sel_boite"
FULL = (0, 0, 1024, 1024)
POT_BASE = (525, 985)                            # bas du pot dans les photos du pothos (cadre 1024)


def pothos(c, name, X, Y, k, s=1.0, rot=0.0):
    place(c, name, FULL, k, *POT_BASE, X, Y, s, rot)


def steam(c, t, x, y, w_, a=1.0, n=6):
    """Volutes de vapeur qui montent (douces, floues)."""
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(n):
        p = (t * 0.55 + i / n) % 1.0
        xx = x + (i - n / 2) * w_ / n + math.sin(t * 2 + i * 1.7) * 30 * p
        yy = y - p * 320
        r = 30 + 60 * p
        d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(255, 255, 255, int(70 * a * math.sin(math.pi * p))))
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(18)))


@lru_cache(None)
def mineral_tile(sym, num, name, size=150):
    im = Image.new("RGBA", (size + 12, size + 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 10, size + 6, size + 10], radius=size * 0.14, fill=DARK)
    d.rounded_rectangle([0, 0, size, size], radius=size * 0.14, fill=YEL, outline=DARK, width=max(3, size // 30))
    im.alpha_composite(text_img(num, F_BLACK, int(size * 0.15), DARK), (int(size * 0.1), int(size * 0.07)))
    k = text_img(sym, F_TITLE, int(size * 0.5), DARK)
    im.alpha_composite(k, ((size - k.width) // 2, int(size * 0.2)))
    p = text_img(name, F_BLACK, int(size * 0.12), DARK)
    im.alpha_composite(p, ((size - p.width) // 2, int(size * 0.76)))
    return im


# ============================================================ A. LE SALON : L'EAU DE PÂTES… BIM (0 → 4.1)
PL_X, PL_Y, PL_K = 680, 1235, 0.76               # pothos dans le coin (≈ 1 m)
SOIL = (PL_X - 5, PL_Y - 205)                    # terre du pot
PAN_K = 380 / 918
PAN_RIM = (115, 500)                             # bord gauche de la casserole (cadre 1024)
PAN_C = (565, 587)
POUR_C = (930, 760)                              # centre de la casserole quand elle verse
POUR_ROT = 52


def pan_rim_world(cx, cy, rot):
    dx, dy = (PAN_RIM[0] - PAN_C[0]) * PAN_K, (PAN_RIM[1] - PAN_C[1]) * PAN_K
    a = math.radians(rot)
    return cx + dx * math.cos(a) + dy * math.sin(a), cy - dx * math.sin(a) + dy * math.cos(a)


def salon(t, dry_t=None):
    w = photo("fond_salon_coin2.jpg").copy()
    shadow(w, PL_X, PL_Y, 300, 80)
    if dry_t is None:
        pothos(w, SAIN, PL_X, PL_Y, PL_K)
    else:
        which, sc = swap((t - dry_t) / 0.3)
        shake = math.sin(t * 70) * 8 * fade(t, dry_t, dry_t + 0.45, 0.02, 0.2) if dry_t < t < dry_t + 0.45 else 0.0
        pothos(w, SAIN if which == 0 else SEC, PL_X + shake, PL_Y, PL_K * sc)
    return w


def s_salon(t):
    w = salon(t, 2.95)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cin = ease_out((t - 0.15) / 0.4)
    tilt = ease_io((t - 0.5) / 0.3)
    cout = ease_in((t - 2.35) / 0.35)
    if 0.15 < t < 2.7:
        cx, cy = lerp(1350, POUR_C[0], cin) + 500 * cout, lerp(400, POUR_C[1], cin) - 300 * cout
        rot = POUR_ROT * tilt * (1 - cout)
        steam(w, t, cx - 40, cy - 120, 260, 0.9)
        ob(w, CASS_HOT, cx, cy, 380, rot=rot)
        if 0.75 < t < 2.4:   # l'eau de cuisson trouble qui coule dans le pot
            rim = pan_rim_world(cx, cy, rot)
            a = fade(t, 0.75, 2.4, 0.08, 0.15)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            pts = [(lerp(rim[0], SOIL[0] + 30, q) - math.sin(q * math.pi) * 25, lerp(rim[1], SOIL[1], q * q))
                   for q in [i / 14 for i in range(15)]]
            d.line(pts, fill=(236, 228, 205, int(215 * a)), width=26, joint="curve")
            d.line([(x - 5, y) for x, y in pts], fill=(255, 252, 240, int(170 * a)), width=7, joint="curve")
            w.alpha_composite(ov.filter(ImageFilter.GaussianBlur(1)))
            steam(w, t + 0.3, SOIL[0] + 40, SOIL[1] - 20, 160, 0.6 * a, 4)
            particles(w, t, t - (t % 0.3), SOIL[0] + 30, SOIL[1], 6, int(t * 10) % 7, col=(240, 232, 210), size=6,
                      up=150, dur=0.3)
    if 2.95 < t < 4.1:   # BIM : feuilles qui tombent, poussière sèche
        particles(w, t, 2.97, PL_X, PL_Y - 380, 18, 7, col=(150, 120, 70), size=12, up=200, dur=1.0)
    w = zoomed(w, lerp(1.25, 1.4, ease_io((t - 2.9) / 0.6)), 640, lerp(900, 930, ease_io((t - 2.9) / 0.6)))
    if 2.95 < t < 3.25:   # flash
        w.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(150 * (1 - (t - 2.95) / 0.3)))))
    w.alpha_composite(shade())
    title(u, "L'EAU DE TES PÂTES ?", t, 0.05, 1.75, y=330, color=YEL, size=125)
    title(u, "ÇA NOURRIT…", t, 1.8, 2.9, y=330, color=GREEN, size=160)
    stamp(u, "OU ÇA TUE !", 540, 340, t, 2.95, None, RED, 150, -7)
    return w, u


cue(0.17, "whoosh", 0.16)
cue(0.75, "pour", 0.32)
cue(2.97, "fail", 0.4)
cue(3.0, "thud", 0.3)


# ============================================================ B. TOUT DÉPEND D'UN DÉTAIL : LE SEL (4.1 → 7.4)
CB_X, CB_Y, CB_W = 470, TABLE + 40, 640
SALT_IN = (CB_X + 40, CB_Y - 330)                # où tombe le sel dans la casserole


def salt_grains(c, t, t0, x, y, dur=0.9, n=26):
    if t < t0 or t > t0 + dur + 0.5:
        return
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(5)
    for i in range(n):
        p = (t - t0 - r.uniform(0, dur)) / 0.45
        if 0 < p < 1:
            gx = x + r.uniform(-30, 30) + r.uniform(-20, 20) * p
            gy = y + p * p * 300
            d.rectangle([gx - 5, gy - 5, gx + 5, gy + 5], fill=(252, 252, 252, 255), outline=(150, 150, 150))


def s_salt(t):
    w, u = new_layers(background("table"))
    s_ = life(t, 4.1, dur=0.35)
    shadow(w, CB_X, CB_Y, CB_W * 0.8 * s_)
    steam(w, t, CB_X, CB_Y - 380, 380, s_)
    ob(w, CASS_HOT, CB_X, CB_Y, CB_W, s=s_, anchor="bottom")
    # la boîte de sel arrive et verse
    if t > 6.2:
        q = ease_out((t - 6.22) / 0.35)
        tilt = 120 * ease_io((t - 6.5) / 0.3)
        ob(w, SEL, lerp(1300, 860, q), lerp(700, 640, q), 210, rot=tilt)
        salt_grains(u, t, 6.8, 664, 760)
        if t > 6.25:
            hl_ellipse(u, 860, 640, 190, 300, life(t, 6.3, 6.75))
    title(u, "TOUT DÉPEND", t, 4.12, 4.95, y=330, size=165)
    title(u, "D'UN SEUL DÉTAIL…", t, 4.99, 6.15, y=330, color=YEL, size=130)
    stamp(u, "LE SEL !", 540, 340, t, 6.22, None, RED, 170, -8)
    return w, u


cue(4.12, "pop", 0.22)
cue(5.0, "tick", 0.2)
cue(5.5, "tick", 0.2)
cue(6.24, "alert1", 0.32)
cue(6.82, "rustle", 0.25)


# ============================================================ C. EN COUPE : LES RACINES POURRISSENT (7.4 → 11.2)
CK = 1.38
CX0, CY0 = 540, TABLE + 40                       # bas du pot coupé (écran)
SOIL_TOP_SRC, ROOT_BOT_SRC = 775, 975            # terre dans la photo (cadre 1024)


def src2w(x, y):
    return CX0 + (x - 502) * CK, CY0 + (y - 998) * CK


def s_roots(t):
    w, u = new_layers(background("table"))
    # racines saines → pourries : le sel descend du haut vers le bas, les racines pourrissent derrière lui
    front_src = lerp(SOIL_TOP_SRC - 10, ROOT_BOT_SRC + 25, ease_io((t - 8.3) / 1.5))
    front = src2w(0, front_src)[1]
    ok, ko = Image.new("RGBA", (W, H), (0, 0, 0, 0)), Image.new("RGBA", (W, H), (0, 0, 0, 0))
    place(ok, COUPE_OK, FULL, CK, 502, 998, CX0, CY0)
    if t > 8.3:
        place(ko, COUPE_KO, FULL, CK, 502, 998, CX0, CY0)
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        pts = [(x, front + math.sin(x * 0.03 + t * 3) * 14) for x in range(0, W + 20, 20)]
        d.polygon([(0, 0), (W, 0)] + pts[::-1], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(12))
        ko.putalpha(Image.composite(ko.getchannel("A"), Image.new("L", (W, H), 0), m))
        ok.putalpha(Image.composite(Image.new("L", (W, H), 0), ok.getchannel("A"), m))
    shadow(w, CX0, CY0, 360)
    w.alpha_composite(ok)
    w.alpha_composite(ko)
    # le sel tombe sur la terre, puis s'accumule dans la terre (cristaux blancs)
    salt_grains(w, t, 7.5, src2w(525, 0)[0], src2w(0, SOIL_TOP_SRC)[1] - 300, dur=0.7)
    if t > 8.3:
        d = ImageDraw.Draw(w)
        r = np.random.default_rng(9)
        acc = ease_out((t - 9.85) / 1.0)
        n = int(20 + 160 * acc)
        x0, x1 = src2w(410, 0)[0], src2w(640, 0)[0]
        for i in range(n):
            lo = src2w(0, SOIL_TOP_SRC)[1]
            gy = r.uniform(lo, max(lo + 1, min(front, src2w(0, ROOT_BOT_SRC)[1])))
            gx = r.uniform(x0, x1)
            if gy < front:
                d.rectangle([gx - 3, gy - 3, gx + 3, gy + 3], fill=(252, 252, 252, 235))
        if 8.3 < t < 9.9:   # le front salé
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ov).rectangle([x0, front - 14, x1, front + 14], fill=(255, 255, 255, 90))
            w.alpha_composite(ov.filter(ImageFilter.GaussianBlur(8)))
    zk = ease_io((t - 7.45) / 0.6)
    w = zoomed(w, lerp(1.0, 1.9, zk), CX0, lerp(960, src2w(0, 880)[1], zk))
    if t > 8.5:
        tag(u, "RACINES POURRIES", 780, 560, t, 9.0, 10.0, rot=-5, size=48)
    if t > 9.85:
        tag(u, "SEL", 820, 560, t, 9.9, None, rot=5, size=60)
    title(u, "L'EAU SALÉE…", t, 7.42, 8.2, y=330, size=165)
    title(u, "ASSÈCHE LES RACINES", t, 8.25, 9.8, y=330, color=RED, size=115)
    title(u, "LE SEL S'ACCUMULE", t, 9.85, None, y=330, color=YEL, size=125)
    return w, u


cue(7.44, "whoosh", 0.16)
cue(7.55, "rustle", 0.22)
cue(8.4, "fail", 0.3)
cue(9.9, "pop", 0.22)


# ============================================================ D. SANS SEL, BIEN REFROIDIE : OUI, DE TEMPS EN TEMPS (11.2 → 14.2)
def s_cool(t):
    w, u = new_layers(background("table"))
    which, sc = swap((t - 12.05) / 0.3)            # elle refroidit : plus de bouillons ni de vapeur
    s_ = life(t, 11.2, dur=0.35)
    shadow(w, 560, TABLE + 40, 600 * s_)
    if which == 0:
        steam(w, t, 560, TABLE - 360, 360, s_)
        ob(w, CASS_HOT, 560, TABLE + 40, 640 * sc, s=s_, anchor="bottom")
    else:
        ob(w, CASS, 560, TABLE + 40, 700 * sc, anchor="bottom")
    # pas de sel
    sg = life(t, 11.25, dur=0.3)
    ob(w, SEL, 170, 860, 170, s=sg, rot=-8)
    put(u, icon("nosign", 250), 170, 860, life(t, 11.45))
    if t > 12.0:
        put(u, icon("thermo", 150), 930, 760, life(t, 12.02))
        tag(u, "REFROIDIE", 880, 600, t, 12.1, None, rot=6, size=50)
    if t > 12.89:
        put(u, icon("check", 170), 560, 640, life(t, 12.9))
        tag(u, "DE TEMPS EN TEMPS", 560, 1470 - 680, t, 13.15, None, rot=-3, size=52)
    title(u, "SANS SEL", t, 11.22, 11.98, y=330, size=180)
    title(u, "ET REFROIDIE ?", t, 12.02, 12.85, y=330, color=YEL, size=160)
    stamp(u, "OUI !", 540, 340, t, 12.9, None, GREEN, 175, -8)
    return w, u


cue(11.24, "pop", 0.22)
cue(11.47, "alert2", 0.22)
cue(12.07, "whoosh", 0.14)
cue(12.92, "ding", 0.3)


# ============================================================ E. LE MEILLEUR : L'EAU DES LÉGUMES (14.2 → 18.1)
VEG = [("poireau/leek_full", -150, 70, -60), ("garlic_bulb_a", 20, 110, 0), ("banque/oignon", 125, 85, 15)]
MINERALS = [("K", "19", "Potassium"), ("Ca", "20", "Calcium"), ("Mg", "12", "Magnésium")]


def s_veg(t):
    w, u = new_layers(background("table"))
    s_ = life(t, 14.22, dur=0.35)
    X, Y, Wc = 540, TABLE + 40, 700
    shadow(w, X, Y, Wc * 0.8 * s_)
    k = Wc / 964
    wx, wy = X + (393 - 513) * k, Y + (432 - 835) * k   # centre de la surface de l'eau
    rim_y = wy
    # les légumes tombent dans l'eau (coupés à la surface)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, (name, dx, wv, rot) in enumerate(VEG):
        q = ease_in((t - 15.3 - i * 0.18) / 0.45)
        if q > 0:
            ob(lay, name, wx + dx, lerp(250, wy + 10, q), wv * 2.2, rot=rot + 40 * q)
    m = Image.new("L", (W, H), 255)
    ImageDraw.Draw(m).rectangle([0, wy + 12, W, H], fill=0)
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m.filter(ImageFilter.GaussianBlur(5))))
    ob(w, CASS, X, Y, Wc, s=s_, anchor="bottom")
    if s_ > 0.99:   # un bouillon de légumes doré et trouble à la place des pâtes
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        rx, ry = 312 * k, 55 * k
        d.ellipse([wx - rx, wy - ry, wx + rx, wy + ry], fill=(196, 170, 96, 245))
        d.ellipse([wx - rx * 0.6, wy - ry * 0.55, wx + rx * 0.1, wy - ry * 0.05], fill=(232, 214, 150, 120))
        w.alpha_composite(ov.filter(ImageFilter.GaussianBlur(2)))
    w.alpha_composite(lay)
    if t > 15.4:
        steam(w, t, X, rim_y - 40, 380, fade(t, 15.4, None, 0.5))
    for i in range(3):
        if 15.9 + i * 0.22 < t < 16.3 + i * 0.22:
            particles(w, t, 15.9 + i * 0.22, X + VEG[i][1], rim_y + 30, 10, i, col=(200, 225, 240), size=7, up=260,
                      dur=0.4)
    # pleine de minéraux : K, Ca, Mg qui montent de l'eau
    if t > 16.7:
        for i, (sym, num, nm) in enumerate(MINERALS):
            q = ease_out((t - 16.72 - i * 0.15) / 0.5)
            if q > 0:
                put(u, mineral_tile(sym, num, nm, 170), 260 + i * 280, lerp(rim_y, 640, q), q)
        sparkles(u, t, 16.8, 540, 700, 380, 10, 9)
    title(u, "LE MEILLEUR ?", t, 14.25, 15.3, y=330, size=165)
    title(u, "L'EAU DES LÉGUMES !", t, 15.35, 16.6, y=330, color=YEL, size=120)
    title(u, "PLEINE DE MINÉRAUX", t, 16.72, None, y=330, color=GREEN, size=118)
    return w, u


cue(14.24, "pop", 0.22)
cue(15.62, "plop", 0.25)
cue(15.85, "plop", 0.22)
cue(16.05, "plop", 0.22)
cue(16.75, "rise", 0.22)
cue(17.0, "success", 0.28)


# ============================================================ F. LE POTHOS EN FORME + ABONNE-TOI (18.1 → fin)
def s_end(t):
    w = salon(t)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w = zoomed(w, 1.25, 640, 900)
    w.alpha_composite(shade())
    sparkles(u, t, 18.2, 600, 760, 330, 10, 7)
    clicked = t > 19.3
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 19.25) / 0.15))
    put(u, btn, 540, 1420, life(t, 18.3) * press)
    if t > 18.8:
        k = ease_out((t - 18.8) / 0.4)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(1650, 1460, k), 1)
    put(u, logo_img(260), 540, 330, life(t, 20.2, dur=0.45))
    sparkles(u, t, 20.3, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 18.15, 20.15, y=330, color=YEL, size=135)
    return w, u


cue(18.17, "pop_lo", 0.3)
cue(19.28, "click", 0.45)
cue(20.3, "sparkle", 0.25)

SCENES = [
    (0.0, 4.1, s_salon),
    (4.1, 7.4, s_salt),
    (7.4, 11.2, s_roots),
    (11.2, 14.2, s_cool),
    (14.2, 18.1, s_veg),
    (18.1, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
