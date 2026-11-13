"""Storyboard « Brûler ses feuilles mortes : interdit » (voix : assets/audio/feuilles_feu/voix.wav).

Décors fournis : le petit jardin avec les maisons du village au fond, le potager en carrés vides / plantés.
0–6       le jardin : un tas de feuilles tout noir (suspense) ; « interdit » ; l'avis de contravention de 450 €.
6–9.1     le tas se révèle… et prend feu : « brûler tes feuilles mortes, c'est interdit en France ».
9.1–14.15 la fumée monte, la caméra file vers les maisons du village, enfumées : particules toxiques.
14.15–17.2 bonne nouvelle : tes feuilles valent de l'or (fond beige, feuilles dorées).
17.2–20.1 le potager : on étale les feuilles en paillage, ou on les met au compost.
20.1–22.9 au printemps : elles sont devenues un terreau gratuit.
22.9–fin  bouton S'abonner et logo.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, put, title, life, fade, ease_out, ease_io, ease_in,
                 ease_out_back, clamp, lerp, icon, tag, button_img, particles, text_img, F_TITLE, F_BLACK, light_rays,
                 background)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import photo, shade, zoomed, shadow
from scenes_banane import ob
from scenes_fumier import Cam, decor, bed_pt, BED, VIDES, PLANTES

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)
SFX_GAIN = 0.27
DUCK = 0.45
TRANS_GAIN = 0.22
SHIFT = 0.25


def cue(t, name, gain=0.5):
    CUES.append((t - SHIFT, name, gain))


JARDIN = "decor_jardin_pelouse_arbres.webp"
TAS, TAS_NOIR = "feuilles/tas_feuilles", "banque/tas_feuilles_noir"
LEAVES = ["banque/feuille_morte_a", "banque/feuille_morte_b", "feuilles/feuille_a", "feuilles/feuille_b",
          "feuilles/feuille_c"]
COMPOST = "compost/composteur_ouvert"
PILE = (620, 1560)                               # le tas sur la pelouse (photo plein écran)
PILE_W = 560
HOUSES = (700, 840)                              # les maisons du village au fond


# ------------------------------------------------------------ effets : feu, fumée, avis de contravention
def fire(c, x, y, w, t, a=1.0):
    """Flammes : des langues de feu qui ondulent (rouge à l'extérieur, orange, cœur jaune), étincelles et halo."""
    if a <= 0.01:
        return
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([x - w * 0.9, y - w * 1.2, x + w * 0.9, y + w * 0.3],
                                 fill=(255, 120, 30, int(110 * a)))
    c.alpha_composite(glow.filter(ImageFilter.GaussianBlur(w * 0.2)))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    r = np.random.default_rng(5)
    tongues = [(r.uniform(-0.42, 0.42), r.uniform(0.55, 1.1), r.uniform(0, 6), r.uniform(5, 9)) for _ in range(13)]
    tongues.sort(key=lambda q: -q[1])
    for scale, col in ((1.0, (205, 45, 15)), (0.72, (250, 125, 20)), (0.42, (255, 220, 120))):
        for ox, hh, ph, fq in tongues:
            bx = x + ox * w * (1.0 if scale == 1.0 else 0.9)
            hgt = w * hh * scale * (0.85 + 0.25 * math.sin(t * fq + ph)) * (1 - abs(ox) * 0.9)
            bw = w * 0.16 * scale
            sway = math.sin(t * fq * 0.7 + ph) * bw * 0.9
            pts = [(bx - bw, y)]
            for k in range(1, 9):
                q = k / 8
                pts.append((bx - bw * (1 - q) ** 0.8 + sway * q * q, y - hgt * q))
            for k in range(8, 0, -1):
                q = k / 8
                pts.append((bx + bw * (1 - q) ** 0.8 + sway * q * q, y - hgt * q))
            pts.append((bx + bw, y))
            d.polygon(pts, fill=col + (int(200 * a),))
    # bords doux et vacillants (pas de « dessin » net) : flou + une couche plus floue par-dessus
    c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(7)))
    soft = lay.filter(ImageFilter.GaussianBlur(18))
    soft.putalpha(soft.getchannel("A").point(lambda v: v // 2))
    c.alpha_composite(soft)
    # étincelles qui s'envolent
    d = ImageDraw.Draw(c)
    for i in range(18):
        p = (t * r.uniform(0.6, 1.1) + i / 18) % 1.0
        xx = x + r.uniform(-0.4, 0.4) * w + math.sin(t * 3 + i) * 30 * p
        yy = y - w * (0.4 + 1.4 * p)
        s_ = 3 * (1 - p) + 1
        d.ellipse([xx - s_, yy - s_, xx + s_, yy + s_], fill=(255, 200, 80, int(230 * a * (1 - p))))


def smoke(c, x, y, t, t0, a=1.0, drift=420, height=1300, n=46, dark=0.0):
    """Fumée : volutes grises qui montent, grossissent et dérivent vers la droite (vers les maisons)."""
    if a <= 0.01 or t < t0:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    r = np.random.default_rng(8)
    age = t - t0
    for i in range(n):
        sp = r.uniform(0.16, 0.24)
        p = (age * sp + i / n) % 1.0
        if p > min(1.0, age * 0.45 + 0.05):   # au début, la colonne de fumée monte peu à peu
            continue
        xx = x + drift * p ** 1.3 + math.sin(t * 0.8 + i) * 40 * p
        yy = y - height * p
        rad = 50 + 330 * p
        g = int(lerp(150, 90, dark))
        al = int(235 * a * (1 - p) ** 0.6 * min(1, p * 6))
        d.ellipse([xx - rad, yy - rad, xx + rad, yy + rad], fill=(g + 25, g + 25, g + 28, al // 2))
        d.ellipse([xx - rad * 0.7, yy - rad * 0.7, xx + rad * 0.7, yy + rad * 0.7], fill=(g, g, g + 3, al))
    c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(16)))


def smoke_band(c, t, t0, y, a=1.0, dark=0.0):
    """Nappe de fumée qui traverse le quartier de gauche à droite, à hauteur des toits."""
    if a <= 0.01 or t < t0:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    r = np.random.default_rng(9)
    for i in range(40):
        sp = r.uniform(110, 190)
        xx = (r.uniform(-300, W + 300) + (t - t0) * sp) % (W + 700) - 350
        yy = y + r.uniform(-260, 260) + math.sin(t * 0.6 + i) * 30
        rad = r.uniform(140, 280)
        g = int(lerp(155, 95, dark))
        al = int(200 * a * clamp((t - t0) * 1.2 - r.uniform(0, 0.6)))
        if al > 0:
            d.ellipse([xx - rad, yy - rad * 0.7, xx + rad, yy + rad * 0.7], fill=(g, g, g + 3, al))
    c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(30)))


def toxic(c, cam, t, t0, a=1.0):
    """Particules toxiques : des grains sombres en suspension dans la fumée."""
    if a <= 0.01 or t < t0:
        return
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(12)
    for i in range(70):
        bx, by = r.uniform(250, 1050), r.uniform(450, 1400)
        X, Y = cam.p(bx + 30 * math.sin(t * 0.7 + i), by - 60 * ((t - t0) * 0.3 + i * 0.13) % 300)
        s = r.uniform(2, 5) * cam.z * 0.8
        d.ellipse([X - s, Y - s, X + s, Y + s], fill=(40, 36, 34, int(200 * a)))


@lru_cache(None)
def ticket_img(w=560):
    """Avis de contravention (dessiné)."""
    h = int(w * 0.62)
    k = 2
    big = Image.new("RGBA", ((w + 30) * k, (h + 30) * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle([14 * k, 22 * k, (w + 14) * k, (h + 22) * k], radius=16 * k, fill=(0, 0, 0, 90))
    d.rounded_rectangle([0, 0, w * k, h * k], radius=16 * k, fill=(250, 248, 240), outline=DARK, width=5 * k)
    d.rounded_rectangle([0, 0, w * k, int(h * 0.26) * k], radius=16 * k, fill=(36, 62, 140))
    d.rectangle([0, int(h * 0.15) * k, w * k, int(h * 0.26) * k], fill=(36, 62, 140))
    for i in range(3):
        yy = int(h * (0.78 + i * 0.06)) * k
        d.line([(40 * k, yy), ((w - 40) * k, yy)], fill=(190, 190, 185), width=3 * k)
    im = big.resize((w + 30, h + 30), Image.LANCZOS)
    t1 = text_img("AVIS DE CONTRAVENTION", F_BLACK, int(w * 0.07), WHITE)
    im.alpha_composite(t1, ((w - t1.width) // 2, int(h * 0.13 - t1.height / 2)))
    t2 = text_img("450 €", F_TITLE, int(w * 0.3), RED, stroke=6, stroke_fill=DARK)
    im.alpha_composite(t2, ((w - t2.width) // 2, int(h * 0.48 - t2.height / 2)))
    return im


# ============================================================ A. LE TAS NOIR (SUSPENSE) → IL BRÛLE (0 → 9.1)
def s_garden(t):
    cam = Cam(lerp(1.0, 1.1, clamp(t / 9.0)), 600, 1150)
    w = zoomed(photo(JARDIN), cam.z, cam.fx, cam.fy).copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    px, py = cam.p(*PILE)
    reveal = ease_io(clamp((t - 6.1) / 0.35))
    s_in = ease_out_back(clamp((t - 0.1) / 0.45), 1.5)
    shadow(w, px, py + 20 * z, PILE_W * z * 0.95 * s_in, 90)
    burnt = clamp((t - 7.4) / 1.6)                       # il noircit en brûlant
    if reveal < 1:
        ob(w, TAS_NOIR, px, py, PILE_W * z, s=max(0.01, s_in), anchor="bottom")
    if reveal > 0:
        ob(w, TAS, px, py, PILE_W * z, alpha=reveal * (1 - 0.55 * burnt), anchor="bottom")
        if burnt > 0:
            ob(w, TAS_NOIR, px, py, PILE_W * z, alpha=0.55 * burnt, anchor="bottom")
    if t > 6.55:   # le feu
        fa = fade(t, 6.55, None, 0.35)
        smoke(w, px, py - 220 * z, t, 6.8, fade(t, 6.8, None, 0.8), drift=380, height=1400)
        fire(w, px, py - 40 * z, PILE_W * z * lerp(0.4, 0.75, ease_out((t - 6.55) / 0.6)), t, fa)
    if 6.1 < t < 6.35:   # flash de la révélation
        w.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(170 * (1 - (t - 6.1) / 0.25)))))
    w.alpha_composite(shade())
    # suspense : un « ? » qui pulse au-dessus du tas noir
    if t < 6.1:
        q = text_img("?", F_TITLE, 200, YEL, stroke=10, stroke_fill=DARK)
        put(u, q, px, py - 420 * z, life(t, 0.5, 6.0) * (1 + 0.06 * math.sin(t * 6)))
    # l'avis de contravention de 450 €
    if 4.2 < t < 6.15:
        k = ease_out_back(clamp((t - 4.22) / 0.4), 1.6)
        put(u, ticket_img(), 540, lerp(1900, 820, k), 1.0, rot=lerp(25, -6, k), alpha=life(t, 4.2, 6.05))
    if t > 7.8:
        put(u, icon("nosign", 300), px, py - 300 * z, life(t, 7.82, 9.0))
    title(u, "CE QUE TU FAIS CHAQUE ANNÉE…", t, 0.05, 2.25, y=330, color=WHITE, size=100)
    stamp(u, "INTERDIT !", 540, 340, t, 2.3, 3.15, RED, 165, -7)
    title(u, "TU RISQUES…", t, 3.2, 4.2, y=330, color=YEL, size=170)
    title(u, "UNE AMENDE !", t, 4.24, 6.05, y=330, color=RED, size=150)
    title(u, "BRÛLER TES FEUILLES ?", t, 6.1, 7.75, y=330, color=YEL, size=115)
    stamp(u, "INTERDIT EN FRANCE !", 540, 340, t, 7.8, 9.0, RED, 86, -6)
    return w, u


cue(0.12, "pop_lo", 0.18)
cue(0.6, "tick", 0.12)
cue(2.32, "alert1", 0.22)
cue(4.24, "whoosh_up", 0.14)
cue(4.5, "fail", 0.18)
cue(6.12, "pop", 0.2)
cue(6.55, "feu", 0.35)
cue(7.82, "alert2", 0.2)


# ============================================================ B. LA FUMÉE SUR TOUT LE QUARTIER (9.1 → 14.15)
def s_smoke(t):
    k = ease_io(clamp((t - 10.2) / 1.4))
    cam = Cam(lerp(1.1, 1.75, k), lerp(600, HOUSES[0], k), lerp(1150, HOUSES[1], k))
    w = zoomed(photo(JARDIN), cam.z, cam.fx, cam.fy).copy()
    z = cam.z
    px, py = cam.p(*PILE)
    # le quartier se voile de gris
    haze = fade(t, 10.6, None, 1.5)
    w.alpha_composite(Image.new("RGBA", (W, H), (120, 118, 112, int(70 * haze))))
    if py < H + 200:
        ob(w, TAS_NOIR, px, py, PILE_W * z, alpha=0.6, anchor="bottom")
        ob(w, TAS, px, py, PILE_W * z, alpha=0.4, anchor="bottom")
        fire(w, px, py - 40 * z, PILE_W * z * 0.7, t, 1.0)
    sx, sy = cam.p(PILE[0], PILE[1] - 220)
    smoke(w, sx, sy, t, 6.8, 1.0, drift=420 * z, height=1400 * z, dark=clamp((t - 11.3) / 1.0))
    # la fumée qui passe devant les maisons
    hx, hy = cam.p(*HOUSES)
    smoke_band(w, t, 10.3, hy - 60, fade(t, 10.3, None, 1.0), dark=clamp((t - 11.3) / 1.0))
    toxic(w, cam, t, 11.5, fade(t, 11.5, None, 0.5))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 11.55:
        tag(u, "PARTICULES TOXIQUES", 540, 1180, t, 11.6, None, rot=-5, size=56)
    if t > 13.4:
        put(u, icon("cross", 170), 880, 700, life(t, 13.42))
    title(u, "POURQUOI ?", t, 9.15, 9.9, y=330, color=YEL, size=190)
    title(u, "LA FUMÉE…", t, 9.92, 11.5, y=330, color=WHITE, size=180)
    title(u, "POLLUE TOUT LE QUARTIER", t, 12.5, None, y=330, color=RED, size=105)
    return w, u


cue(9.17, "pop", 0.14)
cue(10.2, "whoosh", 0.12)
cue(11.6, "alert3", 0.18)
cue(13.44, "fail", 0.16)


# ============================================================ C. BONNE NOUVELLE : TES FEUILLES VALENT DE L'OR (14.15 → 17.2)
def s_gold(t):
    w = background("table")
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    r = np.random.default_rng(4)
    gold = fade(t, 16.5, None, 0.5)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i in range(14):
        t0 = 14.3 + i * 0.07
        q = ease_out(clamp((t - t0) / 0.55))
        if q <= 0:
            continue
        x = 540 + r.uniform(-330, 330)
        y = lerp(-200, 900 + r.uniform(-260, 380), q)
        ob(lay, LEAVES[i % len(LEAVES)], x, y, r.uniform(190, 280), rot=r.uniform(-60, 60) + (1 - q) * 160)
    if gold > 0.01:   # elles prennent un éclat doré
        a = np.asarray(lay).astype(np.float32)
        g = np.array([255, 205, 70], np.float32)
        a[..., :3] = a[..., :3] * (1 - 0.45 * gold) + g * 0.45 * gold
        lay = Image.fromarray(a.astype(np.uint8), "RGBA")
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([140, 520, 940, 1360], fill=(255, 220, 120, int(110 * gold)))
        w.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))
    w.alpha_composite(lay)
    if t > 16.5:
        sparkles(u, t, 16.52, 540, 950, 420, 16, 5, dur=1.2)
    title(u, "BONNE NOUVELLE !", t, 14.25, 15.4, y=330, color=GREEN, size=150)
    title(u, "TES FEUILLES…", t, 15.44, 16.45, y=330, color=WHITE, size=165)
    stamp(u, "VALENT DE L'OR !", 540, 340, t, 16.5, None, YEL, 125, -6)
    return w, u


cue(14.27, "success", 0.18)
cue(14.4, "rustle", 0.16)
cue(16.55, "sparkle", 0.2)


# ============================================================ D. PAILLAGE OU COMPOST (17.2 → 20.1)  E. TERREAU (20.1 → 22.9)
def _leaf_stamps():
    r = np.random.default_rng(31)
    st = []
    for i in range(170):
        u_, v_ = r.uniform(0.03, 0.97), r.uniform(0.02, 0.98)
        st.append((u_, v_, r.uniform(0.8, 1.2), r.uniform(0, 360), i % len(LEAVES), r.uniform(0, 1)))
    st.sort(key=lambda s: s[1])
    return st


LSTAMPS = _leaf_stamps()


@lru_cache(512)
def leaf_img(which, w, rot):
    im = Image.open(os.path.join(IMG, LEAVES[which] + ".png")).convert("RGBA")
    im = im.crop(im.getbbox())
    h = max(2, int(w * im.height / im.width * 0.6))       # couchée au sol : vue en perspective
    im = im.resize((max(2, w), h), Image.LANCZOS)
    return im.rotate(rot, resample=Image.BICUBIC, expand=True)


def mulch(c, cam, t, t0=17.35, dur=1.2, decomp=0.0):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for u_, v_, s, rot, which, rnd in LSTAMPS:
        ts = t0 + (1 - v_) * dur * 0.6 + rnd * dur * 0.4      # étalées du fond vers le devant
        q = clamp((t - ts) / 0.2)
        if q <= 0:
            continue
        x, y = cam.p(*bed_pt(u_, v_))
        wd = int(110 * s * lerp(0.45, 1.0, v_) * cam.z) // 4 * 4
        im = leaf_img(which, max(8, wd), int(rot) // 15 * 15)
        lay.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2 - 30 * (1 - q))))
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon([cam.p(*p) for p in BED], fill=255)
    a = np.asarray(lay.getchannel("A")).astype(np.float32) * np.asarray(m.filter(ImageFilter.GaussianBlur(2))) / 255
    a *= (1 - 0.9 * decomp)
    lay.putalpha(Image.fromarray(a.astype(np.uint8)))
    c.alpha_composite(lay)


def s_garden2(t):
    cam = Cam(1.05, 540, 1000)
    q2 = ease_io(clamp((t - 21.6) / 0.8))            # au printemps : le potager planté
    w = decor(cam, VIDES, PLANTES, q2) if q2 > 0 else decor(cam, VIDES)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    decomp = ease_io(clamp((t - 20.3) / 1.2))
    if q2 < 1:
        mulch(w, cam, t, decomp=decomp)
        if decomp > 0:    # la terre fonce : un terreau riche
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).polygon([cam.p(*p) for p in BED], fill=int(90 * decomp * (1 - q2)))
            dark = Image.new("RGBA", (W, H), (35, 22, 12, 255))
            dark.putalpha(m.filter(ImageFilter.GaussianBlur(4)))
            w.alpha_composite(dark)
    # « ou mets-les au compost » : le composteur arrive, les feuilles s'envolent dedans
    if 18.95 < t < 20.4:
        k = ease_out_back(clamp((t - 19.0) / 0.35), 1.5)
        cx, cy = 900, 1720
        ob(w, COMPOST, lerp(1300, cx, k), cy, 320, anchor="bottom", alpha=life(t, 19.0, 20.3, dur=0.2))
        for i in range(7):
            q = clamp((t - 19.3 - i * 0.08) / 0.45)
            if 0 < q < 1:
                sx, sy = cam.p(*bed_pt(0.6, 0.7))
                ob(w, LEAVES[i % len(LEAVES)], lerp(sx, cx, q), lerp(sy, cy - 560, q) - 260 * math.sin(math.pi * q),
                   120, rot=q * 400 + i * 40)
    if t > 20.35:
        put(u, icon("sun", 190), 900, 600, life(t, 20.4))
    if 17.5 < t < 19.0:
        tag(u, "PAILLAGE", 300, 1330, t, 17.85, 18.95, rot=-5, size=60)
    if 19.2 < t < 20.3:
        tag(u, "COMPOST", 760, 1100, t, 19.25, 20.25, rot=5, size=60)
    if t > 21.8:
        tag(u, "TERREAU GRATUIT", 540, 1300, t, 21.85, None, rot=-4, size=62)
        sparkles(u, t, 21.88, 540, 1150, 420, 14, 3)
    w.alpha_composite(shade())
    title(u, "ÉTALE-LES EN PAILLAGE", t, 17.25, 19.0, y=330, color=YEL, size=112)
    title(u, "OU AU COMPOST !", t, 19.04, 20.1, y=330, color=GREEN, size=140)
    title(u, "AU PRINTEMPS…", t, 20.14, 21.8, y=330, color=YEL, size=150)
    stamp(u, "UN TERREAU GRATUIT !", 540, 340, t, 21.85, None, GREEN, 86, -6)
    return w, u


cue(17.3, "whoosh", 0.1)
cue(17.45, "rustle", 0.2)
cue(19.02, "pop_lo", 0.16)
cue(19.35, "whoosh_up", 0.12)
cue(20.4, "bird", 0.14)
cue(21.9, "success", 0.2)


# ============================================================ F. ABONNE-TOI (22.9 → fin)
def s_end(t):
    cam = Cam(1.0, 540, 1000)
    w = decor(cam, PLANTES)
    light_rays(w, 860, 0, t, 1.0)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    clicked = t > 24.25
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 24.2) / 0.15))
    put(u, btn, 540, 1400, life(t, 23.0) * press)
    if t > 23.65:
        kk = ease_out((t - 23.65) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 25.0, dur=0.45))
    sparkles(u, t, 25.1, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 22.95, 24.95, y=330, color=YEL, size=135)
    return w, u


cue(22.97, "pop_lo", 0.18)
cue(24.23, "click", 0.3)
cue(25.1, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 9.1 - SHIFT, _sh(s_garden)),
    (9.1 - SHIFT, 14.15 - SHIFT, _sh(s_smoke)),
    (14.15 - SHIFT, 17.2 - SHIFT, _sh(s_gold)),
    (17.2 - SHIFT, 22.9 - SHIFT, _sh(s_garden2)),
    (22.9 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
