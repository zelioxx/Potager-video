"""Storyboard « Faire germer un noyau de mangue » (voix : assets/audio/mangue/voix.mp3).

Photos fournies (détourées, cadre 1024 d'origine conservé) : noyau fibreux, noyau dans la main, graine,
graine germée, manguier en pot. Le noyau et la graine sont remis à l'horizontale (*_h.png) pour l'ouverture
« par le côté ». Si assets/video/intro_mangue.mp4 existe, la première phrase montre cette vidéo brute
(sans texte, son coupé) avant le motion design.
"""
import math
import os
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (ROOT, IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, spr, put, title, life, fade,
                 ease_out, ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse, particles,
                 text_img, F_TITLE)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import place, logo_img
from scenes_ananas_v2 import trash_bin, BIN_H
from scenes_aromatiques import pot
from scenes_hortensia import stamp, scissors, dashed

CUES = []
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


A = "mangue/"
FULL = (0, 0, 1024, 1024)
VIDEO = os.path.join(ROOT, "assets", "video", "intro_mangue.mp4")
HAS_VIDEO = os.path.exists(VIDEO)


def video_duration():
    if not HAS_VIDEO:
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                         capture_output=True, text=True).stdout
    return min(2.45, float(out.strip() or 0))


VID_END = video_duration()
NO_CAPTION_UNTIL = VID_END


@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_mangue_intro")
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
PIT_C, PIT_RX, PIT_BOT = (495, 522), 380, 762      # noyau_h : centre, demi-longueur, bas
SEED_C, SEED_RX, SEED_BOT = (539, 499), 438, 777   # graine_h / graine_germee_h
SPROUT = (370, 760)                                # départ de la racine sur graine_germee_h
HAND_PIT = (500, 540)                              # noyau dans noyau_main
TREE_BASE = (512, 980)                             # bas du pot du manguier


@lru_cache(None)
def raw(name):
    return Image.open(os.path.join(IMG, A + name + ".png")).convert("RGBA")


@lru_cache(None)
def scraped_base():
    """noyau_h sans pulpe : chaque tache orange est remplie avec la texture fibreuse voisine (copie décalée)."""
    a = np.asarray(raw("noyau_h")).astype(float)
    rgb = a[..., :3]
    mx, mn = rgb.max(2), rgb.min(2)
    sat = (mx - mn) / np.maximum(mx, 1)
    from scipy import ndimage
    pulp = ndimage.binary_dilation(sat > 0.6, iterations=3) & (a[..., 3] > 0)
    out = rgb.copy()
    todo = pulp.copy()
    for dx, dy in ((46, 0), (-46, 0), (0, 40), (0, -40), (70, 34), (-70, -34), (90, -50), (-90, 50), (130, 0), (-130, 0)):
        src = np.roll(np.roll(rgb, dy, 0), dx, 1)
        ok = np.roll(np.roll(~pulp & (a[..., 3] > 200), dy, 0), dx, 1)
        take = todo & ok
        out[take] = src[take]
        todo &= ~take
    soft = ndimage.gaussian_filter(pulp.astype(float), 1.5)[..., None]
    rgb = rgb * (1 - soft) + out * soft
    return a, rgb


@lru_cache(64)
def pit_img(scrape_q, dry_q):
    """noyau_h : la pulpe orange est grattée (scrape), puis le noyau sèche (fibres plus pâles et ternes)."""
    a, clean = scraped_base()
    a = a.copy()
    k = scrape_q / 10
    rgb = a[..., :3] * (1 - k) + clean * k
    if dry_q:
        kd = dry_q / 10
        g = rgb.mean(2, keepdims=True)
        rgb = rgb * (1 - 0.3 * kd) + (g + np.array([8, 0, -14.0])) * 0.3 * kd
        rgb *= 1 - 0.06 * kd
    a[..., :3] = rgb
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


def pit(c, X, Y, k, scrape=0.0, dry=0.0, s=1.0, rot=0.0, img=None):
    """Noyau posé : le bas de son corps en (X, Y)."""
    if s <= 0.01:
        return
    im = img or pit_img(int(round(scrape * 10)), int(round(dry * 10)))
    sz = int(1024 * k * s)
    r = im.resize((sz, sz), Image.BICUBIC)
    if abs(rot) > 0.1:
        r = r.rotate(rot, resample=Image.BICUBIC)
    put(c, r, X + (512 - PIT_C[0]) * k * s, Y + (512 - PIT_BOT) * k * s, 1.0)


def seed(c, X, Y, k, s=1.0, rot=0.0, sprout=False, alpha=1.0):
    """Graine posée : le bas de son corps en (X, Y)."""
    place(c, A + ("graine_germee_h" if sprout else "graine_h"), FULL, k, SEED_C[0], SEED_BOT, X, Y, s, rot, 0.0,
          alpha)


def shadow(c, X, Y, w_, a=70):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse([X - w_ / 2, Y - w_ * 0.07, X + w_ / 2, Y + w_ * 0.07], fill=(70, 45, 25, a))
    c.alpha_composite(ov)


def tree(c, X, Y, k, s=1.0):
    if s > 0.01:
        shadow(c, X, Y, 300 * k * s)
    place(c, A + "manguier", FULL, k, *TREE_BASE, X, Y, s)


# ------------------------------------------------------------- essuie-tout et boîte
@lru_cache(8)
def towel_tex(w_, h_, wet_q):
    im = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    base = (lerp(250, 222, wet_q / 10), lerp(250, 232, wet_q / 10), lerp(246, 240, wet_q / 10))
    base = tuple(int(v) for v in base)
    d.rounded_rectangle([0, 0, w_ - 1, h_ - 1], radius=26, fill=base + (255,), outline=(200, 196, 186, 255), width=4)
    for y in range(22, h_ - 10, 34):
        for x in range(22 + (y // 34 % 2) * 17, w_ - 10, 34):
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(226, 222, 212, 255))
    if wet_q:
        r = np.random.default_rng(3)
        for _ in range(wet_q):
            x, y, rr = r.uniform(40, w_ - 40), r.uniform(40, h_ - 40), r.uniform(20, 38)
            d.ellipse([x - rr, y - rr * 0.7, x + rr, y + rr * 0.7], fill=(205, 220, 232, 90))
    return im


def towel(c, cx, cy, w_, h_, cover, wet=0.0):
    """Feuille d'essuie-tout qui recouvre de gauche à droite (cover = 0..1)."""
    if cover <= 0.01:
        return
    im = towel_tex(int(w_), int(h_), int(round(wet * 10)))
    cw = max(1, int(im.width * cover))
    part = im.crop((0, 0, cw, im.height))
    sh = Image.new("RGBA", (cw + 20, im.height + 20), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([10, 14, cw + 8, im.height + 16], radius=26, fill=(60, 40, 20, 60))
    x0, y0 = int(cx - w_ / 2), int(cy - h_ / 2)
    c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), (x0 - 10, y0 - 10))
    c.alpha_composite(part, (x0, y0))
    if cover < 0.98:   # bord roulé
        d = ImageDraw.Draw(c)
        d.rounded_rectangle([x0 + cw - 18, y0 - 6, x0 + cw + 18, y0 + h_ + 6], radius=18, fill=(238, 236, 228),
                            outline=(190, 186, 176), width=4)


BOX_W, BOX_H = 760, 420


def box_back(c, cx, base, s=1.0):
    if s <= 0.01:
        return
    w_, h_ = BOX_W * s, BOX_H * s
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle([cx - w_ / 2, base - h_, cx + w_ / 2, base], radius=40 * s,
                                         fill=(235, 245, 250, 70))
    c.alpha_composite(ov)


def box_front(c, cx, base, lid=1.0, s=1.0, lid_lift=0.0):
    """Boîte en plastique transparent ; lid = 0..1 (le couvercle descend), lid_lift = soulevé (ouverture)."""
    if s <= 0.01:
        return
    w_, h_ = BOX_W * s, BOX_H * s
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([cx - w_ / 2, base - h_, cx + w_ / 2, base], radius=40 * s, fill=(225, 240, 248, 60),
                        outline=(255, 255, 255, 230), width=int(7 * s))
    d.line([(cx - w_ / 2 + 40, base - h_ + 40), (cx - w_ / 2 + 40, base - 60)], fill=(255, 255, 255, 120), width=14)
    if lid > 0.01:
        ly = lerp(base - h_ - 500, base - h_ - 18, ease_out(lid)) - lid_lift
        d.rounded_rectangle([cx - w_ / 2 - 16, ly, cx + w_ / 2 + 16, ly + 46 * s], radius=20 * s,
                            fill=(120, 190, 120, 235), outline=DARK, width=int(6 * s))
        d.rounded_rectangle([cx - 80, ly - 12, cx + 80, ly + 6], radius=8, fill=(90, 160, 95, 235))
    c.alpha_composite(ov)


def warm_glow(c, a):
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W // 4, H // 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(8):
        r = 260 - i * 28
        d.ellipse([135 - r, 270 - r * 0.8, 135 + r, 270 + r * 0.8], fill=(255, 160, 60, int(14 * a)))
    c.alpha_composite(ov.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(8)))


# ============================================================ A. TU JETTES TON NOYAU ? (0 → 2.45)
HAND_K = 0.86
HAND_X, HAND_Y = 420, 880       # position du noyau tenu


def hand(c, t, t0=0.0):
    slide = 1 - ease_out((t - t0) / 0.4)
    place(c, A + "noyau_main", FULL, HAND_K, *HAND_PIT, HAND_X - 600 * slide, HAND_Y)


def s_intro(t):
    w, u = new_layers(background("table"))
    trash_bin(w, 880, TABLE + 10, BIN_H * 0.82, 68 * ease_out((t - 0.9) / 0.22), life(t, 0.2, dur=0.35))
    hand(w, t)
    if t > 1.0:   # trajectoire pointillée noyau → poubelle
        d = ImageDraw.Draw(u)
        for i in range(12):
            q = i / 11
            if q > clamp((t - 1.0) / 0.5):
                break
            px, py = lerp(HAND_X + 120, 860, q), lerp(HAND_Y - 180, TABLE - 480, q) - math.sin(math.pi * q) * 260
            d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=YEL + (235,))
    title(u, "TU LE JETTES ?", t, 0.46, None, y=330, size=150)
    return w, u


cue(0.05, "pop_lo", 0.3)
cue(0.9, "click", 0.35)


# ============================================================ B. ATTENTION : UNE GRAINE CACHÉE (2.45 → 4.85)
LENS_R = 230


def s_hidden(t):
    w, u = new_layers(background("table"))
    place(w, A + "noyau_main", FULL, HAND_K, *HAND_PIT, HAND_X, HAND_Y)
    lx, ly = HAND_X + 20, HAND_Y - 20
    g = life(t, 3.1, dur=0.4)
    if g > 0.01:
        r = LENS_R * g
        lens = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lens)
        dl.ellipse([lx - r, ly - r, lx + r, ly + r], fill=(246, 236, 210, 255))
        seed(lens, lx, ly + 130, 0.4 * g + 0.001, rot=-8)
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).ellipse([lx - r, ly - r, lx + r, ly + r], fill=255)
        lens.putalpha(Image.composite(lens.getchannel("A"), Image.new("L", (W, H), 0), m))
        w.alpha_composite(lens)
        d = ImageDraw.Draw(u)
        hx, hy = lx + r * 0.72, ly + r * 0.72
        d.line([(hx, hy), (hx + 150 * g, hy + 150 * g)], fill=DARK, width=int(46 * g))
        d.line([(hx + 10, hy + 10), (hx + 140 * g, hy + 140 * g)], fill=(150, 90, 50), width=int(30 * g))
        d.ellipse([lx - r - 14, ly - r - 14, lx + r + 14, ly + r + 14], outline=DARK, width=int(30 * g))
        d.ellipse([lx - r - 6, ly - r - 6, lx + r + 6, ly + r + 6], outline=(190, 196, 200), width=int(12 * g))
        sparkles(u, t, 3.7, lx, ly, 260, 8, 5)
    stamp(u, "ATTENTION !", 540, 360, t, 2.57, 3.25, RED, 130, -8)
    title(u, "UNE GRAINE CACHÉE !", t, 3.34, None, y=330, color=YEL, size=120)
    return w, u


cue(2.57, "alert1", 0.4)
cue(3.1, "pop_hi", 0.25)
cue(3.7, "sparkle", 0.3)


# ============================================================ C. ÉTAPE 1 : GRATTE LA CHAIR, SÈCHE UNE JOURNÉE (4.85 → 9.0)
K1 = 0.95


def s_step1(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("1", 160), 190, 560, life(t, 4.94, 5.85))
    scrape = ease_io((t - 6.0) / 1.0)
    dry = ease_io((t - 7.6) / 1.2)
    X, Y = 540, TABLE + 20
    shadow(w, X, Y, 640)
    pit(w, X, Y, K1, scrape, dry, life(t, 4.9))
    top = Y - (PIT_BOT - (PIT_C[1] - 240)) * K1
    if 5.9 < t < 7.1:
        sweep = math.sin((t - 5.9) * 7)
        kx = X + 40 + sweep * 220
        spr(w, "poireau/knife", kx, top + 40, 110, shadow=False, rot=-6 + sweep * 3, anchor="center")
        particles(w, t, 6.0, kx - 200, top + 60, 10, 3, col=(245, 175, 30), size=11, up=200)
        particles(w, t, 6.55, kx - 200, top + 60, 10, 4, col=(245, 175, 30), size=11, up=200)
    if t > 7.06:
        p = clamp((t - 7.2) / 1.6)
        sx, sy = lerp(160, 920, p), 600 - math.sin(math.pi * p) * 140
        put(u, icon("sun", 150), sx, sy, life(t, 7.1), t * 30)
        tag(u, "24 H", 860, TABLE - 120, t, 8.3, None, rot=-5, size=64)
    title(u, "ÉTAPE 1", t, 4.94, 5.85, y=330)
    title(u, "GRATTE LA CHAIR", t, 5.9, 7.0, y=330, size=130)
    title(u, "SÈCHE 1 JOURNÉE", t, 7.06, None, y=330, color=YEL, size=125)
    return w, u


cue(5.95, "stir", 0.35)
cue(6.5, "stir", 0.3)
cue(7.2, "sparkle", 0.22)
cue(8.3, "pop", 0.22)


# ============================================================ D. ÉTAPE 2 : OUVRE-LE AU CISEAU, PAR LE CÔTÉ (9.0 → 12.55)
def s_step2(t):
    w, u = new_layers(background("table"))
    put(u, num_badge("2", 160), 190, 560, life(t, 9.1, 9.8))
    X, Y = 540, TABLE + 20
    shadow(w, X, Y, 640)
    pit(w, X, Y, K1, 1.0, 1.0)
    cy = Y - (PIT_BOT - PIT_C[1]) * K1
    p0 = (X + (PIT_RX - 10) * K1, cy)
    p1 = (X - (PIT_RX - 40) * K1, cy)
    cut = clamp((t - 10.3) / 1.3)
    a = fade(t, 9.85, None, 0.2)
    if t > 9.85:
        dashed(u, (lerp(p0[0], p1[0], cut), cy), p1, a)
        d = ImageDraw.Draw(w)
        if cut > 0:
            d.line([p0, (lerp(p0[0], p1[0], cut), cy)], fill=(90, 70, 40), width=6)
    scissors(u, p0, p1, (t - 10.25) / 1.4, flip=True, hh=170)
    if t > 11.74:
        tag(u, "LE CÔTÉ", 860, cy - 260, t, 11.74, None, rot=-5, size=56, string_to=(p0[0] - 10, cy - 20))
    title(u, "ÉTAPE 2", t, 9.1, 9.78, y=330)
    title(u, "OUVRE-LE AU CISEAU", t, 9.82, 11.68, y=330, size=118)
    title(u, "PAR LE CÔTÉ", t, 11.74, None, y=330, color=YEL, size=150)
    return w, u


cue(10.3, "chop", 0.4)
cue(10.95, "chop", 0.4)
cue(11.74, "pop", 0.22)


# ============================================================ E. UNE GROSSE GRAINE, UN HARICOT GÉANT (12.55 → 16.4)
@lru_cache(None)
def pit_halves():
    im = pit_img(10, 10)
    cy = PIT_C[1]
    top, bot = im.copy(), im.copy()
    a = np.asarray(im.getchannel("A"))
    yy = np.arange(1024)[:, None]
    top.putalpha(Image.fromarray(np.where(yy < cy, a, 0).astype("uint8")))
    bot.putalpha(Image.fromarray(np.where(yy >= cy, a, 0).astype("uint8")))
    return top, bot


def s_inside(t):
    w, u = new_layers(background("table"))
    X, Y = 540, TABLE + 20
    k = K1
    top, bot = pit_halves()
    gone = ease_io((t - 13.8) / 0.4)
    op = ease_out((t - 12.66) / 0.45)
    if gone < 1:
        shadow(w, X, Y, 640)
        al = 1 - gone
        sz = int(1024 * k)
        b = bot.resize((sz, sz), Image.BICUBIC)
        put(w, b, X + (512 - PIT_C[0]) * k - 260 * gone, Y + (512 - PIT_BOT) * k, 1.0, 0, al)
    # graine : d'abord dans la coque, puis elle grossit au centre
    gk = lerp(0.62, 0.95, ease_out((t - 13.8) / 0.5))
    gy = lerp(Y - 70, Y, gone)
    seed(w, X, gy, gk, life(t, 12.6, dur=0.2) if t < 13.8 else 1.0)
    if gone < 1:
        sz = int(1024 * k)
        tp = top.resize((sz, sz), Image.BICUBIC)
        # charnière à gauche : la moitié du dessus bascule vers le haut
        hx, hy = X - (PIT_RX - 30) * k, Y - (PIT_BOT - PIT_C[1]) * k
        D = 2 * sz
        can = Image.new("RGBA", (D, D), (0, 0, 0, 0))
        can.alpha_composite(tp, (int(D / 2 - (512 + (PIT_C[0] - 512) - (PIT_RX - 30)) * k),
                                 int(D / 2 - PIT_C[1] * k)))
        can = can.rotate(55 * op, center=(D / 2, D / 2), resample=Image.BICUBIC)
        put(w, can, hx, hy - 40 * op - 300 * gone, 1.0, 0, 1 - gone)
    if t > 12.7:
        sparkles(u, t, 12.75, X, Y - 200, 300, 8, 3)
    if t > 15.02:
        wob = math.sin((t - 15.02) * 9) * 4 * math.exp(-(t - 15.02) * 2)
        tag(u, "HARICOT GÉANT !", 790, TABLE - 520, t, 15.1, None, rot=-6 + wob, size=54)
    title(u, "À L'INTÉRIEUR…", t, 12.66, 13.7, y=330)
    title(u, "UNE GROSSE GRAINE", t, 13.78, None, y=330, color=YEL, size=125)
    return w, u


cue(12.8, "crunch", 0.45)
cue(14.06, "pop_hi", 0.25)
cue(15.3, "ding", 0.25)


# ============================================================ F. ÉTAPE 3 : ESSUIE-TOUT HUMIDE, BOÎTE FERMÉE, AU CHAUD (16.4 → 20.95)
GK3 = 0.62


def bundle(c, t, X, Y, cover, wet, sprout=False, s=1.0):
    """Graine sur l'essuie-tout, recouverte (cover)."""
    tw, th = 640 * s, 420 * s
    towel(c, X, Y - th / 2 + 10, tw + 60, th + 30, 1.0 if cover > 0 else 0.0, wet)
    seed(c, X, Y - 30 * s, GK3 * s, sprout=sprout)
    towel(c, X, Y - th / 2 + 10, tw, th - 20, cover, wet)


def s_step3(t):
    w, u = new_layers(background("table"))
    warm_glow(w, fade(t, 20.46, None, 0.5))
    put(u, num_badge("3", 160), 190, 560, life(t, 16.5, 17.2))
    X, Y = 540, TABLE + 10
    boxs = life(t, 19.1, dur=0.35)
    box_back(w, X, Y + 10, boxs)
    cover = ease_io((t - 17.35) / 0.8)
    wet = ease_out((t - 18.6) / 0.6)
    if t < 17.3:
        shadow(w, X, Y + 10, 520)
        seed(w, X, Y - 20, GK3, life(t, 16.45))
    else:
        bundle(w, t, X, Y, cover, wet)
    if 18.58 < t < 19.2:
        for i in range(6):
            tt = t - 18.58 - i * 0.07
            if 0 < tt < 0.35:
                put(w, icon("drop", 50), X - 220 + i * 90, lerp(Y - 600, Y - 280, (tt / 0.35) ** 2), 1)
    box_front(w, X, Y + 10, ease_out((t - 19.55) / 0.2) if t > 19.4 else 0.0, boxs)
    if t > 20.46:
        put(u, icon("thermo", 150), 900, 620, life(t, 20.5))
    title(u, "ÉTAPE 3", t, 16.5, 17.2, y=330)
    title(u, "ESSUIE-TOUT HUMIDE", t, 17.26, 19.0, y=330, size=118)
    title(u, "BOÎTE FERMÉE", t, 19.06, 20.4, y=330, size=150)
    title(u, "AU CHAUD", t, 20.46, None, y=330, color=YEL, size=170)
    return w, u


cue(17.35, "stir", 0.25)
cue(18.62, "plop", 0.3)
cue(19.72, "click", 0.4)
cue(20.5, "rise", 0.2)


# ============================================================ G. ÉTAPE 4 : PATIENCE, UNE RACINE SORT (20.95 → 25.95)
def s_step4(t):
    w, u = new_layers(background("table"))
    warm_glow(w, 1.0)
    put(u, num_badge("4", 160), 190, 560, life(t, 21.02, 21.9))
    X, Y = 540, TABLE + 10
    reveal = ease_io((t - 24.78) / 0.35)
    if reveal < 1:
        box_back(w, X, Y + 10)
        bundle(w, t, X, Y, 1.0 - reveal, 1.0, sprout=t > 24.78)
        box_front(w, X, Y + 10, 1.0, lid_lift=500 * reveal)
        if 21.4 < t < 24.7:
            night = 0.5 + 0.5 * math.sin((t - 21.4) * 8)
            ov = Image.new("RGBA", (W, H), (20, 26, 60, int(90 * night * fade(t, 21.4, 24.6, 0.2, 0.2))))
            w.alpha_composite(ov)
    else:
        g = ease_out((t - 25.13) / 0.4)
        k = lerp(GK3, 0.98, g)
        seed(w, X, Y - lerp(30, 120, g), k, sprout=True)
        sx, sy = X + (SPROUT[0] - SEED_C[0]) * k, Y - lerp(30, 120, g) + (SPROUT[1] - SEED_BOT) * k
        hl_ellipse(u, sx, sy + 20, 110, 110, life(t, 25.25))
        tag(u, "RACINE !", 830, sy + 150, t, 25.3, None, rot=5, size=60, string_to=(sx + 90, sy + 40))
        sparkles(u, t, 25.15, sx, sy, 200, 8, 9)
    if 23.4 < t < 24.78:
        act = 0 if t < 23.86 else 1
        pills(u, ["1 SEMAINE", "2 SEMAINES"], act, t, 23.45, 24.75, y=1430, pw=300)
    title(u, "ÉTAPE 4", t, 21.02, 22.1, y=330)
    title(u, "PATIENCE…", t, 22.22, 24.7, y=330, size=170)
    title(u, "UNE RACINE SORT !", t, 24.78, None, y=330, color=YEL, size=130)
    return w, u


cue(22.22, "bell", 0.25)
cue(23.5, "tick", 0.25)
cue(23.86, "tick", 0.25)
cue(24.8, "pop_lo", 0.35)
cue(25.15, "success", 0.35)


# ============================================================ H. EN POT (25.95 → 28.0)
POT_TOP = TABLE - 300


def s_pot(t):
    w, u = new_layers(background("table"))
    if t < 27.1:
        drop = ease_out((t - 26.1) / 0.4)
        seed(w, 540, lerp(POT_TOP - 500, POT_TOP + 70, drop), 0.3, sprout=True, rot=-20 * (1 - drop))
        pot(w, 540, POT_TOP, 440, 300)
        if t > 26.5:
            particles(w, t, 26.5, 540, POT_TOP, 12, 4, col=(90, 62, 40), size=9, up=300)
    else:
        tree(w, 540, TABLE + 30, 0.98, life(t, 27.1, dur=0.45))
        sparkles(u, t, 27.2, 540, 700, 380, 10, 8)
    title(u, "EN POT !", t, 27.1, None, y=330, color=YEL, size=170)
    return w, u


cue(26.5, "thud", 0.35)
cue(27.12, "sparkle", 0.3)


# ============================================================ I. CTA (28.0 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    tree(w, 260, TABLE + 30, 0.55, life(t, 28.05))
    shadow(w, 820, TABLE + 20, 260, int(70 * life(t, 28.15)))
    seed(w, 820, TABLE + 20, 0.36, life(t, 28.15), sprout=True)
    clicked = t > 28.62
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 28.57) / 0.15))
    put(u, btn, 540, 300, life(t, 28.1) * press)
    if t > 28.3:
        k = ease_out((t - 28.3) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(330), 540, 590, life(t, 29.9, dur=0.45))
    sparkles(u, t, 30.0, 540, 590, 230, 10, 12)
    return w, u


cue(28.6, "click", 0.45)
cue(30.0, "sparkle", 0.25)

if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video), (VID_END, 2.45, s_intro)]
else:
    _intro = [(0.0, 2.45, s_intro)]

SCENES = _intro + [
    (2.45, 4.85, s_hidden),
    (4.85, 9.0, s_step1),
    (9.0, 12.55, s_step2),
    (12.55, 16.4, s_inside),
    (16.4, 20.95, s_step3),
    (20.95, 25.95, s_step4),
    (25.95, 28.0, s_pot),
    (28.0, 99.0, s_cta),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = [(1, 4.94, 9.0), (2, 9.1, 16.4), (3, 16.5, 20.95), (4, 21.02, 25.95)]

if HAS_VIDEO:
    CUES[:] = [c for c in CUES if c[0] >= VID_END - 0.05]
