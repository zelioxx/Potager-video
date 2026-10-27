"""Storyboard « Planter ses bulbes de tulipe en automne » (voix : assets/audio/tulipes/voix.mp3).

Fonds photo fournis (alternés avec le fond beige) : parterre du voisin, parterre rêvé, sol nu, rayon jardinerie,
coupe de sol « 20 cm » (le bulbe y est incrusté). Photos détourées : bulbe, sachet « Blue Parrot ».
Crocus : Open Images. Si assets/video/intro_tulipes.mp4 existe, la première phrase montre cette vidéo brute.
"""
import math
import os
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (ROOT, IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, put, title, life, fade,
                 ease_out, ease_io, clamp, lerp, icon, tag, button_img, hl_ellipse, particles, text_img, F_TITLE)
from scenes import TABLE, new_layers, sparkles, falling
from scenes_ananas import place, logo_img
from scenes_hortensia import stamp

CUES = []
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


A = "tulipes/"
SRC = os.path.join(ROOT, "assets", "images", "source_utilisateur")
VIDEO = os.path.join(ROOT, "assets", "video", "intro_tulipes.mp4")
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
    d = os.path.join(ROOT, "output", "tmp_tulipes_intro")
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


# ------------------------------------------------------------- fonds photo
@lru_cache(None)
def photo(name):
    """Fond photo fourni, mis à l'échelle 1080×1920 (légèrement plus grand pour le travelling)."""
    im = Image.open(os.path.join(SRC, name + ".png")).convert("RGB")
    return im.resize((int(W * 1.08), int(H * 1.08)), Image.LANCZOS)


@lru_cache(None)
def shade():
    """Dégradés sombres en haut (titres) et en bas (sous-titres) pour la lisibilité sur photo."""
    a = np.zeros((H, 1), np.float32)
    y = np.arange(H)
    a[:, 0] = np.clip((520 - y) / 520, 0, 1) ** 1.5 * 90 + np.clip((y - 1330) / 590, 0, 1) ** 1.3 * 120
    im = Image.new("RGBA", (W, H), (20, 18, 14, 0))
    im.putalpha(Image.fromarray(np.repeat(a, W, 1).astype("uint8")))
    return im


CUR = {}


def photo_bg(name, t, t0, t1, z0=1.0, z1=1.06, fx=0.5, fy=0.5, plain=False):
    """Photo en plein cadre avec travelling lent (zoom z0 → z1 sur la durée de la scène).
    plain=True : photo simplement mise à 1080×1920, sans recadrage (repères fixes)."""
    im = photo(name)
    if plain:
        x0, y0, cw, ch = 0.0, 0.0, float(im.width), float(im.height)
    else:
        p = clamp((t - t0) / max(0.01, t1 - t0))
        z = lerp(z0, z1, ease_io(p))
        cw, ch = im.width / 1.08 / z, im.height / 1.08 / z
        x0 = (im.width - cw) * fx
        y0 = (im.height - ch) * fy
    src_w = Image.open(os.path.join(SRC, name + ".png")).width if name not in CUR.get("_w", {}) else CUR["_w"][name]
    CUR.setdefault("_w", {})[name] = src_w
    k = im.width / src_w
    CUR["map"] = lambda sx, sy: ((sx * k - x0) * W / cw, (sy * k - y0) * H / ch, W / cw * k)
    bg = im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BICUBIC).convert("RGBA")
    bg.alpha_composite(shade())
    return bg


@lru_cache(None)
def medallion(src_name, box, S=300, from_src=True):
    """Médaillon rond : extrait d'une photo (box) sur fond crème, bord sombre."""
    path = os.path.join(SRC, src_name + ".png") if from_src else os.path.join(IMG, A + src_name)
    ph = Image.open(path).convert("RGB").crop(box).resize((S - 40, S - 40), Image.LANCZOS)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, S - 1, S - 1], fill=DARK)
    d.ellipse([9, 9, S - 10, S - 10], fill=CREAM)
    m = Image.new("L", (S - 40, S - 40), 0)
    ImageDraw.Draw(m).ellipse([0, 0, S - 41, S - 41], fill=255)
    im.paste(ph, (20, 20), m)
    return im


# ------------------------------------------------------------- bulbe
BULB_BOX = (238, 61, 1019, 1210)      # bbox du bulbe (racines comprises) dans bulbe.png (1254)
BULB_C = ((BULB_BOX[0] + BULB_BOX[2]) / 2, (BULB_BOX[1] + BULB_BOX[3]) / 2)
BULB_H = 200                          # hauteur à l'écran dans la coupe (20 cm ≈ 540 px ≈ 3 bulbes de 180 px)
BK = BULB_H / (BULB_BOX[3] - BULB_BOX[1])


def bulb(c, cx, cy, k=BK, s=1.0, rot=0.0, rotten=0.0, alpha=1.0):
    """Bulbe centré en (cx, cy), tourné de rot° (180 = tête en bas)."""
    place(c, A + "bulbe", BULB_BOX, k, *BULB_C, cx, cy, s, rot, rotten, alpha)


# repères de la coupe « 20 cm » (coordonnées écran 1080×1920, fond sans travelling)
HOLE_X, HOLE_BOT = 548, 1182          # trou du milieu : centre et fond
SURF_Y = 640                          # haut de la flèche « 20 cm »
BULB_Y = HOLE_BOT - BULB_H / 2 + 8    # centre du bulbe posé au fond du trou
HOLE_L = [(452, 1150), (446, 1000), (425, 850), (405, 700)]    # bord gauche du trou (bas → haut)
HOLE_R = [(645, 1150), (652, 1000), (690, 850), (705, 700)]    # bord droit


# ============================================================ A. AU PRINTEMPS : LE PARTERRE DU VOISIN (0 → 3.62)
def s_intro(t):
    w, u = new_layers(photo_bg("tulipes_fond_voisin", t, 0.0, 3.62, 1.0, 1.07, 0.5, 0.6))
    title(u, "AU PRINTEMPS…", t, 0.2, 1.55, y=330, size=160)
    title(u, "DES TULIPES PARTOUT", t, 1.6, None, y=330, color=YEL, size=125)
    sparkles(u, t, 1.65, 540, 900, 420, 10, 3)
    return w, u


cue(0.1, "rustle", 0.2)
cue(1.65, "sparkle", 0.25)


# ============================================================ B. « JE VEUX LES MÊMES » : LE PARTERRE RÊVÉ (3.62 → 5.9)
@lru_cache(None)
def dream_vignette():
    """Bords blancs flous façon « rêve »."""
    m = Image.new("L", (W, H), 255)
    ImageDraw.Draw(m).ellipse([-120, 80, W + 120, H - 80], fill=0)
    m = m.filter(ImageFilter.GaussianBlur(120))
    im = Image.new("RGBA", (W, H), (255, 252, 240, 0))
    im.putalpha(m.point(lambda v: int(v * 0.85)))
    return im


def s_dream(t):
    w, u = new_layers(photo_bg("tulipes_fond_reve", t, 3.62, 5.9, 1.04, 1.0, 0.5, 0.55))
    w.alpha_composite(dream_vignette())
    for i in range(3):   # petites bulles de pensée qui montent
        r = 16 + i * 12
        x, y = 250 + i * 60, 1300 - i * 90 - 30 * math.sin(t * 2 + i)
        s = life(t, 3.7 + i * 0.08)
        if s > 0.01:
            ImageDraw.Draw(u).ellipse([x - r * s, y - r * s, x + r * s, y + r * s], fill=WHITE, outline=DARK, width=6)
    title(u, "JE VEUX LES MÊMES !", t, 3.66, None, y=330, color=YEL, size=130)
    sparkles(u, t, 3.75, 540, 1000, 420, 10, 5)
    return w, u


cue(3.7, "sparkle", 0.3)


# ============================================================ C. MAIS AU PRINTEMPS… TROP TARD : SOL NU (5.9 → 8.05)
def s_late(t):
    w, u = new_layers(photo_bg("tulipes_fond_sol_nu", t, 5.9, 8.05, 1.0, 1.06, 0.5, 0.7))
    title(u, "MAIS AU PRINTEMPS…", t, 5.98, 7.4, y=330, size=135)
    stamp(u, "TROP TARD !", 540, 620, t, 7.45, None, RED, 150, -8)
    return w, u


cue(7.45, "thud", 0.4)
cue(7.5, "alert2", 0.35)


# ============================================================ D. BONNE NOUVELLE : C'EST MAINTENANT (JARDINERIE) (8.05 → 11.55)
def s_now(t):
    w, u = new_layers(photo_bg("tulipes_fond_jardinerie", t, 8.05, 11.55, 1.0, 1.05, 0.4, 0.2))
    if t > 10.1:
        cx, cy, sc = CUR["map"](359, 183)
        hl_ellipse(u, cx, cy, 52 * sc, 50 * sc, life(t, 10.15))
        tag(u, "AUTOMNE = PLANTATION", 640, cy + 230, t, 10.3, None, rot=-4, size=46,
            string_to=(cx + 20, cy + 62 * sc))
    title(u, "BONNE NOUVELLE !", t, 9.1, 10.0, y=1260, color=YEL, size=140)
    title(u, "C'EST MAINTENANT !", t, 10.06, None, y=1260, color=YEL, size=140)
    return w, u


cue(9.12, "success", 0.3)
cue(10.15, "pop_hi", 0.25)


# ============================================================ E. TULIPE, JONQUILLE, CROCUS (11.55 → 13.85)
MEDS = [("tulipes_fond_voisin", (470, 380, 720, 630), "TULIPE", 11.66),
        ("tulipes_fond_reve", (385, 830, 635, 1080), "JONQUILLE", 12.3),
        (None, (280, 80, 800, 600), "CROCUS", 13.02)]


@lru_cache(None)
def crocus_med():
    ph = Image.open(os.path.join(IMG, A + "crocus_photo.jpg")).convert("RGB")
    S = 300
    ph = ph.crop((280, 80, 800, 600)).resize((S - 40, S - 40), Image.LANCZOS)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, S - 1, S - 1], fill=DARK)
    d.ellipse([9, 9, S - 10, S - 10], fill=CREAM)
    m = Image.new("L", (S - 40, S - 40), 0)
    ImageDraw.Draw(m).ellipse([0, 0, S - 41, S - 41], fill=255)
    im.paste(ph, (20, 20), m)
    return im


def s_kinds(t):
    w, u = new_layers(background("table"))
    for i, (src, box, lab, t0) in enumerate(MEDS):
        x = 190 + i * 350
        y = 760 + (60 if i == 1 else 0)
        med = medallion(src, box) if src else crocus_med()
        put(u, med, x, y, life(t, t0), math.sin(t * 2 + i) * 3)
        put(u, text_img(lab, F_TITLE, 52, YEL, 7, DARK, 6, DARK), x, y + 200, life(t, t0 + 0.06), -3)
    # le bulbe et le sachet posés sur la table
    bulb(w, 330, TABLE - 60, BK * 1.15, life(t, 11.6))
    place(w, A + "sachet", (111, 61, 1137, 1194), 0.3, 624, 1194, 760, TABLE + 40, life(t, 11.7))
    title(u, "TOUS LES BULBES", t, 11.6, None, y=330, size=140)
    return w, u


for _i, _t0 in enumerate((11.66, 12.3, 13.02)):
    cue(_t0, "pop", 0.25)


# ============================================================ F. DANS LA TERRE : PROFONDEUR, SENS, DRAINAGE (13.85 → 23.25)
@lru_cache(None)
def hole_mask():
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    d.polygon(HOLE_L + HOLE_R[::-1], fill=255)
    d.ellipse([HOLE_L[0][0], 1110, HOLE_R[0][0], HOLE_BOT + 8], fill=255)
    return m.filter(ImageFilter.GaussianBlur(6))


def water_in_hole(c, top, t, a=1.0):
    """Eau trouble qui remplit le trou jusqu'à `top` (y écran), épousant sa forme."""
    if top >= HOLE_BOT or a <= 0.01:
        return
    col = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(col)
    for y in range(int(top), HOLE_BOT + 10, 6):
        f = (y - top) / max(1, HOLE_BOT - top)
        d.rectangle([0, y, W, y + 6], fill=(int(lerp(110, 80, f)), int(lerp(165, 130, f)), int(lerp(215, 185, f)),
                                            int(lerp(85, 125, f) * a)))
    wave = [(x, top + 4 * math.sin(x * 0.05 + t * 6)) for x in range(380, 720, 8)]
    d.line(wave, fill=(215, 235, 248, int(220 * a)), width=5)
    m = hole_mask().copy()
    ImageDraw.Draw(m).rectangle([0, 0, W, int(top) - 4], fill=0)
    col.putalpha(Image.composite(col.getchannel("A"), Image.new("L", (W, H), 0), m))
    c.alpha_composite(col)


def s_soil(t):
    w, u = new_layers(photo_bg("tulipes_fond_coupe_20cm", t, 13.85, 23.25, plain=True))
    # --- 1. le bulbe tombe au fond du trou (13.9)
    drop = ease_out((t - 13.95) / 0.45)
    by = lerp(-150, BULB_Y, drop)
    # --- 2. pointe vers le haut / sinon à l'envers (16.8 → 19.6)
    flip = ease_io((t - 18.15) / 0.35) * (1 - ease_io((t - 19.3) / 0.35))
    rot = 180 * flip
    # --- 3. terre drainante / sinon il pourrit (19.6 → 23.25)
    flood = ease_io((t - 21.9) / 0.6)
    rotten = 0.8 * ease_io((t - 22.3) / 0.6)
    if t > 19.7 and flood < 0.05:
        for i in range(8):   # l'eau traverse la terre et s'en va vers le bas
            tt = (t - 19.75 - i * 0.12) % 1.2
            put(w, icon("drop", 40), 470 + (i % 4) * 60, lerp(560, 1750, tt / 1.2), 1, 0, 1 - tt / 1.2)
    wl, wa = lerp(HOLE_BOT, 860, flood), fade(t, 21.9, None, 0.3)
    water_in_hole(w, wl, t, wa)            # l'eau derrière le bulbe…
    if t > 13.9:
        bulb(w, HOLE_X, by, rot=rot, rotten=rotten)
    water_in_hole(w, wl, t, wa * 0.3)      # …et un voile léger devant : le bulbe baigne dedans
    if wa > 0.3:
        for i in range(5):                 # bulles qui remontent
            tt = (t * 0.8 + i * 0.21) % 1.0
            x, y = HOLE_X - 60 + i * 30, lerp(HOLE_BOT - 20, wl + 10, tt)
            ImageDraw.Draw(w).ellipse([x - 7, y - 7, x + 7, y + 7], outline=(225, 242, 252, 200), width=3)
    if 14.3 < t < 14.9:
        particles(w, t, 14.35, HOLE_X, HOLE_BOT - 10, 12, 4, col=(80, 52, 32), size=9, up=300)
    # repères ×3 : 3 bulbes fantômes empilés du fond du trou jusqu'à la surface
    if 15.15 < t < 16.75:
        for i in range(1, 3):
            s = life(t, 15.2 + i * 0.25, 16.7)
            if s > 0.01:
                bulb(u, HOLE_X, BULB_Y - i * (BULB_H - 20), s=s, alpha=0.45)
        for i in range(3):
            s = life(t, 15.2 + i * 0.25, 16.7)
            put(u, text_img(str(i + 1), F_TITLE, 60, YEL, 7, DARK, 6, DARK), HOLE_X + 150, BULB_Y - i * (BULB_H - 20), s)
        tag(u, "2 À 3 × SA HAUTEUR", 800, 520, t, 15.75, 16.7, rot=-4, size=46)
    if 16.85 < t < 18.1:
        put(u, icon("arrow_down", 110), HOLE_X, BULB_Y - 190 - 12 * math.sin(t * 7), life(t, 16.9, 18.05), 180)
        put(u, icon("check", 120), HOLE_X + 190, BULB_Y - 60, life(t, 17.1, 18.05))
    if 18.15 < t < 19.6:
        put(u, icon("cross", 130), HOLE_X + 190, BULB_Y - 60, life(t, 18.3, 19.3))
    if 19.7 < t < 21.85:
        put(u, icon("check", 120), HOLE_X + 190, BULB_Y - 60, life(t, 20.5, 21.8))
    if t > 22.3:
        put(u, icon("cross", 140), HOLE_X + 190, BULB_Y - 60, life(t, 22.4))
    title(u, "ENTERRE CHAQUE BULBE", t, 13.94, 15.1, y=330, size=120)
    title(u, "2 À 3 FOIS SA HAUTEUR", t, 15.16, 16.75, y=330, color=YEL, size=120)
    title(u, "LA POINTE EN HAUT", t, 16.82, 18.05, y=330, color=YEL, size=135)
    title(u, "SINON… À L'ENVERS !", t, 18.12, 19.6, y=330, color=RED, size=125)
    title(u, "TERRE DRAINANTE", t, 19.66, 21.85, y=330, color=YEL, size=135)
    title(u, "SINON IL POURRIT", t, 21.9, None, y=330, color=RED, size=135)
    return w, u


cue(14.3, "thud", 0.35)
for _i in range(3):
    cue(15.2 + _i * 0.25, "tick", 0.25)
cue(16.9, "pop_hi", 0.22)
cue(18.15, "whoosh", 0.18)
cue(18.3, "alert1", 0.3)
cue(19.3, "whoosh_up", 0.16)
cue(19.75, "pour", 0.25)
cue(21.95, "splash", 0.3)
cue(22.4, "fail", 0.38)


# ============================================================ G. POURQUOI EN AUTOMNE ? LE FROID DE L'HIVER (23.25 → 26.45)
def s_winter(t):
    w, u = new_layers(photo_bg("tulipes_fond_sol_nu", t, 23.25, 26.45, 1.06, 1.0, 0.5, 0.7))
    cold = fade(t, 24.8, None, 0.6)
    if cold > 0.01:
        w.alpha_composite(Image.new("RGBA", (W, H), (150, 190, 235, int(80 * cold))))
        falling(w, t, 24.85, None, "snow", 22, 4, 380, 46, sway=40)
        put(u, icon("thermo", 140), 900, 640, life(t, 25.1))
        put(u, icon("snow", 140), 180, 640, life(t, 24.9))
    title(u, "POURQUOI EN AUTOMNE ?", t, 23.34, 24.72, y=330, size=115)
    title(u, "LE FROID DE L'HIVER", t, 24.78, None, y=330, color=YEL, size=125)
    return w, u


cue(23.38, "pop", 0.22)
cue(24.85, "rise", 0.2)


# ============================================================ H. POUR FLEURIR : LES PLUS BEAUX PARTERRES (26.45 → 29.9)
def s_bloom(t):
    w, u = new_layers(photo_bg("tulipes_fond_reve", t, 26.45, 29.9, 1.08, 1.0, 0.5, 0.5))
    sparkles(u, t, 26.5, 540, 900, 460, 12, 7)
    sparkles(u, t, 28.9, 540, 1000, 460, 10, 8)
    title(u, "POUR FLEURIR !", t, 26.5, 27.35, y=330, color=YEL, size=160)
    title(u, "LES PLUS BEAUX PARTERRES", t, 27.42, None, y=330, color=YEL, size=105)
    return w, u


cue(26.52, "success", 0.35)
cue(28.95, "sparkle", 0.25)


# ============================================================ I. CTA (29.9 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    place(w, A + "sachet", (111, 61, 1137, 1194), 0.36, 624, 1194, 280, TABLE + 40, life(t, 29.95))
    bulb(w, 800, TABLE - 50, BK * 1.3, life(t, 30.05))
    clicked = t > 30.6
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 30.55) / 0.15))
    put(u, btn, 540, 300, life(t, 30.0) * press)
    if t > 30.25:
        k = ease_out((t - 30.25) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(330), 540, 590, life(t, 31.6, dur=0.45))
    sparkles(u, t, 31.7, 540, 590, 230, 10, 12)
    return w, u


cue(30.58, "click", 0.45)
cue(31.7, "sparkle", 0.25)

if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video), (VID_END, 3.62, s_intro)]
else:
    _intro = [(0.0, 3.62, s_intro)]

SCENES = _intro + [
    (3.62, 5.9, s_dream),
    (5.9, 8.05, s_late),
    (8.05, 11.55, s_now),
    (11.55, 13.85, s_kinds),
    (13.85, 23.25, s_soil),
    (23.25, 26.45, s_winter),
    (26.45, 29.9, s_bloom),
    (29.9, 99.0, s_cta),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []

if HAS_VIDEO:
    CUES[:] = [c for c in CUES if c[0] >= VID_END - 0.05]
