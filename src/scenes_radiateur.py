"""Storyboard « Pointes brunes : la faute au radiateur » (voix : assets/audio/radiateur/voix.mp3).

Photos de la banque (assets/images/banque) : radiateur, calathea saine → bords secs → très sèche → morte.
Robinet mural et arrosoir : photos fournies. Billes d'argile et vapeur dessinées. Si assets/video/intro_radiateur.mp4 existe,
la première phrase montre cette vidéo brute (sans texte, son coupé) avant le motion design.
"""
import math
import os
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (ROOT, IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, spr, put, title, life, fade,
                 ease_out, ease_io, clamp, lerp, icon, num_badge, pills, tag, button_img, hl_ellipse, particles)
from scenes import TABLE, new_layers, sparkles, falling
from scenes_ananas import place, logo_img
from scenes_hortensia import stamp
from scenes_gingembre import steam

CUES = []
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


B = "banque/"
FULL = (0, 0, 1254, 1254)
VIDEO = os.path.join(ROOT, "assets", "video", "intro_radiateur.mp4")
HAS_VIDEO = os.path.exists(VIDEO)


def video_duration():
    if not HAS_VIDEO:
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                         capture_output=True, text=True).stdout
    return min(3.15, float(out.strip() or 0))


VID_END = video_duration()
NO_CAPTION_UNTIL = VID_END


@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_radiateur_intro")
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
PLANTS = {"saine": ("calathea_saine", (656, 1209)), "secs": ("calathea_bords_secs", (665, 1240)),
          "seche": ("calathea_tres_seche", (669, 1240)), "morte": ("calathea_morte", (636, 1230))}
TIPS = [(118, 525), (222, 205), (875, 45), (1188, 330), (1098, 545), (1062, 880), (272, 905)]   # bouts de feuilles
RAD_BASE = (577, 1026)


def plant(c, state, X, Y, k, s=1.0, alpha=1.0, shadow=True):
    name, base = PLANTS[state]
    if shadow and s > 0.01:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        w_ = 330 * k * s
        ImageDraw.Draw(ov).ellipse([X - w_ / 2, Y - w_ * 0.08, X + w_ / 2, Y + w_ * 0.08],
                                   fill=(70, 45, 25, int(70 * alpha)))
        c.alpha_composite(ov)
    place(c, B + name, FULL, k, *base, X, Y, s, 0.0, 0.0, alpha)


def plant_mix(c, a, b, p, X, Y, k, s=1.0):
    """Passage d'un état de la plante à l'autre (p = 0 → a, 1 → b), sans jamais superposer les deux photos :
    la plante se tasse, change d'un coup au plus petit, puis reprend sa taille (petit rebond)."""
    p = clamp(p)
    if p <= 0.0 or p >= 1.0:
        plant(c, b if p >= 1.0 else a, X, Y, k, s)
        return
    if p < 0.5:
        plant(c, a, X, Y, k, s * (1 - 0.1 * ease_io(p * 2)))
    else:
        q = (p - 0.5) * 2
        plant(c, b, X, Y, k, s * (0.9 + 0.1 * q + 0.03 * math.sin(math.pi * q)))


def tip_pos(i, state, X, Y, k):
    name, base = PLANTS[state]
    return X + (TIPS[i][0] - base[0]) * k, Y + (TIPS[i][1] - base[1]) * k


def radiator(c, X, Y, k, s=1.0):
    """Radiateur fixé au mur : le bas de son corps en (X, Y)."""
    place(c, B + "radiateur_face", FULL, k, *RAD_BASE, X, Y, s)


def heat_waves(c, x0, x1, y0, y1, t, a=1.0, n=5):
    """Ondes d'air chaud qui partent du radiateur vers la gauche."""
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(n):
        y = lerp(y0, y1, i / max(1, n - 1))
        ph = (t * 0.9 + i * 0.23) % 1.0
        xa = lerp(x0, x1, ph)
        pts = [(xa - j * 22, y + 16 * math.sin(j * 0.7 + t * 6 + i)) for j in range(14)]
        al = int(200 * a * math.sin(math.pi * ph))
        d.line(pts, fill=(240, 120, 40, al), width=10, joint="curve")
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(1.5)))


@lru_cache(None)
def clay_tray_img(w_=520, water=False):
    """Soucoupe remplie de billes d'argile (dessin), avec ou sans fond d'eau."""
    k = 2
    h_ = 150
    im = Image.new("RGBA", (w_ * k, h_ * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 40 * k, w_ * k, h_ * k - 2], fill=(60, 58, 56))
    d.rectangle([0, 50 * k, w_ * k, 105 * k], fill=(60, 58, 56))
    d.ellipse([0, 10 * k, w_ * k, 100 * k], fill=(84, 82, 78))
    d.ellipse([12 * k, 18 * k, (w_ - 12) * k, 92 * k], fill=(46, 44, 42))
    if water:
        d.ellipse([18 * k, 26 * k, (w_ - 18) * k, 88 * k], fill=(96, 150, 200))
    r = np.random.default_rng(6)
    balls = []
    for _ in range(140):
        u, v = r.uniform(-1, 1), r.uniform(-1, 1)
        if u * u + v * v > 0.92:
            continue
        balls.append((w_ / 2 + u * (w_ / 2 - 30), 55 + v * 28 - r.uniform(0, 14), r.uniform(13, 19)))
    for x, y, rad in sorted(balls, key=lambda b: b[1]):
        for j in range(6):
            f = j / 5
            rr = rad * (1 - f * 0.75)
            col = (int(lerp(140, 222, f)), int(lerp(70, 132, f)), int(lerp(40, 82, f)))
            ox, oy = -rad * 0.3 * f, -rad * 0.3 * f
            d.ellipse([(x + ox - rr) * k, (y + oy - rr) * k, (x + ox + rr) * k, (y + oy + rr) * k], fill=col)
    return im.resize((w_, h_), Image.LANCZOS)


def clay_tray(c, cx, base, s=1.0, water=False):
    if s <= 0.01:
        return
    im = clay_tray_img(520, water)
    put(c, im, cx, base - im.height / 2 + 20, s)


# ============================================================ A. LES POINTES BRUNISSENT ? (0 → 3.15)
K = 0.62


def s_intro(t):
    w, u = new_layers(background("table"))
    X, Y = 540, TABLE + 30
    p = ease_io((t - 1.18) / 0.6)
    plant_mix(w, "saine", "secs", p, X, Y, K, life(t, 0.0, dur=0.4))
    for i in (0, 1, 3, 4):
        if t > 1.3:
            tx, ty = tip_pos(i, "secs", X, Y, K)
            hl_ellipse(u, tx, ty, 50, 50, life(t, 1.35 + i * 0.07))
    put(u, icon("thermo", 140), 900, 600, life(t, 2.0))
    title(u, "POINTES BRUNES ?", t, 0.3, None, y=330, size=140)
    return w, u


cue(0.05, "pop_lo", 0.3)
cue(1.35, "pop_hi", 0.22)
cue(2.0, "rise", 0.2)


# ============================================================ B. LE COUPABLE : LE RADIATEUR (3.15 → 6.6)


def s_culprit(t):
    w, u = new_layers(background("table"))
    radiator(w, RX, RY, RK, life(t, 3.4, dur=0.4))
    plant(w, "secs", PX, TABLE + 30, PK)
    put(u, icon("question", 130), PX, 560, life(t, 3.5, 5.3))
    if t > 5.42:
        hl_ellipse(u, RX, RY - 155, 270, 185, life(t, 5.45))
        heat_haze(w, t, fade(t, 5.5, None, 0.3))
    title(u, "LE COUPABLE…", t, 3.34, 5.3, y=330, size=150)
    stamp(u, "LE RADIATEUR !", 540, 360, t, 5.42, None, RED, 115, -6)
    return w, u


cue(3.45, "pop", 0.25)
cue(5.42, "thud", 0.4)
cue(5.48, "alert1", 0.35)


# ============================================================ C-D-E. UNE SEULE SCÈNE, LA CAMÉRA GLISSE (6.6 → 16.15)
# décor unique plus large que l'écran : robinet mural à gauche (hors champ), plante et radiateur au centre.
# la caméra glisse vers le robinet puis revient sur la plante en emportant l'arrosoir : aucune coupure.
PX, PK = 540, 0.5                    # plante
RX, RY, RK = 870, TABLE - 50, 0.38   # radiateur
TAP = "banque/robinet_mural"
TAP_K = 0.42
TAP_INLET, TAP_NOZZLE = (150, 630), (950, 1190)     # filetage (dans le mur) / bout du tuyau (robinet_mural.png)
CAN = "banque/arrosoir_zinc"
CAN_K = 0.4
CAN_BASE, CAN_OPEN, CAN_ROSE = (815, 1150), (1000, 450), (110, 430)   # arrosoir_zinc.png
CAM_TAP = -1000                      # décalage caméra quand on regarde le robinet
NOZ_W = (CAM_TAP + 640, 880)         # bout du robinet (coordonnées du décor)
CAN_W = (NOZ_W[0] - (CAN_OPEN[0] - CAN_BASE[0]) * CAN_K, TABLE + 30)   # arrosoir posé, ouverture sous le robinet
TIP_I = 4                            # pointe de feuille montrée à la loupe (TIPS[4], tournée vers la droite)


def cam_x(t):
    go = ease_io((t - 9.45) / 0.5)
    back = ease_io((t - 10.95) / 0.55)
    return CAM_TAP * go * (1 - back)


def heat_haze(c, t, a):
    """Brume de chaleur douce : bandes orangées floues qui glissent du radiateur vers la plante."""
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W // 2, H // 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(4):
        ph = (t * 0.45 + i * 0.25) % 1.0
        x1 = lerp(RX - 120, PX - 160, ph) / 2
        y = (RY - 330 + i * 70) / 2
        pts = [(x1 + j * 12, y + 10 * math.sin(j * 0.5 + t * 3 + i)) for j in range(26)]
        d.line(pts, fill=(245, 130, 50, int(170 * a * math.sin(math.pi * ph))), width=16, joint="curve")
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(7)).resize((W, H), Image.BICUBIC))


def wall_tap(c, cx):
    """Robinet mural en grand ; son filetage rentre dans une rosace fixée au mur."""
    nx = NOZ_W[0] - cx
    if nx < -700 or nx > W + 700:
        return
    ix = nx + (TAP_INLET[0] - TAP_NOZZLE[0]) * TAP_K
    iy = NOZ_W[1] + (TAP_INLET[1] - TAP_NOZZLE[1]) * TAP_K
    d = ImageDraw.Draw(c)
    d.ellipse([ix - 40, iy - 95, ix + 40, iy + 95], fill=(196, 196, 192), outline=(140, 140, 136), width=5)
    place(c, TAP, FULL, TAP_K, *TAP_NOZZLE, nx, NOZ_W[1])


def stream(c, x, y0, y1, t, a=1.0):
    """Filet d'eau continu qui tombe du robinet."""
    if a <= 0.01 or y1 <= y0:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    pts = [(x + 3 * math.sin(yy * 0.05 + t * 20), yy) for yy in range(int(y0), int(y1), 8)]
    if len(pts) > 1:
        d.line(pts, fill=(110, 175, 230, int(220 * a)), width=22, joint="curve")
        d.line([(px - 5, py) for px, py in pts], fill=(225, 242, 252, int(230 * a)), width=5)
    c.alpha_composite(ov)


def tip_specks(c, X, Y, k, acc, state="seche"):
    """Calcaire : points blancs qui s'accumulent au bout des feuilles."""
    if acc <= 0.01:
        return
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(2)
    for i in range(len(TIPS)):
        px, py = tip_pos(i, state, X, Y, k)
        for j in range(14):
            ox, oy, rad = r.normal(0, 13), r.normal(0, 11), r.uniform(4, 8)
            if j < 14 * acc:
                d.ellipse([px + ox - rad, py + oy - rad, px + ox + rad, py + oy + rad], fill=(250, 250, 246),
                          outline=(200, 200, 196))


def can_at(c, base_x, base_y, rot=0.0, s=1.0, alpha=1.0):
    place(c, CAN, FULL, CAN_K, *CAN_BASE, base_x, base_y, s, rot, 0.0, alpha)


def can_rose(base_x, base_y, rot):
    """Position écran de la pomme de l'arrosoir posé en (base_x, base_y) et tourné de rot° (sens PIL)."""
    cx = base_x + (627 - CAN_BASE[0]) * CAN_K
    cy = base_y + (627 - CAN_BASE[1]) * CAN_K
    vx, vy = (CAN_ROSE[0] - 627) * CAN_K, (CAN_ROSE[1] - 627) * CAN_K
    a = math.radians(rot)
    return cx + vx * math.cos(a) + vy * math.sin(a), cy - vx * math.sin(a) + vy * math.cos(a)


@lru_cache(8)
def tip_zoom(burn_q):
    """Gros plan rond sur une pointe de feuille (photo très sèche), qui brunit avec burn."""
    name, base = PLANTS["seche"]
    src = Image.open(os.path.join(IMG, B + name + ".png")).convert("RGBA")
    tx, ty = TIPS[TIP_I]
    r = 120
    crop = src.crop((tx - 40 - r, ty + 5 - r, tx - 40 + r, ty + 5 + r)).resize((340, 340), Image.LANCZOS)
    S = 380
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, S - 1, S - 1], fill=DARK)
    d.ellipse([10, 10, S - 11, S - 11], fill=CREAM)
    m = Image.new("L", (340, 340), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 339, 339], fill=255)
    inner = Image.new("RGBA", (340, 340), CREAM + (255,))
    inner.alpha_composite(crop)
    if burn_q:
        # la pointe (côté gauche du gros plan) devient brun foncé
        b = Image.new("L", (340, 340), 0)
        ImageDraw.Draw(b).ellipse([150, 80, 360, 260], fill=int(235 * burn_q / 10))
        b = b.filter(ImageFilter.GaussianBlur(28))
        brown = Image.new("RGBA", (340, 340), (92, 52, 22, 255))
        a = np.minimum(np.asarray(b), np.asarray(crop.getchannel("A")))
        brown.putalpha(Image.fromarray(a.astype("uint8")))
        inner.alpha_composite(brown)
    im.paste(inner, (20, 20), m)
    return im


def s_middle(t):
    w, u = new_layers(background("table"))
    cx = cam_x(t)
    # --- décor : radiateur + plante (dans le repère du décor, décalé par la caméra)
    radiator(w, RX - cx, RY, RK)
    heat_haze(w, t, fade(t, 6.9, 9.3, 0.5, 0.4))
    if t < 13.3:
        sa, sb, p = "secs", "seche", ease_io((t - 8.0) / 1.2)
    else:
        sa, sb, p = "seche", "morte", ease_io((t - 13.3) / 0.6)
    X = lerp(PX, 230, ease_io((t - 14.86) / 0.7)) - cx
    # --- robinet mural (hors champ à gauche au début)
    wall_tap(w, cx)
    # --- arrosoir : posé sous le robinet, rempli, puis emporté au-dessus du pot
    carry = ease_io((t - 10.95) / 0.6)
    tilt = ease_out((t - 11.45) / 0.35) * (1 - ease_io((t - 12.75) / 0.3))
    pose = (X + 330, TABLE - 230)                          # au-dessus, à droite du pot
    bx = lerp(CAN_W[0] - cx, pose[0], carry)
    by = lerp(CAN_W[1], pose[1], carry) - math.sin(math.pi * carry) * 120
    can_a = 1 - fade(t, 13.0, None, 0.35)
    plant_mix(w, sa, sb, p, X, TABLE + 30, PK)
    if t > 9.3 and can_a > 0.01:
        rot = 32 * tilt
        if 10.0 < t < 10.95:
            nx = NOZ_W[0] - cx
            stream(w, nx, NOZ_W[1] + 4, CAN_W[1] - (CAN_BASE[1] - CAN_OPEN[1]) * CAN_K + 10, t,
                   fade(t, 10.0, 10.9, 0.08, 0.15))
            particles(w, t, 10.05, nx, CAN_W[1] - (CAN_BASE[1] - CAN_OPEN[1]) * CAN_K, 6, 3, col=(200, 230, 250),
                      size=8, up=120, dur=0.85)
        can_at(w, bx, by, rot, life(t, 9.4, dur=0.35), can_a)
        if tilt > 0.3:
            rx_, ry_ = can_rose(bx, by, rot)
            soil = (X, TABLE + 30 - 300 * PK)
            r = np.random.default_rng(4)
            d = ImageDraw.Draw(w)
            for i in range(18):
                ph = ((t - 11.5) * 1.6 + i / 18) % 1
                x = lerp(rx_, soil[0] + r.uniform(-60, 60), ph)
                y = lerp(ry_, soil[1], ph ** 1.3)
                rad = r.uniform(5, 8)
                d.ellipse([x - rad, y - rad * 1.3, x + rad, y + rad * 1.3], fill=(90, 165, 225, 230),
                          outline=(225, 242, 252, 255), width=2)
    # --- calcaire : petits dépôts blancs au bout des feuilles + loupe sur une pointe
    if 11.7 < t < 14.3:
        acc = ease_out((t - 11.75) / 1.3)
        tip_specks(w, X, TABLE + 30, PK, acc * (1 - p if t >= 13.3 else 1))
        burn = ease_io((t - 13.3) / 0.6)
        zx, zy = 830, 600
        zs = life(t, 11.8, 14.25)
        if zs > 0.01:
            z = tip_zoom(int(round(burn * 10))).copy()
            dz = ImageDraw.Draw(z)
            rr = np.random.default_rng(9)
            for j in range(int(40 * acc * (1 - burn))):
                ox, oy, rad = rr.normal(222, 26), rr.normal(176, 18), rr.uniform(5, 10)
                dz.ellipse([ox - rad, oy - rad, ox + rad, oy + rad], fill=(252, 252, 248), outline=(205, 205, 200))
            tx, ty = tip_pos(TIP_I, sa, X, TABLE + 30, PK)
            dl = ImageDraw.Draw(u)
            dl.line([(tx, ty), (zx - 60 * zs, zy + 175 * zs)], fill=DARK + (200,), width=5)
            put(u, z, zx, zy, zs)
            tag(u, "CALCAIRE" if t < 13.26 else "BRÛLURE", 470, 560, t, 12.0, 14.2, rot=-4, size=50)
    # --- icônes
    put(u, icon("thermo", 130), RX - 80 - cx, 640, life(t, 6.95, 9.4))
    if t > 7.38:
        put(u, icon("drop", 100), RX + 90 - cx, 640, life(t, 7.4, 9.4))
        put(u, icon("nosign", 150), RX + 90 - cx, 640, life(t, 7.45, 9.4))
    if 7.74 < t < 9.45:   # la plante transpire
        for i in range(6):
            tt = (t - 7.8 - i * 0.2) % 1.1
            put(w, icon("drop", 36), X - 160 + i * 64, TABLE - 420 - tt * 260, 1, 0, (1 - tt / 1.1) * 0.9)
    if t > 14.9:
        d = ImageDraw.Draw(u)
        a = int(255 * fade(t, 15.3, None, 0.2))
        for i in range(0, 12, 2):
            x0 = 420 + i * 30
            d.line([(x0, TABLE - 120), (x0 + 30, TABLE - 120)], fill=(255, 255, 255, a), width=8)
        tag(u, "LOIN DU RADIATEUR", 540, 640, t, 15.35, None, rot=-4, size=50)
    title(u, "AIR CHAUD ET SEC", t, 6.86, 7.7, y=330, size=140)
    title(u, "ELLE BOIT PLUS VITE", t, 7.74, 9.4, y=330, color=YEL, size=125)
    title(u, "L'EAU DU ROBINET…", t, 9.54, 10.9, y=330, size=135)
    title(u, "LE CALCAIRE", t, 10.98, 13.2, y=330, color=YEL, size=160)
    title(u, "BRÛLE LES FEUILLES", t, 13.26, 14.3, y=330, color=RED, size=125)
    title(u, "ÉLOIGNE-LA !", t, 14.46, None, y=330, color=YEL, size=165)
    return w, u


cue(7.0, "rise", 0.18)
cue(7.45, "pop", 0.2)
cue(9.5, "whoosh", 0.18)
cue(9.88, "squeak", 0.22)
cue(10.02, "pour", 0.3)
cue(11.0, "whoosh", 0.16)
cue(11.5, "pour", 0.22)
cue(11.85, "pop_hi", 0.2)
cue(13.35, "fail", 0.38)
cue(14.9, "whoosh", 0.2)


# ============================================================ F. PLATEAU DE BILLES D'ARGILE + FOND D'EAU (16.15 → 20.85)
def s_tray(t):
    w, u = new_layers(background("table"))
    X = 540
    water = t > 18.46
    clay_tray(w, X, TABLE + 40, life(t, 16.8), water=False)
    if water:
        # le fond d'eau monte entre les billes
        a = ease_out((t - 18.46) / 0.4)
        im = clay_tray_img(520, True).copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
        put(w, im, X, TABLE + 40 - im.height / 2 + 20, 1.0)
    drop = ease_out((t - 17.3) / 0.45)
    if t > 17.2:
        if t < 19.6:
            plant(w, "morte", X, lerp(TABLE - 600, TABLE - 20, drop), 0.55, shadow=False)
        else:
            plant_mix(w, "morte", "saine", ease_io((t - 19.6) / 0.8), X, TABLE - 20, 0.55)
    if t > 18.9:
        steam(u, t, X, TABLE - 60, fade(t, 18.9, None, 0.4))
        a = fade(t, 18.9, None, 0.4)
        for i in range(10):
            tt = (t * 0.7 + i * 0.13) % 1.0
            x = X - 300 + (i * 67) % 600
            put(u, icon("drop", 34), x + 14 * math.sin(t * 3 + i), TABLE - 40 - tt * 620, 1, 0, a * math.sin(math.pi * tt))
        sparkles(u, t, 19.7, X, 760, 360, 9, 4)
    if t > 18.46:
        tag(u, "FOND D'EAU", 860, TABLE - 40, t, 18.5, None, rot=5, size=50, string_to=(X + 200, TABLE + 30))
    title(u, "BILLES D'ARGILE", t, 16.26, 18.4, y=330, size=150)
    title(u, "+ UN FOND D'EAU", t, 18.46, 18.85, y=330, color=YEL, size=145)
    title(u, "L'AIR EST HUMIDE", t, 18.9, None, y=330, color=YEL, size=140)
    return w, u


cue(16.85, "crunch", 0.3)
cue(17.7, "thud", 0.3)
cue(18.5, "pour", 0.25)
cue(19.7, "sparkle", 0.3)


# ============================================================ G. ARROSE À L'EAU DE PLUIE (20.85 → 22.55)
CAN_RAIN = "banque/arrosoir_zinc"


def s_rain(t):
    w, u = new_layers(background("table"))
    falling(w, t, 20.9, None, "drop", 22, 7, 1300, 46, bottom=TABLE)
    plant(w, "saine", 330, TABLE + 30, 0.5)
    spr(w, CAN_RAIN, 800, TABLE + 30, 380, life(t, 21.1))
    put(u, icon("check", 140), 800, 620, life(t, 21.7))
    title(u, "ARROSE À L'EAU DE PLUIE", t, 20.9, None, y=330, size=105)
    return w, u


cue(20.95, "rain", 0.25)
cue(21.75, "ding", 0.25)


# ============================================================ H. CTA (22.55 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    plant(w, "saine", 260, TABLE + 30, 0.42, life(t, 22.6))
    clay_tray(w, 820, TABLE + 40, 0.55 * life(t, 22.7), water=True)
    clicked = t > 23.2
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 23.15) / 0.15))
    put(u, btn, 540, 300, life(t, 22.65) * press)
    if t > 22.85:
        k = ease_out((t - 22.85) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(330), 540, 590, life(t, 24.4, dur=0.45))
    sparkles(u, t, 24.5, 540, 590, 230, 10, 12)
    return w, u


cue(23.18, "click", 0.45)
cue(24.5, "sparkle", 0.25)

if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video), (VID_END, 3.15, s_intro)]
else:
    _intro = [(0.0, 3.15, s_intro)]

SCENES = _intro + [
    (3.15, 6.6, s_culprit),
    (6.6, 16.15, s_middle),
    (16.15, 20.85, s_tray),
    (20.85, 22.55, s_rain),
    (22.55, 99.0, s_cta),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []

if HAS_VIDEO:
    CUES[:] = [c for c in CUES if c[0] >= VID_END - 0.05]
