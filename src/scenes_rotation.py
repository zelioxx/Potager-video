"""Storyboard « La rotation au potager » (voix : assets/audio/rotation/voix.wav, volume d'origine).

Décors fournis : le potager en carrés (été, et le même sous la neige). Fond beige pour le plan sur papier.
Images fournies : feuille de papier (vierge / en 4 cases), dessins au crayon (chou, tomate, carotte, pois),
stades de croissance (pois, haricot, carotte, tomate ; planches agrandies ×2 puis détourées avec leur motte).
0–4.45    ton potager rate chaque année : les pieds de tomate dépérissent… parce que tu ne fais jamais ÇA en hiver.
4.45–11.1 tomates toujours au même endroit : année après année, les nutriments s'épuisent, les maladies restent.
11.1–15.2 cet hiver : une feuille, au crayon, 4 zones.
15.2–21.0 feuilles (chou), fruits (tomate), racines (carotte), haricots et pois.
21.0–23.3 chaque année, tu tournes d'une case (les dessins avancent d'une case).
23.3–27.3 bonus : pois et haricots poussent, enrichissent la terre (azote)… pour les légumes suivants.
27.3–fin  le plan sur sa feuille ; bouton S'abonner et logo.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

from gfx import (W, H, YEL, RED, GREEN, CREAM, DARK, WHITE, BLUE, IMG, put, paste, title, life, fade, ease_out,
                 ease_io, ease_in, ease_out_back, clamp, lerp, icon, tag, button_img, text_img, aa, pills, F_TITLE,
                 F_BLACK, light_rays)
from scenes import sparkles
from scenes_ananas import logo_img
from scenes_hortensia import stamp
from scenes_citron import shade, swap
from scenes_fumier import Cam, decor, snowfall
from scenes_pigeons_choux import bedp, bedw
from scenes_pothos_lumiere import soft_shadow

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
ETE, HIVER = "decor_potager_bacs_vides.webp", "decor_potager_bacs_neige.png"
PAPIER, PAPIER4 = B + "feuille_papier", B + "feuille_papier_4cases"
DESSINS = [B + "dessin_chou", B + "dessin_tomate", B + "dessin_carotte", B + "dessin_pois"]
LABELS = ["FEUILLES", "FRUITS", "RACINES", "HARICOTS & POIS"]
BEIGE = (238, 228, 208)


# ------------------------------------------------------------ images
@lru_cache(None)
def _img(name):
    return Image.open(os.path.join(IMG, name + ".png")).convert("RGBA")


@lru_cache(None)
def _foot(name):
    """Pied de la motte (bas de la silhouette, milieu) dans l'image pleine (cadre du quart de planche)."""
    a = np.asarray(_img(name))[..., 3] > 100
    ys, xs = np.nonzero(a)
    yb = ys.max()
    row = xs[ys >= yb - 25]
    return float(row.mean()), float(yb)


@lru_cache(512)
def _stage_sized(name, w, dry):
    im = _img(name)
    k = w / im.width
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    if dry > 0.01:
        im = withered(im, dry / 100)
    return im


def plant(c, name, x, y, w, alpha=1.0, dry=0.0, s=1.0):
    """Un stade de croissance (image entière du quart de planche, même échelle pour tous les stades d'une plante) :
    le pied de la motte posé en (x, y) ; w = largeur du quart de planche à l'écran."""
    if s <= 0.01 or alpha <= 0.01:
        return
    ww = int(w * s)
    im = _stage_sized(name, ww, int(dry * 100))
    fx, fy = _foot(name)
    k = ww / _img(name).width
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    paste(c, im, x - fx * k, y - fy * k)


def withered(im, k):
    """Le feuillage jaunit et brunit (la plante dépérit)."""
    a = np.asarray(im).astype(np.float32)
    rgb = a[..., :3]
    green = rgb[..., 1] > rgb[..., 0] + 6
    tgt = np.array([168, 140, 62], np.float32)
    rgb[green] = rgb[green] * (1 - 0.7 * k) + tgt * 0.7 * k
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def stages(c, nm, x, y, w, q, dry=0.0):
    """Croissance 1 → 4 (q ∈ [0, 3]) sans superposition : on tasse, on change de stade, on rebondit."""
    i = int(min(2, math.floor(q)))
    k, s = swap(q - i) if q < 3 else (1, 1.0)
    idx = i + k + 1 if q < 3 else 4
    plant(c, f"banque/{nm}_{idx}", x, y, w, dry=dry, s=s)


# ------------------------------------------------------------ pied de tomate : sain (stades) ou malade (vraie photo)
SICK = "banque/pied_tomate"         # vraie photo : feuilles jaunies et tachées, motte de terre


@lru_cache(None)
def _bbox_h(name):
    a = np.asarray(_img(name))[..., 3] > 100
    ys = np.nonzero(a.any(1))[0]
    return float(ys.max() - ys.min())


def tomato(c, x, y, ww, state, s=1.0, alpha=1.0):
    """state : « tomate_1…4 » (pied qui pousse, sain) ou SICK ; même hauteur à l'écran qu'un tomate_4 de largeur ww."""
    if state != SICK:
        plant(c, "banque/" + state, x, y, ww, alpha=alpha, s=s)
        return
    h = _bbox_h("banque/tomate_4") * ww / _img("banque/tomate_4").width * s * 0.95
    k = h / _bbox_h(SICK)
    im = _img(SICK)
    fx, fy = _foot(SICK)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    if alpha < 1:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    paste(c, im, x - fx * k, y - fy * k)


def tomato_swap(c, x, y, ww, a, b, q, alpha=1.0):
    """Passe de l'image a à l'image b sans superposition (on tasse, on change, on rebondit)."""
    k, s = swap(q)
    tomato(c, x, y, ww, a if k == 0 else b, s=s, alpha=alpha)


# ------------------------------------------------------------ fond beige et feuille de papier
@lru_cache(None)
def beige():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - 0.22 * np.clip(((xx - W / 2) / W) ** 2 + ((yy - H * 0.48) / H) ** 2, 0, 1) * 2
    a = np.ones((H, W, 3), np.float32) * np.array(BEIGE, np.float32) * v[..., None]
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")


@lru_cache(None)
def paper_parts():
    """La feuille en 4 cases, séparée en : papier sans les traits / traits seuls (pour les tracer au crayon)."""
    im = _img(PAPIER4)
    a = np.asarray(im).astype(np.float32)
    g = a[..., :3].mean(2)
    bg = ndimage.median_filter(g, 15)
    line = np.clip((bg - g - 6) * 8, 0, 255)
    line[a[..., 3] < 250] = 0
    clean = a.copy()
    for ch in range(3):
        clean[..., ch] = np.where(line > 20, ndimage.median_filter(a[..., ch], 15), a[..., ch])
    lines = np.zeros_like(a)
    lines[..., :3] = a[..., :3]
    lines[..., 3] = line
    ys, xs = np.nonzero(line > 120)
    cx = float(np.median(xs[np.abs(ys - np.median(ys)) > 120])) if len(xs) else im.width / 2
    cy = float(np.median(ys[np.abs(xs - cx) > 120])) if len(ys) else im.height / 2
    return (Image.fromarray(clean.astype(np.uint8), "RGBA"), Image.fromarray(lines.astype(np.uint8), "RGBA"),
            cx, cy)


PH = 1060                       # hauteur de la feuille à l'écran
PCX, PCY = 540, 900             # centre de la feuille


def paper_geom(s=1.0):
    clean, lines, cx, cy = paper_parts()
    k = PH * s / clean.height
    x0, y0 = PCX - clean.width * k / 2, PCY - clean.height * k / 2
    return k, x0, y0, (x0 + cx * k, y0 + cy * k), clean.width * k, clean.height * k


@lru_cache(64)
def _paper_img(hpx, vq, hq):
    clean, lines, cx, cy = paper_parts()
    k = hpx / clean.height
    out = clean.resize((int(clean.width * k), hpx), Image.LANCZOS)
    if vq > 0 or hq > 0:      # les traits au crayon : légèrement tremblés, grain de graphite
        px, py = cx * k, cy * k
        ss = 3
        big = Image.new("RGBA", (out.width * ss, out.height * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(big)
        r = np.random.default_rng(2)
        m = 18
        if vq > 0:
            ys = np.linspace(m, m + (out.height - 2 * m) * vq / 100, 60)
            pts = [((px + 1.5 * math.sin(y / 37) + r.uniform(-0.4, 0.4)) * ss, y * ss) for y in ys]
            d.line(pts, fill=(58, 56, 54, 215), width=4 * ss)
        if hq > 0:
            xs = np.linspace(m, m + (out.width - 2 * m) * hq / 100, 60)
            pts = [(x * ss, (py + 1.5 * math.sin(x / 41) + r.uniform(-0.4, 0.4)) * ss) for x in xs]
            d.line(pts, fill=(58, 56, 54, 215), width=4 * ss)
        big = big.resize(out.size, Image.LANCZOS)
        a = np.asarray(big).astype(np.float32)
        g = r.uniform(0.6, 1.0, a.shape[:2])
        a[..., 3] *= g
        out.alpha_composite(Image.fromarray(a.astype(np.uint8), "RGBA"))
    return out


def paper(c, s=1.0, vq=1.0, hq=1.0, rot=0.0):
    """La feuille posée sur le fond beige ; vq / hq : part tracée des traits vertical / horizontal."""
    hpx = int(PH * s)
    im = _paper_img(hpx, int(vq * 100), int(hq * 100))
    sh = Image.new("RGBA", (im.width + 80, im.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([40, 52, 40 + im.width, 52 + im.height], fill=(60, 40, 20, 70))
    sh = sh.filter(ImageFilter.GaussianBlur(16))
    put(c, sh, PCX, PCY + 6, 1.0, rot)
    put(c, im, PCX, PCY, 1.0, rot)


def cell_center(i, s=1.0):
    """Centre de la case i (0 haut-g, 1 haut-d, 2 bas-g, 3 bas-d), légèrement au-dessus pour l'étiquette."""
    k, x0, y0, (cx, cy), pw, ph = paper_geom(s)
    xs = ((x0 + cx) / 2, (cx + x0 + pw) / 2)
    ys = ((y0 + cy) / 2 - 20, (cy + y0 + ph) / 2 - 20)
    return xs[i % 2], ys[i // 2]


@lru_cache(64)
def _drawing(name, hpx, q100):
    im = _img(name)
    k = hpx / im.height
    im = im.resize((max(1, int(im.width * k)), hpx), Image.LANCZOS)
    q = q100 / 100
    if q < 1:          # le trait se dessine de haut en bas
        a = np.asarray(im.getchannel("A")).astype(np.float32)
        yy = np.arange(im.height)[:, None] / im.height
        m = np.clip((q * 1.15 - yy) / 0.15, 0, 1)
        im = im.copy()
        im.putalpha(Image.fromarray((a * m).astype(np.uint8)))
    return im


def drawing(c, i, x, y, q=1.0, s=1.0):
    if q <= 0.01 or s <= 0.01:
        return
    put(c, _drawing(DESSINS[i], int(300 * s), int(q * 100)), x, y)


# ------------------------------------------------------------ le grand carré du potager
def bed_soil_pt(cam, u, v):
    return cam.p(*bedp(u, v))


def disease(c, cam, k, seed=5):
    """Taches de maladie qui gagnent la terre du carré."""
    if k <= 0.01:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    r = np.random.default_rng(seed)
    for i in range(46):
        u, v = r.uniform(0.08, 0.92), r.uniform(0.08, 0.92)
        if r.random() > k:
            continue
        x, y = bed_soil_pt(cam, u, v)
        rr = r.uniform(30, 62) * cam.z * (bedw(v) / 900)
        pts = [(x + math.cos(a) * rr * r.uniform(0.6, 1.3), y + math.sin(a) * rr * 0.45 * r.uniform(0.6, 1.3))
               for a in np.linspace(0, 2 * math.pi, 9)[:-1]]
        d.polygon(pts, fill=(150, 150, 110, 150))
        d.polygon([(px * 0.6 + x * 0.4, py * 0.6 + y * 0.4) for px, py in pts], fill=(200, 200, 170, 170))
    c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.5)))


@lru_cache(None)
def bar_img(p100, lbl, w=560):
    p = p100 / 100
    h = 110

    def f(d, k, _):
        d.rounded_rectangle([8 * k, 14 * k, (w - 2) * k, (h - 2) * k], radius=30 * k, fill=(0, 0, 0, 90))
        d.rounded_rectangle([0, 0, (w - 10) * k, (h - 14) * k], radius=30 * k, fill=CREAM, outline=DARK, width=6 * k)
        x0, x1 = 24 * k, (w - 34) * k
        d.rounded_rectangle([x0, 52 * k, x1, (h - 30) * k], radius=12 * k, fill=(214, 204, 186))
        if p > 0.02:
            d.rounded_rectangle([x0, 52 * k, x0 + (x1 - x0) * p, (h - 30) * k], radius=12 * k,
                                fill=GREEN if p > 0.5 else (RED if p < 0.25 else (236, 140, 50)))
    im = aa(w, h, f, 3)
    t_ = text_img(lbl, F_BLACK, 34, DARK)
    im.alpha_composite(t_, (26, 10))
    return im


# ============================================================ A. TON POTAGER RATE CHAQUE ANNÉE ? (0 → 4.45)
ROW = [(0.27, 0.1), (0.73, 0.12), (0.3, 0.72), (0.7, 0.75)]


def s_fail(t):
    winter = ease_io(clamp((t - 2.3) / 0.6))
    cam = Cam(lerp(1.15, 1.25, clamp(t / 4.4)), 545, 1180)
    w = decor(cam, ETE, HIVER, winter)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if winter < 0.999:      # les pieds sains deviennent, un à un, des pieds malades (vraie photo)
        for j, (u, v) in sorted(enumerate(ROW), key=lambda p: p[1][1], reverse=True):
            x, y = bed_soil_pt(cam, u, v)
            ww = bedw(v) * cam.z * 0.62
            soft_shadow(lay, x, y, ww * 0.45, 70)
            pop = ease_out_back(clamp((t - 0.1 - j * 0.08) / 0.35), 1.4)
            q = clamp((t - 0.95 - j * 0.18) / 0.45)
            if q <= 0:
                tomato(lay, x, y, ww, "tomate_4", s=pop, alpha=1 - winter)
            else:
                tomato_swap(lay, x, y, ww, "tomate_4", SICK, q, alpha=1 - winter)
    w.alpha_composite(lay)
    if winter > 0.01:
        snowfall(w, t, winter)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    if 1.3 < t < 2.3:
        put(u, icon("cross", 170), 880, 640, ease_out_back(clamp((t - 1.35) / 0.3), 1.6) * life(t, 1.35, 2.25))
    title(u, "TON POTAGER RATE", t, 0.05, 2.2, y=300, color=WHITE, size=125)
    title(u, "CHAQUE ANNÉE ?", t, 0.05, 2.2, y=440, color=YEL, size=125)
    title(u, "TU NE FAIS JAMAIS ÇA…", t, 2.25, 3.7, y=330, color=WHITE, size=115)
    stamp(u, "EN HIVER !", 540, 340, t, 3.75, None, BLUE, 160, -6)
    return w, u


cue(0.12, "pop_lo", 0.14)
cue(1.0, "crunch", 0.12)
cue(1.35, "fail", 0.16)
cue(2.3, "whoosh_up", 0.12)
cue(3.77, "thud", 0.2)


# ============================================================ B. TOUJOURS AU MÊME ENDROIT (4.45 → 11.1)
SPOT = (0.5, 0.22)


def s_same(t):
    cam = Cam(lerp(1.1, 1.2, clamp((t - 4.45) / 6.6)), 545, 1180)
    w = decor(cam, ETE)
    x, y = bed_soil_pt(cam, *SPOT)
    ww = bedw(SPOT[1]) * cam.z * 0.78
    nut = 1 - ease_io(clamp((t - 7.4) / 1.8))
    sick = ease_io(clamp((t - 9.45) / 1.0))
    disease(w, cam, sick)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # chaque année, la tomate repousse au même endroit… un peu moins belle
    # une seule croissance sur les 3 années : petit (année 1), moyen (année 2), grand (année 3)… puis il tombe malade
    yr = 0 if t < 5.6 else (1 if t < 6.7 else 2)
    soft_shadow(lay, x, y, ww * 0.45, 80)
    if t < 5.6:
        tomato(lay, x, y, ww, "tomate_1", s=ease_out_back(clamp((t - 4.6) / 0.35), 1.5))
    elif t < 6.7:
        tomato_swap(lay, x, y, ww, "tomate_1", "tomate_2", clamp((t - 5.6) / 0.5))
    elif t < 8.3:
        tomato_swap(lay, x, y, ww, "tomate_2", "tomate_4", clamp((t - 6.7) / 0.5))
    else:
        tomato_swap(lay, x, y, ww, "tomate_4", SICK, clamp((t - 8.3) / 0.6))
    w.alpha_composite(lay)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    w.alpha_composite(shade())
    pills(u, ["ANNÉE 1", "ANNÉE 2", "ANNÉE 3"], yr, t, 4.6, 7.3, y=560, pw=250)
    if 5.75 < t < 7.3:
        put(u, icon("arrow_down", 140), x, y - ww * 1.55 + 18 * math.sin(t * 7), life(t, 5.8, 7.25))
        tag(u, "MÊME ENDROIT", x + 250, y - ww * 1.2, t, 5.85, 7.25, rot=5, size=54)
    if t > 7.35:
        put(u, bar_img(int(nut * 100), "NUTRIMENTS"), 540, 1330, life(t, 7.4, None))
    if t > 9.5:
        tag(u, "MALADIES", 820, 1180, t, 9.55, None, rot=5, size=62)
    title(u, "TES TOMATES…", t, 4.47, 5.7, y=330, color=RED, size=150)
    title(u, "TOUJOURS AU MÊME ENDROIT ?", t, 5.72, 7.35, y=330, color=WHITE, size=96)
    title(u, "LA TERRE S'ÉPUISE", t, 7.4, 9.45, y=330, color=YEL, size=125)
    title(u, "ET LES MALADIES RESTENT", t, 9.47, None, y=330, color=RED, size=100)
    return w, u


cue(4.5, "whoosh", 0.12)
for _t in (4.65, 5.65, 6.75):
    cue(_t, "pop", 0.14)
cue(5.85, "tick", 0.16)
cue(7.45, "fail", 0.12)
cue(8.35, "crunch", 0.12)
cue(9.55, "alert2", 0.16)


# ============================================================ C. UNE FEUILLE, 4 ZONES (11.1 → 15.2)
def s_sheet(t):
    w = beige().copy()
    s = ease_out_back(clamp((t - 11.3) / 0.5), 1.3)
    vq = ease_io(clamp((t - 13.2) / 0.55))
    hq = ease_io(clamp((t - 13.8) / 0.55))
    if s > 0.01:
        paper(w, s, vq, hq, rot=lerp(8, -1.5, clamp((t - 11.3) / 0.5)))
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t > 14.4:
        for i in range(4):
            x, y = cell_center(i)
            put(u, text_img(str(i + 1), F_TITLE, 150, (205, 195, 175)), x, y + 20,
                ease_out_back(clamp((t - 14.4 - i * 0.08) / 0.3), 1.6) * life(t, 14.4, 15.2, out=0.15))
    title(u, "CET HIVER…", t, 11.15, 12.15, y=260, color=GREEN, size=150)
    title(u, "PRENDS UNE FEUILLE", t, 12.18, 13.15, y=260, color=WHITE, size=120)
    title(u, "DIVISE TON POTAGER", t, 13.18, 14.6, y=260, color=WHITE, size=115)
    stamp(u, "EN 4 ZONES !", 540, 270, t, 14.62, None, RED, 140, -6)
    return w, u


cue(11.15, "whoosh", 0.12)
cue(11.35, "rustle", 0.16)
cue(13.2, "squish", 0.08)
cue(13.8, "squish", 0.08)
cue(14.64, "thud", 0.18)


# ============================================================ D. FEUILLES, FRUITS, RACINES, HARICOTS ET POIS (15.2 → 21.0)
ZT = [15.2, 16.65, 17.98, 19.12]


def zones(u, t, t0s, pos=None):
    for i in range(4):
        q = ease_io(clamp((t - t0s[i]) / 0.55))
        if q <= 0.01:
            continue
        x, y = pos[i] if pos else cell_center(i)
        drawing(u, i, x, y - 10, q)
        tag(u, LABELS[i], x, y + 190, t, t0s[i] + 0.2, None, rot=(-4, 4, -3, 3)[i], size=44 if i < 3 else 36)


def s_zones(t):
    w = beige().copy()
    paper(w)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    zones(w, t, ZT)
    title(u, "LÉGUMES FEUILLES", t, 15.22, 16.6, y=260, color=GREEN, size=120)
    title(u, "LÉGUMES FRUITS", t, 16.65, 17.95, y=260, color=RED, size=125)
    title(u, "LÉGUMES RACINES", t, 17.98, 19.1, y=260, color=(214, 120, 40), size=120)
    title(u, "HARICOTS ET POIS", t, 19.12, None, y=260, color=GREEN, size=120)
    for i, t0 in enumerate(ZT):
        x, y = cell_center(i)
        sparkles(u, t, t0 + 0.45, x, y, 170, 6, 3 + i, 0.7)
    return w, u


for _t in ZT:
    cue(_t + 0.02, "rustle", 0.12)
    cue(_t + 0.25, "pop", 0.14)


# ============================================================ E. CHAQUE ANNÉE, TU TOURNES D'UNE CASE (21.0 → 23.3)
CLOCK = [1, 3, 0, 2]            # case suivante dans le sens des aiguilles : 0→1, 1→3, 3→2, 2→0


@lru_cache(None)
def turn_arrow(r=150):
    S = 2 * r + 60
    k = 3
    im = Image.new("RGBA", (S * k, S * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S * k / 2
    R = r * k
    for col, wd in ((DARK, 40), (YEL, 24)):
        d.arc([c - R, c - R, c + R, c + R], 205, 520, fill=col, width=wd * k // 3 * 3)
    a = math.radians(160)
    tx, ty = c + math.cos(a) * R, c + math.sin(a) * R
    dx, dy = -math.sin(a), math.cos(a)           # sens des aiguilles d'une montre (angle qui augmente)
    for col, s_ in ((DARK, 1.0), (YEL, 0.6)):
        L = 62 * k * s_
        tip = (tx + dx * L * 1.3, ty + dy * L * 1.3)
        d.polygon([tip, (tx - dy * L, ty + dx * L), (tx + dy * L, ty - dx * L)], fill=col)
    return im.resize((S, S), Image.LANCZOS)


def pos_at(i, q):
    a, b = cell_center(i), cell_center(CLOCK[i])
    e = ease_io(q)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    # petit arc vers l'extérieur
    _, _, _, (cx, cy), _, _ = paper_geom()
    ox, oy = mx - cx, my - cy
    bulge = math.sin(math.pi * e) * 0.25
    return lerp(a[0], b[0], e) + ox * bulge, lerp(a[1], b[1], e) + oy * bulge


def s_turn(t):
    w = beige().copy()
    paper(w)
    q = clamp((t - 21.5) / 0.9)
    pos = [pos_at(i, q) for i in range(4)]
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    zones(w, t, [0, 0, 0, 0], pos)
    _, _, _, (cx, cy), _, _ = paper_geom()
    a = life(t, 21.2, None)
    if a > 0.01:
        put(u, turn_arrow(), cx, cy, a, rot=-360 * ease_io(q) * 0.25)
    pills(u, ["ANNÉE 1", "ANNÉE 2"], 0 if q < 0.6 else 1, t, 21.15, None, y=470, pw=250)
    title(u, "CHAQUE ANNÉE…", t, 21.1, 22.2, y=260, color=WHITE, size=140)
    title(u, "TU TOURNES D'UNE CASE !", t, 22.22, None, y=260, color=RED, size=110)
    return w, u


cue(21.12, "whoosh", 0.1)
cue(21.5, "whoosh_up", 0.14)
cue(22.45, "ding", 0.16)


# ============================================================ F. BONUS : POIS ET HARICOTS ENRICHISSENT LA TERRE (23.3 → 27.3)
def s_bonus(t):
    w = beige().copy()
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base = 1360
    nxt = clamp((t - 26.3) / 0.7)
    for x, a, b in ((300, "pois", "tomate"), (780, "haricot", "carotte")):
        soft_shadow(lay, x, base, 420, 70)
        if nxt <= 0:
            stages(lay, a, x, base, 800, clamp((t - 23.6) / 1.5) * 3)
        else:
            k, s = swap(nxt)
            if k == 0:
                plant(lay, f"banque/{a}_4", x, base, 800, s=s)
            else:
                plant(lay, f"banque/{b}_4", x, base, 800, s=s)
    w.alpha_composite(lay)
    # l'azote : des bulles vertes qui montent dans la terre
    az = fade(t, 25.25, 26.4, 0.3, 0.3)
    if az > 0.01:
        d = ImageDraw.Draw(u)
        r = np.random.default_rng(4)
        for i in range(26):
            x = r.choice([300, 780]) + r.uniform(-140, 140)
            ph = (t * 0.9 + r.uniform(0, 1)) % 1
            y = base - ph * 300
            rr = r.uniform(7, 14)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(120, 200, 90, int(200 * az * (1 - ph))),
                      outline=(40, 90, 40, int(220 * az * (1 - ph))), width=2)
        tag(u, "AZOTE", 540, 1100, t, 25.3, 26.4, rot=-4, size=64)
    if t > 26.5:
        put(u, icon("check", 130), 540, 900, ease_out_back(clamp((t - 26.55) / 0.3), 1.6))
        sparkles(u, t, 26.6, 540, 1150, 420, 10, 9, 0.9)
    stamp(u, "BONUS !", 540, 270, t, 23.45, 24.05, GREEN, 170, -6)
    title(u, "HARICOTS ET POIS", t, 24.25, 25.25, y=260, color=GREEN, size=120)
    title(u, "ENRICHISSENT LA TERRE", t, 25.27, 26.3, y=260, color=WHITE, size=105)
    title(u, "POUR LES LÉGUMES SUIVANTS", t, 26.32, None, y=260, color=RED, size=92)
    return w, u


cue(23.47, "thud", 0.18)
cue(23.5, "success", 0.14)
for _k in range(3):
    cue(23.6 + 0.5 * (_k + 1) - 0.25, "pop_hi", 0.12)
cue(25.3, "rise", 0.16)
cue(26.35, "whoosh", 0.1)
cue(26.58, "ding", 0.14)


# ============================================================ G. ABONNE-TOI (27.3 → fin)
def s_end(t):
    w = beige().copy()
    paper(w, 0.82)
    u = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i in range(4):
        x, y = cell_center(CLOCK[i], 0.82)
        drawing(w, i, x, y, 1.0, 0.82)
    clicked = t > 28.95
    btn = button_img("ABONNÉ" if clicked else "S'ABONNER", (120, 120, 120) if clicked else RED, 70)
    press = 1 - 0.08 * math.sin(math.pi * clamp((t - 28.9) / 0.15))
    put(u, btn, 540, 1400, life(t, 27.5) * press)
    if t > 28.4:
        kk = ease_out((t - 28.4) / 0.45)
        put(u, icon("cursor", 110), lerp(900, 640, kk), lerp(1650, 1440, kk), 1)
    put(u, logo_img(260), 540, 300, life(t, 29.9, dur=0.45))
    sparkles(u, t, 30.0, 540, 300, 200, 10, 12)
    title(u, "PLUS D'ASTUCES ?", t, 27.35, 29.85, y=280, color=YEL, size=135)
    return w, u


cue(27.4, "pop_lo", 0.18)
cue(28.93, "click", 0.3)
cue(30.0, "sparkle", 0.16)


def _sh(fn):
    return lambda t: fn(t + SHIFT)


SCENES = [
    (0.0, 4.45 - SHIFT, _sh(s_fail)),
    (4.45 - SHIFT, 11.1 - SHIFT, _sh(s_same)),
    (11.1 - SHIFT, 15.2 - SHIFT, _sh(s_sheet)),
    (15.2 - SHIFT, 21.0 - SHIFT, _sh(s_zones)),
    (21.0 - SHIFT, 23.3 - SHIFT, _sh(s_turn)),
    (23.3 - SHIFT, 27.3 - SHIFT, _sh(s_bonus)),
    (27.3 - SHIFT, 99.0, _sh(s_end)),
]

TRAPS = []
