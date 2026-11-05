"""Storyboard « Eau de cuisson des pâtes : engrais ou poison ? » (voix : assets/audio/eau_pates/voix.mp3).

Le volume de la voix est gardé tel qu'envoyé (aucun mastering, cf. render.py « af »).
0–4.1   coin du salon (photo fournie) : le pothos en pleine forme, une casserole de pâtes fumante verse son eau…
        « ou les tuer » : BIM, la plante sèche d'un coup (photo fournie du même pothos desséché).
4.1–7.4 fond beige : la casserole de pâtes ; « le sel » : la boîte de sel arrive et sale l'eau.
7.4–11.2 le pot coupé en deux (photos fournies) : le sel tombe sur la terre, descend, et les racines blanches
        pourrissent au passage (racines saines → racines pourries, de haut en bas) ; le sel s'accumule dans la terre.
11.2–14.2 sans sel et refroidie : la casserole ne fume plus, la boîte de sel est barrée ; « oui, de temps en temps ».
14.2–18.1 le meilleur : l'eau de cuisson des légumes, pleine de minéraux (K, Ca, Mg).
18.1–fin le pothos de nouveau en forme dans le salon, bouton S'abonner et logo.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, background, put, title, life, fade, ease_out,
                 ease_io, ease_in, clamp, lerp, icon, pills, tag, button_img, hl_ellipse, particles, light_rays,
                 text_img, F_TITLE, F_BLACK)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp
from scenes_citron import photo, shade, zoomed, shadow, swap
from scenes_banane import ob

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


SAIN, SEC = "banque/pothos_sain", "banque/pothos_sec"
COUPE_OK, COUPE_KO = "banque/pothos_coupe_racines_saines", "banque/pothos_coupe_racines_pourries"
CASS, CASS_HOT, SEL = "banque/casserole_pates", "banque/casserole_pates_ebullition", "banque/sel_boite"
FULL = (0, 0, 1024, 1024)
POT_BASE = (525, 985)                            # bas du pot dans les photos du pothos (cadre 1024)


def pothos(c, name, X, Y, k, s=1.0, rot=0.0):
    place(c, name, FULL, k, *POT_BASE, X, Y, s, rot)


def steam(c, t, x, y, w_, a=1.0, n=6):
    """Volutes de vapeur qui montent (douces, floues)."""
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(n):
        p = (t * 0.55 + i / n) % 1.0
        xx = x + (i - n / 2) * w_ / n + math.sin(t * 2 + i * 1.7) * 30 * p
        yy = y - p * 320
        r = 30 + 60 * p
        d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(255, 255, 255, int(70 * a * math.sin(math.pi * p))))
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(18)))


@lru_cache(None)
def mineral_tile(sym, num, name, size=150):
    im = Image.new("RGBA", (size + 12, size + 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 10, size + 6, size + 10], radius=size * 0.14, fill=DARK)
    d.rounded_rectangle([0, 0, size, size], radius=size * 0.14, fill=YEL, outline=DARK, width=max(3, size // 30))
    im.alpha_composite(text_img(num, F_BLACK, int(size * 0.15), DARK), (int(size * 0.1), int(size * 0.07)))
    k = text_img(sym, F_TITLE, int(size * 0.5), DARK)
    im.alpha_composite(k, ((size - k.width) // 2, int(size * 0.2)))
    p = text_img(name, F_BLACK, int(size * 0.12), DARK)
    im.alpha_composite(p, ((size - p.width) // 2, int(size * 0.76)))
    return im


@lru_cache(None)
def _bg(name, z, fx, fy):
    return zoomed(photo(name), z, fx, fy)


def bg_photo(name, z, fx, fy):
    """Décor photo fourni, recadré (z, fx, fy) : les objets se posent sur la ligne TABLE de l'écran."""
    return _bg(name, z, fx, fy).copy(), Image.new("RGBA", (W, H), (0, 0, 0, 0))


KITCHEN = ("citron_fond_cuisine.png", 1.3, 560, 953)      # la planche à découper
WINDOW = ("fond_fenetre.webp", 1.5, 527, 1168)            # le rebord de la fenêtre


# ============================================================ A. LE SALON : L'EAU DE PÂTES… BIM (0 → 4.1)
class Cam:
    """Caméra : le décor est recadré (z, fx, fy) comme zoomed(), et les objets sont dessinés APRÈS, directement
    à la bonne taille (k * z) : ils restent nets au lieu d'être agrandis avec l'image."""

    def __init__(self, z, fx, fy):
        self.z = z
        cw, ch = W / z, H / z
        self.x0 = min(max(fx - cw / 2, 0), W - cw)
        self.y0 = min(max(fy - ch / 2, 0), H - ch)
        self.fx, self.fy = fx, fy

    def p(self, x, y):
        return (x - self.x0) * self.z, (y - self.y0) * self.z

    def bg(self, name):
        return zoomed(_bg(name, 1.0, 540, 960), self.z, self.fx, self.fy).copy()


PL_X, PL_Y, PL_K = 680, 1235, 0.76               # pothos dans le coin (≈ 1 m), coordonnées de la photo
SOIL = (PL_X - 10, PL_Y - 200)                   # terre du pot
PAN_W = 300
PAN_K = PAN_W / 918
PAN_RIM = (112, 470)                             # bec : bord gauche de la casserole fumante (cadre 1024)
PAN_C = (565.5, 587)                            # centre de la casserole (bbox) dans son cadre 1024
LIP = (880, 770)                                 # bec quand elle verse : au-dessus du feuillage, à droite
POUR_ROT = 64


def pan_center(lip, rot):
    """Position (centre de la casserole, comme ob() l'attend) pour que le bec soit en `lip` une fois inclinée.
    ob()/spr() font tourner l'image autour du centre de son cadre 1024, pas du centre de la casserole."""
    k = PAN_K
    vx, vy = (PAN_RIM[0] - 512) * k, (PAN_RIM[1] - 512) * k
    a = math.radians(rot)
    rx, ry = vx * math.cos(a) + vy * math.sin(a), -vx * math.sin(a) + vy * math.cos(a)
    fx, fy = lip[0] - rx, lip[1] - ry                  # centre du cadre
    return fx - (512 - PAN_C[0]) * k, fy - (512 - PAN_C[1]) * k


def pour_stream(c, cam, t, lip, a=1.0):
    """Eau de cuisson qui coule du bec : nappe translucide et trouble qui s'affine en tombant, reflets qui
    descendent, quelques gouttes qui s'échappent, vapeur (eau chaude)."""
    if a <= 0.01:
        return
    g, vy = 2200.0, -40.0
    ground = SOIL[1] + 8
    tau_end = (-vy + math.sqrt(vy * vy + 2 * g * (ground - lip[1]))) / g
    vx = (SOIL[0] + 25 - lip[0]) / tau_end           # elle arrive sur la terre du pot
    n = 22
    pts = [(lip[0] + vx * tau_end * i / n, lip[1] + vy * tau_end * i / n + 0.5 * g * (tau_end * i / n) ** 2)
           for i in range(n + 1)]
    sp = [cam.p(x, y) for x, y in pts]
    z = cam.z
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    left, right = [], []
    for i, (x, y) in enumerate(sp):
        q = i / n
        x2, y2 = sp[min(n, i + 1)] if i < n else sp[i]
        x1, y1 = sp[max(0, i - 1)]
        nx, ny = -(y2 - y1), (x2 - x1)
        ln = math.hypot(nx, ny) or 1
        wid = (15 - 7 * q) * z * (1 + 0.12 * math.sin(q * 22 - t * 26))
        left.append((x + nx / ln * wid, y + ny / ln * wid))
        right.append((x - nx / ln * wid, y - ny / ln * wid))
    d.polygon(left + right[::-1], fill=(226, 220, 200, int(150 * a)))      # eau trouble (amidon)
    d.line(left, fill=(250, 248, 238, int(170 * a)), width=max(2, int(2.5 * z)))
    for k in range(3):                                                     # reflets qui filent vers le bas
        ph = (t * 2.4 + k / 3) % 1.0
        i0 = int(ph * (n - 3))
        d.line(sp[i0:i0 + 3], fill=(255, 255, 255, int(220 * a)), width=max(2, int(3 * z)))
    r = np.random.default_rng(int(t * 30))
    for k in range(7):                                                     # gouttes échappées
        q = r.uniform(0.15, 1.0)
        x, y = sp[int(q * n)]
        x += r.uniform(-24, 24) * z
        rr = r.uniform(2, 4.5) * z
        d.ellipse([x - rr, y - rr * 1.4, x + rr, y + rr * 1.4], fill=(240, 236, 222, int(200 * a)))
    c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(0.9)))
    # vapeur le long du filet (eau bouillante)
    mx, my = cam.p(lip[0] - 30, lip[1] + 40)
    steam(c, t * 1.3, mx, my, 120 * z, 0.75 * a, 4)


def draw_plant(w, t, cam, dry_t=None):
    px, py = cam.p(PL_X, PL_Y)
    shadow(w, px, py, 300 * cam.z, 80)
    if dry_t is None:
        pothos(w, SAIN, px, py, PL_K * cam.z)
    else:
        which, sc = swap((t - dry_t) / 0.3)
        shake = math.sin(t * 70) * 8 * fade(t, dry_t, dry_t + 0.45, 0.02, 0.2) if dry_t < t < dry_t + 0.45 else 0.0
        pothos(w, SAIN if which == 0 else SEC, px + shake, py, PL_K * cam.z * sc)


def s_salon(t):
    zk = ease_io((t - 2.9) / 0.6)
    cam = Cam(lerp(1.25, 1.4, zk), 640, lerp(900, 930, zk))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cin = ease_out((t - 0.15) / 0.45)
    tilt = ease_io((t - 0.55) / 0.3)
    cout = ease_in((t - 2.35) / 0.35)
    flowing = 0.82 < t < 2.4
    w = cam.bg("fond_salon_coin2.jpg")
    # ordre de profondeur : décor → plante → filet d'eau (versé devant, sur la terre) → casserole (au premier plan)
    draw_plant(w, t, cam, 2.95)
    if flowing:
        pour_stream(w, cam, t, LIP, fade(t, 0.82, 2.4, 0.06, 0.15))
    if 0.15 < t < 2.75:   # la casserole, devant la plante (plus près de nous)
        rot = POUR_ROT * tilt * (1 - cout)
        cx, cy = pan_center(LIP, rot)
        cx, cy = cx + (1 - cin) * 520 + cout * 520, cy - (1 - cin) * 260 - cout * 260
        sx, sy = cam.p(cx, cy)
        if not flowing:
            steam(w, t, sx, sy - 90 * cam.z, 200 * cam.z, 0.8)
        ob(w, CASS_HOT, sx, sy, PAN_W * cam.z, rot=rot)
        if flowing:   # éclaboussures sur la terre, entre les feuilles
            gx, gy = cam.p(SOIL[0] - 20, SOIL[1] - 10)
            particles(w, t, t - (t % 0.25), gx, gy, 7, int(t * 12) % 9, col=(238, 232, 214), size=4 * cam.z,
                      up=170, spread=140, dur=0.25)
    if 2.95 < t < 4.1:   # BIM : feuilles qui tombent, poussière sèche
        bx, by = cam.p(PL_X, PL_Y - 380)
        particles(w, t, 2.97, bx, by, 18, 7, col=(150, 120, 70), size=12, up=200, dur=1.0)
    if 2.95 < t < 3.25:   # flash
        w.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(150 * (1 - (t - 2.95) / 0.3)))))
    w.alpha_composite(shade())
    title(u, "L'EAU DE TES PÂTES ?", t, 0.05, 1.75, y=330, color=YEL, size=125)
    title(u, "ÇA NOURRIT…", t, 1.8, 2.9, y=330, color=GREEN, size=160)
    stamp(u, "OU ÇA TUE !", 540, 340, t, 2.95, None, RED, 150, -7)
    return w, u


cue(0.17, "whoosh", 0.16)
cue(0.75, "pour", 0.32)
cue(2.97, "fail", 0.4)
cue(3.0, "thud", 0.3)


# ============================================================ B. TOUT DÉPEND D'UN DÉTAIL : LE SEL (4.1 → 7.4)
CB_X, CB_Y, CB_W = 470, TABLE + 40, 640
PAN_WATER_Y = CB_Y + (470 - 935) * CB_W / 918   # surface de l'eau de la casserole fumante
SALT_BOX = (CB_X - 32 + 185, 850 - 130)          # boîte de sel : l'ouverture, une fois penchée, juste au-dessus


def salt_grains(c, t, t0, x, y, dur=0.9, n=26, fall=300):
    if t < t0 or t > t0 + dur + 0.5:
        return
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(5)
    for i in range(n):
        p = (t - t0 - r.uniform(0, dur)) / 0.45
        if 0 < p < 1:
            gx = x + r.uniform(-30, 30) + r.uniform(-20, 20) * p
            gy = y + p * p * fall
            d.rectangle([gx - 5, gy - 5, gx + 5, gy + 5], fill=(252, 252, 252, 255), outline=(150, 150, 150))


def s_salt(t):
    w, u = bg_photo(*KITCHEN)
    s_ = life(t, 4.1, dur=0.35)
    shadow(w, CB_X, CB_Y, CB_W * 0.8 * s_)
    steam(w, t, CB_X, CB_Y - 380, 380, s_)
    ob(w, CASS_HOT, CB_X, CB_Y, CB_W, s=s_, anchor="bottom")
    # la boîte de sel arrive et verse
    if t > 6.2:
        q = ease_out((t - 6.22) / 0.35)
        tilt = 125 * ease_io((t - 6.5) / 0.3)
        bx, by = lerp(1300, SALT_BOX[0], q), lerp(760, SALT_BOX[1], q)
        ob(w, SEL, bx, by, 210, rot=tilt)
        # le sel sort de l'ouverture de la boîte et tombe dans l'eau (s'arrête à la surface)
        a = math.radians(tilt)
        ox, oy = bx - 226 * math.sin(a), by - 226 * math.cos(a)
        salt_grains(u, t, 6.8, ox, oy + 10, fall=PAN_WATER_Y - oy - 10)
        if t > 6.25:
            hl_ellipse(u, bx, by, 190, 280, life(t, 6.3, 6.75))
    w.alpha_composite(shade())
    title(u, "TOUT DÉPEND", t, 4.12, 4.95, y=330, size=165)
    title(u, "D'UN SEUL DÉTAIL…", t, 4.99, 6.15, y=330, color=YEL, size=130)
    stamp(u, "LE SEL !", 540, 340, t, 6.22, None, RED, 170, -8)
    return w, u


cue(4.12, "pop", 0.22)
cue(5.0, "tick", 0.2)
cue(5.5, "tick", 0.2)
cue(6.24, "alert1", 0.32)
cue(6.82, "rustle", 0.25)


# ============================================================ C. EN COUPE : LES RACINES POURRISSENT (7.4 → 11.2)
CK = 1.38
CX0, CY0 = 540, TABLE + 40                       # bas du pot coupé (écran)
SOIL_TOP_SRC, ROOT_BOT_SRC = 775, 975            # terre dans la photo (cadre 1024)


def src2w(x, y):
    return CX0 + (x - 502) * CK, CY0 + (y - 998) * CK


ROOTS_BG = (1.82, 680, 1023)                     # salon recadré : le pot coupé tombe pile à la place du pothos


def s_roots(t):
    zk = ease_io((t - 7.45) / 0.6)
    cam = Cam(lerp(1.0, 1.9, zk), CX0, lerp(960, src2w(0, 880)[1], zk))
    z = cam.z
    w = zoomed(_bg("fond_salon_coin2.jpg", *ROOTS_BG), z, cam.fx, cam.fy).copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    def V(x, y):    # point de la photo du pot coupé → écran
        return cam.p(*src2w(x, y))

    # racines saines → pourries : le sel descend du haut vers le bas, les racines pourrissent derrière lui
    front = V(0, lerp(SOIL_TOP_SRC - 10, ROOT_BOT_SRC + 25, ease_io((t - 8.3) / 1.5)))[1]
    bx, by = cam.p(CX0, CY0)
    ok, ko = Image.new("RGBA", (W, H), (0, 0, 0, 0)), Image.new("RGBA", (W, H), (0, 0, 0, 0))
    place(ok, COUPE_OK, FULL, CK * z, 502, 998, bx, by)
    if t > 8.3:
        place(ko, COUPE_KO, FULL, CK * z, 502, 998, bx, by)
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        pts = [(x, front + math.sin(x * 0.03 / z + t * 3) * 14 * z) for x in range(0, W + 20, 20)]
        d.polygon([(0, 0), (W, 0)] + pts[::-1], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(12))
        ko.putalpha(Image.composite(ko.getchannel("A"), Image.new("L", (W, H), 0), m))
        ok.putalpha(Image.composite(Image.new("L", (W, H), 0), ok.getchannel("A"), m))
    shadow(w, bx, by, 360 * z)
    w.alpha_composite(ok)
    w.alpha_composite(ko)
    # le sel tombe sur la terre, puis s'accumule dans la terre (cristaux blancs)
    top_y = V(0, SOIL_TOP_SRC)[1]
    salt_grains(w, t, 7.5, V(525, 0)[0], top_y - 300 * z, dur=0.7, fall=300 * z)
    if t > 8.3:
        d = ImageDraw.Draw(w)
        r = np.random.default_rng(9)
        acc = ease_out((t - 9.85) / 1.0)
        n = int(20 + 160 * acc)
        x0, x1 = V(410, 0)[0], V(640, 0)[0]
        bot = V(0, ROOT_BOT_SRC)[1]
        gs = 1.6 * z
        for i in range(n):
            gy = r.uniform(top_y, max(top_y + 1, min(front, bot)))
            gx = r.uniform(x0, x1)
            if gy < front:
                d.rectangle([gx - gs, gy - gs, gx + gs, gy + gs], fill=(252, 252, 252, 235))
        if 8.3 < t < 9.9:   # le front salé
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ov).rectangle([x0, front - 7 * z, x1, front + 7 * z], fill=(255, 255, 255, 90))
            w.alpha_composite(ov.filter(ImageFilter.GaussianBlur(8)))
    if t > 8.5:
        tag(u, "RACINES POURRIES", 780, 560, t, 9.0, 10.0, rot=-5, size=48)
    if t > 9.85:
        tag(u, "SEL", 820, 560, t, 9.9, None, rot=5, size=60)
    w.alpha_composite(shade())
    title(u, "L'EAU SALÉE…", t, 7.42, 8.2, y=330, size=165)
    title(u, "ASSÈCHE LES RACINES", t, 8.25, 9.8, y=330, color=RED, size=115)
    title(u, "LE SEL S'ACCUMULE", t, 9.85, None, y=330, color=YEL, size=125)
    return w, u


cue(7.44, "whoosh", 0.16)
cue(7.55, "rustle", 0.22)
cue(8.4, "fail", 0.3)
cue(9.9, "pop", 0.22)


# ============================================================ D. SANS SEL, BIEN REFROIDIE : OUI, DE TEMPS EN TEMPS (11.2 → 14.2)
def s_cool(t):
    w, u = bg_photo(*WINDOW)
    which, sc = swap((t - 12.05) / 0.3)            # elle refroidit : plus de bouillons ni de vapeur
    s_ = life(t, 11.2, dur=0.35)
    shadow(w, 560, TABLE + 40, 600 * s_)
    if which == 0:
        steam(w, t, 560, TABLE - 360, 360, s_)
        ob(w, CASS_HOT, 560, TABLE + 40, 640 * sc, s=s_, anchor="bottom")
    else:
        ob(w, CASS, 560, TABLE + 40, 700 * sc, anchor="bottom")
    # pas de sel
    sg = life(t, 11.25, dur=0.3)
    ob(w, SEL, 175, TABLE + 40, 150, s=sg, anchor="bottom")
    put(u, icon("nosign", 230), 175, TABLE + 40 - 165, life(t, 11.45))
    if t > 12.0:
        put(u, icon("thermo", 150), 930, 760, life(t, 12.02))
        tag(u, "REFROIDIE", 880, 600, t, 12.1, None, rot=6, size=50)
    if t > 12.89:
        put(u, icon("check", 170), 560, 640, life(t, 12.9))
        tag(u, "DE TEMPS EN TEMPS", 560, 1470 - 680, t, 13.15, None, rot=-3, size=52)
    w.alpha_composite(shade())
    title(u, "SANS SEL", t, 11.22, 11.98, y=330, size=180)
    title(u, "ET REFROIDIE ?", t, 12.02, 12.85, y=330, color=YEL, size=160)
    stamp(u, "OUI !", 540, 340, t, 12.9, None, GREEN, 175, -8)
    return w, u


cue(11.24, "pop", 0.22)
cue(11.47, "alert2", 0.22)
cue(12.07, "whoosh", 0.14)
cue(12.92, "ding", 0.3)


# ============================================================ E. LE MEILLEUR : L'EAU DES LÉGUMES (14.2 → 18.1)
VEG = [("poireau/leek_full", -110, 105, -35), ("garlic_bulb_a", 5, 105, 0), ("banque/oignon", 112, 115, 15)]
MINERALS = [("K", "19", "Potassium"), ("Ca", "20", "Calcium"), ("Mg", "12", "Magnésium")]


def s_veg(t):
    w, u = bg_photo(*KITCHEN)
    s_ = life(t, 14.22, dur=0.35)
    X, Y, Wc = 540, TABLE + 40, 700
    shadow(w, X, Y, Wc * 0.8 * s_)
    k = Wc / 964
    wx, wy = X + (393 - 513) * k, Y + (432 - 835) * k   # centre de la surface de l'eau
    rim_y = wy
    # les légumes tombent dans l'eau (coupés à la surface)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, (name, dx, wv, rot) in enumerate(VEG):
        q = ease_in((t - 15.3 - i * 0.18) / 0.45)
        if q > 0:
            ob(lay, name, wx + dx, lerp(250, wy + 6, q), wv, rot=rot + 20 * q)
    m = Image.new("L", (W, H), 255)
    ImageDraw.Draw(m).rectangle([0, wy + 12, W, H], fill=0)
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m.filter(ImageFilter.GaussianBlur(5))))
    ob(w, CASS, X, Y, Wc, s=s_, anchor="bottom")
    if s_ > 0.99:   # un bouillon de légumes doré et trouble à la place des pâtes
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        rx, ry = 312 * k, 55 * k
        d.ellipse([wx - rx, wy - ry, wx + rx, wy + ry], fill=(196, 170, 96, 245))
        d.ellipse([wx - rx * 0.6, wy - ry * 0.55, wx + rx * 0.1, wy - ry * 0.05], fill=(232, 214, 150, 120))
        w.alpha_composite(ov.filter(ImageFilter.GaussianBlur(2)))
    w.alpha_composite(lay)
    if t > 15.4:
        steam(w, t, X, rim_y - 40, 380, fade(t, 15.4, None, 0.5))
    for i in range(3):
        if 15.9 + i * 0.22 < t < 16.3 + i * 0.22:
            particles(w, t, 15.9 + i * 0.22, X + VEG[i][1], rim_y + 30, 10, i, col=(200, 225, 240), size=7, up=260,
                      dur=0.4)
    # pleine de minéraux : K, Ca, Mg qui montent de l'eau
    if t > 16.7:
        for i, (sym, num, nm) in enumerate(MINERALS):
            q = ease_out((t - 16.72 - i * 0.15) / 0.5)
            if q > 0:
                put(u, mineral_tile(sym, num, nm, 170), 260 + i * 280, lerp(rim_y, 640, q), q)
        sparkles(u, t, 16.8, 540, 700, 380, 10, 9)
    w.alpha_composite(shade())
    title(u, "LE MEILLEUR ?", t, 14.25, 15.3, y=330, size=165)
    title(u, "L'EAU DES LÉGUMES !", t, 15.35, 16.6, y=330, color=YEL, size=120)
    title(u, "PLEINE DE MINÉRAUX", t, 16.72, None, y=330, color=GREEN, size=118)
    return w, u


cue(14.24, "pop", 0.22)
cue(15.62, "plop", 0.25)
cue(15.85, "plop", 0.22)
cue(16.05, "plop", 0.22)
cue(16.75, "rise", 0.22)
cue(17.0, "success", 0.28)


# ============================================================ F. LE POTHOS EN FORME + ABONNE-TOI (18.1 → fin)
def s_end(t):
    cam = Cam(1.25, 640, 900)
    w = cam.bg("fond_salon_coin2.jpg")
    draw_plant(w, t, cam)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    sparkles(u, t, 18.2, 600, 760, 330, 10, 7)
    clicked = t > 19.3
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 19.25) / 0.15))
    put(u, btn, 540, 1420, life(t, 18.3) * press)
    if t > 18.8:
        k = ease_out((t - 18.8) / 0.4)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(1650, 1460, k), 1)
    put(u, logo_img(260), 540, 330, life(t, 20.2, dur=0.45))
    sparkles(u, t, 20.3, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 18.15, 20.15, y=330, color=YEL, size=135)
    return w, u


cue(18.17, "pop_lo", 0.3)
cue(19.28, "click", 0.45)
cue(20.3, "sparkle", 0.25)

SCENES = [
    (0.0, 4.1, s_salon),
    (4.1, 7.4, s_salt),
    (7.4, 11.2, s_roots),
    (11.2, 14.2, s_cool),
    (14.2, 18.1, s_veg),
    (18.1, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
