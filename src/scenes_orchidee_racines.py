"""Storyboard « Les racines grises de l'orchidée » (voix : assets/audio/orchidee_racines/voix.wav, volume d'origine).

Décors fournis : le salon (meuble en chêne, lampe allumée), l'évier de la cuisine (mitigeur).
Objets : orchidée rose à deux tiges, racines aériennes grise / verte / noire, ciseaux ouverts / fermés (photos
fournies, agrandies ×4 puis détourées).
0–3.25    le salon : l'orchidée sur le meuble, une racine grise qui dépasse du pot ; les ciseaux arrivent… ARRÊTE !
3.25–5.4  elles ne sont pas mortes, elles ont soif.
5.4–9.2   grise ou argentée = simplement sèche (la racine en gros plan sur le meuble).
9.2–11.95 sous le robinet : dès qu'on arrose, elle redevient verte.
11.95–16.0 le test : on la pince doucement ; ferme → on la garde.
16.0–20.6 molle, creuse ou noire → là oui, on la coupe avec des ciseaux propres.
20.6–fin  l'orchidée sur le meuble ; bouton S'abonner et logo.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, put, title, life, fade, ease_out, ease_io,
                 ease_in, ease_out_back, clamp, lerp, icon, tag, button_img, particles)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade, shadow, swap
from scenes_fumier import Cam, decor
from scenes_gland import hand_at

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
SALON, EVIER = "decor_salon_meuble_lampe.jpg", "decor_evier_cuisine_soir.jpg"
ORCH = B + "orchidee_rose"
R_GRISE, R_VERTE, R_NOIRE = B + "racine_orchidee_grise", B + "racine_orchidee_verte", B + "racine_orchidee_noire"
CIS_O, CIS_F = B + "ciseaux_ouverts", B + "ciseaux_fermes"
# repères en fractions du cadre de chaque photo (le cadre complet du recadrage, pas la boîte englobante)
O_BOT = (0.49, 0.95)                           # bas du pot
O_RIM_L = (0.36, 0.665)                           # bord gauche du pot : la racine en sort
O_H = 980                                        # hauteur de la photo de l'orchidée à l'écran (zoom 1)
ORCH_AT = (610, 1380)                            # bas du pot, sur le meuble (photo plein écran)
CIS_CUT_O = (0.717, 0.50)                        # entre les lames, ciseaux ouverts (lames vers la droite)
CIS_CUT_F = (0.33, 0.48)                         # au même endroit, ciseaux fermés
ROOT_L = 300                                     # longueur de la racine qui dépasse (zoom 1)
ROOT_SX = 0.62                                   # les racines de la planche sont trapues : on les affine
ROOT_ROT = -38                                   # elle pend vers la gauche, par-dessus le bord du pot


@lru_cache(None)
def _img(name):
    return Image.open(os.path.join(IMG, name + ".png")).convert("RGBA")


def paste_frac(c, name, fx, fy, X, Y, height=None, width=None, rot=0.0, flip=False, alpha=1.0, sx=1.0):
    """Pose la photo de sorte que le point (fx, fy) de son cadre tombe en (X, Y), tournée autour de ce point."""
    im = _img(name)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        fx = 1 - fx
    k = (height / im.height) if height else (width / im.width)
    if k * im.width < 2:
        return
    im = im.resize((max(1, int(im.width * k * sx)), max(1, int(im.height * k))),
                   Image.LANCZOS if k < 0.8 else Image.BICUBIC)
    ax, ay = fx * im.width, fy * im.height
    if rot:
        S = int(2 * math.hypot(max(ax, im.width - ax), max(ay, im.height - ay))) + 4
        can = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        can.alpha_composite(im, (int(S / 2 - ax), int(S / 2 - ay)))
        im = can.rotate(rot, resample=Image.BICUBIC, center=(S / 2, S / 2))
        ax = ay = S / 2
    if alpha < 1:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    c.alpha_composite(im, (int(round(X - ax)), int(round(Y - ay))))


@lru_cache(None)
def root_geom(name):
    """Haut (là où elle sort de la plante) et bout de la racine, en fractions du cadre."""
    a = np.asarray(_img(name))[..., 3] > 128
    ys = np.nonzero(a.any(1))[0]
    y0, y1 = ys.min(), ys.max()
    x0 = np.nonzero(a[y0 + 6])[0].mean()
    x1 = np.nonzero(a[y1 - 6])[0].mean()
    h, w = a.shape
    return (x0 / w, (y0 + 4) / h), (x1 / w, y1 / h), (y1 - y0) / h


def draw_root(c, name, X, Y, length, rot, cut=None, fall=0.0, squeeze=0.0):
    """Racine dont le haut est en (X, Y), de longueur `length`, penchée de `rot`°. `cut` : fraction de la longueur
    où on la coupe ; `fall` (0 → 1) : le bout coupé tombe."""
    (tx, ty), _, frac = root_geom(name)
    im = _img(name)
    hgt = length / frac
    if squeeze > 0.01:          # pincée : elle s'écrase un peu (ferme : à peine)
        hgt *= 1 - 0.02 * squeeze
    if cut is None:
        paste_frac(c, name, tx, ty, X, Y, height=hgt, rot=rot, sx=ROOT_SX)
        return
    # deux morceaux : le haut reste, le bas tombe
    cy = ty + frac * cut
    for part in (0, 1):
        a = np.asarray(im).copy()
        yy = np.arange(a.shape[0])[:, None] / a.shape[0]
        a[..., 3] = np.where((yy < cy) if part == 0 else (yy >= cy), a[..., 3], 0).astype(np.uint8)
        key = f"{name}#{part}#{cut:.2f}"
        _PARTS[key] = Image.fromarray(a, "RGBA")
        if part == 0:
            _paste_img(c, _PARTS[key], tx, ty, X, Y, hgt, rot)
        else:
            a_r = math.radians(rot)
            dxp, dyp = hgt * (cy - ty) * math.sin(a_r), hgt * (cy - ty) * math.cos(a_r)
            px, py = X + dxp, Y + dyp
            _paste_img(c, _PARTS[key], tx, cy, px - 40 * fall, py + 900 * fall * fall, hgt, rot + 70 * fall,
                       alpha=1 - 0.3 * fall)


_PARTS = {}


def _paste_img(c, im, fx, fy, X, Y, hgt, rot, alpha=1.0):
    k = hgt / im.height
    im = im.resize((max(1, int(im.width * k * ROOT_SX)), max(1, int(im.height * k))), Image.LANCZOS)
    ax, ay = fx * im.width, fy * im.height
    S = int(2 * math.hypot(max(ax, im.width - ax), max(ay, im.height - ay))) + 4
    can = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    can.alpha_composite(im, (int(S / 2 - ax), int(S / 2 - ay)))
    can = can.rotate(rot, resample=Image.BICUBIC, center=(S / 2, S / 2))
    if alpha < 1:
        can.putalpha(can.getchannel("A").point(lambda v: int(v * alpha)))
    c.alpha_composite(can, (int(round(X - S / 2)), int(round(Y - S / 2))))


def orchid(c, cam, root=R_GRISE, root_cut=None, fall=0.0, squeeze=0.0, show_root=True):
    """L'orchidée sur le meuble ; la racine aérienne part de l'arrière du pot (dessinée derrière lui) et pend
    par-dessus le bord, sur le côté : elle fait partie de la plante."""
    x, y = cam.p(*ORCH_AT)
    h = O_H * cam.z
    shadow(c, x, y - 4, 300 * cam.z, 95)
    if show_root:
        rx, ry = root_attach(cam)
        draw_root(c, root, rx, ry, ROOT_L * cam.z, ROOT_ROT, root_cut, fall, squeeze)
    paste_frac(c, ORCH, *O_BOT, x, y, height=h)


def root_attach(cam):
    x, y = cam.p(*ORCH_AT)
    h = O_H * cam.z
    im = _img(ORCH)
    wpx = im.width * h / im.height
    return x + (O_RIM_L[0] - O_BOT[0]) * wpx, y + (O_RIM_L[1] - O_BOT[1]) * h


def root_pt(cam, f):
    rx, ry = root_attach(cam)
    L = ROOT_L * cam.z * f
    a = math.radians(ROOT_ROT)
    return rx + L * math.sin(a), ry + L * math.cos(a)


def scissors(c, X, Y, w, closed=False, rot=0.0, alpha=1.0):
    """Ciseaux arrivant de la droite (lames vers la gauche) ; (X, Y) = point de coupe entre les lames."""
    # photo ouverts : lames vers la droite (on la retourne) ; photo fermés : lames déjà vers la gauche
    name, fr, fl = (CIS_F, CIS_CUT_F, False) if closed else (CIS_O, CIS_CUT_O, True)
    paste_frac(c, name, *fr, X, Y, width=w * (1.04 if closed else 1.0), rot=rot, flip=fl, alpha=alpha)


CAM_WIDE = (1.05, 540, 1060)


def cam_on_root(z, f=0.5, dy=0):
    x, y = (ORCH_AT[0] - 150, ORCH_AT[1] - 220 + dy)
    return (z, x, y)


# ============================================================ A. LE SALON : LES CISEAUX… ARRÊTE ! (0 → 3.25)
def s_intro(t):
    k = ease_io(clamp((t - 1.3) / 1.0))
    cam = Cam(*[lerp(a, b, k) for a, b in zip(CAM_WIDE, cam_on_root(1.8))])
    w = decor(cam, SALON)
    orchid(w, cam)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # les ciseaux arrivent de la droite et « mordent » dans le vide, puis se figent et repartent sur « Arrête ! »
    if 0.9 < t < 3.6:
        tx, ty = root_pt(cam, 0.5)
        cin = ease_out(clamp((t - 0.9) / 0.6))
        out = ease_in(clamp((t - 2.85) / 0.4))
        sx = lerp(W + 400, tx + 30 * cam.z, cin) + out * 900
        sy = ty + 10 * math.sin(t * 3)
        snip = 1.6 < t < 2.6 and int((t - 1.6) / 0.25) % 2 == 1
        shake = math.sin(t * 60) * 8 if 2.6 < t < 2.85 else 0
        scissors(w, sx + shake, sy, 400 * cam.z, closed=snip, rot=-10)
    w.alpha_composite(shade())
    title(u, "TU COUPES LES RACINES", t, 0.05, 1.3, y=330, color=WHITE, size=110)
    title(u, "GRISES DE TON ORCHIDÉE ?", t, 1.35, 2.6, y=330, color=YEL, size=108)
    stamp(u, "ARRÊTE !", 540, 340, t, 2.62, None, RED, 165, -7)
    return w, u


cue(0.95, "whoosh", 0.12)
for _i in range(4):
    cue(1.85 + _i * 0.5, "chop", 0.08)
cue(2.64, "alert1", 0.22)
cue(2.9, "whoosh_up", 0.12)


# ============================================================ B. PAS MORTES : ELLES ONT SOIF (3.25 → 5.4)
def s_soif(t):
    cam = Cam(*cam_on_root(lerp(1.8, 2.0, clamp((t - 3.25) / 2.1))))
    w = decor(cam, SALON)
    orchid(w, cam)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    px, py = root_pt(cam, 0.75)
    if t > 3.5:
        put(u, icon("check", 140), px - 30, py - 260, life(t, 3.55, 5.35))
    if t > 4.5:
        put(u, icon("drop", 170), 850, 760, life(t, 4.55, 5.35) * (1 + 0.06 * math.sin(t * 8)))
    title(u, "ELLES NE SONT PAS MORTES…", t, 3.3, 4.45, y=330, color=WHITE, size=100)
    title(u, "ELLES ONT SOIF !", t, 4.5, None, y=330, color=BLUE, size=150)
    return w, u


cue(3.3, "pop", 0.12)
cue(4.55, "plop", 0.18)


# ============================================================ C. GRISE OU ARGENTÉE = SÈCHE (5.4 → 9.2)
def s_seche(t):
    cam = Cam(lerp(1.5, 1.6, clamp((t - 5.4) / 3.8)), 520, 1420)
    w = decor(cam, SALON)
    x, y = cam.p(520, 1500)
    s_in = ease_out_back(clamp((t - 5.45) / 0.4), 1.4)
    shadow(w, x, y + 20, 620 * cam.z * s_in, 70)
    if s_in > 0.01:   # la racine posée en travers du meuble, en gros plan
        paste_frac(w, R_GRISE, 0.5, 0.5, x, y - 120, height=900 * cam.z * s_in * 0.55, rot=72)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 6.2:
        tag(u, "GRISE", 300, 760, t, 6.25, None, rot=-6, size=60)
    if t > 6.85:
        tag(u, "ARGENTÉE", 760, 800, t, 6.9, None, rot=5, size=56)
        sparkles(u, t, 6.9, 540, 1180, 320, 10, 3)
    title(u, "UNE RACINE GRISE…", t, 5.45, 7.4, y=330, color=WHITE, size=140)
    stamp(u, "= RACINE SÈCHE !", 540, 340, t, 8.4, None, YEL, 120, -6)
    if 7.45 < t < 8.4:
        title(u, "C'EST SIMPLEMENT…", t, 7.45, 8.35, y=330, color=WHITE, size=140)
    return w, u


cue(5.47, "whoosh", 0.1)
cue(6.27, "pop", 0.12)
cue(6.92, "sparkle", 0.14)
cue(8.42, "alert2", 0.16)


# ============================================================ D. SOUS LE ROBINET : ELLE REDEVIENT VERTE (9.2 → 11.95)
SPOUT = (510, 772)                               # bout du mitigeur (photo de l'évier, plein écran)


def water(c, x, y0, y1, t, a=1.0, w=26):
    """Filet d'eau du robinet : translucide, reflets qui filent, petites ondulations."""
    if a <= 0.01 or y1 <= y0:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = [(x + 2.5 * math.sin(yy * 0.045 + t * 22) * (yy - y0) / 300, yy) for yy in range(int(y0), int(y1) + 8, 8)]
    if len(pts) > 1:
        d.line(pts, fill=(205, 225, 240, int(120 * a)), width=w, joint="curve")
        d.line([(px - w * 0.22, py) for px, py in pts], fill=(250, 253, 255, int(200 * a)), width=max(2, w // 6))
        for j in range(3):
            ph = (t * 3.5 + j / 3) % 1.0
            i0 = int(ph * (len(pts) - 4))
            d.line(pts[i0:i0 + 4], fill=(255, 255, 255, int(220 * a)), width=max(2, w // 4))
    c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.2)))


def s_robinet(t):
    cam = Cam(lerp(1.2, 1.35, clamp((t - 9.2) / 2.75)), 560, 980)
    w = decor(cam, EVIER)
    sx, sy = cam.p(*SPOUT)
    # la racine tenue sous le filet d'eau
    rx, ry = sx + 15, sy + 180 * cam.z
    flow = fade(t, 9.35, None, 0.2)
    which, sc = swap((t - 10.55) / 0.35)
    name = R_GRISE if which == 0 else R_VERTE
    water(w, sx, sy, ry + 40, t, flow, int(22 * cam.z))
    paste_frac(w, name, 0.5, 0.06, rx, ry, height=520 * cam.z * sc, rot=-8)
    water(w, sx, ry + 40, cam.p(0, 1330)[1], t, flow * 0.9, int(22 * cam.z))      # l'eau continue sous la racine
    if flow > 0.1:
        particles(w, t, t - (t % 0.2), rx, ry + 60, 6, int(t * 10) % 7, col=(225, 238, 250), size=4, up=120,
                  spread=180, dur=0.2)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 10.6:
        sparkles(u, t, 10.62, rx, ry + 200, 280, 12, 4)
        put(u, icon("check", 150), 860, 760, life(t, 10.65))
    title(u, "DÈS QUE TU ARROSES…", t, 9.25, 10.5, y=330, color=WHITE, size=130)
    title(u, "ELLE REDEVIENT VERTE !", t, 10.55, None, y=330, color=GREEN, size=118)
    return w, u


cue(9.27, "whoosh", 0.1)
cue(9.35, "pour", 0.25)
cue(10.57, "success", 0.2)


# ============================================================ E. LE TEST : PINCE-LA… FERME, GARDE-LA (11.95 → 16.0)
def s_test(t):
    cam = Cam(*cam_on_root(2.0, dy=40))
    w = decor(cam, SALON)
    pinch = fade(t, 13.4, 14.5, 0.15, 0.25)
    orchid(w, cam, root=R_VERTE, squeeze=pinch)
    px, py = root_pt(cam, 0.6)
    if t > 12.9:
        q = ease_out(clamp((t - 12.9) / 0.45))
        out = ease_in(clamp((t - 14.6) / 0.4))
        hand_at(w, lerp(px - 700, px, q) - 700 * out, lerp(py - 700, py, q) - 600 * out, 520 * cam.z * 0.68)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 14.6:
        tag(u, "FERME", 300, 760, t, 14.65, None, rot=-5, size=62)
        put(u, icon("check", 160), 850, 760, life(t, 14.95))
    title(u, "FAIS LE TEST !", t, 12.0, 13.1, y=330, color=YEL, size=160)
    title(u, "PINCE-LA DOUCEMENT", t, 13.15, 14.6, y=330, color=WHITE, size=118)
    stamp(u, "FERME ? GARDE-LA !", 540, 340, t, 14.65, None, GREEN, 110, -6)
    return w, u


cue(12.02, "pop", 0.14)
cue(13.2, "whoosh", 0.1)
cue(13.42, "squish", 0.12)
cue(14.97, "ding", 0.18)


# ============================================================ F. MOLLE, CREUSE OU NOIRE : COUPE-LA (16.0 → 20.6)
CUT_T = 19.15


def s_coupe(t):
    cam = Cam(*cam_on_root(lerp(2.0, 2.15, clamp((t - 16.0) / 4.6)), dy=40))
    w = decor(cam, SALON)
    which, sc = swap((t - 16.4) / 0.3)
    root = R_VERTE if which == 0 else R_NOIRE
    cut, fall = (None, 0.0) if t < CUT_T else (0.42, ease_in(clamp((t - CUT_T) / 0.7)))
    orchid(w, cam, root=root, root_cut=cut, fall=fall)
    cx, cy = root_pt(cam, 0.42)
    if 18.35 < t < 20.4:   # les ciseaux propres arrivent, s'ouvrent… et coupent
        cin = ease_out(clamp((t - 18.4) / 0.45))
        out = ease_in(clamp((t - 19.75) / 0.45))
        sx = lerp(W + 400, cx, cin) + 900 * out
        scissors(w, sx, cy, 370 * cam.z, closed=t >= CUT_T, rot=-12)
        if 18.9 < t < 19.6:
            sparkles(w, t, 18.92, sx + 160, cy, 160, 8, 7, dur=0.6)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    for i, (lbl, tt) in enumerate((("MOLLE", 16.75), ("CREUSE", 17.1), ("NOIRE", 17.9))):
        if tt < t < 18.45:
            tag(u, lbl, 790, 640 + i * 130, t, tt, 18.4, rot=(-1) ** i * 5, size=58)
    if t > 19.75:
        tag(u, "CISEAUX PROPRES", 540, 760, t, 19.8, None, rot=-4, size=56)
    title(u, "MAIS SI ELLE EST…", t, 16.05, 18.4, y=330, color=WHITE, size=140)
    title(u, "LÀ OUI…", t, 18.45, 19.1, y=330, color=YEL, size=180)
    stamp(u, "COUPE-LA !", 540, 340, t, 19.15, None, RED, 150, -7)
    return w, u


cue(16.07, "whoosh", 0.1)
cue(16.42, "fail", 0.14)
cue(16.77, "pop", 0.1)
cue(17.12, "pop", 0.1)
cue(17.92, "pop", 0.1)
cue(18.45, "whoosh", 0.1)
cue(CUT_T, "chop", 0.3)
cue(CUT_T + 0.55, "thud", 0.1)


# ============================================================ G. ABONNE-TOI (20.6 → fin)
def s_end(t):
    cam = Cam(*[lerp(a, b, ease_io(clamp((t - 20.6) / 0.9))) for a, b in zip(cam_on_root(2.15, dy=40), CAM_WIDE)])
    w = decor(cam, SALON)
    orchid(w, cam, root=R_NOIRE, root_cut=0.42, fall=1.0)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    sparkles(u, t, 20.7, 600, 800, 330, 10, 7)
    clicked = t > 22.0
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 21.95) / 0.15))
    put(u, btn, 540, 1420, life(t, 20.75) * press)
    if t > 21.4:
        kk = ease_out((t - 21.4) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1670, 1460, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 23.0, dur=0.45))
    sparkles(u, t, 23.1, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 20.65, 22.95, y=330, color=YEL, size=135)
    return w, u


cue(20.67, "pop_lo", 0.16)
cue(21.98, "click", 0.3)
cue(23.1, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 3.25 - SHIFT, _sh(s_intro)),
    (3.25 - SHIFT, 5.4 - SHIFT, _sh(s_soif)),
    (5.4 - SHIFT, 9.2 - SHIFT, _sh(s_seche)),
    (9.2 - SHIFT, 11.95 - SHIFT, _sh(s_robinet)),
    (11.95 - SHIFT, 16.0 - SHIFT, _sh(s_test)),
    (16.0 - SHIFT, 20.6 - SHIFT, _sh(s_coupe)),
    (20.6 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
