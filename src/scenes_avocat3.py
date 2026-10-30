"""Storyboard « Noyau d'avocat » — VARIANTE (même voix que avocat2 : assets/audio/avocat2/voix.mp3, son fort).

Différences avec avocat2 : on ouvre sur le résultat (l'avocatier sur le buffet) qui se « rembobine » jusqu'au noyau,
la poubelle est sur fond beige avec une loupe « rayons X » qui révèle l'arbre caché dedans, les étapes sont numérotées
sur fond beige, la germination est montrée en gros plan, et la fin boucle sur le début (l'avocatier sur le buffet).
Mêmes photos : noyau brun, noyau épluché, noyau fendu, jeune plant, avocatier en pot, poubelle, sopalin, boîte,
buffet du salon.
"""
import math

from PIL import Image, ImageDraw

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, put, title, life, fade, ease_out, ease_io,
                 ease_in, clamp, lerp, icon, pills, tag, button_img, hl_ellipse, particles, num_badge, light_rays)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_mangue import warm_glow
from scenes_citron import photo, shade, zoomed, shadow, swap, sopalin
from scenes_avocat2 import ob, wipe, wrapped, PIT, PELE, FENDU, PLANT, TREE, BIN, BOX_O, BOX_F, TOP

CUES = []
NO_CAPTION_UNTIL = 0.0


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


def rewind_fx(u, t, t0, t1):
    """Effet « retour en arrière » : voile bleuté, lignes de balayage, ◀◀."""
    a = fade(t, t0, t1, 0.08, 0.12)
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (40, 60, 90, int(45 * a)))
    d = ImageDraw.Draw(ov)
    for yy in range(0, H, 9):
        d.line([(0, yy), (W, yy)], fill=(255, 255, 255, int(20 * a)), width=2)
    off = (t * 1100) % H
    d.rectangle([0, off, W, off + 26], fill=(255, 255, 255, int(70 * a)))
    u.alpha_composite(ov)
    d = ImageDraw.Draw(u)
    for i in range(2):
        x0 = 120 + i * 70
        d.polygon([(x0 + 70, 560), (x0 + 70, 660), (x0, 610)], fill=WHITE + (int(240 * a),), outline=DARK)


# ============================================================ A. LE RÉSULTAT D'ABORD… QUI SE REMBOBINE (0 → 1.82)
# (image, largeur, ancrage bas) : avocatier → jeune plant → noyau fendu → noyau épluché → noyau brun
CHAIN = [(TREE, 300), (PLANT, 330), (FENDU, 150), (PELE, 140), (PIT, 140)]
CHAIN_T0, CHAIN_DT = 0.95, 0.2


def chain_state(t):
    i = int(clamp((t - CHAIN_T0) / CHAIN_DT, 0, len(CHAIN) - 1.001))
    if t < CHAIN_T0:
        return CHAIN[0], 1.0
    p = (t - CHAIN_T0 - i * CHAIN_DT) / CHAIN_DT
    which, sc = swap(p)
    j = min(len(CHAIN) - 1, i + which)
    return CHAIN[j], sc


def s_hook(t):
    w = photo("citron_fond_buffet.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    (name, wd), sc = chain_state(t)
    shadow(w, TOP[0], TOP[1], 260 if name in (TREE, PLANT) else 150)
    ob(w, name, TOP[0], TOP[1], wd * sc, anchor="bottom")
    z = lerp(1.0, 1.35, ease_io(t / 1.8))
    w = zoomed(w, z, TOP[0], TOP[1] - 150)
    w.alpha_composite(shade())
    rewind_fx(u, t, CHAIN_T0 - 0.05, 1.8)
    title(u, "TU JETTES ÇA ?", t, 0.1, None, y=330, color=YEL, size=165)
    return w, u


cue(0.0, "sparkle", 0.25)
cue(CHAIN_T0, "rise", 0.3)
for _i in range(1, len(CHAIN)):
    cue(CHAIN_T0 + (_i - 0.5) * CHAIN_DT, "pop_hi", 0.18)


# ============================================================ B. LA POUBELLE : UN ARBRE CACHÉ DEDANS (1.82 → 4.55)
BIN_X, BIN_W = 770, 340
BIN_K = BIN_W / (727 - 297)
BIN_BOT = TABLE + 40
BIN_RIM = BIN_BOT - (920 - 330) * BIN_K             # bord avant de l'ouverture
PIT0 = (300, TABLE - 40)


def s_bin(t):
    w, u = new_layers(background("table"))
    shake = math.sin(t * 60) * 8 * fade(t, 2.38, 2.7, 0.02, 0.2) if 2.38 < t < 2.7 else 0.0
    shadow(w, BIN_X, BIN_BOT, BIN_W * 1.05)
    ob(w, BIN, BIN_X + shake, BIN_BOT, BIN_W, anchor="bottom")
    p = ease_in((t - 1.9) / 0.48)
    if t < 2.38:
        x = lerp(PIT0[0], BIN_X, p)
        y = lerp(PIT0[1], BIN_RIM - 30, p) - math.sin(math.pi * p) * 360
        if p <= 0:
            shadow(w, PIT0[0], TABLE + 40, 130)
        ob(w, PIT, x, y, lerp(150, 120, p), rot=-280 * p)
    if 2.38 < t < 2.8:
        particles(w, t, 2.4, BIN_X, BIN_RIM - 10, 10, 3, col=(170, 170, 170), size=8, up=240)
    # loupe « rayons X » : un arbre caché dans la poubelle
    g = life(t, 2.95, dur=0.4)
    if g > 0.01:
        cx, cy, r = BIN_X, BIN_RIM + 150, 185 * g
        lens = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lens)
        dl.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(20, 40, 50, 235))
        ob(lens, PLANT, cx, cy + r * 0.85, 300 * g, anchor="bottom")
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        lens.putalpha(Image.composite(lens.getchannel("A"), Image.new("L", (W, H), 0), m))
        w.alpha_composite(lens)
        d = ImageDraw.Draw(u)
        d.ellipse([cx - r - 12, cy - r - 12, cx + r + 12, cy + r + 12], outline=DARK, width=int(26 * g))
        d.ellipse([cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5], outline=(190, 196, 200), width=int(10 * g))
        hx, hy = cx - r * 0.72, cy + r * 0.72
        d.line([(hx, hy), (hx - 140 * g, hy + 140 * g)], fill=DARK, width=int(42 * g))
        d.line([(hx - 8, hy + 8), (hx - 132 * g, hy + 132 * g)], fill=(150, 90, 50), width=int(26 * g))
        sparkles(u, t, 3.2, cx, cy, 240, 8, 5)
    title(u, "À LA POUBELLE ?", t, 1.86, 3.05, y=330, color=RED, size=150)
    stamp(u, "UN ARBRE !", 540, 360, t, 3.1, 3.7, GREEN, 135, -8)
    title(u, "SANS LE SAVOIR…", t, 3.74, None, y=330, size=140)
    return w, u


cue(1.92, "whoosh", 0.3)
cue(2.4, "thud", 0.45)
cue(2.98, "pop_lo", 0.25)
cue(3.12, "success", 0.3)


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
    sparkles(u, t, 18.5, TOP[0], TOP[1] - 300, 330, 10, 7)
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
    title(u, "UN AVOCATIER GRATUIT !", t, 18.3, 19.05, y=1300, color=YEL, size=110)
    return w, u


cue(18.32, "pop_lo", 0.3)
cue(19.58, "click", 0.45)
cue(20.0, "sparkle", 0.25)

SCENES = [
    (0.0, 1.82, s_hook),
    (1.82, 4.55, s_bin),
    (4.55, 12.4, s_steps),
    (12.4, 15.6, s_wait),
    (15.6, 18.25, s_macro),
    (18.25, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
