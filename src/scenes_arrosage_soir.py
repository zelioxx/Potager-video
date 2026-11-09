"""Storyboard « Arroser le soir en hiver : la pire idée » (voix : assets/audio/arrosage_soir/voix.mp3).

Le volume de la voix est gardé tel qu'envoyé (aucun mastering, cf. render.py « af ») ; les bruitages restent
nettement sous la voix (SFX_GAIN bas, ducking plus fort pendant qu'elle parle).
Décor : le grand salon fourni (decor_salon_table_fenetre.jpg), le pothos posé sur la table devant la porte-fenêtre.
0–7.95   le salon en plein jour → « le soir » : la lumière vire à l'orange, on arrose ; « en hiver » : il neige
         dehors ; « la pire idée ! ». « La nuit » : le salon passe en nuit bleue, lune et fenêtres allumées en face,
         la plante dort (Zzz) et ne boit pas. « Tu baisses le chauffage » : la caméra glisse vers le radiateur,
         le thermostat tourne, 21 °C → 16 °C, le froid gagne la pièce.
7.95–14.45 la nuit, le pot coupé en deux (photos fournies) : l'eau froide stagne autour des racines jusqu'au
         matin (horloge) ; « résultat » : les racines pourrissent (saines → pourries), la plante se dessèche,
         les moucherons sortent de la terre (et leurs larves).
14.45–19.6 le matin : le soleil entre, on arrose avec de l'eau à 20 °C ; elle boit pendant la journée, à la lumière.
19.6–fin bouton S'abonner et logo.
"""
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, put, title, life, fade, ease_out, ease_io, ease_in,
                 clamp, lerp, icon, tag, button_img, particles, text_img, F_TITLE, F_BLACK, aa)
from scenes import sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp
from scenes_citron import photo, shade, zoomed, shadow, swap
from scenes_banane import ob
from scenes_moucherons import gnat, swarm_pos

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles

# bruitages discrets : nettement sous la voix (TikTok baisse le son quand les effets sont trop présents)
SFX_GAIN = 0.34
DUCK = 0.5
TRANS_GAIN = 0.22


SHIFT = 0.25                                     # les temps ci-dessous suivent la reconnaissance vocale, ~0,25 s en retard


def cue(t, name, gain=0.5):
    CUES.append((t - SHIFT, name, gain))


SALON = "decor_salon_table_fenetre.jpg"
SX, SY = W / 768, H / 1376                       # photo d'origine (768 × 1376) → écran


def P(x, y):
    return x * SX, y * SY


SAIN, SEC = "banque/pothos_sain", "banque/pothos_sec"
COUPE_OK, COUPE_KO = "banque/pothos_coupe_racines_saines", "banque/pothos_coupe_racines_pourries"
CAN, MOON, LARVE = "banque/arrosoir_zinc", "banque/lune_pleine", "banque/larve_blanche"
FULL = (0, 0, 1024, 1024)
POT_BASE = (525, 985)                            # bas du pot dans les photos du pothos (cadre 1024)
PLANT = P(518, 804)                              # bas du pot, sur la table (devant la porte-fenêtre)
PK = 0.6                                         # échelle du pothos (cadre 1024 → écran, zoom 1)
SOIL_IN = [(418, 786), (612, 779), (609, 948), (598, 956), (428, 956), (419, 946)]   # terre du pot coupé (cadre)

# vitres de la porte-fenêtre (photo d'origine) : ce qui est dehors
PANES = [[(486, 329), (592, 311), (592, 778), (486, 778)],
         [(625, 300), (742, 282), (742, 832), (688, 830), (688, 778), (625, 778)]]
LIT = [(515, 337, 545, 370), (507, 418, 535, 460), (505, 628, 532, 675)]                     # fenêtres de l'immeuble d'en face qui s'allument la nuit
MOON_P = (713, 318)
RADIATOR = P(108, 840)                           # milieu du radiateur en fonte (à gauche)


# ============================================================ ÉCLAIRAGE : JOUR → SOIR → NUIT → MATIN
@lru_cache(None)
def _base():
    return np.asarray(photo(SALON).convert("RGB"), np.float32) / 255.0


@lru_cache(None)
def _win():
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for poly in PANES:
        d.polygon([P(*p) for p in poly], fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(1.5)), np.float32)[..., None] / 255.0


@lru_cache(None)
def _moonlit():
    """La nuit, un peu de lumière (lune + lampe de la rue) éclaire encore la table et la plante."""
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    px, py = PLANT
    d2 = ((xx - px) / 520) ** 2 + ((yy - py + 260) / 640) ** 2
    return (1.0 + 0.85 * np.exp(-d2))[..., None]


EVE = np.array([0.6, 0.65, 0.82], np.float32)             # soir d'hiver : lumière froide, grise et bleutée
EVE_OUT = np.array([0.3, 0.4, 0.74], np.float32)          # dehors : l'heure bleue
NIGHT_IN = np.array([0.26, 0.33, 0.55], np.float32)        # pièce dans la nuit (bleu)
NIGHT_OUT = np.array([0.10, 0.14, 0.34], np.float32)       # dehors, plus sombre
MORNING = np.array([1.06, 1.0, 0.88], np.float32)          # matin doré
COLD = np.array([0.86, 0.94, 1.12], np.float32)            # le froid (chauffage baissé)


def light_mul(eve, night, morn, cold, lit=1.0):
    m = np.ones(3, np.float32)
    m = m * (1 + eve * (EVE - 1))
    m = m * (1 + morn * (MORNING - 1))
    m = m * (1 + cold * (COLD - 1))
    return m, (1 + night * (NIGHT_IN * lit - 1))


@lru_cache(64)
def graded_bg(qe, qn, qm, qc):
    eve, night, morn, cold = qe / 24, qn / 24, qm / 24, qc / 24
    a = _base()
    m, _ = light_mul(eve, night, morn, cold)
    a = a * m
    lum = a.mean(2, keepdims=True)
    des = 0.4 * eve + 0.3 * night                          # couleurs éteintes du soir d'hiver
    a = a * (1 - des) + lum * des
    inside = a * (1 + night * (NIGHT_IN[None, None] * _moonlit() - 1))
    out = a * (1 + eve * (EVE_OUT / EVE - 1)) * (1 + night * (NIGHT_OUT - 1))
    wm = _win()
    a = inside * (1 - wm) + out * wm
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    if night + eve > 0.02:   # en face, des fenêtres s'allument ; la lune dans le ciel
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for i, (x0, y0, x1, y1) in enumerate(LIT):
            a_ = clamp(max(night * 1.6, eve * 1.1) - i * 0.12)
            (X0, Y0), (X1, Y1) = P(x0, y0), P(x1, y1)
            d.rectangle([X0, Y0, X1, Y1], fill=(255, 196, 110, int(150 * a_)))
        glow = ov.filter(ImageFilter.GaussianBlur(10))
        ov = Image.alpha_composite(glow, ov.filter(ImageFilter.GaussianBlur(1.2)))
        mx, my = P(*MOON_P)
        mg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(mg).ellipse([mx - 46, my - 46, mx + 46, my + 46], fill=(200, 215, 255, int(110 * night)))
        ov.alpha_composite(mg.filter(ImageFilter.GaussianBlur(16)))
        ob(ov, MOON, mx, my, 40, alpha=night)
        wmask = Image.fromarray((_win()[..., 0] * 255).astype(np.uint8))
        ov.putalpha(Image.composite(ov.getchannel("A"), Image.new("L", (W, H), 0), wmask))
        im.alpha_composite(ov)
    return im


def q24(x):
    return int(round(clamp(x) * 24))


def tint_layer(lay, eve, night, morn=0.0, cold=0.0, lit=1.75):
    """Même éclairage sur les objets ajoutés (plante, arrosoir…) que sur le décor."""
    if eve + night + morn + cold < 0.01:
        return lay
    m, n = light_mul(eve, night, morn, cold, lit)
    a = np.asarray(lay, np.float32)
    rgb = a[..., :3] * (m * n)
    des = 0.4 * eve + 0.3 * night
    rgb = rgb * (1 - des) + rgb.mean(2, keepdims=True) * des
    a[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


class Cam:
    """Le décor est recadré (z, fx, fy) ; les objets sont dessinés après, à la bonne taille (k × z), bien nets."""

    def __init__(self, z, fx, fy):
        self.z = z
        cw, ch = W / z, H / z
        self.x0 = min(max(fx - cw / 2, 0), W - cw)
        self.y0 = min(max(fy - ch / 2, 0), H - ch)
        self.fx, self.fy = fx, fy

    def p(self, x, y):
        return (x - self.x0) * self.z, (y - self.y0) * self.z

    def bg(self, eve, night, morn=0.0, cold=0.0):
        return zoomed(graded_bg(q24(eve), q24(night), q24(morn), q24(cold)), self.z, self.fx, self.fy).copy()


def snow(c, cam, t, a):
    """Neige qui tombe dehors, seulement derrière les vitres."""
    if a <= 0.01:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    r = np.random.default_rng(11)
    for _ in range(90):
        poly = PANES[r.integers(0, 2)]
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        sp = r.uniform(40, 90)
        x = r.uniform(min(xs), max(xs)) + math.sin(t * 1.5 + r.uniform(0, 6)) * 5
        y = min(ys) + (r.uniform(0, 900) + t * sp) % (max(ys) - min(ys))
        X, Y = cam.p(*P(x, y))
        s = r.uniform(1.2, 2.8) * cam.z
        d.ellipse([X - s, Y - s, X + s, Y + s], fill=(255, 255, 255, int(230 * a)))
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon([cam.p(*P(*p)) for p in PANES[0]], fill=255)
    ImageDraw.Draw(m).polygon([cam.p(*P(*p)) for p in PANES[1]], fill=255)
    lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
    c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(0.6)))


def pothos(c, name, X, Y, k, s=1.0, rot=0.0):
    place(c, name, FULL, k, *POT_BASE, X, Y, s, rot)


def soil_pt(cam):
    """Terre du pot (entre les feuilles), à l'écran."""
    x, y = PLANT
    return cam.p(x + (-5) * PK, y + (-205) * PK)


def watering(c, t, a, rose, ground, s=1.0):
    """Pomme d'arrosoir : fins jets en gerbe (paraboles), reflets qui filent, gouttes et éclaboussures."""
    if a <= 0.01:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    g = 1900.0 * s
    r = np.random.default_rng(11)
    for k in range(22):
        q = k / 21
        x0 = rose[0] + lerp(14, -14, q) * s + r.uniform(-3, 3) * s
        y0 = rose[1] + lerp(-22, 22, q) * s + r.uniform(-3, 3) * s
        ang = math.radians(lerp(18, 72, q) + r.uniform(-5, 5))
        v = r.uniform(250, 330) * s
        vx, vy = v * math.cos(ang), v * math.sin(ang)
        tau_end = (-vy + math.sqrt(vy * vy + 2 * g * max(1.0, ground - y0))) / g
        pts = []
        for i in range(19):
            tau = tau_end * i / 18
            pts.append((x0 + vx * tau + math.sin(t * 40 + k * 1.7 + i * 0.9) * 1.2 * s * i / 18,
                        y0 + vy * tau + 0.5 * g * tau * tau))
        d.line(pts, fill=(200, 224, 244, int(115 * a)), width=max(2, int((2 if k % 3 else 3) * s)), joint="curve")
        for j in range(2):
            ph = (t * 3.0 + k * 0.37 + j * 0.5) % 1.0
            i0 = int(ph * 16)
            d.line(pts[i0:i0 + 3], fill=(250, 253, 255, int(200 * a)), width=max(2, int(3 * s)))
    for k in range(24):
        p = (t * 3.4 + k * 0.161) % 1.0
        ang = math.radians(200 + (k * 47) % 140)
        sx = rose[0] + 10 * s + ((k * 29) % 15) * 7 * s
        x = sx + math.cos(ang) * 30 * s * p
        y = ground - 4 + math.sin(ang) * 22 * s * p + 44 * s * p * p
        rr = (2.4 * (1 - p) + 0.8) * s
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(228, 240, 252, int(180 * a * (1 - p))))
    c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(0.6)))


CAN_S = 0.6                                      # arrosoir à l'échelle du pothos (largeur 420 → 250 px)


def can_and_water(c, cam, t, t_in, t_pour, t_end):
    """L'arrosoir arrive de la gauche, s'incline au-dessus du pot, verse, repart."""
    if not (t_in < t < t_end + 0.35):
        return
    s = CAN_S * cam.z
    sx, sy = soil_pt(cam)
    cin = ease_out((t - t_in) / 0.35)
    cout = ease_in((t - t_end) / 0.3)
    tilt = -28 * ease_io((t - t_pour + 0.25) / 0.25) * (1 - cout)
    cx = lerp(-400, sx - 224 * s, cin) - 700 * cout
    cy = sy - 156 * s - 230 * s * (1 - cin)
    ob(c, CAN, cx, cy, 420 * s, rot=tilt, flip=True)
    rose = (cx + 188 * s, cy + 10 * s)
    watering(c, t, fade(t, t_pour, t_end, 0.06, 0.1), rose, sy - 4, s)


def wet(c, cam, k, cold=0.0):
    """La terre du pot mouillée (plus sombre et brillante) ; bleutée si l'eau est froide."""
    if k <= 0.01:
        return
    sx, sy = soil_pt(cam)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rx, ry = 95 * PK * cam.z, 34 * PK * cam.z
    d = ImageDraw.Draw(ov)
    d.ellipse([sx - rx, sy - ry, sx + rx, sy + ry], fill=(10, 8, 6, int(110 * k)))
    d.ellipse([sx - rx * 0.5, sy - ry * 0.55, sx + rx * 0.2, sy - ry * 0.1],
              fill=(int(lerp(230, 170, cold)), int(lerp(235, 205, cold)), 255, int(70 * k)))
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(5 * cam.z)))


@lru_cache(None)
def z_img(size):
    return text_img("Z", F_TITLE, size, CREAM, stroke=max(3, size // 14), stroke_fill=DARK)


@lru_cache(None)
def thermo_cold(size):
    """Thermomètre bleu (eau froide)."""
    a = np.asarray(icon("thermo", size)).copy()
    red = (np.abs(a[..., 0].astype(int) - RED[0]) < 30) & (np.abs(a[..., 1].astype(int) - RED[1]) < 30)
    a[red, 0], a[red, 1], a[red, 2] = BLUE
    return Image.fromarray(a, "RGBA")


def zzz(c, x, y, t, t0, t1):
    """La plante dort : des Z qui montent."""
    if not (t0 < t < t1 + 0.3):
        return
    a_all = fade(t, t0, t1, 0.25, 0.3)
    for i in range(3):
        p = ((t - t0) * 0.55 + i / 3) % 1.0
        sz = int(46 + 40 * p)
        put(c, z_img(sz), x + 60 * p + math.sin(t * 3 + i) * 12, y - 230 * p, 1.0, rot=-10,
            alpha=a_all * math.sin(math.pi * p) ** 0.6)


def thermostat(c, x, y, r, val, a=1.0):
    """Tête thermostatique de radiateur vue de face : graduations 1 → 5, repère en haut."""
    if a <= 0.01:
        return
    S = int(r * 2.6)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = S / 2
    d.ellipse([o - r - 10, o - r - 4, o + r + 10, o + r + 16], fill=(20, 24, 30, 90))
    d.ellipse([o - r, o - r, o + r, o + r], fill=(246, 246, 242), outline=DARK, width=6)
    for i in range(36):   # stries de préhension
        ang = i * 10
        ax, ay = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        d.line([(o + ax * r * 0.86, o + ay * r * 0.86), (o + ax * r * 0.97, o + ay * r * 0.97)], fill=(190, 190, 186),
               width=4)
    d.ellipse([o - r * 0.26, o - r * 0.26, o + r * 0.26, o + r * 0.26], fill=(230, 230, 226), outline=(190, 190, 186),
              width=3)
    labels = ["❄", "1", "2", "3", "4", "5"]
    for i, lb in enumerate(labels):   # la molette tourne : la valeur choisie passe sous le repère du haut
        ang = math.radians(-90 + (i - val) * 42)
        tx, ty = o + math.cos(ang) * r * 0.6, o + math.sin(ang) * r * 0.6
        ti = text_img(lb if lb != "❄" else "*", F_BLACK, int(r * 0.3), BLUE if i == 0 else DARK)
        im.alpha_composite(ti, (int(tx - ti.width / 2), int(ty - ti.height / 2)))
    d.polygon([(o - 16, o - r - 30), (o + 16, o - r - 30), (o, o - r - 4)], fill=RED)
    put(c, im, x, y, 1.0, alpha=a)


def clock(c, x, y, r, hours, a=1.0):
    if a <= 0.01:
        return
    S = int(r * 2.4)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = S / 2
    d.ellipse([o - r - 8, o - r, o + r + 8, o + r + 14], fill=(0, 0, 0, 80))
    d.ellipse([o - r, o - r, o + r, o + r], fill=CREAM, outline=DARK, width=max(5, r // 12))
    for i in range(12):
        ang = math.radians(i * 30)
        d.line([(o + math.sin(ang) * r * 0.78, o - math.cos(ang) * r * 0.78),
                (o + math.sin(ang) * r * 0.9, o - math.cos(ang) * r * 0.9)], fill=DARK, width=max(3, r // 20))
    hm = math.radians(hours * 30)
    mm = math.radians((hours % 1) * 360)
    d.line([(o, o), (o + math.sin(hm) * r * 0.5, o - math.cos(hm) * r * 0.5)], fill=DARK, width=max(6, r // 9))
    d.line([(o, o), (o + math.sin(mm) * r * 0.75, o - math.cos(mm) * r * 0.75)], fill=RED, width=max(4, r // 14))
    d.ellipse([o - 8, o - 8, o + 8, o + 8], fill=DARK)
    put(c, im, x, y, 1.0, alpha=a)


# ============================================================ A. LE SALON : LE SOIR, LA NUIT, LE CHAUFFAGE (0 → 7.95)
CAM_DAY = (1.12, 640, 1000)
CAM_NIGHT = (1.22, 680, 960)
CAM_RAD = (1.45, 330, 1110)
CAM_RAD2 = (1.52, 330, 1110)
T_RAD = 6.35                                     # coupe franche sur le radiateur


def s_salon(t):
    if t < T_RAD:   # une seule lente avancée vers la plante
        cam = Cam(*[lerp(a, b, clamp(t / T_RAD)) for a, b in zip(CAM_DAY, CAM_NIGHT)])
    else:
        cam = Cam(*[lerp(a, b, clamp((t - T_RAD) / 1.6)) for a, b in zip(CAM_RAD, CAM_RAD2)])
    eve = fade(t, 1.25, None, 0.8) * (1 - fade(t, 4.1, None, 0.6))
    night = fade(t, 4.1, None, 0.7)
    cold = fade(t, 7.0, None, 0.8)
    w = cam.bg(eve, night, 0.0, cold)
    snow(w, cam, t, fade(t, 2.0, None, 0.4) * (1 - 0.3 * night))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px, py = cam.p(*PLANT)
    shadow(lay, px, py, 230 * cam.z, 80)
    pothos(lay, SAIN, px, py, PK * cam.z)
    wet(lay, cam, fade(t, 1.4, None, 0.6), cold=night)
    can_and_water(lay, cam, t, 0.45, 1.0, 2.55)
    w.alpha_composite(tint_layer(lay, eve, night, 0.0, cold))
    # « la pire idée » : petit flash rouge
    if 2.9 < t < 3.3:
        w.alpha_composite(Image.new("RGBA", (W, H), (224, 76, 62, int(70 * (1 - (t - 2.9) / 0.4)))))
    # la nuit : la plante dort et ne boit (presque) pas
    zzz(u, px + 120 * cam.z, py - 560 * PK * cam.z, t, 4.7, 6.35)
    if 5.3 < t < 6.6:
        sx, sy = soil_pt(cam)
        a_ = life(t, 5.35, 6.35)
        put(u, icon("drop", 150), sx - 250, sy - 40, a_)
        put(u, icon("nosign", 190), sx - 250, sy - 30, a_)
    # le chauffage : la chaleur s'éteint, la molette tourne, la température chute
    if t > 6.3:
        rx, ry = cam.p(*RADIATOR)
        heat = fade(t, 6.3, 7.3, 0.2, 0.5)
        if heat > 0.01:
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            for i in range(7):
                x = rx - 140 + i * 46
                pts = [(x + math.sin(t * 7 + i + j * 0.6) * 10, ry - 250 - j * 22) for j in range(12)]
                d.line(pts, fill=(255, 170, 90, int(120 * heat)), width=8)
            w.alpha_composite(ov.filter(ImageFilter.GaussianBlur(6)))
        val = lerp(4, 1, ease_io((t - 6.95) / 0.6))
        thermostat(u, 760, 900, 150, val, life(t, 6.55))
        if t > 7.0:
            deg = int(round(lerp(21, 16, ease_io((t - 7.05) / 0.6))))
            put(u, thermo_cold(150) if deg < 19 else icon("thermo", 150), 700, 1230, life(t, 7.02))
            put(u, text_img(f"{deg}°C", F_TITLE, 120, BLUE if deg < 19 else RED, stroke=7, stroke_fill=DARK),
                860, 1230, life(t, 7.02))
    if cold > 0.01:   # le froid gagne les bords de l'image
        yy, xx = np.ogrid[:H, :W]
        v = np.clip((np.hypot((xx - W / 2) / (W * 0.6), (yy - H / 2) / (H * 0.6)) - 0.55) / 0.5, 0, 1)
        fr = Image.fromarray((v * 150 * cold).astype(np.uint8))
        ov = Image.new("RGBA", (W, H), (190, 220, 255, 0))
        ov.putalpha(fr)
        w.alpha_composite(ov)
    w.alpha_composite(shade())
    title(u, "TU ARROSES LE SOIR…", t, 0.05, 2.02, y=330, color=YEL, size=125)
    title(u, "EN HIVER ?", t, 2.06, 2.86, y=330, color=WHITE, size=170)
    stamp(u, "LA PIRE IDÉE !", 540, 340, t, 2.9, 4.15, RED, 140, -7)
    title(u, "LA NUIT…", t, 4.2, 5.0, y=330, color=YEL, size=180)
    title(u, "ELLE NE BOIT PAS !", t, 5.05, 6.4, y=330, color=WHITE, size=125)
    title(u, "TU BAISSES LE CHAUFFAGE", t, 6.45, None, y=330, color=YEL, size=105)
    return w, u


cue(0.45, "whoosh", 0.12)
cue(0.95, "pour", 0.2)
cue(2.07, "tick", 0.14)
cue(2.92, "alert1", 0.22)
cue(4.15, "whoosh_up", 0.12)
cue(4.75, "sparkle", 0.12)
cue(5.36, "pop_lo", 0.16)
cue(6.6, "click", 0.25)
cue(7.05, "tick", 0.14)
cue(7.35, "tick", 0.14)


# ============================================================ B. EN COUPE : L'EAU FROIDE, LES RACINES POURRISSENT (7.95 → 14.45)
@lru_cache(None)
def _cut_ko():
    return Image.open(_img_root() + COUPE_KO + ".png").convert("RGBA")


@lru_cache(None)
def hybrid():
    """Le pot coupé (racines saines) avec le feuillage du pothos en forme au-dessus du pot."""
    ok = Image.open(_img_root() + COUPE_OK + ".png").convert("RGBA")
    sain = Image.open(_img_root() + SAIN + ".png").convert("RGBA")
    m = Image.new("L", ok.size, 255)
    ImageDraw.Draw(m).rectangle([394, 774, 634, 1015], fill=0)      # seul le pot coupé vient de la photo en coupe
    m = m.filter(ImageFilter.GaussianBlur(3))
    out = Image.composite(sain, ok, m)
    return out


def _img_root():
    import os
    from gfx import IMG
    return IMG + os.sep


def place_im(c, im, k, X, Y):
    """Image cadre 1024 (bas du pot POT_BASE) posée en (X, Y) à l'échelle k."""
    s = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    c.alpha_composite(s, (int(X - POT_BASE[0] * k), int(Y - POT_BASE[1] * k)))


CAM_CUT = (2.6, 722, 1010)
CAM_CUT2 = (2.8, 722, 1010)


def s_cut(t):
    cam = Cam(*[lerp(a, b, clamp((t - 7.95) / 6.5)) for a, b in zip(CAM_CUT, CAM_CUT2)])
    z = cam.z
    w = cam.bg(0.0, 1.0, 0.0, 1.0).filter(ImageFilter.GaussianBlur(4))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px, py = cam.p(*PLANT)
    k = PK * z

    def V(x, y):   # point du cadre 1024 du pothos → écran
        return px + (x - POT_BASE[0]) * k, py + (y - POT_BASE[1]) * k

    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow(lay, px, py, 230 * z, 80)
    # racines saines → pourries : le front descend du haut vers le bas ; le feuillage se dessèche en même temps
    rot_k = ease_io((t - 11.55) / 1.3)
    ok = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    place_im(ok, hybrid(), k, px, py)
    if rot_k > 0:
        ko = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        place_im(ko, _cut_ko(), k, px, py)
        front = V(0, lerp(700, 1000, rot_k))[1]
        m = Image.new("L", (W, H), 0)
        pts = [(x, front + math.sin(x * 0.02 + t * 3) * 14) for x in range(0, W + 20, 20)]
        ImageDraw.Draw(m).polygon([(0, 0), (W, 0)] + pts[::-1], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(14))
        if rot_k >= 1:
            m = Image.new("L", (W, H), 255)
        ko.putalpha(Image.composite(ko.getchannel("A"), Image.new("L", (W, H), 0), m))
        ok.putalpha(Image.composite(Image.new("L", (W, H), 0), ok.getchannel("A"), m))
        lay.alpha_composite(ok)
        lay.alpha_composite(ko)
    else:
        lay.alpha_composite(ok)
    # l'eau froide qui stagne dans la terre, autour des racines (bleutée, qui ondule)
    water = fade(t, 8.05, None, 0.6) * (1 - 0.55 * rot_k)
    if water > 0.01:
        fill_k = ease_out((t - 8.05) / 0.7)
        top = V(0, lerp(780, 790, fill_k))[1]
        bot = V(0, lerp(790, 956, fill_k))[1]
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon([V(*p) for p in SOIL_IN], fill=255)
        ImageDraw.Draw(m).rectangle([0, bot, W, H], fill=0)
        m = m.filter(ImageFilter.GaussianBlur(3))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        col = (int(lerp(95, 120, rot_k)), int(lerp(150, 120, rot_k)), int(lerp(225, 80, rot_k)))
        d.rectangle([0, top, W, H], fill=col + (int(105 * water),))
        for j in range(9):   # reflets qui ondulent
            yj = top + (j + 0.5) * (bot - top) / 9
            pts = [(x, yj + math.sin(x * 0.03 + t * 2.5 + j) * 5) for x in range(int(V(418, 0)[0]), int(V(612, 0)[0]), 8)]
            if len(pts) > 1:
                d.line(pts, fill=(225, 240, 255, int(90 * water)), width=3)
        ov.putalpha(Image.composite(ov.getchannel("A"), Image.new("L", (W, H), 0), m))
        lay.alpha_composite(ov.filter(ImageFilter.GaussianBlur(1.2)))
    # les larves dans la terre pourrie
    if t > 12.5:
        for i, (lx, ly) in enumerate([(470, 905), (565, 860), (520, 935)]):
            a_ = life(t, 12.55 + i * 0.2, dur=0.3)
            X, Y = V(lx, ly)
            ob(lay, LARVE, X, Y, 24 * z * (1 + 0.06 * math.sin(t * 9 + i)), rot=math.sin(t * 4 + i * 2) * 10,
               alpha=a_, flip=i % 2 == 1)
    w.alpha_composite(tint_layer(lay, 0.0, 0.7, 0.0, 1.0, lit=2.1))
    # les moucherons sortent de la terre et volent autour
    if t > 12.85:
        sx, sy = V(515, 782)
        burst = clamp((t - 12.85) / 0.8)
        for i in range(16):
            q = clamp(burst * 1.5 - i * 0.04)
            if q <= 0:
                continue
            x, y, vx = swarm_pos(t, i, 540, sy - 260, 380, 260)
            ox = sx + ((i * 37) % 9 - 4) * 24
            x, y = lerp(ox, x, ease_out(q)), lerp(sy, y, ease_out(q))
            gnat(w, x, y, 80 + 14 * (i % 3), vx, i)
    w.alpha_composite(shade())
    # l'eau froide, toute la nuit (horloge qui tourne jusqu'au matin)
    if 8.4 < t < 10.75:
        put(u, thermo_cold(140), 170, 760, life(t, 8.5, 10.6))
        tag(u, "EAU FROIDE", 300, 640, t, 8.6, 10.6, rot=-6, size=50)
    if 9.6 < t < 10.75:
        hrs = lerp(10, 19, ease_io((t - 9.7) / 0.75))   # 22 h → 7 h
        clock(u, 880, 720, 110, hrs, life(t, 9.65, 10.6))
    if t > 11.6:
        tag(u, "RACINES POURRIES", 300, 1250, t, 11.65, 12.75, rot=-5, size=50)
    title(u, "L'EAU RESTE FROIDE…", t, 7.98, 9.65, y=330, color=WHITE, size=120)
    title(u, "JUSQU'AU MATIN !", t, 9.7, 10.6, y=330, color=YEL, size=140)
    title(u, "RÉSULTAT :", t, 10.64, 11.5, y=330, color=WHITE, size=175)
    stamp(u, "ÇA POURRIT !", 540, 340, t, 11.55, 12.75, RED, 145, -7)
    title(u, "LES MOUCHERONS…", t, 12.8, 13.55, y=330, color=WHITE, size=140)
    stamp(u, "ADORENT ÇA !", 540, 340, t, 13.6, None, YEL, 140, -6)
    return w, u


cue(8.1, "plop", 0.14)
cue(8.55, "pop", 0.12)
cue(9.7, "tick", 0.12)
cue(10.0, "tick", 0.12)
cue(10.3, "tick", 0.12)
cue(11.6, "fail", 0.2)
cue(12.9, "buzz", 0.16)
cue(13.62, "pop", 0.12)


# ============================================================ C. LE MATIN : EAU À 20 °C, ELLE BOIT À LA LUMIÈRE (14.45 → 19.6)
CAM_MORN = (1.12, 640, 1000)
CAM_DRINK = (1.22, 680, 960)


def sun_rays(c, cam, t, a):
    """Rayons de soleil qui entrent par la porte-fenêtre et tombent sur la table."""
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(5):
        x0 = 560 + i * 34 + math.sin(t * 0.9 + i) * 8
        top = [cam.p(*P(x0, 300)), cam.p(*P(x0 + 18, 300))]
        bot = [cam.p(*P(x0 - 210 + 12, 1000)), cam.p(*P(x0 - 210 - 55, 1000))]
        d.polygon(top + bot, fill=(255, 232, 170, int(38 * a)))
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(14)))
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gx, gy = cam.p(*P(700, 330))
    ImageDraw.Draw(gl).ellipse([gx - 160, gy - 160, gx + 160, gy + 160], fill=(255, 245, 210, int(120 * a)))
    c.alpha_composite(gl.filter(ImageFilter.GaussianBlur(50)))


def drink_drops(c, cam, t, t0, a):
    """Elle boit : des gouttelettes montent de la terre dans les tiges et les feuilles."""
    if a <= 0.01 or t < t0:
        return
    sx, sy = soil_pt(cam)
    r = np.random.default_rng(4)
    for i in range(14):
        p = ((t - t0) * 0.7 + i / 14) % 1.0
        x = sx + r.uniform(-120, 120) * PK * cam.z * (0.4 + p)
        y = sy - p * 420 * PK * cam.z
        sz = int(r.uniform(26, 40))
        put(c, icon("drop", sz), x, y, 1.0, alpha=a * math.sin(math.pi * p))


def s_morning(t):
    cam = Cam(*[lerp(a, b, clamp((t - 14.45) / 5.15)) for a, b in zip(CAM_MORN, CAM_DRINK)])
    dawn = 1 - fade(t, 14.45, None, 0.55)          # la nuit se lève
    morn = fade(t, 14.45, None, 0.6)
    w = cam.bg(0.0, dawn, morn, 0.0)
    sun_rays(w, cam, t, morn)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px, py = cam.p(*PLANT)
    shadow(lay, px, py, 230 * cam.z, 80)
    pothos(lay, SAIN, px, py, PK * cam.z)
    wet(lay, cam, fade(t, 15.2, None, 0.5) * (1 - 0.7 * fade(t, 17.6, None, 1.5)))
    can_and_water(lay, cam, t, 14.75, 15.25, 16.75)
    w.alpha_composite(tint_layer(lay, 0.0, dawn, morn, 0.0))
    drink_drops(w, cam, t, 17.4, fade(t, 17.4, 19.5, 0.3, 0.3))
    w.alpha_composite(shade())
    if t > 15.95:
        put(u, icon("thermo", 150), 170, 1100, life(t, 16.0, 17.2))
        tag(u, "20°C", 260, 980, t, 16.05, 17.2, rot=-6, size=64)
    if t > 18.6:
        put(u, icon("sun", 190), 880, 640, life(t, 18.65))
        put(u, icon("check", 150), 190, 700, life(t, 18.8))
        sparkles(u, t, 18.65, 640, 820, 330, 9, 5)
    title(u, "ARROSE LE MATIN !", t, 14.5, 15.95, y=330, color=YEL, size=130)
    title(u, "TEMPÉRATURE AMBIANTE", t, 16.0, 17.2, y=330, color=WHITE, size=102)
    title(u, "ELLE BOIT LE JOUR…", t, 17.25, 18.6, y=330, color=WHITE, size=125)
    title(u, "À LA LUMIÈRE !", t, 18.65, None, y=330, color=YEL, size=150)
    return w, u


cue(14.5, "sparkle", 0.16)
cue(14.8, "whoosh", 0.1)
cue(15.2, "pour", 0.2)
cue(16.05, "pop", 0.12)
cue(17.45, "rise", 0.14)
cue(18.7, "success", 0.18)


# ============================================================ D. ABONNE-TOI (19.6 → fin)
def s_end(t):
    cam = Cam(*CAM_DRINK)
    w = cam.bg(0.0, 0.0, 1.0, 0.0)
    sun_rays(w, cam, t, 1.0)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px, py = cam.p(*PLANT)
    shadow(lay, px, py, 230 * cam.z, 80)
    pothos(lay, SAIN, px, py, PK * cam.z)
    w.alpha_composite(tint_layer(lay, 0.0, 0.0, 1.0, 0.0))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    sparkles(u, t, 19.7, 640, 760, 330, 10, 7)
    clicked = t > 20.9
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 20.85) / 0.15))
    put(u, btn, 540, 1400, life(t, 19.8) * press)
    if t > 20.3:
        kk = ease_out((t - 20.3) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 21.7, dur=0.45))
    sparkles(u, t, 21.8, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 19.65, 21.65, y=330, color=YEL, size=135)
    return w, u


cue(19.7, "pop_lo", 0.18)
cue(20.88, "click", 0.3)
cue(21.8, "sparkle", 0.16)

def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, T_RAD - SHIFT, _sh(s_salon)),
    (T_RAD - SHIFT, 7.95 - SHIFT, _sh(s_salon)),
    (7.95 - SHIFT, 14.45 - SHIFT, _sh(s_cut)),
    (14.45 - SHIFT, 19.6 - SHIFT, _sh(s_morning)),
    (19.6 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
