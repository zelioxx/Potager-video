"""Monstera en pot (photos fournies) avec pot « ouvrable » : la coque en terre cuite se sépare en deux
et laisse voir la coupe de la terre et le système racinaire.

Tout est calculé dans les coordonnées de la photo source (1024 x 1024) puis posé à l'échelle voulue.
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import IMG, ROOT, clamp, lerp, put

SRC = os.path.join(ROOT, "assets", "images", "source_utilisateur")
N = 1024
SS = 2  # sur-échantillonnage du dessin des racines

# --- géométrie du pot mesurée sur la photo
RIM_C, RIM_R = (508, 455), (217, 100)
SOIL_C, SOIL_R = (510, 475), (196, 80)
WALL_L = ((294, 470), (422, 828))
WALL_R = ((723, 470), (650, 828))
BOT_C, BOT_R = (536, 828), (114, 14)
POT_BOTTOM = (536, 828)
WALL = 15          # épaisseur de la coupe de la paroi
SPLIT_X = 510


def soil_front_y(x):
    u = (x - SOIL_C[0]) / SOIL_R[0]
    return SOIL_C[1] + SOIL_R[1] * math.sqrt(max(0.0, 1 - u * u))


def _wall_x(wall, y):
    (x0, y0), (x1, y1) = wall
    return x0 + (x1 - x0) * (y - y0) / (y1 - y0)


def interior_poly(inset=WALL):
    """Coupe visible quand le pot est ouvert (sous le bord avant de la surface du terreau)."""
    pts = []
    xl, xr = SOIL_C[0] - SOIL_R[0] + 2, SOIL_C[0] + SOIL_R[0] - 2
    for i in range(41):
        x = xl + (xr - xl) * i / 40
        pts.append((x, soil_front_y(x)))
    yb = BOT_C[1] - inset
    pts += [(_wall_x(WALL_R, yb) - inset, yb), (_wall_x(WALL_L, yb) + inset, yb)]
    return pts


def section_poly():
    """Bande de terre cuite coupée (paroi arrière + fond) autour de la coupe."""
    yb = BOT_C[1]
    y0 = SOIL_C[1] - 4
    out = [(_wall_x(WALL_L, y0), y0), (_wall_x(WALL_R, y0), y0), (_wall_x(WALL_R, yb), yb),
           (_wall_x(WALL_L, yb), yb)]
    return out


@lru_cache(None)
def photo(sick=True):
    im = Image.open(os.path.join(IMG, "arrosage", "monstera_malade_full.png" if sick else "monstera_mieux_full.png"))
    return im.convert("RGBA")


@lru_cache(None)
def masks(sick=True):
    """(masque coque du pot, masque intérieur) en float 0..1, taille 1024."""
    a = np.asarray(photo(sick)).astype(np.float32)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    hull = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(hull)
    d.ellipse([RIM_C[0] - RIM_R[0], RIM_C[1] - RIM_R[1], RIM_C[0] + RIM_R[0], RIM_C[1] + RIM_R[1]], fill=255)
    d.polygon([(WALL_L[0][0], RIM_C[1]), (WALL_R[0][0], RIM_C[1]), WALL_R[1], WALL_L[1]], fill=255)
    d.ellipse([BOT_C[0] - BOT_R[0], BOT_C[1] - BOT_R[1], BOT_C[0] + BOT_R[0], BOT_C[1] + BOT_R[1]], fill=255)
    soil = Image.new("L", (N, N), 0)
    ImageDraw.Draw(soil).ellipse([SOIL_C[0] - SOIL_R[0], SOIL_C[1] - SOIL_R[1], SOIL_C[0] + SOIL_R[0],
                                  SOIL_C[1] + SOIL_R[1]], fill=255)
    hull = np.asarray(hull) > 0
    soil = np.asarray(soil) > 0
    leaf = ((g >= r - 6) & ((g - b) > 25)) | ((r - b > 70) & (np.abs(r - g) < 30) & (r > 140))
    from scipy import ndimage
    leaf = ndimage.binary_opening(leaf, iterations=1)
    leaf = ndimage.binary_dilation(leaf, iterations=1)
    pot = hull & ~soil & ~leaf & (al > 128)
    pot = ndimage.binary_closing(pot, iterations=2) & ~leaf
    yy = np.arange(N)[:, None]
    pot &= np.broadcast_to(yy > SOIL_C[1] - 4, pot.shape)   # le bord arrière du pot reste en place
    potf = np.asarray(Image.fromarray((pot * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))) / 255.0
    inside = Image.new("L", (N, N), 0)
    ImageDraw.Draw(inside).polygon(interior_poly(), fill=255)
    return potf.astype(np.float32), np.asarray(inside.filter(ImageFilter.GaussianBlur(0.7))) / 255.0


@lru_cache(None)
def plant_minus_pot(sick=True):
    a = np.asarray(photo(sick)).copy()
    potf, _ = masks(sick)
    a[..., 3] = (a[..., 3] * (1 - potf)).astype(np.uint8)
    return Image.fromarray(a)


@lru_cache(None)
def shells(sick=True):
    a = np.asarray(photo(sick)).copy()
    potf, _ = masks(sick)
    a[..., 3] = (a[..., 3] * potf).astype(np.uint8)
    full = Image.fromarray(a)
    left, right = full.copy(), full.copy()
    la, ra = np.asarray(left).copy(), np.asarray(right).copy()
    la[:, SPLIT_X:, 3] = 0
    ra[:, :SPLIT_X, 3] = 0
    return Image.fromarray(la), Image.fromarray(ra)


# ------------------------------------------------------------- textures de terre
@lru_cache(None)
def soil_texture():
    """Terreau en coupe : brun très foncé, grains, quelques billes de perlite (comme sur la photo)."""
    r = np.random.default_rng(31)
    small = r.random((N // 6, N // 6)).astype(np.float32)
    nz = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)).astype(np.float32) / 255
    base = np.stack([46 + 22 * nz, 32 + 15 * nz, 23 + 10 * nz], -1)
    im = Image.fromarray(base.astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    for _ in range(14000):
        x, y = r.uniform(0, N), r.uniform(0, N)
        k = r.random()
        rad = r.uniform(1.5, 4.5)
        if k < 0.10:
            gcol = int(r.uniform(190, 235))
            d.ellipse([x - rad, y - rad * 0.8, x + rad, y + rad * 0.8], fill=(gcol, gcol - 4, gcol - 10))
        elif k < 0.55:
            d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(int(r.uniform(70, 105)), int(r.uniform(50, 72)), 38))
        else:
            d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(20, 14, 10))
    return im.filter(ImageFilter.GaussianBlur(0.5))


@lru_cache(None)
def mix_texture():
    r = np.random.default_rng(21)
    im = Image.new("RGBA", (N, N), (52, 36, 26, 255))
    d = ImageDraw.Draw(im)
    for _ in range(9000):
        x, y = r.uniform(0, N), r.uniform(0, N)
        k = r.random()
        if k < 0.42:   # perlite
            rad = r.uniform(3, 7)
            gcol = int(r.uniform(215, 250))
            d.ellipse([x - rad, y - rad * 0.8, x + rad, y + rad * 0.8], fill=(gcol, gcol, gcol - 6))
        elif k < 0.72:  # fibres de coco
            ang = r.uniform(0, math.pi)
            L = r.uniform(8, 20)
            d.line([(x, y), (x + math.cos(ang) * L, y + math.sin(ang) * L)],
                   fill=(int(r.uniform(150, 185)), int(r.uniform(95, 120)), 60), width=3)
        else:  # terreau
            rad = r.uniform(2, 5)
            d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(30, 20, 14))
    return im.filter(ImageFilter.GaussianBlur(0.4))


# ------------------------------------------------------------- racines de monstera
@lru_cache(None)
def root_paths(seed=4):
    """Racines épaisses et charnues : quelques grosses racines + radicelles."""
    rng = np.random.default_rng(seed)
    roots = []
    n = 9
    for i in range(n):
        x = 470 + i * 10 + rng.uniform(-4, 4)
        y = soil_front_y(x) - 2
        ang = math.pi / 2 + (i - (n - 1) / 2) * 0.24 + rng.uniform(-0.1, 0.1)
        L = rng.uniform(300, 400)
        pts = [(x, y)]
        steps = 40
        for k in range(steps):
            ang += rng.uniform(-0.16, 0.16) + 0.04 * (math.pi / 2 - ang)
            x += math.cos(ang) * L / steps
            y += math.sin(ang) * L / steps
            y = min(y, BOT_C[1] - WALL - 7)
            x = min(max(x, _wall_x(WALL_L, y) + WALL + 7), _wall_x(WALL_R, y) - WALL - 7)
            pts.append((x, y))
        roots.append(dict(pts=pts, w0=rng.uniform(10, 12.5), w1=5.5, main=True, idx=len(roots),
                          col=(int(rng.uniform(186, 214)), int(rng.uniform(150, 178)), int(rng.uniform(104, 128)))))
        for _ in range(int(rng.integers(2, 4))):
            k0 = int(rng.integers(8, steps - 6))
            bx, by = pts[k0]
            side = rng.choice([-1, 1])
            a2 = ang + side * rng.uniform(0.7, 1.2)
            L2 = rng.uniform(50, 110)
            sp = [(bx, by)]
            for k in range(10):
                a2 += rng.uniform(-0.2, 0.2)
                bx += math.cos(a2) * L2 / 10
                by += math.sin(a2) * L2 / 10
                by = min(by, BOT_C[1] - WALL - 6)
                bx = min(max(bx, _wall_x(WALL_L, by) + WALL + 6), _wall_x(WALL_R, by) - WALL - 6)
                sp.append((bx, by))
            roots.append(dict(pts=sp, w0=5.5, w1=2.8, main=False, col=roots[-1]["col"] if roots else (200, 168, 120), parent=len(roots) - 1 if False else i,
                              start=k0 / steps, idx=len(roots)))
    # rattache les radicelles à l'indice de leur racine principale
    mains = [r for r in roots if r["main"]]
    for r in roots:
        if not r["main"]:
            r["parent_idx"] = mains[r["parent"]]["idx"]
    return roots


def _mix(c0, c1, k):
    return tuple(int(lerp(a, b, k)) for a, b in zip(c0, c1))


def draw_roots(d, g=1.0, rot=0.0, rot_of=None, hidden=(), ox=0, oy=0):
    """Dessine sur un ImageDraw sur-échantillonné (SS). rot_of(idx) -> pourriture 0..1 de chaque racine."""
    for r in root_paths():
        if r["idx"] in hidden or (not r["main"] and r["parent_idx"] in hidden):
            continue
        rv = rot_of(r["idx"] if r["main"] else r["parent_idx"]) if rot_of else rot
        if r["main"]:
            frac = g
        else:
            frac = clamp((g - r["start"]) / max(0.05, 1 - r["start"]))
        pts = r["pts"]
        m = max(2, int(len(pts) * frac))
        if frac <= 0.01:
            continue
        seg = pts[:m]
        for k in range(len(seg) - 1):
            t = k / max(1, len(pts) - 1)
            wdt = lerp(r["w0"], r["w1"], t) * (1 + 0.25 * rv)
            base = _mix(r.get("col", (200, 168, 120)), (236, 226, 202), t ** 1.6)
            fill = _mix(base, (44, 32, 22), rv)
            edge = _mix((128, 96, 62), (128, 112, 78), rv)
            (x0, y0), (x1, y1) = seg[k], seg[k + 1]
            p0 = ((x0 - ox) * SS, (y0 - oy) * SS)
            p1 = ((x1 - ox) * SS, (y1 - oy) * SS)
            d.line([p0, p1], fill=edge, width=int((wdt + 2.4) * SS))
            d.ellipse([p1[0] - (wdt + 2.4) * SS / 2, p1[1] - (wdt + 2.4) * SS / 2,
                       p1[0] + (wdt + 2.4) * SS / 2, p1[1] + (wdt + 2.4) * SS / 2], fill=edge)
        for k in range(len(seg) - 1):
            t = k / max(1, len(pts) - 1)
            wdt = lerp(r["w0"], r["w1"], t) * (1 + 0.25 * rv)
            base = _mix(r.get("col", (200, 168, 120)), (236, 226, 202), t ** 1.6)
            fill = _mix(base, (44, 32, 22), rv)
            hi = _mix((240, 226, 196), (120, 112, 70), rv)
            (x0, y0), (x1, y1) = seg[k], seg[k + 1]
            p0 = ((x0 - ox) * SS, (y0 - oy) * SS)
            p1 = ((x1 - ox) * SS, (y1 - oy) * SS)
            d.line([p0, p1], fill=fill, width=int(wdt * SS))
            d.ellipse([p1[0] - wdt * SS / 2, p1[1] - wdt * SS / 2, p1[0] + wdt * SS / 2, p1[1] + wdt * SS / 2], fill=fill)
            d.line([(p0[0] - wdt * 0.22 * SS, p0[1]), (p1[0] - wdt * 0.22 * SS, p1[1])], fill=hi,
                   width=max(1, int(wdt * 0.18 * SS)))
        if frac >= 0.999 and r["main"]:
            x, y = seg[-1]
            tip = _mix((250, 246, 236), (70, 52, 36), rv)
            rr = r["w1"] * 0.75 * SS
            d.ellipse([(x - ox) * SS - rr, (y - oy) * SS - rr, (x - ox) * SS + rr, (y - oy) * SS + rr], fill=tip)


def root_tip(idx):
    return root_paths()[idx]["pts"][-1]


def main_roots():
    return [r["idx"] for r in root_paths() if r["main"]]


# ------------------------------------------------------------- bulles d'air dans les pores
@lru_cache(None)
def pores():
    rng = np.random.default_rng(13)
    pts = []
    while len(pts) < 26:
        x, y = rng.uniform(320, 700), rng.uniform(570, 800)
        if _wall_x(WALL_L, y) + 30 < x < _wall_x(WALL_R, y) - 30:
            pts.append((x, y, rng.uniform(5, 9)))
    return pts


# ------------------------------------------------------------- composition
BX0, BY0, BX1, BY1 = 280, 440, 740, 845   # boîte englobante de la coupe


def section_layer(t=0.0, g=1.0, rot=0.0, rot_of=None, hidden=(), water=0.0, air=0.0, dry=0.0, mix=0.0,
                  holes=0.0, murky=0.0):
    """Coupe : paroi de terre cuite + terre + racines + eau + bulles (RGBA 1024)."""
    w, h = BX1 - BX0, BY1 - BY0
    lay = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    # paroi coupée (bande de terre cuite)
    d = ImageDraw.Draw(lay)
    d.polygon(section_poly(), fill=(170, 92, 60, 255))
    d.line(section_poly() + [section_poly()[0]], fill=(120, 60, 38, 255), width=3)
    if holes > 0.01:
        for k in (-0.55, 0, 0.55):
            hx = BOT_C[0] + k * BOT_R[0]
            d.rectangle([hx - 13, BOT_C[1] - WALL - 2, hx + 13, BOT_C[1] + 4], fill=(0, 0, 0, 0))
    # terre
    _, inside = masks()
    soil = soil_texture()
    if mix > 0.01:
        soil = Image.blend(soil, mix_texture(), clamp(mix))
    soil = soil.copy()
    if dry > 0.01:
        band = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        xl, xr = SOIL_C[0] - SOIL_R[0], SOIL_C[0] + SOIL_R[0]
        top = [(x, soil_front_y(x) - 4) for x in np.linspace(xl, xr, 40)]
        bot = [(x, soil_front_y(x) + 58) for x in np.linspace(xr, xl, 40)]
        ImageDraw.Draw(band).polygon(top + bot, fill=(156, 124, 88, int(215 * dry)))
        soil.alpha_composite(band.filter(ImageFilter.GaussianBlur(2)))
    # racines (sur-échantillonnées)
    big = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    draw_roots(ImageDraw.Draw(big), g, rot, rot_of, hidden, BX0, BY0)
    rl = big.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.45))
    soil.alpha_composite(rl, (BX0, BY0))
    sd = ImageDraw.Draw(soil)
    # bulles d'air
    wl = BY1 - (BY1 - 560) * water if water > 0.01 else 9999
    if air > 0.01:
        for (x, y, rad) in pores():
            if y < wl - 4:
                rr = rad * (0.9 + 0.1 * math.sin(t * 5 + x))
                sd.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(235, 245, 255, int(150 * air)),
                           outline=(255, 255, 255, int(255 * air)), width=2)
                sd.ellipse([x - rr * 0.5, y - rr * 0.6, x - rr * 0.1, y - rr * 0.2], fill=(255, 255, 255, int(255 * air)))
    if water > 0.01:
        ov = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        pts = [(x, wl + 3 * math.sin(x / 18 + t * 5)) for x in range(BX0, BX1 + 8, 8)]
        col = (int(lerp(80, 90, murky)), int(lerp(150, 110, murky)), int(lerp(215, 70, murky)), 120)
        od.polygon(pts + [(BX1, BY1), (BX0, BY1)], fill=col)
        od.line(pts, fill=(200, 230, 250, 230), width=3)
        soil.alpha_composite(ov)
    soil.putalpha(Image.fromarray((np.asarray(soil.getchannel("A")) * inside).astype(np.uint8)))
    lay.alpha_composite(soil)
    return lay


def compose(open_=0.0, sick=True, healthy_blend=0.0, t=0.0, **sec):
    """Image 1024 du monstera : pot fermé (open_=0) ou ouvert (open_=1) avec la coupe."""
    out = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    if open_ > 0.01:
        out.alpha_composite(section_layer(t, **sec))
    # coques du pot qui s'écartent
    if open_ < 0.99:
        e = open_ ** 1.3
        lsh, rsh = shells(sick)
        for sh, sg in ((lsh, -1), (rsh, 1)):
            im = sh.rotate(sg * -18 * e, center=(SPLIT_X, POT_BOTTOM[1]), resample=Image.BICUBIC,
                           translate=(sg * 260 * e, 30 * e))
            if e > 0:
                im.putalpha(im.getchannel("A").point(lambda v: int(v * (1 - e))))
            out.alpha_composite(im)
    plant = plant_minus_pot(sick)
    if healthy_blend > 0.01 and sick:
        plant = Image.blend(plant, plant_minus_pot(False), clamp(healthy_blend))
    if open_ < 0.01:
        # pot fermé : photo d'origine telle quelle
        full = photo(sick)
        if healthy_blend > 0.01 and sick:
            full = Image.blend(full, photo(False), clamp(healthy_blend))
        out = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        out.alpha_composite(full)
        return out
    if open_ > 0.01:
        _, inside = masks()
        k = 1 - 0.72 * clamp(open_) * inside
        plant = plant.copy()
        plant.putalpha(Image.fromarray((np.asarray(plant.getchannel("A")) * k).astype(np.uint8)))
    out.alpha_composite(plant)
    return out


def place(c, img, px, py, s):
    """Pose l'image 1024 de sorte que le bas du pot tombe en (px, py) à l'échelle s."""
    cx = px - (POT_BOTTOM[0] - N / 2) * s
    cy = py - (POT_BOTTOM[1] - N / 2) * s
    put(c, img, cx, cy, s)


def to_screen(x, y, px, py, s):
    return px + (x - POT_BOTTOM[0]) * s, py + (y - POT_BOTTOM[1]) * s
