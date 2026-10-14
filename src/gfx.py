"""Primitives graphiques : décor, sprites photo, textes, icônes, badges."""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "images")
FNT = os.path.join(ROOT, "assets", "fonts")

W, H = 1080, 1920
FLOOR_Y = 1235

DARK = (29, 43, 31)
YEL = (247, 199, 52)
CREAM = (248, 242, 229)
GREEN = (60, 126, 66)
RED = (224, 76, 62)
BLUE = (78, 164, 222)
KRAFT = (201, 163, 113)
WHITE = (255, 255, 255)

F_CAP = os.path.join(FNT, "Poppins_800ExtraBold.ttf")
F_BLACK = os.path.join(FNT, "Poppins_900Black.ttf")
F_TITLE = os.path.join(FNT, "LilitaOne_400Regular.ttf")


# ----------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_out_back(x, s=1.9):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_out(x):
    return 1 - (1 - clamp(x)) ** 3


def ease_in(x):
    return clamp(x) ** 3


def ease_io(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def life(t, t0, t1=None, dur=0.32, out=0.16):
    """Échelle d'apparition (pop élastique) puis disparition."""
    if t < t0:
        return 0.0
    s = ease_out_back((t - t0) / dur)
    if t1 is not None and t > t1:
        s *= 1 - ease_in((t - t1) / out)
    return max(0.0, s)


def fade(t, t0, t1=None, dur=0.25, out=0.2):
    if t < t0:
        return 0.0
    a = clamp((t - t0) / dur)
    if t1 is not None and t > t1:
        a *= 1 - clamp((t - t1) / out)
    return a


def lerp(a, b, x):
    return a + (b - a) * x


# ------------------------------------------------------------- décor
def _noise(h, w, scale, seed):
    r = np.random.default_rng(seed)
    small = r.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    im = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im).astype(np.float32) / 255


@lru_cache(None)
def wall():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    top = np.array([233, 222, 200], np.float32)
    bot = np.array([219, 201, 170], np.float32)
    g = top + (bot - top) * (y[..., None] ** 1.2)
    d = np.sqrt(((x - 0.5) * 1.1) ** 2 + ((y - 0.38) * 0.75) ** 2)
    glow = np.clip(1 - d / 0.62, 0, 1) ** 1.5
    g = g + glow[..., None] * np.array([16, 15, 13], np.float32)
    g += (_noise(H, W, 3, 1)[..., None] - 0.5) * 5
    return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")


@lru_cache(None)
def table_floor():
    h = H - FLOOR_Y
    y = np.linspace(0, 1, h)[:, None, None]
    top = np.array([189, 146, 101], np.float32)
    bot = np.array([150, 108, 70], np.float32)
    g = np.broadcast_to(top + (bot - top) * y, (h, W, 3)).copy()
    grain = _noise(h, W, 2, 5)
    grain = np.asarray(Image.fromarray((grain * 255).astype(np.uint8)).resize((W // 8, h)).resize((W, h), Image.BICUBIC)).astype(np.float32) / 255
    g += (grain[..., None] - 0.5) * 14
    img = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    for yy in (215, 470):
        d.line([(0, yy), (W, yy)], fill=(128, 90, 58, 120), width=3)
        d.line([(0, yy + 3), (W, yy + 3)], fill=(205, 165, 120, 90), width=2)
    d.rectangle([0, 0, W, 5], fill=(214, 176, 130, 255))
    sh = Image.new("RGBA", (W, 40), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    for i in range(40):
        sd.line([(0, i), (W, i)], fill=(70, 45, 25, int(70 * (1 - i / 40) ** 2)))
    img.alpha_composite(sh, (0, 6))
    return img


@lru_cache(None)
def soil_tex():
    r = np.random.default_rng(11)
    y = np.linspace(0, 1, H)[:, None, None]
    top = np.array([104, 71, 47], np.float32)
    bot = np.array([72, 47, 31], np.float32)
    g = np.broadcast_to(top + (bot - top) * y, (H, W, 3)).copy()
    g += (_noise(H, W, 40, 3)[..., None] - 0.5) * 16
    g += (_noise(H, W, 4, 4)[..., None] - 0.5) * 10
    img = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    for _ in range(520):
        x, yy = r.uniform(0, W), r.uniform(0, H)
        s = r.uniform(3, 11)
        light = r.random() < 0.6
        c = (150, 118, 90, 200) if light else (52, 33, 22, 200)
        if r.random() < 0.15:
            c = (178, 150, 120, 220)
        d.ellipse([x - s, yy - s * 0.7, x + s, yy + s * 0.7], fill=c)
    return img.filter(ImageFilter.GaussianBlur(0.6))


@lru_cache(None)
def clay_tex():
    im = Image.open(os.path.join(IMG, "clay_photo.jpg")).convert("RGB")
    im = im.resize((W, int(im.height * W / im.width)))
    big = Image.new("RGB", (W, H))
    for yy in range(0, H, im.height):
        big.paste(im if (yy // im.height) % 2 == 0 else im.transpose(Image.FLIP_TOP_BOTTOM), (0, yy))
    return big.convert("RGBA")


def draw_soil(c, soil_y, clay=0.0, warm=0.0, darken=0.0):
    soil_y = int(soil_y)
    if soil_y >= H:
        return
    tex = soil_tex().crop((0, 0, W, H - soil_y))
    if clay > 0:
        ct = clay_tex().crop((0, 0, W, H - soil_y))
        tex = Image.blend(tex, ct, 0.75 * clay)
    if warm > 0:
        ov = Image.new("RGBA", tex.size, (255, 150, 60, int(55 * warm)))
        tex = tex.copy()
        tex.alpha_composite(ov)
    if darken > 0:
        ov = Image.new("RGBA", tex.size, (10, 6, 3, int(120 * darken)))
        tex = tex.copy()
        tex.alpha_composite(ov)
    c.alpha_composite(tex, (0, soil_y))
    d = ImageDraw.Draw(c)
    d.rectangle([0, soil_y - 4, W, soil_y + 3], fill=(240, 231, 212, 255))
    d.rectangle([0, soil_y + 4, W, soil_y + 9], fill=(60, 38, 25, 160))


def background(mode="table", soil_y=None, **kw):
    c = wall().copy()
    if mode == "table":
        c.alpha_composite(table_floor(), (0, FLOOR_Y))
    if soil_y is not None:
        draw_soil(c, soil_y, **kw)
    return c


# ---------------------------------------------------------- sprites photo
@lru_cache(None)
def asset(name):
    im = Image.open(os.path.join(IMG, name + ".png")).convert("RGBA")
    if im.height > 1000:
        im = im.resize((int(im.width * 1000 / im.height), 1000), Image.LANCZOS)
    return im


@lru_cache(None)
def rot_masks(name):
    a = asset(name)
    w, h = a.size
    seed = sum(map(ord, name))
    blot = _noise(h, w, max(8, w // 5), seed)
    blot = np.clip((blot - 0.52) * 5, 0, 1)
    mold = _noise(h, w, max(5, w // 12), seed + 7) * 0.75 + _noise(h, w, max(2, w // 45), seed + 9) * 0.25
    mold = np.clip((mold - 0.66) * 7, 0, 1)
    mold = np.asarray(Image.fromarray((mold * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(1, w // 120)))).astype(np.float32) / 255
    return blot, mold


def rot_effect(im, name, amount):
    """Assombrit / brunit la photo, taches sombres et un peu de moisissure blanche."""
    a = np.asarray(im).astype(np.float32)
    rgb = a[..., :3]
    gray = rgb.mean(-1, keepdims=True)
    brown = (rgb * 0.35 + gray * 0.65) * np.array([0.72, 0.6, 0.42])
    blot, mold = [np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize(im.size)).astype(np.float32)[..., None] / 255
                  for m in rot_masks(name)]
    brown = brown * (1 - 0.55 * blot)
    brown = brown * (1 - mold * 0.75) + mold * 0.75 * np.array([206, 204, 182])
    a[..., :3] = rgb * (1 - amount) + brown * amount
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


@lru_cache(None)
def shadow_blob():
    im = Image.new("L", (400, 120), 0)
    ImageDraw.Draw(im).ellipse([40, 30, 360, 90], fill=255)
    im = im.filter(ImageFilter.GaussianBlur(16))
    s = Image.new("RGBA", im.size, (60, 38, 20, 0))
    s.putalpha(im)
    return s


def spr(c, name, x, base_y, h, s=1.0, rot=0.0, alpha=1.0, rotten=0.0, shadow=True,
        flip=False, sx=1.0, sy=1.0, anchor="bottom", bite=0.0):
    """Pose une photo détourée. (x, base_y) = centre-bas (ou centre si anchor='center')."""
    if s <= 0.01 or alpha <= 0.01:
        return None
    a = asset(name)
    th = h * s * sy
    tw = a.width * h / a.height * s * sx
    if th < 2 or tw < 2:
        return None
    im = a.resize((max(1, int(tw)), max(1, int(th))), Image.BICUBIC)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if rotten > 0.01:
        im = rot_effect(im, name, rotten)
    if bite > 0.01:
        im = im.copy()
        d = ImageDraw.Draw(im)
        w0, h0 = im.size
        for k, (bx, by, br) in enumerate([(0.97, 0.62, 0.2), (0.05, 0.75, 0.17), (0.8, 0.95, 0.16)]):
            if bite > k / 3:
                r = br * w0 * min(1, (bite - k / 3) * 3)
                d.ellipse([bx * w0 - r, by * h0 - r, bx * w0 + r, by * h0 + r], fill=(0, 0, 0, 0))
    if alpha < 1:
        al = im.getchannel("A").point(lambda v: int(v * alpha))
        im.putalpha(al)
    if anchor == "bottom":
        cx, cy = x, base_y - th / 2
    else:
        cx, cy = x, base_y
    if shadow and anchor == "bottom":
        sb = shadow_blob().resize((max(2, int(tw * 1.25)), max(2, int(tw * 0.3))))
        if alpha < 1:
            sb.putalpha(sb.getchannel("A").point(lambda v: int(v * alpha)))
        c.alpha_composite(sb, (int(x - sb.width / 2), int(base_y - sb.height * 0.55)), )
    if abs(rot) > 0.1:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    paste(c, im, cx - im.width / 2, cy - im.height / 2)
    return (cx, cy, tw, th)


def paste(c, im, x, y):
    x, y = int(round(x)), int(round(y))
    if x >= c.width or y >= c.height or x + im.width <= 0 or y + im.height <= 0:
        return
    if x < 0 or y < 0 or x + im.width > c.width or y + im.height > c.height:
        l, t = max(0, -x), max(0, -y)
        r, b = min(im.width, c.width - x), min(im.height, c.height - y)
        im = im.crop((l, t, r, b))
        x, y = x + l, y + t
    c.alpha_composite(im, (x, y))


def scaled(im, s, rot=0.0):
    if s <= 0.01:
        return None
    out = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
    if abs(rot) > 0.1:
        out = out.rotate(rot, expand=True, resample=Image.BICUBIC)
    return out


def put(c, im, cx, cy, s=1.0, rot=0.0, alpha=1.0):
    """Colle une image centrée en (cx, cy) avec échelle / rotation / opacité."""
    if im is None or s <= 0.01 or alpha <= 0.01:
        return
    out = scaled(im, s, rot)
    if alpha < 1:
        out = out.copy()
        out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
    paste(c, out, cx - out.width / 2, cy - out.height / 2)


# ------------------------------------------------------------- textes
@lru_cache(None)
def font(path, size):
    return ImageFont.truetype(path, size)


@lru_cache(4096)
def text_img(txt, path, size, fill, stroke=0, stroke_fill=DARK, shadow=0, shadow_fill=DARK):
    """Texte avec contour + ombre portée ; boîte verticale fixe (lignes de base alignées)."""
    f = font(path, size)
    asc, desc = f.getmetrics()
    l, _, r, _ = f.getbbox(txt, stroke_width=stroke)
    pad = stroke + shadow + 6
    w, h = r - l + pad * 2, asc + desc + pad * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = pad - l, pad + asc
    if shadow:
        d.text((ox, oy + shadow), txt, font=f, fill=shadow_fill, stroke_width=stroke, stroke_fill=shadow_fill, anchor="ls")
    d.text((ox, oy), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill, anchor="ls")
    bb = im.getbbox()
    if bb:  # recadre verticalement de façon symétrique autour du centre de la boîte
        return im.crop((0, 0, w, h))
    return im


def title_img(txt, color=YEL, size=150, maxw=980):
    im = text_img(txt, F_TITLE, size, color, 13, DARK, 11, DARK)
    if im.width > maxw:
        size = int(size * maxw / im.width)
        im = text_img(txt, F_TITLE, size, color, max(8, int(13 * size / 150)), DARK, max(6, int(11 * size / 150)), DARK)
    return im


def title(c, txt, t, t0, t1=None, y=360, color=YEL, size=150, rot=-3.0, x=W / 2):
    s = life(t, t0, t1, dur=0.36)
    if s <= 0:
        return
    wob = math.sin((t - t0) * 2.2) * 1.2
    put(c, title_img(txt, color, size), x, y, s, rot + wob)


# ------------------------------------------------------------- icônes
def aa(w, h, fn, ss=3):
    big = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    fn(ImageDraw.Draw(big), ss, big)
    return big.resize((w, h), Image.LANCZOS)


@lru_cache(None)
def icon(kind, size=160):
    S = size

    def circ(d, k, fill, outline=DARK, ow=0.06):
        o = S * ow * k
        d.ellipse([0, 0, S * k - 1, S * k - 1], fill=outline)
        d.ellipse([o, o, S * k - o, S * k - o], fill=fill)

    if kind == "check":
        def f(d, k, _):
            circ(d, k, GREEN)
            pts = [(0.27, 0.52), (0.44, 0.68), (0.74, 0.34)]
            d.line([(x * S * k, y * S * k) for x, y in pts], fill=WHITE, width=int(S * 0.11 * k), joint="curve")
        return aa(S, S, f)
    if kind == "cross":
        def f(d, k, _):
            circ(d, k, RED)
            w_ = int(S * 0.11 * k)
            d.line([(0.32 * S * k, 0.32 * S * k), (0.68 * S * k, 0.68 * S * k)], fill=WHITE, width=w_)
            d.line([(0.68 * S * k, 0.32 * S * k), (0.32 * S * k, 0.68 * S * k)], fill=WHITE, width=w_)
        return aa(S, S, f)
    if kind == "nosign":
        def f(d, k, _):
            o = S * 0.03 * k
            d.ellipse([o, o, S * k - o, S * k - o], outline=RED, width=int(S * 0.1 * k))
            d.line([(0.22 * S * k, 0.78 * S * k), (0.78 * S * k, 0.22 * S * k)], fill=RED, width=int(S * 0.1 * k))
        return aa(S, S, f)
    if kind == "drop":
        def f(d, k, _):
            Sk = S * k
            for col, inset in ((DARK, 0), (BLUE, 0.055)):
                i = Sk * inset
                d.ellipse([0.18 * Sk + i, 0.38 * Sk + i, 0.82 * Sk - i, Sk - i - 2], fill=col)
                d.polygon([(0.5 * Sk, 0.02 * Sk + i * 1.6), (0.205 * Sk + i, 0.62 * Sk), (0.795 * Sk - i, 0.62 * Sk)], fill=col)
            d.ellipse([0.33 * Sk, 0.6 * Sk, 0.43 * Sk, 0.78 * Sk], fill=(200, 232, 250))
        im = aa(S, S, f)
        return im.crop(im.getbbox())
    if kind == "sun":
        def f(d, k, _):
            Sk = S * k
            c0 = Sk / 2
            for i in range(10):
                a = i * math.pi / 5
                p = [(c0 + math.cos(a) * Sk * 0.49, c0 + math.sin(a) * Sk * 0.49),
                     (c0 + math.cos(a + 0.2) * Sk * 0.3, c0 + math.sin(a + 0.2) * Sk * 0.3),
                     (c0 + math.cos(a - 0.2) * Sk * 0.3, c0 + math.sin(a - 0.2) * Sk * 0.3)]
                d.polygon(p, fill=(245, 168, 40))
            d.ellipse([0.2 * Sk, 0.2 * Sk, 0.8 * Sk, 0.8 * Sk], fill=DARK)
            d.ellipse([0.235 * Sk, 0.235 * Sk, 0.765 * Sk, 0.765 * Sk], fill=YEL)
        return aa(S, S, f)
    if kind == "thermo":
        def f(d, k, _):
            Sk = S * k
            d.rounded_rectangle([0.36 * Sk, 0.02 * Sk, 0.64 * Sk, 0.75 * Sk], radius=0.14 * Sk, fill=DARK)
            d.ellipse([0.22 * Sk, 0.6 * Sk, 0.78 * Sk, 0.99 * Sk], fill=DARK)
            d.rounded_rectangle([0.4 * Sk, 0.06 * Sk, 0.6 * Sk, 0.75 * Sk], radius=0.1 * Sk, fill=CREAM)
            d.ellipse([0.26 * Sk, 0.64 * Sk, 0.74 * Sk, 0.95 * Sk], fill=RED)
            d.rounded_rectangle([0.45 * Sk, 0.25 * Sk, 0.55 * Sk, 0.75 * Sk], radius=0.05 * Sk, fill=RED)
        im = aa(S, S, f)
        return im.crop(im.getbbox())
    if kind == "lightbulb":
        def f(d, k, _):
            Sk = S * k
            d.ellipse([0.12 * Sk, 0.02 * Sk, 0.88 * Sk, 0.72 * Sk], fill=DARK)
            d.ellipse([0.16 * Sk, 0.06 * Sk, 0.84 * Sk, 0.68 * Sk], fill=YEL)
            d.rounded_rectangle([0.32 * Sk, 0.62 * Sk, 0.68 * Sk, 0.96 * Sk], radius=0.06 * Sk, fill=DARK)
            for yy in (0.7, 0.8):
                d.rectangle([0.36 * Sk, yy * Sk, 0.64 * Sk, (yy + 0.05) * Sk], fill=(180, 180, 175))
            d.ellipse([0.28 * Sk, 0.16 * Sk, 0.42 * Sk, 0.34 * Sk], fill=(255, 245, 200))
        im = aa(S, S, f)
        return im.crop(im.getbbox())
    if kind == "bubble":
        def f(d, k, _):
            Sk = S * k
            d.rounded_rectangle([0.02 * Sk, 0.04 * Sk, 0.98 * Sk, 0.7 * Sk], radius=0.18 * Sk, fill=DARK)
            d.polygon([(0.2 * Sk, 0.6 * Sk), (0.42 * Sk, 0.6 * Sk), (0.16 * Sk, 0.92 * Sk)], fill=DARK)
            d.rounded_rectangle([0.06 * Sk, 0.08 * Sk, 0.94 * Sk, 0.66 * Sk], radius=0.15 * Sk, fill=WHITE)
            d.polygon([(0.23 * Sk, 0.6 * Sk), (0.38 * Sk, 0.6 * Sk), (0.21 * Sk, 0.82 * Sk)], fill=WHITE)
        return aa(S, S, f)
    if kind == "snow":
        def f(d, k, _):
            Sk = S * k
            c0 = Sk / 2
            for i in range(6):
                a = i * math.pi / 3
                d.line([(c0, c0), (c0 + math.cos(a) * Sk * 0.46, c0 + math.sin(a) * Sk * 0.46)], fill=WHITE, width=int(Sk * 0.08))
                for b in (0.25, 0.35):
                    px, py = c0 + math.cos(a) * Sk * b, c0 + math.sin(a) * Sk * b
                    for sgn in (-1, 1):
                        d.line([(px, py), (px + math.cos(a + sgn * 0.8) * Sk * 0.12, py + math.sin(a + sgn * 0.8) * Sk * 0.12)], fill=WHITE, width=int(Sk * 0.06))
        im = aa(S, S, f)
        sh = Image.new("RGBA", im.size, DARK + (0,))
        sh.putalpha(im.getchannel("A").filter(ImageFilter.MaxFilter(3)).point(lambda v: int(v * 0.6)))
        sh.alpha_composite(im)
        return sh
    if kind == "star":
        def f(d, k, _):
            Sk = S * k
            c0 = Sk / 2
            for col, sc in ((DARK, 1.0), (YEL, 0.8)):
                pts = []
                for i in range(8):
                    a = i * math.pi / 4 - math.pi / 2
                    r = (0.5 if i % 2 == 0 else 0.17) * Sk * sc
                    pts.append((c0 + math.cos(a) * r, c0 + math.sin(a) * r))
                d.polygon(pts, fill=col)
        return aa(S, S, f)
    if kind == "arrow_down":
        def f(d, k, _):
            Sk = S * k
            for col, i in ((DARK, 0), (YEL, 0.045 * Sk)):
                d.rectangle([0.33 * Sk + i, 0.02 * Sk + i, 0.67 * Sk - i, 0.55 * Sk], fill=col)
                d.polygon([(0.06 * Sk + i * 1.8, 0.5 * Sk + i * 0.6), (0.94 * Sk - i * 1.8, 0.5 * Sk + i * 0.6), (0.5 * Sk, 0.98 * Sk - i * 1.6)], fill=col)
        return aa(S, S, f)
    if kind == "fly":
        def f(d, k, _):
            Sk = S * k
            d.ellipse([0.0, 0.05 * Sk, 0.48 * Sk, 0.4 * Sk], fill=(170, 190, 205, 150))
            d.ellipse([0.52 * Sk, 0.05 * Sk, Sk, 0.4 * Sk], fill=(170, 190, 205, 150))
            d.ellipse([0.3 * Sk, 0.2 * Sk, 0.7 * Sk, 0.98 * Sk], fill=(25, 25, 25))
            d.ellipse([0.36 * Sk, 0.12 * Sk, 0.64 * Sk, 0.38 * Sk], fill=(40, 30, 30))
        return aa(S, S, f)
    if kind == "question":
        def f(d, k, im):
            circ(d, k, CREAM, ow=0.05)
        im = aa(S, S, f)
        q = text_img("?", F_TITLE, int(S * 0.72), DARK)
        im.alpha_composite(q, ((S - q.width) // 2, (S - q.height) // 2 + int(S * 0.02)))
        return im
    if kind == "cursor":
        def f(d, k, _):
            Sk = S * k
            pts = [(0.1, 0.02), (0.1, 0.82), (0.3, 0.64), (0.45, 0.98), (0.6, 0.92), (0.45, 0.58), (0.72, 0.58)]
            d.polygon([(x * Sk, y * Sk) for x, y in pts], fill=DARK)
            pts2 = [(0.16, 0.14), (0.16, 0.68), (0.31, 0.53), (0.47, 0.87), (0.52, 0.85), (0.37, 0.52), (0.58, 0.52)]
            d.polygon([(x * Sk, y * Sk) for x, y in pts2], fill=WHITE)
        return aa(S, S, f)
    raise KeyError(kind)


def num_badge_img(txt, size=150, fill=CREAM, color=DARK):
    def f(d, k, _):
        d.ellipse([0, 0, size * k - 1, size * k - 1], fill=DARK)
        o = size * 0.055 * k
        d.ellipse([o, o, size * k - o, size * k - o], fill=fill)
    im = aa(size, size, f)
    q = text_img(txt, F_BLACK, int(size * 0.5), color)
    im.alpha_composite(q, ((size - q.width) // 2, (size - q.height) // 2 + int(size * 0.03)))
    return im


@lru_cache(None)
def num_badge(txt, size=150, fill=CREAM, color=DARK):
    return num_badge_img(txt, size, fill, color)


def ring_badge(c, num, prog, s, x=968, y=215, r=70):
    """Petit badge rond haut-droite : numéro du piège + arc de progression."""
    if s <= 0.01:
        return
    k = 3
    S = int(r * 2 + 30)

    def f(d, kk, _):
        cx = cy = S * kk / 2
        R = r * kk
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(221, 211, 190))
        d.ellipse([cx - R * 0.78, cy - R * 0.78, cx + R * 0.78, cy + R * 0.78], fill=CREAM)
        if prog > 0.005:
            d.arc([cx - R + 5 * kk, cy - R + 5 * kk, cx + R - 5 * kk, cy + R - 5 * kk], -90, -90 + 360 * prog,
                  fill=GREEN, width=int(R * 0.2))
            a = math.radians(-90 + 360 * prog)
            ex, ey = cx + math.cos(a) * (R - 5 * kk - R * 0.1), cy + math.sin(a) * (R - 5 * kk - R * 0.1)
            d.ellipse([ex - R * 0.17, ey - R * 0.17, ex + R * 0.17, ey + R * 0.17], fill=YEL, outline=DARK, width=2 * kk)
    im = aa(S, S, f, k)
    q = text_img(str(num), F_BLACK, int(r * 0.78), DARK)
    im.alpha_composite(q, ((S - q.width) // 2, (S - q.height) // 2 + 2))
    put(c, im, x, y, s)


def pills(c, labels, active, t, t0, t1=None, y=470, x=W / 2, pw=196):
    """Barre de mois façon calendrier (actif en jaune)."""
    s = life(t, t0, t1, dur=0.3)
    if s <= 0.01:
        return
    n = len(labels)
    ph, gap, pad = 92, 12, 12
    w = n * pw + (n - 1) * gap + pad * 2
    h = ph + pad * 2
    k = 2
    big = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle([0, 0, w * k - 1, h * k - 1], radius=22 * k, fill=(38, 64, 44))
    for i, lab in enumerate(labels):
        x0 = (pad + i * (pw + gap)) * k
        col = YEL if i == active else CREAM
        d.rounded_rectangle([x0, pad * k, x0 + pw * k, (pad + ph) * k], radius=14 * k, fill=col)
    im = big.resize((w, h), Image.LANCZOS)
    for i, lab in enumerate(labels):
        ti = text_img(lab, F_BLACK, 50, DARK)
        x0 = pad + i * (pw + gap)
        im.alpha_composite(ti, (int(x0 + (pw - ti.width) / 2), int(pad + (ph - ti.height) / 2 + 2)))
    put(c, im, x, y, s)


@lru_cache(None)
def tag_img(txt, size=46):
    ti = text_img(txt, F_BLACK, size, DARK)
    w, h = ti.width + 70, ti.height + 34
    k = 3

    def f(d, kk, _):
        d.polygon([(0, h * kk / 2), (28 * kk, 0), (w * kk, 0), (w * kk, h * kk), (28 * kk, h * kk)], fill=(120, 88, 52))
        d.polygon([(4 * kk, h * kk / 2), (30 * kk, 4 * kk), (w * kk - 4 * kk, 4 * kk), (w * kk - 4 * kk, h * kk - 4 * kk), (30 * kk, h * kk - 4 * kk)], fill=KRAFT)
        d.ellipse([18 * kk, h * kk / 2 - 7 * kk, 32 * kk, h * kk / 2 + 7 * kk], fill=(120, 88, 52))
    im = aa(w, h, f, k)
    im.alpha_composite(ti, (48, (h - ti.height) // 2 + 2))
    return im


def tag(c, txt, x, y, t, t0, t1=None, rot=-6, size=46, string_to=None):
    s = life(t, t0, t1)
    if s <= 0.01:
        return
    if string_to is not None:
        d = ImageDraw.Draw(c)
        d.line([string_to, (x - tag_img(txt, size).width * 0.42 * s, y)], fill=(240, 236, 228), width=4)
    put(c, tag_img(txt, size), x, y, s, rot)


@lru_cache(None)
def button_img(txt, fill, size=64, tcol=WHITE):
    ti = text_img(txt, F_TITLE, size, tcol, 0)
    w, h = ti.width + 80, ti.height + 40
    k = 3

    def f(d, kk, _):
        d.rounded_rectangle([0, 8 * kk, w * kk - 1, (h + 8) * kk - 1], radius=26 * kk, fill=DARK)
        d.rounded_rectangle([0, 0, w * kk - 1, h * kk - 1], radius=26 * kk, fill=DARK)
        d.rounded_rectangle([6 * kk, 6 * kk, w * kk - 6 * kk, h * kk - 6 * kk], radius=22 * kk, fill=fill)
    im = aa(w, h + 8, f, k)
    im.alpha_composite(ti, ((w - ti.width) // 2, (h - ti.height) // 2 + 2))
    return im


@lru_cache(None)
def magnifier_img(r=220):
    S = 2 * r + 30
    tex = clay_tex().crop((150, 120, 150 + 2 * r, 120 + 2 * r))
    mask = aa(2 * r, 2 * r, lambda d, k, _: d.ellipse([0, 0, 2 * r * k - 1, 2 * r * k - 1], fill=WHITE))
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    def f(d, k, _):
        d.ellipse([0, 0, S * k - 1, S * k - 1], fill=DARK)
        d.ellipse([7 * k, 7 * k, S * k - 7 * k, S * k - 7 * k], fill=CREAM)
    im = aa(S, S, f)
    t2 = tex.copy()
    t2.putalpha(mask.getchannel("A"))
    im.alpha_composite(t2, (15, 15))
    return im


def hl_ellipse(c, cx, cy, rx, ry, s=1.0, width=9):
    if s <= 0.01:
        return
    rx, ry = rx * s, ry * s
    w, h = int(rx * 2 + 40), int(ry * 2 + 40)

    def f(d, k, _):
        d.ellipse([20 * k, 20 * k, (w - 20) * k, (h - 20) * k], outline=DARK, width=int((width + 6) * k))
        d.ellipse([20 * k + 3 * k, 20 * k + 3 * k, (w - 20) * k - 3 * k, (h - 20) * k - 3 * k], outline=YEL, width=int(width * k))
    im = aa(w, h, f, 2)
    paste(c, im, cx - w / 2, cy - h / 2)


def hline(c, x0, x1, y, prog, width=12):
    if prog <= 0.01:
        return
    xe = x0 + (x1 - x0) * prog
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([x0 - 4, y - width / 2 - 4, xe + 4, y + width / 2 + 4], radius=width, fill=DARK)
    d.rounded_rectangle([x0, y - width / 2, xe, y + width / 2], radius=width, fill=YEL)


def measure(c, x, y0, y1, label, s):
    if s <= 0.01:
        return
    d = ImageDraw.Draw(c)
    mid = (y0 + y1) / 2
    ya, yb = mid - (mid - y0) * s, mid + (y1 - mid) * s
    for col, w_ in ((DARK, 16), (YEL, 8)):
        d.line([(x, ya), (x, yb)], fill=col, width=w_)
        for yy, sg in ((ya, 1), (yb, -1)):
            d.polygon([(x - 26 - (w_ - 8) / 2, yy + sg * 34), (x + 26 + (w_ - 8) / 2, yy + sg * 34), (x, yy - sg * (w_ - 8) / 2)], fill=col)
    put(c, text_img(label, F_TITLE, 84, YEL, 9, DARK, 7, DARK), x + 150, mid, s)


# ------------------------------------------------------------- végétal dessiné
def roots(c, x, y, g, seed=1, spread=110, length=190, n=11):
    """Racines blanches qui poussent (g = 0..1)."""
    if g <= 0:
        return
    r = np.random.default_rng(seed)
    d = ImageDraw.Draw(c)
    for i in range(n):
        ang = math.pi / 2 + r.uniform(-1.1, 1.1)
        L = length * r.uniform(0.55, 1.1) * g
        px, py = x + r.uniform(-spread / 2, spread / 2) * 0.5, y
        pts = [(px, py)]
        steps = 9
        for k in range(steps):
            ang += r.uniform(-0.35, 0.35)
            px += math.cos(ang) * L / steps
            py += math.sin(ang) * L / steps
            pts.append((px, py))
        d.line(pts, fill=(70, 50, 34), width=7, joint="curve")
        d.line(pts, fill=(238, 228, 205), width=4, joint="curve")


def shoots(c, x, y, g, h=320, seed=2, n=3):
    """Feuilles vertes qui sortent de terre."""
    if g <= 0:
        return
    r = np.random.default_rng(seed)
    d = ImageDraw.Draw(c)
    for i in range(n):
        lean = (i - (n - 1) / 2) * 0.22 + r.uniform(-0.05, 0.05)
        L = h * g * r.uniform(0.75, 1.05)
        wdt = 16
        tipx, tipy = x + math.sin(lean) * L + lean * 40, y - math.cos(lean) * L
        midx, midy = x + math.sin(lean) * L * 0.5, y - math.cos(lean) * L * 0.5
        poly = [(x - wdt, y), (midx - wdt * 0.8, midy), (tipx, tipy), (midx + wdt * 0.8, midy), (x + wdt, y)]
        d.polygon(poly, fill=(46, 82, 36))
        inner = [(x - wdt + 5, y), (midx - wdt * 0.8 + 5, midy), (tipx, tipy + 10), (midx + wdt * 0.8 - 5, midy), (x + wdt - 5, y)]
        d.polygon(inner, fill=(104, 168, 70))
        d.line([(x, y), (midx, midy), (tipx, tipy + 12)], fill=(150, 205, 110), width=3)


def water(c, top, t, alpha=0.5):
    if top >= H:
        return
    top = int(top)
    hgt = H - top + 20
    ov = Image.new("RGBA", (W, hgt), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    pts = [(x, 18 + 8 * math.sin(x / 70 + t * 4) + 4 * math.sin(x / 31 - t * 3)) for x in range(0, W + 20, 20)]
    d.polygon(pts + [(W, hgt), (0, hgt)], fill=(70, 140, 205, int(255 * alpha)))
    d.line(pts, fill=(180, 220, 245, int(255 * min(1, alpha * 1.8))), width=6)
    c.alpha_composite(ov, (0, top - 18))


def particles(c, t, t0, x, y, n=14, seed=3, col=(96, 64, 40), spread=360, up=520, size=12, dur=0.9):
    if t < t0 or t > t0 + dur:
        return
    r = np.random.default_rng(seed)
    k = (t - t0)
    d = ImageDraw.Draw(c)
    for i in range(n):
        vx = r.uniform(-spread, spread)
        vy = -r.uniform(up * 0.5, up)
        px = x + vx * k
        py = y + vy * k + 1400 * k * k
        s = size * r.uniform(0.6, 1.3) * (1 - k / dur)
        d.ellipse([px - s, py - s, px + s, py + s], fill=col + (255,))
