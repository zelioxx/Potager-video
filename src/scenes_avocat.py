"""Storyboard « Faire germer un noyau d'avocat » (voix : assets/audio/avocat/voix.mp3).

Photos fournies (détourées, cadre 1024 d'origine conservé) : noyau, noyau avec 3 cure-dents, noyau fendu,
noyau avec racines et tige, plant d'avocatier en pot. Un cure-dent est extrait de la photo aux cure-dents pour
poser le noyau sur le verre. Si assets/video/intro_avocat.mp4 existe, la première phrase montre cette vidéo
brute (sans texte, son coupé) avant le motion design.
"""
import math
import os
import subprocess
from functools import lru_cache

from PIL import Image, ImageDraw

from gfx import (ROOT, IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, put, title, life, fade,
                 ease_out, ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse, particles,
                 text_img, aa, glass_back, glass_front, window_img, light_rays, F_TITLE)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import place, logo_img
from scenes_ananas_v2 import trash_bin, bin_rim_y, progress_bar, BIN_H
from scenes_hortensia import stamp

CUES = []
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


A = "avocat/"
FULL = (0, 0, 1024, 1024)
VIDEO = os.path.join(ROOT, "assets", "video", "intro_avocat.mp4")
HAS_VIDEO = os.path.exists(VIDEO)


def video_duration():
    if not HAS_VIDEO:
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                         capture_output=True, text=True).stdout
    return min(2.0, float(out.strip() or 0))


VID_END = video_duration()
NO_CAPTION_UNTIL = VID_END


@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_avocat_intro")
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
# centre du noyau (là où il est le plus large) et diamètre, par photo
PIT = {"noyau": (511, 550, 630), "noyau_fendu": (511, 550, 627), "noyau_curedents": (511, 550, 628),
       "noyau_racines": (512, 590, 498)}
# cure-dents de noyau_curedents.png : (entrée dans le noyau, pointe)
PICKS = [((310, 672), (125, 885)), ((515, 690), (515, 930)), ((705, 672), (905, 885))]
POT_BASE = (518, 975)


@lru_cache(None)
def raw(name):
    return Image.open(os.path.join(IMG, A + name + ".png")).convert("RGBA")


def pit(c, name, X, Y, D, s=1.0, rot=0.0, alpha=1.0):
    """Noyau dont le centre (le plus large) est en (X, Y), diamètre D à l'écran."""
    cx, cy, d = PIT[name]
    place(c, A + name, FULL, D / d, cx, cy, X, Y, s, rot, 0.0, alpha)


def shadow(c, X, Y, w_):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse([X - w_ / 2, Y - w_ * 0.08, X + w_ / 2, Y + w_ * 0.08], fill=(70, 45, 25, 70))
    c.alpha_composite(ov)


def pit_on_table(c, name, X, D, s=1.0, rot=0.0, lift=0.0):
    cx, cy, d = PIT[name]
    bottom = {"noyau": 825, "noyau_fendu": 832, "noyau_curedents": 830, "noyau_racines": 800}[name]
    if s > 0.01:
        shadow(c, X, TABLE + 20, D * 0.8 * s * (1 - clamp(lift / 600) * 0.5))
    pit(c, name, X, TABLE + 20 - (bottom - cy) * D / d * s - lift, D, s, rot)


def plant(c, X, Y, k, s=1.0, alpha=1.0):
    place(c, A + "pot", FULL, k, *POT_BASE, X, Y, s, 0.0, 0.0, alpha)


def pick(c, base, tip, k_len=1.0, alpha=1.0):
    """Cure-dent (photo) de `base` (côté noyau) jusqu'à `tip`."""
    im = raw("curedent_contour")
    L = math.hypot(tip[0] - base[0], tip[1] - base[1])
    ang = -math.degrees(math.atan2(tip[1] - base[1], tip[0] - base[0]))
    put(c, im, (base[0] + tip[0]) / 2, (base[1] + tip[1]) / 2, L / im.width * k_len, ang, alpha)


def at(p, name, X, Y, D):
    cx, cy, d = PIT[name]
    return X + (p[0] - cx) * D / d, Y + (p[1] - cy) * D / d


# ------------------------------------------------------------- verre d'eau
GX, GW, GH = 540, 430, 520
D_GLASS = 360
RIM = TABLE - GH


def glass_pit(c, t, name="noyau", lvl=0.97, murky=0.0, drop=1.0, s=1.0, shake=0.0):
    """Noyau posé sur le verre par 2 cure-dents horizontaux qui reposent sur le bord : moitié dans l'eau."""
    glass_back(c, GX, TABLE, GW, GH, s)
    Y = lerp(RIM - 700, RIM + 4, drop)
    X = GX + shake
    r = D_GLASS / 2
    L = raw("curedent").width * D_GLASS / 630 * 1.35
    for side in (-1, 1):
        pick(c, (X + side * (r - 14), Y - 6), (X + side * (r - 14 + L), Y - 2))
    pit(c, name, X, Y, D_GLASS, s)
    glass_front(c, GX, TABLE, lvl, t, GW, GH, s, murky)
    return X, Y


# ============================================================ A. TU JETTES TON NOYAU ? (0 → 2.0)
BX = 790


def throw_path(t):
    sx, sy = 280, TABLE + 20 - (825 - 550) * 300 / 630
    ex, ey = BX, bin_rim_y() + 60
    if t < 0.5:
        return sx, sy, 0.0
    if t < 0.98:
        p = ease_io((t - 0.5) / 0.48)
        return lerp(sx, ex, p), lerp(sy, ey - 60, p) - math.sin(math.pi * p) * 380, -360 * p
    if t < 2.2:
        p = ease_out((t - 0.98) / 0.15)
        return ex, lerp(ey - 60, ey, p), 0.0
    p = ease_io((t - 2.2) / 0.5)
    return lerp(ex, 540, p), lerp(ey, TABLE + 20 - (825 - 550) * 420 / 630, p) - math.sin(math.pi * p) * 320, 360 * p


def s_intro(t):
    w, u = new_layers(background("table"))
    lid = 68 * ease_out((t - 0.3) / 0.22)
    shake = math.sin(t * 55) * 9 * fade(t, 1.0, 1.35) if t > 1.0 else 0.0
    x, y, rot = throw_path(t)
    D = 300 if t < 2.2 else lerp(300, 420, ease_io((t - 2.2) / 0.5))
    draw = lambda c: pit(c, "noyau", x, y, D, life(t, 0.0, dur=0.35), rot)
    inside = 0.98 <= t < 2.2
    if t < 0.5:
        shadow(w, 280, TABLE + 20, 240 * life(t, 0.0, dur=0.35))
    trash_bin(w, BX + shake, TABLE + 10, BIN_H, lid, life(t, 0.1, 2.75, dur=0.35), draw if inside else None)
    if not inside:
        draw(w)
    if t > 1.0:
        particles(w, t, 1.0, BX, bin_rim_y() - 10, 10, 9, col=(120, 100, 70), size=9, up=260)
    title(u, "TU LE JETTES ?", t, 0.42, 1.95, y=330, size=150)
    if 2.06 <= t < 2.3:
        put(u, icon("cross", 260), BX, TABLE - 260, life(t, 2.06))
    stamp(u, "DOMMAGE !", 540, 360, t, 2.06, 2.75)
    return w, u


cue(0.05, "pop_lo", 0.3)
cue(0.5, "whoosh", 0.3)
cue(0.98, "thud", 0.45)
cue(2.06, "alert3", 0.4)


# ============================================================ B. UN ARBRE QUI DORT (2.0 → 4.55)
@lru_cache(None)
def dream_bubble():
    w_, h_ = 400, 420
    im = aa(w_, h_, lambda d, k, _: (
        d.ellipse([0, 0, w_ * k - 1, h_ * k - 1], fill=WHITE + (235,), outline=DARK, width=int(9 * k)),))
    return im


def s_sleep(t):
    w, u = new_layers(background("table"))
    pit_on_table(w, "noyau", 540, 420, 1.0, 0.0)
    if t > 2.82:
        bx, by = 760, 640
        for i, (dx, dy, r) in enumerate(((-210, 330, 22), (-150, 250, 34))):
            sc = life(t, 2.85 + i * 0.08)
            if sc > 0.01:
                d = ImageDraw.Draw(u)
                d.ellipse([bx + dx - r * sc, by + dy - r * sc, bx + dx + r * sc, by + dy + r * sc], fill=WHITE,
                          outline=DARK, width=7)
        put(u, dream_bubble(), bx, by, life(t, 3.0))
        plant(u, bx, by + 175, 0.36, life(t, 3.18))
    for i in range(3):
        tt = (t - 2.9 - i * 0.35) % 1.05
        if t > 2.9 + i * 0.35:
            put(u, text_img("Z", F_TITLE, 80 + i * 22, CREAM, 8, DARK, 6, DARK), 380 - tt * 120 - i * 50,
                TABLE - 360 - tt * 240 - i * 60, 1.0, 12, 1 - tt)
    title(u, "UN ARBRE QUI DORT", t, 2.82, None, y=330, size=125)
    return w, u


cue(3.05, "sparkle", 0.25)


# ============================================================ C. ÉTAPE 1 : LAVE-LE, 3 CURE-DENTS (4.55 → 7.1)
D1 = 460


def s_step1(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("1", 160), 190, 560, life(t, 4.6, 5.4))
    X = 540
    cx, cy, d = PIT["noyau"]
    Y = TABLE + 20 - (825 - cy) * D1 / d
    shadow(w, X, TABLE + 20, D1 * 0.8)
    swap = t > 6.5
    if not swap:
        # cure-dents glissés sous le noyau : on ne voit que la partie qui dépasse
        for i, (base, tip) in enumerate(PICKS):
            t0 = 5.94 + i * 0.18
            if t < t0:
                continue
            p = ease_out((t - t0) / 0.2)
            b, tp = at(base, "noyau", X, Y, D1), at(tip, "noyau", X, Y, D1)
            ox, oy = (tp[0] - b[0]) * 0.8 * (1 - p), (tp[1] - b[1]) * 0.8 * (1 - p)
            pick(w, (b[0] + ox, b[1] + oy), (tp[0] + ox, tp[1] + oy))
            put(u, num_badge(str(i + 1), 90, YEL), tp[0], tp[1] + 60, life(t, t0 + 0.05, 6.9))
        pit(w, "noyau", X, Y, D1)
    else:
        pit(w, "noyau_curedents", X, Y, D1)
        for i, (base, tip) in enumerate(PICKS):
            tp = at(tip, "noyau", X, Y, D1)
            put(u, num_badge(str(i + 1), 90, YEL), tp[0], tp[1] + 60, life(t, 0.0, 6.9))
    if t < 5.5:
        # lavage : gouttes + bulles
        for i in range(7):
            tt = (t - 4.66 - i * 0.09) % 0.6
            if t > 4.66 + i * 0.09:
                put(w, icon("drop", 46), X - 180 + i * 60, lerp(Y - 420, Y - 120, tt / 0.6), 1, 0, 1 - tt / 0.6)
        d = ImageDraw.Draw(u)
        for i in range(9):
            a = i * 0.7 + t * 1.5
            r = 18 + (i % 3) * 10
            bx, by = X + math.cos(a) * 260, Y + math.sin(a * 1.3) * 200
            al = int(220 * fade(t, 4.75, 5.45, 0.2, 0.2))
            if al > 0:
                d.ellipse([bx - r, by - r, bx + r, by + r], outline=(255, 255, 255, al), width=5)
        sparkles(u, t, 5.1, X, Y - 80, 260, 7, 3)
    title(u, "LAVE-LE", t, 4.66, 5.5, y=330, size=170)
    title(u, "3 CURE-DENTS", t, 5.58, None, y=330, color=YEL, size=150)
    return w, u


cue(4.7, "splash", 0.3)
for _i in range(3):
    cue(5.94 + _i * 0.18, "click", 0.3)


# ============================================================ D. ÉTAPE 2 : SUR UN VERRE, PLAT EN BAS, À MOITIÉ (7.1 → 11.1)
def s_step2(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("2", 160), 190, 560, life(t, 7.15, 8.0))
    drop = ease_out((t - 7.3) / 0.45)
    lvl = lerp(0.62, 0.97, ease_io((t - 9.9) / 0.7))
    X, Y = glass_pit(w, t, "noyau", lvl, drop=drop, s=life(t, 7.12))
    if t > 7.6:
        particles(w, t, 7.72, GX, RIM, 10, 5, col=(200, 230, 250), size=10, up=260)
    if 8.5 < t < 9.85:
        tag(u, "POINTE EN HAUT", 830, Y - 300, t, 8.62, None, rot=-5, size=40, string_to=(X + 40, Y - 160))
        tag(u, "PLAT EN BAS", 830, Y + 320, t, 8.9, None, rot=4, size=40, string_to=(X + 60, Y + 170))
        put(u, icon("arrow_down", 110), X - 250, Y + 130, life(t, 8.9), 0)
    if t > 9.86:
        d = ImageDraw.Draw(u)
        a = int(255 * fade(t, 10.3, None, 0.2))
        for i in range(0, 14, 2):
            x0 = X - 330 + i * 48
            d.line([(x0, Y), (x0 + 48, Y)], fill=(255, 255, 255, a), width=8)
        tag(u, "50 %", X + 300, Y + 110, t, 10.35, None, rot=-4, size=54)
    title(u, "SUR UN VERRE D'EAU", t, 7.18, 8.45, y=330, size=125)
    title(u, "CÔTÉ PLAT EN BAS", t, 8.5, 9.8, y=330, color=YEL, size=130)
    title(u, "À MOITIÉ DANS L'EAU", t, 9.86, None, y=330, size=118)
    return w, u


cue(7.72, "plop", 0.4)
cue(8.75, "pop", 0.22)
cue(9.95, "pour", 0.3)


# ============================================================ E. AU CHAUD, LUMIÈRE, CHANGE L'EAU (11.1 → 14.0)
def s_care(t):
    w, u = new_layers(background("table"))
    put(w, window_img(), 540, 700, life(t, 11.15))
    light_rays(w, 330, 330, t, fade(t, 12.06, None, 0.4))
    # change l'eau : trouble → se vide → se remplit clair
    lvl, murky = 0.97, 0.0
    if t > 12.78:
        murky = clamp((t - 12.78) / 0.25) * (1 - clamp((t - 13.2) / 0.05))
        lvl = 0.97 - 0.9 * ease_io((t - 12.95) / 0.25) + 0.9 * ease_io((t - 13.22) / 0.35)
    glass_pit(w, t, "noyau", lvl, murky)
    put(u, icon("thermo", 140), 170, 620, life(t, 11.46))
    put(u, icon("sun", 160), 910, 620, life(t, 12.06), t * 25)
    if t > 13.42:
        act = min(3, int((t - 13.42) / 0.14))
        pills(u, ["S1", "S2", "S3", "S4"], act, t, 13.36, None, y=1430, pw=170)
    title(u, "AU CHAUD", t, 11.22, 12.0, y=330, size=170)
    title(u, "À LA LUMIÈRE", t, 12.06, 12.7, y=330, color=YEL, size=150)
    title(u, "CHANGE L'EAU", t, 12.78, None, y=330, size=150)
    return w, u


cue(11.46, "pop", 0.22)
cue(12.06, "sparkle", 0.22)
cue(12.95, "pour", 0.28)


# ============================================================ F. ET MAINTENANT, PATIENCE (14.0 → 16.6)
def s_wait(t):
    w, u = new_layers(background("table"))
    put(w, window_img(), 540, 700)
    glass_pit(w, t, "noyau", 0.97)
    # jours et nuits qui défilent
    if t > 14.4:
        night = 0.5 + 0.5 * math.sin((t - 14.4) * 9)
        ov = Image.new("RGBA", (W, H), (20, 26, 60, int(110 * night * fade(t, 14.4, 16.4, 0.2, 0.2))))
        w.alpha_composite(ov)
    p = ease_io((t - 14.3) / 2.2)
    progress_bar(u, 200, 880, 1395, p, ["S1", "S3", "S6"], t, 14.2)
    title(u, "ET MAINTENANT…", t, 14.07, 15.35, y=330, size=140)
    title(u, "PATIENCE…", t, 15.45, None, y=330, color=YEL, size=170)
    return w, u


cue(15.45, "bell", 0.25)


# ============================================================ G. IL SE FEND, UNE RACINE, PUIS UNE TIGE (16.6 → 20.95)
def s_sprout(t):
    w, u = new_layers(background("table"))
    put(w, window_img(), 540, 700)
    name = "noyau" if t < 18.78 else ("noyau_fendu" if t < 19.98 else "noyau_racines")
    shake = math.sin(t * 60) * 8 * fade(t, 18.78, 19.1, 0.02, 0.2) if 18.78 < t < 19.1 else 0.0
    X, Y = glass_pit(w, t, name, 0.97, shake=shake)
    if t > 18.78:
        sparkles(w, t, 18.8, X, Y - 120, 200, 7, 4, 0.6)
    if 19.26 < t < 19.98:
        rt = at((530, 815), "noyau_fendu", X, Y, D_GLASS)
        hl_ellipse(u, rt[0], rt[1], 60, 70, life(t, 19.3))
        tag(u, "RACINE", 850, rt[1] + 80, t, 19.3, None, rot=4, size=46, string_to=(rt[0] + 50, rt[1]))
    if t > 19.98:
        st = at((512, 200), "noyau_racines", X, Y, D_GLASS)
        rt = at((500, 900), "noyau_racines", X, Y, D_GLASS)
        tag(u, "TIGE", 850, st[1], t, 20.1, None, rot=-4, size=50, string_to=(st[0] + 60, st[1]))
        tag(u, "RACINES", 860, rt[1] + 40, t, 20.3, None, rot=4, size=44, string_to=(rt[0] + 70, rt[1]))
        sparkles(u, t, 20.0, X, Y - 200, 300, 9, 7)
    title(u, "QUELQUES SEMAINES +TARD", t, 16.78, 18.7, y=330, size=105)
    title(u, "IL SE FEND !", t, 18.78, 19.2, y=330, size=150)
    title(u, "UNE RACINE", t, 19.26, 19.92, y=330, color=YEL, size=150)
    title(u, "PUIS UNE TIGE !", t, 19.98, None, y=330, color=YEL, size=145)
    return w, u


cue(18.78, "crunch", 0.45)
cue(19.3, "pop_hi", 0.22)
cue(20.05, "success", 0.35)


# ============================================================ H. CTA (20.95 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    plant(w, 260, TABLE + 30, 0.58, life(t, 21.0))
    pit_on_table(w, "noyau_curedents", 830, 230, life(t, 21.1))
    clicked = t > 21.65
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 21.6) / 0.15))
    put(u, btn, 540, 300, life(t, 21.05) * press)
    if t > 21.3:
        k = ease_out((t - 21.3) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(330), 540, 590, life(t, 22.5, dur=0.45))
    sparkles(u, t, 22.6, 540, 590, 230, 10, 12)
    return w, u


cue(21.63, "click", 0.45)
cue(22.6, "sparkle", 0.25)

if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video), (VID_END, 2.75, s_intro)]
else:
    _intro = [(0.0, 2.75, s_intro)]

SCENES = _intro + [
    (2.75, 4.55, s_sleep),
    (4.55, 7.1, s_step1),
    (7.1, 11.1, s_step2),
    (11.1, 14.0, s_care),
    (14.0, 16.6, s_wait),
    (16.6, 20.95, s_sprout),
    (20.95, 99.0, s_cta),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = [(1, 4.6, 7.1), (2, 7.15, 11.1), (3, 11.15, 16.6)]

if HAS_VIDEO:
    CUES[:] = [c for c in CUES if c[0] >= VID_END - 0.05]
