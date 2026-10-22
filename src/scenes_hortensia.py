"""Storyboard « Bouturer un hortensia à partir d'une tige » (voix : assets/audio/hortensia/voix.mp3).

Photos fournies (détourées, cadre 1024 d'origine conservé) : hortensia en pot, hortensia avec sa motte,
bouture entière, bouture aux feuilles coupées en deux (les deux moitiés en sont extraites pour tomber).
Si assets/video/intro_hortensia.mp4 existe, la première phrase montre cette vidéo brute (sans texte, son
coupé) avant le motion design.
"""
import math
import os
import subprocess
from functools import lru_cache

from PIL import Image, ImageDraw

from gfx import (ROOT, IMG, shadow_blob, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, spr, put, title, life, fade,
                 ease_out, ease_in, ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse,
                 particles, text_img, aa, roots, window_img, F_TITLE, F_BLACK)
from scenes import TABLE, new_layers, sparkles
from scenes_aromatiques import pot, snow_window
from scenes_ananas import place, logo_img

CUES = []
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


A = "hortensia/"
FULL = (0, 0, 1024, 1024)
VIDEO = os.path.join(ROOT, "assets", "video", "intro_hortensia.mp4")
HAS_VIDEO = os.path.exists(VIDEO)


def video_duration():
    if not HAS_VIDEO:
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                         capture_output=True, text=True).stdout
    return min(3.2, float(out.strip() or 0))


VID_END = video_duration()
NO_CAPTION_UNTIL = VID_END


@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_hortensia_intro")
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

# ------------------------------------------------------------- géométrie des photos (coordonnées d'origine 1024)
STEM = (498, 970)          # bas de la tige des deux boutures
NODE_TOP = (512, 495)      # 1re paire de bourgeons (attache des feuilles)
NODE_LOW = (512, 688)      # 2e paire de bourgeons
POT_BASE = (519, 978)      # bas du pot / de la motte
POT_RIM = 636              # haut du pot en terre cuite
CUT_L = ((120, 320), (392, 150))   # trait de coupe feuille gauche (extérieur → centre)
CUT_R = ((906, 320), (646, 156))   # trait de coupe feuille droite


@lru_cache(None)
def raw(name):
    return Image.open(os.path.join(IMG, A + name + ".png")).convert("RGBA")


def cutting(c, X, Y, k, s=1.0, cut=False, rot=0.0, rotten=0.0, alpha=1.0):
    """Bouture posée par le bas de sa tige en (X, Y)."""
    place(c, A + ("bouture_coupee" if cut else "bouture"), FULL, k, *STEM, X, Y, s, rot, rotten, alpha)


def plant(c, name, X, Y, k, s=1.0, rotten=0.0):
    if s > 0.01:
        sw = 380 * k * s
        sb = shadow_blob().resize((max(2, int(sw * 1.25)), max(2, int(sw * 0.3))))
        c.alpha_composite(sb, (int(X - sb.width / 2), int(Y - 12 * k - sb.height * 0.55)))
    place(c, A + name, FULL, k, *POT_BASE, X, Y, s, 0.0, rotten)


def at(p, X, Y, k, origin=STEM):
    """Point p de la photo → coordonnées écran, la photo étant posée par `origin` en (X, Y)."""
    return X + (p[0] - origin[0]) * k, Y + (p[1] - origin[1]) * k


@lru_cache(None)
def piece(name):
    im = raw(name)
    bb = im.getbbox()
    return im.crop(bb), bb


def put_piece(c, name, X, Y, k, dx=0.0, dy=0.0, rot=0.0, alpha=1.0, origin=STEM):
    im, bb = piece(name)
    cx, cy = at(((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2), X, Y, k, origin)
    put(c, im, cx + dx, cy + dy, k, rot, alpha)


@lru_cache(None)
def small_leaf():
    """Feuille entière (gauche) de la bouture, pétiole en bas à droite → feuilles du bas."""
    im = raw("bouture").crop((96, 91, 500, 520))
    return im


@lru_cache(None)
def flower():
    """Tête de fleur bleue découpée dans la photo de l'hortensia en pot."""
    r, cx, cy = 100, 735, 170
    src = Image.open(os.path.join(ROOT, "assets", "images", "source_utilisateur", "hortensia_pot.webp")).convert("RGBA")
    ph = src.crop((cx - r, cy - r, cx + r, cy + r)).resize((300, 300), Image.LANCZOS)
    S = 340
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, S - 1, S - 1], fill=DARK)
    d.ellipse([8, 8, S - 9, S - 9], fill=CREAM)
    m = Image.new("L", (300, 300), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 299, 299], fill=255)
    im.paste(ph, (20, 20), m)
    return im


def low_leaves(c, X, Y, k, t, t0):
    """Deux petites feuilles à la 2e paire de bourgeons, qui tombent à t0."""
    nx, ny = at(NODE_LOW, X, Y, k)
    lf = small_leaf()
    sc = k * 0.5
    for side in (-1, 1):
        im = lf if side < 0 else lf.transpose(Image.FLIP_LEFT_RIGHT)
        # le pétiole (coin bas intérieur) doit toucher la tige
        ox = -im.width * sc / 2 + 18 * sc if side < 0 else im.width * sc / 2 - 18 * sc
        cx, cy = nx + ox, ny - im.height * sc / 2 + 14 * sc
        rot = 0.0
        if t > t0:
            p = t - t0
            cx += side * 160 * p
            cy += 1500 * p * p
            rot = -side * 160 * p
        if cy < H + 300:
            put(c, im, cx, cy, sc, rot)


def scissors(c, p0, p1, p, flip=False, hh=150):
    """Ciseaux dont la pointe glisse de p0 vers p1 (p = 0..1)."""
    if p <= 0 or p >= 1.15:
        return
    q = clamp(p)
    px, py = lerp(p0[0], p1[0], q), lerp(p0[1], p1[1], q)
    ang = math.degrees(math.atan2(-(p1[1] - p0[1]), p1[0] - p0[0]))
    sc = hh / 260
    tip = (336 * sc, -75 * sc)
    if flip:
        tip = (-336 * sc, -75 * sc)
        ang = ang - 180
    a = math.radians(ang)
    rx = tip[0] * math.cos(a) + tip[1] * math.sin(a)
    ry = -tip[0] * math.sin(a) + tip[1] * math.cos(a)
    im = spr_img("arrosage/ciseaux", hh, flip)
    snip = 5 * math.sin(p * 40)
    put(c, im, px - rx, py - ry, 1.0, ang + snip)


@lru_cache(None)
def spr_img(name, hh, flip=False):
    im = Image.open(os.path.join(IMG, name + ".png")).convert("RGBA")
    im = im.resize((int(im.width * hh / im.height), int(hh)), Image.LANCZOS)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


def dashed(c, p0, p1, a=1.0, col=WHITE):
    if a <= 0.01:
        return
    d = ImageDraw.Draw(c)
    n = 12
    for i in range(n):
        if i % 2:
            continue
        q0, q1 = i / n, (i + 1) / n
        d.line([(lerp(p0[0], p1[0], q0), lerp(p0[1], p1[1], q0)), (lerp(p0[0], p1[0], q1), lerp(p0[1], p1[1], q1))],
               fill=col + (int(255 * a),), width=9)


def stamp(c, txt, x, y, t, t0, t1=None, color=RED, size=150, rot=-12):
    """Tampon qui s'écrase (grand → taille normale) avec un cadre."""
    if t < t0:
        return
    k = clamp((t - t0) / 0.18)
    s = lerp(2.2, 1.0, ease_out(k))
    a = clamp(k * 1.5) * (1 - clamp((t - t1) / 0.2) if t1 else 1)
    if a <= 0.01:
        return
    ti = text_img(txt, F_TITLE, size, color, 0)
    w, h = ti.width + 70, ti.height + 40
    im = aa(w, h, lambda d, kk, _: (
        d.rounded_rectangle([0, 0, w * kk - 1, h * kk - 1], radius=24 * kk, outline=color, width=int(12 * kk)),))
    im.alpha_composite(ti, (35, 20))
    put(c, im, x, y, s, rot, alpha=a)


def soil_pile(c, x, y, w_, col, seed, s=1.0):
    """Petit tas (terreau ou sable) fait de grains."""
    if s <= 0.01:
        return
    import numpy as np
    r = np.random.default_rng(seed)
    d = ImageDraw.Draw(c)
    w_ *= s
    hgt = w_ * 0.45
    d.ellipse([x - w_ / 2 - 10, y - 14, x + w_ / 2 + 10, y + 18], fill=(80, 52, 32, 90))
    d.chord([x - w_ / 2, y - hgt * 2, x + w_ / 2, y + 2], 180, 360, fill=col)
    for _ in range(int(220 * s)):
        u = r.uniform(-1, 1)
        top = y - hgt * math.sqrt(max(0, 1 - u * u))
        gx, gy = x + u * w_ / 2, r.uniform(min(top + 4, y - 1), y)
        g = r.uniform(-28, 28)
        rad = r.uniform(3, 6) * s
        d.ellipse([gx - rad, gy - rad, gx + rad, gy + rad],
                  fill=tuple(int(clamp((v + g) / 255) * 255) for v in col))


TERREAU = (78, 54, 36)
SABLE = (214, 182, 128)


def gauge(c, t, t0, pos, y=1408, x0=150, x1=930):
    """Jauge d'humidité SEC | HUMIDE | DÉTREMPÉE ; pos = 0..1 (curseur)."""
    s = life(t, t0)
    if s <= 0.01:
        return
    d = ImageDraw.Draw(c)
    cols = [(206, 170, 112), (90, 160, 200), (40, 70, 140)]
    for i, col in enumerate(cols):
        a = x0 + (x1 - x0) * i / 3
        b = x0 + (x1 - x0) * (i + 1) / 3
        d.rectangle([a, y - 26, b, y + 26], fill=col)
    d.rounded_rectangle([x0 - 6, y - 32, x1 + 6, y + 32], radius=10, outline=DARK, width=8)
    for i, lab in enumerate(["SEC", "HUMIDE", "DÉTREMPÉE"]):
        put(c, text_img(lab, F_BLACK, 32, WHITE, 5, DARK), x0 + (x1 - x0) * (i + 0.5) / 3, y, s)
    px = lerp(x0, x1, pos)
    d.polygon([(px - 24, y - 70), (px + 24, y - 70), (px, y - 34)], fill=DARK)


# ============================================================ A. UN HORTENSIA GRATUIT, UNE SEULE TIGE ? (0 → 3.3)
def s_intro(t):
    w, u = new_layers(background("table"))
    m = ease_io((t - 2.1) / 0.5)
    plant(w, "pot", lerp(540, 790, m), TABLE + 30, lerp(0.9, 0.65, m), life(t, 0.0, dur=0.4))
    if t > 2.14:
        cutting(w, 230, TABLE + 20, 0.5, life(t, 2.2))
        put(u, icon("arrow_down", 100), 478, TABLE - 250, life(t, 2.5), 90)
        put(u, icon("question", 120), 230, 640, life(t, 2.7), math.sin(t * 5) * 6)
    if t < 2.14:
        put(u, tag_price(), 880, 1140, life(t, 1.02, 2.1), 8 + 4 * math.sin(t * 6))
        sparkles(u, t, 1.05, 880, 1140, 160, 8, 2)
    title(u, "HORTENSIA GRATUIT", t, 0.4, 2.05, y=330, size=130)
    title(u, "UNE SEULE TIGE ?", t, 2.14, None, y=330, color=YEL, size=140)
    return w, u


@lru_cache(None)
def tag_price():
    ti = text_img("0 €", F_TITLE, 120, WHITE, 8, DARK, 6, DARK)
    w_, h_ = ti.width + 90, ti.height + 50
    im = aa(w_, h_, lambda d, k, _: (
        d.rounded_rectangle([0, 0, w_ * k - 1, h_ * k - 1], radius=30 * k, fill=GREEN, outline=DARK, width=int(8 * k)),))
    im.alpha_composite(ti, (45, 25))
    return im


cue(0.05, "pop_lo", 0.35)
cue(0.4, "whoosh_up", 0.2)
cue(1.02, "bell", 0.35)
cue(2.14, "whoosh", 0.25)
cue(2.2, "pop", 0.3)
cue(2.7, "pop_hi", 0.25)


# ============================================================ B. OUI OUI, SUPER SIMPLE (3.3 → 5.85)
def s_yes(t):
    w, u = new_layers(background("table"))
    bob = math.sin(t * 3) * 6
    cutting(w, 540, TABLE + 20 + bob, 0.85, life(t, 3.32))
    stamp(u, "OUI OUI !", 540, 360, t, 3.38, 4.55, GREEN, 140, -8)
    title(u, "SUPER SIMPLE", t, 4.62, None, y=330, size=150)
    act = -1 if t < 4.9 else min(2, int((t - 4.9) / 0.28))
    pills(u, ["COUPE", "PRÉPARE", "PLANTE"], act, t, 4.7, None, y=1430, pw=250)
    return w, u


cue(3.32, "pop", 0.3)
cue(3.38, "thud", 0.45)
cue(3.42, "success", 0.3)
cue(4.62, "whoosh_up", 0.25)
for _k in range(3):
    cue(4.9 + _k * 0.28, "tick", 0.3)


# ============================================================ C. ÉTAPE 1 : TIGE DE L'ANNÉE, SANS FLEURS, 2 PAIRES (5.85 → 9.15)
SNIP = (655, 470)   # point de coupe sur la photo du pot


def s_step1(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("1", 160), 190, 560, life(t, 5.9, 6.9))
    title(u, "ÉTAPE 1", t, 5.9, 6.45, y=330)
    if t < 6.9:
        k = 0.92
        plant(w, "pot", 540, TABLE + 30, k)
        sx, sy = at(SNIP, 540, TABLE + 30, k, POT_BASE)
        hl_ellipse(w, sx, sy - 40, 120, 150, life(t, 6.1, 6.85))
        if t > 6.15:
            snip = abs(math.sin((t - 6.15) * 9)) * 14
            spr(w, "bouture/secateur", sx + 117, sy + 74, 230, rot=-snip, shadow=False, anchor="center")
        title(u, "TIGE DE L'ANNÉE", t, 6.5, 6.9, y=330, size=130)
    elif t < 7.62:
        cutting(w, 330, TABLE + 20, 0.78, life(t, 6.92))
        put(u, icon("check", 140), 330, 560, life(t, 7.2))
        put(w, flower(), 790, 860, life(t, 7.0), 6)
        put(u, icon("nosign", 330), 790, 860, life(t, 7.18))
        title(u, "SANS FLEURS", t, 6.98, None, y=330, color=RED, size=150)
    else:
        k = 1.0
        X, Y = 540, TABLE + 20
        cutting(w, X, Y, k, life(t, 7.64))
        for i, (node, t0) in enumerate(((NODE_TOP, 8.0), (NODE_LOW, 8.3))):
            nx, ny = at(node, X, Y, k)
            hl_ellipse(u, nx, ny, 90, 60, life(t, t0))
            put(u, num_badge(str(i + 1), 100, YEL), nx + 190, ny, life(t, t0 + 0.06))
        title(u, "2 PAIRES DE BOURGEONS", t, 7.66, None, y=330, size=110)
    return w, u


cue(5.9, "rise", 0.3)
cue(6.2, "chop", 0.55)
cue(6.92, "whoosh", 0.25)
cue(7.18, "alert2", 0.35)
cue(7.64, "pop", 0.3)
cue(8.0, "pop_hi", 0.3)
cue(8.3, "pop_hi", 0.3)


# ============================================================ D. ÉTAPE 2 : FEUILLES DU BAS, CELLES DU HAUT EN DEUX (9.15 → 12.1)
def s_step2(t):
    w, u = new_layers(background("table"))
    k, X, Y = 1.0, 540, TABLE + 20
    put(u, num_badge("2", 160), 190, 560, life(t, 9.2, 9.9))
    title(u, "ÉTAPE 2", t, 9.2, 9.65, y=330)
    title(u, "FEUILLES DU BAS", t, 9.7, 10.6, y=330, size=135)
    title(u, "EN DEUX !", t, 10.66, None, y=330, color=YEL, size=160)
    cut_l, cut_r = 11.05, 11.4
    if t < 11.05:
        cutting(w, X, Y, k)
    else:
        cutting(w, X, Y, k, cut=True)
    low_leaves(w, X, Y, k, t, 9.75)
    if 9.7 < t < 10.6:
        nx, ny = at(NODE_LOW, X, Y, k)
        hl_ellipse(u, nx, ny, 170, 110, life(t, 9.72, 10.5))
    # moitiés des feuilles du haut : restent en place jusqu'à leur coupe, puis tombent
    for name, tc, side in (("moitie_g", cut_l, -1), ("moitie_d", cut_r, 1)):
        if t < 11.05:
            continue
        p = max(0.0, t - tc)
        put_piece(w, name, X, Y, k, side * 220 * p, 1700 * p * p - 60 * p, side * 140 * p)
    pl = [at(q, X, Y, k) for q in CUT_L]
    pr = [at(q, X, Y, k) for q in CUT_R]
    a = fade(t, 10.66, None, 0.15)
    if t < cut_l:
        dashed(u, *pl, a)
    if t < cut_r:
        dashed(u, *pr, a)
    scissors(u, pl[0], pl[1], (t - 10.75) / 0.3)
    scissors(u, pr[0], pr[1], (t - 11.1) / 0.3, flip=True)
    return w, u


cue(9.2, "rise", 0.3)
cue(9.75, "crunch", 0.4)
cue(9.8, "whoosh", 0.2)
cue(10.66, "pop_hi", 0.25)
cue(10.8, "chop", 0.45)
cue(11.15, "chop", 0.45)
cue(11.42, "whoosh", 0.2)


# ============================================================ E. ÉTAPE 3 : TERREAU + SABLE, À L'ABRI DU FROID (12.1 → 15.8)
POT_TOP = TABLE - 330


def potted(c, t, t0=12.2, k=0.78, rotten=0.0, s=1.0):
    """La bouture descend dans le pot (dessinée avant le pot : la tige disparaît sous le terreau)."""
    drop = ease_out((t - t0) / 0.45)
    cutting(c, 540, lerp(POT_TOP - 300, POT_TOP + 230, drop), k, s, cut=True, rotten=rotten)
    pot(c, 540, POT_TOP, 420, 330)


def s_step3(t):
    w, u = new_layers(background("table"))
    cold = t > 14.54
    if cold:
        put(w, window_img(), 540, 700, life(t, 14.56))
        if t > 14.7:
            snow_window(w, t, 270, 350, 540, 620)
    potted(w, t)
    if t > 12.7:
        particles(w, t, 12.62, 540, POT_TOP, 12, 4, col=(90, 62, 40), size=9, up=300)
    soil_pile(w, 170, TABLE + 60, 230, TERREAU, 3, life(t, 13.38, 14.5))
    soil_pile(w, 910, TABLE + 60, 230, SABLE, 5, life(t, 14.1, 14.5))
    tag(u, "TERREAU", 190, TABLE - 120, t, 13.42, 14.5, rot=-5, size=44)
    tag(u, "SABLE", 900, TABLE - 120, t, 14.12, 14.5, rot=5, size=44)
    if cold:
        put(u, icon("snow", 140), 180, 600, life(t, 14.7))
        put(u, icon("nosign", 190), 180, 600, life(t, 14.9))
        put(u, icon("check", 130), 900, 600, life(t, 15.05))
    put(u, num_badge("3", 160), 190, 560, life(t, 12.2, 12.9))
    title(u, "ÉTAPE 3", t, 12.2, 12.8, y=330)
    title(u, "TERREAU + SABLE", t, 12.86, 14.5, y=330, size=135)
    title(u, "À L'ABRI DU FROID", t, 14.56, None, y=330, size=125)
    return w, u


cue(12.2, "rise", 0.3)
cue(12.3, "whoosh", 0.25)
cue(12.62, "crunch", 0.4)
cue(13.38, "pour", 0.35)
cue(14.1, "pour", 0.3)
cue(14.56, "whoosh_up", 0.2)
cue(14.9, "pop_lo", 0.3)
cue(15.05, "ding", 0.3)


# ============================================================ F. PETIT SECRET : HUMIDE, JAMAIS DÉTREMPÉE (15.8 → 19.45)
def overflow(c, t, t0):
    """Le pot déborde : eau sur le terreau, coulures sur le pot, flaque sur la table."""
    p = ease_out((t - t0) / 0.6)
    if p <= 0:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = int(190 * p)
    d.ellipse([540 - 204, POT_TOP - 16, 540 + 204, POT_TOP + 32], fill=(70, 130, 200, a))
    d.ellipse([540 - 170, POT_TOP - 8, 540 + 150, POT_TOP + 16], outline=(200, 230, 250, a), width=4)
    for i, x in enumerate((360, 450, 610, 700)):
        ln = clamp((t - t0 - 0.15 - i * 0.07) / 0.5) * (300 - abs(x - 540) * 0.6)
        if ln > 0:
            d.line([(x, POT_TOP + 40), (x + (x - 540) * 0.05, POT_TOP + 40 + ln)], fill=(90, 150, 215, a), width=14)
    pw = 520 * ease_out((t - t0 - 0.4) / 0.6)
    if pw > 0:
        d.ellipse([540 - pw / 2, TABLE - 10, 540 + pw / 2, TABLE + 40], fill=(80, 140, 205, int(a * 0.8)))
    c.alpha_composite(ov)


def s_secret(t):
    w, u = new_layers(background("table"))
    rot = 0.85 * ease_io((t - 18.7) / 0.6)
    potted(w, t, t0=0.0, rotten=rot)
    if t > 18.06:
        overflow(w, t, 18.1)
    if t < 16.9:
        put(u, icon("lightbulb", 170), 540, 560, life(t, 15.9, 16.85), math.sin(t * 4) * 5)
    title(u, "PETIT SECRET", t, 15.9, 16.85, y=330)
    title(u, "TERRE HUMIDE", t, 16.9, 18.0, y=330, color=YEL, size=145)
    title(u, "JAMAIS DÉTREMPÉE", t, 18.06, None, y=330, color=RED, size=125)
    if 16.9 < t < 18.06:
        for i in range(3):
            tt = t - 17.15 - i * 0.25
            if 0 < tt < 0.5:
                put(w, icon("drop", 50), 470 + i * 70, lerp(POT_TOP - 420, POT_TOP, (tt / 0.5) ** 2), 1)
        put(u, icon("check", 130), 880, 620, life(t, 17.5))
    pos = lerp(0.18, 0.5, ease_out((t - 17.14) / 0.4))
    pos = lerp(pos, 0.84, ease_io((t - 18.3) / 0.45))
    gauge(u, t, 16.95, pos)
    if t > 18.75:
        put(u, icon("cross", 150), 880, 620, life(t, 18.78))
    return w, u


cue(15.9, "sparkle", 0.3)
cue(16.9, "pop", 0.3)
cue(17.15, "plop", 0.25)
cue(17.4, "plop", 0.2)
cue(17.5, "ding", 0.25)
cue(18.1, "splash", 0.35)
cue(18.78, "fail", 0.4)


# ============================================================ G. AU PRINTEMPS : DES RACINES… UN NOUVEL HORTENSIA (19.45 → 23.4)
SOIL = 1000


def s_spring(t):
    warm = fade(t, 19.5, None, 0.6)
    if t < 21.7:
        w, u = new_layers(background("none", SOIL, warm=warm))
        k, X, Y = 0.82, 540, SOIL + 230
        rg = ease_out((t - 20.9) / 0.8)
        roots(w, X, Y - 10, rg, 7, spread=120, length=280, n=13)
        cutting(w, X, Y, k, life(t, 19.5), cut=True)
        if t > 20.9:
            sparkles(w, t, 21.0, X, Y + 120, 220, 8, 6)
        title(u, "AU PRINTEMPS…", t, 19.54, 20.65, y=330)
        title(u, "DES RACINES !", t, 20.7, None, y=330, color=YEL)
    else:
        w, u = new_layers(background("table", warm=warm))
        plant(w, "motte", 540, TABLE + 30, 0.86, life(t, 21.72, dur=0.45))
        sparkles(w, t, 22.0, 540, 700, 380, 10, 8)
        tag(u, "GRATUIT !", 850, 1200, t, 22.6, rot=-5, size=60)
        title(u, "UN NOUVEL HORTENSIA !", t, 21.74, None, y=330, color=YEL, size=110)
    put(u, icon("sun", 170), 880, 560, life(t, 19.6, 21.7), t * 25)
    return w, u


cue(19.5, "whoosh_up", 0.3)
cue(19.6, "sparkle", 0.25)
cue(20.9, "rise", 0.3)
cue(21.0, "pop_hi", 0.25)
cue(21.72, "pop_lo", 0.4)
cue(22.0, "success", 0.4)
cue(22.6, "pop", 0.25)


# ============================================================ H. CTA (23.4 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    plant(w, "pot", 250, TABLE + 30, 0.5, life(t, 23.45))
    cutting(w, 840, TABLE + 20, 0.42, life(t, 23.55), cut=True)
    clicked = t > 24.1
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 24.05) / 0.15))
    put(u, btn, 540, 300, life(t, 23.5) * press)
    if t > 23.75:
        k = ease_out((t - 23.75) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(330), 540, 590, life(t, 24.9, dur=0.45))
    sparkles(u, t, 25.0, 540, 590, 230, 10, 12)
    return w, u


cue(23.45, "pop_lo", 0.3)
cue(23.5, "pop_hi", 0.3)
cue(24.08, "click", 0.55)
cue(24.15, "bell", 0.35)
cue(25.0, "sparkle", 0.3)

if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video), (VID_END, 3.3, s_intro)]
else:
    _intro = [(0.0, 3.3, s_intro)]

SCENES = _intro + [
    (3.3, 5.85, s_yes),
    (5.85, 9.15, s_step1),
    (9.15, 12.1, s_step2),
    (12.1, 15.8, s_step3),
    (15.8, 19.45, s_secret),
    (19.45, 23.4, s_spring),
    (23.4, 99.0, s_cta),
]

TRAPS = [(1, 5.9, 9.15), (2, 9.2, 12.1), (3, 12.15, 15.8)]

if HAS_VIDEO:
    CUES[:] = [c for c in CUES if c[0] >= VID_END - 0.05]
