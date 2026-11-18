"""Storyboard « Les pigeons qui dévorent les choux en hiver » (voix : assets/audio/pigeons_choux/voix.wav).

Décor fourni : le potager en carrés sous la neige (même cadrage que les carrés vides / plantés).
Objets fournis (planches détourées) : choux rongés, poireaux, arceaux et filet anti-oiseaux, épouvantails, CD.
Pigeons : vraies photos (Open Images, CC BY 2.0) détourées — bisets qui marchent, ramier, pigeons en vol.
0–2.3     le potager en hiver : des choux plantés dans le grand carré, des poireaux dans les carrés du fond.
2.3–4.85  ce ne sont pas les chenilles (barrée)… ce sont les pigeons ! (ils arrivent en vol et roucoulent).
4.85–7.75 en hiver, les chenilles ont disparu depuis longtemps.
7.75–9.8  mais les pigeons, eux, ont faim (ils se promènent entre les choux).
9.8–12.95 ils picorent jusqu'à ne laisser que les nervures (le chou se fait dévorer).
12.95–16.8 la solution : les arceaux se plantent, le filet se déroule par-dessus ; un pigeon reste dehors.
16.8–20.95 attention : le filet ne doit pas toucher les feuilles, sinon ils picorent à travers.
20.95–25.15 oublie les CD et les épouvantails : au bout de quelques jours, ils n'ont plus peur (ils se perchent
          sur l'épouvantail et lui picorent le chapeau).
25.15–fin le carré protégé par son filet, bouton S'abonner et logo.
"""
import math
import os
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, IMG, put, paste, title, life, ease_out, ease_io, ease_in,
                 ease_out_back, clamp, lerp, icon, tag, button_img, text_img, aa, F_TITLE, F_BLACK)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade
from scenes_fumier import Cam, decor, snowfall
from scenes_arrosage_soir import snow_badge

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
POTAGER = "decor_potager_bacs_neige.png"
CHOU, CHOU_N = B + "chou_ronge", B + "chou_nervures"
SAINS = [B + "chou_sain_a", B + "chou_sain_b", B + "chou_sain_c", B + "chou_sain_d"]
POIREAUX = [B + "poireau_motte_a", B + "poireau_motte_b", B + "poireau_motte_c"]
PIG, PIG_PK = B + "pigeon_debout", B + "pigeon_picore"          # debout (regarde à droite), picore (à gauche)
MARCHE = BIZET = RAMIER = PIG
VOL_UP, VOL_DOWN = [B + "pigeon_vol_haut"], [B + "pigeon_vol_bas"]
EPOUV, CD, CD2 = B + "epouvantail", B + "cd_face", B + "cd_biais"
ARCEAUX, CHENILLE = B + "arceaux_biais", B + "chenille"
NET_SRC = "planche_arceaux_filet_face.webp"
COLD = np.array([0.9, 0.96, 1.07], np.float32)

# ------------------------------------------------------------ le grand carré du premier plan (plein écran)
BED_Q = [(92, 1612), (1012, 1612), (778, 848), (392, 848)]          # devant-g, devant-d, fond-d, fond-g
_HM = cv2.getPerspectiveTransform(np.float32([(0, 0), (1, 0), (1, 1), (0, 1)]), np.float32(BED_Q))


def bedp(u, v):
    """(u : gauche → droite, v : devant → fond) ∈ [0, 1]² → point du grand carré (photo plein écran)."""
    p = _HM @ np.array([u, v, 1.0])
    return float(p[0] / p[2]), float(p[1] / p[2])


def bedw(v):
    """Largeur du carré (en px, plein écran) à la profondeur v : l'échelle locale."""
    return bedp(1, v)[0] - bedp(0, v)[0]


VF = 0.62                       # les hauteurs paraissent écrasées (on regarde le carré d'en haut)


def up(u, v, h):
    """Point à la hauteur h (en largeurs de carré) au-dessus du sol (u, v)."""
    x, y = bedp(u, v)
    return x, y - h * bedw(v) * VF


# choux plantés : (u, v, image, miroir) — du fond vers l'avant
CABBAGES = [(0.27, 0.80, CHOU, False), (0.73, 0.78, CHOU, True),
            (0.29, 0.47, CHOU, True), (0.71, 0.49, CHOU, False),
            (0.27, 0.15, CHOU, False), (0.73, 0.16, CHOU, True)]
C_W = 0.40                      # largeur d'un chou (motte comprise) en largeurs de carré
HERO = 4                        # le chou de devant à gauche : celui qu'on regarde de près

# poireaux : rangées dans les carrés du fond et sur les côtés (x, y au sol, hauteur) — photo plein écran
LEEKS = ([(560 + i * 34, 742, 74) for i in range(6)] + [(548 + i * 36, 778, 84) for i in range(6)] +
         [(190 + i * 40, 742, 74) for i in range(6)] + [(172 + i * 42, 778, 84) for i in range(6)] +
         [(850 + i * 40, 745, 76) for i in range(5)] + [(872 + i * 42, 782, 86) for i in range(5)] +
         [(40 + i * 62, 900 - i * 0, 120) for i in range(4)] + [(30 + i * 55, 1010, 140) for i in range(3)] +
         [(990 + i * 50, 930, 128) for i in range(2)] + [(1010 + i * 50, 1060, 146) for i in range(2)])


# ------------------------------------------------------------ sprites (cache par taille)
@lru_cache(None)
def _src(name):
    im = Image.open(os.path.join(IMG, name + ".png")).convert("RGBA")
    return im.crop(im.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox())


def _cold(im, k=1.0):
    a = np.asarray(im).astype(np.float32)
    rgb = a[..., :3]
    lum = rgb.mean(2, keepdims=True)
    rgb = rgb * (1 - 0.15 * k) + lum * 0.15 * k
    a[..., :3] = np.clip(rgb * (1 + k * (COLD - 1)), 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


@lru_cache(2048)
def _sized(name, w, flip, cold):
    im = _src(name)
    h = max(1, round(im.height * w / im.width))
    im = im.resize((max(1, w), h), Image.LANCZOS)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return _cold(im, cold / 10) if cold else im


def sp(c, name, x, y, w, ax=0.5, ay=1.0, rot=0.0, flip=False, alpha=1.0, cold=8, sy=1.0):
    """Colle l'objet de largeur w avec son point d'ancrage (ax, ay ∈ [0, 1] dans sa boîte) en (x, y) ;
    rotation (degrés, sens trigo) autour de ce point. sy : tassement vertical (atterrissage)."""
    if w < 2 or alpha <= 0.01:
        return
    im = _sized(name, int(round(w)), flip, cold)
    if abs(sy - 1) > 0.005:
        im = im.resize((im.width, max(1, int(im.height * sy))), Image.LANCZOS)
    axp = (1 - ax if flip else ax) * im.width
    ayp = ay * im.height
    if abs(rot) > 0.05:
        r = int(math.ceil(max(math.hypot(axp, ayp), math.hypot(im.width - axp, ayp),
                              math.hypot(axp, im.height - ayp), math.hypot(im.width - axp, im.height - ayp)))) + 2
        big = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0))
        big.paste(im, (int(r - axp), int(r - ayp)))
        im = big.rotate(rot, resample=Image.BICUBIC)
        axp = ayp = r
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    paste(c, im, x - axp, y - ayp)


def ground_shadow(c, x, y, w, a=70, flat=0.16):
    if w < 3:
        return
    pad = int(w * 0.3) + 8
    im = Image.new("RGBA", (int(w + 2 * pad), int(w * flat * 2 + 2 * pad)), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([pad, pad, pad + w, pad + w * flat * 2], fill=(25, 22, 30, a))
    im = im.filter(ImageFilter.GaussianBlur(max(2, w * 0.06)))
    paste(c, im, x - im.width / 2, y - im.height / 2)


# ------------------------------------------------------------ le potager : choux + poireaux
def cab_pos(i, cam):
    u, v, name, fl = CABBAGES[i]
    x, y = bedp(u, v)
    return cam.p(x, y + 0.03 * bedw(v)), C_W * bedw(v) * cam.z


def garden(cam, eaten=None, skip=(), extra=None, sain=0.0):
    """Décor + poireaux + choux. eaten : {i: q} → le chou i se fait dévorer (q ∈ [0, 1]).
    sain : 1 = choux intacts, 0 = rongés (nombre, ou {i: valeur}).
    extra(lay, i) : appelé avant de dessiner le chou i (pigeons derrière lui)."""
    w = decor(cam, POTAGER)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    for k, (x, y, h) in enumerate(LEEKS):
        X, Y = cam.p(x, y)
        if -200 < X < W + 200 and -300 < Y < H + 300:
            nm = POIREAUX[k % 3]
            im = _src(nm)
            hh = h * 1.3
            sp(lay, nm, X, Y + hh * 0.08 * z, hh * z * im.width / im.height, 0.5, 1.0, rot=((k * 37) % 7 - 3),
               flip=k % 2 == 1)
    for i in range(len(CABBAGES)):
        if extra:
            extra(lay, i)
        if i in skip:
            continue
        (X, Y), cw = cab_pos(i, cam)
        ground_shadow(lay, X, Y - cw * 0.04, cw * 0.95, 60)
        q = (eaten or {}).get(i, 1.0 if i != HERO else 0.0)
        sn = sain.get(i, 0.0) if isinstance(sain, dict) else sain
        draw_cabbage(lay, X, Y, cw, q, CABBAGES[i][3], sn, i)
    if extra:
        extra(lay, len(CABBAGES))
    w.alpha_composite(lay)
    return w


def draw_cabbage(c, X, Y, cw, q, flip=False, sain=0.0, i=0):
    """Chou intact (sain = 1) → rongé (q = 0) → réduit aux nervures (q = 1) : fondus enchaînés."""
    if sain < 0.999:
        if q < 0.999:
            sp(c, CHOU, X, Y, cw, 0.5, 1.0, flip=flip, alpha=1.0)
        if q > 0.001:
            sp(c, CHOU_N, X, Y, cw * 0.93, 0.5, 1.0, flip=flip, alpha=ease_io(q))
    if sain > 0.001:
        sp(c, SAINS[i % 4], X, Y, cw * 1.02, 0.5, 1.0, flip=flip, alpha=ease_io(sain))


# ------------------------------------------------------------ les pigeons
@lru_cache(None)
def feet(name):
    """Point d'appui (pattes) : milieu des pixels les plus bas de la silhouette, en fraction de la boîte."""
    a = np.asarray(_src(name).getchannel("A")) > 100
    h_ = a.shape[0]
    rows = a[int(h_ * 0.93):]
    ys, xs = np.nonzero(rows)
    return float(xs.mean() / a.shape[1]), 0.985


def pigeon(c, name, x, y, w, flip=False, t=0.0, peck=0.0, bob=0.0, sy=1.0, alpha=1.0):
    """Pigeon posé, pattes en (x, y), tourné vers la droite (flip : vers la gauche).
    peck > 0.45 : photo du pigeon qui picore (tête au sol), sinon pigeon debout qui hoche la tête."""
    ground_shadow(c, x, y, w * 0.7, 55)
    if peck > 0.45:
        nm, fl = PIG_PK, not flip
        ww = w * _src(PIG_PK).width / _src(PIG).width
        rot = (-4 if not flip else 4) * (peck - 0.45) / 0.55
    else:
        nm, fl, ww = PIG, flip, w
        rot = math.sin(t * 9) * 2.0 * bob + (-10 if not flip else 10) * peck
    fx, fy = feet(nm)
    sp(c, nm, x, y, ww, fx, fy, rot=rot, flip=fl, alpha=alpha, sy=sy, cold=5)


def flying(c, x, y, w, t, flip=False, seed=0, alpha=1.0):
    """Pigeon en vol (alternance ailes hautes / ailes basses, ~8 battements/s)."""
    ph = (t * 8 + seed * 0.37) % 1
    name = (VOL_UP if ph < 0.5 else VOL_DOWN)[0]
    sp(c, name, x, y, w, 0.5, 0.5, rot=(6 if flip else -6) * math.sin(t * 3 + seed), flip=flip, alpha=alpha, cold=5)


def fly_land(c, t, t0, t1, p0, p1, w0, w1, name=MARCHE, flip=False, seed=0, peck_from=None):
    """Arrive en vol de p0 et se pose en p1 entre t0 et t1, puis reste posé (petits mouvements)."""
    if t < t0:
        return
    if t < t1:
        q = (t - t0) / (t1 - t0)
        e = ease_out(q)
        x = lerp(p0[0], p1[0], e)
        y = lerp(p0[1], p1[1], e) - math.sin(math.pi * q) * 140 * (1 - q)
        flying(c, x, y - w1 * 0.35 * (1 - q) - w1 * 0.25, lerp(w0, w1 * 1.15, e), t, flip, seed)
        return
    land = clamp((t - t1) / 0.25)
    sy = 1 - 0.12 * math.sin(math.pi * land)
    pk = 0.0
    if peck_from is not None and t > peck_from:
        pk = max(0.0, math.sin((t - peck_from) * 2 * math.pi * 1.6)) ** 0.6
    pigeon(c, name, p1[0], p1[1], w1, flip, t + seed, peck=pk, bob=1 - pk, sy=sy)


def leaf_bits(c, t, t0, x, y, n=8, seed=1, spread=160, dur=0.7, size=16):
    """Petits morceaux de feuille de chou arrachés."""
    if t < t0 or t > t0 + dur:
        return
    r = np.random.default_rng(seed)
    q = (t - t0) / dur
    d = ImageDraw.Draw(c)
    for _ in range(n):
        ang = r.uniform(-math.pi * 0.95, -math.pi * 0.05)
        sp_ = r.uniform(0.4, 1.0) * spread
        px = x + math.cos(ang) * sp_ * q
        py = y + math.sin(ang) * sp_ * q + 260 * q * q
        s = size * r.uniform(0.6, 1.2) * (1 - 0.4 * q)
        col = (int(r.uniform(90, 140)), int(r.uniform(150, 190)), int(r.uniform(70, 100)), int(255 * (1 - q ** 2)))
        d.polygon([(px - s, py), (px, py - s * 0.6), (px + s * 0.8, py + s * 0.2), (px - s * 0.2, py + s * 0.6)],
                  fill=col)


# ------------------------------------------------------------ arceaux et filet anti-oiseaux sur le grand carré
NET_V0, NET_V1 = 0.03, 0.93                       # le tunnel couvre presque tout le carré
NET_U, NET_H = 0.46, 0.52                         # demi-largeur et hauteur du tunnel (en largeurs de carré)
HOOPS = [0.03, 0.255, 0.48, 0.705, 0.93]


def arch(v, n=40, k=1.0):
    """Arceau à la profondeur v : points (plein écran). k ∈ [0, 1] : enfoncé dans le sol (il monte)."""
    pts = []
    for i in range(n + 1):
        th = math.pi * i / n
        pts.append(up(0.5 - NET_U * math.cos(th), v, NET_H * math.sin(th) * k))
    return pts


def hoop(d, cam, v, k, ss):
    pts = [cam.p(*p) for p in arch(v, 48, k)]
    pts = [(x * ss, y * ss) for x, y in pts]
    wd = max(2, int(0.022 * bedw(v) * cam.z * ss))
    d.line(pts, fill=(38, 54, 46, 255), width=wd, joint="curve")
    d.line([(x - wd * 0.18, y - wd * 0.18) for x, y in pts], fill=(110, 132, 120, 255), width=max(1, wd // 4),
           joint="curve")


def net_layer(cam, hoops_k, net_q, front_cap=1.0):
    """Arceaux (hoops_k[i] ∈ [0, 1] : ils sortent du sol) et filet déroulé du fond vers l'avant (net_q)."""
    ss = 2
    big = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    z = cam.z
    if net_q > 0.001:
        vmin = NET_V1 - (NET_V1 - NET_V0) * net_q
        # voile gris très léger (la maille fine vue de loin)
        veil = Image.new("L", (W * ss, H * ss), 0)
        dv = ImageDraw.Draw(veil)
        nv = 26
        for j in range(nv):
            va, vb = lerp(vmin, NET_V1, j / nv), lerp(vmin, NET_V1, (j + 1) / nv)
            poly = arch(va, 30) + arch(vb, 30)[::-1]
            dv.polygon([(cam.p(*p)[0] * ss, cam.p(*p)[1] * ss) for p in poly], fill=70)
        cap = arch(NET_V1, 30)
        dv.polygon([(cam.p(*p)[0] * ss, cam.p(*p)[1] * ss) for p in cap], fill=50)
        if net_q > 0.98 and front_cap > 0:
            dv.polygon([(cam.p(*p)[0] * ss, cam.p(*p)[1] * ss) for p in arch(NET_V0, 30)],
                       fill=int(50 * front_cap))
        tint = Image.new("RGBA", (W * ss, H * ss), (215, 222, 220, 0))
        tint.putalpha(veil)
        big.alpha_composite(tint)
        # les mailles : lignes le long du tunnel (θ constant) et parallèles aux arceaux (v constant)
        col = (26, 38, 32, 215)
        lw = 2
        nth = 46
        for i in range(1, nth):
            th = math.pi * i / nth
            u, hh = 0.5 - NET_U * math.cos(th), NET_H * math.sin(th)
            pts = [cam.p(*up(u, lerp(vmin, NET_V1, j / 30), hh)) for j in range(31)]
            d.line([(x * ss, y * ss) for x, y in pts], fill=col, width=lw)
        nvl = int(70 * net_q) + 1
        for j in range(nvl + 1):
            vv = lerp(vmin, NET_V1, j / nvl)
            pts = [cam.p(*p) for p in arch(vv, 40)]
            d.line([(x * ss, y * ss) for x, y in pts], fill=col, width=lw)
        # fond (et devant à la fin) : maille verticale/horizontale dans le plan de l'arceau
        caps = [NET_V1] + ([NET_V0] if net_q > 0.98 and front_cap > 0 else [])
        for vv in caps:
            for i in range(1, 30):
                u = 0.5 - NET_U + 2 * NET_U * i / 30
                hh = NET_H * math.sqrt(max(0.0, 1 - ((u - 0.5) / NET_U) ** 2))
                a, b = cam.p(*up(u, vv, 0)), cam.p(*up(u, vv, hh))
                d.line([(a[0] * ss, a[1] * ss), (b[0] * ss, b[1] * ss)], fill=col, width=lw)
            for j in range(1, 16):
                hh = NET_H * j / 16
                du = NET_U * math.sqrt(max(0.0, 1 - (hh / NET_H) ** 2))
                a, b = cam.p(*up(0.5 - du, vv, hh)), cam.p(*up(0.5 + du, vv, hh))
                d.line([(a[0] * ss, a[1] * ss), (b[0] * ss, b[1] * ss)], fill=col, width=lw)
        # bord du filet qui se déroule (un peu plus épais)
        if net_q < 0.98:
            pts = [cam.p(*p) for p in arch(vmin, 40)]
            d.line([(x * ss, y * ss) for x, y in pts], fill=(30, 44, 38, 230), width=3 * ss)
    for v, k in zip(HOOPS, hoops_k):
        if k > 0.001:
            hoop(d, cam, v, k, ss)
    return big.resize((W, H), Image.LANCZOS)


def net_top(v, cam):
    return cam.p(*up(0.5, v, NET_H))


# ------------------------------------------------------------ le filet posé directement sur le chou
def net_on(c, cab_layer, cell, alpha=1.0, seed=0):
    """Filet plaqué sur les feuilles : maille souple (lignes ondulées) limitée à la silhouette du chou."""
    m = cab_layer.getchannel("A").point(lambda v: 255 if v > 40 else 0).filter(ImageFilter.MaxFilter(15))
    bb = m.getbbox()
    if not bb or alpha <= 0.01:
        return
    ss = 2
    x0, y0, x1, y1 = bb[0] - 20, bb[1] - 20, bb[2] + 20, bb[3] + 20
    big = Image.new("RGBA", ((x1 - x0) * ss, (y1 - y0) * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    col = (24, 36, 30, 235)
    lw = max(2, int(cell * 0.09 * ss))
    n_x = int((x1 - x0) / cell) + 2
    n_y = int((y1 - y0) / cell) + 2
    for i in range(n_x):
        pts = [((i * cell + 5 * math.sin(yy / 37.0 + i * 0.7)) * ss, yy * ss) for yy in range(0, y1 - y0 + 8, 8)]
        d.line(pts, fill=col, width=lw)
    for j in range(n_y):
        pts = [(xx * ss, (j * cell + 5 * math.sin(xx / 41.0 + j * 0.9)) * ss) for xx in range(0, x1 - x0 + 8, 8)]
        d.line(pts, fill=col, width=lw)
    net = big.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    paste(full, net, x0, y0)
    a = np.asarray(full.getchannel("A")).astype(np.float32) * (np.asarray(m).astype(np.float32) / 255) * alpha
    full.putalpha(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    # léger voile gris (le filet aplatit les couleurs des feuilles)
    veil = Image.new("RGBA", (W, H), (200, 208, 205, 0))
    veil.putalpha(m.point(lambda v: int(v * 0.16 * alpha)))
    c.alpha_composite(veil)
    c.alpha_composite(full)


# ------------------------------------------------------------ petites cartes
@lru_cache(None)
def photo_card(name, size=330, ring=GREEN):
    """Pastille ronde avec un objet détouré dedans (crème, cerclée)."""
    k = 3

    def f(d, kk, _):
        d.ellipse([8 * kk, 14 * kk, size * kk - 1, size * kk + 5 * kk], fill=(0, 0, 0, 80))
        d.ellipse([0, 0, (size - 8) * kk, (size - 8) * kk], fill=CREAM, outline=ring, width=12 * kk)
    im = aa(size + 8, size + 14, f, k)
    ob_ = _src(name)
    s = (size * 0.66) / max(ob_.width, ob_.height)
    o = ob_.resize((int(ob_.width * s), int(ob_.height * s)), Image.LANCZOS)
    im.alpha_composite(o, ((size - 8 - o.width) // 2, (size - 8 - o.height) // 2))
    return im


@lru_cache(None)
def day_card(n, size=300):
    w_, h_ = size, int(size * 1.1)

    def f(d, kk, _):
        d.rounded_rectangle([10 * kk, 18 * kk, (w_ - 2) * kk, (h_ - 2) * kk], radius=24 * kk, fill=(0, 0, 0, 90))
        d.rounded_rectangle([0, 0, (w_ - 12) * kk, (h_ - 14) * kk], radius=24 * kk, fill=CREAM)
        d.rounded_rectangle([0, 0, (w_ - 12) * kk, int(h_ * 0.27) * kk], radius=24 * kk, fill=RED)
        d.rectangle([0, int(h_ * 0.15) * kk, (w_ - 12) * kk, int(h_ * 0.27) * kk], fill=RED)
        d.rounded_rectangle([0, 0, (w_ - 12) * kk, (h_ - 14) * kk], radius=24 * kk, outline=DARK, width=6 * kk)
    im = aa(w_, h_, f, 3)
    m = text_img("JOUR", F_BLACK, int(size * 0.15), WHITE)
    im.alpha_composite(m, ((w_ - 12 - m.width) // 2, int(h_ * 0.135 - m.height / 2)))
    t_ = text_img(str(n), F_TITLE, int(size * 0.5), DARK)
    im.alpha_composite(t_, ((w_ - 12 - t_.width) // 2, int(h_ * 0.6 - t_.height / 2)))
    return im


# ============================================================ A. LES CHOUX DÉVORÉS EN PLEIN HIVER (0 → 2.3)
def s_open(t):
    k = ease_io(clamp(t / 2.3))
    cam = Cam(lerp(1.0, 1.22, k), lerp(540, 520, k), lerp(960, 1230, k))
    order = [4, 1, 3, 0, 5, 2]
    sain = {i: 1 - ease_io(clamp((t - 0.78 - 0.13 * order.index(i)) / 0.3)) for i in range(len(CABBAGES))}
    w = garden(cam, sain=sain)
    bits = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for n_, i in enumerate(order):
        (X, Y), cw = cab_pos(i, cam)
        leaf_bits(bits, t, 0.85 + 0.13 * n_, X, Y - cw * 0.5, 7, seed=40 + n_, spread=cw * 0.8, size=cw * 0.06)
    w.alpha_composite(bits)
    snowfall(w, t, 1.0)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    title(u, "TES CHOUX DÉVORÉS…", t, 0.05, 1.15, y=330, color=WHITE, size=120)
    title(u, "EN PLEIN HIVER ?", t, 1.2, 2.3, y=330, color=YEL, size=140)
    put(u, snow_badge(), 900, 610, life(t, 1.25, 2.3))
    return w, u


cue(0.05, "whoosh", 0.1)
cue(1.25, "pop", 0.16)
for _n in range(6):
    cue(0.85 + 0.13 * _n, "peck", 0.1)


# ============================================================ B. PAS LES CHENILLES… LES PIGEONS ! (2.3 → 4.85)
def s_culprit(t):
    hx, hy = bedp(*CABBAGES[HERO][:2])
    k = ease_io(clamp((t - 2.3) / 0.9))
    cam = Cam(lerp(1.22, 2.0, k), lerp(520, hx + 60, k), lerp(1230, hy - 120, k))
    (X, Y), cw = cab_pos(HERO, cam)
    z = cam.z

    def extra(lay, i):
        if i != len(CABBAGES):
            return
        # la chenille sur une feuille (barrée), puis les pigeons qui arrivent
        if 2.6 < t < 4.3:
            a = life(t, 2.6, 4.25)
            cx, cy = X + cw * 0.12, Y - cw * 0.55
            sp(lay, CHENILLE, cx + math.sin(t * 3) * 6, cy, cw * 0.5 * a, 0.5, 0.5, rot=-12, alpha=a, cold=3)
        fly_land(lay, t, 4.2, 4.7, (W + 250, 500), (X - cw * 0.55, Y + cw * 0.05), 200, cw * 0.62, MARCHE, False,
                 0, peck_from=None)
        fly_land(lay, t, 4.32, 4.82, (-250, 700), (X + cw * 0.62, Y + cw * 0.12), 200, cw * 0.66, BIZET, True, 1)
    w = garden(cam, extra=extra)
    snowfall(w, t, 0.7)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if 2.6 < t < 4.2:
        a = life(t, 2.95, 4.15)
        put(u, icon("nosign", 330), X + cw * 0.12, Y - cw * 0.55, a)
    title(u, "CE NE SONT PAS", t, 2.3, 3.6, y=300, color=WHITE, size=120)
    title(u, "LES CHENILLES…", t, 2.3, 3.6, y=440, color=YEL, size=120)
    stamp(u, "CE SONT LES PIGEONS !", 540, 350, t, 4.27, None, RED, 100, -6)
    return w, u


cue(2.32, "whoosh", 0.1)
cue(2.98, "fail", 0.16)
cue(4.2, "flap", 0.2)
cue(4.32, "flap", 0.16)
cue(4.27, "thud", 0.2)
cue(4.7, "coo", 0.22)


# ============================================================ C. EN HIVER, LES CHENILLES ONT DISPARU (4.85 → 7.75)
def s_winter(t):
    k = ease_io(clamp((t - 4.85) / 2.9))
    cam = Cam(lerp(1.15, 1.05, k), 540, lerp(1050, 980, k))
    w = garden(cam)
    snowfall(w, t, 1.4, n=170)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    # la chenille dans sa pastille : elle s'efface (partie depuis longtemps)
    s = life(t, 5.95, 7.65)
    if s > 0.01:
        card = photo_card(CHENILLE, 360)
        fadeq = clamp((t - 6.55) / 0.7)
        put(u, card, 540, 1000, s, rot=-4)
        if fadeq > 0:
            put(u, icon("cross", 200), 540, 1000, ease_out_back(clamp(fadeq / 0.4), 1.6) * s)
    put(u, icon("snow", 170), 880, 620, life(t, 5.2, 7.65))
    title(u, "EN HIVER…", t, 4.87, 5.9, y=330, color=WHITE, size=150)
    title(u, "LES CHENILLES ONT DISPARU", t, 5.95, 7.7, y=330, color=YEL, size=88)
    return w, u


cue(4.88, "whoosh", 0.1)
cue(5.95, "pop", 0.16)
cue(6.6, "fail", 0.14)


# ============================================================ D. MAIS LES PIGEONS, EUX, ONT FAIM (7.75 → 9.8)
WALK = [((0.36, 0.30), (0.50, 0.31), MARCHE, False, 0.36), ((0.68, 0.05), (0.56, 0.05), BIZET, True, 0.38),
        ((0.5, 0.64), (0.47, 0.62), RAMIER, True, 0.40)]


def s_hungry(t):
    k = ease_io(clamp((t - 7.75) / 2.0))
    cam = Cam(lerp(1.3, 1.45, k), 540, lerp(1200, 1260, k))
    z = cam.z

    def extra(lay, i):
        # chaque pigeon est dessiné avant le chou qui est devant lui
        for j, (a, b, nm, fl, sz) in enumerate(WALK):
            vb = lerp(a[1], b[1], 0.5)
            order = sum(1 for c_ in CABBAGES if c_[1] > vb)
            if order != i:
                continue
            q = clamp((t - 7.8 - j * 0.15) / 2.0)
            u_, v_ = lerp(a[0], b[0], q), lerp(a[1], b[1], q)
            x, y = cam.p(*bedp(u_, v_))
            hop = abs(math.sin(t * 6 + j)) * 6 * z
            pk = max(0.0, math.sin((t - 8.6 - j * 0.3) * 2 * math.pi * 1.4)) ** 0.7 if t > 8.6 + j * 0.3 else 0
            pigeon(lay, nm, x, y - hop * (1 - pk), sz * bedw(v_) * z, fl, t + j, peck=pk * 0.8, bob=1)
    w = garden(cam, extra=extra)
    snowfall(w, t, 0.8)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    title(u, "MAIS LES PIGEONS…", t, 7.77, 9.0, y=330, color=WHITE, size=120)
    stamp(u, "EUX, ONT FAIM !", 540, 350, t, 9.05, 9.75, RED, 120, -6)
    return w, u


cue(7.8, "whoosh", 0.1)
cue(8.2, "coo", 0.2)
cue(9.05, "thud", 0.18)
cue(9.3, "coo_lo", 0.18)


# ============================================================ E. ILS PICORENT JUSQU'AUX NERVURES (9.8 → 12.95)
def s_peck(t):
    hx, hy = bedp(*CABBAGES[HERO][:2])
    cwo = C_W * bedw(CABBAGES[HERO][1])
    cam = Cam(lerp(2.0, 2.2, clamp((t - 9.8) / 3.1)), hx + cwo * 0.18, hy - cwo * 0.45)
    (X, Y), cw = cab_pos(HERO, cam)
    q = ease_io(clamp((t - 10.3) / 2.1))
    pk_l = max(0.0, math.sin((t - 10.0) * 2 * math.pi * 1.7)) ** 0.6 if t > 10.0 else 0
    pk_r = max(0.0, math.sin((t - 10.25) * 2 * math.pi * 1.5)) ** 0.6 if t > 10.25 else 0

    def extra(lay, i):
        if i == HERO:            # le pigeon de droite est un peu derrière le chou
            pigeon(lay, BIZET, X + cw * 0.52, Y - cw * 0.1, cw * 0.68, True, t + 1, peck=pk_r * 0.85, bob=0.5)
        if i == len(CABBAGES):
            pigeon(lay, MARCHE, X + cw * 0.02, Y + cw * 0.16, cw * 0.68, False, t, peck=pk_l, bob=0.5)
    w = garden(cam, eaten={HERO: q}, extra=extra)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for n_, t0 in enumerate([10.05, 10.65, 11.25, 11.85]):
        leaf_bits(lay, t, t0 + 0.18, X - cw * 0.2, Y - cw * 0.45, 7, seed=n_ + 3, spread=220, size=18)
    for n_, t0 in enumerate([10.35, 11.0, 11.65]):
        leaf_bits(lay, t, t0 + 0.2, X + cw * 0.22, Y - cw * 0.5, 6, seed=n_ + 11, spread=200, size=16)
    w.alpha_composite(lay)
    snowfall(w, t, 0.5)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    title(u, "ILS PICORENT TES CHOUX…", t, 9.82, 12.25, y=330, color=WHITE, size=100)
    tag(u, "IL RESTE LES NERVURES", X + cw * 0.05, Y - cw * 1.25, t, 12.3, None, rot=-5, size=52)
    return w, u


cue(9.83, "whoosh", 0.1)
for _t in (10.2, 10.85, 11.45, 12.0):
    cue(_t, "peck", 0.22)
cue(10.6, "coo", 0.16)
cue(12.32, "pop", 0.18)


# ============================================================ F. LA SOLUTION : FILET SUR ARCEAUX (12.95 → 16.8)
HOOP_T = [13.25, 13.45, 13.65, 13.85, 14.05]


def s_net(t):
    k = ease_io(clamp((t - 12.95) / 1.2))
    cam = Cam(lerp(1.45, 1.12, k), 545, lerp(1260, 1220, k))
    hk = [ease_out_back(clamp((t - t0) / 0.35), 1.4) for t0 in HOOP_T]
    nq = ease_io(clamp((t - 14.35) / 1.2))

    def extra(lay, i):
        if i == len(CABBAGES):
            # un pigeon dérangé s'envole quand le filet arrive
            if t < 14.3:
                x, y = cam.p(*bedp(0.52, 0.62))
                pigeon(lay, MARCHE, x, y, 0.30 * bedw(0.62) * cam.z, False, t)
            elif t < 15.2:
                qq = (t - 14.3) / 0.9
                x, y = cam.p(*bedp(0.52, 0.62))
                flying(lay, lerp(x, W + 300, ease_in(qq)), lerp(y - 60, 200, ease_out(qq)), 230, t)
    w = garden(cam, extra=extra, sain=1.0)
    w.alpha_composite(_cold(net_layer(cam, hk, nq), 0.4))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # un pigeon se pose sur le filet : il ne peut pas entrer
    tx, ty = net_top(0.5, cam)
    fly_land(lay, t, 15.55, 16.15, (-250, 450), (tx, ty + 6), 220, 0.28 * bedw(0.5) * cam.z, BIZET, True, 1)
    w.alpha_composite(lay)
    snowfall(w, t, 0.6)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    title(u, "LA SOLUTION :", t, 12.97, 14.3, y=330, color=WHITE, size=140)
    title(u, "UN FILET ANTI-OISEAUX", t, 14.32, 16.2, y=330, color=YEL, size=96)
    title(u, "SUR DES ARCEAUX", t, 16.22, 16.8, y=330, color=YEL, size=120)
    s = life(t, 16.2, 16.8)
    if s > 0.01:
        put(u, photo_card(ARCEAUX, 300), 880, 620, s, rot=5)
    if t > 16.15:
        put(u, icon("check", 140), tx + 150, ty - 120, ease_out_back(clamp((t - 16.15) / 0.3), 1.6))
    return w, u


cue(12.98, "whoosh", 0.1)
for _t in HOOP_T:
    cue(_t, "pop_lo", 0.14)
cue(14.35, "whoosh_up", 0.16)
cue(15.55, "flap", 0.18)
cue(16.15, "ding", 0.16)
cue(16.3, "pop", 0.14)


# ============================================================ G. ATTENTION : PAS SUR LES FEUILLES (16.8 → 20.95)
def s_touch(t):
    hx, hy = bedp(*CABBAGES[HERO][:2])
    cam = Cam(lerp(2.0, 2.2, clamp((t - 16.8) / 4.1)), hx + 20, hy - 170)
    (X, Y), cw = cab_pos(HERO, cam)
    pk = max(0.0, math.sin((t - 19.3) * 2 * math.pi * 1.7)) ** 0.6 if t > 19.3 else 0
    # le chou du premier plan, sain d'abord (q = 0), le filet posé dessus
    w = garden(cam, skip=(HERO,), sain=1.0)
    cab = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ground_shadow(cab, X, Y - cw * 0.04, cw * 0.95, 60)
    draw_cabbage(cab, X, Y, cw, 0.0, CABBAGES[HERO][3], 1 - clamp((t - 19.6) / 1.2), HERO)
    w.alpha_composite(cab)
    netk = ease_out(clamp((t - 17.6) / 0.6))
    if netk > 0:
        net_on(w, cab, 30, alpha=netk)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fly_land(lay, t, 18.6, 19.2, (W + 250, 420), (X + cw * 0.2, Y - cw * 0.62), 230, cw * 0.58, MARCHE, True, 0)
    if t > 19.2:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pigeon(lay, MARCHE, X + cw * 0.2, Y - cw * 0.62, cw * 0.58, True, t, peck=pk, bob=0.4,
               sy=1 - 0.12 * math.sin(math.pi * clamp((t - 19.2) / 0.25)))
    w.alpha_composite(lay)
    bits = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for n_, t0 in enumerate([19.5, 20.1, 20.7]):
        leaf_bits(bits, t, t0, X - cw * 0.05, Y - cw * 0.55, 7, seed=n_ + 21, spread=210, size=18)
    w.alpha_composite(bits)
    snowfall(w, t, 0.5)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    stamp(u, "ATTENTION !", 540, 330, t, 16.85, 17.6, RED, 140, -6)
    title(u, "LE FILET NE DOIT PAS", t, 17.62, 19.25, y=300, color=WHITE, size=100)
    title(u, "TOUCHER LES FEUILLES", t, 17.62, 19.25, y=430, color=YEL, size=100)
    title(u, "SINON ILS PICORENT", t, 19.27, 20.95, y=300, color=WHITE, size=110)
    title(u, "À TRAVERS !", t, 19.27, 20.95, y=430, color=YEL, size=130)
    if t > 19.75:
        put(u, icon("cross", 170), X - cw * 0.45, Y - cw * 1.05, ease_out_back(clamp((t - 19.75) / 0.3), 1.6))
    return w, u


cue(16.86, "thud", 0.2)
cue(16.9, "alert1", 0.14)
cue(17.62, "whoosh", 0.12)
cue(18.6, "flap", 0.18)
for _t in (19.45, 20.05, 20.65):
    cue(_t, "peck", 0.22)
cue(19.8, "fail", 0.14)


# ============================================================ H. OUBLIE LES CD ET LES ÉPOUVANTAILS (20.95 → 25.15)
SCARE = (0.5, 0.10)               # l'épouvantail planté au milieu du carré
CD_SPOTS = [(0.12, 0.30), (0.88, 0.30)]


def scarecrow_geom(cam):
    x, y = cam.p(*bedp(*SCARE))
    h = 0.8 * bedw(SCARE[1]) * cam.z
    im = _src(EPOUV)
    wd = h * im.width / im.height
    return x, y, wd, h


def s_scare(t):
    k = ease_io(clamp((t - 20.95) / 1.0))
    cam = Cam(lerp(1.15, 1.28, k), 545, lerp(1180, 1240, k))
    z = cam.z
    ex, ey, ew, eh = scarecrow_geom(cam)
    ks = ease_out_back(clamp((t - 22.15) / 0.45), 1.5)
    cds = [ease_out_back(clamp((t - 21.25 - 0.15 * i) / 0.45), 1.5) for i in range(2)]

    def extra(lay, i):
        # CD pendus à un piquet (bords du carré)
        if i == 2:
            for j, (cu, cv) in enumerate(CD_SPOTS):
                if cds[j] <= 0.01:
                    continue
                bx, by = cam.p(*bedp(cu, cv))
                ph = bedw(cv) * z * 0.7 * cds[j]
                d = ImageDraw.Draw(lay)
                pw = max(3, int(9 * z))
                d.line([(bx, by), (bx, by - ph)], fill=(118, 92, 60, 255), width=pw)
                d.line([(bx - pw * 0.3, by), (bx - pw * 0.3, by - ph)], fill=(150, 120, 82, 255), width=max(1, pw // 3))
                d.line([(bx, by - ph * 0.95), (bx + 0.12 * ph * (1 if j else -1), by - ph * 0.95)],
                       fill=(118, 92, 60, 255), width=pw)
                hx_ = bx + 0.12 * ph * (1 if j else -1)
                sw = math.sin(t * 2.2 + j) * 10
                spin = abs(math.cos(t * 2.6 + j * 1.3))
                cw_ = ph * 0.27
                d.line([(hx_, by - ph * 0.95), (hx_ + math.sin(math.radians(sw)) * ph * 0.12, by - ph * 0.83)],
                       fill=(196, 170, 120, 255), width=max(1, pw // 3))
                sp(lay, CD if spin > 0.5 else CD2, hx_ + math.sin(math.radians(sw)) * ph * 0.12, by - ph * 0.84,
                   cw_ * (0.35 + 0.65 * spin), 0.5, 0.0, rot=sw, cold=2)
        if i == len(CABBAGES) and ks > 0.01:
            sp(lay, EPOUV, ex, ey, ew * ks, 0.5, 1.0, cold=5)
        if i == len(CABBAGES):
            # au bout de quelques jours, les pigeons se posent sur l'épouvantail et le picorent
            arm_y = ey - eh * 0.66
            fly_land(lay, t, 24.0, 24.55, (-250, 450), (ex - ew * 0.36, arm_y), 220, ew * 0.27, BIZET, False, 1,
                     peck_from=24.75)
            fly_land(lay, t, 24.15, 24.7, (W + 250, 380), (ex + ew * 0.36, arm_y), 220, ew * 0.27, MARCHE, True, 0,
                     peck_from=24.85)
            fly_land(lay, t, 24.35, 24.9, (W + 250, 250), (ex + ew * 0.04, ey - eh * 0.93), 200, ew * 0.25,
                     MARCHE, False, 2, peck_from=24.95)
    w = garden(cam, extra=extra)
    snowfall(w, t, 0.6)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    for j, (cu, cv) in enumerate(CD_SPOTS):
        bx, by = cam.p(*bedp(cu, cv))
        ph = bedw(cv) * z * 0.7
        sparkles(u, t, 21.4 + 0.3 * j, bx + 0.12 * ph * (1 if j else -1), by - ph * 0.72, 70, 6, 5 + j, 0.8)
    if 21.65 < t < 23.0:
        a = life(t, 21.67, 22.95)
        bx, by = cam.p(*bedp(*CD_SPOTS[0]))
        put(u, icon("nosign", 130), bx - 0.084 * bedw(0.3) * z, by - bedw(0.3) * z * 0.5, a)
        bx, by = cam.p(*bedp(*CD_SPOTS[1]))
        put(u, icon("nosign", 130), bx + 0.084 * bedw(0.3) * z, by - bedw(0.3) * z * 0.5, a)
    title(u, "OUBLIE LES CD…", t, 20.97, 22.15, y=330, color=WHITE, size=130)
    title(u, "ET LES ÉPOUVANTAILS !", t, 22.17, 23.0, y=330, color=YEL, size=105)
    # quelques jours passent
    for n_ in range(1, 5):
        t0 = 23.05 + (n_ - 1) * 0.28
        s = life(t, t0, 24.1 if n_ == 4 else t0 + 0.28, dur=0.12, out=0.08)
        if s > 0.01:
            put(u, day_card(n_), 540, 330, s, rot=-4 + n_ * 2)
    title(u, "ILS N'ONT PLUS PEUR !", t, 24.15, 25.15, y=330, color=YEL, size=110)
    return w, u


cue(20.98, "whoosh", 0.1)
cue(21.3, "sparkle", 0.14)
cue(21.67, "fail", 0.12)
cue(22.17, "pop_lo", 0.18)
for _n in range(4):
    cue(23.05 + _n * 0.28, "tick", 0.2)
cue(24.0, "flap", 0.18)
cue(24.3, "flap", 0.14)
cue(24.5, "coo", 0.2)
for _t in (24.8, 25.1):
    cue(_t, "peck", 0.2)
cue(24.9, "laugh", 0.06)


# ============================================================ I. ABONNE-TOI (25.15 → fin)
def s_end(t):
    cam = Cam(1.12, 545, 1220)
    tx, ty = net_top(0.5, cam)
    w = garden(cam, sain=1.0)
    w.alpha_composite(_cold(net_layer(cam, [1] * 5, 1.0), 0.4))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pigeon(lay, BIZET, tx, ty + 6, 0.32 * bedw(0.5) * cam.z, True, t, bob=1)
    gx, gy = cam.p(150, 1330)
    pigeon(lay, RAMIER, gx, gy, 270, False, t + 2, bob=1)
    w.alpha_composite(lay)
    snowfall(w, t, 0.8)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    clicked = t > 26.75
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 26.7) / 0.15))
    put(u, btn, 540, 1400, life(t, 25.4) * press)
    if t > 26.2:
        kk = ease_out((t - 26.2) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 27.65, dur=0.45))
    sparkles(u, t, 27.75, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 25.2, 27.6, y=330, color=YEL, size=135)
    return w, u


cue(25.25, "pop_lo", 0.18)
cue(25.6, "coo_lo", 0.14)
cue(26.73, "click", 0.3)
cue(27.75, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 2.3 - SHIFT, _sh(s_open)),
    (2.3 - SHIFT, 4.85 - SHIFT, _sh(s_culprit)),
    (4.85 - SHIFT, 7.75 - SHIFT, _sh(s_winter)),
    (7.75 - SHIFT, 9.8 - SHIFT, _sh(s_hungry)),
    (9.8 - SHIFT, 12.95 - SHIFT, _sh(s_peck)),
    (12.95 - SHIFT, 16.8 - SHIFT, _sh(s_net)),
    (16.8 - SHIFT, 20.95 - SHIFT, _sh(s_touch)),
    (20.95 - SHIFT, 25.15 - SHIFT, _sh(s_scare)),
    (25.15 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
