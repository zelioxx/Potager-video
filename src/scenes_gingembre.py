"""Storyboard « Faire repousser un morceau de gingembre » (voix : assets/audio/gingembre/voix.mp3).

Photos fournies (détourées, cadre 1254 d'origine conservé) : gingembre, gingembre avec ses yeux, gingembre germé,
plant de gingembre en pot, sac en papier kraft (le « panier »). Si assets/video/intro_gingembre.mp4 existe, la
première phrase montre cette vidéo brute (sans texte, son coupé) avant le motion design.
"""
import math
import os
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (ROOT, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, put, title, life, fade, ease_out,
                 ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse, particles, glass_back,
                 glass_front)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import place, logo_img
from scenes_ananas_v2 import trash_bin, BIN_H
from scenes_hortensia import stamp, gauge
from scenes_mangue import warm_glow

CUES = []
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


A = "gingembre/"
FULL = (0, 0, 1254, 1254)
VIDEO = os.path.join(ROOT, "assets", "video", "intro_gingembre.mp4")
HAS_VIDEO = os.path.exists(VIDEO)


def video_duration():
    if not HAS_VIDEO:
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                         capture_output=True, text=True).stdout
    return min(2.3, float(out.strip() or 0))


VID_END = video_duration()
NO_CAPTION_UNTIL = VID_END


@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_gingembre_intro")
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
GIN_BASE = (630, 925)        # bas du gingembre (mêmes repères sur les 3 photos)
GIN_TOP = 321                # haut du corps
EYES = [(325, 268), (540, 428), (100, 515), (92, 728), (712, 880), (1213, 608)]   # yeux de gingembre_yeux
POT_BASE = (600, 1228)       # bas du pot (plante_pot)
BAG_BASE = (628, 1208)       # bas du sac
BAG_TOP = 120                # bord du sac


def gin(c, X, Y, k, name="gingembre", s=1.0, rot=0.0, alpha=1.0, shadow=True):
    """Gingembre posé : le bas de son corps en (X, Y)."""
    if shadow and s > 0.01:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        w_ = 1000 * k * s
        ImageDraw.Draw(ov).ellipse([X - w_ / 2, Y - w_ * 0.05, X + w_ / 2, Y + w_ * 0.05],
                                   fill=(70, 45, 25, int(70 * alpha)))
        c.alpha_composite(ov)
    place(c, A + name, FULL, k, *GIN_BASE, X, Y, s, rot, 0.0, alpha)


def at(p, X, Y, k, origin=GIN_BASE):
    return X + (p[0] - origin[0]) * k, Y + (p[1] - origin[1]) * k


def plant(c, X, Y, k, s=1.0, alpha=1.0):
    place(c, A + "plante_pot", FULL, k, *POT_BASE, X, Y, s, 0.0, 0.0, alpha)


# ------------------------------------------------------------- pot en coupe
PX, PTOP, PW, PH = 540, 800, 820, 470
SURF = PTOP + 40          # surface du terreau dans le pot


@lru_cache(None)
def pot_cut_img():
    """Pot en terre cuite vu en coupe : parois, terreau grumeleux visible à l'intérieur."""
    k = 2
    w_, h_ = PW + 60, PH + 40
    im = Image.new("RGBA", (w_ * k, h_ * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = w_ / 2
    bw = PW * 0.74
    S = lambda pts: [(x * k, y * k) for x, y in pts]
    d.polygon(S([(cx - PW / 2, 30), (cx + PW / 2, 30), (cx + bw / 2, PH), (cx - bw / 2, PH)]), fill=(186, 100, 62))
    d.polygon(S([(cx + PW * 0.2, 30), (cx + PW / 2, 30), (cx + bw / 2, PH), (cx + bw * 0.22, PH)]), fill=(166, 88, 54))
    inset = 30
    inner = [(cx - PW / 2 + inset, 40), (cx + PW / 2 - inset, 40), (cx + bw / 2 - inset * 0.8, PH - 26),
             (cx - bw / 2 + inset * 0.8, PH - 26)]
    d.polygon(S(inner), fill=(84, 56, 36))
    r = np.random.default_rng(3)
    for _ in range(900):
        y = r.uniform(46, PH - 34)
        f = (y - 40) / (PH - 66)
        half = (PW / 2 - inset) * (1 - f) + (bw / 2 - inset * 0.8) * f
        x = cx + r.uniform(-half + 8, half - 8)
        rad = r.uniform(3, 8)
        g = int(r.uniform(-24, 30))
        d.ellipse([(x - rad) * k, (y - rad) * k, (x + rad) * k, (y + rad) * k],
                  fill=(84 + g, 56 + g // 2, 36 + g // 3))
    d.rounded_rectangle([(cx - PW / 2 - 22) * k, 4 * k, (cx + PW / 2 + 22) * k, 52 * k], radius=12 * k,
                        fill=(204, 114, 72))
    d.rectangle([(cx - PW / 2 + inset) * k, 40 * k, (cx + PW / 2 - inset) * k, 52 * k], fill=(84, 56, 36))
    return im.resize((w_, h_), Image.LANCZOS)


def pot_cut(c, s=1.0):
    if s <= 0.01:
        return
    im = pot_cut_img()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse([PX - PW * 0.42, PTOP + PH - 14, PX + PW * 0.42, PTOP + PH + 26], fill=(70, 45, 25, 80))
    c.alpha_composite(ov)
    put(c, im, PX, PTOP - 30 + im.height / 2 + (1 - s) * 300, s)


GK = 0.38                     # échelle du gingembre dans le pot
GIN_Y = SURF + 6 + (GIN_BASE[1] - 278) * GK     # yeux juste sous la surface


def gin_in_pot(c, t, name="gingembre_yeux", drop=1.0, alpha=1.0):
    """Le gingembre reste dans le terreau (coupé aux parois) ; seules les pousses dépassent de la surface."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gin(layer, PX, lerp(GIN_Y - 700, GIN_Y, drop), GK, name, rot=-25 * (1 - drop), shadow=False, alpha=alpha)
    if drop >= 1:
        bw = PW * 0.74
        top = PTOP + 22
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon([(PX - PW / 2 + 32, top), (PX + PW / 2 - 32, top), (PX + bw / 2 - 26, PTOP + PH - 56),
                                   (PX - bw / 2 + 26, PTOP + PH - 56)], fill=255)
        ImageDraw.Draw(m).rectangle([PX - PW / 2, 0, PX + PW / 2, top], fill=255)
        layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", (W, H), 0), m))
    c.alpha_composite(layer)


# ============================================================ A. AU FOND DE TON PANIER ? (0 → 2.3)
BAG_K, BAG_X = 0.75, 540
BAG_FRONT = [(360, 166), (600, 171), (895, 157)]     # bord supérieur du pan avant du sac
PEEK_K = 0.33


@lru_cache(None)
def bag_front():
    """Pan avant du sac seul (sous son bord supérieur) : redessiné devant le gingembre."""
    im = Image.open(os.path.join(ROOT, "assets", "images", A + "sac.png")).convert("RGBA")
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).polygon(BAG_FRONT + [(895, 1254), (360, 1254)], fill=255)
    im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", im.size, 0), m))
    return im


def bag_scene(c, t, gin_pose=None, s=1.0, dx=0.0, alpha=1.0):
    """Sac posé ; gin_pose = (x, y, rot) : gingembre DANS le sac (devant le fond, derrière le pan avant)."""
    if s <= 0.01:
        return
    place(c, A + "sac", FULL, BAG_K, *BAG_BASE, BAG_X + dx, TABLE + 40, s, 0.0, 0.0, alpha)
    if gin_pose:
        x, y, rot = gin_pose
        gin(c, x, y, PEEK_K, "gingembre", rot=rot, shadow=False)
        front = bag_front()
        sz = int(1254 * BAG_K * s)
        f = front.resize((sz, sz), Image.LANCZOS)
        put(c, f, BAG_X + dx + (627 - BAG_BASE[0]) * BAG_K * s, TABLE + 40 + (627 - BAG_BASE[1]) * BAG_K * s, 1.0)


def bag_rim_y():
    return TABLE + 40 + (166 - BAG_BASE[1]) * BAG_K


def peek_pose(t):
    """Le gingembre, presque debout dans le sac, pointe hors de l'ouverture."""
    p = ease_out((t - 0.85) / 0.45)
    wob = math.sin(t * 6) * 4 * p
    # gingembre tourné de 70° : son bas (repère GIN_BASE) est caché dans le sac
    return BAG_X + 10, bag_rim_y() + lerp(420, 170, p), -70 + wob


def s_intro(t):
    w, u = new_layers(background("table"))
    bag_scene(w, t, peek_pose(t) if t > 0.8 else None, life(t, 0.0, dur=0.4))
    put(u, icon("question", 130), 860, 600, life(t, 1.4), math.sin(t * 5) * 6)
    title(u, "AU FOND DU PANIER ?", t, 0.38, None, y=330, size=125)
    return w, u


cue(0.05, "pop_lo", 0.3)
cue(0.9, "rustle", 0.25)
cue(1.4, "pop_hi", 0.22)


# ============================================================ B. NE LE JETTE PAS, IL PEUT REPOUSSER (2.3 → 4.75)
def s_dont(t):
    w, u = new_layers(background("table"))
    if t > 3.3:
        plant(w, 540, TABLE + 30, 0.62, life(t, 3.4, dur=0.5), alpha=0.35 + 0.15 * math.sin(t * 4))
    # il saute hors du sac et atterrit à gauche ; le sac s'en va ensuite
    p = clamp((t - 2.4) / 0.55)
    x0, y0, r0 = peek_pose(2.4)
    # 1) il sort tout droit par l'ouverture (toujours derrière le pan avant), 2) il bascule et saute à gauche
    up = ease_out(clamp(p / 0.35))
    q = ease_io(clamp((p - 0.3) / 0.7))
    x = lerp(x0, 290, q)
    y = lerp(y0 - 70 * up, TABLE + 30, q) - math.sin(math.pi * q) * 80
    rot = lerp(r0, 0, q)
    k = lerp(PEEK_K, 0.4, q)
    bag_a = 1 - ease_io((t - 2.62) / 0.22)
    if q <= 0:
        bag_scene(w, t, (x, y, rot))
    else:
        bag_scene(w, t, None, 1.0, alpha=bag_a)
        gin(w, x, y, k, "gingembre", rot=rot, shadow=q >= 1)
    if 2.75 < t < 3.38:
        trash_bin(w, 820, TABLE + 10, BIN_H * 0.8, 0, life(t, 2.78, 3.35))
        put(u, icon("nosign", 330), 820, TABLE - 230, life(t, 2.95, 3.35))
    elif t >= 3.38:
        sparkles(u, t, 3.45, 540, 760, 360, 9, 4)
    title(u, "NE LE JETTE PAS !", t, 2.42, 3.32, y=330, color=RED, size=140)
    title(u, "IL PEUT REPOUSSER", t, 3.38, None, y=330, color=YEL, size=130)
    return w, u


cue(2.45, "whoosh_up", 0.22)
cue(2.9, "thud", 0.3)
cue(3.0, "alert2", 0.32)
cue(3.45, "sparkle", 0.3)


# ============================================================ C. ÉTAPE 1 : DODU, AVEC DES PETITS YEUX = BOURGEONS (4.75 → 10.2)
@lru_cache(None)
def shrivelled():
    """Morceau maigre et sec : même photo, aplatie, plus terne et plus sombre."""
    im = Image.open(os.path.join(ROOT, "assets", "images", A + "gingembre.png")).convert("RGBA")
    a = np.asarray(im).astype(float)
    g = a[..., :3].mean(2, keepdims=True)
    a[..., :3] = (a[..., :3] * 0.5 + g * np.array([0.95, 0.85, 0.7]) * 0.5) * 0.82
    im = Image.fromarray(np.clip(a, 0, 255).astype("uint8"))
    return im.resize((1254, 820), Image.LANCZOS)


def s_step1(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("1", 160), 190, 560, life(t, 4.94, 5.85))
    if t < 7.6:
        # dodu (gauche, validé) contre maigre et sec (droite, refusé)
        gin(w, 300, TABLE + 30, 0.4, s=life(t, 5.9))
        if t > 6.0:
            s = life(t, 6.05)
            im = shrivelled()
            sc = 0.3 * s
            put(w, im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS),
                810, TABLE + 30 - im.height * sc * 0.42, 1.0)
            put(u, icon("check", 130), 300, 640, life(t, 7.0))
            put(u, icon("cross", 130), 810, 640, life(t, 7.1))
            tag(u, "DODU !", 300, TABLE - 300, t, 7.18, None, rot=-5, size=60)
        title(u, "ÉTAPE 1", t, 4.94, 5.85, y=330)
        title(u, "UN MORCEAU BIEN DODU", t, 5.9, None, y=330, size=110)
    else:
        k = 0.74
        X, Y = 540, TABLE + 30
        name = "gingembre_yeux" if t > 7.66 else "gingembre"
        gin(w, X, Y, k, name, alpha=1.0)
        for i, e in enumerate(EYES):
            ex, ey = at(e, X, Y, k)
            hl_ellipse(u, ex, ey, 46, 46, life(t, 7.9 + i * 0.1))
        if t > 8.98:
            ex, ey = at(EYES[0], X, Y, k)
            tag(u, "BOURGEON", ex + 230, ey - 140, t, 9.05, None, rot=-5, size=52, string_to=(ex + 30, ey - 30))
            sparkles(u, t, 9.0, X, Y - 200, 420, 9, 6)
        title(u, "DES PETITS YEUX", t, 7.66, 8.92, y=330, size=140)
        title(u, "= SES BOURGEONS", t, 8.98, None, y=330, color=YEL, size=135)
    return w, u


cue(5.95, "pop", 0.25)
cue(7.05, "ding", 0.25)
cue(7.9, "pop_hi", 0.22)
cue(9.0, "sparkle", 0.3)


# ============================================================ D. ÉTAPE 2 : UNE NUIT DANS L'EAU TIÈDE (10.2 → 13.45)
BW, BH = 760, 380


def steam(c, t, x, y, a):
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(4):
        x0 = x - 210 + i * 140
        tt = (t * 0.8 + i * 0.27) % 1.0
        pts = [(x0 + 18 * math.sin(j * 0.6 + t * 4 + i), y - j * 18 - tt * 120) for j in range(12)]
        d.line(pts, fill=(255, 255, 255, int(170 * a * (1 - tt))), width=9, joint="curve")
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(2)))


def s_step2(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("2", 160), 190, 560, life(t, 10.45, 11.1))
    night = fade(t, 12.14, None, 0.4)
    if night > 0.01:
        ov = Image.new("RGBA", (W, H), (20, 26, 60, int(80 * night)))
        w.alpha_composite(ov)
    s = life(t, 10.3)
    glass_back(w, 540, TABLE + 20, BW, BH, s)
    drop = ease_out((t - 11.1) / 0.4)
    if t > 11.0:
        gin(w, 540, lerp(TABLE - 700, TABLE - 40, drop), 0.5, "gingembre_yeux", rot=-15 * (1 - drop), shadow=False)
    glass_front(w, 540, TABLE + 20, 0.82, t, BW, BH, s)
    if t > 11.45:
        particles(w, t, 11.5, 540, TABLE - BH + 60, 12, 5, col=(200, 230, 250), size=11, up=300)
    steam(u, t, 540, TABLE - BH - 10, fade(t, 12.6, None, 0.4))
    put(u, icon("thermo", 130), 900, 640, life(t, 12.62))
    tag(u, "1 NUIT", 200, 660, t, 12.14, None, rot=-5, size=64)
    title(u, "ÉTAPE 2", t, 10.45, 11.04, y=330)
    title(u, "UNE NUIT DANS L'EAU TIÈDE", t, 11.1, None, y=330, size=100)
    return w, u


cue(11.5, "splash", 0.35)
cue(12.14, "pop", 0.22)
cue(12.65, "rise", 0.2)


# ============================================================ E. ÉTAPE 3 : COUCHÉ DANS UN POT, YEUX EN HAUT (13.45 → 18.45)
def s_step3(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("3", 160), 190, 560, life(t, 13.6, 14.2))
    pot_cut(w, life(t, 13.5, dur=0.4))
    drop = ease_out((t - 14.3) / 0.5)
    if t > 14.2:
        gin_in_pot(w, t, drop=drop)
    if t > 14.8:
        particles(w, t, 14.8, PX, SURF, 12, 4, col=(90, 62, 40), size=9, up=260)
    if t > 15.5:
        for i, e in enumerate(EYES[:2] + EYES[5:]):
            ex, ey = at(e, PX, GIN_Y, GK)
            put(u, icon("arrow_down", 80), ex, ey - 90 - 10 * math.sin(t * 6 + i), life(t, 15.55 + i * 0.1), 180)
    if t > 16.54:
        d = ImageDraw.Draw(u)
        a = int(255 * fade(t, 16.6, None, 0.2))
        for i in range(0, 16, 2):
            x0 = PX - PW / 2 + 40 + i * 44
            d.line([(x0, SURF + 4), (x0 + 44, SURF + 4)], fill=(255, 255, 255, a), width=7)
        tag(u, "JUSTE SOUS LA SURFACE", 540, SURF - 200, t, 16.6, None, rot=-4, size=48, string_to=(540, SURF - 10))
    title(u, "ÉTAPE 3", t, 13.6, 14.2, y=330)
    title(u, "COUCHÉ DANS UN POT", t, 14.26, 15.45, y=330, size=125)
    title(u, "YEUX VERS LE HAUT", t, 15.5, None, y=330, color=YEL, size=125)
    return w, u


cue(13.55, "pop_lo", 0.3)
cue(14.8, "crunch", 0.35)
cue(15.6, "pop_hi", 0.22)
cue(16.62, "tick", 0.25)


# ============================================================ F. PETIT SECRET : CHALEUR, TERRE À PEINE HUMIDE (18.45 → 22.4)
def s_secret(t):
    w, u = new_layers(background("table"))
    warm_glow(w, fade(t, 19.9, None, 0.5))
    pot_cut(w)
    gin_in_pot(w, t)
    if t < 19.5:
        put(u, icon("lightbulb", 170), 540, 560, life(t, 18.6, 19.45), math.sin(t * 4) * 5)
    put(u, icon("thermo", 140), 180, 620, life(t, 19.95))
    if t > 21.0:
        for i in range(3):
            tt = t - 21.05 - i * 0.2
            if 0 < tt < 0.45:
                put(w, icon("drop", 46), PX - 120 + i * 120, lerp(PTOP - 380, SURF, (tt / 0.45) ** 2), 1)
        pos = lerp(0.12, 0.38, ease_out((t - 21.3) / 0.4))
        gauge(u, t, 21.05, pos, y=1405)
        put(u, icon("check", 130), 900, 620, life(t, 21.9))
    title(u, "PETIT SECRET", t, 18.6, 19.45, y=330)
    title(u, "DE LA CHALEUR", t, 19.54, 20.95, y=330, color=YEL, size=150)
    title(u, "À PEINE HUMIDE", t, 21.02, None, y=330, size=145)
    return w, u


cue(18.6, "sparkle", 0.25)
cue(19.95, "rise", 0.2)
cue(21.1, "plop", 0.25)
cue(21.9, "ding", 0.25)


# ============================================================ G. QUELQUES SEMAINES : UNE POUSSE VERTE (22.4 → 26.6)
def s_grow(t):
    w, u = new_layers(background("table"))
    if t < 25.5:
        warm_glow(w, 1.0)
        pot_cut(w)
        sprout = t > 24.14
        gin_in_pot(w, t, "gingembre_germe" if sprout else "gingembre_yeux")
        if 22.9 < t < 24.1:
            nt = 0.5 + 0.5 * math.sin((t - 22.9) * 9)
            ov = Image.new("RGBA", (W, H), (20, 26, 60, int(90 * nt * fade(t, 22.9, 24.0, 0.15, 0.15))))
            w.alpha_composite(ov)
            act = min(2, int((t - 22.94) / 0.3))
            pills(u, ["S1", "S2", "S3"], act, t, 22.9, 24.1, y=560, pw=170)
        if sprout:
            sparkles(u, t, 24.2, PX, SURF - 100, 380, 9, 7)
            tag(u, "POUSSE !", 860, SURF - 260, t, 24.3, None, rot=-5, size=58, string_to=(PX + 160, SURF - 90))
    else:
        plant(w, 540, TABLE + 30, 0.9, life(t, 25.5, dur=0.45))
        sparkles(u, t, 25.6, 540, 700, 380, 10, 8)
    title(u, "QUELQUES SEMAINES…", t, 22.54, 24.05, y=330, size=125)
    title(u, "UNE POUSSE VERTE !", t, 24.14, None, y=330, color=YEL, size=130)
    return w, u


for _k in range(3):
    cue(22.96 + _k * 0.3, "tick", 0.25)
cue(24.2, "pop_lo", 0.35)
cue(25.55, "success", 0.35)


# ============================================================ H. CTA (26.6 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    plant(w, 250, TABLE + 30, 0.5, life(t, 26.65))
    gin(w, 820, TABLE + 30, 0.3, "gingembre_yeux", life(t, 26.75))
    clicked = t > 27.3
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 27.25) / 0.15))
    put(u, btn, 540, 300, life(t, 26.75) * press)
    if t > 26.95:
        k = ease_out((t - 26.95) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(330), 540, 590, life(t, 28.3, dur=0.45))
    sparkles(u, t, 28.4, 540, 590, 230, 10, 12)
    return w, u


cue(27.28, "click", 0.45)
cue(28.4, "sparkle", 0.25)

if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video), (VID_END, 2.3, s_intro)]
else:
    _intro = [(0.0, 2.3, s_intro)]

SCENES = _intro + [
    (2.3, 4.75, s_dont),
    (4.75, 10.2, s_step1),
    (10.2, 13.45, s_step2),
    (13.45, 18.45, s_step3),
    (18.45, 22.4, s_secret),
    (22.4, 26.6, s_grow),
    (26.6, 99.0, s_cta),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = [(1, 4.94, 10.2), (2, 10.45, 13.45), (3, 13.6, 18.45)]

if HAS_VIDEO:
    CUES[:] = [c for c in CUES if c[0] >= VID_END - 0.05]
