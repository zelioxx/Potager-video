"""Storyboard « Le poinsettia et le froid du parking » (voix : assets/audio/poinsettia/voix.wav, volume d'origine).

Décors fournis : le parking de la jardinerie (côté magasin, côté panneau), le coffre de la voiture ; le salon
(meuble et lampe) pour la maison. Poinsettia (planche fournie, agrandie ×4, détourée) : en forme, qui fane,
nu (feuilles tombées), emballé dans sa housse transparente.
0–5.5     du magasin à la voiture : le poinsettia traverse le parking glacé… ça peut suffire à le tuer.
5.5–9.4   il vient du Mexique (soleil, 25 °C) et déteste le froid (le bleu gagne, il frissonne).
9.4–12.4  quelques minutes sur le parking glacé : l'horloge tourne, le givre le gagne… CHOC !
12.4–17.5 à la maison : on ne voit rien (loupe)… quelques jours plus tard, il perd toutes ses feuilles.
17.5–21.6 fais-le emballer (housse), et chauffe la voiture avant (coffre, chaleur).
21.6–24.9 à la maison : loin des courants d'air, très peu d'eau.
24.9–fin  le poinsettia en forme dans le salon ; bouton S'abonner et logo.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, put, title, life, fade, ease_out, ease_io, ease_in,
                 ease_out_back, clamp, lerp, icon, tag, button_img, text_img, F_TITLE, light_rays, magnifier_img)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade, swap
from scenes_fumier import Cam, decor, snowfall
from scenes_arrosage_soir import thermo_cold, snow_badge
from scenes_pothos_lumiere import sp, soft_shadow, light as salon_light, LAMP
from scenes_pigeons_choux import day_card

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)
SFX_GAIN = 0.27
DUCK = 0.45
TRANS_GAIN = 0.22
SHIFT = 0.25


def cue(t, name, gain=0.5):
    CUES.append((t - SHIFT, name, gain))


B = "banque/"
MAGASIN, PANNEAU, COFFRE = ("decor_parking_jardinerie_magasin.webp", "decor_parking_jardinerie_panneau.webp",
                            "decor_coffre_voiture.webp")
SALON = "decor_salon_meuble_lampe.jpg"
SAIN, FANE, NU, EMBALLE = B + "poinsettia_sain", B + "poinsettia_fane", B + "poinsettia_nu", B + "poinsettia_emballe"
# bas du pot et milieu du pot dans chaque image (fractions de la boîte) ; hauteur de la boîte relative au
# poinsettia en forme (même échelle sur la planche : les pots restent de la même taille)
POT_BOTTOM = {SAIN: 0.996, FANE: 0.967, NU: 0.995, EMBALLE: 0.995}
POT_X = {SAIN: 0.5, FANE: 0.44, NU: 0.523, EMBALLE: 0.483}
PLANT_H = {SAIN: 1.0, FANE: 982 / 1060, NU: 942 / 1060, EMBALLE: 1109 / 1060}

STORE = (640, 800)              # porte du magasin (parking côté magasin, plein écran)
POT_HOME = (600, 1400)          # bas du pot sur le meuble du salon
TRUNK = (540, 1150)             # bas du pot dans le coffre


def poins(c, name, x, y, h, rot=0.0, alpha=1.0):
    """Poinsettia, bas du pot en (x, y), h = hauteur de la plante en forme (référence commune)."""
    hh = h * PLANT_H[name]
    sp(c, name, x, y, hh, POT_X[name], POT_BOTTOM[name], rot=rot, alpha=alpha)


def stage(c, x, y, h, q, rot=0.0):
    """Évolution sans superposition : 0 = en forme, 1 = qui fane, 2 = nu (on tasse, on change, on rebondit)."""
    if q <= 1:
        k, s = swap(q)
        name = SAIN if k == 0 else FANE
    else:
        k, s = swap(q - 1)
        name = FANE if k == 0 else NU
    soft_shadow(c, x, y, h * 0.5, 100)
    poins(c, name, x, y, h * s, rot)


# ------------------------------------------------------------ ambiances
def cold(im, k):
    """Froid d'hiver : image désaturée, bleutée, un peu plus sombre ; givre sur les bords."""
    if k <= 0.01:
        return im
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    lum = a.mean(2, keepdims=True)
    c = (a * 0.55 + lum * 0.45) * np.array([0.86, 0.95, 1.12], np.float32) * 0.9
    out = a * (1 - k) + c * k
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    edge = np.clip(1 - np.minimum(np.minimum(xx, W - xx), np.minimum(yy, H - yy)) / 170, 0, 1) ** 1.6
    out = out * (1 - edge[..., None] * 0.6 * k) + np.array([0.9, 0.95, 1.0], np.float32) * edge[..., None] * 0.6 * k
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert("RGBA")


def warm(im, k):
    if k <= 0.01:
        return im
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    w_ = np.clip(a * np.array([1.12, 0.98, 0.78], np.float32) * 1.05, 0, 1)
    return Image.fromarray((np.clip(a * (1 - k) + w_ * k, 0, 1) * 255).astype(np.uint8)).convert("RGBA")


def frost_plant(c, x, y, h, a, seed=1):
    """Givre sur les feuilles : petits cristaux blancs dans le feuillage."""
    if a <= 0.01:
        return
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(seed)
    for _ in range(120):
        px, py = x + r.uniform(-0.48, 0.48) * h, y - h * r.uniform(0.35, 0.98)
        s = r.uniform(3, 9)
        al = int(255 * a * r.uniform(0.4, 0.95))
        d.line([(px - s, py), (px + s, py)], fill=(235, 245, 255, al), width=2)
        d.line([(px, py - s), (px, py + s)], fill=(235, 245, 255, al), width=2)


def breath(c, t, x, y, a):
    """Petits souffles de vent glacé (lignes qui filent)."""
    if a <= 0.01:
        return
    d = ImageDraw.Draw(c)
    for i in range(6):
        ph = (t * 1.6 + i * 0.37) % 1
        xx = lerp(x - 520, x + 520, ph)
        yy = y + (i - 3) * 70 + math.sin(t * 3 + i) * 12
        L = 160
        al = int(200 * a * math.sin(math.pi * ph))
        d.arc([xx - L, yy - 26, xx + L, yy + 26], 200, 340, fill=(255, 255, 255, al), width=6)


def clock_img(q, r=95):
    """Petite horloge dont l'aiguille fait le tour (quelques minutes qui passent)."""
    S = 2 * r + 20
    im = Image.new("RGBA", (S * 3, S * 3), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S * 1.5
    R = r * 3
    d.ellipse([c - R - 18, c - R - 18 + 24, c + R + 18, c + R + 18 + 24], fill=(0, 0, 0, 90))
    d.ellipse([c - R - 18, c - R - 18, c + R + 18, c + R + 18], fill=DARK)
    d.ellipse([c - R, c - R, c + R, c + R], fill=CREAM)
    d.pieslice([c - R * 0.86, c - R * 0.86, c + R * 0.86, c + R * 0.86], -90, -90 + 360 * q, fill=(120, 180, 230))
    a = math.radians(-90 + 360 * q)
    d.line([(c, c), (c + math.cos(a) * R * 0.8, c + math.sin(a) * R * 0.8)], fill=DARK, width=18)
    d.ellipse([c - 20, c - 20, c + 20, c + 20], fill=RED)
    return im.resize((S, S), Image.LANCZOS)


# ============================================================ A. DU MAGASIN À LA VOITURE… (0 → 5.5)
def s_carry(t):
    cam = Cam(lerp(1.05, 1.2, ease_io(clamp(t / 5.4))), 560, lerp(1050, 1150, ease_io(clamp(t / 5.4))))
    w = decor(cam, MAGASIN)
    # le poinsettia porté : il sort du magasin et vient vers nous en se balançant au rythme des pas
    q = ease_io(clamp((t - 0.3) / 4.2))
    gx, gy = lerp(STORE[0], 560, q), lerp(STORE[1] + 20, 1830, q)
    hh = lerp(110, 720, q ** 1.3)
    X, Y = cam.p(gx, gy - hh * 0.55)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bob = abs(math.sin(t * 6.5)) * 14 * q
    poins(lay, SAIN, X, Y - bob, hh * cam.z, rot=math.sin(t * 6.5) * 3)
    w.alpha_composite(lay)
    w = cold(w, 0.55 + 0.25 * clamp((t - 3.3) / 1.5))
    snowfall(w, t, 0.8)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    title(u, "TA PLANTE DE NOËL…", t, 0.05, 2.35, y=330, color=WHITE, size=125)
    title(u, "DU MAGASIN À LA VOITURE", t, 2.4, 4.6, y=330, color=YEL, size=100)
    put(u, snow_badge(), 900, 620, life(t, 2.5, 5.4))
    stamp(u, "ÇA PEUT LE TUER !", 540, 340, t, 4.65, None, RED, 120, -6)
    return w, u


cue(0.06, "whoosh", 0.1)
# un petit « plop » à chaque pas (quand le balancement repose le pot : sin(6,5 t) = 0)
for _k in range(2, 10):
    cue(_k * math.pi / 6.5, "plop", 0.17)
cue(2.42, "whoosh_up", 0.1)
cue(4.67, "thud", 0.2)
cue(4.75, "alert1", 0.16)


# ============================================================ B. IL VIENT DU MEXIQUE, IL DÉTESTE LE FROID (5.5 → 9.4)
def s_mexico(t):
    w = decor(Cam(1.0, 540, 960), MAGASIN).filter(ImageFilter.GaussianBlur(14))
    hot = 1 - ease_io(clamp((t - 8.3) / 0.6))
    w = warm(w, hot)
    w = cold(w, 1 - hot)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shiver = (1 - hot) * math.sin(t * 38) * 2.5
    s = ease_out_back(clamp((t - 5.55) / 0.4), 1.4)
    poins(lay, SAIN, 540 + shiver * 3, 1500, 760 * s, rot=shiver)
    frost_plant(lay, 540, 1500, 760, (1 - hot) * 0.6)
    w.alpha_composite(lay)
    if hot > 0.01:
        light_rays(w, 860, 300, t, hot * 0.9)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 7.2:
        a = life(t, 7.25, 8.4)
        put(u, icon("sun", 190), 860, 640, a)
        put(u, text_img("25 °C", F_TITLE, 100, YEL, 8, DARK), 860, 790, a)
        tag(u, "MEXIQUE", 250, 700, t, 7.3, 8.4, rot=-5, size=64)
    if t > 8.35:
        a = life(t, 8.4, None)
        put(u, thermo_cold(190), 860, 650, a)
        put(u, text_img("-2 °C", F_TITLE, 100, BLUE, 8, DARK), 860, 800, a)
    title(u, "LE POINSETTIA…", t, 5.55, 7.2, y=330, color=RED, size=140)
    title(u, "VIENT DU MEXIQUE", t, 7.25, 8.35, y=330, color=YEL, size=120)
    title(u, "IL DÉTESTE LE FROID !", t, 8.37, None, y=330, color=BLUE, size=115)
    return w, u


cue(5.55, "whoosh", 0.12)
cue(7.27, "sparkle", 0.14)
cue(8.38, "whoosh_up", 0.12)
cue(8.45, "crunch", 0.12)


# ============================================================ C. QUELQUES MINUTES SUR UN PARKING GLACÉ : CHOC (9.4 → 12.4)
def s_parking(t):
    cam = Cam(lerp(1.1, 1.25, clamp((t - 9.4) / 3.0)), 520, 1180)
    w = decor(cam, PANNEAU)
    gx, gy = 520, 1500
    X, Y = cam.p(gx, gy)
    hh = 640 * cam.z
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    choc = clamp((t - 11.85) / 0.15)
    shake = math.sin(t * 60) * 10 * choc * (1 - clamp((t - 12.0) / 0.4))
    poins(lay, SAIN, X + shake, Y, hh, rot=math.sin(t * 2.2) * 1.5 + shake * 0.4)
    frost_plant(lay, X, Y, hh * 0.92, ease_io(clamp((t - 10.3) / 1.6)), seed=4)
    w.alpha_composite(lay)
    w = cold(w, 0.9)
    snowfall(w, t, 1.2, n=150)
    breath(w, t, 540, 1000, 0.7)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    a = life(t, 9.45, 11.8)
    if a > 0.01:
        put(u, clock_img(clamp((t - 9.5) / 2.2)), 880, 620, a)
        put(u, text_img("5 MIN", F_TITLE, 80, WHITE, 7, DARK), 880, 760, a)
    title(u, "QUELQUES MINUTES…", t, 9.42, 10.35, y=330, color=WHITE, size=125)
    title(u, "SUR UN PARKING GLACÉ", t, 10.37, 11.82, y=330, color=BLUE, size=105)
    stamp(u, "CHOC !", 540, 340, t, 11.85, None, RED, 190, -8)
    return w, u


cue(9.43, "whoosh", 0.1)
for _i in range(5):
    cue(9.6 + _i * 0.42, "tick", 0.14)
cue(10.4, "crunch", 0.14)
cue(11.86, "thud", 0.24)
cue(11.9, "fail", 0.16)


# ============================================================ D. ON NE VOIT RIEN… PUIS IL PERD SES FEUILLES (12.4 → 17.5)
def falling_leaves(c, t, t0, x, y, h, n=10, seed=3):
    if t < t0:
        return
    r = np.random.default_rng(seed)
    d = ImageDraw.Draw(c)
    for i in range(n):
        st = t0 + r.uniform(0, 1.2)
        q = (t - st) / 1.1
        if not 0 < q < 1:
            continue
        px = x + r.uniform(-0.45, 0.45) * h + math.sin(q * 6 + i) * 25
        py = y - h * r.uniform(0.6, 0.95) + q * h * 0.7
        s = r.uniform(18, 30)
        ang = q * 4 + i
        col = (int(r.uniform(150, 200)), int(r.uniform(20, 40)), int(r.uniform(25, 40)), int(255 * (1 - q ** 3)))
        pts = [(px + math.cos(ang + k * 2.1) * s * (1 if k % 2 else 0.45), py + math.sin(ang + k * 2.1) * s * 0.6)
               for k in range(4)]
        d.polygon(pts, fill=col)


def s_days(t):
    cam = Cam(lerp(1.3, 1.45, clamp((t - 12.4) / 5.0)), POT_HOME[0], POT_HOME[1] - 330)
    w = decor(cam, SALON)
    X, Y = cam.p(*POT_HOME)
    hh = 700 * cam.z
    q = 0.0
    if t > 15.3:
        q = clamp((t - 15.3) / 0.7) + clamp((t - 16.45) / 0.7)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    stage(lay, X, Y, hh, q)
    falling_leaves(lay, t, 15.6, X, Y, hh, 12, 3)
    falling_leaves(lay, t, 16.6, X, Y, hh, 12, 8)
    w.alpha_composite(lay)
    w = salon_light(w, cam, 0.55)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if 13.5 < t < 15.0:   # on regarde de près : tout a l'air normal
        put(u, icon("check", 150), 860, 700, ease_out_back(clamp((t - 13.6) / 0.3), 1.6) * life(t, 13.6, 14.95))
        tag(u, "TOUT A L'AIR NORMAL", 400, 1240, t, 13.65, 14.95, rot=-5, size=56)
    # les jours passent
    for n_ in range(1, 6):
        t0 = 15.05 + (n_ - 1) * 0.3
        s = life(t, t0, (17.5 if n_ == 5 else t0 + 0.3), dur=0.12, out=0.08)
        if s > 0.01:
            put(u, day_card(n_, 240), 880, 640, s, rot=-4 + n_ * 2)
    title(u, "LE PIRE…", t, 12.42, 13.5, y=330, color=WHITE, size=160)
    title(u, "TU NE VOIS RIEN !", t, 13.52, 15.0, y=330, color=YEL, size=130)
    title(u, "QUELQUES JOURS PLUS TARD…", t, 15.02, 16.4, y=330, color=WHITE, size=92)
    stamp(u, "IL PERD TOUTES SES FEUILLES !", 540, 340, t, 16.45, None, RED, 78, -5)
    return w, u


cue(12.43, "whoosh", 0.12)
cue(13.55, "whoosh_up", 0.1)
for _n in range(5):
    cue(15.05 + _n * 0.3, "tick", 0.18)
cue(15.6, "rustle", 0.16)
cue(16.47, "fail", 0.16)
cue(16.6, "rustle", 0.14)


# ============================================================ E. EMBALLÉ, ET LA VOITURE CHAUFFÉE (17.5 → 21.6)
def s_wrap(t):
    car = t > 19.95
    if not car:
        w = decor(Cam(1.0, 540, 960), MAGASIN).filter(ImageFilter.GaussianBlur(14))
        w = cold(w, 0.6)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        k, s_ = swap(clamp((t - 17.95) / 0.7))
        soft_shadow(lay, 540, 1500, 380, 110)
        poins(lay, SAIN if k == 0 else EMBALLE, 540, 1500, 760 * s_)
        w.alpha_composite(lay)
        u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        w.alpha_composite(shade())
        if t > 18.7:
            put(u, icon("check", 160), 860, 760, ease_out_back(clamp((t - 18.7) / 0.3), 1.6))
            tag(u, "BIEN EMBALLÉ", 300, 1240, t, 18.75, None, rot=-5, size=60)
        title(u, "FAIS-LE EMBALLER !", t, 17.52, None, y=330, color=YEL, size=125)
        return w, u
    cam = Cam(lerp(1.05, 1.15, clamp((t - 20.0) / 1.6)), 540, 1050)
    w = decor(cam, COFFRE)
    X, Y = cam.p(*TRUNK)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    drop = ease_out(clamp((t - 20.05) / 0.4))
    soft_shadow(lay, X, Y, 230 * cam.z, int(120 * drop))
    poins(lay, EMBALLE, X, lerp(Y - 600, Y, drop), 450 * cam.z)
    w.alpha_composite(lay)
    heat = ease_io(clamp((t - 20.3) / 0.8))
    w = warm(w, heat * 0.8)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if heat > 0.01:     # l'air chaud qui ondule dans le coffre
        d = ImageDraw.Draw(u)
        for i in range(5):
            x0 = 300 + i * 120
            pts = [(x0 + math.sin(yy / 40 + t * 6 + i) * 14, yy) for yy in range(int(Y - 640), int(Y - 260), 8)]
            d.line(pts, fill=(255, 190, 120, int(130 * heat)), width=6)
    w.alpha_composite(shade())
    put(u, icon("thermo", 170), 880, 640, life(t, 20.2, None))
    put(u, text_img("20 °C", F_TITLE, 90, YEL, 8, DARK), 880, 790, life(t, 20.25, None))
    title(u, "CHAUFFE TA VOITURE", t, 19.97, None, y=300, color=YEL, size=115)
    title(u, "AVANT !", t, 19.97, None, y=440, color=RED, size=140)
    return w, u


cue(17.53, "whoosh", 0.12)
cue(18.3, "pop", 0.16)
cue(18.72, "ding", 0.16)
cue(19.98, "whoosh", 0.12)
cue(20.4, "thud", 0.14)
cue(20.6, "rise", 0.14)


# ============================================================ F. À LA MAISON : PAS DE COURANT D'AIR, PEU D'EAU (21.6 → 24.9)
def s_home(t):
    cam = Cam(lerp(1.15, 1.3, clamp((t - 21.6) / 3.3)), POT_HOME[0], POT_HOME[1] - 330)
    w = decor(cam, SALON)
    X, Y = cam.p(*POT_HOME)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    soft_shadow(lay, X, Y, 700 * cam.z * 0.5, 100)
    poins(lay, SAIN, X, Y, 700 * cam.z, rot=math.sin(t * 1.4) * 0.8)
    w.alpha_composite(lay)
    w = salon_light(w, cam, 0.45)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = life(t, 22.7, 23.95)
    if a > 0.01:
        breath(u, t, 540, 800, a)
        put(u, icon("nosign", 260), 540, 800, ease_out_back(clamp((t - 22.95) / 0.3), 1.6) * a)
    if t > 24.2:
        put(u, icon("drop", 110), 300, 760, life(t, 24.25, None))
        tag(u, "TRÈS PEU D'EAU", 330, 900, t, 24.3, None, rot=-5, size=56)
    w.alpha_composite(shade())
    title(u, "À LA MAISON…", t, 21.62, 22.7, y=330, color=WHITE, size=150)
    title(u, "PAS DE COURANTS D'AIR", t, 22.72, 24.2, y=330, color=YEL, size=100)
    title(u, "ET TRÈS PEU D'EAU", t, 24.22, None, y=330, color=BLUE, size=120)
    return w, u


cue(21.63, "whoosh", 0.12)
cue(22.75, "whoosh_up", 0.1)
cue(22.97, "alert2", 0.14)
cue(24.27, "plop", 0.16)


# ============================================================ G. ABONNE-TOI (24.9 → fin)
def s_end(t):
    cam = Cam(1.15, POT_HOME[0], POT_HOME[1] - 330)
    w = decor(cam, SALON)
    X, Y = cam.p(*POT_HOME)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    soft_shadow(lay, X, Y, 700 * cam.z * 0.5, 100)
    poins(lay, SAIN, X, Y, 700 * cam.z, rot=math.sin(t * 1.4) * 0.8)
    w.alpha_composite(lay)
    w = salon_light(w, cam, 0.5)
    snowfall(w, t, 0.4)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    clicked = t > 26.5
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 26.45) / 0.15))
    put(u, btn, 540, 1400, life(t, 25.1) * press)
    if t > 25.95:
        kk = ease_out((t - 25.95) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 27.4, dur=0.45))
    sparkles(u, t, 27.5, 540, 330, 200, 10, 12)
    sparkles(u, t, 25.2, X, Y - 700 * cam.z * 0.6, 300, 10, 5, 1.2)
    title(u, "PLUS D'ASTUCES ?", t, 24.95, 27.35, y=330, color=YEL, size=135)
    return w, u


cue(24.97, "pop_lo", 0.18)
cue(25.25, "sparkle", 0.12)
cue(26.48, "click", 0.3)
cue(27.5, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 5.5 - SHIFT, _sh(s_carry)),
    (5.5 - SHIFT, 9.4 - SHIFT, _sh(s_mexico)),
    (9.4 - SHIFT, 12.4 - SHIFT, _sh(s_parking)),
    (12.4 - SHIFT, 17.5 - SHIFT, _sh(s_days)),
    (17.5 - SHIFT, 19.95 - SHIFT, _sh(s_wrap)),
    (19.95 - SHIFT, 21.6 - SHIFT, _sh(s_wrap)),
    (21.6 - SHIFT, 24.9 - SHIFT, _sh(s_home)),
    (24.9 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
