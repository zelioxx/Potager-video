"""Storyboard « Parler à ses plantes, ça marche ? » (voix : assets/audio/parler_plantes/voix.mp3).

Volume de la voix gardé tel qu'envoyé (render.py « af »).
0–3.3   le coin du salon : on parle au pothos (bulles), tout le monde se moque (HAHA !).
3.3–5.5 « ce que dit la science » : la loupe (photo fournie) passe sur la plante.
5.5–9.2 fond beige : les mots ✗ (bla bla), les vibrations ✓ (ondes, la plante frémit).
9.2–13.5 l'étude : une chenille (photo fournie) grignote une feuille, crunch crunch, la plante réagit (alerte).
13.5–18.2 le vrai secret : dans le salon, la loupe sur les feuilles (tu les regardes), un arrosage, ✓ mieux soin.
18.2–fin S'abonner + logo.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, put, title, life, fade, ease_out, ease_io,
                 ease_in, clamp, lerp, icon, tag, button_img, hl_ellipse, particles, light_rays, text_img, F_BLACK,
                 F_TITLE)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp
from scenes_citron import shade, shadow
from scenes_banane import ob
from scenes_eau_pates import Cam, draw_plant, PL_X, PL_Y, PL_K, SAIN, POT_BASE, FULL

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


LOUPE, CHENILLE = "banque/loupe", "banque/chenille_arquee_g"
ARROSOIR = "banque/arrosoir_zinc"
GLASS_C, GLASS_R = (286.5, 367.5), 204.5        # verre de la loupe dans son cadre 1024
MOUTH = (317, 822)                              # bouche de la chenille (photo retournée, cadre 1024)


def bubble(c, txt, x, y, s, tail=(0, 1), size=58, col=WHITE):
    """Bulle de parole (x, y = centre), petite queue vers `tail` (direction)."""
    if s <= 0.01:
        return
    ti = text_img(txt, F_BLACK, int(size * s), DARK)
    w_, h_ = ti.width + 70 * s, ti.height + 44 * s
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    tx, ty = x + tail[0] * w_ * 0.3, y + h_ / 2
    d.polygon([(tx - 26 * s, ty - 6), (tx + 22 * s, ty - 6), (tx - 40 * s * tail[0] - 10 * s, ty + 50 * s)],
              fill=DARK)
    d.rounded_rectangle([x - w_ / 2 + 6, y - h_ / 2 + 8, x + w_ / 2 + 6, y + h_ / 2 + 8], radius=h_ / 2, fill=DARK)
    d.rounded_rectangle([x - w_ / 2, y - h_ / 2, x + w_ / 2, y + h_ / 2], radius=h_ / 2, fill=col, outline=DARK,
                        width=max(3, int(6 * s)))
    d.polygon([(tx - 18 * s, ty - 10), (tx + 14 * s, ty - 10), (tx - 34 * s * tail[0] - 6 * s, ty + 38 * s)],
              fill=col)
    ov.alpha_composite(ti, (int(x - ti.width / 2), int(y - ti.height / 2)))
    c.alpha_composite(ov)


def waves(c, t, x, y, a=1.0, n=4, rmax=330, ang=(-50, 50), col=WHITE, speed=1.2):
    """Ondes sonores (arcs concentriques qui s'éloignent)."""
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(n):
        p = (t * speed + i / n) % 1.0
        r = 40 + p * rmax
        d.arc([x - r, y - r, x + r, y + r], ang[0], ang[1], fill=col + (int(235 * a * (1 - p)),), width=12)
    c.alpha_composite(ov)


def magnifier(w, cx, cy, k, zoom=1.9, rot=0.0):
    """Pose la loupe (photo) avec le centre du verre en (cx, cy) ; dans le verre, le décor de `w` agrandi."""
    r = GLASS_R * k
    src = w.crop((int(cx - r / zoom), int(cy - r / zoom), int(cx + r / zoom), int(cy + r / zoom)))
    src = src.resize((int(2 * r), int(2 * r)), Image.BICUBIC)
    m = Image.new("L", src.size, 0)
    ImageDraw.Draw(m).ellipse([0, 0, src.width - 1, src.height - 1], fill=255)
    w.paste(src, (int(cx - r), int(cy - r)), m)
    place(w, LOUPE, FULL, k, *GLASS_C, cx, cy, 1.0, rot)


# ============================================================ A. LE SALON : TU PARLES À TES PLANTES ? (0 → 5.5)
def s_salon(t):
    zk = ease_io((t - 3.3) / 0.8)
    cam = Cam(lerp(1.25, 1.5, zk), lerp(640, 680, zk), lerp(900, 880, zk))
    w = cam.bg("fond_salon_coin2.jpg")
    draw_plant(w, t, cam)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # la loupe : « ce que dit la science »
    if t > 4.0:
        q = ease_out((t - 4.0) / 0.5)
        sweep = math.sin((t - 4.5) * 2.2) * 60 if t > 4.5 else 0
        lx, ly = lerp(1300, 600 + sweep, q), lerp(1300, 760, q)
        magnifier(w, lx, ly, 0.75, rot=15)
    w.alpha_composite(shade())
    bubble(u, "COUCOU MA BELLE !", 330, 640, life(t, 0.2, 1.6, dur=0.3), tail=(1, 1))
    bubble(u, "TU AS SOIF ?", 300, 820, life(t, 0.85, 1.6, dur=0.3), tail=(1, 1))
    if 1.65 < t < 3.3:
        for i, (hx, hy, rot, t0) in enumerate([(230, 650, -10, 1.7), (840, 560, 8, 1.85), (300, 1000, 6, 2.0),
                                               (850, 920, -6, 2.15)]):
            wob = math.sin((t - t0) * 14 + i) * 5
            tag(u, "HAHA !", hx, hy + wob, t, t0, 3.25, rot=rot + wob, size=60)
    title(u, "TU PARLES À TES PLANTES ?", t, 0.05, 1.6, y=330, color=YEL, size=108)
    title(u, "TOUT LE MONDE SE MOQUE…", t, 1.65, 3.2, y=330, color=RED, size=105)
    title(u, "ATTENDS…", t, 3.25, 4.6, y=330, size=170)
    stamp(u, "LA SCIENCE !", 540, 340, t, 4.65, None, GREEN, 140, -7)
    return w, u


cue(0.22, "pop", 0.22)
cue(0.87, "pop", 0.2)
cue(1.7, "pop_hi", 0.16)
cue(1.85, "pop_hi", 0.16)
cue(2.0, "pop_hi", 0.16)
cue(2.15, "pop_hi", 0.16)
cue(4.02, "whoosh", 0.18)
cue(4.68, "ding", 0.3)


# ============================================================ B. PAS LES MOTS, MAIS LES VIBRATIONS (5.5 → 9.2)
PK = 1.18
PX, PY = 600, TABLE + 40


def plant(c, X, Y, k, rot=0.0):
    shadow(c, X, Y, 330 * k, 80)
    place(c, SAIN, FULL, k, *POT_BASE, X, Y, 1.0, rot)


def s_vibes(t):
    w, u = new_layers(background("table"))
    shiver = math.sin(t * 38) * 1.4 * fade(t, 7.95, None, 0.2) if t > 7.95 else 0.0
    plant(w, PX, PY, PK * life(t, 5.5, dur=0.35), shiver)
    # « ne comprennent pas tes mots »
    if t < 7.6:
        bubble(u, "BLA BLA BLA…", 270, 760, life(t, 5.75, 7.55, dur=0.3), tail=(1, 1))
        put(u, icon("cross", 140), 470, 680, life(t, 6.85, 7.55))
    # « mais elles sentent les vibrations »
    if t > 7.7:
        a = fade(t, 7.7, None, 0.3)
        waves(u, t, 40, 860, a, n=5, rmax=520, ang=(-40, 40), col=YEL)
        put(u, icon("check", 140), 860, 600, life(t, 8.5))
        tag(u, "VIBRATIONS", 820, 470, t, 8.45, None, rot=-5, size=56)
    title(u, "PAS TES MOTS…", t, 5.6, 7.5, y=330, size=160)
    title(u, "MAIS LES VIBRATIONS !", t, 7.55, None, y=330, color=YEL, size=115)
    return w, u


cue(5.55, "whoosh", 0.16)
cue(5.78, "pop", 0.2)
cue(6.88, "alert2", 0.22)
cue(7.75, "rise", 0.22)
cue(8.52, "ding", 0.24)


# ============================================================ C. L'ÉTUDE : LA CHENILLE QUI MANGE (9.2 → 13.5)
CK = 2.6                                        # gros plan sur la feuille mangée
CX, CY = 600 - (686 - 525) * 2.6, 980 - (598 - 985) * 2.6
LEAF_EDGE = (674, 607)                           # bord haut-droit de la grande feuille (cadre 1024 du pothos)
BITES = [(672, 606, 0.0), (666, 590, 0.35), (679, 624, 0.7), (686, 642, 1.05)]
CHEW_T0 = 11.4


def s_study(t):
    w, u = new_layers(background("table"))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    place(lay, SAIN, FULL, CK, *POT_BASE, CX, CY, life(t, 9.2, dur=0.35))

    def P(x, y):
        return CX + (x - POT_BASE[0]) * CK, CY + (y - POT_BASE[1]) * CK

    ex, ey = P(*LEAF_EDGE)
    # les bouchées : trous dans la feuille
    if t > CHEW_T0:
        m = Image.new("L", (W, H), 255)
        d = ImageDraw.Draw(m)
        for bx, by, dt in BITES:
            if t > CHEW_T0 + dt:
                x, y = P(bx, by)
                r = 15 * CK
                d.ellipse([x - r, y - r, x + r, y + r], fill=0)
        lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
    # la plante « réagit » : ses feuilles rougissent par pulsations (alerte)
    react = fade(t, 12.05, None, 0.3)
    if react > 0.01:
        pulse = 0.5 + 0.5 * math.sin((t - 12.05) * 9)
        a = int(110 * react * (0.4 + 0.6 * pulse))
        tint = Image.new("RGBA", (W, H), RED + (a,))
        tint.putalpha(Image.composite(tint.getchannel("A"), Image.new("L", (W, H), 0), lay.getchannel("A")))
        glow = lay.getchannel("A").filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * a / 160))
        g = Image.new("RGBA", (W, H), RED + (0,))
        g.putalpha(glow)
        w.alpha_composite(g)
        lay.alpha_composite(tint)
    w.alpha_composite(lay)
    # la chenille arrive par la droite et grignote le bord de la feuille
    arrive = ease_out((t - 10.3) / 0.8)
    chew = math.sin((t - CHEW_T0) * 16) * 6 if t > CHEW_T0 else 0.0
    kc = 0.36
    mx, my = lerp(1350, ex + 6, arrive) + chew, ey + 10
    if t > 10.3:
        place(w, CHENILLE, FULL, kc, *MOUTH, mx, my, 1.0, -8 + chew * 0.6)
    if t > CHEW_T0:
        waves(u, t, ex + 20, ey, 1.0, n=3, rmax=260, ang=(180, 330), col=WHITE, speed=1.8)
        particles(w, t, t - (t % 0.35), ex, ey + 10, 5, int(t * 9) % 7, col=(90, 150, 60), size=6, up=180, dur=0.35)
        tag(u, "CRUNCH !", 850, ey - 300, t, CHEW_T0 + 0.05, None, rot=6, size=54)
    if react > 0.01:
        tag(u, "ELLE RÉAGIT !", 280, 620, t, 12.1, None, rot=-5, size=56)
    if t > 9.3:
        tag(u, "ÉTUDE SCIENTIFIQUE", 540, 470, t, 9.35, 11.3, rot=-3, size=50)
    title(u, "UNE ÉTUDE A MONTRÉ…", t, 9.25, 11.3, y=330, size=115)
    title(u, "LE BRUIT D'UNE CHENILLE", t, 11.35, 12.85, y=330, color=YEL, size=105)
    stamp(u, "ELLES RÉAGISSENT !", 540, 340, t, 12.9, None, RED, 108, -6)
    return w, u


cue(9.28, "pop", 0.22)
cue(10.32, "whoosh", 0.16)
for _k in range(4):
    cue(CHEW_T0 + _k * 0.35, "crunch", 0.22)
cue(12.1, "alert1", 0.28)


# ============================================================ D. LE VRAI SECRET : TU LES REGARDES, TU EN PRENDS SOIN (13.5 → 18.2)
def s_secret(t):
    cam = Cam(1.45, 680, 880)
    w = cam.bg("fond_salon_coin2.jpg")
    draw_plant(w, t, cam)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # « tu les regardes » : la loupe passe sur les feuilles
    if 15.6 < t < 17.1:
        q = ease_out((t - 15.6) / 0.4)
        out = ease_in((t - 16.75) / 0.35)
        sweep = math.sin((t - 15.6) * 3) * 90
        magnifier(w, lerp(1300, 560 + sweep, q) + 800 * out, lerp(1100, 820, q), 0.7, rot=15)
    # « tu prends mieux soin d'elles » : un petit arrosage
    if t > 16.95:
        cin = ease_out((t - 16.95) / 0.35)
        px, py = cam.p(PL_X, PL_Y - 200)
        tilt = -26 * ease_io((t - 17.25) / 0.2)
        ob(w, ARROSOIR, lerp(-250, px - 230, cin), py - 170, 330, rot=tilt, flip=True)
        if t > 17.4:
            d = ImageDraw.Draw(w)
            for k in range(6):
                p = (t * 3 + k / 6) % 1.0
                x, y = px - 70 + k * 6 + 30 * p, lerp(py - 150, py, p * p)
                d.ellipse([x - 4, y - 6, x + 4, y + 6], fill=(214, 234, 250, 225))
    w.alpha_composite(shade())
    if t > 17.55:
        put(u, icon("check", 170), 540, 640, life(t, 17.6))
        sparkles(u, t, 17.6, 600, 820, 330, 10, 7)
    if 14.55 < t < 15.6:
        bubble(u, "ÇA VA TOI ?", 330, 700, life(t, 14.6, 15.55, dur=0.3), tail=(1, 1))
    title(u, "LE VRAI SECRET ?", t, 13.55, 14.5, y=330, color=YEL, size=150)
    title(u, "QUAND TU LEUR PARLES…", t, 14.55, 15.55, y=330, size=110)
    title(u, "TU LES REGARDES", t, 15.6, 16.9, y=330, color=YEL, size=140)
    stamp(u, "TU EN PRENDS SOIN !", 540, 340, t, 16.95, None, GREEN, 105, -6)
    return w, u


cue(13.57, "whoosh_up", 0.16)
cue(14.62, "pop", 0.2)
cue(15.62, "whoosh", 0.16)
cue(17.0, "whoosh", 0.14)
cue(17.45, "pour", 0.22)
cue(17.62, "success", 0.28)


# ============================================================ E. ABONNE-TOI (18.2 → fin)
def s_end(t):
    cam = Cam(1.25, 640, 900)
    w = cam.bg("fond_salon_coin2.jpg")
    draw_plant(w, t, cam)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    sparkles(u, t, 18.3, 600, 760, 330, 10, 7)
    clicked = t > 19.7
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 19.65) / 0.15))
    put(u, btn, 540, 1420, life(t, 18.35) * press)
    if t > 19.2:
        k = ease_out((t - 19.2) / 0.4)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(1650, 1460, k), 1)
    put(u, logo_img(260), 540, 330, life(t, 20.4, dur=0.45))
    sparkles(u, t, 20.5, 540, 330, 200, 10, 12)
    bubble(u, "MERCI !", 820, 760, life(t, 18.5, 20.2, dur=0.3), tail=(-1, 1), col=CREAM)
    title(u, "PLUS D'ASTUCES ?", t, 18.25, 20.35, y=330, color=YEL, size=135)
    return w, u


cue(18.27, "pop_lo", 0.28)
cue(19.68, "click", 0.45)
cue(20.5, "sparkle", 0.25)

SCENES = [
    (0.0, 5.5, s_salon),
    (5.5, 9.2, s_vibes),
    (9.2, 13.5, s_study),
    (13.5, 18.2, s_secret),
    (18.2, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
