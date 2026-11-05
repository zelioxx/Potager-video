"""Storyboard « La banane est une baie, la fraise non ! » (voix : assets/audio/banane_fraise/voix.mp3).

Volume de la voix gardé tel qu'envoyé (render.py « af »).
0–5     la cuisine (planche) : banane ✓ BAIE, fraise ✗ ; « attends de voir la suite » : la caméra se rapproche.
5–8.6   fond beige : une baie = un fruit charnu, graines cachées à l'intérieur (banane épluchée, loupe sur la coupe).
8.6–11.7 comme la tomate, le kiwi… et même la citrouille ! (✓ chacun).
11.7–15.3 la fraise : ses vrais fruits sont les petits grains sur sa peau (loupe sur les akènes).
15.3–18 la framboise non plus n'est pas une baie.
18–fin  le récap (banane ✓, fraise ✗) + S'abonner + logo.
Photos : banane, tomates (banque) ; fraise, framboise, kiwi, citrouille (Open Images) ; cuisine (fournie).
"""
import math

from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, put, title, life, fade, ease_out, ease_io,
                 ease_in, clamp, lerp, icon, tag, button_img, hl_ellipse, particles, light_rays, text_img, F_BLACK)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade, shadow, swap
from scenes_banane import ob
from scenes_eau_pates import Cam

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


BANANE, EPLUCHEE = "banque/banane_entiere", "banque/banane_epluchee"
FRAISE, FRAMBOISE = "banque/fraise", "banque/framboise"
TOMATES, KIWI, CITROUILLE = "banque/tomate", "banque/kiwi_coupe", "banque/citrouille"
KIWI_ENTIER, MYRTILLE, CONCOMBRE = "banque/kiwi_entier", "banque/myrtille", "banque/concombre"


def badge(c, ok, x, y, s, size=150):
    put(c, icon("check" if ok else "cross", size), x, y, s)


def lens(u, src, sx, sy, sr, lx, ly, r, g):
    """Loupe : agrandit le disque (sx, sy, sr) du calque `src` dans un cercle de rayon r en (lx, ly)."""
    if g <= 0.01:
        return
    r = r * g
    crop = src.crop((int(sx - sr), int(sy - sr), int(sx + sr), int(sy + sr))).resize((int(2 * r), int(2 * r)),
                                                                                      Image.BICUBIC)
    disk = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(disk).ellipse([lx - r, ly - r, lx + r, ly + r], fill=CREAM + (255,))
    disk.alpha_composite(crop, (int(lx - r), int(ly - r)))
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse([lx - r, ly - r, lx + r, ly + r], fill=255)
    disk.putalpha(Image.composite(disk.getchannel("A"), Image.new("L", (W, H), 0), m))
    u.alpha_composite(disk)
    d = ImageDraw.Draw(u)
    hx, hy = lx + r * 0.72, ly + r * 0.72
    d.line([(hx, hy), (hx + 150 * g, hy + 150 * g)], fill=DARK, width=int(46 * g))
    d.line([(hx + 10, hy + 10), (hx + 140 * g, hy + 140 * g)], fill=(150, 90, 50), width=int(30 * g))
    d.ellipse([lx - r - 14, ly - r - 14, lx + r + 14, ly + r + 14], outline=DARK, width=int(30 * g))
    d.ellipse([lx - r - 6, ly - r - 6, lx + r + 6, ly + r + 6], outline=(190, 196, 200), width=int(12 * g))


# ============================================================ A. LA CUISINE : BANANE ✓, FRAISE ✗ (0 → 5.0)
BX, FX = 440, 700                                # banane et fraise sur la planche (coordonnées de la photo)
GROUND = 1265


def s_kitchen(t):
    zk = ease_io((t - 3.6) / 1.2)
    cam = Cam(lerp(1.75, 1.95, zk), 560, lerp(1030, 1060, zk))
    w = cam.bg("citron_fond_cuisine.png")
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    z = cam.z
    bx, by = cam.p(BX, GROUND)
    fx, fy = cam.p(FX, GROUND)
    hop_b = abs(math.sin(math.pi * clamp((t - 0.9) / 0.35))) * 40 * z
    hop_f = abs(math.sin(math.pi * clamp((t - 2.35) / 0.3))) * 30 * z
    shadow(w, bx, by, 300 * z, 70)
    ob(w, BANANE, bx, by - hop_b, 250 * z, s=life(t, 0.0, dur=0.35), anchor="bottom", rot=-6)
    shake = math.sin(t * 60) * 8 * fade(t, 3.05, 3.4, 0.02, 0.2) if 3.05 < t < 3.4 else 0.0
    shadow(w, fx, fy, 150 * z, 70)
    ob(w, FRAISE, fx + shake, fy - hop_f, 165 * z, s=life(t, 0.15, dur=0.35), anchor="bottom")
    w.alpha_composite(shade())
    badge(u, True, bx + 40, by - 260 * z, life(t, 1.33))
    if t > 1.33:
        tag(u, "BAIE", bx - 10, by - 150 * z, t, 1.4, None, rot=-5, size=58)
    badge(u, False, fx, fy - 230 * z, life(t, 3.05))
    if t > 3.6:
        for i, (qx, qy, t0) in enumerate([(250, 640, 3.65), (840, 600, 3.8), (560, 560, 3.95)]):
            wob = math.sin((t - t0) * 6 + i) * 8
            put(u, qmark(), qx, qy + wob, life(t, t0), wob)
    title(u, "LA BANANE ?", t, 0.05, 1.3, y=330, color=YEL, size=165)
    stamp(u, "UNE BAIE !", 540, 340, t, 1.33, 2.1, GREEN, 150, -7)
    title(u, "LA FRAISE…", t, 2.13, 3.0, y=330, size=165)
    stamp(u, "NON !", 540, 340, t, 3.05, 3.55, RED, 170, -8)
    title(u, "ATTENDS LA SUITE…", t, 3.6, None, y=330, color=YEL, size=130)
    return w, u


_Q = {}


def qmark():
    if "q" not in _Q:
        from gfx import F_TITLE
        _Q["q"] = text_img("?", F_TITLE, 170, YEL, 8, DARK, 6, DARK)
    return _Q["q"]


cue(0.03, "pop", 0.22)
cue(0.95, "pop_hi", 0.2)
cue(1.35, "ding", 0.3)
cue(2.38, "pop_hi", 0.18)
cue(3.07, "alert2", 0.3)
cue(3.65, "tick", 0.18)
cue(3.8, "tick", 0.18)
cue(3.95, "tick", 0.18)


# ============================================================ B. UNE BAIE = FRUIT CHARNU, GRAINES À L'INTÉRIEUR (5.0 → 8.6)
def banana_slice(size):
    """Rondelle de banane dessinée (vue en coupe) : chair crème, centre plus clair, petites graines noires."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    d.ellipse([4, 4, size - 4, size - 4], fill=(244, 222, 150), outline=(210, 180, 90), width=max(3, size // 40))
    d.ellipse([c - size * 0.3, c - size * 0.3, c + size * 0.3, c + size * 0.3], fill=(250, 238, 190))
    for k in range(6):
        a = k * math.pi / 3 + 0.3
        x, y = c + math.cos(a) * size * 0.11, c + math.sin(a) * size * 0.11
        rr = size * 0.025
        d.ellipse([x - rr, y - rr * 1.4, x + rr, y + rr * 1.4], fill=(55, 40, 30))
    return im.filter(ImageFilter.GaussianBlur(0.8))


def s_define(t):
    w, u = new_layers(background("table"))
    light_rays(w, 540, 500, t, fade(t, 5.0, None, 0.4) * 0.6)
    which, sc = swap((t - 6.35) / 0.3)            # « fruit charnu » : on l'épluche
    s_ = life(t, 5.02, dur=0.35)
    shadow(w, 540, TABLE + 30, 560 * s_)
    if which == 0:
        ob(w, BANANE, 540, TABLE + 30, 700 * sc, s=s_, anchor="bottom", rot=-4)
    else:
        ob(w, EPLUCHEE, 540, TABLE + 30, 560 * sc, anchor="bottom")
    # « graines cachées à l'intérieur » : une rondelle en coupe sous la loupe
    g = life(t, 7.15, dur=0.4)
    if g > 0.01:
        sl = banana_slice(int(420 * g))
        lx, ly = 540, 760
        put(u, sl, lx, ly, 1.0)
        d = ImageDraw.Draw(u)
        r = 230 * g
        d.ellipse([lx - r - 14, ly - r - 14, lx + r + 14, ly + r + 14], outline=DARK, width=int(30 * g))
        d.ellipse([lx - r - 6, ly - r - 6, lx + r + 6, ly + r + 6], outline=(190, 196, 200), width=int(12 * g))
        hx, hy = lx + r * 0.72, ly + r * 0.72
        d.line([(hx, hy), (hx + 150 * g, hy + 150 * g)], fill=DARK, width=int(46 * g))
        d.line([(hx + 10, hy + 10), (hx + 140 * g, hy + 140 * g)], fill=(150, 90, 50), width=int(30 * g))
        if t > 7.6:
            tag(u, "GRAINES", 860, 520, t, 7.6, None, rot=-6, size=54, string_to=(lx + 40, ly - 30))
    title(u, "UNE BAIE ?", t, 5.05, 6.25, y=330, color=YEL, size=170)
    title(u, "UN FRUIT CHARNU", t, 6.3, 7.05, y=330, size=140)
    title(u, "GRAINES À L'INTÉRIEUR", t, 7.1, None, y=330, color=YEL, size=112)
    return w, u


cue(5.05, "pop", 0.22)
cue(6.38, "squish", 0.22)
cue(7.18, "pop_hi", 0.22)
cue(7.62, "pop", 0.18)


# ============================================================ C. COMME LA TOMATE, LE KIWI, MÊME LA CITROUILLE (8.6 → 11.7)
TRIO = [(TOMATES, 200, 290, 9.15), (KIWI, 540, 300, 9.85), (CITROUILLE, 870, 330, 10.95)]


def s_examples(t):
    w, u = new_layers(background("table"))
    for name, x, wd, t0 in TRIO:
        s_ = life(t, t0, dur=0.35)
        if s_ > 0.01:
            shadow(w, x, TABLE + 30, wd * 0.85 * s_)
            if name == KIWI:   # le kiwi arrive entier, puis il est coupé : on voit ses graines
                which, sc = swap((t - 10.25) / 0.3)
                ob(w, KIWI_ENTIER if which == 0 else KIWI, x, TABLE + 30, (230 if which == 0 else wd) * sc * s_,
                   anchor="bottom")
            else:
                ob(w, name, x, TABLE + 30, wd, s=s_, anchor="bottom")
            badge(u, True, x, TABLE - 450, life(t, t0 + 0.2), 130)
    if t > 11.05:
        sparkles(u, t, 11.1, 850, TABLE - 150, 220, 8, 5)
    title(u, "COMME LA TOMATE", t, 8.7, 9.8, y=330, size=140)
    title(u, "LE KIWI…", t, 9.85, 10.9, y=330, color=YEL, size=170)
    stamp(u, "ET LA CITROUILLE !", 540, 340, t, 10.95, None, GREEN, 110, -6)
    return w, u


cue(9.17, "pop", 0.22)
cue(9.87, "pop", 0.22)
cue(10.97, "pop_lo", 0.28)
cue(11.1, "success", 0.25)


# ============================================================ D. LA FRAISE : SES VRAIS FRUITS = LES PETITS GRAINS (11.7 → 15.3)
FR_X, FR_BOT, FR_W = 540, TABLE + 30, 470
SEEDS = [(292, 337), (501, 335), (671, 346), (243, 445), (392, 457), (592, 444), (765, 426), (493, 540)]   # akènes


def s_strawberry(t):
    w, u = new_layers(background("table"))
    s_ = life(t, 11.75, dur=0.35)
    shadow(w, FR_X, FR_BOT, FR_W * 0.8 * s_)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ob(lay, FRAISE, FR_X, FR_BOT, FR_W, s=s_, anchor="bottom")
    w.alpha_composite(lay)
    k = FR_W / (813 - 210)

    def P(x, y):
        return FR_X + (x - 511.5) * k, FR_BOT + (y - 948) * k

    # les petits grains : entourés un par un
    if t > 13.95:
        for i, (sx, sy) in enumerate(SEEDS):
            x, y = P(sx, sy)
            hl_ellipse(u, x, y, 28, 28, life(t, 14.0 + i * 0.07), width=6)
    # la loupe sur la peau
    g = life(t, 12.9, 13.9, dur=0.35)
    if g > 0.01:
        cx, cy = P(470, 470)
        lens(u, lay, cx, cy, 70, 290, 760, 200, g)
    if t > 13.0:
        tag(u, "VRAIS FRUITS !", 800, TABLE - 640, t, 13.25, None, rot=-5, size=56,
            string_to=P(592, 444) if t > 14.0 else None)
    title(u, "ET LA FRAISE ?", t, 11.8, 12.85, y=330, color=YEL, size=150)
    title(u, "SES VRAIS FRUITS…", t, 12.9, 13.9, y=330, size=135)
    title(u, "LES PETITS GRAINS !", t, 13.95, None, y=330, color=YEL, size=120)
    return w, u


cue(11.8, "pop", 0.22)
cue(12.95, "pop_hi", 0.2)
cue(14.0, "sparkle", 0.22)


# ============================================================ E. LA FRAMBOISE NON PLUS (15.3 → 17.95)
def s_rasp(t):
    w, u = new_layers(background("table"))
    s_ = life(t, 15.35, dur=0.35)
    shake = math.sin(t * 60) * 8 * fade(t, 16.5, 16.85, 0.02, 0.2) if 16.5 < t < 16.85 else 0.0
    shadow(w, 540, TABLE + 30, 460 * s_)
    ob(w, FRAMBOISE, 540 + shake, TABLE + 30, 480, s=s_, anchor="bottom")
    badge(u, False, 830, TABLE - 520, life(t, 16.55), 170)
    title(u, "LA FRAMBOISE ?", t, 15.4, 16.45, y=330, color=YEL, size=140)
    stamp(u, "PAS UNE BAIE !", 540, 340, t, 16.5, None, RED, 125, -7)
    return w, u


cue(15.42, "pop", 0.22)
cue(16.52, "alert2", 0.3)


# ============================================================ F. RÉCAP + ABONNE-TOI (17.95 → fin)
def s_end(t):
    w, u = new_layers(background("table"))
    light_rays(w, 540, 300, t, 0.6)
    baies = [(BANANE, 100, 165, -6), (TOMATES, 262, 125, 0), (KIWI, 390, 125, 0), (MYRTILLE, 490, 80, 0),
             (CONCOMBRE, 590, 130, -20)]
    non = [(FRAISE, 800, 125, 0), (FRAMBOISE, 960, 125, 0)]
    for i, (name, x, wd, rot) in enumerate(baies + non):
        s_ = life(t, 18.0 + i * 0.07, dur=0.35)
        shadow(w, x, TABLE + 30, wd * 0.8 * s_)
        ob(w, name, x, TABLE + 30, wd, s=s_, anchor="bottom", rot=rot)
    ga = life(t, 18.45, dur=0.3)
    if ga > 0.01:
        tag(u, "BAIES", 340, TABLE - 300, t, 18.45, None, rot=-4, size=56)
        badge(u, True, 340, TABLE - 410, ga, 110)
        tag(u, "PAS DES BAIES", 880, TABLE - 300, t, 18.55, None, rot=4, size=44)
        badge(u, False, 880, TABLE - 410, life(t, 18.55, dur=0.3), 110)
        ImageDraw.Draw(w).line([(695, TABLE - 220), (695, TABLE + 60)], fill=DARK + (160,), width=6)
    put(u, logo_img(250), 540, 560, life(t, 18.05, dur=0.45))
    sparkles(u, t, 18.15, 540, 560, 210, 10, 12)
    clicked = t > 19.5
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 19.45) / 0.15))
    put(u, btn, 540, 790, life(t, 18.35) * press)
    if t > 18.95:
        k = ease_out((t - 18.95) / 0.45)
        put(u, icon("cursor", 110), lerp(880, 640, k), lerp(1040, 830, k), 1)
    title(u, "PLUS D'ASTUCES ?", t, 18.0, None, y=330, color=YEL, size=135)
    return w, u


cue(18.02, "pop_lo", 0.28)
cue(19.48, "click", 0.45)
cue(20.1, "sparkle", 0.25)

SCENES = [
    (0.0, 5.0, s_kitchen),
    (5.0, 8.6, s_define),
    (8.6, 11.7, s_examples),
    (11.7, 15.3, s_strawberry),
    (15.3, 17.95, s_rasp),
    (17.95, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
