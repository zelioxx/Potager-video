"""Storyboard « Les feuilles mortes = paillage gratuit » (voix : assets/audio/feuilles/voix.mp3).

Photos fournies (détourées, cadre 1254 d'origine conservé) : tas de feuilles mortes, tondeuse, feuilles broyées,
ver de terre, brouette et râteau (séparés). La première phrase montre la vidéo brute fournie
(assets/video/intro_feuilles.mp4, sans texte, son coupé) avant le motion design.
"""
import math
import os
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (ROOT, IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, spr, put, title, life, fade,
                 ease_out, ease_io, clamp, lerp, icon, num_badge, tag, button_img, particles, text_img, F_TITLE,
                 F_BLACK)
from scenes import TABLE, new_layers, sparkles, falling
from scenes_ananas import place, logo_img
from scenes_hortensia import stamp

CUES = []
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


A = "feuilles/"
FULL = (0, 0, 1254, 1254)
VIDEO = os.path.join(ROOT, "assets", "video", "intro_feuilles.mp4")
HAS_VIDEO = os.path.exists(VIDEO)


def video_duration():
    if not HAS_VIDEO:
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                         capture_output=True, text=True).stdout
    return min(2.75, float(out.strip() or 0))


VID_END = video_duration()
NO_CAPTION_UNTIL = VID_END


@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_feuilles_intro")
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

# ------------------------------------------------------------- géométrie des photos (coordonnées d'origine 1254)
PILE_BASE = (630, 1040)       # bas du tas de feuilles
MULCH_BASE = (630, 1060)      # bas du tas broyé
MOWER_BASE = (640, 1190)      # sous les roues de la tondeuse
MOWER_FRONT = 1220            # avant de la tondeuse (roue avant droite)
BARROW_BASE = (560, 1150)     # sous la roue / les pieds de la brouette
RAKE_BASE = (1070, 1150)
LEAVES = ["feuilles/feuille_a", "feuilles/feuille_b", "feuilles/feuille_c"]   # platane (vidéo compost) teinté


@lru_cache(None)
def raw(name):
    return Image.open(os.path.join(IMG, A + name + ".png")).convert("RGBA")


def item(c, name, base, X, Y, k, s=1.0, rot=0.0, alpha=1.0, shadow=0.0):
    if s > 0.01 and shadow > 0:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        w_ = shadow * k * s
        ImageDraw.Draw(ov).ellipse([X - w_ / 2, Y - w_ * 0.06, X + w_ / 2, Y + w_ * 0.06], fill=(70, 45, 25, 70))
        c.alpha_composite(ov)
    place(c, A + name, FULL, k, *base, X, Y, s, rot, 0.0, alpha)


def leaves_falling(c, t, t0, t1, n=14, seed=2, bottom=None, size=1.0):
    """Feuilles d'automne (photos) qui tombent en virevoltant."""
    a = fade(t, t0, t1, 0.2, 0.3)
    if a <= 0:
        return
    r = np.random.default_rng(seed)
    bottom = bottom or H
    for i in range(n):
        x0, off, sp = r.uniform(60, W - 60), r.uniform(0, 1), r.uniform(380, 560)
        y = -100 + ((t - t0) * sp + off * (bottom + 100)) % (bottom + 100)
        x = x0 + math.sin(t * 2.2 + i) * 60
        spr(c, LEAVES[i % 3], x, y, 130 * size * r.uniform(0.75, 1.25), rot=math.sin(t * 3 + i) * 50, alpha=a,
            shadow=False, anchor="center")


# ------------------------------------------------------------- coupe du sol avec paillage
SOIL = 1060


@lru_cache(None)
def mulch_band(w_=W + 80, h_=170):
    """Bande de feuilles mortes (découpée dans la photo du tas) posée sur la terre, bord du haut irrégulier."""
    im = raw("tas_feuilles").crop((150, 560, 1110, 790)).resize((w_, h_), Image.LANCZOS)
    r = np.random.default_rng(4)
    m = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(m)
    pts = [(0, h_)]
    for x in range(0, w_ + 40, 40):
        pts.append((x, r.uniform(0, 34)))
    pts.append((w_, h_))
    d.polygon(pts, fill=255)
    a = np.minimum(np.asarray(m), np.asarray(im.getchannel("A")).clip(200, 255))
    im.putalpha(Image.fromarray(a.astype("uint8")).filter(ImageFilter.GaussianBlur(1.2)))
    return im


def mulch(c, spread=1.0, alpha=1.0, y=SOIL):
    """Paillage étalé depuis le centre (spread 0..1)."""
    if spread <= 0.01 or alpha <= 0.01:
        return
    b = mulch_band()
    half = int(b.width * spread / 2)
    part = b.crop((b.width // 2 - half, 0, b.width // 2 + half, b.height))
    if alpha < 1:
        part = part.copy()
        part.putalpha(part.getchannel("A").point(lambda v: int(v * alpha)))
    c.alpha_composite(part, (int(W / 2 - half), int(y - b.height + 40)))


def soil_scene(t, warm=0.0):
    return new_layers(background("none", SOIL, warm=warm))


def worm(c, x, y, k, t, rot=0.0, phase=0.0):
    """Ver de terre qui ondule (légère déformation verticale)."""
    im = raw("ver").crop(raw("ver").getbbox())
    w_, h_ = int(im.width * k), int(im.height * k)
    if w_ < 8 or h_ < 8:
        return
    im = im.resize((w_, h_), Image.BICUBIC)
    a = np.asarray(im)
    out = np.zeros_like(a)
    for xx in range(0, w_, 4):
        dy = int(math.sin(xx / max(1, w_) * 6.28 * 1.5 + t * 6 + phase) * 10 * k / 0.3)
        dy = max(-(h_ - 1), min(h_ - 1, dy))
        sl = a[:, xx:xx + 4]
        if dy >= 0:
            out[dy:, xx:xx + 4] = sl[:h_ - dy]
        else:
            out[:dy, xx:xx + 4] = sl[-dy:]
    put(c, Image.fromarray(out), x, y, 1.0, rot)


# ============================================================ A. BONNE NOUVELLE : PAILLAGE GRATUIT (2.75 → 6.45)
def s_free(t):
    w, u = new_layers(background("table"))
    leaves_falling(w, t, 2.75, 5.2, 12, 3, bottom=TABLE)
    grow = ease_out((t - 3.0) / 1.4)
    item(w, "tas_feuilles", PILE_BASE, 540, TABLE + 40, 0.82, max(0.02, grow), shadow=900)
    title(u, "BONNE NOUVELLE !", t, 3.3, 4.3, y=330, size=140)
    title(u, "PAILLAGE GRATUIT", t, 4.4, None, y=330, color=YEL, size=135)
    stamp(u, "0 € !", 820, 640, t, 5.58, None, GREEN, 120, 8)
    return w, u


cue(3.34, "pop_hi", 0.25)
cue(4.4, "rise", 0.22)
cue(5.6, "thud", 0.4)
cue(5.66, "success", 0.3)


# ============================================================ B. ÉTALÉES : PROTÈGENT DU FROID ET DE LA PLUIE (6.45 → 10.75)
def s_spread(t):
    w, u = soil_scene(t)
    spread = ease_io((t - 6.62) / 0.9)
    if t > 9.7:
        falling(w, t, 9.72, 10.2, "snow", 14, 5, 700, 50, bottom=SOIL - 120)
    if t > 10.1:
        falling(w, t, 10.12, None, "drop", 16, 6, 1200, 44, bottom=SOIL - 120)
    mulch(w, spread)
    if t > 9.0:
        put(u, icon("check", 140), 540, SOIL + 200, life(t, 10.3))
    put(u, icon("snow", 130), 170, 600, life(t, 9.78))
    put(u, icon("drop", 120), 910, 600, life(t, 10.3))
    title(u, "ÉTALE-LES SUR LE POTAGER", t, 6.62, 8.75, y=330, size=105)
    title(u, "ELLES PROTÈGENT LA TERRE", t, 8.82, None, y=330, color=YEL, size=100)
    return w, u


cue(6.7, "stir", 0.3)
cue(9.0, "pop", 0.22)
cue(9.8, "pop_hi", 0.2)
cue(10.15, "rain", 0.25)


# ============================================================ C. LES VERS DE TERRE SE RÉGALENT (10.75 → 13.95)
def s_worms(t):
    w, u = soil_scene(t)
    mulch(w, 1.0)
    # morceaux de feuilles tirés sous terre
    r = np.random.default_rng(8)
    for i in range(6):
        x = r.uniform(140, 940)
        tt = (t - 11.9 - i * 0.25) % 1.6
        if t > 11.9 + i * 0.25:
            spr(w, LEAVES[i % 3], x, SOIL + 10 + tt * 160, 60, rot=i * 40 + tt * 60, alpha=1 - tt / 1.6, shadow=False,
                anchor="center")
    for i, (x, y, k, rot, t0) in enumerate(((300, SOIL + 220, 0.32, -12, 11.95), (770, SOIL + 380, 0.26, 168, 12.2))):
        s = life(t, t0)
        if s > 0.01:
            worm(w, x + math.sin(t * 1.5 + i) * 30, y, k * s, t, rot, i * 2)
    if t > 13.3:
        sparkles(u, t, 13.35, 540, SOIL + 400, 380, 9, 4)
    title(u, "EN DESSOUS…", t, 10.85, 11.85, y=330, size=160)
    title(u, "LES VERS SE RÉGALENT", t, 11.92, None, y=330, color=YEL, size=115)
    stamp(u, "MIAM !", 820, 700, t, 13.34, None, GREEN, 110, 8)
    return w, u


cue(11.95, "squish", 0.3)
cue(13.36, "pop_hi", 0.28)


# ============================================================ D. AU PRINTEMPS : ENGRAIS, TERRE SOUPLE (13.95 → 17.95)
FORK = "compost/fourche"


def s_spring(t):
    warm = fade(t, 14.0, None, 0.6)
    w, u = soil_scene(t, warm)
    gone = ease_io((t - 14.8) / 0.9)
    mulch(w, 1.0, 1 - gone)
    if gone > 0.01:   # les feuilles sont devenues une couche d'humus sombre
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ov).rectangle([0, SOIL + 6, W, SOIL + 80], fill=(62, 42, 28, int(190 * gone)))
        w.alpha_composite(ov.filter(ImageFilter.GaussianBlur(6)))
    put(u, icon("sun", 170), 880, 560, life(t, 14.1), t * 25)
    if t > 15.92:
        dip = ease_out((t - 16.3) / 0.35)
        spr(w, FORK, 470, lerp(SOIL - 120, SOIL + 160, dip), 620, rot=-8, shadow=False)
        if t > 16.35:
            particles(w, t, 16.35, 470, SOIL, 12, 4, col=(80, 56, 38), size=10, up=260)
        put(u, icon("check", 150), 760, SOIL - 260, life(t, 16.9))
    title(u, "AU PRINTEMPS…", t, 14.1, 14.7, y=330)
    title(u, "DE L'ENGRAIS !", t, 14.78, 15.85, y=330, color=YEL, size=160)
    title(u, "TERRE TOUTE SOUPLE", t, 15.92, None, y=330, size=120)
    return w, u


cue(14.1, "sparkle", 0.25)
cue(14.8, "rise", 0.22)
cue(16.32, "crunch", 0.35)
cue(16.9, "ding", 0.25)


# ============================================================ E. PETIT CONSEIL : LA TONDEUSE (17.95 → 20.65)
MOWER_K = 0.62


def s_mower(t):
    w, u = new_layers(background("table"))
    X = 540
    pile_k = 0.78
    # la tondeuse passe de gauche à droite : derrière elle, le tas devient du broyat
    mx = lerp(-800, 1450, clamp((t - 19.1) / 1.45)) if t > 19.1 else -800
    front = mx + (MOWER_FRONT - MOWER_BASE[0]) * MOWER_K
    cut = int(clamp(front - 260, 0, W))
    pile = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    item(pile, "tas_feuilles", PILE_BASE, X, TABLE + 40, pile_k, life(t, 18.0), shadow=900)
    if cut > 0:
        pile.paste((0, 0, 0, 0), (0, 0, cut, H))
        chips = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        item(chips, "broyat", MULCH_BASE, X, TABLE + 40, pile_k * 0.95, shadow=900)
        chips.paste((0, 0, 0, 0), (cut, 0, W, H))
        w.alpha_composite(chips)
        if front < W + 200:
            particles(w, t, 19.3, min(W, front - 80), TABLE - 60, 14, int(t * 10) % 7, col=(150, 96, 50), size=10,
                      up=360, dur=0.5)
    w.alpha_composite(pile)
    if t > 19.1:
        item(w, "tondeuse", MOWER_BASE, mx, TABLE + 70, MOWER_K)
    if t < 19.1:
        put(u, icon("lightbulb", 170), 540, 560, life(t, 18.1), math.sin(t * 4) * 5)
    title(u, "PETIT CONSEIL", t, 18.1, 19.05, y=330)
    title(u, "LA TONDEUSE !", t, 19.14, None, y=330, color=YEL, size=160)
    return w, u


cue(18.1, "sparkle", 0.25)
cue(19.1, "mower", 0.4)


# ============================================================ F. BROYÉES : PAS DE CROÛTE, PLUS VITE (20.65 → 24.3)
def race_bar(c, x0, x1, y, p, col, label, s):
    if s <= 0.01:
        return
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([x0 - 6, y - 30, x1 + 6, y + 30], radius=30, fill=DARK)
    d.rounded_rectangle([x0, y - 22, x1, y + 22], radius=22, fill=CREAM)
    if p > 0.02:
        d.rounded_rectangle([x0, y - 22, x0 + (x1 - x0) * clamp(p), y + 22], radius=22, fill=col)
    put(c, text_img(label, F_BLACK, 34, DARK), x0 + 10 + text_img(label, F_BLACK, 34, DARK).width / 2, y - 62, s)


def s_compare(t):
    w, u = new_layers(background("table"))
    item(w, "tas_feuilles", PILE_BASE, 290, TABLE + 40, 0.42, life(t, 20.7), shadow=900)
    item(w, "broyat", MULCH_BASE, 790, TABLE + 40, 0.42, life(t, 20.82), shadow=900)
    if t > 21.58:
        tag(u, "CROÛTE", 300, TABLE - 420, t, 21.6, None, rot=-6, size=50, string_to=(290, TABLE - 250))
        put(u, icon("cross", 130), 290, 560, life(t, 21.62))
        put(u, icon("check", 130), 790, 560, life(t, 21.75))
    if t > 22.78:
        s = life(t, 22.78)
        race_bar(u, 100, 480, 1430, 0.3 * ease_io((t - 22.9) / 1.0), (196, 110, 50), "ENTIÈRES", s)
        race_bar(u, 600, 980, 1430, ease_io((t - 22.9) / 0.9), YEL, "BROYÉES", s)
    title(u, "PAS DE CROÛTE", t, 21.58, 22.7, y=330, size=150)
    title(u, "PLUS VITE !", t, 22.78, None, y=330, color=YEL, size=170)
    return w, u


cue(20.82, "pop", 0.25)
cue(21.62, "alert2", 0.3)
cue(22.9, "rise", 0.25)
cue(23.75, "ding", 0.25)


# ============================================================ G. CE WEEK-END : RÂTEAU ET BROUETTE (24.3 → 26.85)
def s_weekend(t):
    w, u = new_layers(background("table"))
    rk = ease_out((t - 25.7) / 0.35)
    if t > 25.7:
        item(w, "rateau", RAKE_BASE, 880, TABLE + 40, 0.72, 1.0, lerp(-40, 0, rk), shadow=0)
    if t > 26.18:
        roll = 1 - ease_out((t - 26.2) / 0.35)
        bx = 380 - 700 * roll
        k = 0.66
        item(w, "brouette", BARROW_BASE, bx, TABLE + 40, k, shadow=700)
        # tas de feuilles DANS le bac : posé sur la brouette, on efface ce qui passe sous le bord avant du bac
        P = lambda x, y: (bx + (x - BARROW_BASE[0]) * k, TABLE + 40 + (y - BARROW_BASE[1]) * k)
        pile = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cx, cy = P(545, 690)
        item(pile, "tas_feuilles", PILE_BASE, cx, cy, 0.5 * k)
        m = Image.new("L", (W, H), 255)
        ImageDraw.Draw(m).polygon([P(195, 652), P(885, 668), P(885, 1300), P(195, 1300)], fill=0)
        pile.putalpha(Image.composite(pile.getchannel("A"), Image.new("L", (W, H), 0), m))
        w.alpha_composite(pile)
    act = 0 if t < 25.1 else 1
    from gfx import pills
    pills(u, ["SAMEDI", "DIMANCHE"], act, t, 24.55, None, y=560, pw=280)
    title(u, "CE WEEK-END…", t, 24.5, 25.65, y=330, size=150)
    title(u, "RÂTEAU + BROUETTE", t, 25.74, None, y=330, color=YEL, size=120)
    return w, u


cue(24.55, "pop", 0.25)
cue(25.75, "whoosh_up", 0.22)
cue(26.25, "squeak", 0.25)


# ============================================================ H. CTA (26.85 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    item(w, "tas_feuilles", PILE_BASE, 250, TABLE + 40, 0.34, life(t, 26.9), shadow=900)
    worm(w, 830, TABLE - 40, 0.2 * life(t, 27.0) + 0.001, t, -10)
    clicked = t > 27.55
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 27.5) / 0.15))
    put(u, btn, 540, 300, life(t, 27.0) * press)
    if t > 27.2:
        k = ease_out((t - 27.2) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(330), 540, 590, life(t, 28.7, dur=0.45))
    sparkles(u, t, 28.8, 540, 590, 230, 10, 12)
    return w, u


cue(27.53, "click", 0.45)
cue(28.8, "sparkle", 0.25)


def s_cold_open(t):
    """Sans vidéo : feuilles qui tombent sur un tas (même décor que la suite)."""
    w, u = new_layers(background("table"))
    leaves_falling(w, t, 0.0, None, 16, 1, bottom=TABLE)
    title(u, "TEMPÊTE !", t, 0.3, None, y=330, size=170)
    return w, u


if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video)]
else:
    _intro = [(0.0, 2.75, s_cold_open)]

SCENES = _intro + [
    (2.75, 6.45, s_free),
    (6.45, 10.75, s_spread),
    (10.75, 13.95, s_worms),
    (13.95, 17.95, s_spring),
    (17.95, 20.65, s_mower),
    (20.65, 24.3, s_compare),
    (24.3, 26.85, s_weekend),
    (26.85, 99.0, s_cta),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []

if HAS_VIDEO:
    CUES[:] = [c for c in CUES if c[0] >= VID_END - 0.05]
