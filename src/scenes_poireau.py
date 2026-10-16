"""Storyboard « Refaire pousser un poireau à partir du pied » (voix : assets/audio/poireau/voix.mp3).

Même direction artistique que scenes.py : fond beige, table / terre, photos réelles détourées,
titres jaunes, badge d'étape haut-droite, transitions whip. Temps absolus calés sur la voix off.
"""
import math

import numpy as np
from PIL import Image

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, background, spr, put, title, life, fade, ease_out, ease_in,
                 ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse, hline, measure, roots,
                 particles, text_img, F_TITLE, F_BLACK, glass_back, glass_front, window_img, light_rays)
from scenes import TABLE, new_layers, drop, flies, sparkles

CUES = []


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


P = "poireau/"
FULL_H, TOP_H, BASE_H = 1132, 890, 242   # proportions de la photo du poireau entier (px)
LONG_H = 358                              # pied aux racines allongées
ROOT_FRAC = 0.46                          # part des racines en bas du pied


def leek(c, x, ground, h, top_dx=0.0, top_dy=0.0, top_rot=0.0, top_alpha=1.0, base=True, top=True,
         s=1.0, shadow=True, rotten=0.0):
    """Poireau entier = partie haute + pied (deux photos alignées, séparables pour la coupe)."""
    k = h * s / FULL_H
    bh, th = BASE_H * k, TOP_H * k
    if base:
        spr(c, P + "leek_base", x, ground, bh, shadow=shadow, rotten=rotten)
    if top and top_alpha > 0.01:
        spr(c, P + "leek_top", x + top_dx, ground - bh + top_dy, th, rot=top_rot, alpha=top_alpha, shadow=False)
    return bh


def base_piece(c, x, ground, bh, s=1.0, rotten=0.0, shadow=True, name="leek_base", sy=1.0):
    spr(c, P + name, x, ground, bh, s, shadow=shadow, rotten=rotten, sy=sy)


def pied(c, x, ground, k, g=0.0, long=False, rotten=0.0, shadow=True, s=1.0):
    """Pied coupé (+ repousse). La repousse est la vraie partie verte du même poireau, réduite
    d'un facteur g et ancrée au cœur du pied : tige et feuilles restent parfaitement alignées."""
    hh = (LONG_H if long else BASE_H) * k * s
    top_y = ground - hh
    if g > 0.01 and s > 0.01:
        spr(c, P + "leek_top", x, top_y + 8 * k * s, TOP_H * k * s * g, shadow=False, rotten=rotten)
    spr(c, P + ("leek_base_long" if long else "leek_base"), x, ground, hh, shadow=shadow, rotten=rotten)
    return top_y


# ============================================================ 1. STOP ! (0 → 3.15)
def s_stop(t):
    w, u = new_layers(background("table"))
    spr(w, P + "trash", 760, TABLE, 470, life(t, 0.0))
    # le pied tombait vers la poubelle… et se fige sur « Stop »
    k = ease_out(t / 0.35)
    shake = math.sin(t * 45) * 6 * fade(t, 0.0, 0.6)
    bx, by = lerp(560, 470, k) + shake, lerp(500, 980, k)
    base_piece(w, bx, by, 340, shadow=False)
    put(u, icon("cross", 200), 760, 860, life(t, 1.58), math.sin(t * 6) * 4)
    title(u, "STOP !", t, 0.0, 1.3, y=380, color=RED, size=230)
    title(u, "NE LE JETTE PAS !", t, 1.35, None, y=380, color=YEL, size=120)
    return w, u


cue(0.02, "thud", 0.5)
cue(0.05, "pop_lo", 0.45)
cue(1.35, "pop", 0.35)
cue(1.58, "pop_hi", 0.4)


# ============================================================ 2. ON EN REFAIT UN (3.15 → 6.8)
def s_regrow(t):
    w, u = new_layers(background("table"))
    k = ease_io((t - 4.9) / 0.5)
    bx = lerp(540, 300, k)
    base_piece(w, bx, TABLE, 380)
    hl_ellipse(w, bx, TABLE - 200, 190, 270, life(t, 4.18, 4.9))
    if t > 5.0:
        put(u, icon("arrow_down", 150), 540, 1000, life(t, 5.05), 90)
        leek(w, 790, TABLE, 1000, s=life(t, 5.26))
    sparkles(w, t, 5.3, 790, 600, 300, 8, 3)
    title(u, "1 PIED", t, 3.3, 5.0, y=360)
    title(u, "= 1 POIREAU", t, 5.26, None, y=360, size=140)
    put(u, icon("check", 150), 860, 1180, life(t, 6.38))
    return w, u


cue(3.3, "pop", 0.35)
cue(4.18, "pop_hi", 0.3)
cue(4.95, "whoosh_up", 0.25)
cue(5.26, "pop_lo", 0.45)
cue(5.3, "sparkle", 0.35)
cue(6.38, "success", 0.35)


# ============================================================ 3. GARDE LE PIED (6.8 → 10.4)
def s_keep(t):
    w, u = new_layers(background("table"))
    leek(w, 540, TABLE, 1300, s=life(t, 6.85, dur=0.4))
    bh = 1300 * BASE_H / FULL_H
    hl_ellipse(w, 540, TABLE - bh * 0.5, 210, bh * 0.55, life(t, 8.34))
    put(u, text_img("LE PIED", F_TITLE, 100, YEL, 11, DARK, 9, DARK), 830, TABLE - bh * 0.75, life(t, 8.6), -6)
    put(u, text_img("RACINES", F_TITLE, 74, CREAM, 9, DARK, 7, DARK), 290, TABLE - 40, life(t, 9.82), 5)
    title(u, "EN CUISINE", t, 7.1, 8.3, y=360)
    return w, u


cue(6.85, "pop_lo", 0.35)
cue(7.1, "rise", 0.25)
cue(8.34, "pop_hi", 0.35)
cue(8.6, "pop", 0.3)
cue(9.82, "pop", 0.3)


# ============================================================ 4. COUPE À 4-5 CM (10.4 → 15.3)
def s_cut(t):
    w, u = new_layers(background("table"))
    hgt = 1300
    bh = hgt * BASE_H / FULL_H
    cut_y = TABLE - bh
    # couteau : arrive par la droite puis tranche
    kin = ease_out((t - 10.45) / 0.35)
    kslice = ease_io((t - 11.0) / 0.25)
    kx = lerp(1500, 860, kin) - 520 * kslice
    kout = ease_in((t - 11.45) / 0.3)
    kx += 900 * kout
    # partie haute qui s'envole après la coupe
    off = ease_in((t - 11.3) / 0.6)
    leek(w, 540, TABLE, hgt, top_dx=-500 * off, top_dy=-700 * off, top_rot=40 * off, top_alpha=1 - off * 0.3)
    if 10.4 < t < 12.2:
        spr(w, P + "knife", kx, cut_y + 40, 120, shadow=False, rot=2)
    if t > 11.2:
        hline(w, 330, 750, cut_y, ease_out((t - 11.2) / 0.25), 10)
    root_y = TABLE - bh * ROOT_FRAC
    measure(u, 750, cut_y, root_y, "4-5 cm", life(t, 11.7))
    title(u, "COUPE", t, 10.5, 12.2, y=360)
    title(u, "PAS MOINS !", t, 14.38, None, y=360, color=RED, size=150)
    put(u, icon("cross", 130), 250, cut_y + 120, life(t, 14.5), math.sin(t * 9) * 6)
    return w, u


cue(10.45, "whoosh", 0.3)
cue(11.05, "chop", 0.65)
cue(11.35, "whoosh_up", 0.25)
cue(11.7, "pop_hi", 0.35)
cue(12.34, "tick", 0.3)
cue(14.38, "fail", 0.3)


# ============================================================ 5. VERRE D'EAU (15.3 → 19.7)
GX, GH, GW = 540, 560, 440
BH_G = 330  # hauteur du pied posé dans le verre
KG = BH_G / BASE_H


def glass_scene(w, t, water, base_y_off=0.0, base_s=1.0, base_vis=True, murky=0.0, rotten=0.0, gx=GX,
                base_name="leek_base", shoot=0.0, shoot_h=420, s=1.0, sy=1.0):
    glass_back(w, gx, TABLE, GW, GH, s)
    bh = BH_G
    if base_vis:
        pied(w, gx, TABLE - 24 + base_y_off, KG, shoot, rotten=rotten, shadow=False)
    glass_front(w, gx, TABLE, water, t, GW, GH, s, murky)
    return bh


def s_glass(t):
    w, u = new_layers(background("table"))
    gs = life(t, 16.8)
    water = 0.3 * ease_out((t - 17.0) / 0.45)
    y = drop(t, 17.42, 0, 900, 0.45)
    if gs > 0.01:
        glass_scene(w, t, water, base_y_off=(y if y is not None else 0), base_vis=y is not None, s=gs)
    if t > 17.85:
        particles(w, t, 17.87, GX, TABLE - 26 - 520 * 0.3, 12, 8, col=(170, 215, 245), size=10, up=500, dur=0.6)
    put(u, icon("arrow_down", 130), 830, 1030 + 25 * math.sin(t * 7), life(t, 18.54))
    put(u, text_img("RACINES EN BAS", F_TITLE, 70, CREAM, 8, DARK, 7, DARK), 540, 650, life(t, 18.54), -3)
    title(u, "UN VERRE D'EAU", t, 16.3, None, y=360, size=130)
    return w, u


cue(16.3, "rise", 0.25)
cue(16.8, "pop", 0.4)
cue(17.0, "pour", 0.4)
cue(17.85, "splash", 0.45)
cue(18.54, "pop_hi", 0.3)


# ============================================================ 6. ASTUCE : NIVEAU D'EAU (19.7 → 24.9)
def s_level(t):
    w, u = new_layers(background("table"))
    split = ease_io((t - 22.9) / 0.45)
    gx1 = lerp(540, 300, split)
    glass_scene(w, t, 0.3, gx=gx1)
    rot = clamp((t - 24.4) / 0.5)
    if t > 22.9:
        gx2 = lerp(1300, 790, split)
        glass_scene(w, t, lerp(0.3, 0.92, ease_out((t - 23.15) / 0.5)), gx=gx2, rotten=rot, murky=rot * 0.8)
        put(u, icon("cross", 140), gx2, 820, life(t, 23.3))
        flies(w, t, 24.6, 25.5, gx2, 760, 150)
    hline(w, gx1 - 170, gx1 + 170, TABLE - 26 - (GH - 26) * 0.3, ease_out((t - 21.94) / 0.4), 9)
    put(u, icon("check", 140), gx1, 820, life(t, 22.4))
    put(u, icon("lightbulb", 170), 540, 560, life(t, 19.78, 21.9), math.sin(t * 4) * 5)
    title(u, "ASTUCE", t, 19.78, 21.9, y=360)
    title(u, "JUSTE LES RACINES", t, 21.94, 24.3, y=360, size=120)
    title(u, "IL POURRIT !", t, 24.5, None, y=360, color=RED)
    return w, u


cue(19.78, "sparkle", 0.35)
cue(19.8, "pop", 0.3)
cue(21.94, "whoosh_up", 0.2)
cue(22.4, "success", 0.35)
cue(22.9, "whoosh", 0.25)
cue(23.2, "pour", 0.3)
cue(23.3, "pop_lo", 0.35)
cue(24.5, "fail", 0.35)
cue(24.6, "buzz", 0.15)


# ============================================================ 7. FENÊTRE + CHANGER L'EAU (24.9 → 30.6)
def s_window(t):
    w, u = new_layers(background("table"))
    ws = life(t, 25.6, dur=0.4)
    put(w, window_img(), 540, 800, ws)
    light_rays(w, 360, 420, t, fade(t, 26.4, None, 0.6))
    drain = 0.0
    if 27.46 < t < 28.6:
        x = (t - 27.46) / 1.14
        drain = math.sin(math.pi * x)
    glass_scene(w, t, 0.3 - 0.26 * drain)
    if 27.9 < t < 29.0:
        k = ease_io((t - 27.9) / 0.3) * (1 - ease_io((t - 28.7) / 0.3))
        spr(w, P + "watering_can", 860, 1010, 330, k, rot=lerp(0, 28, k), shadow=False)
    put(u, icon("sun", 170), 870, 470, life(t, 26.5), t * 25)
    act = -1 if t < 28.5 else (0 if t < 28.9 else (1 if t < 29.3 else 2))
    pills(u, ["J1", "J3", "J5"], act, t, 28.4, None, y=1080, pw=150)
    sparkles(w, t, 29.9, 540, TABLE - 150, 200, 7, 5)
    title(u, "LUMIÈRE", t, 26.4, 27.4, y=300)
    title(u, "TOUS LES 2 JOURS", t, 28.5, None, y=300, size=120)
    return w, u


cue(25.6, "pop", 0.35)
cue(26.4, "sparkle", 0.3)
cue(26.5, "pop_hi", 0.3)
cue(27.9, "pop", 0.3)
cue(28.0, "pour", 0.4)
cue(28.5, "tick", 0.3)
cue(28.9, "tick", 0.3)
cue(29.3, "tick", 0.3)
cue(29.9, "sparkle", 0.35)


# ============================================================ 8. ON ATTEND (30.6 → 33.0)
def s_wait(t):
    w, u = new_layers(background("table"))
    glass_scene(w, t, 0.3)
    day = 1 + int(clamp((t - 31.9) / 1.0) * 3.99)
    put(u, num_badge(f"J{day}", 200), 540, 640, life(t, 31.9), math.sin(t * 3) * 4)
    title(u, "ON ATTEND…", t, 30.98, None, y=360)
    return w, u


cue(30.98, "rise", 0.25)
for _k in range(4):
    cue(31.9 + _k * 0.25, "tick", 0.35)


# ============================================================ 9. LA POUSSE (33.0 → 37.8)
def s_shoot(t):
    w, u = new_layers(background("table"))
    g = ease_out((t - 35.9) / 1.6) * 0.2
    glass_scene(w, t, 0.3, shoot=g)
    top_y = TABLE - 24 - BH_G
    hl_ellipse(w, GX, top_y + 10, 110, 70, life(t, 34.4, 35.85))
    sparkles(w, t, 36.0, GX, top_y - 120, 160, 6, 9)
    pills(u, ["J3", "J4", "J5"], 1 if t > 33.8 else -1, t, 33.2, 35.0, y=560, pw=150)
    title(u, "LE CENTRE", t, 34.4, 35.8, y=360)
    title(u, "UNE POUSSE !", t, 36.0, None, y=360, color=YEL)
    return w, u


cue(33.2, "pop", 0.3)
cue(33.8, "tick", 0.3)
cue(34.4, "pop_hi", 0.35)
cue(35.95, "rise", 0.3)
cue(36.0, "sparkle", 0.35)


# ============================================================ 10. UNE SEMAINE PLUS TARD (37.8 → 40.5)
def s_week(t):
    w, u = new_layers(background("table"))
    g = lerp(0.2, 0.45, ease_out((t - 38.3) / 1.6))
    glass_scene(w, t, 0.3, shoot=g)
    sparkles(w, t, 39.7, GX, 600, 260, 8, 12)
    pills(u, ["J1", "J4", "J7"], 2 if t > 38.5 else -1, t, 38.35, None, y=1380, pw=150)
    title(u, "1 SEMAINE", t, 38.3, None, y=260)
    return w, u


cue(38.3, "pop", 0.35)
cue(38.4, "rise", 0.3)
cue(38.5, "tick", 0.3)
cue(39.7, "sparkle", 0.35)


# ============================================================ 11. PLUS LOIN : RACINES + POT (40.5 → 46.5)
def s_further(t):
    w, u = new_layers(background("table"))
    to_pot = ease_io((t - 44.4) / 0.5)
    if to_pot < 1:
        gx = lerp(540, -400, to_pot)
        lift = ease_io((t - 41.9) / 0.45)          # on sort le pied du verre pour voir les racines
        ground = TABLE - 24 - 260 * lift
        glass_back(w, gx, TABLE, GW, GH)
        pied(w, gx, ground, KG, 0.45, long=t > 42.55, shadow=False, s=1 + 0.06 * life(t, 42.55, 42.9))
        glass_front(w, gx, TABLE, 0.3, t, GW, GH)
        hl_ellipse(w, gx, ground - 85, 190, 110, life(t, 42.9, 44.3))
    if t > 44.4:
        bx = lerp(1400, 540, to_pot)
        y = drop(t, 44.8, TABLE - 200, 700, 0.4)
        if y is not None:
            pied(w, bx, y, KG, 0.4, long=True, shadow=False)
        spr(w, P + "barrel", bx, TABLE + 10, 560)
        # terre visible en haut du bac
        put(u, text_img("EN POT", F_TITLE, 80, YEL, 9, DARK, 7, DARK), 220, 960, life(t, 45.26), -4)
        put(u, text_img("OU AU POTAGER", F_TITLE, 66, YEL, 8, DARK, 7, DARK), 790, 960, life(t, 45.7), 4)
    title(u, "PLUS LOIN ?", t, 40.6, 42.2, y=330)
    title(u, "BLANCHES & LONGUES", t, 42.9, 44.3, y=330, size=100)
    title(u, "REPLANTE !", t, 44.46, None, y=360, color=YEL)
    return w, u


cue(40.6, "rise", 0.3)
cue(42.9, "pop_hi", 0.35)
cue(43.0, "sparkle", 0.3)
cue(44.4, "whoosh", 0.3)
cue(45.2, "thud", 0.45)
cue(45.26, "pop", 0.3)
cue(45.7, "pop_hi", 0.3)


# ============================================================ 12. EN TERRE, IL GROSSIT (46.5 → 50.4)
def s_soil(t):
    soil_y = lerp(H, 1180, ease_out((t - 46.55) / 0.45))
    w, u = new_layers(background("none", soil_y))
    grow = ease_io((t - 48.5) / 1.3)
    roots(w, 540, soil_y + 420, clamp((t - 47.0) / 0.8), 51, length=170, n=12)
    k = KG * lerp(1.0, 1.35, grow)                 # il grossit
    pied(w, 540, soil_y - 20 + LONG_H * k, k, lerp(0.45, 0.55, grow), long=True, shadow=False)
    # nutriments qui remontent vers les racines
    if 47.9 < t < 49.6:
        r = np.random.default_rng(3)
        for i in range(14):
            ph = ((t - 47.9) * 0.9 + r.uniform(0, 1)) % 1
            x0 = r.uniform(120, 960)
            px = lerp(x0, 540, ph)
            py = lerp(r.uniform(1450, 1850), soil_y + 260, ph)
            put(w, icon("star", 34), px, py, 1 - ph * 0.5, t * 90)
    title(u, "SE NOURRIR", t, 47.98, 48.45, y=300)
    title(u, "IL GROSSIT !", t, 48.54, None, y=300)
    return w, u


cue(46.5, "whoosh_up", 0.35)
cue(47.98, "sparkle", 0.3)
cue(48.0, "pop", 0.3)
cue(48.54, "rise", 0.35)
cue(48.6, "pop_lo", 0.35)


# ============================================================ 13. 1 LÉGUME / 2 RÉCOLTES / 0 GASPI (50.4 → 53.9)
def s_recap(t):
    w, u = new_layers(background("table"))
    leek(w, 300, TABLE, 1100, s=life(t, 50.46))
    spr(w, P + "leek_top", 620, TABLE, 470, life(t, 51.45), rot=-8)
    base_piece(w, 840, TABLE, 300, life(t, 51.6))
    spr(w, P + "trash", 860, TABLE - 520, 220, life(t, 52.7), shadow=False)
    put(u, icon("nosign", 260), 860, TABLE - 630, life(t, 52.8))
    for i, (lab, txt, t0) in enumerate([("1", "LÉGUME", 50.46), ("2", "RÉCOLTES", 51.42), ("0", "GASPI", 52.7)]):
        x = 220 + i * 320
        put(u, num_badge(lab, 150), x, 230, life(t, t0))
        put(u, text_img(txt, F_TITLE, 66, YEL, 8, DARK, 6, DARK), x, 345, life(t, t0 + 0.08), -3)
    return w, u


cue(50.46, "pop", 0.4)
cue(51.42, "pop_hi", 0.4)
cue(51.6, "pop", 0.3)
cue(52.7, "pop_lo", 0.4)
cue(52.98, "success", 0.4)


# ============================================================ 14. CTA (53.9 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    leek(w, 540, TABLE, 1050, s=life(t, 53.95))
    spr(w, "garlic_bulb_a", 220, TABLE, 300, life(t, 57.3))
    spr(w, "shallot_red", 860, TABLE, 300, life(t, 57.45))
    for x, t0 in ((220, 57.5), (860, 57.65)):
        put(u, icon("question", 110), x, TABLE - 460, life(t, t0), math.sin(t * 5) * 8)
    clicked = t > 54.6
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 54.55) / 0.15))
    put(u, btn, 540, 330, life(t, 54.02) * press)
    if t > 54.2:
        k = ease_out((t - 54.2) / 0.35)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(620, 370, k), 1)
    sparkles(u, t, 54.65, 540, 330, 260, 8, 21)
    sb = life(t, 56.58)
    put(u, icon("bubble", 230), 540, 560, sb, math.sin(t * 3) * 3)
    if sb > 0.5:
        for i in range(3):
            yy = 535 - 12 * max(0, math.sin(t * 8 - i * 0.9))
            put(u, text_img("•", F_BLACK, 90, DARK), 475 + i * 65, yy - 10, sb)
    put(u, text_img("ASTUCES POTAGER", F_TITLE, 92, YEL, 10, DARK, 8, DARK), 540, 160, life(t, 55.0), -3)
    return w, u


cue(53.95, "pop", 0.3)
cue(54.02, "pop_hi", 0.4)
cue(54.58, "click", 0.6)
cue(54.65, "bell", 0.4)
cue(55.0, "sparkle", 0.3)
cue(56.58, "pop", 0.4)
cue(57.3, "pop", 0.3)
cue(57.45, "pop_hi", 0.3)
cue(58.3, "sparkle", 0.3)


SCENES = [
    (0.0, 3.15, s_stop),
    (3.15, 6.8, s_regrow),
    (6.8, 10.4, s_keep),
    (10.4, 15.3, s_cut),
    (15.3, 19.7, s_glass),
    (19.7, 24.9, s_level),
    (24.9, 30.6, s_window),
    (30.6, 33.0, s_wait),
    (33.0, 37.8, s_shoot),
    (37.8, 40.5, s_week),
    (40.5, 46.5, s_further),
    (46.5, 50.4, s_soil),
    (50.4, 53.9, s_recap),
    (53.9, 99.0, s_cta),
]

# badge d'étape haut-droite : (numéro, début, fin)
TRAPS = [(1, 10.45, 15.3), (2, 15.35, 30.6), (3, 30.65, 40.5), (4, 40.55, 50.4)]
