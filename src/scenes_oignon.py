"""Storyboard « Faire germer un oignon » (voix : assets/audio/oignon/voix.mp3), d'après le découpage fourni.

0–1.8  le placard (photo fournie) : gros plan sur l'oignon dans le panier, une pousse verte jaillit (pop).
1.8–4.5 la cuisine : l'oignon file vers la poubelle, grosse croix rouge, il revient se poser sur la planche.
4.5–7.5 fond beige : l'oignon descend dans un pot en terre, la terre se remplit autour, la pointe verte dépasse.
7.5–10  la fenêtre (photo fournie) : le pot glisse sur le rebord ensoleillé, un petit arrosoir verse quelques gouttes.
10–14   vue en coupe du pot : le bulbe se divise en 2, puis en 3.
14–17.6 les longues tiges vertes poussent, des ciseaux en coupent : comme de la ciboulette.
17.6–fin écran de fin « Les potagers de Louis » + bouton S'abonner animé.
Photos : oignon, oignon germé (court / long), placard, fenêtre (fournies) ; cuisine, poubelle zinc, pot de terreau,
arrosoir, ciseaux (vidéos précédentes).
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, put, title, life, fade, ease_out,
                 ease_io, ease_in, clamp, lerp, icon, pills, tag, button_img, hl_ellipse, particles, light_rays,
                 num_badge)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp, scissors
from scenes_citron import photo, shade, zoomed, shadow, swap
from scenes_banane import ob
from scenes_avocat3 import ZB_SHUT, BIN_X, BIN_W, BIN_BOT, bin_img, bsrc

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


OIGNON, COURT, LONG = "banque/oignon", "banque/oignon_germe_court", "banque/oignon_germe_long"
# bulbe dans chaque photo (cadre 1024) : centre x, largeur, haut du bulbe, bas
BULB = {OIGNON: (502, 653, 300, 931), COURT: (500, 436, 500, 941), LONG: (501, 295, 668, 969)}
POT, ARROSOIR = "citron/pot_vide", "banque/arrosoir_zinc"
P_BB = (291, 248, 965, 1025)                    # pot_vide (cadre 1254) : bbox ; surface de la terre (624, 412)


def onion(c, name, X, Ybot, bw, s=1.0, rot=0.0, alpha=1.0):
    """Oignon dont le BULBE fait bw de large, bas du bulbe en (X, Ybot)."""
    cx, w0, _, bot = BULB[name]
    place(c, name, (0, 0, 1024, 1024), bw / w0, cx, bot, X, Ybot, s, rot, 0.0, alpha)


def bulb_h(name, bw):
    cx, w0, top, bot = BULB[name]
    return (bot - top) * bw / w0


def pot_geom(X, Ybot, Wp):
    k = Wp / (P_BB[2] - P_BB[0])
    surf = (X + (624 - (P_BB[0] + P_BB[2]) / 2) * k, Ybot + (412 - P_BB[3]) * k)
    return k, surf, 300 * k, 132 * k


@lru_cache(None)
def soil_tex():
    im = Image.open(os.path.join(IMG, POT + ".png")).convert("RGBA").crop((420, 330, 830, 490))
    return im


def soil_patch(size):
    w_, h_ = max(2, int(size[0])), max(2, int(size[1]))
    return soil_tex().resize((w_, h_), Image.BICUBIC)


def planted(c, name, X, Ybot, Wp, bw, depth=1.0, mound=1.0, hole=0.0, drop=0.0):
    """Pot en terre avec l'oignon planté : depth 0 → 1 (il s'enfonce), mound 0 → 1 (la terre se referme autour)."""
    k, surf, rx, ry = pot_geom(X, Ybot, Wp)
    ob(c, POT, X, Ybot, Wp, anchor="bottom")
    if hole > 0.01:   # trou creusé au centre
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hr = bw * 0.62 * hole
        ImageDraw.Draw(ov).ellipse([surf[0] - hr, surf[1] - hr * 0.36, surf[0] + hr, surf[1] + hr * 0.36],
                                   fill=(28, 18, 10, 230))
        c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(3)))
    # l'oignon : au-dessus du pot il est entier, puis le bas disparaît sous la surface
    hb = bulb_h(name, bw)
    yb = lerp(surf[1] - 520 - hb * 0.2, surf[1] + hb * 0.92, depth) - drop
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    onion(lay, name, X, yb, bw)
    m = Image.new("L", (W, H), 255)
    ImageDraw.Draw(m).rectangle([0, surf[1] + 4, W, H], fill=0)
    m = m.filter(ImageFilter.GaussianBlur(3))
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
    c.alpha_composite(lay)
    # la terre revient autour du collet (on laisse dégagée la pointe verte)
    if mound > 0.01:
        mr = bw * 0.75 * mound
        tex = soil_patch((2 * mr, mr * 0.7))
        mm = Image.new("L", tex.size, 0)
        ImageDraw.Draw(mm).ellipse([0, 0, tex.width - 1, tex.height - 1], fill=255)
        cut = int(tex.width / 2 - bw * 0.1), int(tex.width / 2 + bw * 0.1)
        ImageDraw.Draw(mm).rectangle([cut[0], 0, cut[1], int(tex.height * 0.42)], fill=0)
        mm = mm.filter(ImageFilter.GaussianBlur(4))
        tex.putalpha(mm)
        c.alpha_composite(tex, (int(surf[0] - tex.width / 2), int(surf[1] - tex.height * 0.42)))
    return surf


# ============================================================ 1. LE PLACARD (0 → 1.83)
PL_ON = (418, 1438)                             # oignon posé sur le haut du panier


def s_placard(t):
    w = photo("fond_placard.webp").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    which, sc = swap((t - 0.5) / 0.28)
    shadow(w, PL_ON[0], PL_ON[1], 100, 60)
    if which == 0:
        onion(w, OIGNON, PL_ON[0], PL_ON[1], 100 * sc)
    else:
        onion(w, COURT, PL_ON[0], PL_ON[1], 100 * sc)
    zk = ease_io(t / 0.6)
    w = zoomed(w, lerp(1.25, 2.1, zk), lerp(540, PL_ON[0], zk), lerp(1150, PL_ON[1] - 120, zk))
    w.alpha_composite(shade())
    if t > 0.64:
        sparkles(u, t, 0.66, 540, 760, 220, 8, 3)
    title(u, "TON OIGNON GERME ?", t, 0.05, None, y=330, color=YEL, size=130)
    return w, u


cue(0.04, "whoosh_up", 0.16)
cue(0.62, "pop_hi", 0.35)
cue(0.7, "sparkle", 0.2)


# ============================================================ 2. NE LE JETTE PAS (1.83 → 4.47)
BD = (390, 1235)                                # oignon sur la planche (bas du bulbe)
BW = 125


def s_bin(t):
    w = photo("citron_fond_cuisine.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shake = math.sin(t * 60) * 6 * fade(t, 2.28, 2.6, 0.02, 0.2) if 2.28 < t < 2.6 else 0.0
    shadow(w, BIN_X, BIN_BOT, BIN_W * 0.95)
    bin_img(w, ZB_SHUT, shake)
    top = (BIN_X, bsrc(0, 120)[1])
    go = ease_io((t - 1.86) / 0.42)               # vers la poubelle…
    back = ease_io((t - 2.55) / 0.5)              # … refusé : il revient sur la planche
    if t < 2.55:
        x, y = lerp(BD[0], top[0] - 120, go), lerp(BD[1], top[1] - 60, go) - math.sin(math.pi * go) * 260
        rot = -25 * go
    else:
        x, y = lerp(top[0] - 120, BD[0], back), lerp(top[1] - 60, BD[1], back) - math.sin(math.pi * back) * 200
        rot = -25 * (1 - back)
    land = 1 - 0.1 * math.sin(math.pi * clamp((t - 3.05) / 0.2)) if t > 3.05 else 1.0
    if back >= 1 or go <= 0:
        shadow(w, BD[0], BD[1], BW * 1.1, 60)
    onion(w, COURT, x, y, BW * land, rot=rot)
    w = zoomed(w, 1.2, 620, 1150)
    w.alpha_composite(shade())
    if 2.26 < t < 3.4:
        s_ = life(t, 2.27, 3.3, dur=0.25)
        put(u, icon("cross", 360), 820, 820, s_, -8 + math.sin((t - 2.27) * 20) * 4 * fade(t, 2.27, 2.6, 0.01, 0.2))
    title(u, "NE LE JETTE PAS !", t, 1.86, 2.95, y=330, color=RED, size=145)
    title(u, "IL T'EN DONNERA", t, 2.99, 3.8, y=330, size=150)
    title(u, "D'AUTRES !", t, 3.83, None, y=330, color=YEL, size=180)
    return w, u


cue(1.88, "whoosh", 0.2)
cue(2.28, "alert2", 0.35)
cue(2.58, "whoosh", 0.16)
cue(3.06, "thud", 0.3)
cue(3.85, "ding", 0.25)


# ============================================================ 3. PLANTE-LE DANS UN POT (4.47 → 7.55)
PX, PBOT, PWD = 540, TABLE + 80, 700
PBW = 300


def s_plant(t):
    w, u = new_layers(background("table"))
    s_ = life(t, 4.47, dur=0.35)
    shadow(w, PX, PBOT, PWD * 0.75 * s_)
    depth = ease_in((t - 4.75) / 0.55)
    mound = ease_out((t - 5.3) / 0.55)
    hole = (1 - mound) * life(t, 4.6, dur=0.3)
    if s_ < 0.99:
        ob(w, POT, PX, PBOT, PWD, s=s_, anchor="bottom")
        surf = pot_geom(PX, PBOT, PWD)[1]
    else:
        surf = planted(w, COURT, PX, PBOT, PWD, PBW, depth, mound, hole)
    if 5.3 < t < 5.95:   # la terre tombe autour
        for i in range(3):
            particles(w, t, 5.3 + i * 0.15, PX + (i - 1) * 120, surf[1] - 260, 14, i + 3, col=(62, 42, 28),
                      size=12, up=30, spread=90, dur=0.5)
    if t > 5.75:   # la pointe verte, juste au-dessus de la terre
        tip_y = surf[1] - 230
        hl_ellipse(u, PX + 10, tip_y, 120, 170, life(t, 5.78))
        tag(u, "POINTE VERTE", 850, 560, t, 5.8, None, rot=-6, size=52, string_to=(PX + 90, tip_y - 60))
    if t > 6.47:
        d = ImageDraw.Draw(u)
        a = life(t, 6.5)
        for xx in range(int(PX - 330), int(PX + 330), 34):
            d.line([(xx, surf[1] + 2), (xx + 18, surf[1] + 2)], fill=WHITE + (int(240 * a),), width=6)
    title(u, "PLANTE-LE", t, 4.5, 5.55, y=330, color=YEL, size=175)
    title(u, "LA POINTE VERTE", t, 5.59, 6.43, y=330, size=145)
    title(u, "AU-DESSUS DE LA TERRE", t, 6.47, None, y=330, color=YEL, size=112)
    return w, u


cue(4.5, "pop", 0.22)
cue(4.8, "whoosh", 0.15)
cue(5.32, "rustle", 0.3)
cue(5.82, "pop_hi", 0.2)


# ============================================================ 4. PRÈS D'UNE FENÊTRE, ARROSAGE LÉGER (7.55 → 10.05)
SILL = (540, 1428)                              # rebord de la fenêtre (photo 1080 x 1920)
SW = 300
DROPS_T = 8.95


def s_window(t):
    w = photo("fond_fenetre.webp").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    light_rays(w, 330, 300, t, fade(t, 7.6, None, 0.5))
    slide = ease_out((t - 7.55) / 0.5)
    px = lerp(-300, SILL[0], slide)
    shadow(w, px, SILL[1], SW * 0.8, 80)
    surf = planted(w, COURT, px, SILL[1], SW, SW * 0.43, 1.0, 1.0)
    # le petit arrosoir : quelques gouttes
    cin = ease_out((t - 8.6) / 0.3)
    cout = ease_in((t - 9.75) / 0.3)
    if 8.6 < t < 10.05:
        tilt = -28 * ease_io((t - 8.8) / 0.2) * (1 - cout)
        ob(w, ARROSOIR, lerp(-200, surf[0] - 133, cin) - 600 * cout, surf[1] - 160, 250, rot=tilt, flip=True)
        if DROPS_T < t < 9.8:
            rose = (surf[0] - 22, surf[1] - 152)
            for k in range(7):
                p = (t - DROPS_T - k * 0.11) / 0.32
                if 0 < p < 1:
                    x = rose[0] + (k % 3 - 1) * 9 + 22 * p
                    y = lerp(rose[1], surf[1] - 4, p * p)
                    ImageDraw.Draw(w).ellipse([x - 4, y - 6, x + 4, y + 6], fill=(214, 234, 250, 225))
                elif 1 <= p < 1.6:
                    particles(w, t, DROPS_T + k * 0.11 + 0.32, rose[0] + 22 + (k % 3 - 1) * 9, surf[1] - 4, 4, k,
                              col=(214, 234, 250), size=5, up=110, dur=0.2)
    w = zoomed(w, 1.7, 545, 1160)
    w.alpha_composite(shade())
    if t > 8.15:
        put(u, icon("sun", 170), 880, 560, life(t, 8.15), t * 25)
    title(u, "PRÈS D'UNE FENÊTRE", t, 7.58, 8.55, y=330, color=YEL, size=125)
    title(u, "ARROSAGE LÉGER", t, 8.59, None, y=330, size=140)
    return w, u


cue(7.58, "whoosh", 0.18)
cue(8.18, "rise", 0.18)
cue(8.62, "whoosh", 0.14)
for _k in range(0, 7, 2):
    cue(DROPS_T + 0.32 + _k * 0.11, "plop", 0.12)


# ============================================================ 5. VUE EN COUPE : IL SE DIVISE (10.05 → 14.1)
CX, CTOP, CBOT, CWT, CWB = 540, 800, 1400, 760, 560     # pot en coupe : haut, bas, largeurs
SOIL_Y = CTOP + 110


def section_pot(c, t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    th = 34
    outer = [(CX - CWT / 2, CTOP), (CX + CWT / 2, CTOP), (CX + CWB / 2, CBOT), (CX - CWB / 2, CBOT)]
    inner = [(CX - CWT / 2 + th, CTOP), (CX + CWT / 2 - th, CTOP), (CX + CWB / 2 - th, CBOT - th),
             (CX - CWB / 2 + th, CBOT - th)]
    d.polygon(outer, fill=(196, 102, 64))
    d.polygon(inner, fill=(110, 66, 44))
    c.alpha_composite(ov)
    # la terre (texture de la photo) dans le pot, sous la surface
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tile = soil_patch((280, 110))
    for yy in range(SOIL_Y - 10, CBOT, 100):
        for xx in range(int(CX - CWT / 2), int(CX + CWT / 2), 270):
            lay.alpha_composite(tile, (xx + (yy // 100 % 2) * 135 - 135, yy))
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(inner, fill=255)
    ImageDraw.Draw(m).rectangle([0, 0, W, SOIL_Y], fill=0)
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
    c.alpha_composite(lay)
    d = ImageDraw.Draw(c)
    d.line([inner[0], inner[3]], fill=(232, 150, 108), width=5)        # faces coupées (plus claires)
    d.line([inner[1], inner[2]], fill=(232, 150, 108), width=5)
    d.rounded_rectangle([CX - CWT / 2 - 26, CTOP - 54, CX + CWT / 2 + 26, CTOP + 6], radius=12, fill=(206, 110, 70),
                        outline=(150, 74, 44), width=4)


SPLITS = [[(0, 270)], [(-110, 210), (110, 210)], [(-175, 170), (0, 180), (175, 170)]]


def s_split(t):
    w, u = new_layers(background("table"))
    warm_glow = fade(t, 10.1, None, 0.4)
    light_rays(w, 140, 200, t, 0.6 * warm_glow)
    shadow(w, CX, CBOT + 4, CWB * 1.05)
    section_pot(w, t)
    # 1 → 2 → 3 bulbes (changement sans superposition)
    stage, sc = 0, 1.0
    if t > 11.8:
        which, sc = swap((t - 11.8) / 0.3)
        stage = which
    if t > 12.8:
        which, sc = swap((t - 12.8) / 0.3)
        stage = 1 + which
    for dx, bw in SPLITS[stage]:
        onion(w, COURT, CX + dx, SOIL_Y + bulb_h(COURT, bw) * 0.92, bw * sc)
    if 10.3 < t < 11.75:
        act = min(3, int((t - 10.35) / 0.33))
        pills(u, ["S1", "S2", "S3", "S4"], act, t, 10.3, 11.7, y=560, pw=170)
    if t > 13.2:
        sparkles(u, t, 13.2, CX, SOIL_Y + 120, 330, 10, 6)
        tag(u, "NOUVEAUX OIGNONS !", 760, 640, t, 13.27, None, rot=-4, size=50)
    title(u, "QUELQUES SEMAINES…", t, 10.07, 11.4, y=330, size=125)
    title(u, "IL SE DIVISE", t, 11.43, 12.55, y=330, color=YEL, size=160)
    stamp(u, "EN PLUSIEURS !", 540, 340, t, 12.59, None, GREEN, 125, -6)
    return w, u


cue(10.09, "whoosh", 0.16)
for _k in range(4):
    cue(10.36 + _k * 0.33, "tick", 0.2)
cue(11.92, "pop_hi", 0.28)
cue(12.92, "pop_hi", 0.3)
cue(13.3, "success", 0.28)


# ============================================================ 6. LES TIGES SE MANGENT COMME DE LA CIBOULETTE (14.1 → 17.65)
LX, LBOT, LBW = 470, TABLE + 60, 300
CUT_T = 15.95


def s_chives(t):
    w, u = new_layers(background("table"))
    k = LBW / BULB[LONG][1]
    which, sc = swap((t - 14.15) / 0.32)
    shadow(w, LX, LBOT, LBW * 1.1)
    if t < CUT_T:
        onion(w, COURT if which == 0 else LONG, LX, LBOT, LBW * sc)
    else:
        # les tiges coupées : le bas reste, le haut tombe sur la table
        cut_y = LBOT - (BULB[LONG][3] - 390) * k
        full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        onion(full, LONG, LX, LBOT, LBW)
        low, high = full.copy(), full.copy()
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle([0, cut_y, W, H], fill=255)
        low.putalpha(Image.composite(low.getchannel("A"), Image.new("L", (W, H), 0), m))
        high.putalpha(Image.composite(Image.new("L", (W, H), 0), high.getchannel("A"), m))
        w.alpha_composite(low)
        f = ease_in((t - CUT_T) / 0.55)
        bb = high.getbbox()
        if bb:
            piece = high.crop(bb)
            land = ease_out((t - CUT_T - 0.55) / 0.2) if t > CUT_T + 0.55 else 0
            ang = lerp(0, -90, f)
            px = lerp((bb[0] + bb[2]) / 2, 820, f)
            py = lerp((bb[1] + bb[3]) / 2, LBOT - 40, f)
            if f >= 1:
                shadow(w, 820, LBOT + 5, 300, 50)
            put(w, piece.rotate(ang, expand=True, resample=Image.BICUBIC), px, py, 1.0)
    if 15.25 < t < CUT_T + 0.3:   # les ciseaux traversent les tiges
        cy = LBOT - (BULB[LONG][3] - 390) * k
        scissors(u, (LX + 260, cy), (LX - 120, cy), (t - 15.35) / 0.6, flip=True, hh=150)
    if t > 16.47:
        tag(u, "COMME DE LA CIBOULETTE !", 600, 640, t, 16.5, None, rot=-4, size=46)
        sparkles(u, t, 16.5, 820, LBOT - 60, 200, 8, 4)
    title(u, "EN ATTENDANT…", t, 14.15, 15.1, y=330, size=160)
    title(u, "SES TIGES VERTES", t, 15.15, 15.95, y=330, color=YEL, size=140)
    title(u, "SE MANGENT !", t, 15.99, None, y=330, size=165)
    return w, u


cue(14.18, "rise", 0.22)
cue(15.6, "chop", 0.35)
cue(15.9, "chop", 0.35)
cue(16.55, "pop", 0.22)


# ============================================================ 7. ÉCRAN DE FIN (17.65 → fin)
def s_end(t):
    w, u = new_layers(background("table"))
    warm = fade(t, 17.7, None, 0.4)
    light_rays(w, 540, 300, t, 0.7 * warm)
    shadow(w, 820, TABLE + 60, 240 * life(t, 17.7))
    if life(t, 17.7) > 0.99:
        planted(w, LONG, 820, TABLE + 60, 300, 110, 1.0, 1.0)
    else:
        ob(w, POT, 820, TABLE + 60, 300, s=life(t, 17.7), anchor="bottom")
    put(u, logo_img(320), 540, 620, life(t, 17.75, dur=0.45))
    sparkles(u, t, 17.85, 540, 620, 240, 10, 12)
    clicked = t > 19.15
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 19.1) / 0.15))
    put(u, btn, 470, 960, life(t, 18.1) * press)
    if t > 18.6:
        k = ease_out((t - 18.6) / 0.45)
        put(u, icon("cursor", 110), lerp(820, 570, k), lerp(1240, 1000, k), 1)
    title(u, "LES POTAGERS DE LOUIS", t, 17.68, None, y=300, color=YEL, size=112)
    return w, u


cue(17.7, "pop_lo", 0.3)
cue(19.12, "click", 0.45)
cue(19.7, "sparkle", 0.25)

SCENES = [
    (0.0, 1.83, s_placard),
    (1.83, 4.47, s_bin),
    (4.47, 7.55, s_plant),
    (7.55, 10.05, s_window),
    (10.05, 14.1, s_split),
    (14.1, 17.65, s_chives),
    (17.65, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
