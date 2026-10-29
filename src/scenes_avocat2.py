"""Storyboard « Noyau d'avocat » v2 (voix : assets/audio/avocat2/voix.mp3).

Décors photo fournis : plan de travail avec planche (cuisine), buffet du salon. Le noyau est jeté à la poubelle puis
revient, il est lavé, épluché, enroulé dans un sopalin humide et mis dans une boîte transparente fermée, posée au chaud
et à la lumière sur le buffet ; il se fend, une racine sort, puis le petit arbre pousse sur ce même buffet.
Photos : noyau brun, avocatier en pot (vidéo avocat précédente), noyau épluché, noyau fendu, jeune plant, poubelle
(fournies), sopalin et boîte (vidéo citron). Si assets/video/intro_avocat2.mp4 existe, la 1re phrase montre la vidéo.
"""
import math
import os
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (ROOT, IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, put, title, life, fade, ease_out, ease_io,
                 clamp, lerp, icon, pills, tag, button_img, hl_ellipse, particles, light_rays)
from scenes import sparkles
from scenes_ananas import place, logo_img
from scenes_hortensia import stamp
from scenes_mangue import warm_glow
from scenes_citron import photo, shade, zoomed, shadow, swap, sopalin

CUES = []
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


VIDEO = os.path.join(ROOT, "assets", "video", "intro_avocat2.mp4")
HAS_VIDEO = os.path.exists(VIDEO)


def video_duration():
    if not HAS_VIDEO:
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                         capture_output=True, text=True).stdout
    return min(1.75, float(out.strip() or 0))


VID_END = video_duration()
NO_CAPTION_UNTIL = VID_END


@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_avocat2_intro")
    if not os.path.isdir(d) or not os.listdir(d):
        os.makedirs(d, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", VIDEO, "-an", "-vf",
                        f"fps={FPS},scale={W}:{H}:flags=lanczos", os.path.join(d, "%04d.png")], check=True)
    return sorted(os.path.join(d, f) for f in os.listdir(d))


def s_video(t):
    fr = video_frames()
    i = min(len(fr) - 1, max(0, int(round(t * FPS))))
    return Image.open(fr[i]).convert("RGBA"), Image.new("RGBA", (W, H), (0, 0, 0, 0))


s_video.raw = True


# ------------------------------------------------------------- objets détourés (cadre carré complet de chaque photo)
@lru_cache(None)
def geom(name):
    im = Image.open(os.path.join(IMG, name + ".png"))
    return im.width, im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()


def ob(c, name, X, Y, width, s=1.0, rot=0.0, alpha=1.0, anchor="center"):
    """Objet détouré de largeur `width` ; (X, Y) = centre, ou bas-centre si anchor='bottom'."""
    if s <= 0.01 or alpha <= 0.01:
        return
    fr, bb = geom(name)
    k = width / (bb[2] - bb[0])
    cx = (bb[0] + bb[2]) / 2
    cy = bb[3] if anchor == "bottom" else (bb[1] + bb[3]) / 2
    place(c, name, (0, 0, fr, fr), k, cx, cy, X, Y, s, rot, 0.0, alpha)


PIT = "avocat/noyau"            # noyau brun (avec sa peau)
PELE = "avocat2/noyau_pele"
FENDU = "avocat2/noyau_fendu"
PLANT = "avocat2/jeune_plant"
TREE = "avocat/pot"
BIN = "avocat2/poubelle"
BOX_O, BOX_F = "citron/boite_ouverte", "citron/boite_fermee"


def wipe(c, a, b, X, Y, wa, wb, p, rot=0.0):
    """Passage de la photo a à la photo b d'un bord à l'autre (épluchage), sans fantôme."""
    if p <= 0:
        ob(c, a, X, Y, wa, rot=rot)
        return
    if p >= 1:
        ob(c, b, X, Y, wb, rot=rot)
        return
    la, lb = Image.new("RGBA", (W, H), (0, 0, 0, 0)), Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ob(la, a, X, Y, wa, rot=rot)
    ob(lb, b, X, Y, wb, rot=rot)
    cut = X - wa * 0.6 + wa * 1.2 * p
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rectangle([cut, 0, W, H], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(10))
    la.putalpha(Image.composite(la.getchannel("A"), Image.new("L", (W, H), 0), m))
    lb.putalpha(Image.composite(lb.getchannel("A"), Image.new("L", (W, H), 0), Image.eval(m, lambda v: 255 - v)))
    c.alpha_composite(lb)
    c.alpha_composite(la)


def wrapped(c, X, Y, w_, pit, pit_w, cover, wet, see=0.45, pit_rot=-10):
    """Noyau sur un sopalin humide, recouvert (cover 0..1, de gauche à droite) par un 2e pan de sopalin translucide."""
    sopalin(c, X, Y, w_, 1.0, wet)
    ob(c, pit, X, Y - pit_w * 0.18, pit_w, rot=pit_rot)
    if cover > 0.01:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sopalin(lay, X, Y - 6, w_ * 0.96, 1.0, wet)
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle([0, 0, X - w_ / 2 + w_ * cover, H], fill=int(255 * (1 - see)))
        lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
        c.alpha_composite(lay)


# ============================================================ A-B-C. LA CUISINE, UN SEUL PLAN (0 → 12.4)
BOARD = (520, 1170)
BIN_X, BIN_BASE, BIN_W = 880, 1470, 250
BIN_RIM = BIN_BASE - (920 - 330) / (727 - 297) * BIN_W     # bord avant de la poubelle (écran)


def cam(t):
    k1 = ease_io((t - 5.3) / 0.6)        # zoom sur le noyau (lavage, peau)
    k2 = ease_io((t - 8.1) / 0.6)        # plus large pour le sopalin et la boîte
    z = lerp(lerp(1.0, 1.8, k1), 1.25, k2)
    fx = lerp(lerp(540, BOARD[0], k1), BOARD[0], k2)
    fy = lerp(lerp(1100, 1080, k1), 1130, k2)
    return z, fx, fy


def pit_path(t):
    """Le noyau : sur la planche → lancé dans la poubelle → il en ressort et revient sur la planche."""
    start = (BOARD[0] - 60, BOARD[1] - 20)
    inbin = (BIN_X, BIN_RIM + 60)
    if t < 0.55:
        return start[0], start[1], 0.0, True
    if t < 1.1:
        p = ease_io((t - 0.55) / 0.55)
        return lerp(start[0], inbin[0], p), lerp(start[1], inbin[1] - 60, p) - math.sin(math.pi * p) * 380, -360 * p, True
    if t < 2.35:
        p = ease_out((t - 1.1) / 0.2)
        return inbin[0], lerp(inbin[1] - 60, inbin[1], p), 0.0, True
    p = ease_io((t - 2.35) / 0.6)
    return lerp(inbin[0], BOARD[0], p), lerp(inbin[1], BOARD[1] - 20, p) - math.sin(math.pi * p) * 420, 360 * p, p < 0.25


def s_kitchen(t):
    world = photo("citron_fond_cuisine.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    PW = 190   # largeur du noyau dans le décor
    # --- 1. jeté à la poubelle, puis il revient (0 → 3.0)
    bin_s = life(t, 0.0, 3.3, dur=0.35)
    if t < 3.3:
        x, y, rot, near_bin = pit_path(t)
        if bin_s > 0.01:
            shadow(world, BIN_X, BIN_BASE, BIN_W * 1.1 * bin_s)
            ob(world, BIN, BIN_X, BIN_BASE, BIN_W, bin_s, anchor="bottom")
        if near_bin and 1.0 < t < 2.6:
            # dans la poubelle : on ne voit que ce qui dépasse du bord avant
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ob(lay, PIT, x, y, PW * 0.8, rot=rot)
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).rectangle([0, 0, W, int(BIN_RIM)], fill=255)
            lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
            world.alpha_composite(lay)
        else:
            if t < 0.6 or t > 2.9:
                shadow(world, x, BOARD[1] + 70, PW * 0.9)
            ob(world, PIT, x, y, PW * (0.8 if 0.55 < t < 2.9 else 1.0), rot=rot)
        if 1.1 < t < 1.5:
            particles(world, t, 1.12, BIN_X, BIN_RIM - 10, 8, 3, col=(150, 150, 150), size=7, up=220)
    # --- 2. lavage et peau brune (5.3 → 8.1)
    if t >= 3.3:
        X, Y = BOARD[0], BOARD[1] - 20
        if t < 8.6:
            shadow(world, X, BOARD[1] + 70, PW * 0.9)
            wipe(world, PIT, PELE, X, Y, PW, PW * 0.92, ease_io((t - 6.85) / 0.9))
        if 5.95 < t < 6.6:
            for i in range(10):
                tt = (t - 5.95 - i * 0.05) % 0.45
                put(world, icon("drop", 30), X - 80 + (i * 41) % 160, lerp(Y - 240, Y - 30, tt / 0.45), 1, 0, 1 - tt / 0.45)
        if 6.85 < t < 7.9:
            particles(world, t, 6.95, X + 40, Y, 10, 5, col=(110, 70, 40), size=8, up=200, dur=1.0)
    # --- 3. sopalin humide, on l'enroule, boîte fermée (8.1 → 12.4)
    if t >= 8.6:
        BOX = (BOARD[0], BOARD[1] - 50)
        into = ease_io((t - 10.75) / 0.4)
        sx, sy = lerp(BOARD[0], BOX[0], into), lerp(BOARD[1], BOX[1] + 105, into)
        sw = lerp(360, 300, into)
        drop = ease_out((t - 8.6) / 0.3)
        if t > 10.5:
            bx = lerp(1300, BOX[0], ease_out((t - 10.5) / 0.4))
            shadow(world, bx, BOX[1] + 190, 560)
        if drop < 1:
            sopalin(world, sx, lerp(sy - 400, sy, drop), sw, ease_io((t - 8.65) / 0.25), 0.0, drop)
            ob(world, PELE, BOARD[0], BOARD[1] - 20, PW * 0.92)
        else:
            wrapped(world, sx, sy, sw, PELE, lerp(PW * 0.75, PW * 0.6, into), ease_io((t - 8.85) / 0.7),
                    ease_out((t - 10.05) / 0.5))
        if 10.05 < t < 10.5:
            for i in range(8):
                tt = (t - 10.05 - i * 0.04) % 0.35
                put(world, icon("drop", 30), sx - 130 + i * 38, lerp(sy - 280, sy - 20, tt / 0.35), 1, 0, 1)
        if t > 10.5:
            which, sc = swap((t - 11.1) / 0.3)
            if which == 0:
                ob(world, BOX_O, lerp(1300, BOX[0], ease_out((t - 10.5) / 0.4)), BOX[1], 620 * sc)
            else:
                ob(world, BOX_F, BOX[0], BOX[1] - 6, 620 * 1.0 * sc)
    z, fx, fy = cam(t)
    world = zoomed(world, z, fx, fy)
    world.alpha_composite(shade())
    # --- UI
    if 2.4 < t < 5.3:
        s_ = life(t, 2.5, 5.2)
        if s_ > 0.01:
            d = ImageDraw.Draw(u)
            r = 165 * s_
            d.ellipse([860 - r - 8, 780 - r - 8, 860 + r + 8, 780 + r + 8], fill=DARK)
            d.ellipse([860 - r, 780 - r, 860 + r, 780 + r], fill=CREAM)
            ob(u, TREE, 860, 790, 190, s_)
        sparkles(u, t, 4.15, 860, 780, 230, 8, 4)
    if 6.85 < t < 8.05:
        tag(u, "PEAU BRUNE", 790, 640, t, 6.9, 8.0, rot=-5, size=52)
    title(u, "TU LE JETTES ?", t, 0.3, 1.75, y=330, size=150)
    stamp(u, "UN ARBRE !", 540, 360, t, 2.9, 4.0, GREEN, 130, -8)
    title(u, "SANS LE SAVOIR…", t, 4.05, 5.25, y=330, size=140)
    title(u, "LAVE-LE", t, 5.9, 6.75, y=330, color=YEL, size=170)
    title(u, "RETIRE SA PEAU", t, 6.8, 8.0, y=330, size=145)
    title(u, "ESSUIE-TOUT HUMIDE", t, 8.75, 10.5, y=330, size=118)
    title(u, "BOÎTE FERMÉE", t, 10.55, 11.75, y=330, color=YEL, size=145)
    title(u, "AU CHAUD", t, 11.8, None, y=330, color=YEL, size=165)
    return world, u


cue(0.05, "pop_lo", 0.3)
cue(0.6, "whoosh", 0.3)
cue(1.12, "thud", 0.45)
cue(1.85, "alert3", 0.35)
cue(2.4, "whoosh_up", 0.3)
cue(2.95, "thud", 0.35)
cue(3.0, "success", 0.25)
cue(5.4, "whoosh", 0.15)
cue(5.98, "splash", 0.3)
cue(6.9, "squish", 0.25)
cue(8.65, "pop", 0.2)
cue(8.9, "stir", 0.22)
cue(10.08, "plop", 0.25)
cue(10.55, "whoosh", 0.16)
cue(11.12, "click", 0.4)


# ============================================================ D. LE BUFFET DU SALON : ON ATTEND… ÇA POUSSE (12.4 → fin)
TOP = (560, 795)


def s_buffet(t):
    w = photo("citron_fond_buffet.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    warm_glow(w, fade(t, 12.45, 17.3, 0.5, 0.5))
    light_rays(w, 260, 0, t, fade(t, 12.5, 17.3, 0.5, 0.5))
    plant_p = (t - 17.35) / 0.35
    tree_p = (t - 18.3) / 0.4
    if plant_p < 0.5:
        # boîte fermée sur le buffet ; à travers, le noyau se fend et une racine sort
        land = ease_out((t - 12.45) / 0.4)
        bx, by = TOP[0], lerp(TOP[1] - 500, TOP[1] - 100, land)
        s = 1.0 if plant_p < 0 else 1 - 0.12 * ease_io(plant_p * 2)
        shadow(w, TOP[0], TOP[1], 330 * land)
        which, sc = swap((t - 15.85) / 0.35)
        sopalin(w, bx, by + 78, 250 * s, 1.0, 1.0)
        if which == 0:
            ob(w, PELE, bx, by + 45, 125 * sc * s)
        else:
            ob(w, FENDU, bx, by + 35, 135 * sc * s)
        # pan de sopalin translucide par-dessus (léger, pour voir le noyau)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sopalin(lay, bx, by + 72, 240 * s, 1.0, 1.0)
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * 0.12)))
        w.alpha_composite(lay)
        ob(w, BOX_F, bx, by, 430 * s)
        # le plastique est clair : on redessine le noyau à travers la paroi, un peu atténué
        if which == 0:
            ob(w, PELE, bx, by + 45, 125 * sc * s, alpha=0.6)
        else:
            ob(w, FENDU, bx, by + 35, 135 * sc * s, alpha=0.65)
        if 16.7 < t < 17.35:
            hl_ellipse(w, bx + 15, by + 108, 30, 34, life(t, 16.75, 17.3), width=5)
    elif tree_p < 0.5:
        q = clamp((plant_p - 0.5) * 2)
        sc = 0.88 + 0.12 * q + 0.04 * math.sin(math.pi * q)
        s2 = 1.0 if tree_p < 0 else 1 - 0.12 * ease_io(tree_p * 2)
        shadow(w, TOP[0], TOP[1], 260)
        sopalin(w, TOP[0], TOP[1] - 22, 260, 1.0, 1.0)
        ob(w, PLANT, TOP[0], TOP[1] - 10, 330 * sc * s2, anchor="bottom")
    else:
        q = clamp((tree_p - 0.5) * 2)
        sc = 0.88 + 0.12 * q + 0.04 * math.sin(math.pi * q)
        shadow(w, TOP[0], TOP[1], 300)
        ob(w, TREE, TOP[0], TOP[1], 300 * sc, anchor="bottom")
        sparkles(u, t, 18.5, TOP[0], TOP[1] - 300, 330, 10, 7)
    zk = ease_io((t - 15.45) / 0.45) * (1 - ease_io((t - 17.25) / 0.4))
    w = zoomed(w, 1 + 1.1 * zk, TOP[0], TOP[1] - 60)
    w.alpha_composite(shade())
    put(u, icon("thermo", 140), 180, 1180, life(t, 12.5, 13.3))
    put(u, icon("sun", 160), 900, 1180, life(t, 12.6, 13.3), t * 25)
    if 13.4 < t < 15.6:
        act = min(3, int((t - 13.5) / 0.45))
        pills(u, ["S1", "S2", "S3", "S4"], act, t, 13.4, 15.55, y=1180, pw=170)
    if 16.75 < t < 18.2:
        tag(u, "RACINE !", 820, 1180, t, 16.8, 18.15, rot=5, size=60)
    # CTA directement sur le buffet, avec l'avocatier
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
    title(u, "ET LÀ… ON ATTEND", t, 12.5, 14.3, y=1300, size=135)
    title(u, "QUELQUES SEMAINES", t, 14.38, 15.6, y=1300, color=YEL, size=125)
    title(u, "IL SE FEND…", t, 15.66, 16.6, y=1300, size=150)
    title(u, "UNE RACINE SORT !", t, 16.66, 18.2, y=1300, color=YEL, size=130)
    title(u, "TON AVOCATIER !", t, 18.28, 19.05, y=1300, color=YEL, size=140)
    return w, u


cue(12.5, "thud", 0.3)
cue(12.6, "rise", 0.18)
for _k in range(4):
    cue(13.5 + _k * 0.45, "tick", 0.24)
cue(15.9, "crunch", 0.4)
cue(16.75, "pop_hi", 0.25)
cue(17.4, "pop_lo", 0.3)
cue(18.35, "success", 0.35)
cue(19.58, "click", 0.45)
cue(20.0, "sparkle", 0.25)

if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video), (VID_END, 12.4, s_kitchen)]
else:
    _intro = [(0.0, 12.4, s_kitchen)]

SCENES = _intro + [
    (12.4, 99.0, s_buffet),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []

if HAS_VIDEO:
    CUES[:] = [c for c in CUES if c[0] >= VID_END - 0.05]
