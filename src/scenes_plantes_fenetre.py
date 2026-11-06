"""Storyboard « Plantes qui gèlent près de la fenêtre » (voix : assets/audio/plantes_fenetre/voix.mp3).

Volume de la voix gardé tel qu'envoyé (render.py « af »).
Un seul plan continu devant la fenêtre de la cuisine (photo fournie), avec une tringle et des rideaux (fournis) :
0–5.5   le jour, il neige dehors ; l'orchidée (fournie) sur le rebord, tout contre la vitre ; le givre commence.
5.5–9   la nuit tombe (lune), la vitre se couvre de givre ; une feuille touche la vitre.
9–11    elle noircit et meurt (orchidée fanée, fournie).
11–17   retour en arrière ; le pire piège : les rideaux se ferment, la plante est coincée derrière (vue « rayons X »).
17–20.4 on l'avance de 20 cm, côté pièce, devant le rideau : au chaud.
20.4–fin l'orchidée sur la petite table du coin du salon (photo fournie) + S'abonner + logo.
"""
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, put, title, life, fade, ease_out, ease_io, ease_in,
                 clamp, lerp, icon, pills, tag, button_img, hl_ellipse, particles, light_rays, spr)
from scenes import sparkles
from scenes_ananas import logo_img, place
from scenes_hortensia import stamp
from scenes_citron import shade, shadow, zoomed, photo
from scenes_eau_pates import Cam

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


SAINE, FANEE = "banque/orchidee_saine", "banque/orchidee_fanee"
RIDEAU, TRINGLE, LUNE = "banque/rideau", "banque/tringle", "banque/lune_pleine"
FULL = (0, 0, 1024, 1024)
POT_S, POT_F = (517, 965, 264), (520, 960, 334)          # pot dans chaque photo : centre x, bas, largeur

PANES = [(62, 0, 448, 1284), (605, 0, 918, 1247)]       # vitres (photo de la fenêtre, 1080 x 1920), au pixel près
SILL_BACK, SILL_FRONT = 1448, 1512                      # sur le rebord : contre la vitre / au bord, côté pièce
PLANT_X, POT_W = 330, 165
ROD_Y, CURT_TOP, CURT_BOT = 108, 122, 1388


# ------------------------------------------------------------- givre, neige, nuit
@lru_cache(None)
def frost_base():
    """Texture de givre (photo) : distance au bord de chaque vitre, voile nuageux et grain fin."""
    from scipy.ndimage import gaussian_filter
    r = np.random.default_rng(3)
    dist = np.full((1920, 1080), 1e6, np.float32)
    yy, xx = np.mgrid[:1920, :1080]
    for x0, y0, x1, y1 in PANES:
        inside = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
        d = np.minimum(np.minimum(xx - x0, x1 - xx), np.minimum(yy - y0, y1 - yy)).astype(np.float32)
        dist = np.where(inside, np.minimum(dist, d), dist)

    def nz(sig):
        n = gaussian_filter(r.standard_normal((1920, 1080)).astype(np.float32), sig)
        return (n - n.min()) / (n.max() - n.min())

    cloud = 0.6 * nz(28) + 0.4 * nz(9)          # voile irrégulier
    grain = nz(1.1)                              # grain fin (cristaux)
    return dist, cloud, grain


@lru_cache(24)
def frost_img(q):
    """Givre à l'avancement q/20 : il part des bords et gagne toute la vitre."""
    f = q / 20
    dist, cloud, grain = frost_base()
    reach = f * 430
    cov = np.clip((reach - dist) / 110 + (cloud - 0.5) * 1.2, 0, 1)
    cov = np.where(dist > 1e5, 0, cov)
    alpha = np.clip(cov * (0.5 + 0.45 * grain) + cov ** 3 * 0.15, 0, 0.9)
    shade_ = 225 + 25 * grain
    rgb = np.dstack([shade_ - 6, shade_ + 2, shade_ + 10]).clip(0, 255)
    return Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")


def snow(c, t, a):
    if a <= 0.01:
        return
    d = ImageDraw.Draw(c)
    r = np.random.default_rng(11)
    for _ in range(70):
        x0, y0, x1, y1 = PANES[r.integers(0, 2)]
        sp = r.uniform(70, 150)
        x = r.uniform(x0, x1) + math.sin(t * 1.5 + r.uniform(0, 6)) * 14
        y = y0 + (r.uniform(0, 1300) + t * sp) % (y1 - y0)
        if x0 + 4 < x < x1 - 4 and y < y1 - 6:   # elle ne tombe que derrière les vitres (dehors)
            s = r.uniform(2, 5)
            d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 255, 255, int(220 * a)))


def tinted(lay, night, warm=0.0):
    """Assombrit (bleu nuit) les objets d'un calque, ou les réchauffe (lumière de la pièce)."""
    if night > 0.01:
        ov = Image.new("RGBA", lay.size, (18, 28, 70, int(150 * night)))
        ov.putalpha(Image.composite(ov.getchannel("A"), Image.new("L", lay.size, 0), lay.getchannel("A")))
        lay.alpha_composite(ov)
    if warm > 0.01:
        ov = Image.new("RGBA", lay.size, (255, 180, 90, int(70 * warm)))
        ov.putalpha(Image.composite(ov.getchannel("A"), Image.new("L", lay.size, 0), lay.getchannel("A")))
        lay.alpha_composite(ov)
    return lay


def orchid(c, X, Y, pot_w, dead=False, rotten=0.0, s=1.0):
    cx, bot, pw = POT_F if dead else POT_S
    k = pot_w / pw
    place(c, FANEE if dead else SAINE, FULL, k, cx, bot, X, Y, s, 0.0, rotten)


def curtains(c, cam, close, xray=None):
    """Tringle + deux rideaux ; close 0 → 1 : les pans se déploient jusqu'au milieu."""
    z = cam.z
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hh = (CURT_BOT - CURT_TOP) * z
    nat = 422 * hh / 805                                  # largeur naturelle d'un pan (rideau.png : 422 x 805)
    for side in (-1, 1):
        wid = lerp(200, 560, close)
        cx = lerp(75 if side < 0 else 1005, 270 if side < 0 else 810, close)
        x, y = cam.p(cx, CURT_BOT)
        spr(lay, RIDEAU, x, y, hh, sx=wid * z / nat, flip=side > 0, shadow=False)
    if xray is not None and xray[2] > 0.01:              # vue « rayons X » : on voit à travers le rideau
        ex, ey, a, rx, ry = xray
        m = Image.new("L", (W, H), 255)
        ImageDraw.Draw(m).ellipse([ex - rx, ey - ry, ex + rx, ey + ry], fill=int(255 * (1 - 0.8 * a)))
        m = m.filter(ImageFilter.GaussianBlur(14))
        lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
    rx_, ry_ = cam.p(540, ROD_Y)
    spr(lay, TRINGLE, rx_, ry_ + 35 * z, 70 * z, sx=1100 / 517, shadow=False)
    c.alpha_composite(lay)
    return lay


# ============================================================ LA FENÊTRE (0 → 20.45)
REWIND = 11.0
CLOSE_T = 12.7
FORWARD_T = 17.6


def s_window(t):
    fy = lerp(915, 960, ease_io((t - 17.2) / 0.8))
    cam = Cam(lerp(1.15, 1.25, ease_io((t - 7.9) / 1.0)) if t < REWIND else lerp(1.25, 1.15, ease_io((t - REWIND) / 0.6)),
              540, fy)
    z = cam.z
    night = fade(t, 5.6, None, 0.6)
    warm = ease_io((t - FORWARD_T) / 0.8)
    bg = photo("fond_fenetre.webp").copy()
    snow(bg, t, 1 - night)
    if night > 0.01:
        bg.alpha_composite(Image.new("RGBA", (W, H), (14, 22, 60, int(165 * night))))
        q = ease_out((t - 5.7) / 0.9)
        place(bg, LUNE, FULL, 0.2, 512, 512, 760, lerp(520, 290, q), 1.0, 0.0, 0.0, q)
    # le givre : un peu dès « elle peut geler », beaucoup la nuit ; le retour en arrière le ramène à mi-chemin
    if t < REWIND:
        f = 0.25 * ease_io((t - 3.5) / 1.5) + 0.7 * ease_io((t - 6.4) / 1.4)
    else:
        f = lerp(0.95, 0.75, ease_io((t - REWIND) / 0.5))
    if f > 0.02:
        bg.alpha_composite(frost_img(int(round(f * 20))))
    if night > 0.01:   # la lune reste visible à travers le givre
        q = ease_out((t - 5.7) / 0.9)
        place(bg, LUNE, FULL, 0.2, 512, 512, 760, lerp(520, 290, q), 1.0, 0.0, 0.0, 0.55 * q)
    w = zoomed(bg, z, cam.fx, cam.fy).copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # la plante : contre la vitre, puis avancée de 20 cm (côté pièce, devant le rideau)
    fwd = ease_io((t - FORWARD_T) / 0.7)
    py = lerp(SILL_BACK, SILL_FRONT, fwd)
    pw = POT_W * lerp(1.0, 1.08, fwd)
    dead = REWIND > t > 9.45
    rot_ = 0.55 * ease_io((t - 9.45) / 0.9) if dead else 0.0
    shake = math.sin(t * 60) * 6 * fade(t, 9.45, 9.8, 0.02, 0.2) if 9.45 < t < 9.8 else 0.0
    plant = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    X, Y = cam.p(PLANT_X + shake, py)
    shadow(plant, X, Y, pw * z * 0.95, 70)
    orchid(plant, X, Y, pw * z, dead, rot_)
    tinted(plant, night * (1 - 0.75 * warm), warm)
    close = ease_io((t - CLOSE_T) / 0.7) if t > CLOSE_T else 0.0
    xr = fade(t, 14.2, FORWARD_T, 0.4, 0.35)
    if fwd < 0.5:   # derrière le rideau (contre la vitre)
        w.alpha_composite(plant)
        cl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        curtains(cl, cam, close, (X, Y - 250 * z, xr, 260 * z, 330 * z))
        w.alpha_composite(tinted(cl, night * (1 - 0.6 * warm), warm))
    else:            # devant le rideau, côté pièce
        cl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        curtains(cl, cam, close)
        w.alpha_composite(tinted(cl, night * (1 - 0.6 * warm), warm))
        w.alpha_composite(plant)
    if xr > 0.01:   # le froid coincé derrière le rideau
        cold = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(cold).ellipse([X - 250 * z, Y - 560 * z, X + 250 * z, Y + 30 * z], fill=(120, 180, 255, int(70 * xr)))
        w.alpha_composite(cold.filter(ImageFilter.GaussianBlur(30)))
    if warm > 0.01:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([X - 380, Y - 700, X + 380, Y + 120], fill=(255, 190, 110, int(60 * warm)))
        w.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60)))
    w.alpha_composite(shade())
    # --- les explications
    if 3.5 < t < 5.6:
        put(u, icon("thermo", 150), 900, 640, life(t, 3.55, 5.5))
    if 6.5 < t < 9.4:
        tag(u, "-5 °C", 860, 620, t, 6.6, 9.35, rot=-5, size=70)
    if 7.95 < t < 9.4:
        lx, ly = cam.p(PLANT_X - 70, SILL_BACK - 120)
        hl_ellipse(u, lx, ly, 110, 80, life(t, 8.0, 9.35))
        tag(u, "CONTRE LA VITRE", 300, 760, t, 8.05, 9.35, rot=-4, size=46, string_to=(lx, ly - 60))
    if REWIND - 0.05 < t < REWIND + 0.45:   # retour en arrière
        a = fade(t, REWIND - 0.05, REWIND + 0.45, 0.08, 0.15)
        ov = Image.new("RGBA", (W, H), (40, 60, 90, int(60 * a)))
        d = ImageDraw.Draw(ov)
        for yy in range(0, H, 9):
            d.line([(0, yy), (W, yy)], fill=(255, 255, 255, int(18 * a)), width=2)
        u.alpha_composite(ov)
    if 14.3 < t < FORWARD_T:
        tag(u, "COINCÉE !", 300, 760, t, 14.4, FORWARD_T - 0.1, rot=-5, size=58)
    if 16.0 < t < FORWARD_T:
        pills(u, ["22 H", "2 H", "6 H"], min(2, int((t - 16.05) / 0.3)), t, 16.0, FORWARD_T - 0.05, y=560, pw=210)
    if t > FORWARD_T + 0.3:   # 20 cm : flèche entre la vitre et le pot
        a = life(t, FORWARD_T + 0.35)
        x0, y0 = cam.p(PLANT_X + 120, SILL_BACK - 10)
        x1, y1 = cam.p(PLANT_X + 120, SILL_FRONT - 10)
        d = ImageDraw.Draw(u)
        if a > 0.01:
            d.line([(x0, y0 - 40), (x1, y1)], fill=YEL + (int(255 * a),), width=10)
            d.polygon([(x1 - 22, y1 - 26), (x1 + 22, y1 - 26), (x1, y1 + 8)], fill=YEL + (int(255 * a),))
        tag(u, "20 CM", 860, y1 - 230, t, FORWARD_T + 0.4, None, rot=-5, size=66, string_to=(x1 + 20, y1 - 30))
        put(u, icon("check", 150), 860, 640, life(t, 19.5))
    title(u, "PRÈS DE LA FENÊTRE ?", t, 0.05, 2.3, y=330, color=YEL, size=120)
    title(u, "CET HIVER…", t, 2.35, 3.45, y=330, size=165)
    stamp(u, "ELLE PEUT GELER !", 540, 340, t, 3.5, 5.6, RED, 115, -6)
    title(u, "LA NUIT…", t, 5.67, 6.5, y=330, size=170)
    title(u, "LA VITRE GÈLE", t, 6.55, 7.9, y=330, color=YEL, size=150)
    title(u, "UNE FEUILLE LA TOUCHE ?", t, 7.95, 9.4, y=330, size=110)
    stamp(u, "ELLE MEURT !", 540, 340, t, 9.45, 10.95, RED, 140, -7)
    title(u, "LE PIRE PIÈGE ?", t, 11.07, 12.62, y=330, color=YEL, size=150)
    stamp(u, "LE RIDEAU FERMÉ !", 540, 340, t, 12.67, 14.1, RED, 112, -6)
    title(u, "COINCÉE DANS LE FROID", t, 14.15, 17.1, y=330, size=112)
    title(u, "ÉLOIGNE-LA DE 20 CM", t, 17.15, 18.9, y=330, color=YEL, size=118)
    stamp(u, "CÔTÉ PIÈCE !", 540, 340, t, 18.95, None, GREEN, 140, -6)
    return w, u


cue(0.05, "whoosh_up", 0.14)
cue(3.52, "alert1", 0.28)
cue(5.65, "whoosh", 0.16)
cue(5.9, "bell", 0.15)
cue(6.6, "rustle", 0.16)
cue(8.02, "pop_hi", 0.2)
cue(9.47, "fail", 0.32)
cue(10.97, "rise", 0.2)
cue(CLOSE_T + 0.02, "whoosh", 0.22)
cue(CLOSE_T + 0.7, "thud", 0.18)
cue(14.25, "alert3", 0.22)
for _k in range(3):
    cue(16.06 + _k * 0.3, "tick", 0.2)
cue(FORWARD_T, "whoosh", 0.16)
cue(FORWARD_T + 0.4, "pop", 0.2)
cue(18.97, "ding", 0.28)
cue(19.52, "success", 0.24)


# ============================================================ LE COIN DU SALON + ABONNE-TOI (20.45 → fin)
TABLE_X, TABLE_Y = 235, 1078                     # dessus de la petite table ronde (photo du salon)


def s_end(t):
    cam = Cam(1.35, 420, 930)
    w = cam.bg("fond_salon_coin2.jpg")
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    X, Y = cam.p(TABLE_X, TABLE_Y)
    s_ = life(t, 20.5, dur=0.4)
    shadow(w, X, Y, 150 * cam.z * s_, 70)
    orchid(w, X, Y, 125 * cam.z, s=s_)
    w.alpha_composite(shade())
    sparkles(u, t, 20.6, X, Y - 300, 260, 10, 7)
    clicked = t > 22.0
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 21.95) / 0.15))
    put(u, btn, 700, 1150, life(t, 20.7) * press)
    if t > 21.5:
        k = ease_out((t - 21.5) / 0.4)
        put(u, icon("cursor", 110), lerp(980, 800, k), lerp(1380, 1190, k), 1)
    put(u, logo_img(260), 540, 330, life(t, 22.6, dur=0.45))
    sparkles(u, t, 22.7, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 20.55, 22.55, y=330, color=YEL, size=135)
    return w, u


cue(20.52, "pop_lo", 0.28)
cue(21.98, "click", 0.45)
cue(22.7, "sparkle", 0.25)

SCENES = [
    (0.0, 20.45, s_window),
    (20.45, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
