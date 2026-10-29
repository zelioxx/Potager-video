"""Storyboard « Récupérer les chrysanthèmes fanés » (voix : assets/audio/chrysantheme/voix.mp3).

Décors photo fournis : poubelle du cimetière (le pied à moitié fané y est posé), établi (on coupe les tiges à 10 cm),
puis le sol nu du jardin (photo de la vidéo des tulipes) où on le plante ; l'automne suivant il refleurit.
Photos détourées fournies : pied à moitié fané (non coupé), pied coupé, pied bien fleuri, sécateur ouvert / fermé.
Si assets/video/intro_chrysantheme.mp4 existe, la première phrase montre cette vidéo brute.
"""
import math
import os
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (ROOT, IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, put, title, life, fade, ease_out, ease_io,
                 clamp, lerp, icon, pills, tag, hl_ellipse, particles, measure, text_img, F_TITLE)
from scenes import sparkles, falling
from scenes_ananas import place, logo_img
from scenes_hortensia import stamp
from scenes_citron import photo, shade, zoomed, shadow, swap

CUES = []
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


VIDEO = os.path.join(ROOT, "assets", "video", "intro_chrysantheme.mp4")
HAS_VIDEO = os.path.exists(VIDEO)


def video_duration():
    if not HAS_VIDEO:
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                         capture_output=True, text=True).stdout
    return min(3.6, float(out.strip() or 0))


VID_END = video_duration()
NO_CAPTION_UNTIL = VID_END


@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_chrysantheme_intro")
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

# ------------------------------------------------------------- pieds de chrysanthème (cadre 1254 d'origine)
C = "chrysantheme/"
# nom : (centre x de la motte, haut de la motte = surface de la terre, largeur de référence de la motte)
PLANTS = {"fane": (621, 790, 399), "coupe": (633, 690, 431), "fleuri": (618, 790, 397)}


def plant(c, name, X, Y, rbw, s=1.0, rot=0.0, clip=None, alpha=1.0):
    """Pied posé avec le haut de sa motte (surface de la terre) en (X, Y) ; rbw = largeur de la motte à l'écran.
    clip(x) -> y : tout ce qui est sous cette ligne est caché (dans la poubelle, sous la terre)."""
    if s <= 0.01 or alpha <= 0.01:
        return
    cx, top, ref = PLANTS[name]
    k = rbw / ref
    if clip is None:
        place(c, C + name, (0, 0, 1254, 1254), k, cx, top, X, Y, s, rot, 0.0, alpha)
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    place(lay, C + name, (0, 0, 1254, 1254), k, cx, top, X, Y, s, rot, 0.0, alpha)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon([(0, 0), (W, 0), (W, clip(W)), (0, clip(0))], fill=255)
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m.filter(ImageFilter.GaussianBlur(2))))
    c.alpha_composite(lay)


def secateur(c, tip, width, closed, rot=0.0, s=1.0):
    """Sécateur dont la pointe de la lame (à gauche) est en `tip`."""
    name = "secateur_ferme" if closed else "secateur_ouvert"
    bb = (56, 325, 956, 695) if closed else (59, 218, 945, 800)
    k = width / (bb[2] - bb[0])
    tip_src = (bb[0], (bb[1] + bb[3]) / 2)
    place(c, C + name, (0, 0, 1024, 1024), k, *tip_src, tip[0], tip[1], s, rot)


# ============================================================ A. LA POUBELLE DU CIMETIÈRE (0 → 9.55)
def rim(x):
    """Bord avant de la poubelle (écran) : légèrement en pente."""
    return 1300 + (x - 200) / 880 * 140


PX0, PY0, RBW0 = 600, 1395, 210      # notre pied, posé dans le tas de fleurs fanées
DROPS = [(360, 5.9, -14), (840, 6.35, 12), (560, 6.8, -6)]


def s_bin(t):
    w = photo("chrys_fond_cimetiere.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # d'autres pieds fanés tombent dans la poubelle : « des milliers »
    for x, t0, r in DROPS:
        if t > t0:
            p = ease_out(clamp((t - t0) / 0.45))
            plant(w, "fane", x, lerp(-200, 1380, p), 150, rot=r, clip=rim)
    # notre pied : récupéré (il sort de la poubelle vers la caméra)
    lift = ease_io((t - 8.75) / 0.7)
    X = lerp(PX0, 540, lift)
    Y = lerp(PY0, 1250, lift) - math.sin(math.pi * lift) * 120
    plant(w, "fane", X, Y, lerp(RBW0, 300, lift), clip=rim if lift < 0.6 else None)
    if 7.4 < t < 7.9:
        particles(w, t, 7.45, 600, 1150, 10, 3, col=(150, 90, 40), size=8, up=200)
    z = lerp(1.35, 1.0, ease_out(clamp(t / 0.7))) + 0.12 * ease_io((t - 8.75) / 0.7)
    w = zoomed(w, z, 600, 1150)
    w.alpha_composite(shade())
    if 8.15 < t < 8.8:
        hl_ellipse(u, PX0, 1180, 230, 200, life(t, 8.2, 8.75))
    stamp(u, "0 € !", 820, 640, t, 1.15, 3.6, GREEN, 120, 8)
    title(u, "CHRYSANTHÈMES GRATUITS ?", t, 0.3, 3.6, y=330, size=105)
    title(u, "JE T'EXPLIQUE", t, 3.7, 4.85, y=330, color=YEL, size=150)
    if t > 4.9:
        tag(u, "APRÈS LA TOUSSAINT", 540, 560, t, 4.95, 8.1, rot=-4, size=50)
    title(u, "DES MILLIERS…", t, 5.7, 7.5, y=330, size=160)
    title(u, "À LA POUBELLE !", t, 7.54, 8.6, y=330, color=RED, size=150)
    title(u, "RÉCUPÈRE-LES !", t, 8.66, None, y=330, color=YEL, size=145)
    return w, u


cue(0.0, "whoosh_up", 0.22)
cue(1.18, "pop_hi", 0.25)
cue(3.72, "pop", 0.2)
cue(4.95, "pop", 0.2)
for _x, _t0, _r in DROPS:
    cue(_t0 + 0.42, "thud", 0.28)
cue(7.56, "alert3", 0.3)
cue(8.2, "pop_hi", 0.22)
cue(8.78, "whoosh_up", 0.25)


# ============================================================ B. L'ÉTABLI : COUPE LES TIGES À 10 CM (9.55 → 11.45)
BX, BY, BRBW = 480, 1170, 300        # pied posé sur l'établi (haut de la motte)
BOTTOM_OFFSET = {"fane": (1229 - 790), "coupe": (1191 - 690)}


def s_bench(t):
    w = photo("chrys_fond_etabli.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    land = ease_out(clamp((t - 9.55) / 0.3))
    which, sc = swap((t - 10.25) / 0.3)
    name = "fane" if which == 0 else "coupe"
    rbw = BRBW * sc
    bottom = BY + BOTTOM_OFFSET[name] * rbw / PLANTS[name][2]
    shadow(w, BX, bottom, rbw * 1.3 * land)
    plant(w, name, BX, lerp(BY - 500, BY, land), rbw)
    cut_y = BY - 240                  # hauteur de coupe (≈ 10 cm au-dessus de la terre, haut des tiges coupées)
    if 9.85 < t < 11.4:
        s_ = life(t, 9.85, 11.35)
        closed = (10.05 < t < 10.2) or (10.4 < t < 10.55)
        secateur(w, (BX + 30, cut_y), 430, closed, rot=-8, s=s_)
    if 10.1 < t < 10.9:
        particles(w, t, 10.12, BX, cut_y - 40, 16, 4, col=(205, 165, 40), size=10, up=380, dur=0.8)
        particles(w, t, 10.45, BX - 60, cut_y - 40, 10, 7, col=(95, 120, 60), size=9, up=320, dur=0.7)
    if t > 10.55:
        measure(u, 70, cut_y, BY, "10 CM", life(t, 10.6))
    w = zoomed(w, 1.15, BX, BY - 150)
    w.alpha_composite(shade())
    title(u, "COUPE LES TIGES", t, 9.62, 10.65, y=330, size=140)
    title(u, "À 10 CM", t, 10.7, None, y=330, color=YEL, size=170)
    return w, u


cue(9.6, "thud", 0.3)
cue(10.08, "chop", 0.5)
cue(10.42, "chop", 0.45)
cue(10.62, "tick", 0.25)


# ============================================================ C. AU JARDIN : PLANTÉ… ET L'AUTOMNE PROCHAIN, IL REFLEURIT (11.45 → fin)
GX, GY = 480, 1190                   # pied planté (surface de la terre, au premier plan)
BACK = [(250, 850, 150, 14.5), (820, 760, 125, 14.7)]      # autres pieds plus loin dans le massif


def ground(x):
    return GY + 8


def mound(c, x, y, wdt):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.ellipse([x - wdt / 2, y - wdt * 0.1, x + wdt / 2, y + wdt * 0.12], fill=(38, 28, 20, 230))
    d.ellipse([x - wdt * 0.42, y - wdt * 0.12, x + wdt * 0.42, y + wdt * 0.04], fill=(56, 40, 28, 230))
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(3)))


def s_garden(t):
    w = photo("tulipes_fond_sol_nu.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bloom_t = 14.22
    warm = fade(t, bloom_t, None, 0.6)
    # l'année passe : teinte froide (hiver) puis chaude
    if 12.9 < t < bloom_t + 0.3:
        cold = fade(t, 12.95, bloom_t, 0.3, 0.3)
        w.alpha_composite(Image.new("RGBA", (W, H), (150, 185, 230, int(70 * cold))))
        if 13.0 < t < 13.7:
            falling(w, t, 13.0, 13.7, "snow", 18, 4, 420, 44, sway=30)
    if warm > 0.01:
        w.alpha_composite(Image.new("RGBA", (W, H), (255, 190, 90, int(28 * warm))))
    # les pieds du fond fleurissent aussi
    for x, y, rbw, t0 in BACK:
        s_ = life(t, t0, dur=0.4)
        if s_ > 0.01:
            mound(w, x, y + 6, rbw * 1.3)
            plant(w, "fleuri", x, y, rbw, s_, clip=lambda xx, y=y: y + 8)
    drop = ease_out(clamp((t - 11.5) / 0.35))
    which, sc = swap((t - bloom_t) / 0.35)
    name = "coupe" if which == 0 else "fleuri"
    mound(w, GX, GY + 6, 300 * drop)
    plant(w, name, GX, lerp(GY - 600, GY, drop), 230 * sc, clip=ground)
    if 11.8 < t < 12.3:
        particles(w, t, 11.82, GX, GY - 10, 14, 4, col=(70, 50, 32), size=9, up=320)
    w.alpha_composite(shade())
    if 12.9 < t < 14.2:
        act = int((t - 12.95) / 0.4)
        pills(u, ["HIVER", "ÉTÉ", "AUTOMNE"], min(act, 2), t, 12.9, 14.15, y=560, pw=270)
    if t > bloom_t:
        sparkles(u, t, bloom_t + 0.05, GX, GY - 250, 330, 10, 6)
    stamp(u, "GRATUIT !", 540, 500, t, 15.05, 15.95, GREEN, 120, 8)
    title(u, "PLANTE-LES AU JARDIN", t, 11.52, 12.8, y=330, size=115)
    title(u, "L'AUTOMNE PROCHAIN…", t, 12.85, 14.15, y=330, size=125)
    title(u, "ILS REFLEURISSENT !", t, 14.2, 15.95, y=330, color=YEL, size=130)
    title(u, "MALIN, NON ?", t, 16.0, None, y=330, color=YEL, size=165)
    if t > 16.4:
        put(u, logo_img(260), 540, 590, life(t, 16.45, dur=0.45))
    return w, u


cue(11.55, "whoosh", 0.18)
cue(11.85, "crunch", 0.35)
for _k in range(3):
    cue(12.97 + _k * 0.4, "tick", 0.24)
cue(14.25, "success", 0.35)
cue(15.08, "pop_hi", 0.25)
cue(16.05, "sparkle", 0.25)

if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video), (VID_END, 9.55, s_bin)]
else:
    _intro = [(0.0, 9.55, s_bin)]

SCENES = _intro + [
    (9.55, 11.45, s_bench),
    (11.45, 99.0, s_garden),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []

if HAS_VIDEO:
    CUES[:] = [c for c in CUES if c[0] >= VID_END - 0.05]
