"""Storyboard « Peau de banane comme engrais ? » (voix : assets/audio/banane/voix.mp3, son fort).

Ouverture dans la cuisine (photo fournie) : la banane devient sa peau, la peau tombe dans le verre d'eau, ça se
mélange et l'eau devient trouble ; on verse cette « eau de banane » sur la monstera malade… qui ne change pas.
Puis sur fond beige : oui, du potassium (fleurs et tomates) ; mais posée telle quelle, des mois, mouches et rongeurs ;
l'eau de banane : presque rien ; la bonne méthode : petits morceaux au compost, qui libère les nutriments ;
fin sur l'hortensia en fleurs sur le buffet.
Photos : banane, peau, verres (fournies) ; monstera, hortensia, composteur, épluchures, rat, couteau (vidéos
précédentes) ; mouche et tomates (Open Images).
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, spr, put, title, life, fade, ease_out,
                 ease_io, ease_in, clamp, lerp, icon, pills, tag, button_img, hl_ellipse, particles, light_rays,
                 text_img, F_TITLE, F_BLACK)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_mangue import warm_glow
from scenes_citron import photo, shade, zoomed, shadow, swap
from scenes_avocat2 import geom, TOP

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


BANANE, PEAU, VERRE = "banque/banane_entiere", "banque/peau_banane", "banque/verre_eau"
MOUCHE, TOMATES = "banque/mouche", "banque/tomates_grappe"
MONSTERA, HORTENSIA = "arrosage/monstera_malade_full", "hortensia/pot"
COMPO_O, COMPO_F = "compost/composteur_ouvert", "compost/composteur_ferme"
MORCEAUX, RAT, KNIFE = "compost/epluchure_banane", "compost/rat", "poireau/knife"


def ob(c, name, X, Y, width, s=1.0, rot=0.0, alpha=1.0, anchor="center", rotten=0.0, flip=False):
    """Objet détouré de largeur `width` ; (X, Y) = centre, ou bas-centre si anchor='bottom'."""
    if s <= 0.01 or alpha <= 0.01:
        return
    fr, bb = geom(name)
    im = Image.open(os.path.join(IMG, name + ".png"))
    k = width / (bb[2] - bb[0])
    cx = (bb[0] + bb[2]) / 2
    cy = bb[3] if anchor == "bottom" else (bb[1] + bb[3]) / 2
    X = X + (im.width / 2 - cx) * k * s * (-1 if flip else 1)
    Y = Y + (im.height / 2 - cy) * k * s
    spr(c, name, X, Y, im.height * k, s, rot=rot, alpha=alpha, rotten=rotten, shadow=False, flip=flip,
        anchor="center")


@lru_cache(None)
def k_tile(size=240):
    """Case « K – Potassium » façon tableau périodique."""
    im = Image.new("RGBA", (size + 16, size + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 14, size + 8, size + 14], radius=size * 0.14, fill=DARK)
    d.rounded_rectangle([0, 0, size, size], radius=size * 0.14, fill=YEL, outline=DARK, width=max(3, size // 30))
    n = text_img("19", F_BLACK, int(size * 0.15), DARK)
    im.alpha_composite(n, (int(size * 0.1), int(size * 0.07)))
    k = text_img("K", F_TITLE, int(size * 0.55), DARK)
    im.alpha_composite(k, ((size - k.width) // 2, int(size * 0.2)))
    p = text_img("Potassium", F_BLACK, int(size * 0.12), DARK)
    im.alpha_composite(p, ((size - p.width) // 2, int(size * 0.76)))
    return im


@lru_cache(None)
def qmark(size=150):
    return text_img("?", F_TITLE, size, YEL, 8, DARK, 6, DARK)


# ------------------------------------------------------------- le verre d'eau (photo transparente) et son contenu
G_BB = (279, 152, 745, 924)                    # verre_eau : cadre 1024
G_RIM, G_WTOP, G_WBOT = 160, 282, 818          # bord, surface de l'eau, fond (intérieur)
G_IN = [(300, 160), (724, 160), (692, G_WBOT), (332, G_WBOT)]      # intérieur du verre
G_WATER = [(306, G_WTOP), (718, G_WTOP), (692, G_WBOT), (332, G_WBOT)]
CLOUD = (222, 196, 118)


@lru_cache(4)
def glass_base(S):
    return Image.open(os.path.join(IMG, VERRE + ".png")).convert("RGBA").resize((S, S), Image.LANCZOS)


@lru_cache(4)
def peel_upright(hgt):
    """Peau de banane redressée (tige en haut), hauteur hgt."""
    im = Image.open(os.path.join(IMG, PEAU + ".png")).convert("RGBA")
    im = im.crop(im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox())
    im = im.rotate(84, expand=True, resample=Image.BICUBIC)
    im = im.crop(im.getbbox())
    return im.resize((max(1, int(im.width * hgt / im.height)), hgt), Image.LANCZOS)


def poly_mask(S, k, pts):
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).polygon([(x * k, y * k) for x, y in pts], fill=255)
    return m


def glass_img(Hg, peel=0.0, cloud=0.0, t=0.0, wob=0.0):
    """Le verre (hauteur Hg à l'écran) avec la peau dedans (peel 0 → 1 : elle descend) et l'eau trouble (cloud)."""
    k = Hg / (G_BB[3] - G_BB[1])
    S = int(1024 * k)
    can = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    if peel > 0.01:
        pim = peel_upright(int(760 * k))
        lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        px = 512 * k - pim.width / 2 + math.sin(wob) * 10 * k
        py = (40 - (1 - peel) * 900) * k
        lay.alpha_composite(pim.rotate(math.sin(wob * 1.3) * 4, resample=Image.BICUBIC), (int(px), int(py)))
        # dans le verre : coupée par les parois ; au-dessus du bord : libre
        inside = poly_mask(S, k, G_IN)
        ImageDraw.Draw(inside).rectangle([0, 0, S, int((G_RIM + 6) * k)], fill=255)
        lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (S, S), 0), inside))
        # sous l'eau : plus pâle, un peu floue
        wm = poly_mask(S, k, G_WATER)
        under = lay.filter(ImageFilter.GaussianBlur(1.5 * k + 0.5))
        tint = Image.new("RGBA", (S, S), (215, 222, 214, 255))
        under = Image.blend(under, Image.composite(tint, under, under.getchannel("A")), 0.28)
        under.putalpha(under.getchannel("A"))
        lay = Image.composite(under, lay, wm)
        can.alpha_composite(lay)
    if cloud > 0.01:
        cl = Image.new("RGBA", (S, S), CLOUD + (int(195 * cloud),))
        d = ImageDraw.Draw(cl)
        for i in range(7):   # volutes qui tournent
            a = t * 4.5 + i * 0.9
            cx, cy = (512 + math.cos(a) * 150) * k, (560 + math.sin(a * 0.8 + i) * 200) * k
            r = (70 + 20 * (i % 3)) * k
            d.ellipse([cx - r, cy - r * 0.7, cx + r, cy + r * 0.7], fill=(176, 142, 66, int(170 * cloud)))
        cl = cl.filter(ImageFilter.GaussianBlur(22 * k))
        wm = poly_mask(S, k, G_WATER)
        cl.putalpha(Image.composite(cl.getchannel("A"), Image.new("L", (S, S), 0), wm))
        can.alpha_composite(cl)
    can.alpha_composite(glass_base(S))
    return can, k


def glass(c, X, Ybot, Hg, peel=0.0, cloud=0.0, t=0.0, wob=0.0, rot=0.0):
    """Verre posé : bas-centre en (X, Ybot) ; rot autour du centre du verre."""
    im, k = glass_img(Hg, peel, cloud, t, wob)
    cy = Ybot - (G_BB[3] - 512) * k
    if abs(rot) > 0.1:
        im = im.rotate(rot, resample=Image.BICUBIC, center=(512 * k, (G_BB[1] + G_BB[3]) / 2 * k))
        cy = Ybot - (G_BB[3] - G_BB[1]) / 2 * k + ((G_BB[1] + G_BB[3]) / 2 - 512) * k
    c.alpha_composite(im, (int(X - 512 * k), int(cy - 512 * k)))


def stream(c, p0, p1, a=1.0, t=0.0):
    """Filet d'eau de banane qui coule de p0 vers p1."""
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    pts = []
    for i in range(16):
        q = i / 15
        pts.append((lerp(p0[0], p1[0], q) + math.sin(q * 3) * 12, lerp(p0[1], p1[1], q * q)))
    d.line(pts, fill=(196, 160, 72, int(245 * a)), width=34, joint="curve")
    d.line([(x - 5, y) for x, y in pts], fill=(250, 232, 170, int(190 * a)), width=8, joint="curve")
    c.alpha_composite(ov)
    particles(c, t, t - (t % 0.3), p1[0], p1[1], 6, int(t * 10) % 7, col=(215, 190, 120), size=7, up=160, dur=0.3)


# ============================================================ A. LA CUISINE : L'EAU DE BANANE (0 → 5.2)
G_X, G_Y, G_H = 395, 1240, 290                 # verre d'eau sur la planche (~15 cm)
B_C, B_W = (705, 1205), 340                    # banane (~18 cm)
M_X, M_Y, M_W = 790, 960, 470                  # monstera malade au fond du plan de travail
POUR = (585, 515)                              # centre du verre quand il verse
SOIL = (785, 690)


def s_kitchen(t):
    w = photo("citron_fond_cuisine.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ob(w, MONSTERA, M_X, M_Y, M_W, anchor="bottom")
    # --- la banane → sa peau, qui saute dans le verre
    which, sc = swap((t - 0.3) / 0.3)
    hop = ease_io((t - 0.62) / 0.3)
    if t < 0.62:
        shadow(w, B_C[0], B_C[1] + 70, B_W * 0.9, 55)
        if which == 0:
            ob(w, BANANE, B_C[0], B_C[1], B_W * sc)
        else:
            ob(w, PEAU, B_C[0], B_C[1] + 15, B_W * 1.05 * sc)
    elif t < 0.92:      # en cloche jusqu'au-dessus du verre
        x = lerp(B_C[0], G_X, hop)
        y = lerp(B_C[1], G_Y - G_H - 160, hop) - math.sin(math.pi * hop) * 220
        ob(w, PEAU, x, y, lerp(B_W * 1.05, 200, hop), rot=lerp(0, 84, hop))
    # --- le verre : la peau descend dedans (0.92 → 1.05), ça tourne, l'eau se trouble ; puis on verse
    peel = ease_in((t - 0.9) / 0.15) if t >= 0.9 else 0.0
    cloud = ease_io((t - 1.15) / 0.9)
    wob = (t - 1.1) * 9 if 1.1 < t < 2.1 else 0.0
    go = ease_io((t - 2.1) / 0.45)            # le verre se lève et va au-dessus de la plante
    tilt = ease_io((t - 2.45) / 0.3)
    back = ease_in((t - 3.2) / 0.35)          # puis il sort du cadre
    gx = lerp(G_X, POUR[0], go) - 700 * back
    gy = lerp(G_Y, POUR[1] + G_H / 2, go) - math.sin(math.pi * go) * 60
    if back < 1:
        if go < 0.05:
            shadow(w, G_X, G_Y, G_H * 0.62, 60)
        glass(w, gx, gy, G_H, peel, cloud, t, wob, rot=-72 * tilt * (1 - back))
    if 0.98 < t < 1.5:
        particles(w, t, 1.0, G_X, G_Y - G_H * 0.82, 12, 4, col=(170, 205, 230), size=9, up=260, dur=0.5)
    if 1.15 < t < 2.05:   # flèches de mélange
        d = ImageDraw.Draw(w)
        a0 = (t - 1.15) * 400
        bx, by, r = G_X, G_Y - G_H * 0.45, G_H * 0.42
        d.arc([bx - r, by - r * 0.45, bx + r, by + r * 0.45], a0, a0 + 230, fill=WHITE + (230,), width=9)
    if 2.62 < t < 3.25:
        rim = (POUR[0] + 140, POUR[1] - 30)
        stream(w, rim, SOIL, fade(t, 2.62, 3.25, 0.08, 0.12), t)
    # --- caméra : la planche, puis la plante
    zk = ease_io((t - 2.05) / 0.5)
    zf = ease_io((t - 3.55) / 0.8)
    z = lerp(lerp(1.5, 1.2, zk), 1.65, zf)
    fx, fy = lerp(lerp(540, 640, zk), M_X, zf), lerp(lerp(1110, 900, zk), 760, zf)
    w = zoomed(w, z, fx, fy)
    w.alpha_composite(shade())
    if t > 3.25:   # … et rien ne change
        for i, (qx, qy, t0) in enumerate([(300, 760, 3.3), (800, 650, 3.42), (560, 560, 3.54)]):
            wob_q = math.sin((t - t0) * 6 + i) * 8
            put(u, qmark(170), qx, qy + wob_q, life(t, t0), wob_q)
    title(u, "LA PEAU DE BANANE", t, 0.07, 1.3, y=330, color=YEL, size=125)
    title(u, "COMME ENGRAIS ?", t, 1.35, 2.3, y=330, size=135)
    stamp(u, "ÇA MARCHE ?", 540, 340, t, 2.35, 3.52, RED, 125, -7)
    title(u, "LA RÉPONSE…", t, 3.59, None, y=330, color=YEL, size=165)
    return w, u


cue(0.32, "pop", 0.25)
cue(0.64, "whoosh", 0.22)
cue(0.98, "splash", 0.35)
cue(1.2, "stir", 0.28)
cue(2.12, "whoosh_up", 0.18)
cue(2.62, "pour", 0.32)
cue(3.3, "pop_lo", 0.2)
cue(3.42, "pop_lo", 0.2)
cue(3.54, "pop_lo", 0.2)
cue(3.62, "tick", 0.2)
cue(4.0, "tick", 0.2)
cue(4.38, "tick", 0.2)


# ============================================================ B. OUI : DU POTASSIUM, FLEURS ET TOMATES (5.2 → 9.4)
def s_yes(t):
    w, u = new_layers(background("table"))
    side = ease_in((t - 7.12) / 0.3)
    if side < 1:
        shadow(w, 540, TABLE + 10 + 400 * side, 610)
        ob(w, PEAU, 540, TABLE - 110 + 900 * side, 720, s=life(t, 5.2, dur=0.35))
    # les fleurs (hortensia) et les tomates arrivent
    fx = lerp(-300, 290, ease_out((t - 7.19) / 0.4))
    if t > 7.19:
        shadow(w, fx, TABLE + 40, 340)
        ob(w, HORTENSIA, fx, TABLE + 40, 540, anchor="bottom")
    tx = lerp(1400, 820, ease_out((t - 7.75) / 0.4))
    if t > 7.75:
        shadow(w, tx, TABLE + 30, 220)
        ob(w, TOMATES, tx, TABLE + 30, 250, anchor="bottom")
    # le potassium sort de la peau, puis file vers les plantes
    if 5.9 < t < 7.4:
        light_rays(w, 540, 760, t, fade(t, 5.9, 7.4, 0.3, 0.2))
        put(u, k_tile(250), 540, 760 - 30 * ease_out((t - 5.9) / 0.4), life(t, 5.92, 7.35))
        sparkles(u, t, 6.0, 540, 760, 250, 8, 4)
    if 7.4 < t < 9.4:
        for i, (ex, ey, t0) in enumerate([(290, 600, 7.45), (820, 800, 7.95)]):
            q = ease_io((t - t0) / 0.5)
            if q > 0:
                put(u, k_tile(130), lerp(540, ex, q), lerp(760, ey, q) - math.sin(math.pi * q) * 160,
                    1 - 0.4 * ease_in((t - t0 - 0.6) / 0.4) if t < 8.6 else life(t, t0, 8.9))
    if t > 8.55:
        put(u, icon("check", 120), 290, 540, life(t, 8.6))
        put(u, icon("check", 120), 820, 740, life(t, 8.72))
        sparkles(u, t, 8.6, 540, 820, 380, 10, 5)
    stamp(u, "OUI !", 540, 340, t, 5.27, 5.88, GREEN, 170, -8)
    title(u, "DU POTASSIUM", t, 5.92, 7.12, y=330, color=YEL, size=145)
    title(u, "LES FLEURS", t, 7.19, 7.7, y=330, size=160)
    title(u, "ET LES TOMATES", t, 7.75, 8.5, y=330, size=140)
    title(u, "ADORENT ÇA !", t, 8.55, None, y=330, color=YEL, size=160)
    return w, u


cue(5.29, "ding", 0.3)
cue(5.95, "rise", 0.22)
cue(7.22, "whoosh", 0.16)
cue(7.78, "whoosh", 0.16)
cue(8.6, "success", 0.28)


# ============================================================ C. POSÉE TELLE QUELLE : DES MOIS, MOUCHES, RONGEURS (9.4 → 15.4)
def fly_path(t, i):
    a = t * (3.1 + i * 0.7) + i * 2.1
    x = 650 + math.cos(a) * (150 + 30 * i) + math.sin(a * 2.3) * 40
    y = TABLE - 230 - math.sin(a * 1.4) * (110 + 20 * i)
    ang = math.degrees(math.atan2(-(math.cos(a * 1.4) * 1.4 * (110 + 20 * i)), -math.sin(a) * (150 + 30 * i)))
    return x, y, ang


def s_months(t):
    w, u = new_layers(background("table"))
    shadow(w, 330, TABLE + 40, 380)
    ob(w, HORTENSIA, 330, TABLE + 40, 600, anchor="bottom", s=life(t, 9.4, dur=0.35))
    # la peau posée au pied : elle noircit lentement
    rot_ = 0.85 * ease_io((t - 11.5) / 1.5)
    shadow(w, 650, TABLE + 25, 320, 60)
    ob(w, PEAU, 650, TABLE - 45, 350, s=life(t, 9.55, dur=0.35), rotten=rot_)
    if 9.6 < t < 11.3:
        d = ImageDraw.Draw(u)
        q = ease_out((t - 9.7) / 0.4)
        d.line([(650, TABLE - 300), (650, TABLE - 300 + 140 * q)], fill=WHITE, width=14)
        d.polygon([(620, TABLE - 170 + 140 * q - 140), (680, TABLE - 170 + 140 * q - 140),
                   (650, TABLE - 120 + 140 * q - 140)], fill=WHITE)
    if 11.4 < t < 13.0:
        act = min(2, int((t - 11.5) / 0.5))
        pills(u, ["1 MOIS", "2 MOIS", "3 MOIS"], act, t, 11.4, 12.95, y=560, pw=250)
    # les mouches
    if t > 13.05:
        for i in range(3):
            x, y, ang = fly_path(t, i)
            ob(w, MOUCHE, x, y, 85, s=life(t, 13.07 + i * 0.12, dur=0.25), rot=ang + 90)
        tag(u, "MOUCHES", 860, TABLE - 520, t, 14.27, None, rot=-5, size=52)
    # le rongeur
    if t > 14.59:
        rx = lerp(1350, 905, ease_out((t - 14.59) / 0.45))
        shadow(w, rx, TABLE + 30, 300)
        ob(w, RAT, rx, TABLE + 30, 380, anchor="bottom", flip=True)
        tag(u, "RONGEURS", 820, TABLE - 360, t, 14.83, None, rot=5, size=52)
    title(u, "POSÉE TELLE QUELLE ?", t, 9.43, 11.25, y=330, size=118)
    title(u, "DES MOIS !", t, 11.31, 13.0, y=330, color=RED, size=170)
    title(u, "LES MOUCHES…", t, 13.07, 14.55, y=330, size=150)
    title(u, "ET LES RONGEURS !", t, 14.59, None, y=330, color=RED, size=130)
    return w, u


cue(9.45, "pop", 0.2)
cue(11.52, "tick", 0.22)
cue(12.02, "tick", 0.22)
cue(12.52, "tick", 0.22)
cue(12.2, "fail", 0.18)
cue(13.1, "buzz", 0.3)
cue(14.62, "squeak", 0.3)


# ============================================================ D. ET L'EAU DE BANANE ? PRESQUE RIEN (15.4 → 18.95)
def gauge(c, t, t0, x, y, w_, val, a=1.0):
    if a <= 0.01:
        return
    d = ImageDraw.Draw(c)
    h_ = 64
    d.rounded_rectangle([x - w_ / 2, y - h_ / 2 + 8, x + w_ / 2, y + h_ / 2 + 8], radius=h_ / 2, fill=DARK)
    d.rounded_rectangle([x - w_ / 2, y - h_ / 2, x + w_ / 2, y + h_ / 2], radius=h_ / 2, fill=CREAM, outline=DARK,
                        width=6)
    fw = max(h_, (w_ - 12) * val)
    d.rounded_rectangle([x - w_ / 2 + 6, y - h_ / 2 + 6, x - w_ / 2 + 6 + fw, y + h_ / 2 - 6], radius=h_ / 2 - 6,
                        fill=RED)
    lab = text_img(f"{int(round(val * 100))} %", F_BLACK, 40, DARK)
    c.alpha_composite(lab, (int(x + w_ / 2 - lab.width - 30), int(y - lab.height / 2)))


def s_water(t):
    w, u = new_layers(background("table"))
    s_ = life(t, 15.4, dur=0.35)
    Hg = 690 * s_
    if Hg > 20:
        shadow(w, 540, TABLE + 40, 480 * s_)
        glass(w, 540, TABLE + 40, Hg, 1.0, 0.85, t, t * 2)
    # le potassium reste dans la peau : les K « rebondissent » contre la paroi de la peau
    if t > 17.35:
        for i, (dx, dy) in enumerate([(-40, -180), (50, -60), (-20, 60)]):
            bob = math.sin((t - 17.35) * 7 + i * 2) * 10
            put(u, k_tile(90), 540 + dx + bob, TABLE + 40 - 440 + dy, life(t, 17.4 + i * 0.1))
        gauge(u, t, 17.5, 540, 545, 700, 0.05 * ease_out((t - 17.6) / 0.6), life(t, 17.5))
        lab = text_img("DANS L'EAU", F_BLACK, 42, DARK)
        put(u, lab, 540, 478, life(t, 17.5))
    title(u, "ET L'EAU DE BANANE ?", t, 15.5, 17.3, y=330, color=YEL, size=118)
    stamp(u, "PRESQUE RIEN", 540, 330, t, 17.4, None, RED, 120, -6)
    return w, u


cue(15.45, "pop", 0.2)
cue(15.6, "stir", 0.18)
cue(17.42, "alert1", 0.3)
cue(17.65, "tick", 0.2)


# ============================================================ E. COUPE-LA EN MORCEAUX, AU COMPOST (18.95 → 21.65)
CH = (300, TABLE + 10)          # tas de morceaux (bas-centre)
CP_X, CP_BOT, CP_W = 770, TABLE + 90, 380


def s_chop(t):
    w, u = new_layers(background("table"))
    which, sc = swap((t - 19.85) / 0.3)
    fly = ease_io((t - 20.75) / 0.45)
    cin = ease_out((t - 20.47) / 0.4)
    if t > 20.47:   # le composteur arrive
        cx = lerp(1400, CP_X, cin)
        shadow(w, cx, CP_BOT, CP_W * 1.1)
        cw, csc = swap((t - 21.2) / 0.3)
        k = CP_W / 461
        ob(w, COMPO_O if cw == 0 else COMPO_F, cx, CP_BOT, CP_W * csc, anchor="bottom")
    px = lerp(540, CH[0], ease_io((t - 20.47) / 0.35))
    if fly <= 0:
        shadow(w, px, CH[1], 520 if which else 600)
        if which == 0:
            ob(w, PEAU, 540, TABLE - 80, 640 * sc)
        else:
            ob(w, MORCEAUX, px, CH[1], 480 * sc, anchor="bottom")
    elif fly < 1:   # les morceaux sautent dans le composteur (ouverture en haut)
        top = CP_BOT - 969 * CP_W / 461 + 170
        ob(w, MORCEAUX, lerp(CH[0], CP_X, fly), lerp(CH[1], top, fly) - math.sin(math.pi * fly) * 380,
           lerp(480, 160, fly), anchor="bottom", rot=-120 * fly)
    # le couteau
    if 19.2 < t < 19.95:
        for i, t0 in enumerate([19.25, 19.48, 19.71]):
            p = clamp((t - t0) / 0.22)
            if 0 < p < 1:
                down = math.sin(math.pi * p)
                kx = 380 + i * 150
                spr(w, KNIFE, kx + 150, TABLE - 300 + 200 * down, 70, shadow=False, rot=-70, anchor="center")
            if t > t0 + 0.11:
                ImageDraw.Draw(w).line([(380 + i * 150 + 30, TABLE - 200), (380 + i * 150 + 10, TABLE + 10)],
                                       fill=(120, 90, 40), width=5)
    title(u, "COUPE-LA", t, 18.99, 19.88, y=330, color=YEL, size=170)
    title(u, "EN PETITS MORCEAUX", t, 19.91, 20.45, y=330, size=115)
    title(u, "AU COMPOST !", t, 20.5, None, y=330, color=YEL, size=160)
    return w, u


cue(19.27, "chop", 0.35)
cue(19.5, "chop", 0.35)
cue(19.73, "chop", 0.35)
cue(19.9, "pop_hi", 0.2)
cue(20.5, "whoosh", 0.16)
cue(21.0, "plop", 0.3)
cue(21.3, "click", 0.35)


# ============================================================ F. LE COMPOST LIBÈRE LES VRAIS NUTRIMENTS (21.65 → 25.0)
def s_compost(t):
    w, u = new_layers(background("table"))
    warm_glow(w, fade(t, 22.6, None, 0.5))
    cx = lerp(CP_X, 330, ease_io((t - 21.65) / 0.4))
    shadow(w, cx, CP_BOT, CP_W * 1.1)
    ob(w, COMPO_F, cx, CP_BOT, CP_W, anchor="bottom")
    if 21.8 < t < 22.65:   # le temps passe (jour / nuit)
        night = 0.5 + 0.5 * math.sin((t - 21.8) * 12)
        w.alpha_composite(Image.new("RGBA", (W, H), (20, 26, 60, int(80 * night * fade(t, 21.8, 22.65, 0.1, 0.1)))))
    hx = lerp(1400, 800, ease_out((t - 22.67) / 0.45))
    if t > 22.67:
        shadow(w, hx, TABLE + 40, 330)
        ob(w, HORTENSIA, hx, TABLE + 40, 440, anchor="bottom")
    top = CP_BOT - 696 * CP_W / 461
    if t > 22.9:   # les nutriments sortent du compost et vont à la plante
        for i in range(4):
            t0 = 22.95 + i * 0.32
            q = ease_io((t - t0) / 0.6)
            if 0 < q < 1:
                put(u, k_tile(110), lerp(330, 760, q), lerp(top + 40, 900, q) - math.sin(math.pi * q) * 260, 1.0)
    if t > 24.3:
        sparkles(u, t, 24.3, 800, 820, 300, 10, 8)
        put(u, icon("check", 130), 800, 560, life(t, 24.35))
    title(u, "EN SE DÉCOMPOSANT", t, 21.67, 22.62, y=330, size=118)
    title(u, "ELLE LIBÈRE", t, 22.67, 23.85, y=330, color=YEL, size=160)
    stamp(u, "VRAIS NUTRIMENTS !", 540, 340, t, 23.9, None, GREEN, 100, -6)
    return w, u


cue(21.7, "tick", 0.2)
cue(22.0, "tick", 0.2)
cue(22.3, "tick", 0.2)
cue(22.7, "whoosh", 0.16)
cue(23.0, "rise", 0.22)
cue(24.33, "success", 0.3)


# ============================================================ G. L'HORTENSIA SUR LE BUFFET + ABONNE-TOI (25.0 → fin)
def s_end(t):
    w = photo("citron_fond_buffet.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    q = life(t, 25.05, dur=0.45)
    shadow(w, TOP[0], TOP[1], 300 * q)
    ob(w, HORTENSIA, TOP[0], TOP[1], 320, s=q, anchor="bottom")
    w = zoomed(w, 1.55, TOP[0], TOP[1] - 230)
    w.alpha_composite(shade())
    sparkles(u, t, 25.2, 540, 760, 330, 10, 7)
    clicked = t > 26.3
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 26.25) / 0.15))
    put(u, btn, 540, 1240, life(t, 25.3) * press)
    if t > 25.8:
        k = ease_out((t - 25.8) / 0.4)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(1520, 1280, k), 1)
    put(u, logo_img(260), 540, 330, life(t, 27.0, dur=0.45))
    sparkles(u, t, 27.1, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 25.05, 26.95, y=330, color=YEL, size=135)
    return w, u


cue(25.07, "pop_lo", 0.3)
cue(26.28, "click", 0.45)
cue(27.1, "sparkle", 0.25)

SCENES = [
    (0.0, 5.2, s_kitchen),
    (5.2, 9.4, s_yes),
    (9.4, 15.4, s_months),
    (15.4, 18.95, s_water),
    (18.95, 21.65, s_chop),
    (21.65, 25.0, s_compost),
    (25.0, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
