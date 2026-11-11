"""Storyboard « Du gland au chêne » (voix : assets/audio/gland/voix.mp3).

Le volume de la voix est gardé tel qu'envoyé (aucun mastering, cf. render.py « af ») ; bruitages sous la voix
(niveau validé sur la vidéo « arroser le soir »).
0–4.65   le chemin dans la forêt (photo fournie) : un gland tombe lentement, la caméra le suit, « toc » ; zoom doux,
         une main le ramasse, dézoom lent sur la promenade ; « un chêne de 300 ans » : un grand chêne pousse derrière.
4.65–8.15 la table du salon, vue à la 1re personne : les glands tombent sur la table ; « trie tes glands » (« ? »).
8.15–14.45 le bol en verre (photo fournie) : on les plonge ; ceux qui flottent sont vides → poubelle ; ceux qui
         coulent, on les garde.
14.45–17.55 le pot profond coupé en deux : le gland est planté à 2 cm (règle) ; « pot profond » (flèche).
17.55–24.95 dehors, dans le coin contre le vieux mur aux outils : tout l'hiver (neige) ; on arrose, jamais sec ; au printemps la neige fond,
         le soleil revient et le premier chêne sort de terre.
24.95–fin le salon : le petit chêne sur la table, bouton S'abonner et logo.
"""
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, put, title, life, fade, ease_out, ease_io, ease_in,
                 ease_out_back, clamp, lerp, icon, tag, button_img, particles, text_img, F_TITLE, hl_ellipse, measure,
                 light_rays)
from scenes import sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp
from scenes_citron import photo, shade, zoomed, shadow, swap
from scenes_banane import ob
from scenes_arrosage_soir import watering, snow_badge, thermo_cold

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles

# bruitages sous la voix : niveau validé sur « arroser le soir »
SFX_GAIN = 0.27                                   # voix envoyée plus basse (-17,5 LUFS) : bruitages réduits d'autant
DUCK = 0.45
TRANS_GAIN = 0.26
SHIFT = 0.25                                     # les temps ci-dessous suivent la reconnaissance vocale (~0,25 s en retard)


def cue(t, name, gain=0.5):
    CUES.append((t - SHIFT, name, gain))


B = "banque/"
GLAND, GLAND2 = B + "gland", B + "gland2"
HAND, BOWL = B + "main_ouverte", B + "bol_verre_eau"
OAK, POT, POT_OAK, POT_CUT = B + "chene_arbre", B + "pot_haut", B + "pot_chene", B + "pot_coupe_terre"
CAN = B + "arrosoir_zinc"
FULL = (0, 0, 1024, 1024)
FOREST, KITCHEN, GARDEN, SALON = ("decor_foret_chemin.webp", "decor_salon_table_bois.webp",
                                  "tulipes_fond_sol_nu.png", "decor_salon_table_fenetre.jpg")
WALL = "decor_mur_outils_jardin.jpg"             # dehors : contre le vieux mur, avec les outils


class Cam:
    """Décor recadré (z, fx, fy) ; les objets sont dessinés après, à la bonne taille (k × z), bien nets."""

    def __init__(self, z, fx, fy):
        self.z = z
        cw, ch = W / z, H / z
        self.x0 = min(max(fx - cw / 2, 0), W - cw)
        self.y0 = min(max(fy - ch / 2, 0), H - ch)
        self.fx, self.fy = fx, fy

    def p(self, x, y):
        return (x - self.x0) * self.z, (y - self.y0) * self.z

    def bg(self, name):
        return zoomed(photo(name), self.z, self.fx, self.fy).copy()


def acorn(c, x, y, w_, rot=0.0, which=0, alpha=1.0):
    ob(c, GLAND if which % 2 == 0 else GLAND2, x, y, w_, rot=rot, alpha=alpha)


# ============================================================ A. LA FORÊT : LE GLAND TOMBE, LA MAIN LE RAMASSE (0 → 4.65)
GROUND = (560, 1480)                             # là où le gland atterrit, sur le chemin (photo plein écran)
AC_W = 88                                        # largeur du gland (zoom 1)
HAND_W = 520                                     # largeur de la main (zoom 1)
PINCH = (815, 655)                               # entre le pouce et l'index (cadre 1024 de la main)
HB_C = (512, 511.5)                              # centre de la boîte de la main
FG = (430, 1200)                                 # la main présente le gland au premier plan
FALL = (0.05, 0.95)
OAK_BASE = (566, 890)                            # pied du tronc (cadre 1024 du chêne)


def hand_at(c, px, py, hw, alpha=1.0):
    """Main posée de sorte que la pince (pouce-index) soit en (px, py)."""
    k = hw / 960
    ob(c, HAND, px - (PINCH[0] - HB_C[0]) * k, py - (PINCH[1] - HB_C[1]) * k, hw, alpha=alpha)


T_LAND = 1.4                                     # le gland touche le sol (chute lente, qu'on a le temps de suivre)
Z_FALL, Z_CLOSE = 1.6, 2.1                       # zooms modérés (pas trop rapides, pas trop forts)
T_GRAB, T_LIFT = 2.35, (2.45, 3.45)
T_OAK = 3.4


def s_forest(t):
    # le gland : chute lente (il se balance et tourne), puis deux petits rebonds sur le chemin
    if t < T_LAND:
        p = clamp((t - FALL[0]) / (T_LAND - FALL[0]))
        f = 0.35 * p + 0.65 * p * p
        ax = lerp(640, GROUND[0], p) + 26 * math.sin(p * 7.0) * (1 - p)
        ay = lerp(-160, GROUND[1], f)
        arot = 420 * p + 18 * math.sin(p * 9)
    else:
        q1, q2 = clamp((t - T_LAND) / 0.26), clamp((t - T_LAND - 0.26) / 0.16)
        ax = GROUND[0] + 18 * ease_out(clamp((t - T_LAND) / 0.45))
        ay = GROUND[1] - 70 * math.sin(math.pi * q1) - 22 * math.sin(math.pi * q2)
        arot = 420 + 70 * ease_out(clamp((t - T_LAND) / 0.45))
    # caméra : suit la chute, s'approche doucement du gland posé, puis dézoome lentement quand la main le remonte
    if t < T_LAND:
        cam = Cam(Z_FALL, 580, ay + 120)
    elif t < T_LIFT[0]:
        k = ease_io((t - T_LAND) / 0.9)
        cam = Cam(lerp(Z_FALL, Z_CLOSE, k), lerp(580, GROUND[0] + 18, k), lerp(GROUND[1] + 120, GROUND[1] - 120, k))
    else:
        k = ease_io((t - T_LIFT[0]) / (T_LIFT[1] - T_LIFT[0]))
        cam = Cam(lerp(Z_CLOSE, 1.0, k), lerp(GROUND[0] + 18, 540, k), lerp(GROUND[1] - 120, 960, k))
    w = cam.bg(FOREST)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    # le grand chêne de 300 ans pousse au loin sur le chemin
    if t > T_OAK:
        # il « pousse » du sol vers le ciel (révélé de bas en haut) : le haut de la photo reste hors du cadre
        g = ease_out(clamp((t - T_OAK) / 0.75))
        bx, by = 600, 1300
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        place(lay, OAK, FULL, 1800 * lerp(0.97, 1.0, g) / 960, *OAK_BASE, bx, by)
        if g < 1:
            line = lerp(by + 40, -250, g)
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).rectangle([0, line, W, H], fill=255)
            m = m.filter(ImageFilter.GaussianBlur(60))
            lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
        w.alpha_composite(lay)
        if t < T_OAK + 0.5:
            particles(w, t, T_OAK + 0.01, bx, by, 16, 5, col=(120, 90, 60), size=10, up=260, dur=0.6)
    sx, sy = cam.p(ax, ay)
    if t < T_LIFT[0]:
        shadow(w, sx, cam.p(ax, GROUND[1])[1] + AC_W * z * 0.35, AC_W * z * 0.9 * clamp((t - 0.7) / 0.7), 90)
        acorn(w, sx, sy, AC_W * z, arot)
        if T_LAND < t < T_LAND + 0.5:   # petites feuilles et poussière soulevées
            particles(w, t, T_LAND + 0.01, sx, sy + 25 * z, 10, 3, col=(150, 120, 80), size=4 * z, up=150, spread=200,
                      dur=0.5)
        if t > T_GRAB - 0.6:      # la main arrive doucement et pince le gland
            k = ease_out((t - (T_GRAB - 0.6)) / 0.6)
            px, py = lerp(sx - 700, sx, k), lerp(sy - 800, sy, k)
            hand_at(w, px, py, HAND_W * z)
    else:            # la main remonte le gland au premier plan
        k = ease_io((t - T_LIFT[0]) / (T_LIFT[1] - T_LIFT[0]))
        gx, gy = cam.p(GROUND[0] + 18, GROUND[1])
        px, py = lerp(gx, FG[0], k), lerp(gy, FG[1], k)
        hw = lerp(HAND_W * Z_CLOSE, 760, k)
        py += math.sin(t * 2.2) * 6 * clamp((t - T_LIFT[1]) / 0.4)
        acorn(w, px, py, hw * AC_W / HAND_W, arot)
        hand_at(w, px, py, hw)
    w.alpha_composite(shade())
    title(u, "CE PETIT GLAND…", t, 0.05, 2.4, y=330, color=YEL, size=150)
    title(u, "PEUT DEVENIR…", t, 2.44, 3.36, y=330, color=WHITE, size=160)
    title(u, "UN CHÊNE…", t, 3.4, 3.85, y=330, color=GREEN, size=180)
    stamp(u, "DE 300 ANS !", 540, 340, t, 3.88, None, RED, 150, -7)
    return w, u


cue(0.1, "whoosh", 0.1)
cue(T_LAND, "toc", 0.5)
cue(T_LAND + 0.02, "rustle", 0.16)
cue(T_GRAB, "pop_lo", 0.18)
cue(T_LIFT[0] + 0.05, "whoosh_up", 0.12)
cue(T_OAK + 0.02, "rise", 0.2)
cue(T_OAK + 0.5, "sparkle", 0.14)
cue(3.9, "alert1", 0.2)


# ============================================================ B. LA CUISINE : TRIE TES GLANDS (4.65 → 8.15)
BOARD = (545, 1490)                              # milieu de la planche (photo plein écran)
PILE = [(-150, 10, 20, 0), (-40, -25, -35, 1), (70, 5, 70, 0), (175, -20, 10, 1), (20, 60, 110, 0), (-95, 70, -60, 1)]
KW = 88                                          # largeur d'un gland sur la planche (zoom 1)


def s_kitchen(t):
    cam = Cam(lerp(1.25, 1.32, clamp((t - 4.65) / 3.5)), 545, 1330)
    z = cam.z
    w = cam.bg(KITCHEN)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, (dx, dy, rot, which) in enumerate(PILE):
        t0 = 4.75 + i * 0.12
        q = clamp((t - t0) / 0.3)
        if q <= 0:
            continue
        x, y = cam.p(BOARD[0] + dx, BOARD[1] + dy)
        yy = lerp(-200, y, ease_in(q)) - (34 * math.sin(math.pi * clamp((t - t0 - 0.3) / 0.18)) if q >= 1 else 0)
        shadow(w, x, y + KW * z * 0.3, KW * z * 0.9 * q, 80)
        acorn(w, x, yy, KW * z, rot + (1 - q) * 200, which)
        if t > 7.45:   # lesquels sont bons ?
            a_ = life(t, 7.45 + i * 0.06)
            put(u, text_img("?", F_TITLE, 90, YEL, stroke=8, stroke_fill=DARK), x + 10, y - 95 - 8 * math.sin(t * 5 + i),
                a_, rot=(-1) ** i * 10)
    w.alpha_composite(shade())
    title(u, "JE TE MONTRE COMMENT !", t, 4.7, 6.0, y=330, color=WHITE, size=110)
    title(u, "MAIS D'ABORD…", t, 6.06, 7.36, y=330, color=YEL, size=160)
    stamp(u, "TRIE TES GLANDS !", 540, 340, t, 7.4, None, RED, 125, -6)
    return w, u


for _i in range(6):
    cue(5.05 + _i * 0.12, "toc", 0.22)
cue(7.42, "alert2", 0.18)


# ============================================================ C. LE BOL D'EAU : FLOTTENT / COULENT (8.15 → 14.45)
BOWL_BOT, BOWL_W = (545, 1580), 560              # bas et largeur du bol sur la planche (zoom 1)
BB = (181, 349, 848, 783)                        # bol dans son cadre 1024
WATER_Y, FLOOR_Y = 487, 716                      # surface de l'eau et fond intérieur (cadre du bol)
INNER = [(205, 380), (826, 380), (822, 560), (792, 650), (722, 720), (600, 748), (430, 748), (310, 720), (240, 650),
         (206, 560)]
AW = 92                                          # largeur d'un gland dans le bol (cadre du bol)
# (x d'arrivée, flotte ?, x au fond, rotation au fond, image)
DROPS = [(330, False, 330, 95, 0), (430, True, 0, 0, 1), (530, False, 520, -80, 0), (630, True, 0, 0, 0),
         (720, False, 700, 100, 1)]
DROP_T = [8.85, 9.1, 9.35, 9.6, 9.85]
FLOAT_X = {1: 400, 3: 650}
THROW = (12.08, 12.6)


def s_bowl(t):
    cam = Cam(lerp(1.5, 1.6, clamp((t - 8.15) / 6.3)), 545, 1400)
    z = cam.z
    w = cam.bg(KITCHEN)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bx, by = cam.p(*BOWL_BOT)
    s_in = ease_out_back(clamp((t - 8.18) / 0.35), 1.6)
    k = BOWL_W * z / (BB[2] - BB[0]) * max(0.01, s_in)

    def V(x, y):   # cadre du bol → écran
        return bx + (x - 515) * k, by + (y - BB[3]) * k

    shadow(w, bx, by - 8 * k, BOWL_W * z * 0.95 * s_in, 80)
    if s_in < 0.99:
        ob(w, BOWL, bx, by, BOWL_W * z, s=s_in, anchor="bottom")
        w.alpha_composite(shade())
        title(u, "PLONGE-LES DANS L'EAU", t, 8.2, 10.2, y=330, color=YEL, size=112)
        return w, u
    poly = [V(*p) for p in INNER]
    wy = V(0, WATER_Y)[1]
    # l'eau dans le bol
    water = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(water)
    d.polygon(poly, fill=(150, 196, 214, 46))
    mw = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mw).rectangle([0, wy, W, H], fill=255)
    water.putalpha(Image.composite(water.getchannel("A"), Image.new("L", (W, H), 0), mw))
    w.alpha_composite(water)
    # les glands
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, (x0, floats, xb, rb, which) in enumerate(DROPS):
        t0 = DROP_T[i]
        if t < t0:
            continue
        p = clamp((t - t0) / 0.3)
        hit = t0 + 0.3
        if p < 1:
            x, y, rot = x0, lerp(-1100, WATER_Y, ease_in(p)), 300 * p
        elif floats:
            q = t - hit
            fx = FLOAT_X[i]
            x = lerp(x0, fx, ease_out(clamp(q / 0.8)))
            y = WATER_Y - 6 + 34 * math.exp(-q * 5) * math.cos(q * 12) + 3 * math.sin(t * 3 + i)
            rot = 300 + 20 * math.sin(t * 2 + i)
            if t > THROW[0]:   # jeté : il saute hors du bol, vers la poubelle (à gauche)
                r = ease_in(clamp((t - THROW[0]) / (THROW[1] - THROW[0])))
                x, y, rot = lerp(x, -900, r), y - 900 * math.sin(math.pi * r * 0.8), rot - 400 * r
        else:
            q = ease_out(clamp((t - hit) / 0.65))
            x = lerp(x0, xb, q) + math.sin((t - hit) * 7) * 14 * (1 - q)
            y = lerp(WATER_Y, FLOOR_Y - 28, q)
            rot = lerp(300, 360 + rb, q)
        X, Y = V(x, y)
        acorn(lay, X, Y, AW * k, rot, which)
        if hit < t < hit + 0.45:
            sx, sy = V(x0, WATER_Y)
            particles(u, t, hit, sx, sy, 12, i + 3, col=(220, 236, 248), size=6 * z, up=300, spread=240, dur=0.45)
    # sous l'eau : bleutés, un peu flous ; tout ce qui est dans le bol est découpé à l'intérieur du verre
    m_in = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m_in).polygon(poly + [], fill=255)
    m_in = Image.composite(m_in, Image.new("L", (W, H), 0), Image.new("L", (W, H), 255))
    top = Image.new("L", (W, H), 0)
    ImageDraw.Draw(top).rectangle([0, 0, W, V(0, 380)[1]], fill=255)       # au-dessus du bol : visible
    inside = Image.fromarray(np.maximum(np.asarray(m_in), np.asarray(top)))
    under = lay.filter(ImageFilter.GaussianBlur(1.2))
    tint = Image.new("RGBA", (W, H), (120, 170, 190, 0))
    tint.putalpha(Image.fromarray((np.asarray(under.getchannel("A")).astype(np.float32) * 0.28).astype(np.uint8)))
    under.alpha_composite(tint)
    mu = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mu).rectangle([0, wy + 2, W, H], fill=255)
    mu = mu.filter(ImageFilter.GaussianBlur(2))
    lay = Image.composite(under, lay, mu)
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), inside))
    w.alpha_composite(lay)
    # surface de l'eau (reflet) et le verre par-dessus
    sf = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    l_, r_ = V(212, WATER_Y), V(818, WATER_Y)
    ImageDraw.Draw(sf).ellipse([l_[0], wy - 16 * k, r_[0], wy + 16 * k], outline=(255, 255, 255, 110), width=3)
    w.alpha_composite(sf.filter(ImageFilter.GaussianBlur(1)))
    ob(w, BOWL, bx, by, BOWL_W * z, anchor="bottom")
    # repères
    sx, sy = V(525, WATER_Y)
    if 10.3 < t < 12.1:
        hl_ellipse(u, sx, sy - 10, 300 * k, 90 * k, life(t, 10.32, 12.0))
    if 11.3 < t < 12.7:
        put(u, icon("cross", 150), sx + 250 * k, sy - 200 * k, life(t, 11.32, 12.6))
        tag(u, "VIDES", sx - 170 * k, sy - 230 * k, t, 11.35, 12.6, rot=-6, size=58)
    fx_, fy_ = V(525, FLOOR_Y - 30)
    if t > 12.7:
        hl_ellipse(u, fx_, fy_, 290 * k, 80 * k, life(t, 12.72))
    if t > 13.66:
        put(u, icon("check", 150), fx_ + 250 * k, fy_ - 170 * k, life(t, 13.68))
        tag(u, "BONS !", fx_ - 180 * k, fy_ - 190 * k, t, 13.7, None, rot=-5, size=60)
    w.alpha_composite(shade())
    title(u, "PLONGE-LES DANS L'EAU", t, 8.2, 10.2, y=330, color=YEL, size=112)
    title(u, "ÇA FLOTTE ? C'EST VIDE", t, 10.24, 11.85, y=330, color=WHITE, size=112)
    stamp(u, "POUBELLE !", 540, 340, t, 12.04, 12.6, RED, 150, -7)
    title(u, "ÇA COULE ?", t, 12.64, 13.6, y=330, color=WHITE, size=170)
    stamp(u, "GARDE-LES !", 540, 340, t, 13.64, None, GREEN, 150, -6)
    return w, u


cue(8.2, "pop", 0.18)
for _t0 in DROP_T:
    cue(_t0 + 0.3, "plop", 0.24)
cue(10.32, "whoosh", 0.1)
cue(11.35, "fail", 0.2)
cue(12.1, "whoosh_up", 0.18)
cue(12.72, "whoosh", 0.1)
cue(13.68, "success", 0.2)


# ============================================================ D. LE POT PROFOND, EN COUPE : 2 CM (14.45 → 17.55)
POT_BOT, POT_W = (545, 1600), 340                # pot coupé sur la planche (zoom 1) ; largeur du pot
PC_BB = (244, 32, 780, 992)                      # pot coupé dans son cadre 1024
SOIL_TOP = 92                                    # surface de la terre (cadre du pot coupé)
DEPTH = 96                                       # 2 cm (le pot fait ~20 cm de haut)
PAW = 115                                        # gland dans le pot (cadre du pot)


def s_pot(t):
    cam = Cam(lerp(1.3, 1.38, clamp((t - 14.45) / 3.1)), 680, 1260)
    z = cam.z
    w = cam.bg(KITCHEN)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bx, by = cam.p(*POT_BOT)
    s_in = ease_out_back(clamp((t - 14.5) / 0.35), 1.6)
    k = POT_W * z / (PC_BB[2] - PC_BB[0])

    def V(x, y):
        return bx + (x - 512) * k, by + (y - 992) * k

    shadow(w, bx, by - 6 * k, POT_W * z * 1.05 * s_in, 85)
    place(w, POT_CUT, FULL, k, 512, 992, bx, by, s=max(0.01, s_in))
    # le gland tombe sur la terre, puis s'enfonce de 2 cm (couché sur le côté)
    surf_c = SOIL_TOP + PAW * 0.32
    deep_c = SOIL_TOP + DEPTH + PAW * 0.32
    if t > 15.05:
        p = clamp((t - 15.05) / 0.3)
        if p < 1:
            yv, rot = lerp(-700, surf_c, ease_in(p)), 200 * p
        else:
            yv, rot = lerp(surf_c, deep_c, ease_io(clamp((t - 15.5) / 0.4))), 200 + 70 * ease_out(clamp((t - 15.35) / 0.4))
        X, Y = V(512, yv)
        acorn(w, X, Y, PAW * k, rot)
        if 15.35 < t < 15.8:
            sx, sy = V(512, SOIL_TOP)
            particles(w, t, 15.35, sx, sy, 10, 4, col=(70, 50, 35), size=5 * z, up=180, spread=200, dur=0.4)
    if 15.95 < t < 17.05:   # la règle : 2 cm entre la surface et le gland
        x, y0 = V(760, SOIL_TOP)
        y1 = V(0, SOIL_TOP + DEPTH)[1]
        measure(u, x + 20, y0, y1, "2 CM", life(t, 15.97, 16.85))
        ImageDraw.Draw(u).line([V(300, SOIL_TOP + DEPTH), (x + 20, y1)], fill=(255, 255, 255, 160), width=3)
    if t > 16.85:   # un pot profond : flèche sur toute la hauteur
        x, ya = V(800, 40)
        yb = V(0, 985)[1]
        a_ = life(t, 16.87)
        if a_ > 0.01:
            d = ImageDraw.Draw(u)
            ym = lerp(ya, yb, ease_out(clamp((t - 16.87) / 0.35)))
            x += 60
            for col, wd in ((DARK, 14), (WHITE, 7)):
                d.line([(x, ya), (x, ym)], fill=col, width=wd)
            d.polygon([(x - 24, ym - 30), (x + 24, ym - 30), (x, ym + 6)], fill=WHITE, outline=DARK)
            tag(u, "PROFOND", x + 150, lerp(ya, yb, 0.5), t, 16.95, None, rot=-6, size=52)
    w.alpha_composite(shade())
    title(u, "PLANTE-LES À 2 CM", t, 14.5, 16.8, y=330, color=YEL, size=140)
    title(u, "DANS UN POT PROFOND", t, 16.84, None, y=330, color=WHITE, size=115)
    return w, u


cue(14.52, "pop", 0.16)
cue(15.35, "thud", 0.25)
cue(15.98, "tick", 0.16)
cue(16.9, "whoosh", 0.1)


# ============================================================ E. LE JARDIN : L'HIVER, L'ARROSAGE, LE PRINTEMPS (17.55 → 24.95)
G_POT, G_POT_W = (445, 1585), 150                # pot posé dans le coin, contre le mur, devant le râteau (zoom 1)
WALL_CAM = (1.25, 520, 1380)
GROUND_Y = 1640                                  # le sol commence ici (photo plein écran) : la neige tient dessous
PH_BB_W, PO_W = 507, 344                         # largeur du pot dans pot_haut / pot_chene (cadre 1024)
OPEN = (512, 62, 226, 19)                        # ouverture du pot (pot_haut) : centre, demi-axes


@lru_cache(None)
def _noise():
    from scipy.ndimage import gaussian_filter
    r = np.random.default_rng(5)
    n = gaussian_filter(r.standard_normal((H, W)), 30)
    return ((n - n.min()) / (n.max() - n.min())).astype(np.float32)


def season(im, winter, spring, ground=None):
    """Hiver : froid, terne, neige au sol ; printemps : doré et lumineux."""
    if winter < 0.01 and spring < 0.01:
        return im
    a = np.asarray(im.convert("RGB"), np.float32)
    if winter > 0.01:
        lum = a.mean(2, keepdims=True)
        a = a * (1 - 0.45 * winter) + lum * 0.45 * winter
        a = a * (1 + winter * (np.array([0.82, 0.9, 1.08], np.float32) - 1))
        cov = np.clip((_noise() + 0.05) * 2.6, 0, 0.85)[..., None] * winter     # la neige se pose / fond en douceur
        g0 = 420 if ground is None else ground
        cov *= np.clip((np.arange(H)[:, None, None] - g0) / 80, 0, 1)      # la neige tient au sol, pas sur le mur
        a = a * (1 - cov) + np.array([238, 242, 250], np.float32) * cov
    if spring > 0.01:
        a = a * (1 + spring * (np.array([1.08, 1.03, 0.9], np.float32) - 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


def tint_obj(lay, winter, spring):
    """Même lumière d'hiver / de printemps sur le pot que sur le décor (sans la neige au sol)."""
    if winter < 0.01 and spring < 0.01:
        return lay
    a = np.asarray(lay, np.float32).copy()
    rgb = a[..., :3]
    lum = rgb.mean(2, keepdims=True)
    rgb = rgb * (1 - 0.45 * winter) + lum * 0.45 * winter
    rgb = rgb * (1 + winter * (np.array([0.82, 0.9, 1.08], np.float32) - 1))
    rgb = rgb * (1 + spring * (np.array([1.08, 1.03, 0.9], np.float32) - 1))
    a[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def snowfall(c, t, a):
    if a <= 0.01:
        return
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(13)
    for _ in range(110):
        sp = r.uniform(90, 200)
        x = r.uniform(0, W) + math.sin(t * 1.4 + r.uniform(0, 6)) * 20
        y = (r.uniform(0, H) + t * sp) % H
        s = r.uniform(2.5, 7)
        d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 255, 255, int(220 * a)))


@lru_cache(None)
def soil_disc(rx, ry):
    g = photo(GARDEN).crop((200, 1300, 200 + int(rx * 2) + 4, 1300 + int(ry * 2) + 4)).convert("RGB")
    m = Image.new("L", g.size, 0)
    ImageDraw.Draw(m).ellipse([2, 2, 2 + rx * 2, 2 + ry * 2], fill=255)
    g = g.convert("RGBA")
    g.putalpha(m.filter(ImageFilter.GaussianBlur(1)))
    return g


def s_garden(t):
    cam = Cam(*WALL_CAM)
    z = cam.z
    winter = fade(t, 17.6, None, 0.6) * (1 - fade(t, 21.85, None, 0.7))
    spring = fade(t, 21.85, None, 0.7)
    w = season(cam.bg(WALL), winter, spring, cam.p(0, GROUND_Y)[1])
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px, py = cam.p(*G_POT)
    pw = G_POT_W * z
    shadow(w, px, py - 4, pw * 1.15, 90)
    pl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    which, sc = swap((t - 24.02) / 0.3)
    if which == 0:
        k = pw / PH_BB_W
        place(pl, POT, FULL, k * sc, 511, 992, px, py)
        ox, oy = px + (OPEN[0] - 511) * k * sc, py + (OPEN[1] - 992) * k * sc + 8 * k
        disc = soil_disc(int(OPEN[2] * k * sc * 0.96), int(OPEN[3] * k * sc))
        pl.alpha_composite(disc, (int(ox - disc.width / 2), int(oy - disc.height / 2)))
        w.alpha_composite(tint_obj(pl, winter, spring))
        cap = winter * clamp((t - 18.0) / 0.6)
        if cap > 0.01:   # un petit chapeau de neige sur la terre du pot
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ov).ellipse([ox - disc.width * 0.48, oy - disc.height * 0.55, ox + disc.width * 0.48,
                                        oy + disc.height * 0.4], fill=(245, 248, 255, int(235 * cap)))
            w.alpha_composite(ov.filter(ImageFilter.GaussianBlur(2)))
    else:
        k = pw / PO_W
        place(pl, POT_OAK, FULL, k * sc, 508, 992, px, py)
        w.alpha_composite(tint_obj(pl, winter, spring))
    snowfall(w, t, winter * (1 - fade(t, 19.3, None, 0.6)) if t < 21.85 else 0.0)
    # « ne les laisse jamais sécher » : on arrose
    if 19.35 < t < 21.9:
        s = 0.62 * z
        sx, sy = px, py - 960 * (pw / PH_BB_W) + 30
        cin = ease_out((t - 19.4) / 0.35)
        cout = ease_in((t - 21.5) / 0.3)
        tilt = -28 * ease_io((t - 19.75) / 0.25) * (1 - cout)
        cx = lerp(-400, sx - 224 * s, cin) - 700 * cout
        cy = sy - 156 * s - 200 * s * (1 - cin)
        ob(w, CAN, cx, cy, 420 * s, rot=tilt, flip=True)
        watering(w, t, fade(t, 20.0, 21.45, 0.06, 0.1), (cx + 188 * s, cy + 10 * s), sy - 4, s)
    if spring > 0.01:
        light_rays(w, 820, 0, t, spring)
    w.alpha_composite(shade())
    if 18.75 < t < 19.6:
        put(u, snow_badge(), 880, 610, life(t, 18.78, 19.4))
        put(u, thermo_cold(140), 190, 640, life(t, 18.85, 19.4))
    if 20.25 < t < 21.9:
        put(u, icon("drop", 150), 880, 640, life(t, 20.3, 21.8))
    if t > 22.15:
        put(u, icon("sun", 200), 880, 620, life(t, 22.18))
    if t > 24.05:
        sparkles(u, t, 24.06, px, py - 380 * z, 300, 10, 4)
    title(u, "LAISSE-LES DEHORS…", t, 17.6, 18.72, y=330, color=WHITE, size=120)
    title(u, "TOUT L'HIVER !", t, 18.76, 19.35, y=330, color=BLUE, size=150)
    title(u, "ET SURTOUT…", t, 19.4, 20.2, y=330, color=WHITE, size=160)
    stamp(u, "JAMAIS SEC !", 540, 340, t, 20.24, 21.8, RED, 150, -7)
    title(u, "AU PRINTEMPS…", t, 21.85, 23.0, y=330, color=YEL, size=150)
    title(u, "TON PREMIER CHÊNE !", t, 23.04, None, y=330, color=GREEN, size=120)
    return w, u


cue(17.62, "rustle", 0.12)
cue(18.8, "pop_hi", 0.12)
cue(19.42, "whoosh", 0.1)
cue(19.95, "pour", 0.2)
cue(20.26, "alert1", 0.18)
cue(21.9, "sparkle", 0.16)
cue(24.04, "pop", 0.2)
cue(24.1, "success", 0.2)


# ============================================================ F. LE SALON : LE PETIT CHÊNE + ABONNE-TOI (24.95 → fin)
TABLE_PT = (728, 1122)                           # dessus de la table du salon (photo plein écran)


def s_end(t):
    cam = Cam(lerp(1.15, 1.22, clamp((t - 24.95) / 4)), 660, 1000)
    z = cam.z
    w = cam.bg(SALON)
    px, py = cam.p(*TABLE_PT)
    pw = 150 * z
    shadow(w, px, py - 3, pw * 1.2, 90)
    place(w, POT_OAK, FULL, pw / PO_W, 508, 992, px, py)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    sparkles(u, t, 25.05, px, py - 250, 260, 9, 7)
    clicked = t > 26.4
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 26.35) / 0.15))
    put(u, btn, 540, 1400, life(t, 25.2) * press)
    if t > 25.8:
        kk = ease_out((t - 25.8) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 27.4, dur=0.45))
    sparkles(u, t, 27.5, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 25.0, 27.35, y=330, color=YEL, size=135)
    return w, u


cue(25.05, "pop_lo", 0.18)
cue(26.38, "click", 0.3)
cue(27.5, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 4.65 - SHIFT, _sh(s_forest)),
    (4.65 - SHIFT, 8.15 - SHIFT, _sh(s_kitchen)),
    (8.15 - SHIFT, 14.45 - SHIFT, _sh(s_bowl)),
    (14.45 - SHIFT, 17.55 - SHIFT, _sh(s_pot)),
    (17.55 - SHIFT, 24.95 - SHIFT, _sh(s_garden)),
    (24.95 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
