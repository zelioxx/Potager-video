"""Storyboard « D'où viennent les fraises ? » (voix : assets/audio/fraises/voix.mp3).

Volume de la voix gardé tel qu'envoyé (render.py « af »).
Décor : la cuisine lumineuse avec vue sur Paris (photo fournie). Sur la planche : un plant de fraisier en pot, composé
avec les photos fournies (foliole, étapes de la fleur au fruit), et le panier de fraises.
0–3.55   « la fraise n'est pas un fruit » : une fraise saute du panier, ✗ ; « et ce n'est pas le pire ».
3.55–7.3 « la partie rouge… la base gonflée de la fleur » : fraise coupée, puis la fleur se transforme en fraise.
7.3–10.3 fond beige : les vrais fruits = les petits grains (loupe sur la photo macro de la peau).
10.3–12.1 chaque grain cache une graine (akène).
12.1–16.6 une seule fraise ≈ 200 fruits (compteur, grains qui s'allument).
16.6–fin retour cuisine : le plant donne ses fraises en accéléré ; S'abonner + logo.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, put, title, life, fade, ease_out,
                 ease_io, ease_in, clamp, lerp, icon, tag, button_img, hl_ellipse, particles, light_rays, text_img,
                 F_TITLE)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp
from scenes_citron import shade, shadow, swap
from scenes_banane import ob
from scenes_eau_pates import Cam

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


B = "banque/"
KITCHEN = "decor_cuisine_planche_fenetre.jpg"
FULL = (0, 0, 1024, 1024)
GROSSE, COUPEE, PANIER, AKENE, LOUPE = B + "fraise_grosse", B + "fraise_coupee", B + "panier_fraises", B + "akene", \
    B + "loupe"
POT = "citron/pot_vide"
# étapes de la fleur au fruit : (nom, x de la tige, bas de la tige, col / début de la tête) dans le cadre 1024
STAGES = [(B + "fraisier_bouton", 489, 957, 434), (B + "fraisier_bouton2", 483, 961, 392),
          (B + "fraisier_fleur_ouvre", 531, 961, 508), (B + "fraisier_fleur", 491, 965, 610),
          (B + "fraisier_sans_petales", 491, 961, 507), (B + "fraisier_fruit_vert", 540, 960, 481)]
GLASS_C, GLASS_R = (286.5, 367.5), 204.5        # verre de la loupe (cadre 1024)


@lru_cache(None)
def img(name):
    return Image.open(os.path.join(IMG, name + ".png")).convert("RGBA")


@lru_cache(None)
def red_stage():
    """Dernière étape : la tige du fruit vert portant la fraise mûre (tête gonflée et rouge)."""
    base = img(STAGES[5][0]).copy()
    a = np.asarray(base).copy()
    a[:STAGES[5][3] + 25, :, 3] = 0                        # on garde la tige, sans la tête verte
    out = Image.fromarray(a)
    f = img(GROSSE).rotate(180, resample=Image.BICUBIC)     # pointe en haut, sépales sur la tige
    k = 423 * 1.35 / 689
    f = f.resize((int(1024 * k), int(1024 * k)), Image.LANCZOS)
    ax, ay = (1024 - 515) * k, (1024 - 75) * k              # pédoncule de la fraise retournée
    out.alpha_composite(f, (int(540 - ax), int(STAGES[5][3] + 30 - ay)))
    return out


def stage_img(i):
    return red_stage() if i >= 6 else img(STAGES[i][0])


def stage_anchor(i):
    s = STAGES[min(i, 5)]
    return s[1], s[2]


@lru_cache(256)
def _scaled(key, k_q):
    name, i = key
    im = stage_img(i) if name is None else (img(name) if not name.endswith("jpg") else None)
    k = k_q / 1000
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.BICUBIC)


def pivot(c, key, px, py, X, Y, k, rot=0.0, alpha=1.0):
    """Pose l'image (clé) à l'échelle k, son point (px, py) en (X, Y), tournée de rot degrés autour de ce point."""
    if k <= 0.003:
        return
    im = _scaled(key, int(round(k * 1000)))
    px, py = px * k, py * k
    R = int(math.hypot(max(px, im.width - px), max(py, im.height - py))) + 2
    can = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    can.paste(im, (int(R - px), int(R - py)))
    if abs(rot) > 0.1:
        can = can.rotate(rot, resample=Image.BICUBIC)
    if alpha < 1:
        can.putalpha(can.getchannel("A").point(lambda v: int(v * alpha)))
    c.alpha_composite(can, (int(X - R), int(Y - R)))


# ------------------------------------------------------------- le plant de fraisier en pot
LEAVES = [(-80, 0.7, 0), (-55, 1.0, 0), (-30, 1.15, 1), (-5, 1.25, 0), (18, 1.1, 1), (42, 1.05, 0), (65, 0.85, 1),
          (88, 0.6, 0), (-95, 0.5, 1)]
FLOWERS = [(-28, 1.05, 0.0), (22, 0.95, 0.35), (55, 0.8, 0.7)]      # angle, longueur, décalage d'âge


def trifoliate(c, x, y, ang, s):
    """Feuille de fraisier : trois folioles (photo) en éventail au bout du pétiole."""
    for d in (-40, 0, 40):
        pivot(c, (B + "foliole_fraisier", 0), 300, 560, x, y, s * (0.85 if d else 1.0), -(ang + d))


def plant(c, X, Ybot, pw, stage, wob=0.0):
    """Plant de fraisier : pot (photo) de largeur pw, bas en (X, Ybot) ; stage 0..6 = âge des fleurs/fruits."""
    k = pw / 674
    shadow(c, X, Ybot, pw * 0.95, 70)
    place(c, POT, (0, 0, 1254, 1254), k, 628, 1025, X, Ybot)
    sx, sy = X + (624 - 628) * k, Ybot + (412 - 1025) * k
    s = pw / 300
    d = ImageDraw.Draw(c)
    tips = []
    for ang, ln, front in LEAVES:
        a = math.radians(ang + wob * math.sin(ang))
        tx, ty = sx + math.sin(a) * 150 * ln * s, sy - math.cos(a) * 150 * ln * s
        tips.append((tx, ty, ang, front))
    for tx, ty, ang, front in tips:          # feuilles du fond
        if not front:
            d.line([(sx, sy), (tx, ty)], fill=(78, 128, 52), width=max(2, int(5 * s)))
            trifoliate(c, tx, ty, ang, 0.13 * s)
    for tx, ty, ang, front in tips:          # feuilles de devant
        if front:
            d.line([(sx, sy), (tx, ty)], fill=(84, 138, 56), width=max(2, int(5 * s)))
            trifoliate(c, tx, ty, ang, 0.13 * s)
    for ang, ln, off in FLOWERS:             # hampes florales : bouton → fleur → fruit
        st = int(clamp(stage - off * 1.5, 0, 6))
        x0, y0 = stage_anchor(st)
        pivot(c, (None, st), x0, y0, sx + math.sin(math.radians(ang)) * 12 * s, sy, 0.34 * ln * s, -ang * 0.8)


# ============================================================ A. LA CUISINE : PAS UN FRUIT (0 → 3.55)
P_X, P_Y, P_W = 330, 1600, 260                   # plant en pot sur la planche (coordonnées de la photo)
K_X, K_Y, K_W = 770, 1610, 330                   # panier de fraises
F_X, F_Y = 555, 1655                             # la fraise qui sort du panier (devant, sur la planche)


def kitchen(t, cam, stage=6.0, wob=0.0, hop=None):
    w = cam.bg(KITCHEN)
    z = cam.z
    px, py = cam.p(P_X, P_Y)
    plant(w, px, py, P_W * z, stage, wob)
    kx, ky = cam.p(K_X, K_Y)
    shadow(w, kx, ky, K_W * z * 0.9, 70)
    ob(w, PANIER, kx, ky, K_W * z, anchor="bottom")
    return w


def s_intro(t):
    cam = Cam(lerp(1.15, 1.3, ease_io(t / 3.5)), 560, 1300)
    w = kitchen(t, cam, wob=math.sin(t * 2) * 3)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    hop = ease_io((t - 0.75) / 0.45)                 # une fraise saute du panier
    if hop > 0:
        kx, ky = cam.p(K_X - 30, K_Y - 260)
        fx, fy = cam.p(F_X, F_Y)
        x, y = lerp(kx, fx, hop), lerp(ky, fy, hop) - math.sin(math.pi * hop) * 260 * z
        if hop >= 1:
            shadow(w, fx, fy, 120 * z, 70)
        shake = math.sin(t * 60) * 6 * fade(t, 1.65, 2.0, 0.02, 0.2) if 1.65 < t < 2.0 else 0.0
        ob(w, GROSSE, x + shake, y, 150 * z, anchor="bottom", rot=-30 * (1 - hop))
        put(u, icon("cross", 150), fx + 120 * z, fy - 230 * z, life(t, 1.66, 3.5))
    w.alpha_composite(shade())
    title(u, "LA FRAISE ?", t, 0.05, 1.6, y=330, color=YEL, size=175)
    stamp(u, "PAS UN FRUIT !", 540, 340, t, 1.63, 2.1, RED, 140, -7)
    title(u, "ET CE N'EST PAS LE PIRE…", t, 2.15, None, y=330, size=108)
    return w, u


cue(0.05, "pop", 0.2)
cue(0.78, "whoosh", 0.16)
cue(1.2, "thud", 0.22)
cue(1.66, "alert2", 0.3)
cue(2.2, "rise", 0.18)


# ============================================================ B. LA BASE GONFLÉE DE LA FLEUR (3.55 → 7.3)
MORPH = [(5.1, 3), (5.85, 4), (6.2, 5), (6.55, 6)]      # (temps, étape) : fleur → sans pétales → vert → rouge


def s_base(t):
    zk = ease_io((t - 3.55) / 0.6)
    cam = Cam(lerp(1.3, 1.75, zk), lerp(560, F_X, zk), lerp(1300, 1420, zk))
    w = kitchen(t, cam)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    fx, fy = cam.p(F_X, F_Y)
    if t < 5.05:   # la partie rouge : la fraise est coupée en deux
        which, sc = swap((t - 3.7) / 0.3)
        shadow(w, fx, fy, 130 * z, 70)
        ob(w, GROSSE if which == 0 else COUPEE, fx, fy, (150 if which == 0 else 160) * z * sc, anchor="bottom")
        if t > 4.05:
            hl_ellipse(u, fx, fy - 105 * z, 95 * z, 110 * z, life(t, 4.1, 5.0))
            tag(u, "LA PARTIE ROUGE", 300, 640, t, 4.15, 5.0, rot=-5, size=52, string_to=(fx - 80 * z, fy - 140 * z))
    else:          # … c'est la base de la fleur qui gonfle
        st, t0 = 3, 5.05
        for tt, s_ in MORPH:
            if t >= tt:
                st, t0 = s_, tt
        g = life(t, 5.05, dur=0.3)
        pop_ = 1 + 0.12 * math.sin(math.pi * clamp((t - t0) / 0.25)) if t0 > 5.1 else 1.0
        x0, y0 = stage_anchor(st)
        shadow(w, fx, fy, 90 * z, 70)
        pivot(w, (None, st), x0, y0, fx, fy, 0.3 * z * g * pop_)
        if 5.85 < t < 6.6:   # les pétales tombent
            particles(w, t, 5.87, fx, fy - 190 * z, 10, 4, col=(250, 250, 245), size=10, up=150, dur=0.7)
        if t > 5.85:
            hy = fy - 0.3 * z * 620
            hl_ellipse(u, fx, hy, 0.3 * z * 230, 0.3 * z * 210, life(t, 5.9))
            tag(u, "BASE DE LA FLEUR", 290, 720, t, 5.95, None, rot=-5, size=50, string_to=(fx - 70 * z, hy - 40 * z))
        if t > 6.55:
            sparkles(u, t, 6.58, fx, fy - 190 * z, 200, 8, 6)
    w.alpha_composite(shade())
    title(u, "LA PARTIE ROUGE…", t, 3.6, 5.0, y=330, color=RED, size=150)
    title(u, "C'EST LA BASE", t, 5.05, 6.0, y=330, size=160)
    stamp(u, "DE LA FLEUR !", 540, 340, t, 6.05, None, GREEN, 140, -7)
    return w, u


cue(3.72, "chop", 0.3)
cue(5.07, "pop_hi", 0.2)
cue(5.87, "rustle", 0.18)
cue(6.22, "pop", 0.2)
cue(6.57, "pop_lo", 0.25)
cue(6.62, "sparkle", 0.2)


# ============================================================ C-D. LES VRAIS FRUITS = LES GRAINS, CHACUN UNE GRAINE (7.3 → 12.1)
@lru_cache(None)
def macro():
    return Image.open(os.path.join(IMG, B + "fraise_peau_macro.jpg")).convert("RGBA")


def lens_disc(c, cx, cy, r, zoom=1.0, off=(0, 0)):
    """Disque rempli de la photo macro de la peau (les grains), centré en (cx, cy)."""
    m = macro()
    side = int(2 * r)
    src = m.crop((0, 0, m.width, m.height))
    s = side * zoom / min(src.size)
    im = src.resize((int(src.width * s), int(src.height * s)), Image.BICUBIC)
    lay = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    lay.paste(im, (int(side / 2 - im.width / 2 + off[0] * s), int(side / 2 - im.height / 2 + off[1] * s)))
    mk = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mk).ellipse([0, 0, side - 1, side - 1], fill=255)
    lay.putalpha(mk)
    c.alpha_composite(lay, (int(cx - r), int(cy - r)))


def loupe(c, cx, cy, k, rot=15):
    vx, vy = (GLASS_C[0] - 512) * k, (GLASS_C[1] - 512) * k
    a = math.radians(rot)
    rx, ry = vx * math.cos(a) + vy * math.sin(a), -vx * math.sin(a) + vy * math.cos(a)
    place(c, LOUPE, FULL, k, 512, 512, cx - rx, cy - ry, 1.0, rot)


SX, SY = 540, TABLE + 30                         # grosse fraise sur fond beige
SW = 560
LX, LY = 600, 800                                # centre du verre de la loupe


def s_grains(t):
    w, u = new_layers(background("table"))
    s_ = life(t, 7.32, dur=0.35)
    shadow(w, SX, SY, SW * 0.7 * s_)
    ob(w, GROSSE, SX, SY, SW, s=s_, anchor="bottom")
    # la loupe arrive sur la peau (« les petits grains sur sa peau »)
    q = ease_out((t - 8.65) / 0.45)
    grow = ease_io((t - 10.25) / 0.45)               # puis on plonge dans la loupe
    if t > 8.65:
        r = lerp(GLASS_R * 1.25, 400, grow)
        cx, cy = lerp(1300, LX, q), lerp(1300, LY, q)
        cx, cy = lerp(cx, 540, grow), lerp(cy, 830, grow)
        lens_disc(w, cx, cy, r, zoom=lerp(1.0, 1.25, grow))
        if grow < 0.98:
            loupe(w, cx, cy, r / GLASS_R, 15)
        else:
            d = ImageDraw.Draw(w)
            d.ellipse([cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14], outline=DARK, width=26)
            d.ellipse([cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5], outline=(214, 170, 80), width=10)
        if 9.2 < t < 10.3:
            tag(u, "VRAIS FRUITS !", 290, 560, t, 9.25, None, rot=-5, size=54, string_to=(cx - 60, cy - 60))
    # « chaque grain cache une graine » : un grain s'ouvre, la graine apparaît
    if t > 10.7:
        gx, gy = 540 - 40, 830 - 15
        hl_ellipse(u, gx, gy, 62, 80, life(t, 10.75))
        a = life(t, 11.25, dur=0.35)
        if a > 0.01:
            d = ImageDraw.Draw(u)
            d.line([(gx + 70, gy - 40), (800, 690)], fill=WHITE, width=10)
            ob(u, AKENE, 860, 640, 200, s=a, rot=-20)
            tag(u, "UNE GRAINE", 860, 800, t, 11.35, None, rot=4, size=56)
    title(u, "LES VRAIS FRUITS ?", t, 7.35, 8.6, y=330, color=YEL, size=140)
    title(u, "LES PETITS GRAINS !", t, 8.65, 10.3, y=330, size=125)
    title(u, "CHAQUE GRAIN…", t, 10.35, 11.55, y=330, color=YEL, size=150)
    stamp(u, "CACHE UNE GRAINE !", 540, 340, t, 11.6, None, GREEN, 110, -6)
    return w, u


cue(7.35, "pop", 0.22)
cue(8.68, "whoosh", 0.16)
cue(9.27, "pop_hi", 0.18)
cue(10.3, "whoosh_up", 0.16)
cue(10.77, "pop", 0.18)
cue(11.3, "pop_hi", 0.22)
cue(11.65, "ding", 0.26)


# ============================================================ E. ENVIRON 200 FRUITS DANS UNE FRAISE (12.1 → 16.6)
@lru_cache(None)
def seeds():
    """Positions des grains (akènes jaunes) sur la photo de la grosse fraise, cadre 1024, du haut vers le bas."""
    a = np.asarray(img(GROSSE)).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    m = (al > 200) & (g > 110) & (r > 170) & (b < 120) & (g < 210)
    m[:230] = False
    from scipy import ndimage
    lab, n = ndimage.label(m)
    cs = ndimage.center_of_mass(m, lab, range(1, n + 1))
    sz = ndimage.sum(m, lab, range(1, n + 1))
    pts = [(c[1], c[0]) for c, s in zip(cs, sz) if 12 < s < 500]
    rng = np.random.default_rng(1)
    rng.shuffle(pts)
    return pts


CW = 440


def s_count(t):
    w, u = new_layers(background("table"))
    light_rays(w, 540, 400, t, 0.6)
    shadow(w, SX, SY, CW * 0.7)
    ob(w, GROSSE, SX, SY, CW, s=life(t, 12.12, dur=0.3), anchor="bottom")
    k = CW / (859 - 170)
    n_on = 0
    if t > 13.0:
        p = ease_in(clamp((t - 13.0) / 2.2))
        pts = seeds()
        n_on = int(p * len(pts))
        d = ImageDraw.Draw(u)
        for x, y in pts[:n_on]:
            X, Y = SX + (x - 514.5) * k, SY + (y - 968) * k
            d.ellipse([X - 9, Y - 9, X + 9, Y + 9], fill=YEL + (235,), outline=DARK, width=3)
    if t > 12.95:   # compteur
        val = int(round(200 * ease_in(clamp((t - 13.0) / 2.2))))
        put(u, text_img(str(val), F_TITLE, 210, YEL, 10, DARK, 8, DARK), 540, 570, life(t, 12.95))
        put(u, text_img("FRUITS", F_TITLE, 90, WHITE, 8, DARK, 6, DARK), 540, 700, life(t, 13.0))
    if t > 15.25:
        sparkles(u, t, 15.3, 540, 900, 380, 12, 9)
    title(u, "DANS UNE SEULE FRAISE…", t, 12.15, 15.15, y=330, size=110)
    stamp(u, "ENVIRON 200 !", 540, 340, t, 15.2, None, RED, 140, -6)
    return w, u


cue(12.15, "pop", 0.22)
for _k in range(9):
    cue(13.05 + 2.1 * (_k / 9) ** 0.6, "tick", 0.15)
cue(15.22, "alert1", 0.28)
cue(15.32, "success", 0.24)


# ============================================================ F. PLUS JAMAIS PAREILLE + ABONNE-TOI (16.6 → fin)
def s_end(t):
    cam = Cam(lerp(1.45, 1.25, ease_io((t - 16.6) / 0.7)), 560, 1320)
    stage = lerp(2.0, 6.0, ease_io((t - 16.75) / 1.6))    # le plant fleurit et donne ses fraises en accéléré
    w = kitchen(t, cam, stage, wob=math.sin(t * 2) * 3)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    w.alpha_composite(shade())
    px, py = cam.p(P_X, P_Y - 230)
    if t > 18.3:
        sparkles(u, t, 18.35, px, py, 230, 10, 7)
    if t > 18.75:
        clicked = t > 20.2
        btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
        press = 1 - 0.08 * math.sin(math.pi * clamp((t - 20.15) / 0.15))
        put(u, btn, 540, 760, life(t, 18.8) * press)
        if t > 19.7:
            kk = ease_out((t - 19.7) / 0.4)
            put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1000, 800, kk), 1)
        put(u, logo_img(230), 540, 540, life(t, 20.75, dur=0.45))
        sparkles(u, t, 20.85, 540, 540, 200, 10, 12)
    title(u, "MAINTENANT…", t, 16.65, 17.6, y=330, size=165)
    stamp(u, "PLUS JAMAIS PAREILLE !", 540, 340, t, 17.65, 18.7, GREEN, 100, -6)
    title(u, "PLUS D'ASTUCES ?", t, 18.75, None, y=330, color=YEL, size=135)
    return w, u


cue(16.68, "whoosh", 0.16)
cue(17.0, "pop_hi", 0.16)
cue(17.5, "pop_hi", 0.16)
cue(17.68, "ding", 0.25)
cue(18.35, "sparkle", 0.2)
cue(20.18, "click", 0.45)
cue(20.85, "sparkle", 0.22)

SCENES = [
    (0.0, 3.55, s_intro),
    (3.55, 7.3, s_base),
    (7.3, 12.1, s_grains),
    (12.1, 16.6, s_count),
    (16.6, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
