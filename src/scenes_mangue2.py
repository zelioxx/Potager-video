"""Storyboard « Noyau de mangue » v2 (voix : assets/audio/mangue2/voix.mp3, son fort).

Même direction que la variante avocat (scenes_avocat3) : on ouvre dans la cuisine (photo fournie), la mangue coupée
(photo fournie) est sur la planche, le noyau est retiré de sa moitié et jeté dans la poubelle en zinc ; STOP, il ressort
(◀◀) et ▶▶ il devient un manguier. Puis les étapes en gros plan sur fond beige : nettoyer, ouvrir la coque au ciseau
par le côté, la grosse graine, sopalin humide et boîte fermée au chaud ; sur le buffet on attend, une racine sort,
et le manguier sur le buffet pour la fin.
Photos : mangue coupée, noyau, graine, graine germée, manguier (vidéo mangue précédente), poubelle zinc, sopalin,
boîte, cuisine et buffet.
"""
import math

from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, DARK, WHITE, background, put, title, life, fade, ease_out, ease_io, ease_in,
                 clamp, lerp, icon, pills, tag, button_img, hl_ellipse, particles, num_badge, light_rays)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp, scissors, dashed
from scenes_mangue import warm_glow, pit, pit_halves, PIT_C, PIT_RX, PIT_BOT
from scenes_citron import photo, shade, zoomed, shadow, swap, sopalin
from scenes_avocat2 import ob, wrapped, BOX_O, BOX_F, TOP
from scenes_avocat3 import (ZB_OPEN, ZB_SHUT, BIN_X, BIN_W, BIN_BOT, bsrc, bin_img, lid, speed_fx, in_bin,
                            LID_REST)

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


NOY, GRAINE, GERME, TREE = "mangue/noyau_h", "mangue/graine_h", "mangue/graine_germee_h", "mangue/manguier"

# ============================================================ A. LA CUISINE (0 → 5.15)
# la mangue coupée sur la planche, le noyau dans la moitié gauche ; la poubelle en zinc (~28 cm) sur le plan de travail.
# Le couvercle se pose devant ; le noyau sort de la mangue et tombe dans la poubelle (devant le bord arrière, derrière
# le bord avant) ; STOP, il ressort (◀◀) ; ▶▶ sur la planche : noyau → graine → graine germée → manguier.
MANGO = "banque/mangue_coupee"
M_C, M_W = (383, 1170), 470                    # mangue (centre du cadre utile, largeur) : ~15 cm par moitié
M_K = M_W / 1254
CAV = (M_C[0] + (400 - 627) * M_K, M_C[1] + (565 - 624) * M_K)   # creux de la moitié gauche
CAV_ROT = -47                                  # axe du creux (descend vers la droite)
PL = 190                                       # longueur du noyau (~10 cm)
GROW_C = (560, 1300)
GROW = [(NOY, 300), (GRAINE, 290), (GERME, 310), (TREE, 400)]
GROW_T0, GROW_DT = 2.45, 0.32


def grow_state(t):
    if t < GROW_T0:
        return GROW[0], 1.0
    i = int(clamp((t - GROW_T0) / GROW_DT, 0, len(GROW) - 1.001))
    p = (t - GROW_T0 - i * GROW_DT) / GROW_DT
    which, sc = swap(p)
    return GROW[min(len(GROW) - 1, i + which)], sc


def s_open(t):
    w = photo("citron_fond_cuisine.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out = ease_in((t - 2.2) / 0.4)                      # avance rapide : poubelle, couvercle et mangue s'en vont
    bdx, adx = 700 * out, -800 * out
    shake = math.sin(t * 60) * 5 * fade(t, 1.05, 1.35, 0.02, 0.2) if 1.05 < t < 1.35 else 0.0
    # --- la mangue coupée sur la planche
    if adx > -700:
        shadow(w, M_C[0] + adx, M_C[1] + 0.27 * M_W, M_W * 0.95, 55)
        place(w, MANGO, (0, 0, 1254, 1254), M_K, 627, 624, M_C[0] + adx, M_C[1])
    # --- la poubelle : fermée → ouverte (le couvercle se soulève à 0,15 puis se pose devant 0,35 → 0,7)
    up = ease_out((t - 0.15) / 0.2)
    slide = ease_io((t - 0.35) / 0.35)
    lox, loy = bsrc(512, 305)
    lx = lerp(lox, LID_REST[0], slide)
    ly = lerp(loy - 120 * up, LID_REST[1], slide) - math.sin(math.pi * slide) * 110
    if bdx < 600:
        shadow(w, BIN_X + bdx, BIN_BOT, BIN_W * 0.95)
        bin_img(w, ZB_SHUT if t < 0.15 else ZB_OPEN, bdx + shake)
    target = bsrc(512, 300)                             # fond de l'ouverture
    hover = (BIN_X, bsrc(0, 60)[1])                     # juste au-dessus de la poubelle
    inside, depth = False, 0.0
    if t < 0.45:                                        # dans le creux de la mangue
        x, y, rot = CAV[0], CAV[1], CAV_ROT
    elif t < 0.72:                                      # on le retire de la mangue
        p = ease_out((t - 0.45) / 0.27)
        x, y, rot = CAV[0], CAV[1] - 120 * p, lerp(CAV_ROT, 0, p)
    elif t < 1.05:                                      # lancé en cloche dans la poubelle
        p = ease_io((t - 0.72) / 0.33)
        x = lerp(CAV[0], target[0], p)
        y = lerp(CAV[1] - 120, target[1], p) - math.sin(math.pi * p) * 260
        rot, inside = -280 * p, p > 0.7
        depth = clamp((p - 0.85) / 0.15) * 0.4
    elif t < 1.66:
        x, y, rot, inside, depth = target[0], target[1] + 40, -280, True, 0.55
    elif t < 2.1:                                       # ◀◀ on le récupère : il ressort
        p = ease_out((t - 1.66) / 0.44)
        x, y, rot = target[0], lerp(target[1] + 40, hover[1], p), -280 * (1 - p)
        inside, depth = p < 0.55, 0.55 * (1 - p)
    else:
        x, y, rot = hover[0], hover[1], 0.0
    if t >= 0.15:
        if slide > 0.55:
            shadow(w, LID_REST[0] + adx, LID_REST[1], 360 * clamp((slide - 0.55) / 0.45), 60)
        if adx > -700:
            lid(w, lx + adx, ly, -8 * up * (1 - slide))
    if t < 2.2:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t < 0.45:
            shadow(lay, x + 6, y + 40, PL * 0.7, 70)
        ob(lay, NOY, x, y, PL, rot=rot)
        if inside:
            in_bin(lay, depth)
        w.alpha_composite(lay)
    else:
        (name, wd), sc = grow_state(t)
        p = ease_io((t - 2.2) / 0.25)
        gx = lerp(hover[0], GROW_C[0], p)
        gb = lerp(hover[1] + PL * 0.3, GROW_C[1], p)
        wd = lerp(PL, wd, p) if name == NOY else wd
        shadow(w, gx, gb, wd * 0.8 * sc, 70)
        ob(w, name, gx, gb, wd * sc, anchor="bottom")
    if 0.45 < t < 0.75:
        particles(w, t, 0.47, CAV[0], CAV[1], 8, 3, col=(250, 175, 30), size=8, up=160)
    if 1.06 < t < 1.45:
        particles(w, t, 1.07, BIN_X, bsrc(0, 220)[1], 9, 3, col=(170, 170, 170), size=6, up=200)
    # --- caméra : plan large de la cuisine, puis on se rapproche de la planche pour l'avance rapide
    zk = ease_io((t - 2.25) / 0.45)
    z = lerp(lerp(1.15, 1.1, ease_out(t / 0.6)), 1.45, zk)
    fx, fy = lerp(600, GROW_C[0], zk), lerp(1200, 1000, zk)
    w = zoomed(w, z, fx, fy)
    w.alpha_composite(shade())
    if t > GROW_T0 + 3 * GROW_DT - 0.1:
        sparkles(u, t, GROW_T0 + 3 * GROW_DT, 540, 900, 360, 10, 7)
    speed_fx(u, t, 1.66, 2.12, forward=False)
    speed_fx(u, t, 2.2, GROW_T0 + 3 * GROW_DT + 0.1, forward=True)
    title(u, "TU JETTES ÇA ?", t, 0.05, 1.62, y=330, color=YEL, size=165)
    title(u, "STOP !", t, 1.66, 2.2, y=330, color=RED, size=190)
    title(u, "SUPERBE PLANTE", t, 3.22, 4.1, y=330, color=YEL, size=150)
    stamp(u, "D'INTÉRIEUR !", 540, 340, t, 4.14, 5.15, GREEN, 125, -7)
    return w, u


cue(0.0, "pop_lo", 0.25)
cue(0.17, "click", 0.35)
cue(0.47, "squish", 0.25)
cue(0.74, "whoosh", 0.25)
cue(1.05, "thud", 0.45)
cue(1.68, "alert3", 0.32)
cue(2.22, "rise", 0.3)
for _i in range(1, len(GROW)):
    cue(GROW_T0 + (_i - 0.5) * GROW_DT, "pop_hi", 0.18)
cue(3.4, "success", 0.3)
cue(4.16, "pop", 0.25)


# ============================================================ B. LE NOYAU : NETTOIE À L'EAU, OUVRE PAR LE CÔTÉ (5.15 → 8.75)
PK = 0.92                                      # échelle du noyau (photo 1024) : il fait presque tout l'écran
PX, PY = 540, TABLE - 40


def s_pit(t):
    w, u = new_layers(background("table"))
    scrape = ease_io((t - 6.05) / 0.45)                  # l'eau emporte la pulpe
    pop = life(t, 5.15, dur=0.35)
    shadow(w, PX, PY, 600 * pop)
    pit(w, PX, PY, PK, scrape, 0.0, pop)
    cy = PY - (PIT_BOT - PIT_C[1]) * PK
    if 5.95 < t < 6.6:                                  # filet d'eau
        for i in range(14):
            tt = (t - 5.95 - i * 0.045) % 0.4
            put(w, icon("drop", 40), PX - 220 + (i * 53) % 440, lerp(cy - 420, cy - 40, tt / 0.4), 1, 0,
                1 - tt / 0.4)
        particles(w, t, 6.05, PX, cy, 14, 5, col=(250, 175, 30), size=10, up=240, dur=0.6)
    # ciseaux : le long du côté
    p0 = (PX + (PIT_RX - 10) * PK, cy)
    p1 = (PX - (PIT_RX - 40) * PK, cy)
    cut = clamp((t - 7.3) / 1.1)
    a = fade(t, 6.75, None, 0.2)
    if t > 6.75:
        dashed(u, (lerp(p0[0], p1[0], cut), cy), p1, a)
        if cut > 0:
            ImageDraw.Draw(w).line([p0, (lerp(p0[0], p1[0], cut), cy)], fill=(90, 70, 40), width=6)
    scissors(u, p0, p1, (t - 7.25) / 1.2, flip=True, hh=170)
    if t > 8.14:
        tag(u, "LE CÔTÉ", 860, cy - 260, t, 8.14, None, rot=-5, size=56, string_to=(p0[0] - 10, cy - 20))
    put(u, num_badge("1", 150), 150, 560, life(t, 5.2, 6.4))
    put(u, num_badge("2", 150), 150, 560, life(t, 6.5, 8.7))
    title(u, "NETTOIE-LA", t, 5.22, 6.0, y=330, size=170)
    title(u, "À L'EAU", t, 6.06, 6.42, y=330, color=YEL, size=180)
    title(u, "OUVRE LA COQUE", t, 6.48, 7.45, y=330, size=135)
    title(u, "AU CISEAU", t, 7.5, 8.1, y=330, color=YEL, size=170)
    title(u, "PAR LE CÔTÉ", t, 8.14, None, y=330, size=150)
    return w, u


cue(5.18, "pop", 0.25)
cue(5.98, "splash", 0.32)
cue(6.5, "pop_hi", 0.2)
cue(7.32, "chop", 0.4)
cue(7.9, "chop", 0.4)
cue(8.16, "pop", 0.2)


# ============================================================ C. UNE GROSSE GRAINE, UN HARICOT GÉANT (8.75 → 12.25)
def s_inside(t):
    w, u = new_layers(background("table"))
    k = PK
    top, bot = pit_halves()
    gone = ease_io((t - 9.9) / 0.4)
    op = ease_out((t - 8.85) / 0.45)
    sz = int(1024 * k)
    if gone < 1:
        shadow(w, PX, PY, 600)
        b = bot.resize((sz, sz), Image.BICUBIC)
        put(w, b, PX + (512 - PIT_C[0]) * k - 260 * gone, PY + (512 - PIT_BOT) * k, 1.0, 0, 1 - gone)
    # la graine : d'abord dans la coque, puis elle grossit au centre
    gw = lerp(430, 640, ease_out((t - 9.9) / 0.5))
    gy = lerp(PY - 60, PY, gone)
    if gone > 0.3:
        shadow(w, PX, PY, gw * 0.85)
    ob(w, GRAINE, PX, gy, gw, s=life(t, 8.8, dur=0.2) if t < 9.9 else 1.0, anchor="bottom")
    if gone < 1:
        tp = top.resize((sz, sz), Image.BICUBIC)
        hx, hy = PX - (PIT_RX - 30) * k, PY - (PIT_BOT - PIT_C[1]) * k
        D = 2 * sz
        can = Image.new("RGBA", (D, D), (0, 0, 0, 0))
        can.alpha_composite(tp, (int(D / 2 - (512 + (PIT_C[0] - 512) - (PIT_RX - 30)) * k), int(D / 2 - PIT_C[1] * k)))
        can = can.rotate(55 * op, center=(D / 2, D / 2), resample=Image.BICUBIC)
        put(w, can, hx, hy - 40 * op - 300 * gone, 1.0, 0, 1 - gone)
    if t > 8.9:
        sparkles(u, t, 8.95, PX, PY - 200, 300, 8, 3)
    if t > 11.4:
        wob = math.sin((t - 11.4) * 9) * 4 * math.exp(-(t - 11.4) * 2)
        tag(u, "HARICOT GÉANT !", 790, TABLE - 470, t, 11.46, None, rot=-6 + wob, size=56)
    title(u, "À L'INTÉRIEUR…", t, 8.85, 9.88, y=330, size=150)
    title(u, "UNE GROSSE GRAINE", t, 9.94, None, y=330, color=YEL, size=125)
    return w, u


cue(8.95, "crunch", 0.45)
cue(10.2, "pop_hi", 0.25)
cue(11.5, "ding", 0.25)


# ============================================================ D. SOPALIN HUMIDE, BOÎTE FERMÉE, AU CHAUD (12.25 → 16.1)
SX, SY, SW = 540, 1250, 400             # sopalin (même place que dans la boîte)
BOX_C = (540, 1135)
SEED_W = 270


def s_wrap(t):
    w, u = new_layers(background("table"))
    warm_glow(w, fade(t, 15.62, None, 0.5))
    sop_in = ease_out((t - 12.3) / 0.3)
    land = ease_out((t - 12.45) / 0.35)
    if t < 12.8:
        sopalin(w, SX, lerp(SY + 500, SY, sop_in), SW, 1.0, 0.0)
        ob(w, GRAINE, SX, lerp(SY - 520, SY - SEED_W * 0.18, land), lerp(400, SEED_W, land), rot=-10 * land)
    else:
        wrapped(w, SX, SY, SW, GRAINE, SEED_W, ease_io((t - 12.8) / 0.8), ease_out((t - 13.66) / 0.5))
    if 13.66 < t < 14.1:
        for i in range(8):
            tt = (t - 13.66 - i * 0.04) % 0.35
            put(w, icon("drop", 30), SX - 130 + i * 38, lerp(SY - 280, SY - 20, tt / 0.35), 1, 0, 1)
    if t > 14.2:
        bx = lerp(1300, BOX_C[0], ease_out((t - 14.2) / 0.4))
        shadow(w, bx, BOX_C[1] + 225, 660)
        which, sc = swap((t - 14.9) / 0.3)
        ob(w, BOX_O if which == 0 else BOX_F, bx, BOX_C[1] - (6 if which else 0), 730 * sc)
    w = zoomed(w, 1.3, 540, 1130)
    if t > 15.62:
        put(u, icon("thermo", 150), 170, 640, life(t, 15.66))
        put(u, icon("sun", 160), 910, 640, life(t, 15.76), t * 25)
    put(u, num_badge("3", 150), 150, 560, life(t, 12.3, 15.5))
    title(u, "ENROULE-LA", t, 12.3, 13.1, y=330, color=YEL, size=165)
    title(u, "ESSUIE-TOUT HUMIDE", t, 13.14, 14.05, y=330, size=118)
    title(u, "BOÎTE FERMÉE", t, 14.1, 15.55, y=330, color=YEL, size=145)
    title(u, "AU CHAUD !", t, 15.62, None, y=330, size=165)
    return w, u


cue(12.32, "pop", 0.22)
cue(12.85, "stir", 0.22)
cue(13.7, "plop", 0.25)
cue(14.25, "whoosh", 0.16)
cue(14.98, "click", 0.4)
cue(15.68, "rise", 0.18)


# ============================================================ E. LE BUFFET : 1 À 2 SEMAINES (16.1 → 17.7)
def s_wait(t):
    w = photo("citron_fond_buffet.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    light_rays(w, 260, 0, t, fade(t, 16.2, None, 0.5))
    land = ease_out((t - 16.12) / 0.35)
    bx, by = TOP[0], lerp(TOP[1] - 500, TOP[1] - 100, land)
    shadow(w, TOP[0], TOP[1], 330 * land)
    sopalin(w, bx, by + 78, 250, 1.0, 1.0)
    ob(w, GRAINE, bx, by + 45, 165, rot=-10)
    ob(w, BOX_F, bx, by, 430)
    ob(w, GRAINE, bx, by + 45, 165, rot=-10, alpha=0.6)
    if 16.5 < t < 17.7:   # les jours et les nuits défilent
        night = 0.5 + 0.5 * math.sin((t - 16.5) * 12)
        w.alpha_composite(Image.new("RGBA", (W, H), (20, 26, 60, int(95 * night * fade(t, 16.5, 17.7, 0.15, 0.15)))))
    w = zoomed(w, lerp(1.0, 1.3, ease_io((t - 16.1) / 1.6)), TOP[0], TOP[1] - 120)
    w.alpha_composite(shade())
    if 16.3 < t < 17.7:
        pills(u, ["1 SEMAINE", "2 SEMAINES"], 0 if t < 16.6 else 1, t, 16.3, 17.65, y=1100, pw=300)
    title(u, "1 À 2 SEMAINES", t, 16.14, 17.1, y=1300, color=YEL, size=135)
    title(u, "PLUS TARD…", t, 17.14, None, y=1300, size=150)
    return w, u


cue(16.14, "thud", 0.3)
cue(16.36, "tick", 0.24)
cue(16.62, "tick", 0.24)


# ============================================================ F. GROS PLAN : UNE RACINE SORT (17.7 → 18.75)
def s_macro(t):
    w, u = new_layers(background("table"))
    light_rays(w, 200, 0, t, 0.8)
    which, sc = swap((t - 17.8) / 0.3)
    shake = math.sin(t * 70) * 7 * fade(t, 17.72, 17.95, 0.02, 0.1) if 17.72 < t < 17.95 else 0.0
    MW = 700
    shadow(w, 540, TABLE + 10, MW * 0.8)
    ob(w, GRAINE if which == 0 else GERME, 540 + shake, TABLE + 10, MW * sc, anchor="bottom")
    if t > 18.0:   # départ de la racine (en bas à gauche de graine_germee_h)
        rx, ry = 540 - 0.33 * MW, TABLE - 0.12 * MW
        hl_ellipse(u, rx, ry, 110, 110, life(t, 18.02))
        tag(u, "RACINE !", 800, ry + 170, t, 18.05, None, rot=5, size=62, string_to=(rx + 90, ry + 30))
        sparkles(u, t, 18.0, rx, ry, 200, 8, 9)
    title(u, "UNE RACINE SORT !", t, 17.74, None, y=330, color=YEL, size=135)
    return w, u


cue(17.82, "crunch", 0.4)
cue(18.05, "pop_hi", 0.25)


# ============================================================ G. LE MANGUIER SUR LE BUFFET + ABONNE-TOI (18.75 → fin)
def s_end(t):
    w = photo("citron_fond_buffet.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    q = ease_out((t - 18.8) / 0.45)
    shadow(w, TOP[0], TOP[1], 300 * q)
    ob(w, TREE, TOP[0], TOP[1], 300, s=life(t, 18.8, dur=0.45), anchor="bottom")
    w = zoomed(w, 1.6, TOP[0], TOP[1] - 230)
    sparkles(u, t, 19.0, 540, 760, 330, 10, 7)
    w.alpha_composite(shade())
    if t > 20.6:
        clicked = t > 21.7
        btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
        press = 1 - 0.08 * math.sin(math.pi * clamp((t - 21.65) / 0.15))
        put(u, btn, 540, 1240, life(t, 20.65) * press)
        if t > 21.2:
            k = ease_out((t - 21.2) / 0.4)
            put(u, icon("cursor", 110), lerp(900, 640, k), lerp(1520, 1280, k), 1)
        put(u, logo_img(260), 540, 330, life(t, 22.4, dur=0.45))
        sparkles(u, t, 22.5, 540, 330, 200, 10, 12)
    title(u, "UNE PLANTE MAGNIFIQUE !", t, 18.82, 20.5, y=330, color=YEL, size=110)
    return w, u


cue(18.82, "pop_lo", 0.3)
cue(19.75, "success", 0.3)
cue(21.68, "click", 0.45)
cue(22.5, "sparkle", 0.25)

SCENES = [
    (0.0, 5.15, s_open),
    (5.15, 8.75, s_pit),
    (8.75, 12.25, s_inside),
    (12.25, 16.1, s_wrap),
    (16.1, 17.7, s_wait),
    (17.7, 18.75, s_macro),
    (18.75, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
