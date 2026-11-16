"""Storyboard « Faire mûrir les tomates vertes » (voix : assets/audio/tomates_vertes/voix.wav).

Décors fournis : le potager en carrés devant la maison (le pied de tomate est planté dans le carré vide), le salon
(grande table en chêne). Objets : planches fournies (tomates, papier journal, banane, cagette), agrandies ×4 (EDSR)
puis détourées ; le pied de tomate détouré sans son pot.
0–5.85    le potager en novembre (lumière froide) : le pied chargé de tomates vertes ; zoom lent sur la grappe.
5.85–9.45 cueille-les avant le gel : le givre gagne, une main cueille la plus belle tomate.
9.45–14.1 le salon : la tomate s'enveloppe dans le journal, puis les boules rejoignent la cagette, au chaud.
14.1–19.8 le secret : une banane bien mûre dans la cagette ; son gaz (éthylène) enveloppe les tomates.
19.8–22.5 une à deux semaines plus tard : on déballe, elle est rouge !
22.5–fin  la cagette de tomates rouges ; bouton S'abonner et logo.
"""
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, put, title, life, fade, ease_out, ease_io, ease_in,
                 ease_out_back, clamp, lerp, icon, tag, button_img, particles, text_img, F_TITLE, pills)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade, shadow, swap
from scenes_banane import ob
from scenes_fumier import Cam, decor, snowfall
from scenes_gland import hand_at
from scenes_feuilles_feu import _puffs
from scenes_arrosage_soir import thermo_cold

CUES = []
NO_CAPTION_UNTIL = 0.0
CAP_STYLE = dict(max_words=4, max_chars=24, size=90)
SFX_GAIN = 0.27
DUCK = 0.45
TRANS_GAIN = 0.22
SHIFT = 0.25


def cue(t, name, gain=0.5):
    CUES.append((t - SHIFT, name, gain))


B = "banque/"
POTAGER, SALON = "decor_potager_bacs_neige.png", "decor_salon_table_bois.webp"     # le potager déjà en hiver
PIED, PIED_C = B + "pied_tomate", B + "pied_tomate_cueillie"
PIED_PLUS = B + "pied_tomate_plus"               # le pied + une tomate verte accrochée sous la grappe (celle qu'on cueille)
GRAPPE = B + "tomate_verte_grappe"
VERTE, ROUGE, BOULE = B + "tomate_verte", B + "tomate_rouge", B + "tomate_journal_boule"
VERTE_J, ROUGE_J, BANANE, CAGETTE = (B + "tomate_verte_journal", B + "tomate_rouge_journal", B + "banane_mure",
                                     B + "cagette")

# --- le pied de tomate (cadre 2048 : bbox x 564–1483, y 64–1984 ; bas de la motte 1984)
P_BASE = (560, 1270)                             # planté dans le grand carré enneigé (photo plein écran)
P_H = 760                                        # hauteur à l'écran (zoom 1)
PK = P_H / 1920
P_BB_W = 1483 - 564
TOM = (1018, 1410)                               # la tomate ajoutée, cueillie (cadre 2048), rayon 64
TOM_R = 64


def pied_xy(fx, fy):
    """Point du cadre 2048 du pied → photo plein écran."""
    return P_BASE[0] + (fx - 1023.5) * PK, P_BASE[1] + (fy - 1984) * PK


TOM_W = pied_xy(*TOM)                            # la tomate, dans la photo


def november(im, k=1.0, frost_k=0.0):
    """Lumière de novembre : froide et un peu grise ; givre (bords blanchis, bleu) si frost_k > 0."""
    a = np.asarray(im.convert("RGB"), np.float32)
    lum = a.mean(2, keepdims=True)
    a = a * (1 - 0.28 * k) + lum * 0.28 * k
    a = a * (1 + k * (np.array([0.9, 0.96, 1.06], np.float32) - 1))
    if frost_k > 0.01:
        yy, xx = np.ogrid[:H, :W]
        v = np.clip((np.hypot((xx - W / 2) / (W * 0.55), (yy - H / 2) / (H * 0.55)) - 0.62) / 0.45, 0, 1)
        g = _frost_grain()
        f = np.clip(v * 0.9 * frost_k + (g - 0.5) * 0.35 * v * frost_k, 0, 0.6)[..., None]
        a = a * (1 - f) + np.array([232, 242, 255], np.float32) * f
        a = a * (1 + 0.3 * frost_k * (np.array([0.88, 0.95, 1.1], np.float32) - 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


_FG = None


def _frost_grain():
    global _FG
    if _FG is None:
        from scipy.ndimage import gaussian_filter
        r = np.random.default_rng(3)
        g = 0.6 * gaussian_filter(r.standard_normal((H, W)), 3) + 0.4 * gaussian_filter(r.standard_normal((H, W)), 0.8)
        _FG = ((g - g.min()) / (g.max() - g.min())).astype(np.float32)
    return _FG


# ============================================================ A. LE POTAGER EN NOVEMBRE (0 → 5.85)
CAM_A0, CAM_A1 = (1.08, 600, 1000), (2.1, TOM_W[0] + 20, TOM_W[1] + 40)


@lru_cache(2)
def garden_hd(picked):
    """Le potager enneigé avec le pied planté, composé une fois en haute définition (2 × l'écran) : la caméra
    recadre ensuite cette image d'un seul tenant, le pied ne « tremble » plus pendant les zooms."""
    import os
    from scenes_citron import photo_hd, _hd_path, photo
    base = (photo_hd(POTAGER) if os.path.exists(_hd_path(POTAGER)) else
            photo(POTAGER).resize((2 * W, 2 * H), Image.LANCZOS)).copy()
    x, y = 2 * P_BASE[0], 2 * P_BASE[1]
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    r = P_BB_W * PK * 2 * 0.55
    ImageDraw.Draw(sh).ellipse([x - r, y - r * 0.16, x + r, y + r * 0.16], fill=(40, 30, 25, 110))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    ob(base, PIED if picked else PIED_PLUS, x, y, P_BB_W * PK * 2, anchor="bottom")
    return base


def garden(cam, picked=False):
    cw, ch = W / cam.z, H / cam.z
    return garden_hd(picked).resize((W, H), Image.LANCZOS,
                                    box=(2 * cam.x0, 2 * cam.y0, 2 * (cam.x0 + cw), 2 * (cam.y0 + ch)))


def s_potager(t):
    k = ease_io(clamp((t - 0.5) / 2.3))             # zoom plus franc (≈ 2,3 s), puis on reste sur la grappe
    cam = Cam(*[lerp(a, b, k) for a, b in zip(CAM_A0, CAM_A1)])
    w = garden(cam)
    snowfall(w, t, 0.7, 70)
    w = november(w, 0.6, 0.45)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 3.6:   # la feuille de journal
        im = Image.new("RGBA", (420, 420), (0, 0, 0, 0))
        ob(im, BOULE, 210, 210, 330)
        put(u, im, 830, 780, life(t, 3.65, 5.75), rot=8)
    title(u, "TES TOMATES SONT VERTES ?", t, 0.05, 2.5, y=330, color=WHITE, size=105)
    stamp(u, "NE LES JETTE PAS !", 540, 340, t, 2.55, 3.55, RED, 120, -6)
    title(u, "UNE FEUILLE DE JOURNAL…", t, 3.6, 5.75, y=330, color=YEL, size=110)
    return w, u


cue(0.08, "whoosh", 0.1)
cue(0.4, "rustle", 0.12)
cue(2.57, "alert1", 0.2)
cue(3.67, "rustle", 0.16)


# ============================================================ B. CUEILLE-LES AVANT LE GEL (5.85 → 9.45)
PICK = (6.55, 7.25, 8.0)                         # arrivée de la main, pincement, la tomate emportée


def s_pick(t):
    cam = Cam(lerp(2.9, 3.1, clamp((t - 5.85) / 3.6)), TOM_W[0] + 30, TOM_W[1] - 20)
    z = cam.z
    picked = t >= PICK[1]
    w = garden(cam, picked)
    tx, ty = cam.p(*TOM_W)
    tw = 2 * TOM_R * PK * z
    hw = tw * 3.4
    if t > PICK[0]:
        if t < PICK[1]:          # la main arrive et saisit la tomate par le haut
            q = ease_out((t - PICK[0]) / (PICK[1] - PICK[0]))
            hand_at(w, lerp(tx - 700, tx, q), lerp(ty - 900, ty - tw * 0.38, q), hw)
        else:                    # elle l'emporte
            q = ease_in(clamp((t - PICK[1] - 0.15) / (PICK[2] - PICK[1])))
            px, py = lerp(tx, tx - 300, q), lerp(ty, ty - 1200, q)
            ob(w, GRAPPE, px, py, tw)
            hand_at(w, px, py - tw * 0.38, hw)
    snowfall(w, t, 0.7, 70)
    frost_k = 0.45 + 0.55 * ease_io(clamp((t - 6.0) / 1.2))
    w = november(w, 0.6, frost_k)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 6.9:
        put(u, thermo_cold(150), 930, 640, life(t, 6.95, 8.1))
        tag(u, "AVANT LE GEL", 760, 790, t, 7.0, 8.1, rot=5, size=54)
    if t > 8.2:
        put(u, icon("check", 150), 880, 720, life(t, 8.25))
    title(u, "D'ABORD…", t, 5.9, 6.5, y=330, color=WHITE, size=180)
    title(u, "CUEILLE-LES AVANT LE GEL", t, 6.55, 8.1, y=330, color=BLUE, size=105)
    title(u, "GARDE LES PLUS BELLES", t, 8.15, None, y=330, color=YEL, size=110)
    return w, u


cue(5.92, "whoosh", 0.1)
cue(6.2, "sparkle", 0.12)
cue(7.27, "pop_lo", 0.18)
cue(7.4, "whoosh_up", 0.1)
cue(8.27, "ding", 0.16)


# ============================================================ C. LE SALON : LE JOURNAL, LA CAGETTE, AU CHAUD (9.45 → 14.1)
TABLE_C = (560, 1560)                            # sur la table du salon (photo plein écran)
CRATE = (540, 1690)                              # bas de la cagette
CRATE_W = 620
CR_BB = (64, 333, 1984, 1715)                    # cagette (cadre 2048)
RIM = [(80, 600), (800, 890), (1970, 550)]       # arête haute des deux faces avant (cadre 2048)
SLOTS = [(560, 660), (930, 760), (1290, 690), (1640, 610), (760, 560), (1130, 520)]   # boules dans la cagette
BANANA_SLOT = (1200, 600)


def crate_pt(cam, fx, fy, base=None):
    base = base or CRATE
    k = CRATE_W / (CR_BB[2] - CR_BB[0])
    x, y = base[0] + (fx - (CR_BB[0] + CR_BB[2]) / 2) * k, base[1] + (fy - CR_BB[3]) * k
    return cam.p(x, y)


def crate(c, cam, items, s=1.0, dx=0.0, base=None):
    """Cagette avec son contenu : la paroi avant passe devant les tomates (elles dépassent juste du bord)."""
    x, y = cam.p(*(base or CRATE))
    x += dx
    cw = CRATE_W * cam.z * s
    shadow(c, x, y - 10, cw * 1.05, 95)
    ob(c, CAGETTE, x, y, cw, anchor="bottom")
    items(c)
    front = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ob(front, CAGETTE, x, y, cw, anchor="bottom")
    k = cw / (CR_BB[2] - CR_BB[0])

    def P(fx, fy):
        return x + (fx - (CR_BB[0] + CR_BB[2]) / 2) * k, y + (fy - CR_BB[3]) * k

    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon([P(*p) for p in RIM] + [P(1990, 1720), P(60, 1720)], fill=255)
    front.putalpha(Image.composite(front.getchannel("A"), Image.new("L", (W, H), 0), m))
    c.alpha_composite(front)


def ball(c, cam, slot, t0, t, s_total=1.0, which=BOULE, w_=None, base=None):
    """Une tomate emballée qui tombe dans la cagette, sur sa place."""
    q = clamp((t - t0) / 0.35)
    if q <= 0:
        return
    x, y = crate_pt(cam, *slot, base=base)
    bw = (w_ or 150) * cam.z * s_total
    yy = lerp(y - 900, y, ease_in(q)) - (14 * cam.z * math.sin(math.pi * clamp((t - t0 - 0.35) / 0.15)) if q >= 1 else 0)
    ob(c, which, x, yy, bw, rot=(slot[0] % 30) - 15)


def warm(im, k):
    if k <= 0.01:
        return im
    a = np.asarray(im.convert("RGB"), np.float32) * (1 + k * (np.array([1.07, 1.0, 0.86], np.float32) - 1))
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([140, 900, 940, 1800], fill=(255, 170, 80, int(70 * k)))
    out.alpha_composite(g.filter(ImageFilter.GaussianBlur(120)))
    return out


def s_wrap(t):
    # 1) gros plan sur la tomate qui s'enveloppe ; 2) on recule : la cagette
    k = ease_io(clamp((t - 11.95) / 0.7))
    cam = Cam(lerp(2.1, 1.45, k), lerp(TABLE_C[0], CRATE[0], k), lerp(TABLE_C[1] - 180, CRATE[1] - 260, k))
    z = cam.z
    w = decor(cam, SALON)
    tx, ty = cam.p(*TABLE_C)
    if t < 12.0:   # la tomate verte → à moitié emballée → boule de journal
        if t < 10.75:
            which, sc = swap((t - 10.45) / 0.3)
            nm = VERTE if which == 0 else VERTE_J
        else:
            which, sc = swap((t - 11.2) / 0.3)
            nm = VERTE_J if which == 0 else BOULE
        s_in = ease_out_back(clamp((t - 9.5) / 0.35), 1.5)
        shadow(w, tx, ty - 4, 170 * z * s_in, 90)
        ob(w, nm, tx, ty, 190 * z * sc * max(0.01, s_in), anchor="bottom")
        if 10.4 < t < 11.6:
            particles(w, t, 10.42, tx, ty - 90 * z, 8, 3, col=(235, 232, 225), size=6, up=160, spread=220, dur=0.4)
    else:
        sl = ease_out(clamp((t - 12.0) / 0.4))

        def items(c):
            for i, slot in enumerate(SLOTS[:5]):
                ball(c, cam, slot, 12.25 + i * 0.16, t)
        crate(w, cam, items, dx=(1 - sl) * 900)
    w = warm(w, fade(t, 13.55, None, 0.5))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 13.6:
        put(u, text_img("20 °C", F_TITLE, 110, RED, stroke=7, stroke_fill=DARK), 860, 720, life(t, 13.62))
    title(u, "ENSUITE…", t, 9.5, 10.3, y=330, color=WHITE, size=180)
    title(u, "ENVELOPPE-LA DANS DU JOURNAL", t, 10.35, 12.0, y=330, color=YEL, size=92)
    title(u, "RANGE-LES DANS UNE BOÎTE", t, 12.05, 13.55, y=330, color=WHITE, size=104)
    stamp(u, "AU CHAUD !", 540, 340, t, 13.6, None, RED, 150, -6)
    return w, u


cue(9.52, "whoosh", 0.12)
cue(9.6, "pop", 0.12)
cue(10.47, "rustle", 0.2)
cue(11.22, "rustle", 0.2)
cue(12.02, "whoosh", 0.1)
for _i in range(5):
    cue(12.6 + _i * 0.16, "thud", 0.1)
cue(13.62, "pop", 0.14)


# ============================================================ D. LE SECRET : UNE BANANE BIEN MÛRE (14.1 → 19.8)
def gas(c, cam, t, t0, a=1.0):
    """Le gaz de la banane (éthylène) : volutes jaune pâle qui montent et enveloppent les tomates."""
    if a <= 0.01 or t < t0:
        return
    bx, by = crate_pt(cam, *BANANA_SLOT)
    r = np.random.default_rng(5)
    pf = []
    for i in range(34):
        p = ((t - t0) * r.uniform(0.25, 0.4) + i / 34) % 1.0
        if p > (t - t0) * 0.7 + 0.05:
            continue
        ang = r.uniform(0, 2 * math.pi)
        rr = 60 + 360 * p
        x = bx + math.cos(ang + t * 0.6) * rr * cam.z * 0.45
        y = by - 40 * cam.z - p * 260 * cam.z + math.sin(ang + t * 0.6) * rr * cam.z * 0.15
        rad = (50 + 130 * p) * cam.z
        pf.append((x, y, rad, rad * 0.75, 0.32 * a * (1 - p) * min(1, p * 8 + 0.2)))
    c.alpha_composite(_puffs(pf, (232, 236, 150)))


def s_banana(t):
    k = ease_io(clamp((t - 17.4) / 1.0))
    cam = Cam(lerp(1.45, 1.75, k), CRATE[0], lerp(CRATE[1] - 260, CRATE[1] - 230, k))
    z = cam.z
    w = decor(cam, SALON)

    def items(c):
        for i, slot in enumerate(SLOTS[:5]):
            ball(c, cam, slot, -10, t)
        q = clamp((t - 15.95) / 0.4)
        if q > 0:
            x, y = crate_pt(cam, *BANANA_SLOT)
            ob(c, BANANE, x, lerp(y - 1000, y, ease_in(q)), 260 * z, rot=lerp(60, -12, q))
    crate(w, cam, items)
    gas(w, cam, t, 17.6, fade(t, 17.6, None, 0.6))
    w = warm(w, 1.0)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if t > 18.0:
        tag(u, "ÉTHYLÈNE", 300, 760, t, 18.05, None, rot=-5, size=62)
        sparkles(u, t, 18.1, 540, 1100, 380, 10, 6)
    title(u, "LE PETIT SECRET…", t, 14.15, 15.35, y=330, color=WHITE, size=160)
    title(u, "UNE BANANE BIEN MÛRE !", t, 15.4, 17.55, y=330, color=YEL, size=112)
    title(u, "SON GAZ ACCÉLÈRE TOUT", t, 17.6, None, y=330, color=GREEN, size=110)
    return w, u


cue(14.17, "pop", 0.14)
cue(15.42, "pop_hi", 0.12)
cue(16.3, "thud", 0.14)
cue(17.65, "rise", 0.16)
cue(18.07, "sparkle", 0.14)


# ============================================================ E. UNE À DEUX SEMAINES : ROUGES ! (19.8 → 22.5)
def s_ripe(t):
    cam = Cam(lerp(1.75, 1.9, clamp((t - 19.8) / 2.7)), CRATE[0], CRATE[1] - 230)
    z = cam.z
    w = decor(cam, SALON)
    reveal = [21.35, 21.5, 21.65, 21.8, 21.95]

    def items(c):
        for i, slot in enumerate(SLOTS[:5]):
            which, sc = swap((t - reveal[i]) / 0.3)
            ball(c, cam, slot, -10, t, s_total=sc * (1.0 if which == 0 else 1.15),
                 which=BOULE if which == 0 else ROUGE_J)
        x, y = crate_pt(cam, *BANANA_SLOT)
        ob(c, BANANE, x, y, 260 * z, rot=-12)
    crate(w, cam, items)
    w = warm(w, 1.0)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if 19.9 < t < 21.4:
        act = 0 if t < 20.6 else 1
        pills(u, ["1 SEMAINE", "2 SEMAINES"], act, t, 19.95, 21.35, y=560, pw=330)
    if t > 21.4:
        sparkles(u, t, 21.42, 540, 1150, 420, 14, 3, dur=1.2)
    title(u, "UNE À DEUX SEMAINES…", t, 19.85, 21.3, y=330, color=WHITE, size=115)
    stamp(u, "ELLES SONT ROUGES !", 540, 340, t, 21.35, None, RED, 110, -6)
    return w, u


cue(19.87, "whoosh", 0.1)
cue(19.95, "tick", 0.12)
cue(20.65, "tick", 0.12)
for _i in range(5):
    cue(21.37 + _i * 0.15, "rustle", 0.08)
cue(21.45, "success", 0.2)


# ============================================================ F. ABONNE-TOI (22.5 → fin)
def s_end(t):
    cam = Cam(1.2, CRATE[0], CRATE[1] - 250)
    z = cam.z
    w = decor(cam, SALON)
    eb = (CRATE[0], CRATE[1] - 160)               # la cagette un peu plus loin sur la table (au-dessus des sous-titres)

    def items(c):
        for slot in SLOTS[:5]:
            ball(c, cam, slot, -10, t, s_total=1.15, which=ROUGE_J, base=eb)
        x, y = crate_pt(cam, *BANANA_SLOT, base=eb)
        ob(c, BANANE, x, y, 260 * z, rot=-12)
    crate(w, cam, items, base=eb)
    # deux tomates rouges posées sur la table, de chaque côté
    for dx, s in ((-330, 0.8), (335, 0.75)):
        x, y = cam.p(eb[0] + dx, eb[1] - 60)
        shadow(w, x, y - 3, 150 * z * s, 90)
        ob(w, ROUGE, x, y, 170 * z * s, anchor="bottom")
    w = warm(w, 1.0)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    clicked = t > 24.0
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 23.95) / 0.15))
    put(u, btn, 540, 1470, life(t, 22.7) * press)
    if t > 23.4:
        kk = ease_out((t - 23.4) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1720, 1510, kk), 1)
    put(u, logo_img(260), 540, 330, life(t, 25.4, dur=0.45))
    sparkles(u, t, 25.5, 540, 330, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 22.6, 25.35, y=330, color=YEL, size=135)
    return w, u


cue(22.62, "pop_lo", 0.16)
cue(23.98, "click", 0.3)
cue(25.5, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 5.85 - SHIFT, _sh(s_potager)),
    (5.85 - SHIFT, 9.45 - SHIFT, _sh(s_pick)),
    (9.45 - SHIFT, 14.1 - SHIFT, _sh(s_wrap)),
    (14.1 - SHIFT, 19.8 - SHIFT, _sh(s_banana)),
    (19.8 - SHIFT, 22.5 - SHIFT, _sh(s_ripe)),
    (22.5 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
