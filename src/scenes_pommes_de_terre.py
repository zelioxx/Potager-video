"""Storyboard « Pomme de terre verte : poison… ou trésor ? » (voix : assets/audio/pommes_de_terre/voix.mp3).

Volume de la voix gardé tel qu'envoyé (render.py « af »). Décors fournis : placard, plan de travail de la cuisine,
rebord de fenêtre, jardin à la terre retournée.
0–4.35    le placard : une pomme de terre verte, « elle peut te rendre malade ».
4.35–11.2 le plan de travail : elle germe, verdit ; coupée en deux : la solanine ; ne la mange pas.
11.2–13.15 … mais ne la jette pas.
13.15–14.65 le rebord de fenêtre : elle germe à la lumière, dans une boîte à œufs.
14.65–18.7 le jardin : on la plante au printemps, elle pousse, on récolte une dizaine de pommes de terre.
18.7–fin le panier de pommes de terre sur le plan de travail + S'abonner + logo.
"""
import math

from PIL import Image, ImageDraw

from gfx import (W, H, YEL, RED, GREEN, DARK, WHITE, put, title, life, fade, ease_out, ease_io, ease_in, clamp,
                 lerp, icon, tag, button_img, hl_ellipse, particles, light_rays, text_img, F_TITLE, pills)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade, shadow, swap
from scenes_banane import ob
from scenes_eau_pates import Cam
from scenes_parler_plantes import emoji

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


B = "banque/"
PDT, GERMEE, VERTE, COUPEE = B + "pdt", B + "pdt_germee", B + "pdt_verte", B + "pdt_verte_coupee"
BOITE, JEUNE, FLEURI, PANIER = B + "boite_oeufs_vide", B + "pdt_jeune_plant", B + "pdt_plant_fleuri", B + "panier_pdt"
PLACARD, CUISINE = "fond_placard.webp", "decor_cuisine_planche_fenetre.jpg"
REBORD, JARDIN = "decor_rebord_fenetre_radiateur.jpg", "tulipes_fond_sol_nu.png"


def no(u, ch, x, y, s, size=170):
    """Emoji barré (interdit)."""
    if s <= 0.01:
        return
    put(u, emoji(ch, size), x, y, s)
    put(u, icon("nosign", int(size * 1.35)), x, y, s)


# ============================================================ A. LE PLACARD (0 → 4.35)
PL = (575, 1588)                                 # sur l'étagère du bas, entre les deux paniers


def s_placard(t):
    zin = ease_io(t / 0.9)
    zout = ease_io((t - 2.6) / 0.8)
    z = lerp(lerp(1.15, 2.3, zin), 1.35, zout)
    cam = Cam(z, lerp(560, PL[0], zin * (1 - zout)), lerp(1250, PL[1] - 120, zin) * (1 - zout) + 1350 * zout)
    w = cam.bg(PLACARD)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x, y = cam.p(*PL)
    shadow(w, x, y, 95 * cam.z, 70)
    ob(w, VERTE, x, y, 105 * cam.z, anchor="bottom", s=life(t, 0.05, dur=0.35))
    w.alpha_composite(shade())
    if 1.75 < t < 2.65:
        put(u, emoji("🤢", 200), 820, 760, life(t, 1.8, 2.6))
    if t > 2.75:
        hl_ellipse(u, x, y - 45 * cam.z, 85 * cam.z, 55 * cam.z, life(t, 2.8))
        tag(u, "ELLE EST LÀ !", 300, 700, t, 2.85, None, rot=-5, size=56, string_to=(x - 60 * cam.z, y - 60 * cam.z))
    title(u, "CETTE POMME DE TERRE…", t, 0.05, 1.7, y=330, color=YEL, size=115)
    stamp(u, "PEUT TE RENDRE MALADE !", 540, 340, t, 1.75, 2.6, RED, 95, -6)
    title(u, "DANS TON PLACARD !", t, 2.65, None, y=330, size=125)
    return w, u


cue(0.05, "whoosh_up", 0.15)
cue(1.78, "alert1", 0.3)
cue(2.68, "whoosh", 0.16)
cue(2.88, "pop", 0.2)


# ============================================================ B-C-D. LE PLAN DE TRAVAIL (4.35 → 13.15)
BD = (545, 1600)                                 # sur la planche (coordonnées de la photo)
STEPS = [(4.35, PDT, 300), (4.9, GERMEE, 320), (5.45, VERTE, 300), (6.4, COUPEE, 340), (11.25, GERMEE, 320)]


def s_board(t):
    cam = Cam(lerp(1.3, 1.45, ease_io((t - 4.35) / 2.0)), 545, 1350)
    w = cam.bg(CUISINE)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    i = max(k for k, (t0, _, _) in enumerate(STEPS) if t >= t0 or k == 0)
    t0, name, wd = STEPS[i]
    prev = STEPS[i - 1] if i > 0 else STEPS[0]
    which, sc = swap((t - t0 + 0.15) / 0.3) if i > 0 else (1, 1.0)
    name, wd = (name, wd) if which else (prev[1], prev[2])
    x, y = cam.p(*BD)
    shake = math.sin(t * 60) * 6 * fade(t, 6.45, 6.8, 0.02, 0.2) if 6.45 < t < 6.8 else 0.0
    shadow(w, x, y, wd * 0.8 * z, 70)
    ob(w, name, x + shake, y, wd * z * sc * life(t, 4.35, dur=0.3), anchor="bottom")
    if 6.4 < t < 6.7:
        particles(w, t, 6.42, x, y - 60 * z, 10, 3, col=(235, 225, 160), size=8, up=200, dur=0.3)
    w.alpha_composite(shade())
    # poison : les parties vertes clignotent, la solanine
    if 6.5 < t < 11.2:
        a = (0.5 + 0.5 * math.sin((t - 6.5) * 8)) * fade(t, 6.5, 11.15, 0.2, 0.2)
        for dx in (-150, 150):
            hl_ellipse(u, x + dx * z, y - 75 * z, 45 * z, 80 * z, a, width=8)
    if t > 7.67:
        put(u, emoji("☠", 170), 860, 640, life(t, 7.7, 11.15))
        tag(u, "SOLANINE", 270, 700, t, 7.72, 11.15, rot=-5, size=66, string_to=(x - 150 * z, y - 120 * z))
    if 10.05 < t < 11.2:
        no(u, "🍴", 860, 900, life(t, 10.1, 11.15))
    if t > 11.85:
        no(u, "🗑", 850, 760, life(t, 11.9, 13.1))
    title(u, "QUAND ELLE GERME…", t, 4.4, 5.4, y=330, size=135)
    title(u, "OU DEVIENT VERTE", t, 5.45, 6.35, y=330, color=GREEN, size=135)
    stamp(u, "POISON !", 540, 340, t, 6.4, 7.6, RED, 170, -8)
    title(u, "LA SOLANINE", t, 7.67, 8.65, y=330, color=YEL, size=150)
    title(u, "TRÈS VERTE ?", t, 8.7, 10.05, y=330, size=165)
    stamp(u, "NE LA MANGE PAS !", 540, 340, t, 10.1, 11.2, RED, 115, -7)
    title(u, "MAIS ATTENDS…", t, 11.25, 11.85, y=330, color=YEL, size=150)
    stamp(u, "NE LA JETTE PAS !", 540, 340, t, 11.9, None, GREEN, 115, -6)
    return w, u


cue(4.38, "pop", 0.2)
cue(4.92, "pop_hi", 0.2)
cue(5.47, "pop_hi", 0.2)
cue(6.42, "chop", 0.35)
cue(6.5, "alert3", 0.24)
cue(7.72, "pop", 0.22)
cue(10.12, "alert2", 0.28)
cue(11.27, "pop_hi", 0.2)
cue(11.92, "ding", 0.26)


# ============================================================ E. LE REBORD : GERMER À LA LUMIÈRE (13.15 → 14.65)
BOX = (540, 1290, 640)                           # boîte à œufs sur le rebord : bas-centre, largeur
CELLS = [(-0.33, 13.25), (-0.11, 13.4), (0.11, 13.55), (0.33, 13.7)]


def s_window(t):
    cam = Cam(1.25, 540, 1050)
    w = cam.bg(REBORD)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    light_rays(w, 300, 200, t, fade(t, 13.2, None, 0.4))
    bx, by = cam.p(BOX[0], BOX[1])
    bw = BOX[2] * z
    shadow(w, bx, by, bw * 0.95, 60)
    ob(w, BOITE, bx, by, bw, anchor="bottom", s=life(t, 13.15, dur=0.3))
    for fx, t0 in CELLS:   # les pommes de terre germées dans les alvéoles
        d = ease_out((t - t0) / 0.3)
        if d > 0:
            ob(w, GERMEE, bx + fx * bw, lerp(by - 700, by - 0.2 * bw, d), 0.25 * bw, anchor="bottom",
               rot=(fx * 20))
    w.alpha_composite(shade())
    put(u, icon("sun", 170), 880, 620, life(t, 13.3), t * 30)
    title(u, "LAISSE-LA GERMER", t, 13.2, 14.0, y=330, size=135)
    title(u, "À LA LUMIÈRE !", t, 14.05, None, y=330, color=YEL, size=150)
    return w, u


cue(13.18, "whoosh", 0.16)
for _k in range(4):
    cue(13.3 + _k * 0.15, "plop", 0.16)
cue(14.07, "rise", 0.18)


# ============================================================ F. LE JARDIN : PLANTE-LA, RÉCOLTE (14.65 → 18.7)
PLANT = (540, 1440, 540)                         # pied de pomme de terre : bas de la butte, largeur
HARVEST = [(-330, 1470, 17.1), (-190, 1510, 17.18), (-60, 1530, 17.26), (80, 1525, 17.34), (220, 1505, 17.42),
           (340, 1465, 17.5), (-270, 1380, 17.58), (290, 1385, 17.66), (-140, 1420, 17.74), (160, 1425, 17.82)]


def s_garden(t):
    cam = Cam(1.05, 540, 1150)
    w = cam.bg(JARDIN)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    px, py = cam.p(PLANT[0], PLANT[1])
    pw = PLANT[2] * z
    if t < 15.85:   # on la plante : le trou, elle tombe dedans, la terre la recouvre
        hole = life(t, 14.7, 15.6, dur=0.2)
        if hole > 0.01:
            d = ImageDraw.Draw(w)
            d.ellipse([px - 90 * z, py - 60 * z, px + 90 * z, py - 10 * z], fill=(35, 24, 16, int(235 * hole)))
        drop = ease_in((t - 14.75) / 0.35)
        if drop < 1:
            ob(w, GERMEE, px, lerp(py - 700, py - 30, drop), 150 * z, anchor="bottom", rot=-20 * (1 - drop))
        if 15.1 < t < 15.6:
            particles(w, t, 15.12, px, py - 40, 16, 5, col=(55, 38, 26), size=10, up=180, dur=0.5)
    else:           # une seule patate… un pied qui pousse et fleurit
        which, sc = swap((t - 16.4) / 0.3)
        g = life(t, 15.87, dur=0.4)
        ob(w, JEUNE if which == 0 else FLEURI, px, py, pw * (0.85 if which == 0 else 1.0) * sc * g, anchor="bottom")
    # … et une dizaine de pommes de terre à récolter
    n = 0
    for dx, yy, t0 in HARVEST:
        a = life(t, t0, dur=0.25)
        if a > 0.01:
            n += 1
            hx, hy = cam.p(PLANT[0] + dx, yy)
            shadow(w, hx, hy, 100 * z * a, 60)
            ob(w, PDT, hx, hy - 40 * (1 - a), 120 * z * a, anchor="bottom", rot=(dx % 40) - 20)
    w.alpha_composite(shade())
    if t > 17.1:
        put(u, text_img(f"x{n}", F_TITLE, 200, YEL, 10, DARK, 8, DARK), 850, 640, life(t, 17.1))
    if 14.95 < t < 15.85:
        pills(u, ["MARS", "AVRIL", "MAI"], 1, t, 15.0, 15.8, y=560, pw=210)
    if t > 18.0:
        sparkles(u, t, 18.0, 540, 1150, 420, 12, 7)
    title(u, "PLANTE-LA", t, 14.7, 15.25, y=330, color=YEL, size=170)
    title(u, "AU PRINTEMPS", t, 15.3, 15.85, y=330, size=150)
    title(u, "UNE SEULE PATATE…", t, 15.9, 17.0, y=330, size=130)
    stamp(u, "UNE DIZAINE !", 540, 340, t, 17.05, None, GREEN, 140, -7)
    return w, u


cue(14.72, "whoosh", 0.16)
cue(15.08, "thud", 0.28)
cue(15.15, "rustle", 0.2)
cue(15.9, "rise", 0.2)
cue(16.42, "pop_hi", 0.22)
for _k in range(0, 10, 2):
    cue(HARVEST[_k][2], "pop", 0.14)
cue(18.02, "success", 0.26)


# ============================================================ G. LE PANIER + ABONNE-TOI (18.7 → fin)
def s_end(t):
    cam = Cam(1.3, 545, 1350)
    w = cam.bg(CUISINE)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    x, y = cam.p(*BD)
    s_ = life(t, 18.72, dur=0.4)
    shadow(w, x, y, 360 * z * s_, 70)
    ob(w, PANIER, x, y, 400 * z, s=s_, anchor="bottom")
    w.alpha_composite(shade())
    sparkles(u, t, 18.85, x, y - 250, 260, 10, 7)
    clicked = t > 20.3
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 20.25) / 0.15))
    put(u, btn, 540, 780, life(t, 18.9) * press)
    if t > 19.8:
        k = ease_out((t - 19.8) / 0.4)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(1020, 820, k), 1)
    put(u, logo_img(230), 540, 560, life(t, 20.9, dur=0.45))
    sparkles(u, t, 21.0, 540, 560, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 18.75, None, y=330, color=YEL, size=135)
    return w, u


cue(18.75, "pop_lo", 0.28)
cue(20.28, "click", 0.45)
cue(21.0, "sparkle", 0.22)

SCENES = [
    (0.0, 4.35, s_placard),
    (4.35, 13.15, s_board),
    (13.15, 14.65, s_window),
    (14.65, 18.7, s_garden),
    (18.7, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
