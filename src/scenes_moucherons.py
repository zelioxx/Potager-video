"""Storyboard « Moucherons du terreau » (voix : assets/audio/moucherons/voix.mp3).

Ouverture dans le coin du salon (photo fournie) : une grosse monstera, des moucherons qui tournent autour ; on
arrose, ils jaillissent de la terre ; la caméra plonge sur la terre du pot. Puis sur fond beige, le même pot en gros
plan : la loupe montre les larves dans le terreau humide ; la surface sèche entre deux arrosages ; on la recouvre
d'1 cm de sable (texture de la photo fournie) : plus de ponte. Bonus : le bol de vinaigre de cidre + une goutte de
liquide vaisselle, les moucherons plongent dedans. Fin dans le salon, la monstera sans moucherons.
Photos : salon, moucherons, bol, sable, larve (fournies) ; monstera, pot de terreau, arrosoir (vidéos précédentes).
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, background, spr, put, title, life, fade,
                 ease_out, ease_io, ease_in, clamp, lerp, icon, pills, tag, button_img, hl_ellipse, particles,
                 light_rays, num_badge, text_img, F_BLACK)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import photo, shade, zoomed, shadow, swap
from scenes_avocat2 import geom
from scenes_banane import ob

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)     # blocs de 3-4 mots, gros et lisibles


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


GNATS = ["banque/moucheron_a", "banque/moucheron_b"]
MONSTERA, ARROSOIR = "arrosage/monstera_mieux_full", "banque/arrosoir_zinc"
POT, LARVE, BOL = "citron/pot_vide", "banque/larve_blanche", "banque/bol_vinaigre_cidre"


def gnat(c, x, y, w_, vx, i=0, alpha=1.0, rot=0.0):
    """Moucheron (tête à gauche dans la photo) orienté selon sa vitesse horizontale."""
    ob(c, GNATS[i % 2], x, y, w_, rot=rot, alpha=alpha, flip=vx > 0)


def swarm_pos(t, i, cx, cy, rx, ry):
    """Vol erratique autour de (cx, cy) ; renvoie x, y, vx."""
    a = t * (2.2 + 0.37 * (i % 5)) + i * 1.7
    b = t * (3.1 + 0.23 * (i % 7)) + i * 0.9
    x = cx + math.cos(a) * rx * (0.55 + 0.45 * math.sin(i * 2.3)) + math.sin(b * 2.7) * 18
    y = cy + math.sin(b) * ry * (0.5 + 0.5 * math.cos(i * 1.3)) + math.cos(a * 3.1) * 14
    vx = -math.sin(a) * (2.2 + 0.37 * (i % 5))
    return x, y, vx


# ============================================================ A. LE COIN DU SALON (0 → 5.97)
MON_X, MON_Y, MON_W = 730, 1350, 640            # monstera sur le tapis, au milieu bas de l'image (hors titres)
MON_K = MON_W / (931 - 109)
SOIL_W = (MON_X + (512 - 520) * MON_K, MON_Y + (483 - 950) * MON_K)    # terre du pot (décor)
CAN_C, CAN_W, CAN_ROT = (SOIL_W[0] - 224, SOIL_W[1] - 156), 420, -28  # arrosoir (retourné, pomme à droite)
SPOUT = (SOIL_W[0], SOIL_W[1] - 167)


N_START, N_BURST = 3, 26                         # 2-3 moucherons au début, puis une nuée à l'arrosage


def salon(t, gnats=True, burst=0.0):
    w = photo("fond_salon_coin.webp").copy()
    shadow(w, MON_X, MON_Y, MON_W * 0.8, 70)
    ob(w, MONSTERA, MON_X, MON_Y, MON_W, anchor="bottom")
    if gnats:
        n = N_START + (N_BURST if burst > 0 else 0)
        for i in range(n):
            if i < N_START:
                x, y, vx = swarm_pos(t, i, MON_X - 40, MON_Y - 380, 250, 200)
            else:                             # ils jaillissent de la terre et se dispersent
                x, y, vx = swarm_pos(t, i, MON_X - 80, MON_Y - 400, 420, 360)
                q = clamp(burst * 1.6 - (i - N_START) * 0.035)
                if q <= 0:
                    continue
                ox = SOIL_W[0] + ((i * 37) % 9 - 4) * 26
                x, y = lerp(ox, x, ease_out(q)), lerp(SOIL_W[1] - 5, y, ease_out(q))
            gnat(w, x, y, 62 + 12 * (i % 3), vx, i)
    return w


ROSE = (SOIL_W[0] - 36, SOIL_W[1] - 146)       # centre de la face de la pomme de l'arrosoir (incliné)


def watering(c, t, a):
    """Pomme d'arrosoir : fins jets d'eau en gerbe (paraboles), reflets qui filent, gouttes et éclaboussures."""
    if a <= 0.01:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    g, ground = 1900.0, SOIL_W[1] - 4
    r = np.random.default_rng(11)
    n = 26
    for k in range(n):
        q = k / (n - 1)
        x0 = ROSE[0] + lerp(14, -14, q) + r.uniform(-3, 3)      # le long du disque de la pomme
        y0 = ROSE[1] + lerp(-22, 22, q) + r.uniform(-3, 3)
        ang = math.radians(lerp(18, 72, q) + r.uniform(-5, 5))
        v = r.uniform(250, 330)
        vx, vy = v * math.cos(ang), v * math.sin(ang)
        tau_end = (-vy + math.sqrt(vy * vy + 2 * g * (ground - y0))) / g
        pts = []
        for i in range(19):
            tau = tau_end * i / 18
            wob = math.sin(t * 40 + k * 1.7 + i * 0.9) * 1.2 * i / 18
            pts.append((x0 + vx * tau + wob, y0 + vy * tau + 0.5 * g * tau * tau))
        d.line(pts, fill=(196, 222, 244, int(105 * a)), width=2 if k % 3 else 3, joint="curve")
        # reflets qui descendent le long du jet
        for j in range(2):
            ph = (t * 3.0 + k * 0.37 + j * 0.5) % 1.0
            i0 = int(ph * 16)
            d.line(pts[i0:i0 + 3], fill=(250, 253, 255, int(200 * a)), width=3)
        # le bout du jet se casse en gouttes
        ex, ey = pts[-1]
        for j in range(3):
            ph = (t * 4.0 + k * 0.29 + j * 0.33) % 1.0
            gx, gy = lerp(pts[-4][0], ex, ph), lerp(pts[-4][1], ey, ph)
            d.ellipse([gx - 2.4, gy - 3.2, gx + 2.4, gy + 3.2], fill=(232, 244, 254, int(200 * a)))
    # éclaboussures sur la terre
    for k in range(30):
        p = (t * 3.4 + k * 0.161) % 1.0
        ang = math.radians(200 + (k * 47) % 140)
        sx = SOIL_W[0] - 40 + ((k * 29) % 15) * 9
        x = sx + math.cos(ang) * 34 * p
        y = ground - 4 + math.sin(ang) * 26 * p + 50 * p * p
        rr = 2.4 * (1 - p) + 0.8
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(228, 240, 252, int(180 * a * (1 - p))))
    c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(0.6)))


def wet_soil(c, k):
    """La terre du pot s'assombrit en buvant l'eau."""
    if k <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rx, ry = 150 * MON_K, 62 * MON_K
    ImageDraw.Draw(ov).ellipse([SOIL_W[0] - rx, SOIL_W[1] - ry, SOIL_W[0] + rx, SOIL_W[1] + ry],
                               fill=(12, 8, 4, int(95 * k)))
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(10)))


def s_salon(t):
    burst = clamp((t - 2.8) / 0.9) if t > 2.8 else 0.0
    w = salon(t, True, burst)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # l'arrosoir arrive à « dès que tu l'arroses »
    cin = ease_out((t - 2.15) / 0.35)
    cout = ease_in((t - 3.25) / 0.3)
    wet_soil(w, ease_out((t - 2.7) / 0.6))
    if 2.15 < t < 3.6:
        tilt = CAN_ROT * ease_io((t - 2.45) / 0.25) * (1 - cout)
        ob(w, ARROSOIR, lerp(-400, CAN_C[0], cin) - 700 * cout, CAN_C[1], CAN_W, rot=tilt, flip=True)
        watering(w, t, fade(t, 2.66, 3.27, 0.06, 0.1))
    # caméra : tout le coin, puis plongée sur la terre du pot
    zk = ease_io((t - 3.5) / 0.7)
    w = zoomed(w, lerp(1.12, 2.3, zk), lerp(600, SOIL_W[0], zk), lerp(980, SOIL_W[1] - 40, zk))
    w.alpha_composite(shade())
    if t > 4.3:
        hl_ellipse(u, 540, 1050, 300, 125, life(t, 4.35))
    title(u, "DES MOUCHERONS ?!", t, 0.05, 1.9, y=330, color=YEL, size=130)
    title(u, "PARTOUT !", t, 1.95, 3.5, y=330, color=RED, size=180)
    title(u, "LE PROBLÈME…", t, 3.59, 5.0, y=330, size=160)
    stamp(u, "LA TERRE !", 540, 340, t, 5.07, None, RED, 150, -7)
    return w, u


cue(0.05, "buzz", 0.22)
cue(1.95, "pop", 0.2)
cue(2.2, "whoosh", 0.16)
cue(2.62, "pour", 0.3)
cue(2.8, "buzz", 0.3)
cue(3.6, "whoosh_up", 0.18)
cue(5.09, "alert1", 0.3)


# ============================================================ B-C-D. LE POT EN GROS PLAN (5.97 → 15.0)
P_X, P_BOT, P_W = 540, TABLE + 70, 700          # pot de terreau (photo citron/pot_vide, cadre 1254)
P_BB = (291, 248, 965, 1025)
P_K = P_W / (P_BB[2] - P_BB[0])
S_C, S_RX, S_RY = (624, 412), 300, 132          # surface de la terre dans la photo (cadre 1254)


def p2w(x, y):
    return P_X + (x - (P_BB[0] + P_BB[2]) / 2) * P_K, P_BOT + (y - P_BB[3]) * P_K


SURF = p2w(*S_C)
SRX, SRY = S_RX * P_K, S_RY * P_K


def soil_mask(scale=1.0, cx=None):
    m = Image.new("L", (W, H), 0)
    x, y = SURF if cx is None else cx
    ImageDraw.Draw(m).ellipse([x - SRX * scale, y - SRY * scale, x + SRX * scale, y + SRY * scale], fill=255)
    return m.filter(ImageFilter.GaussianBlur(4))


def tint_soil(c, wet, dry):
    """Terre mouillée (plus sombre, brillante) ou sèche (plus claire, grisée) à la surface du pot."""
    if wet < 0.01 and dry < 0.01:
        return
    m = soil_mask(0.98)
    if wet > 0.01:
        ov = Image.new("RGBA", (W, H), (10, 6, 2, int(110 * wet)))
        ov.putalpha(Image.composite(ov.getchannel("A"), Image.new("L", (W, H), 0), m))
        c.alpha_composite(ov)
        d = ImageDraw.Draw(c)
        r = np.random.default_rng(4)
        for _ in range(int(14 * wet)):
            x, y = SURF[0] + r.uniform(-0.8, 0.8) * SRX, SURF[1] + r.uniform(-0.6, 0.6) * SRY
            d.ellipse([x - 7, y - 3, x + 7, y + 3], fill=(255, 255, 255, int(110 * wet)))
    if dry > 0.01:
        ov = Image.new("RGBA", (W, H), (176, 150, 120, int(120 * dry)))
        ov.putalpha(Image.composite(ov.getchannel("A"), Image.new("L", (W, H), 0), m))
        c.alpha_composite(ov)


@lru_cache(None)
def sand_tex():
    im = Image.open(os.path.join(IMG, "banque", "sable_texture.jpg")).convert("RGBA")
    return im.resize((int(SRX * 2.2), int(SRX * 2.2)), Image.LANCZOS)


def sand_layer(c, cover):
    """Couche de sable sur la terre : elle s'étale depuis le centre (cover 0 → 1)."""
    if cover <= 0.01:
        return
    tx = sand_tex()
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.alpha_composite(tx, (int(SURF[0] - tx.width / 2), int(SURF[1] - tx.height / 2)))
    m = soil_mask(min(1.0, cover))
    lay.putalpha(m)
    # léger relief : bord plus clair
    c.alpha_composite(lay)


def larve(c, x, y, w_, t, i):
    s = 1 + 0.06 * math.sin(t * 9 + i)
    ob(c, LARVE, x, y, w_ * s, rot=math.sin(t * 4 + i * 2) * 8, flip=i % 2 == 1)


LENS = (540, 760, 260)                          # loupe : centre, rayon


def s_pot(t):
    w, u = new_layers(background("table"))
    shadow(w, P_X, P_BOT, P_W * 0.75)
    ob(w, POT, P_X, P_BOT, P_W, anchor="bottom", s=life(t, 5.97, dur=0.35))
    wet = 1.0 - ease_io((t - 9.1) / 1.0)
    dry = ease_io((t - 9.1) / 1.0) * (1 - ease_io((t - 11.3) / 0.4))
    tint_soil(w, wet, dry)
    # le sable : un filet qui tombe et s'étale
    cover = ease_out((t - 11.45) / 1.3)
    sand_layer(w, cover)
    if 11.35 < t < 12.9:
        d = ImageDraw.Draw(w)
        a = fade(t, 11.35, 12.9, 0.1, 0.2)
        d.rectangle([SURF[0] - 22, 0, SURF[0] + 22, SURF[1]], fill=(196, 178, 140, int(235 * a)))
        particles(w, t, t - (t % 0.25), SURF[0], SURF[1], 10, int(t * 8) % 9, col=(205, 186, 146), size=8, up=140,
                  dur=0.25)
    if 12.45 < t < 13.7:   # épaisseur : 1 cm
        x0 = SURF[0] + SRX + 30
        d = ImageDraw.Draw(u)
        a = life(t, 12.47)
        if a > 0.01:
            d.line([(x0, SURF[1] - 18), (x0, SURF[1] + 18)], fill=DARK, width=8)
            d.line([(x0 - 14, SURF[1] - 18), (x0 + 14, SURF[1] - 18)], fill=DARK, width=8)
            d.line([(x0 - 14, SURF[1] + 18), (x0 + 14, SURF[1] + 18)], fill=DARK, width=8)
        tag(u, "1 CM", 900, SURF[1] - 190, t, 12.47, 13.62, rot=-5, size=60, string_to=(x0, SURF[1]))
    # la loupe : les larves dans le terreau humide
    g = life(t, 6.15, 8.3, dur=0.35)
    if g > 0.01:
        lx, ly, r = LENS[0], LENS[1], LENS[2] * g
        lens = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        src = w.crop((int(SURF[0] - SRX * 0.55), int(SURF[1] - SRY * 0.55), int(SURF[0] + SRX * 0.55),
                      int(SURF[1] + SRY * 0.55))).resize((int(2.4 * LENS[2]), int(2.4 * LENS[2])), Image.BICUBIC)
        lens.alpha_composite(src, (int(lx - src.width / 2), int(ly - src.height / 2)))
        for i, (dx, dy) in enumerate([(-90, -70), (70, 10), (-30, 100)]):
            larve(lens, lx + dx * g, ly + dy * g, 230 * g, t, i)
        if t > 6.83:
            for i in range(6):
                tt = (t - 6.83 - i * 0.07) % 0.6
                put(lens, icon("drop", 34), lx - 150 + i * 60, ly - r + tt / 0.6 * r * 1.6, g, 0, 1 - tt / 0.6)
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).ellipse([lx - r, ly - r, lx + r, ly + r], fill=255)
        lens.putalpha(Image.composite(lens.getchannel("A"), Image.new("L", (W, H), 0), m))
        u.alpha_composite(lens)
        d = ImageDraw.Draw(u)
        hx, hy = lx + r * 0.72, ly + r * 0.72
        d.line([(hx, hy), (hx + 150 * g, hy + 150 * g)], fill=DARK, width=int(46 * g))
        d.line([(hx + 10, hy + 10), (hx + 140 * g, hy + 140 * g)], fill=(150, 90, 50), width=int(30 * g))
        d.ellipse([lx - r - 14, ly - r - 14, lx + r + 14, ly + r + 14], outline=DARK, width=int(30 * g))
        d.ellipse([lx - r - 6, ly - r - 6, lx + r + 6, ly + r + 6], outline=(190, 196, 200), width=int(12 * g))
        if t > 6.3:
            tag(u, "LARVES", 860, 480, t, 6.3, 8.2, rot=-6, size=56, string_to=(lx + 60, ly - 40))
    # séchage : soleil + calendrier d'arrosage
    if 9.05 < t < 11.25:
        put(u, icon("sun", 170), 880, 560, life(t, 9.1, 11.2), t * 30)
    if 10.07 < t < 11.25:
        pills(u, ["ARROSAGE", "SÈCHE", "ARROSAGE"], min(2, int((t - 10.1) / 0.33)), t, 10.07, 11.2, y=470, x=540,
              pw=300)
    # plus de ponte : un moucheron se pose sur le sable… interdit
    if t > 13.67:
        q = ease_out((t - 13.67) / 0.45)
        gx, gy = lerp(1150, SURF[0] + 40, q), lerp(500, SURF[1] - 30, q) - math.sin(math.pi * q) * 80
        gnat(w, gx, gy, 150, -1, 1)
        put(u, icon("nosign", 260), SURF[0] + 40, SURF[1] - 50, life(t, 14.3))
    put(u, num_badge("1", 150), 140, 470, life(t, 8.5, 10.0))
    put(u, num_badge("2", 150), 140, 470, life(t, 11.3, 14.9))
    title(u, "LEURS LARVES…", t, 6.0, 6.8, y=330, size=160)
    title(u, "ADORENT L'HUMIDE", t, 6.83, 8.3, y=330, color=YEL, size=125)
    title(u, "LAISSE SÉCHER", t, 8.47, 10.02, y=330, size=150)
    title(u, "ENTRE 2 ARROSAGES", t, 10.07, 11.25, y=330, color=YEL, size=118)
    title(u, "RECOUVRE DE SABLE", t, 11.31, 13.6, y=330, size=120)
    stamp(u, "PLUS DE PONTE !", 540, 340, t, 13.67, None, RED, 118, -6)
    return w, u


cue(5.99, "pop", 0.22)
cue(6.2, "pop_hi", 0.2)
cue(6.9, "plop", 0.2)
cue(9.12, "rise", 0.18)
cue(10.1, "tick", 0.2)
cue(10.43, "tick", 0.2)
cue(10.76, "tick", 0.2)
cue(11.45, "pour", 0.3)
cue(12.5, "pop", 0.2)
cue(13.7, "buzz", 0.22)
cue(14.32, "alert2", 0.28)


# ============================================================ E. BONUS : LE PIÈGE AU VINAIGRE DE CIDRE (15.0 → 21.3)
B_X, B_BOT, B_W = 540, TABLE + 60, 700          # bol (cadre 1024)
B_BB = (217, 276, 807, 785)
B_K = B_W / (B_BB[2] - B_BB[0])
LIQ = (B_X + (510 - 512) * B_K, B_BOT + (470 - B_BB[3]) * B_K)    # milieu du liquide


@lru_cache(None)
def soap_drop(size=90):
    im = icon("drop", size).copy()
    a = np.asarray(im).astype(float)
    blue = (np.abs(a[..., 0] - BLUE[0]) < 40) & (np.abs(a[..., 2] - BLUE[2]) < 40) & (a[..., 3] > 0)
    a[blue, :3] = (120, 200, 90)
    return Image.fromarray(a.astype("uint8"))


def s_bonus(t):
    w, u = new_layers(background("table"))
    s_ = life(t, 16.15, dur=0.35)
    shadow(w, B_X, B_BOT, B_W * 0.8 * s_)
    ob(w, BOL, B_X, B_BOT, B_W, anchor="bottom", s=s_)
    # la goutte de liquide vaisselle
    if 18.0 < t < 18.5:
        q = ease_in((t - 18.0) / 0.4)
        put(u, soap_drop(90), LIQ[0], lerp(300, LIQ[1], q), 1)
    if t > 18.4:
        r = 60 + 260 * ease_out((t - 18.4) / 0.8)
        a = fade(t, 18.4, 19.3, 0.05, 0.4)
        if a > 0.01:
            ImageDraw.Draw(w).ellipse([LIQ[0] - r, LIQ[1] - r * 0.4, LIQ[0] + r, LIQ[1] + r * 0.4],
                                      outline=(255, 245, 220, int(200 * a)), width=6)
    # les moucherons plongent dedans
    if t > 19.6:
        for i in range(7):
            t0 = 19.65 + i * 0.12
            q = ease_in((t - t0) / 0.55)
            if q <= 0:
                sx = -100 if i % 2 == 0 else 1180
                x, y = sx, 600 + i * 70
            else:
                sx = -100 if i % 2 == 0 else 1180
                ex, ey = LIQ[0] + (i - 3) * 55, LIQ[1] + (i % 3 - 1) * 25
                x, y = lerp(sx, ex, q), lerp(600 + i * 70, ey, q) - math.sin(math.pi * q) * 200
            if q < 1:
                gnat(w, x, y, 160, 1 if i % 2 == 0 else -1, i, rot=-25 * q if i % 2 == 0 else 25 * q)
            elif t - t0 - 0.55 < 0.35:
                particles(w, t, t0 + 0.55, LIQ[0] + (i - 3) * 55, LIQ[1] + (i % 3 - 1) * 25, 6, i, col=(220, 150, 60),
                          size=7, up=150, dur=0.35)
    if t > 16.95:
        tag(u, "VINAIGRE DE CIDRE", 300, 640, t, 16.95, None, rot=-5, size=50, string_to=(LIQ[0] - 60, LIQ[1] - 30))
    if t > 18.07:
        tag(u, "+ 1 GOUTTE DE LIQUIDE VAISSELLE", 560, 790, t, 18.1, None, rot=4, size=38)
    stamp(u, "BONUS !", 540, 340, t, 15.15, 16.1, YEL, 170, -8)
    title(u, "UN PETIT VERRE", t, 16.19, 16.9, y=330, size=150)
    title(u, "DE VINAIGRE DE CIDRE", t, 16.95, 18.0, y=330, color=YEL, size=112)
    title(u, "+ LIQUIDE VAISSELLE", t, 18.07, 19.62, y=330, size=118)
    title(u, "ILS PLONGENT !", t, 19.67, None, y=330, color=YEL, size=150)
    return w, u


cue(15.17, "ding", 0.3)
cue(16.2, "pop", 0.22)
cue(17.0, "pop_hi", 0.18)
cue(18.38, "plop", 0.32)
cue(19.7, "buzz", 0.25)
for _i in range(0, 7, 2):
    cue(20.2 + _i * 0.12, "plop", 0.16)
cue(20.9, "success", 0.28)


# ============================================================ F. LE SALON SANS MOUCHERONS + ABONNE-TOI (21.3 → fin)
def s_end(t):
    w = salon(t, gnats=False)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w = zoomed(w, 1.25, 660, 1100)
    w.alpha_composite(shade())
    sparkles(u, t, 21.4, 560, 760, 340, 10, 7)
    clicked = t > 22.7
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 22.65) / 0.15))
    put(u, btn, 540, 1340, life(t, 21.45) * press)
    if t > 22.2:
        k = ease_out((t - 22.2) / 0.4)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(1600, 1380, k), 1)
    put(u, logo_img(260), 540, 330, life(t, 23.45, dur=0.45))
    sparkles(u, t, 23.55, 540, 330, 200, 10, 12)
    title(u, "ADIEU MOUCHERONS !", t, 21.35, 23.4, y=330, color=YEL, size=118)
    return w, u


cue(21.37, "pop_lo", 0.3)
cue(22.68, "click", 0.45)
cue(23.55, "sparkle", 0.25)

SCENES = [
    (0.0, 5.97, s_salon),
    (5.97, 15.0, s_pot),
    (15.0, 21.3, s_bonus),
    (21.3, 99.0, s_end),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []
