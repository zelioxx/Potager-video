"""Storyboard « Noyau d'avocat » — VARIANTE (même voix que avocat2 : assets/audio/avocat2/voix.mp3, son fort).

Différences avec avocat2 : on ouvre sur le résultat (l'avocatier sur le buffet) qui se « rembobine » jusqu'au noyau,
la poubelle est sur fond beige avec une loupe « rayons X » qui révèle l'arbre caché dedans, les étapes sont numérotées
sur fond beige, la germination est montrée en gros plan, et la fin boucle sur le début (l'avocatier sur le buffet).
Mêmes photos : noyau brun, noyau épluché, noyau fendu, jeune plant, avocatier en pot, poubelle, sopalin, boîte,
buffet du salon.
"""
import math

from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, put, title, life, fade, ease_out, ease_io,
                 ease_in, clamp, lerp, icon, pills, tag, button_img, hl_ellipse, particles, num_badge, light_rays)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_mangue import warm_glow
from scenes_citron import photo, shade, zoomed, shadow, swap, sopalin
from scenes_avocat2 import ob, wipe, wrapped, PIT, PELE, FENDU, PLANT, TREE, BOX_O, BOX_F, TOP
from scenes_ananas import place

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, plus gros et plus lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


# ============================================================ A. OUVERTURE DANS LA CUISINE (0 → 4.55)
# la cuisine (photo fournie, plan de travail + planche) : l'avocat coupé sur la planche, le noyau dans sa cavité,
# la poubelle en zinc à droite sur le plan de travail. Le couvercle s'ouvre et se pose devant ; le noyau est lancé
# dedans (il passe DEVANT le bord arrière et DERRIÈRE le bord avant) ; STOP, il ressort (◀◀) ; puis ▶▶ avance rapide
# sur la planche : noyau → épluché → fendu → jeune plant → avocatier (le pot fait la moitié de l'écran).
ZB_OPEN, ZB_SHUT, ZB_LID = "banque/poubelle_zinc_ouverte", "banque/poubelle_zinc_fermee", "banque/poubelle_zinc_couvercle"
AVO = "banque/avocat_coupe"
BIN_X, BIN_W, BIN_BOT = 875, 330, 1445        # poubelle posée sur le plan de travail, à droite de la planche
BIN_K = BIN_W / (845 - 179)
SRC_BOT = 919                                 # bas de la poubelle dans la photo
LIP = (512, 218, 275, 74)                     # ouverture : centre x, centre y, demi-axes (photo ouverte)
LID_K = BIN_K * 564 / 902                     # couvercle seul ramené à l'échelle de la poubelle
LID_ON = (626, 784)                           # bas-centre du couvercle seul ↔ (512, 305) sur la photo fermée
LID_REST = (940, 1530)                        # couvercle posé à plat devant, à droite de la poubelle
AVO_C, AVO_W = (430, 1175), 540               # avocat coupé sur la planche (centre, largeur)
AVO_K = AVO_W / (943 - 81)
CAVITY = (AVO_C[0] + (300 - 512) * AVO_K, AVO_C[1] + (500 - 496) * AVO_K)   # cavité de la moitié gauche
PW = 128                                      # largeur du noyau
GROW_C = (560, 1300)                          # avance rapide : posé au centre de la planche (bas)


def bsrc(x, y, dx=0.0):
    """Point (x, y) de la photo de la poubelle → décor."""
    return BIN_X + dx + (x - 512) * BIN_K, BIN_BOT + (y - SRC_BOT) * BIN_K


def lip_y(x, dx=0.0):
    """Bord AVANT de l'ouverture (décor) à l'abscisse x."""
    cx, cy, rx, ry = LIP
    sx = 512 + (x - BIN_X - dx) / BIN_K
    f = clamp(1 - ((sx - cx) / rx) ** 2, 0, 1)
    return bsrc(0, cy + ry * math.sqrt(f))[1]


def bin_img(c, name, dx=0.0):
    place(c, name, (0, 0, 1024, 1024), BIN_K, 512, SRC_BOT, BIN_X + dx, BIN_BOT)


def lid(c, X, Y, rot=0.0):
    """Couvercle seul, son bas-centre en (X, Y)."""
    place(c, ZB_LID, (0, 0, 1254, 1254), LID_K, *LID_ON, X, Y, 1.0, rot)


def speed_fx(u, t, t0, t1, forward=True):
    """Effet vidéo : voile, lignes de balayage, ◀◀ (retour) ou ▶▶ (avance rapide)."""
    a = fade(t, t0, t1, 0.08, 0.12)
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (40, 60, 90, int(40 * a)))
    d = ImageDraw.Draw(ov)
    for yy in range(0, H, 9):
        d.line([(0, yy), (W, yy)], fill=(255, 255, 255, int(18 * a)), width=2)
    off = (t * 1100) % H
    d.rectangle([0, off, W, off + 26], fill=(255, 255, 255, int(60 * a)))
    u.alpha_composite(ov)
    d = ImageDraw.Draw(u)
    for i in range(2):
        x0 = 860 + i * 70 if forward else 120 + i * 70
        pts = [(x0, 560), (x0, 660), (x0 + 70, 610)] if forward else [(x0 + 70, 560), (x0 + 70, 660), (x0, 610)]
        d.polygon(pts, fill=WHITE + (int(240 * a),), outline=DARK)


GROW = [(PIT, 200), (PELE, 190), (FENDU, 230), (PLANT, 420), (TREE, 400)]
GROW_T0, GROW_DT = 2.05, 0.3


def grow_state(t):
    if t < GROW_T0:
        return GROW[0], 1.0
    i = int(clamp((t - GROW_T0) / GROW_DT, 0, len(GROW) - 1.001))
    p = (t - GROW_T0 - i * GROW_DT) / GROW_DT
    which, sc = swap(p)
    return GROW[min(len(GROW) - 1, i + which)], sc


def in_bin(lay, depth):
    """Le noyau dans la poubelle : caché sous le bord avant, assombri en descendant."""
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon([(0, 0), (W, 0)] + [(xx, lip_y(xx)) for xx in range(W, -1, -12)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(1))
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
    if depth > 0.01:
        dark = Image.new("RGBA", (W, H), (20, 20, 22, int(150 * depth)))
        dark.putalpha(Image.composite(dark.getchannel("A"), Image.new("L", (W, H), 0), lay.getchannel("A")))
        lay.alpha_composite(dark)


def s_open(t):
    w = photo("citron_fond_cuisine.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out = ease_in((t - 1.85) / 0.4)                     # avance rapide : poubelle, couvercle et avocat s'en vont
    bdx, adx = 700 * out, -800 * out
    shake = math.sin(t * 60) * 5 * fade(t, 1.05, 1.35, 0.02, 0.2) if 1.05 < t < 1.35 else 0.0
    # --- l'avocat coupé sur la planche
    if adx > -700:
        shadow(w, AVO_C[0] + adx, AVO_C[1] + 150, AVO_W * 0.9, 50)
        place(w, AVO, (0, 0, 1024, 1024), AVO_K, 512, 496, AVO_C[0] + adx, AVO_C[1])
    # --- la poubelle : fermée → ouverte (le couvercle se soulève 0,15 puis se pose devant 0,35 → 0,7)
    up = ease_out((t - 0.15) / 0.2)
    slide = ease_io((t - 0.35) / 0.35)
    lox, loy = bsrc(512, 305)
    lx = lerp(lox, LID_REST[0], slide) + bdx
    ly = lerp(loy - 90 * up, LID_REST[1], slide) - math.sin(math.pi * slide) * 70
    behind = False
    if bdx < 600:
        shadow(w, BIN_X + bdx, BIN_BOT, BIN_W * 0.95)
        bin_img(w, ZB_SHUT if t < 0.15 else ZB_OPEN, bdx + shake)
    # --- le noyau
    (name, wd), sc = grow_state(t)
    target = bsrc(512, 300)                             # fond de l'ouverture
    hover = (BIN_X, bsrc(0, 60)[1])                     # juste au-dessus de la poubelle
    inside, depth = False, 0.0
    if t < 0.72:
        x, y, rot = CAVITY[0], CAVITY[1] - 10 * ease_out(t / 0.3), 0.0
    elif t < 1.05:                                      # lancé en cloche dans la poubelle
        p = ease_io((t - 0.72) / 0.33)
        x = lerp(CAVITY[0], target[0], p)
        y = lerp(CAVITY[1] - 10, target[1], p) - math.sin(math.pi * p) * 300
        rot, inside = -300 * p, p > 0.7
        depth = clamp((p - 0.85) / 0.15) * 0.4
    elif t < 1.4:
        x, y, rot, inside, depth = target[0], target[1] + 40, -300, True, 0.55
    elif t < 1.78:                                      # ◀◀ il ressort
        p = ease_out((t - 1.4) / 0.38)
        x, y, rot = target[0], lerp(target[1] + 40, hover[1], p), -300 * (1 - p)
        inside, depth = p < 0.55, 0.55 * (1 - p)
    if t < 1.85:
        if t >= 0.15 and bdx < 600:
            if slide > 0.55:
                shadow(w, LID_REST[0] + bdx, LID_REST[1], 270 * clamp((slide - 0.55) / 0.45), 60)
            lid(w, lx, ly, -8 * up * (1 - slide))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t >= 1.78:
            x, y, rot = hover[0], hover[1], 0.0
        ob(lay, PIT, x, y, PW, rot=rot)
        if inside:
            in_bin(lay, depth)
        w.alpha_composite(lay)
    else:
        if bdx < 600:
            shadow(w, LID_REST[0] + bdx, LID_REST[1], 270, 60)
            lid(w, lx, ly, 0.0)
        p = ease_io((t - 1.85) / 0.2)
        gx = lerp(hover[0], GROW_C[0], p)
        gb = lerp(hover[1] + PW * 0.45, GROW_C[1], p)
        shadow(w, gx, gb, wd * 0.8 * sc, 70)
        ob(w, name, gx, gb, wd * sc, anchor="bottom")
    if 1.06 < t < 1.45:
        particles(w, t, 1.07, BIN_X, bsrc(0, 220)[1], 9, 3, col=(170, 170, 170), size=6, up=200)
    # --- caméra : plan large de la cuisine, puis on se rapproche de la planche pour l'avance rapide
    zk = ease_io((t - 1.9) / 0.45)
    z = lerp(lerp(1.22, 1.12, ease_out(t / 0.6)), 1.45, zk)
    fx, fy = lerp(660, GROW_C[0], zk), lerp(1250, 1000, zk)
    w = zoomed(w, z, fx, fy)
    w.alpha_composite(shade())
    if t > GROW_T0 + 4 * GROW_DT - 0.1:
        sparkles(u, t, GROW_T0 + 4 * GROW_DT, 540, 900, 360, 10, 7)
    speed_fx(u, t, 1.4, 1.8, forward=False)
    speed_fx(u, t, 1.86, GROW_T0 + 4 * GROW_DT + 0.1, forward=True)
    title(u, "TU JETTES ÇA ?", t, 0.05, 1.36, y=330, color=YEL, size=165)
    title(u, "STOP !", t, 1.4, 1.84, y=330, color=RED, size=190)
    stamp(u, "UN ARBRE !", 540, 340, t, 3.12, 3.7, GREEN, 135, -8)
    title(u, "SANS LE SAVOIR…", t, 3.74, None, y=330, size=140)
    return w, u


cue(0.0, "pop_lo", 0.25)
cue(0.17, "click", 0.35)
cue(0.62, "chop", 0.22)
cue(0.74, "whoosh", 0.25)
cue(1.05, "thud", 0.45)
cue(1.42, "alert3", 0.32)
cue(1.88, "rise", 0.3)
for _i in range(1, len(GROW)):
    cue(GROW_T0 + (_i - 0.5) * GROW_DT, "pop_hi", 0.18)
cue(3.15, "success", 0.32)


# ============================================================ C. LES ÉTAPES SUR FOND BEIGE (4.55 → 12.4)
SX, SY, SW = 540, 1262, 300             # sopalin (même place que dans la boîte)
BOX_C = (540, 1157)
BIG = (540, TABLE - 105)


def s_steps(t):
    w, u = new_layers(background("table"))
    warm_glow(w, fade(t, 11.75, None, 0.5))
    # --- étape 1 : laver, éplucher
    pop = life(t, 4.6, dur=0.35)
    move = ease_io((t - 8.15) / 0.45)        # le noyau épluché va sur le sopalin
    if t < 8.15:
        shadow(w, BIG[0], TABLE + 40, 260 * pop)
        wipe(w, PIT, PELE, BIG[0], BIG[1], 300 * pop, 300 * 0.92 * pop, ease_io((t - 6.85) / 0.9))
        if 5.95 < t < 6.7:
            for i in range(12):
                tt = (t - 5.95 - i * 0.05) % 0.45
                put(w, icon("drop", 34), BIG[0] - 120 + (i * 47) % 240, lerp(BIG[1] - 330, BIG[1] - 40, tt / 0.45),
                    1, 0, 1 - tt / 0.45)
        if 6.85 < t < 7.9:
            particles(w, t, 6.95, BIG[0] + 60, BIG[1], 12, 5, col=(110, 70, 40), size=9, up=220, dur=1.0)
    # --- étape 2 : sopalin humide, boîte fermée, au chaud
    if t >= 8.15:
        sop_in = ease_out((t - 8.15) / 0.3)
        pw = lerp(300 * 0.92, 165, move)
        if move < 1:
            sopalin(w, SX, lerp(SY + 500, SY, sop_in), SW, 1.0, 0.0)
            ob(w, PELE, lerp(BIG[0], SX, move), lerp(BIG[1], SY - pw * 0.18, move), pw)
        else:
            wrapped(w, SX, SY, SW, PELE, 165, ease_io((t - 8.85) / 0.7), ease_out((t - 10.05) / 0.5))
        if 10.05 < t < 10.5:
            for i in range(8):
                tt = (t - 10.05 - i * 0.04) % 0.35
                put(w, icon("drop", 30), SX - 130 + i * 38, lerp(SY - 280, SY - 20, tt / 0.35), 1, 0, 1)
        if t > 10.5:
            bx = lerp(1300, BOX_C[0], ease_out((t - 10.5) / 0.4))
            shadow(w, bx, BOX_C[1] + 190, 560)
            which, sc = swap((t - 11.1) / 0.3)
            ob(w, BOX_O if which == 0 else BOX_F, bx, BOX_C[1] - (6 if which else 0), 620 * sc)
    w = zoomed(w, 1.3, 540, 1130)          # objets plus gros à l'écran
    if t > 11.8:
        put(u, icon("thermo", 150), 170, 640, life(t, 11.85))
        put(u, icon("sun", 160), 910, 640, life(t, 11.95), t * 25)
    put(u, num_badge("1", 150), 150, 560, life(t, 5.3, 8.0))
    put(u, num_badge("2", 150), 150, 560, life(t, 8.08, 11.7))
    if 6.85 < t < 8.05:
        tag(u, "PEAU BRUNE", 820, 640, t, 6.9, 8.0, rot=-5, size=52)
    title(u, "D'ABORD…", t, 4.6, 5.9, y=330, size=160)
    title(u, "LAVE-LE", t, 5.95, 6.75, y=330, color=YEL, size=170)
    title(u, "RETIRE SA PEAU", t, 6.8, 8.0, y=330, size=145)
    title(u, "ENROULE-LE", t, 8.08, 9.6, y=330, color=YEL, size=160)
    title(u, "ESSUIE-TOUT HUMIDE", t, 9.65, 10.5, y=330, size=118)
    title(u, "BOÎTE FERMÉE", t, 10.55, 11.75, y=330, color=YEL, size=145)
    title(u, "AU CHAUD !", t, 11.8, None, y=330, size=165)
    return w, u


cue(4.62, "pop", 0.25)
cue(5.35, "pop_hi", 0.2)
cue(5.98, "splash", 0.3)
cue(6.9, "squish", 0.25)
cue(8.1, "pop_hi", 0.2)
cue(8.9, "stir", 0.22)
cue(10.08, "plop", 0.25)
cue(10.55, "whoosh", 0.16)
cue(11.12, "click", 0.4)
cue(11.88, "rise", 0.18)


# ============================================================ D. LE BUFFET : ON ATTEND (12.4 → 15.6)
def s_wait(t):
    w = photo("citron_fond_buffet.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    light_rays(w, 260, 0, t, fade(t, 12.5, None, 0.5))
    land = ease_out((t - 12.45) / 0.4)
    bx, by = TOP[0], lerp(TOP[1] - 500, TOP[1] - 100, land)
    shadow(w, TOP[0], TOP[1], 330 * land)
    sopalin(w, bx, by + 78, 250, 1.0, 1.0)
    ob(w, PELE, bx, by + 45, 125)
    ob(w, BOX_F, bx, by, 430)
    ob(w, PELE, bx, by + 45, 125, alpha=0.6)
    if 13.3 < t < 15.5:   # les jours et les nuits défilent
        night = 0.5 + 0.5 * math.sin((t - 13.3) * 10)
        w.alpha_composite(Image.new("RGBA", (W, H), (20, 26, 60, int(95 * night * fade(t, 13.3, 15.5, 0.2, 0.2)))))
    w = zoomed(w, lerp(1.0, 1.3, ease_io((t - 12.4) / 3.2)), TOP[0], TOP[1] - 120)
    w.alpha_composite(shade())
    if 13.4 < t < 15.6:
        act = min(3, int((t - 13.5) / 0.45))
        pills(u, ["S1", "S2", "S3", "S4"], act, t, 13.4, 15.55, y=1180, pw=170)
    title(u, "ET LÀ… ON ATTEND", t, 12.5, 14.3, y=1300, size=135)
    title(u, "QUELQUES SEMAINES", t, 14.38, None, y=1300, color=YEL, size=125)
    return w, u


cue(12.5, "thud", 0.3)
for _k in range(4):
    cue(13.5 + _k * 0.45, "tick", 0.24)


# ============================================================ E. GROS PLAN : IL SE FEND, UNE RACINE SORT (15.6 → 18.25)
MX, MY, MW = 540, 1095, 440
FK = MW / (839 - 181)                       # noyau_fendu : bbox (181, 125, 839, 948) dans l'image 1024


def s_macro(t):
    w, u = new_layers(background("table"))
    light_rays(w, 200, 0, t, 0.8)
    which, sc = swap((t - 15.82) / 0.32)
    shake = math.sin(t * 70) * 7 * fade(t, 15.7, 15.95, 0.02, 0.1) if 15.7 < t < 15.95 else 0.0
    shadow(w, MX, TABLE + 40, MW * 0.8)
    if which == 0:
        ob(w, PELE, MX + shake, MY, MW * 0.95 * sc)
    else:
        ob(w, FENDU, MX, MY, MW * sc)
    if 15.95 < t < 16.6:
        particles(w, t, 15.98, MX, MY - 100, 12, 6, col=(235, 220, 170), size=9, up=320)
    if t > 16.66:
        rx, ry = MX + (600 - 510) * FK, MY + (900 - 536) * FK
        hl_ellipse(u, rx, ry, 70, 80, life(t, 16.7))
        tag(u, "RACINE !", 830, ry + 40, t, 16.75, None, rot=5, size=62, string_to=(rx + 60, ry))
        sparkles(u, t, 16.8, rx, ry, 200, 8, 9)
    title(u, "IL SE FEND !", t, 15.62, 16.6, y=330, size=165)
    title(u, "UNE RACINE SORT !", t, 16.66, None, y=330, color=YEL, size=135)
    return w, u


cue(15.85, "crunch", 0.45)
cue(16.75, "pop_hi", 0.25)
cue(17.5, "success", 0.3)


# ============================================================ F. RETOUR AU DÉBUT : L'AVOCATIER SUR LE BUFFET (18.25 → fin)
def s_end(t):
    w = photo("citron_fond_buffet.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    q = ease_out((t - 18.3) / 0.45)
    shadow(w, TOP[0], TOP[1], 300 * q)
    ob(w, TREE, TOP[0], TOP[1], 300, s=life(t, 18.3, dur=0.45), anchor="bottom")
    w = zoomed(w, 1.65, TOP[0], TOP[1] - 230)
    sparkles(u, t, 18.5, 540, 760, 330, 10, 7)
    w.alpha_composite(shade())
    if t > 19.1:
        clicked = t > 19.6
        btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
        press = 1 - 0.08 * math.sin(math.pi * clamp((t - 19.55) / 0.15))
        put(u, btn, 540, 1240, life(t, 19.15) * press)
        if t > 19.25:
            k = ease_out((t - 19.25) / 0.3)
            put(u, icon("cursor", 110), lerp(900, 640, k), lerp(1520, 1280, k), 1)
        put(u, logo_img(260), 540, 330, life(t, 19.9, dur=0.45))
        sparkles(u, t, 20.0, 540, 330, 200, 10, 12)
    title(u, "UNE PLANTE GRATUITE !", t, 18.3, 19.05, y=1300, color=YEL, size=120)
    if t > 18.45:
        tag(u, "PAS D'AVOCATS… MAIS QUELLE DÉCO !", 540, 1100, t, 18.5, 19.05, rot=-3, size=40)
    return w, u


cue(18.32, "pop_lo", 0.3)
cue(19.58, "click", 0.45)
cue(20.0, "sparkle", 0.25)

SCENES = [
    (0.0, 4.55, s_open),
    (4.55, 12.4, s_steps),
    (12.4, 15.6, s_wait),
    (15.6, 18.25, s_macro),
    (18.25, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
