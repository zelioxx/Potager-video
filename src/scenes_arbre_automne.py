"""Storyboard « Planter un arbre en automne » (voix : assets/audio/arbre_automne/voix.wav, volume d'origine).

Décors fournis : le même jardin (pelouse, deux arbres, maisons du village) au printemps, en été (pelouse grillée),
en automne et sous la neige. Objets : arbre feuillu / nu avec ses racines, pelle, tas de terre (planches fournies,
agrandies ×4 puis détourées). Le jeune arbre est planté au milieu-droite de la pelouse.
0–5.4     printemps → été : l'arbre planté au printemps se dessèche ; « tu as raté la bonne date ! »
5.4–9.4   en coupe, l'été : de toutes petites racines, la terre craquelée sous la chaleur.
9.4–14.8  en coupe, l'automne puis l'hiver : terre tiède et humide, les racines poussent tranquillement.
14.8–20.0 le jardin d'automne : « à la Sainte-Catherine, tout bois prend racine » (25 novembre).
20.0–24.2 on creuse un grand trou, on plante, on arrose, même s'il pleut.
24.2–26.8 jamais dans une terre gelée (la pelle rebondit) ou détrempée (flaque).
26.8–fin  au printemps, il démarre d'un coup ; bouton S'abonner et logo.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, put, title, life, fade, ease_out, ease_io,
                 ease_in, ease_out_back, clamp, lerp, icon, tag, button_img, particles, text_img, F_TITLE, F_BLACK,
                 light_rays, aa)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade, shadow, photo
from scenes_banane import ob
from scenes_fumier import Cam, decor, snowfall, rainfall
from scenes_arrosage_soir import watering, thermo_cold

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
PRINTEMPS, ETE, AUTOMNE, HIVER = ("decor_jardin_pelouse_arbres.webp", "decor_jardin_ete_sec.webp",
                                  "decor_jardin_automne.webp", "decor_jardin_neige.jpg")
COUPE_SOL = "tulipes_fond_coupe_20cm.png"
FEUILLU, NU = B + "arbre_feuillu_racines", B + "arbre_nu_racines"
PELLE, PELLE_P, TAS = B + "pelle_droite", B + "pelle_penchee", B + "tas_terre"
CAN = B + "arrosoir_zinc"
LEAVES = [B + "feuille_morte_a", B + "feuille_morte_b", "feuilles/feuille_a", "feuilles/feuille_b"]

SPOT = (720, 1460)                               # le jeune arbre, au milieu-droite de la pelouse (plein écran)
TREE_H = 520                                     # hauteur du jeune arbre hors sol (zoom 1)


@lru_cache(None)
def _img(name):
    return Image.open(os.path.join(IMG, name + ".png")).convert("RGBA")


@lru_cache(None)
def collar(name):
    """Collet de l'arbre (là où le tronc rejoint les racines), en pixels du cadre : la rangée la plus étroite entre
    le houppier et l'éventail des racines (on cherche dans les 30 % du bas)."""
    a = np.asarray(_img(name))[..., 3] > 100
    ys = np.nonzero(a.any(1))[0]
    y0, y1 = ys.min(), ys.max()
    best = None
    for y in range(int(y0 + (y1 - y0) * 0.5), int(y0 + (y1 - y0) * 0.8)):
        xs = np.nonzero(a[y])[0]
        if len(xs) == 0:
            continue
        wdt = xs.max() - xs.min()
        if best is None or wdt < best[0]:
            best = (wdt, y, (xs.max() + xs.min()) / 2)
    # le collet : la dernière rangée « tronc » avant que les racines ne s'écartent
    wdt0, yb, xc = best
    for y in range(yb, int(y1)):
        xs = np.nonzero(a[y])[0]
        if len(xs) and xs.max() - xs.min() > wdt0 * 2.2:
            return xc, y, y0, y1
    return xc, yb, y0, y1


@lru_cache(64)
def tree_parts(name, h_above, roots_q=1.0, dry=0.0, only_roots=False):
    """L'arbre mis à l'échelle (h_above = hauteur du tronc+houppier) : (image, x collet, y collet).
    roots_q : part visible des racines (0 = coupées net au collet, 1 = toutes) ; dry : feuillage desséché."""
    im = _img(name)
    xc, yc, y0, y1 = collar(name)
    k = h_above / (yc - y0)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    xc, yc, y1 = xc * k, yc * k, y1 * k
    a = np.asarray(im).astype(np.float32)
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    if roots_q < 0.999:   # racines : révélées depuis le collet, sur un rayon qui grandit
        rmax = (y1 - yc) * 1.08 * roots_q
        d = np.hypot((xx - xc) * 0.9, yy - yc)
        keep = (yy < yc + 2) | (d < rmax)
        a[..., 3] = np.where(keep, a[..., 3], a[..., 3] * np.clip(1 - (d - rmax) / 12, 0, 1))
    if only_roots:
        a[..., 3] = np.where(yy < yc + 2, 0, a[..., 3])
    if dry > 0.01:        # feuillage qui jaunit/brunit (au-dessus du collet)
        rgb = a[..., :3]
        green = (rgb[..., 1] > rgb[..., 0] + 8) & (yy < yc)
        tgt = np.array([150, 112, 55], np.float32)
        rgb[green] = rgb[green] * (1 - 0.75 * dry) + tgt * 0.75 * dry
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA"), xc, yc


def tree(c, name, X, Y, h_above, roots_q=0.0, dry=0.0, s=1.0, sway=0.0, only_roots=False):
    """Pose l'arbre avec son collet en (X, Y) (au ras du sol)."""
    if s <= 0.01:
        return
    im, xc, yc = tree_parts(name, int(h_above * s) // 2 * 2, round(roots_q, 2), round(dry, 2), only_roots)
    if sway:
        im = im.rotate(sway, resample=Image.BICUBIC, center=(xc, yc))
    c.alpha_composite(im, (int(round(X - xc)), int(round(Y - yc))))


def falling_leaves(c, t, a=1.0, n=14, seed=4):
    if a <= 0.01:
        return
    r = np.random.default_rng(seed)
    for i in range(n):
        sp = r.uniform(0.18, 0.3)
        p = (t * sp + i / n) % 1.0
        x = r.uniform(0, W) + math.sin(t * 1.5 + i) * 60
        y = -100 + p * (H + 200)
        ob(c, LEAVES[i % len(LEAVES)], x, y, r.uniform(50, 85), rot=t * 90 * (1 if i % 2 else -1) + i * 40,
           alpha=a)


# ============================================================ A. PRINTEMPS → ÉTÉ : IL SÈCHE (0 → 5.4)
def s_garden(t):
    k = ease_io(clamp((t - 0.3) / 2.2))
    cam = Cam(lerp(1.05, 1.45, k), lerp(540, SPOT[0] - 60, k), lerp(1000, SPOT[1] - 330, k))
    z = cam.z
    q = ease_io(clamp((t - 2.4) / 0.6))           # « pendant l'été » : la pelouse grille
    w = decor(cam, PRINTEMPS, ETE, q)
    x, y = cam.p(*SPOT)
    shadow(w, x, y, 200 * z, 70)
    dry = ease_io(clamp((t - 2.7) / 1.4))
    droop = -4 * dry + math.sin(t * 2) * 0.6
    tree(w, FEUILLU, x, y, TREE_H * z, 0.0, dry, s=ease_out_back(clamp((t - 0.15) / 0.4), 1.5), sway=droop)
    if t < 4.6:   # au printemps, les fleurs éclosent… puis fanent une à une avec l'été
        blossoms(w, x, y, TREE_H * z, t, 0.4, z, spread=1.6, t_off=2.5, off_spread=1.5)
    if q > 0.01:
        light_rays(w, 900, 0, t, q)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 2.6:
        put(u, icon("sun", 190), 900, 620, life(t, 2.65, 5.35))
        put(u, text_img("35 °C", F_TITLE, 100, RED, stroke=7, stroke_fill=DARK), 900, 770, life(t, 2.75, 5.35))
    title(u, "PLANTÉ AU PRINTEMPS…", t, 0.05, 2.5, y=330, color=GREEN, size=118)
    title(u, "IL MEURT EN ÉTÉ ?", t, 2.55, 4.2, y=330, color=WHITE, size=140)
    stamp(u, "MAUVAISE DATE !", 540, 340, t, 4.25, None, RED, 130, -6)
    return w, u


cue(0.18, "pop", 0.14)
cue(2.5, "whoosh_up", 0.1)
cue(2.68, "sparkle", 0.1)
cue(3.3, "fail", 0.16)
cue(4.27, "alert1", 0.2)


# ============================================================ B / C. EN COUPE : LES RACINES (5.4 → 14.8)
ROOTS_H = 1000                                   # échelle du chevelu de racines (≈ taille d'origine de la photo : net)
GROUND = 880                                     # ligne du sol dans la vue en coupe
CUT_X = 540


@lru_cache(8)
def section_bg(season):
    """Vue en coupe : en haut, le jardin (bande de la photo de la saison) ; en dessous, la terre (photo)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    top = photo({"ete": ETE, "automne": AUTOMNE, "hiver": HIVER, "printemps": PRINTEMPS}[season])
    oy = 1170 - GROUND if season != "hiver" else 1240 - GROUND
    img.alpha_composite(top.crop((0, oy, W, oy + GROUND)), (0, 0))
    soil = photo(COUPE_SOL).crop((0, 1200, W, 1920))          # de la terre, sans le trou ni la légende
    soil2 = soil.transpose(Image.FLIP_TOP_BOTTOM)
    img.alpha_composite(soil, (0, GROUND))
    img.alpha_composite(soil2, (0, GROUND + soil.height))
    # le bord de la coupe : une lèvre de terre plus claire et une ombre portée
    d = ImageDraw.Draw(img)
    d.rectangle([0, GROUND - 3, W, GROUND + 4], fill=(96, 70, 48, 255))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([0, GROUND + 4, W, GROUND + 40], fill=(0, 0, 0, 110))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    return img


@lru_cache(None)
def cracks():
    """Fissures de terre sèche (réseau ramifié, déterministe)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    r = np.random.default_rng(7)
    for i in range(16):
        x, y = r.uniform(0, W), r.uniform(GROUND + 30, H)
        ang = r.uniform(0, 2 * math.pi)
        wd = r.uniform(5, 11)
        for _ in range(int(r.uniform(6, 14))):
            ang += r.uniform(-0.7, 0.7)
            L = r.uniform(30, 90)
            nx, ny = x + math.cos(ang) * L, y + math.sin(ang) * L
            d.line([(x, y), (nx, ny)], fill=(28, 18, 12, 255), width=int(wd))
            if r.random() < 0.35:
                b = ang + r.choice([-1, 1]) * r.uniform(0.6, 1.2)
                d.line([(nx, ny), (nx + math.cos(b) * L * 0.6, ny + math.sin(b) * L * 0.6)], fill=(28, 18, 12, 255),
                       width=max(2, int(wd * 0.5)))
            x, y, wd = nx, ny, max(2, wd * 0.85)
    return lay.filter(ImageFilter.GaussianBlur(0.8))


def soil_tone(c, dry=0.0, wet=0.0):
    """Terre sèche (pâle, craquelée) ou humide (sombre, brillante), sous la ligne du sol."""
    if dry > 0.01:
        ov = Image.new("RGBA", (W, H - GROUND), (205, 170, 120, int(95 * dry)))
        c.alpha_composite(ov, (0, GROUND + 5))
        cr = cracks().copy()
        cr.putalpha(cr.getchannel("A").point(lambda v: int(v * dry)))
        c.alpha_composite(cr)
    if wet > 0.01:
        ov = Image.new("RGBA", (W, H - GROUND), (15, 10, 8, int(90 * wet)))
        c.alpha_composite(ov, (0, GROUND + 5))
        d = ImageDraw.Draw(c)
        r = np.random.default_rng(3)
        for _ in range(60):   # petites perles d'humidité
            x, y = r.uniform(0, W), r.uniform(GROUND + 30, H)
            rr = r.uniform(3, 6)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(170, 205, 230, int(120 * wet)))


def s_section(t):
    summer = t < 9.4
    if summer:
        season = "ete"
    elif t < 12.5:
        season = "automne"
    else:
        season = "hiver"
    w = section_bg(season).copy()
    zoomk = 1.0                                   # pas de zoom dans la coupe : les racines restent nettes
    if summer:
        soil_tone(w, dry=ease_io(clamp((t - 6.0) / 1.6)))
        roots = 0.28 + 0.04 * clamp((t - 5.6) / 2.5)
        tree(w, FEUILLU, CUT_X, GROUND, ROOTS_H, roots, only_roots=True)
        tree(w, FEUILLU, CUT_X, GROUND, 720, 0.0, dry=0.25 * clamp((t - 7.5) / 1.5))
        light_rays(w, 900, 0, t, 1.0)
    else:
        wet = fade(t, 9.5, None, 0.6)
        soil_tone(w, wet=wet)
        # les racines s'installent tranquillement, tout l'hiver
        # en automne / hiver : l'arbre sans feuilles, et le même chevelu de racines qui s'étend
        roots = 0.32 + 0.68 * ease_io(clamp((t - 12.6) / 2.0))
        tree(w, FEUILLU, CUT_X, GROUND, ROOTS_H, roots, only_roots=True)      # chevelu agrandi (vue en coupe)
        tree(w, NU, CUT_X, GROUND, 720, 0.0)
        if season == "automne":
            falling_leaves(w, t, fade(t, 9.4, 12.5, 0.3, 0.2), n=10)
        else:
            snowfall(w, t, 1.0, 90)
            # un voile de neige posé sur le sol
            d = ImageDraw.Draw(w)
            d.rectangle([0, GROUND - 14, W, GROUND + 2], fill=(245, 248, 255, 255))
    if zoomk > 1.001:
        cw, ch = W / zoomk, H / zoomk
        w = w.resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) * 0.55, (W + cw) / 2, (H - ch) * 0.55 + ch))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if summer:
        if t > 6.9:
            tag(u, "PETITES RACINES", 300, 1300, t, 6.95, 9.3, rot=-5, size=54)
        if t > 8.4:
            put(u, icon("thermo", 150), 900, 620, life(t, 8.45, 9.3))
        title(u, "AU PRINTEMPS…", t, 5.45, 6.9, y=330, color=GREEN, size=160)
        title(u, "PAS LE TEMPS DE S'ENRACINER", t, 6.95, 8.4, y=330, color=WHITE, size=92)
        title(u, "AVANT LES CHALEURS !", t, 8.45, None, y=330, color=RED, size=120)
    else:
        if 10.4 < t < 12.4:
            put(u, icon("thermo", 140), 170, 1200, life(t, 10.45, 12.35))
            tag(u, "TIÈDE", 330, 1200, t, 10.5, 12.35, rot=-5, size=58)
            put(u, icon("drop", 140), 900, 1200, life(t, 11.6, 12.35))
            tag(u, "HUMIDE", 740, 1320, t, 11.65, 12.35, rot=5, size=58)
        if t > 13.6:
            tag(u, "RACINES", 300, 1480, t, 13.65, None, rot=-5, size=60)
            sparkles(u, t, 13.7, CUT_X, 1150, 360, 12, 6)
        title(u, "MAIS EN AUTOMNE…", t, 9.45, 10.4, y=330, color=YEL, size=150)
        title(u, "TERRE TIÈDE ET HUMIDE", t, 10.45, 12.45, y=330, color=WHITE, size=110)
        title(u, "TOUT L'HIVER, IL S'INSTALLE", t, 12.5, None, y=330, color=BLUE, size=96)
    return w, u


cue(5.45, "whoosh", 0.12)
cue(6.2, "crunch", 0.16)
cue(8.47, "alert2", 0.16)
cue(9.45, "whoosh", 0.12)
cue(9.6, "rustle", 0.14)
cue(11.7, "plop", 0.14)
cue(12.5, "whoosh_up", 0.1)
cue(13.7, "rise", 0.16)


# ============================================================ D. LA SAINTE-CATHERINE (14.8 → 20.0)
@lru_cache(None)
def calendar_img(size=380):
    """Feuille d'éphéméride « 25 NOVEMBRE »."""
    w_, h_ = size, int(size * 1.12)
    k = 3

    def f(d, kk, _):
        d.rounded_rectangle([10 * kk, 18 * kk, (w_ - 2) * kk, (h_ - 2) * kk], radius=26 * kk, fill=(0, 0, 0, 90))
        d.rounded_rectangle([0, 0, (w_ - 12) * kk, (h_ - 14) * kk], radius=26 * kk, fill=CREAM, outline=DARK,
                            width=6 * kk)
        d.rounded_rectangle([0, 0, (w_ - 12) * kk, int(h_ * 0.27) * kk], radius=26 * kk, fill=RED)
        d.rectangle([0, int(h_ * 0.15) * kk, (w_ - 12) * kk, int(h_ * 0.27) * kk], fill=RED)
        d.rounded_rectangle([0, 0, (w_ - 12) * kk, (h_ - 14) * kk], radius=26 * kk, outline=DARK, width=6 * kk)
    im = aa(w_, h_, f, k)
    m = text_img("NOVEMBRE", F_BLACK, int(size * 0.13), WHITE)
    im.alpha_composite(m, ((w_ - 12 - m.width) // 2, int(h_ * 0.135 - m.height / 2)))
    n = text_img("25", F_TITLE, int(size * 0.5), DARK)
    im.alpha_composite(n, ((w_ - 12 - n.width) // 2, int(h_ * 0.6 - n.height / 2)))
    return im


def s_catherine(t):
    cam = Cam(lerp(1.05, 1.15, clamp((t - 14.8) / 5.2)), 540, 1000)
    w = decor(cam, AUTOMNE)
    falling_leaves(w, t, 1.0, n=12, seed=6)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    k = ease_out_back(clamp((t - 17.4) / 0.45), 1.6)
    if k > 0:
        put(u, calendar_img(), 540, 1050, k, rot=-4 + 3 * math.sin(t * 2))
    title(u, "LES ANCIENS LE DISAIENT…", t, 14.85, 17.35, y=330, color=WHITE, size=100)
    title(u, "À LA SAINTE-CATHERINE…", t, 17.4, 18.7, y=330, color=YEL, size=108)
    stamp(u, "TOUT BOIS PREND RACINE !", 540, 340, t, 18.75, None, GREEN, 92, -6)
    return w, u


cue(14.87, "whoosh", 0.12)
cue(15.0, "rustle", 0.14)
cue(17.45, "pop", 0.18)
cue(18.78, "success", 0.2)


# ============================================================ E. PLANTE-LE : UN GRAND TROU, ARROSE BIEN (20.0 → 24.2)
CAM_PLANT = (1.6, SPOT[0] - 40, SPOT[1] - 260)


def hole(c, cam, q, wet=0.0):
    """Le trou dans la pelouse : ellipse sombre avec un bord de terre retournée."""
    if q <= 0.01:
        return
    x, y = cam.p(*SPOT)
    rx, ry = 150 * cam.z * q, 48 * cam.z * q
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([x - rx * 1.25, y - ry * 1.3, x + rx * 1.25, y + ry * 1.25], fill=(92, 64, 42, 255))
    d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=(38, 25, 17, 255))
    d.ellipse([x - rx * 0.8, y - ry * 0.85, x + rx * 0.8, y + ry * 0.3], fill=(22, 14, 10, 255))
    if wet > 0.01:
        d.ellipse([x - rx * 0.7, y - ry * 0.35, x + rx * 0.7, y + ry * 0.55], fill=(120, 150, 170, int(160 * wet)))
    c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.5)))


def s_plant(t, cam=None):
    k = ease_io(clamp((t - 20.0) / 0.6))
    cam = cam or Cam(*[lerp(a, b, k) for a, b in zip((1.15, 540, 1000), CAM_PLANT)])
    z = cam.z
    w = decor(cam, AUTOMNE)
    x, y = cam.p(*SPOT)
    # la pelle creuse (deux coups), la terre s'empile à côté, le trou s'agrandit
    dig = clamp((t - 20.35) / 1.1)
    hole(w, cam, ease_out(dig), wet=fade(t, 22.7, None, 0.4))
    pile = ease_out(clamp((t - 20.6) / 0.8))
    if pile > 0.01:
        ob(w, TAS, x - 260 * z, y + 20 * z, 280 * z * pile, anchor="bottom")
    if 20.2 < t < 21.6:
        ph = ((t - 20.35) / 0.55) % 1.0
        stab = math.sin(math.pi * ph)
        sx, sy = x + 40 * z, y - 120 * z + 60 * z * stab
        ob(w, PELLE_P, sx, sy - 250 * z, 330 * z, rot=lerp(-8, 14, stab))
        if stab > 0.9:
            particles(w, t, t - 0.02, x, y, 8, int(t * 7), col=(80, 55, 35), size=6 * z, up=160, spread=200, dur=0.3)
    # l'arbre (racines nues) descend dans le trou
    if t > 21.5:
        q = ease_out(clamp((t - 21.5) / 0.45))
        tree(w, NU, x, lerp(y - 500 * z, y, q), TREE_H * z, 0.0)
        if t > 21.95:   # on rebouche : la terre autour du pied
            fill = ease_out(clamp((t - 21.95) / 0.4))
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ov).ellipse([x - 120 * z, y - 30 * z, x + 120 * z, y + 30 * z],
                                       fill=(70, 48, 32, int(235 * fill)))
            w.alpha_composite(ov.filter(ImageFilter.GaussianBlur(2)))
            tree(w, NU, x, y, TREE_H * z, 0.0)
    # « arrose bien »
    if 22.4 < t < 23.7:
        s = 0.62 * z
        cin = ease_out(clamp((t - 22.4) / 0.3))
        cout = ease_in(clamp((t - 23.4) / 0.3))
        tilt = -28 * ease_io(clamp((t - 22.6) / 0.2)) * (1 - cout)
        cx = lerp(-400, x - 230 * s, cin) - 700 * cout
        cy = y - 170 * s
        ob(w, CAN, cx, cy, 420 * s, rot=tilt, flip=True)
        watering(w, t, fade(t, 22.75, 23.45, 0.06, 0.1), (cx + 188 * s, cy + 10 * s), y - 4, s)
    rainfall(w, t, fade(t, 23.35, None, 0.3) * 0.9)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 21.0:
        tag(u, "GRAND TROU", 300, 1250, t, 21.05, 22.35, rot=-5, size=58)
    title(u, "PLANTE-LE MAINTENANT !", t, 20.05, 21.0, y=330, color=YEL, size=112)
    title(u, "DANS UN GRAND TROU", t, 21.05, 22.35, y=330, color=WHITE, size=118)
    title(u, "ARROSE BIEN…", t, 22.4, 23.3, y=330, color=BLUE, size=160)
    title(u, "MÊME S'IL PLEUT !", t, 23.35, None, y=330, color=WHITE, size=140)
    return w, u


cue(20.05, "whoosh", 0.12)
for _i in range(2):
    cue(20.55 + _i * 0.55, "chop", 0.14)
cue(21.75, "thud", 0.2)
cue(22.0, "rustle", 0.12)
cue(22.75, "pour", 0.2)
cue(23.4, "rain", 0.2)


# ============================================================ F. JAMAIS GELÉE NI DÉTREMPÉE (24.2 → 26.8)
NSPOT = (560, 1560)                              # sur la pelouse enneigée


def s_never(t):
    if t < 25.85:   # terre gelée : la pelle rebondit
        cam = Cam(1.5, NSPOT[0], NSPOT[1] - 240)
        z = cam.z
        w = decor(cam, HIVER)
        x, y = cam.p(*NSPOT)
        b = abs(math.sin((t - 24.4) * 9)) * math.exp(-max(0, t - 24.4) * 2.5) if t > 24.4 else 0
        ob(w, PELLE_P, x + 40 * z, y - 260 * z - 70 * z * b, 330 * z, rot=8 + 10 * b)
        if 24.4 < t < 24.7:
            particles(w, t, 24.42, x, y, 10, 5, col=(240, 245, 255), size=6 * z, up=180, spread=220, dur=0.3)
        snowfall(w, t, 0.8)
        lbl, col = "TERRE GELÉE", BLUE
    else:           # terre détrempée : une grande flaque
        cam = Cam(*CAM_PLANT)
        z = cam.z
        w = decor(cam, AUTOMNE)
        x, y = cam.p(*SPOT)
        pud = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        q = ease_out(clamp((t - 25.9) / 0.4))
        d = ImageDraw.Draw(pud)
        d.ellipse([x - 300 * z * q, y - 70 * z * q, x + 300 * z * q, y + 70 * z * q], fill=(110, 130, 140, 200))
        d.ellipse([x - 200 * z * q, y - 40 * z * q, x + 60 * z * q, y + 10 * z * q], fill=(200, 215, 225, 120))
        w.alpha_composite(pud.filter(ImageFilter.GaussianBlur(3)))
        rainfall(w, t, 0.9)
        lbl, col = "TERRE DÉTREMPÉE", BLUE
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    put(u, icon("nosign", 300), 540, 1050, life(t, 24.45 if t < 25.85 else 25.95, 25.8 if t < 25.85 else None))
    tag(u, lbl, 540, 1290, t, 24.5 if t < 25.85 else 26.0, 25.8 if t < 25.85 else None, rot=-4, size=60)
    title(u, "MAIS JAMAIS…", t, 24.25, None, y=330, color=RED, size=170)
    return w, u


cue(24.27, "whoosh", 0.12)
cue(24.42, "thud", 0.22)
cue(24.47, "fail", 0.16)
cue(25.87, "whoosh", 0.1)
cue(25.95, "splash", 0.16)


@lru_cache(8)
def blossom_spots(h_above):
    """Points du houppier (dans l'image de l'arbre feuillu à cette taille) où poser des fleurs."""
    im, xc, yc = tree_parts(FEUILLU, h_above, 0.0, 0.0)
    a = np.asarray(im)
    r = np.random.default_rng(12)
    ys, xs = np.nonzero((a[..., 3] > 200) & (np.arange(a.shape[0])[:, None] < yc * 0.72))
    idx = r.choice(len(xs), size=min(46, len(xs)), replace=False)
    return [(xs[i] - xc, ys[i] - yc, r.uniform(0.75, 1.25), r.uniform(0, 0.8), r.integers(0, 3)) for i in idx]


@lru_cache(16)
def blossom_img(rad, kind):
    """Petite fleur : la vraie photo d'une fleur blanche à 5 pétales (banque/fleur_fraisier), réduite, plus ou
    moins rosée, légèrement tournée."""
    im = _img(B + "fleur_fraisier")
    im = im.crop(im.getbbox()).resize((rad * 2, rad * 2), Image.LANCZOS)
    if kind:
        a = np.asarray(im).astype(np.float32)
        tint = np.array([255, 205, 222], np.float32) if kind == 1 else np.array([250, 180, 205], np.float32)
        white = (a[..., :3].min(2) > 170)[..., None]
        a[..., :3] = np.where(white, a[..., :3] * 0.55 + tint * 0.45, a[..., :3])
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    return im.rotate(kind * 23, resample=Image.BICUBIC)


def blossoms(c, X, Y, h_above, t, t0, z, spread=2.0, t_off=None, off_spread=1.4):
    """Le printemps : des fleurs qui éclosent tranquillement, une à une, étalées sur `spread` secondes.
    Si t_off est donné, elles fanent aussi une à une (chacune à son moment) : elles se détachent, glissent un peu
    vers le bas en tournant et s'effacent."""
    if t < t0:
        return
    r = np.random.default_rng(31)
    for i, (dx, dy, sc, delay, kind) in enumerate(blossom_spots(int(h_above) // 2 * 2)):
        d_on = delay / 0.8 * spread                      # ordre d'éclosion propre à chaque fleur
        q = ease_out_back(clamp((t - t0 - d_on) / 0.45), 1.6)
        if q <= 0.02:
            continue
        rad = max(4, int(9 * z * sc))
        a, fy, rot = 1.0, 0.0, kind * 23
        if t_off is not None:
            d_off = t_off + r.uniform(0, off_spread)
            f = clamp((t - d_off) / 0.6)
            if f >= 1:
                continue
            a, fy, rot = 1 - f, 90 * z * f * f, rot + 140 * f
        put(c, blossom_img(rad, int(kind)), X + dx + 15 * z * math.sin(i) * (fy > 0) * fy / (90 * z + 1e-6),
            Y + dy + fy, q, rot=rot - kind * 23, alpha=a)


# ============================================================ G. AU PRINTEMPS, IL DÉMARRE D'UN COUP (26.8 → fin)
def s_spring(t, end=False):
    k = ease_io(clamp((t - 26.85) / 1.2))
    cam = Cam(*[lerp(a, b, k) for a, b in zip(CAM_PLANT, (1.1, 600, 1050))])
    z = cam.z
    w = decor(cam, PRINTEMPS)
    x, y = cam.p(*SPOT)
    shadow(w, x, y, 200 * z, 70)
    g = ease_out_back(clamp((t - 28.25) / 0.45), 1.8)
    if t < 28.25:
        tree(w, NU, x, y, TREE_H * z, 0.0)
    else:
        h = TREE_H * z * (0.9 + 0.1 * g)
        tree(w, FEUILLU, x, y, h, 0.0)
        blossoms(w, x, y, h, t, 28.3, z, spread=1.8)
    # une mésange vient se poser dans l'arbre en fleurs
    if t > 29.0:
        from scenes_oiseaux_hiver import flight, bird, PROFIL
        px, py = x + 70 * z, y - TREE_H * z * 0.55
        if t < 29.6:
            flight(w, W + 150, 250, px, py, (t - 29.0) / 0.6, lerp(160, 95 * z, (t - 29.0) / 0.6), t, flip=True)
        else:
            bird(w, PROFIL, px, py, 95 * z, flip=True, t=t, hop=0.15)
    # des pétales qui volent dans la brise
    if t > 28.6:
        r = np.random.default_rng(9)
        for i in range(12):
            p = ((t - 28.6) * r.uniform(0.15, 0.3) + i / 12) % 1.0
            px_ = x + r.uniform(-200, 500) * z * 0.6 - p * 300
            py_ = y - TREE_H * z * 0.8 + p * 600 * z * 0.6 + math.sin(t * 3 + i) * 20
            put(w, blossom_img(max(4, int(6 * z)), i % 3), px_, py_, 0.8, rot=t * 80 + i * 30,
                alpha=fade(t, 28.6, None, 0.5) * math.sin(math.pi * p))
    light_rays(w, 900, 0, t, 1.0)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if 28.25 < t < 29.6:
        sparkles(u, t, 28.27, x, y - 300 * z, 330, 14, 4, dur=1.2)
    if not end:
        title(u, "ET AU PRINTEMPS…", t, 26.85, 28.2, y=330, color=GREEN, size=150)
        stamp(u, "IL DÉMARRE D'UN COUP !", 540, 340, t, 28.25, None, GREEN, 96, -6)
        return w, u
    clicked = t > 30.85
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 30.8) / 0.15))
    put(u, btn, 540, 1420, life(t, 29.6) * press)
    if t > 30.3:
        kk = ease_out((t - 30.3) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1670, 1460, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 31.9, dur=0.45))
    sparkles(u, t, 32.0, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 29.5, 31.85, y=330, color=YEL, size=135)
    return w, u


cue(26.87, "bird", 0.16)
cue(28.27, "pop_lo", 0.2)
cue(28.3, "success", 0.2)
cue(28.6, "sparkle", 0.14)
cue(29.05, "bird", 0.16)
cue(29.55, "pop_lo", 0.16)
cue(30.88, "click", 0.3)
cue(32.0, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 5.4 - SHIFT, _sh(s_garden)),
    (5.4 - SHIFT, 14.8 - SHIFT, _sh(s_section)),
    (14.8 - SHIFT, 20.0 - SHIFT, _sh(s_catherine)),
    (20.0 - SHIFT, 24.2 - SHIFT, _sh(s_plant)),
    (24.2 - SHIFT, 26.8 - SHIFT, _sh(s_never)),
    (26.8 - SHIFT, 29.45 - SHIFT, _sh(s_spring)),
    (29.45 - SHIFT, 99.0, _sh(lambda t: s_spring(t, end=True))),
]

TRAPS = []
