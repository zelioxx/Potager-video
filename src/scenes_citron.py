"""Storyboard « Faire germer un pépin de citron » (voix : assets/audio/citron/voix.mp3).

Décors photo fournis : frigo (les deux citrons en sortent), plan de travail avec planche (citron coupé, pépin,
sopalin, boîte transparente), buffet (boîte au chaud, pot avec la pousse, citronnier). Objets détourés fournis :
citron, citron coupé, pépin avec / sans peau, pépin germé, pépin avec feuilles, sopalin, boîte ouverte / fermée
(rendues transparentes), pot de terreau, citronnier. Si assets/video/intro_citron.mp4 existe, la première phrase
montre cette vidéo brute.
"""
import math
import os
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (ROOT, IMG, W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, background, spr, put, title, life, fade,
                 ease_out, ease_io, clamp, lerp, icon, pills, tag, button_img, hl_ellipse, particles, text_img,
                 light_rays, F_TITLE)
from scenes import TABLE, new_layers, sparkles
from scenes_ananas import place, logo_img
from scenes_hortensia import stamp
from scenes_mangue import warm_glow

CUES = []
FPS = 30


def cue(t, name, gain=0.5):
    CUES.append((t, name, gain))


A = "citron/"
FULL = (0, 0, 1254, 1254)
SRC = os.path.join(ROOT, "assets", "images", "source_utilisateur")
VIDEO = os.path.join(ROOT, "assets", "video", "intro_citron.mp4")
HAS_VIDEO = os.path.exists(VIDEO)


def video_duration():
    if not HAS_VIDEO:
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                         capture_output=True, text=True).stdout
    return min(3.4, float(out.strip() or 0))


VID_END = video_duration()
NO_CAPTION_UNTIL = VID_END


@lru_cache(None)
def video_frames():
    d = os.path.join(ROOT, "output", "tmp_citron_intro")
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


# ------------------------------------------------------------- outils : décors photo, zoom caméra, objets
@lru_cache(None)
def shade():
    """Dégradés sombres en haut (titres) et en bas (sous-titres) pour la lisibilité sur photo."""
    a = np.zeros((H, 1), np.float32)
    y = np.arange(H)
    a[:, 0] = np.clip((520 - y) / 520, 0, 1) ** 1.5 * 90 + np.clip((y - 1330) / 590, 0, 1) ** 1.3 * 120
    im = Image.new("RGBA", (W, H), (20, 18, 14, 0))
    im.putalpha(Image.fromarray(np.repeat(a, W, 1).astype("uint8")))
    return im


@lru_cache(None)
def photo(name):
    p = os.path.join(SRC, name)
    return Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS).convert("RGBA")


LEMONS = [(505, 976, 118), (612, 979, 118)]      # citrons dans le frigo : centre et largeur (écran)


@lru_cache(None)
def fridge_empty():
    """Frigo sans les deux citrons (trou rempli par diffusion des pixels voisins)."""
    im = np.asarray(photo("citron_fond_frigo.jpg").convert("RGB")).astype(np.float32)
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for x, y, w_ in LEMONS:
        d.ellipse([x - w_ / 2 - 8, y - w_ * 0.43 - 8, x + w_ / 2 + 8, y + w_ * 0.43 + 10], fill=255)
    from scipy.ndimage import gaussian_filter
    mask = np.asarray(m) > 0
    valid = (~mask).astype(np.float32)
    out = im.copy()
    for sig in (45, 18):
        wv = gaussian_filter(valid, sig)
        fill = np.stack([gaussian_filter(out[..., i] * valid, sig) for i in range(3)], -1) / np.maximum(wv, 1e-6)[..., None]
        out[mask] = fill[mask]
    return Image.fromarray(np.clip(out, 0, 255).astype("uint8")).convert("RGBA")


def zoomed(img, z, fx, fy):
    """Zoom caméra : agrandit `img` d'un facteur z autour du point (fx, fy), sans sortir du cadre."""
    if z <= 1.001:
        return img
    cw, ch = W / z, H / z
    x0 = min(max(fx - cw / 2, 0), W - cw)
    y0 = min(max(fy - ch / 2, 0), H - ch)
    return img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BICUBIC)


def obj(c, name, bbox, X, Y, width, s=1.0, rot=0.0, alpha=1.0):
    """Objet détouré centré en (X, Y), de largeur `width` à l'écran."""
    k = width / (bbox[2] - bbox[0])
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    place(c, A + name, FULL, k, cx, cy, X, Y, s, rot, 0.0, alpha)   # cadre 1254 complet (proportions exactes)


def shadow(c, X, Y, w_, a=70):
    if w_ <= 2:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse([X - w_ / 2, Y - w_ * 0.09, X + w_ / 2, Y + w_ * 0.09], fill=(60, 40, 22, a))
    c.alpha_composite(ov.filter(ImageFilter.GaussianBlur(6)))


def swap(p):
    """Changement d'image sans superposition : tassement, bascule au plus petit, rebond."""
    p = clamp(p)
    if p < 0.5:
        return 0, 1 - 0.12 * ease_io(p * 2)
    q = (p - 0.5) * 2
    return 1, 0.88 + 0.12 * q + 0.04 * math.sin(math.pi * q)


BB = {"citron": (131, 224, 1117, 973), "citron_coupe": (52, 289, 1208, 919), "pepin_nu": (306, 268, 1018, 934),
      "pepin_peau": (218, 177, 1137, 992), "pepin_germe": (271, 187, 940, 1067),
      "pepin_feuilles": (292, 44, 1065, 1225), "sopalin": (186, 149, 1073, 1106),
      "boite_ouverte": (189, 355, 1079, 975), "boite_fermee": (218, 352, 1051, 957),
      "pot_vide": (286, 245, 969, 1029), "citronnier": (249, 25, 1057, 1219)}


def o(c, name, X, Y, width, s=1.0, rot=0.0, alpha=1.0):
    obj(c, name, BB[name], X, Y, width, s, rot, alpha)


@lru_cache(64)
def sop_img(wq, hq, wet_q):
    im = Image.open(os.path.join(IMG, A + "sopalin.png")).convert("RGBA").crop(BB["sopalin"])
    im = im.resize((wq, hq), Image.LANCZOS)
    if wet_q:
        sp = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(sp)
        r = np.random.default_rng(5)
        for _ in range(9):
            x, y, rr = r.uniform(0.15, 0.85) * wq, r.uniform(0.15, 0.85) * hq, r.uniform(0.1, 0.18) * wq
            d.ellipse([x - rr, y - rr * hq / wq, x + rr, y + rr * hq / wq], fill=(185, 200, 215, int(5 * wet_q)))
        sp.putalpha(Image.composite(sp.getchannel("A"), Image.new("L", im.size, 0), im.getchannel("A")))
        im.alpha_composite(sp)
    return im


def sopalin(c, X, Y, w_, flat=0.0, wet=0.0, alpha=1.0, rot=0.0):
    """Feuille de sopalin ; flat = 0 vue de face, 1 posée à plat (écrasée en perspective)."""
    if alpha <= 0.01 or w_ < 4:
        return
    h_ = w_ * (1.08 - 0.66 * flat)
    im = sop_img(int(w_), int(h_), int(round(wet * 10)))
    put(c, im, X, Y, 1.0, rot, alpha)


# ============================================================ A. LE FRIGO : TES PÉPINS DE CITRON ? (0 → 3.46)
def s_fridge(t):
    w, u = new_layers(fridge_empty().copy())
    # les deux citrons (photos détourées posées pile sur ceux du frigo), qui sortent vers la caméra
    out = ease_io((t - 2.95) / 0.5)
    for i, (x, y, w_) in enumerate(LEMONS):
        tx, ty = 420 + i * 240, 1050
        X, Y = lerp(x, tx, out), lerp(y, ty, out) - math.sin(math.pi * out) * 160
        hop = abs(math.sin((t - 0.9 - i * 0.12) * 9)) * 10 * fade(t, 0.9, 1.5, 0.05, 0.2) if t > 0.9 else 0
        o(w, "citron", X, Y - hop, w_ * lerp(1.0, 3.0, out), rot=lerp(0, -20 + 40 * i, out))
    if 0.9 < t < 2.95:
        hl_ellipse(u, 558, 978, 150, 85, life(t, 0.95, 2.9))
    w.alpha_composite(shade())
    title(u, "TES PÉPINS DE CITRON ?", t, 0.3, 1.6, y=330, size=120)
    stamp(u, "ARRÊTE !", 540, 360, t, 1.66, 2.4, RED, 140, -8)
    title(u, "CE SONT DES ARBRES !", t, 2.47, None, y=330, color=YEL, size=120)
    if t > 2.5:
        s_ = life(t, 2.55, 3.4)
        if s_ > 0.01:
            d = ImageDraw.Draw(u)
            r = 150 * s_
            d.ellipse([870 - r - 8, 640 - r - 8, 870 + r + 8, 640 + r + 8], fill=DARK)
            d.ellipse([870 - r, 640 - r, 870 + r, 640 + r], fill=CREAM)
            o(u, "citronnier", 870, 650, 150, s_)
    return w, u


cue(0.05, "pop_lo", 0.3)
cue(0.95, "pop_hi", 0.22)
cue(1.66, "thud", 0.4)
cue(1.7, "alert1", 0.3)
cue(2.55, "sparkle", 0.25)
cue(2.95, "whoosh_up", 0.25)


# ============================================================ B. LA CUISINE : UN SEUL PLAN, LA CAMÉRA ZOOME (3.46 → 20.66)
BOARD = (560, 1170)
HALF_R = (640, 1172)          # moitié droite du citron coupé (où sont les pépins), coordonnées du décor
SEED = (560, 1040)            # où se tient le pépin pendant le gros plan
KNIFE = "poireau/knife"


def cam(t):
    """Zoom caméra et point visé selon le moment."""
    k1 = ease_io((t - 6.2) / 0.7)        # vers le pépin
    k2 = ease_io((t - 15.2) / 0.7)       # retour plus large pour le sopalin et la boîte
    z = lerp(lerp(1.0, 1.75, k1), 1.2, k2)
    fx = lerp(lerp(560, 580, k1), 560, k2)
    fy = lerp(lerp(1100, 1060, k1), 1140, k2)
    return z, fx, fy


def peeled(c, X, Y, width, p):
    """Pépin dont la peau blanche glisse : la photo « nu » apparaît d'un bord à l'autre (pas de fantôme)."""
    if p <= 0:
        o(c, "pepin_peau", X, Y, width * 1.18)
        return
    if p >= 1:
        o(c, "pepin_nu", X, Y, width)
        return
    a = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o(a, "pepin_peau", X, Y, width * 1.18)
    o(b, "pepin_nu", X, Y, width)
    cut = X - width * 0.7 + width * 1.4 * p
    ma = Image.new("L", (W, H), 0)
    ImageDraw.Draw(ma).rectangle([cut, 0, W, H], fill=255)
    ma = ma.filter(ImageFilter.GaussianBlur(10))
    a.putalpha(Image.composite(a.getchannel("A"), Image.new("L", (W, H), 0), ma))
    mb = Image.eval(ma, lambda v: 255 - v)
    b.putalpha(Image.composite(b.getchannel("A"), Image.new("L", (W, H), 0), mb))
    c.alpha_composite(b)
    c.alpha_composite(a)


def s_kitchen(t):
    world = photo("citron_fond_cuisine.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # --- 1. le citron atterrit sur la planche puis est coupé (3.46 → 6.1)
    land = ease_out((t - 3.5) / 0.45)
    cut = t > 5.3
    gone = ease_io((t - 8.9) / 0.5)                     # les moitiés s'en vont pendant le gros plan
    if not cut:
        X, Y = BOARD[0], lerp(500, BOARD[1] - 10, land) - math.sin(math.pi * land) * 120
        shadow(world, BOARD[0], BOARD[1] + 70, 200 * land)
        o(world, "citron", X, Y, 210, rot=lerp(-25, 0, land))
        if 4.9 < t < 5.4:   # le couteau tranche
            k = ease_io((t - 4.9) / 0.4)
            spr(world, KNIFE, BOARD[0] + 40, lerp(BOARD[1] - 260, BOARD[1] + 40, k), 110, shadow=False, rot=-4,
                anchor="center")
    elif gone < 1:
        sx = -700 * gone
        shadow(world, BOARD[0] + sx, BOARD[1] + 75, 330)
        o(world, "citron_coupe", BOARD[0] + sx, BOARD[1], 340, s=1.0 if t > 5.55 else 0.9 + 0.1 * ease_out((t - 5.3) / 0.25))
        if t < 5.8:
            particles(world, t, 5.32, BOARD[0], BOARD[1] - 40, 12, 3, col=(250, 225, 90), size=9, up=320)
    # --- 2. un pépin sort de la moitié, puis rinçage (6.9 → 9.0)
    if 6.95 < t < 15.2:
        pop = ease_out((t - 6.95) / 0.5)
        X = lerp(HALF_R[0], SEED[0], pop)
        Y = lerp(HALF_R[1], SEED[1], pop) - math.sin(math.pi * pop) * 120
        width = lerp(20, 120, pop)
        if t < 12.9:
            peeled(world, X, Y, width, ease_io((t - 10.2) / 1.3))
        if 8.3 < t < 9.1:   # rinçage : gouttes d'eau
            for i in range(10):
                tt = (t - 8.3 - i * 0.06) % 0.45
                put(world, icon("drop", 26), SEED[0] - 60 + (i * 37) % 120, lerp(SEED[1] - 220, SEED[1], tt / 0.45),
                    1, 0, 1 - tt / 0.45)
        if 10.2 < t < 11.6:   # petits lambeaux de peau qui tombent
            particles(world, t, 10.3, SEED[0] - 40, SEED[1], 8, 6, col=(245, 240, 220), size=7, up=150, dur=1.1)
        # --- 3. petit secret : 2× plus vite (12.9 → 15.2)
        if t >= 12.9:
            k = ease_out((t - 12.9) / 0.35)
            o(world, "pepin_peau", lerp(SEED[0], SEED[0] - 110, k), SEED[1] + 10, 150 * 1.18 * lerp(1, 0.85, k))
            which, sc = swap((t - 14.05) / 0.35)
            o(world, "pepin_nu" if which == 0 else "pepin_germe", lerp(SEED[0], SEED[0] + 110, k), SEED[1] - 20 * which,
              (150 if which == 0 else 150 * 669 / 712) * lerp(1, 0.85, k) * sc)
    # --- 4. sopalin humide, pépin, boîte transparente, couvercle (15.2 → 20.66)
    BOX = (BOARD[0], BOARD[1] - 40)
    if t > 15.9:
        box_in = ease_out((t - 18.1) / 0.45)
        into = ease_io((t - 18.45) / 0.4)
        # le sopalin (et le pépin) : sur la planche, puis dans le fond de la boîte
        sx = lerp(BOARD[0], BOX[0] - 2, into)
        sy = lerp(BOARD[1], BOX[1] + 95, into)
        sw = lerp(330, 290, into)
        drop = ease_out((t - 16.0) / 0.35)
        if t > 18.0:   # la boîte (fond) arrive par la droite
            bx = lerp(1300, BOX[0], box_in)
            shadow(world, bx, BOX[1] + 175, 560 * min(1, box_in + 0.2))
        flat = ease_io((t - 16.2) / 0.3)
        sopalin(world, sx, lerp(sy - 400, sy, drop), sw, flat, ease_out((t - 17.4) / 0.6),
                drop, rot=lerp(12, 0, drop))
        place_s = ease_out((t - 16.5) / 0.35)
        if t > 16.45:
            o(world, "pepin_nu", sx, lerp(sy - 300, sy - 6, place_s), lerp(110, 100, into), rot=-20)
        if 17.35 < t < 17.9:
            for i in range(8):
                tt = (t - 17.35 - i * 0.05) % 0.4
                put(world, icon("drop", 30), sx - 120 + i * 34, lerp(sy - 300, sy - 20, tt / 0.4), 1, 0, 1)
        if t > 18.0:   # la boîte transparente par-dessus : on voit le sopalin et le pépin à travers
            closed = t > 19.85
            which, sc = swap((t - 19.7) / 0.3)
            if which == 0:
                o(world, "boite_ouverte", lerp(1300, BOX[0], box_in), BOX[1], 600 * sc)
            else:
                o(world, "boite_fermee", BOX[0], BOX[1] - 6, 600 * 833 / 890 * 1.07 * sc)
            if closed:
                tag(u, "FILM TRANSPARENT", 800, 640, t, 20.0, None, rot=-5, size=46)
    # --- caméra
    z, fx, fy = cam(t)
    world = zoomed(world, z, fx, fy)
    world.alpha_composite(shade())
    # --- UI : titres et icônes
    if 12.3 < t < 13.25:
        put(u, icon("lightbulb", 170), 540, 600, life(t, 12.35, 13.2), math.sin(t * 4) * 5)
    if 13.0 < t < 15.15:
        z_, fx_, fy_ = cam(t)
        for dx, lab, col in ((-110, "AVEC PEAU", CREAM), (110, "SANS PEAU", YEL)):
            sx_ = (SEED[0] + dx - (min(max(fx_ - W / z_ / 2, 0), W - W / z_))) * z_
            sy_ = (SEED[1] + 110 - (min(max(fy_ - H / z_ / 2, 0), H - H / z_))) * z_
            put(u, text_img(lab, F_TITLE, 46, col, 6, DARK, 5, DARK), sx_, sy_, life(t, 13.1, 15.1), -3)
    if t > 14.1 and t < 15.15:
        tag(u, "2× PLUS VITE !", 760, 640, t, 14.1, 15.1, rot=-5, size=58)
    if 9.6 < t < 12.2:
        tag(u, "PEAU BLANCHE", 780, 640, t, 9.65, 12.1, rot=-5, size=50)
    title(u, "SUPER SIMPLE !", t, 4.3, 6.0, y=330, color=YEL, size=150)
    title(u, "DES PÉPINS BIEN FRAIS", t, 6.9, 8.25, y=330, size=115)
    title(u, "RINCE-LES", t, 8.3, 9.55, y=330, color=YEL, size=160)
    title(u, "RETIRE LA PEAU", t, 9.62, 12.25, y=330, size=145)
    title(u, "PETIT SECRET", t, 12.34, 13.25, y=330)
    title(u, "ÇA GERME 2× PLUS VITE", t, 13.3, 15.1, y=330, color=YEL, size=110)
    title(u, "SOPALIN HUMIDE", t, 16.14, 17.62, y=330, size=140)
    title(u, "DANS UNE BOÎTE", t, 17.86, 19.6, y=330, color=YEL, size=140)
    title(u, "BIEN FERMÉE", t, 19.7, None, y=330, size=150)
    return world, u


cue(3.55, "thud", 0.35)
cue(4.95, "chop", 0.5)
cue(6.25, "whoosh", 0.16)
cue(7.0, "pop", 0.25)
cue(8.35, "splash", 0.3)
cue(10.25, "squish", 0.25)
cue(12.38, "sparkle", 0.25)
cue(14.1, "rise", 0.22)
cue(16.05, "whoosh", 0.16)
cue(16.5, "pop_lo", 0.22)
cue(17.4, "plop", 0.25)
cue(18.15, "whoosh", 0.16)
cue(19.75, "click", 0.4)


# ============================================================ C. LE BUFFET : AU CHAUD, À LA LUMIÈRE, ÇA POUSSE (20.66 → 26.95)
TOP = (560, 795)                 # dessus du buffet, entre la bougie et le diffuseur


def potted(c, X, Y, grow):
    """Pot de terreau ; la jeune pousse ne dépasse que par le haut (le pépin reste sous la terre)."""
    k = 230 / (BB["pot_vide"][2] - BB["pot_vide"][0])
    pb = BB["pot_vide"]
    shadow(c, X, Y, 260)
    place(c, A + "pot_vide", FULL, k, (pb[0] + pb[2]) / 2, pb[3], X, Y)
    soil_y = Y - (pb[3] - 400) * k            # surface de la terre (centre)
    if grow > 0.01:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fb = BB["pepin_feuilles"]
        fk = 340 / (fb[3] - fb[1]) * lerp(0.6, 1.0, grow)
        # repère : jonction pépin / tige (≈ 760, 470) placée sous la surface ; seule la tige feuillée dépasse
        place(lay, A + "pepin_feuilles", FULL, fk, 790, 470, X - 6, soil_y + lerp(70, 10, grow), 1.0, -12)
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle([0, 0, W, int(soil_y + 4)], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(2))
        lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), m))
        c.alpha_composite(lay)


def scent(c, X, Y, t, a):
    """Petites volutes « ça sent le citron »."""
    if a <= 0.01:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(3):
        x0 = X - 120 + i * 120
        ph = (t * 0.7 + i * 0.3) % 1.0
        pts = [(x0 + 18 * math.sin(j * 0.6 + t * 4 + i), Y - j * 16 - ph * 80) for j in range(12)]
        d.line(pts, fill=(250, 215, 40, int(220 * a * (1 - ph))), width=9, joint="curve")
    c.alpha_composite(ov)


def s_buffet(t):
    w = photo("citron_fond_buffet.png").copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    warm_glow(w, fade(t, 21.9, 23.3, 0.5, 0.5))
    light_rays(w, 260, 0, t, fade(t, 22.4, 23.5, 0.5, 0.5))
    pot_t = 24.75
    tree_p = (t - 26.15) / 0.4
    if t < pot_t:
        # la boîte fermée posée sur le buffet ; à travers, le pépin germe
        land = ease_out((t - 20.75) / 0.4)
        bx, by = TOP[0], lerp(TOP[1] - 500, TOP[1] - 100, land)
        shadow(w, TOP[0], TOP[1], 330 * land)
        sopalin(w, bx, by + 78, 235, 1.0, 1.0)
        germ = ease_io((t - 23.6) / 0.6)
        if germ < 0.5:
            o(w, "pepin_nu", bx, by + 72, 70 * (1 - 0.15 * ease_io(germ * 2)), rot=-20)
        else:
            o(w, "pepin_germe", bx, by + 58, 80 * (0.85 + 0.15 * (germ - 0.5) * 2), rot=-10)
        o(w, "boite_fermee", bx, by, 420)
    elif tree_p < 0.5:
        s = 1.0 if tree_p < 0 else 1 - 0.12 * ease_io(tree_p * 2)
        drop = ease_out((t - pot_t) / 0.4)
        potted(w, TOP[0], lerp(TOP[1] - 400, TOP[1], drop) if drop < 1 else TOP[1], ease_out((t - 25.0) / 0.9))
    else:
        q = clamp((tree_p - 0.5) * 2)
        sc = 0.88 + 0.12 * q + 0.04 * math.sin(math.pi * q)
        cb = BB["citronnier"]
        k = 560 / (cb[3] - cb[1]) * sc
        shadow(w, TOP[0], TOP[1], 300)
        place(w, A + "citronnier", FULL, k, (cb[0] + cb[2]) / 2, cb[3], TOP[0], TOP[1])
        scent(u, TOP[0], TOP[1] - 560, t, fade(t, 26.3, None, 0.3))
        sparkles(u, t, 26.3, TOP[0], TOP[1] - 300, 330, 10, 7)
    w.alpha_composite(shade())
    put(u, icon("thermo", 140), 180, 1180, life(t, 21.95, 23.3))
    put(u, icon("sun", 160), 900, 1180, life(t, 22.5, 23.3), t * 25)
    if 23.4 < t < 24.7:
        act = min(2, int((t - 23.45) / 0.35))
        pills(u, ["S1", "S2", "S3"], act, t, 23.4, 24.7, y=1180, pw=170)
    title(u, "AU CHAUD", t, 21.9, 22.4, y=1300, color=YEL, size=160)
    title(u, "ET À LA LUMIÈRE", t, 22.45, 23.3, y=1300, color=YEL, size=135)
    title(u, "2 À 3 SEMAINES…", t, 23.38, 24.7, y=1300, size=140)
    title(u, "DE PETITES FEUILLES", t, 24.8, 26.1, y=1300, color=YEL, size=120)
    title(u, "QUI SENTENT LE CITRON", t, 26.15, None, y=1300, color=YEL, size=110)
    return w, u


cue(20.8, "thud", 0.3)
cue(21.95, "rise", 0.2)
cue(22.5, "sparkle", 0.2)
for _k in range(3):
    cue(23.45 + _k * 0.35, "tick", 0.25)
cue(23.65, "pop_hi", 0.22)
cue(24.8, "pop_lo", 0.3)
cue(26.2, "success", 0.35)


# ============================================================ D. CTA (26.95 → fin)
def s_cta(t):
    w, u = new_layers(background("table"))
    cb = BB["citronnier"]
    place(w, A + "citronnier", FULL, 520 / (cb[3] - cb[1]), (cb[0] + cb[2]) / 2, cb[3], 270, TABLE + 40, life(t, 27.0))
    o(w, "citron", 740, TABLE - 40, 230, life(t, 27.1))
    o(w, "pepin_feuilles", 960, TABLE - 120, 110, life(t, 27.2), rot=-10)
    clicked = t > 27.6
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 27.55) / 0.15))
    put(u, btn, 540, 300, life(t, 27.05) * press)
    if t > 27.25:
        k = ease_out((t - 27.25) / 0.3)
        put(u, icon("cursor", 110), lerp(900, 640, k), lerp(580, 340, k), 1)
    put(u, logo_img(330), 540, 590, life(t, 28.6, dur=0.45))
    sparkles(u, t, 28.7, 540, 590, 230, 10, 12)
    return w, u


cue(27.58, "click", 0.45)
cue(28.7, "sparkle", 0.25)

if HAS_VIDEO:
    _intro = [(0.0, VID_END, s_video), (VID_END, 3.46, s_fridge)]
else:
    _intro = [(0.0, 3.46, s_fridge)]

SCENES = _intro + [
    (3.46, 20.66, s_kitchen),
    (20.66, 26.95, s_buffet),
    (26.95, 99.0, s_cta),
]

# bruitages allégés : un son par action, rien dans les 0,4 s autour des transitions
TRANS_GAIN = 0.26

TRAPS = []

if HAS_VIDEO:
    CUES[:] = [c for c in CUES if c[0] >= VID_END - 0.05]
