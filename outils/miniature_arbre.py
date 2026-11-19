"""Miniatures « planter un arbre en automne / Sainte-Catherine » : python3 outils/miniature_arbre.py
→ output/miniatures/miniature_arbre_automne{,_b}_{3x4,9x16,16x9}.jpg
3x4 : TikTok et grille Instagram ; 9x16 : couverture Reels Instagram / Facebook, YouTube Shorts ;
16x9 : vignette YouTube classique.
A : vues en coupe côte à côte — planté au printemps (petites racines, terre craquelée, feuillage grillé)
    contre planté en automne (grand chevelu de racines, terre humide, arbre en pleine forme).
B : le jardin d'automne, le jeune arbre fraîchement planté et l'éphéméride du 25 novembre."""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from gfx import YEL, RED, WHITE, GREEN, DARK, CREAM, title_img, icon, put, tag_img, aa  # noqa: E402
from scenes_citron import photo_hd, shadow  # noqa: E402
from scenes_banane import ob  # noqa: E402
import scenes_arbre_automne as A  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "miniatures")
FORMATS = {"3x4": (1080, 1440), "9x16": (1080, 1920), "16x9": (1280, 720)}
LIGHT_GREEN = (120, 196, 92)


def titles(c, lines, cx, y0, maxw, gap=0.9):
    y = y0
    for txt, col, size, rot in lines:
        im = title_img(txt, col, size, maxw)
        put(c, im, cx, y + im.height / 2, 1.0, rot)
        y += im.height * gap
    return y


def top_shade(c, frac=0.42, a=150):
    cw, ch = c.size
    y = np.arange(ch)
    al = (np.clip((ch * frac - y) / (ch * frac), 0, 1) ** 1.4 * a)[:, None]
    sh = Image.new("RGBA", (cw, ch), (20, 18, 14, 0))
    sh.putalpha(Image.fromarray(np.repeat(al, cw, 1).astype("uint8")))
    c.alpha_composite(sh)


# ------------------------------------------------------------ A : les deux vues en coupe
SEC_BOX = (120, 100, 960, 1500)                 # arbre + chevelu de racines, cadrés serré


def section(kind):
    from PIL import ImageFilter
    if kind == "printemps":                     # planté au printemps : en été, il grille
        w = A.section_bg("ete").copy()
    else:                                       # planté en automne : au printemps, il démarre
        w = A.section_bg("printemps").copy()
    # le jardin du haut un peu flou : le jeune arbre se détache des arbres du fond
    top = w.crop((0, 0, A.W, A.GROUND - 4)).filter(ImageFilter.GaussianBlur(5))
    w.alpha_composite(top, (0, 0))
    if kind == "printemps":
        A.soil_tone(w, dry=1.0)
        A.tree(w, A.FEUILLU, A.CUT_X, A.GROUND, A.ROOTS_H, 0.3, only_roots=True)
        A.tree(w, A.FEUILLU, A.CUT_X, A.GROUND, 720, 0.0, dry=0.9, sway=-4)
    else:
        A.soil_tone(w, wet=0.6)
        A.tree(w, A.FEUILLU, A.CUT_X, A.GROUND, int(A.ROOTS_H * 1.45), 1.0, only_roots=True)
        A.tree(w, A.FEUILLU, A.CUT_X, A.GROUND, 720, 0.0)
    return w.crop(SEC_BOX)


def panel(kind, pw, ph):
    """Vignette arrondie, cadre crème, étiquette de saison et pastille ✓ / ✗."""
    sec = section(kind)
    k = max(pw / sec.width, ph / sec.height)
    im = sec.resize((int(sec.width * k), int(sec.height * k)), Image.LANCZOS)
    im = im.crop(((im.width - pw) // 2, 0, (im.width - pw) // 2 + pw, ph))
    r = int(pw * 0.07)
    m = Image.new("L", (pw * 3, ph * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, pw * 3 - 1, ph * 3 - 1], radius=r * 3, fill=255)
    im.putalpha(m.resize((pw, ph), Image.LANCZOS))
    b = max(6, pw // 60)
    out = aa(pw + 2 * b, ph + 2 * b, lambda d, kk, _: d.rounded_rectangle(
        [0, 0, (pw + 2 * b) * kk - 1, (ph + 2 * b) * kk - 1], radius=(r + b) * kk, fill=CREAM))
    out.alpha_composite(im, (b, b))
    good = kind == "automne"
    lab = tag_img("EN AUTOMNE" if good else "AU PRINTEMPS", int(pw * 0.085))
    put(out, lab, out.width / 2, ph * 0.075, 1.0, -4 if good else 4)
    put(out, icon("check" if good else "cross", int(pw * 0.24)), out.width / 2, ph * 0.88, 1.0)
    return out


def scene_a(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    c = Image.new("RGBA", (cw, ch), (236, 226, 204, 255))
    # fond : le jardin d'automne flouté, pour rester dans l'ambiance
    bg = photo_hd(A.AUTOMNE).convert("RGB")
    s = max(cw / bg.width, ch / bg.height)
    bg = bg.resize((int(bg.width * s) + 1, int(bg.height * s) + 1), Image.LANCZOS)
    bg = bg.crop(((bg.width - cw) // 2, (bg.height - ch) // 2, (bg.width - cw) // 2 + cw, (bg.height - ch) // 2 + ch))
    from PIL import ImageFilter
    c.alpha_composite(bg.filter(ImageFilter.GaussianBlur(10)).convert("RGBA"))
    c.alpha_composite(Image.new("RGBA", (cw, ch), (20, 16, 10, 70)))
    if land:
        ph = int(ch * 0.92)
        pw = int(ph * 0.5)
        y = (ch - ph) // 2 - 6
        for i, kind in enumerate(("printemps", "automne")):
            p = panel(kind, pw, ph)
            c.alpha_composite(p, (int(cw * 0.47 + i * (pw + 22)), y))
        titles(c, [("TON ARBRE", WHITE, 130, -3), ("MEURT L'ÉTÉ ?", YEL, 130, -3), ("MAUVAISE", RED, 135, -4),
                   ("DATE !", RED, 135, -4)], cw * 0.235, ch * 0.08, cw * 0.44, 0.86)
    else:
        top = 300 if tall else int(ch * 0.035)
        yb = titles(c, [("TON ARBRE MEURT L'ÉTÉ ?", YEL, 150, -3), ("MAUVAISE DATE !", RED, 160, -4)],
                    cw / 2, top, cw * 0.94, 0.9)
        bottom = 1675 if tall else ch - 25
        ph = int(bottom - yb - 20)
        pw = min(int(ph * 0.55), (cw - 60) // 2)
        for i, kind in enumerate(("printemps", "automne")):
            p = panel(kind, pw, ph)
            x = cw / 2 - pw - 12 + i * (pw + 24) - 6
            c.alpha_composite(p, (int(x), int(yb + 18)))
    return c


# ------------------------------------------------------------ B : la Sainte-Catherine au jardin
def garden_view(cw, ch, ww, cx, cy):
    """Recadrage HD du jardin d'automne : fenêtre de largeur ww (coordonnées plein écran) centrée en (cx, cy)."""
    hd = photo_hd(A.AUTOMNE).convert("RGB")
    k = hd.width / 1080
    hh = ww * ch / cw
    x0 = min(max(cx - ww / 2, 0), 1080 - ww)
    y0 = min(max(cy - hh / 2, 0), 1920 - hh)
    im = hd.crop((int(x0 * k), int(y0 * k), int((x0 + ww) * k), int((y0 + hh) * k))).resize((cw, ch), Image.LANCZOS)
    s = cw / ww
    return im.convert("RGBA"), (lambda x, y: ((x - x0) * s, (y - y0) * s)), s


def leaves(c, n, seed):
    r = np.random.default_rng(seed)
    for _ in range(n):
        nm = A.LEAVES[int(r.integers(0, 2))]
        ob(c, nm, r.uniform(0, c.width), r.uniform(c.height * 0.1, c.height * 0.85), r.uniform(40, 75),
           rot=r.uniform(-60, 60))


def scene_b(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    if land:
        ww, cx, cy = 1080, 540, A.SPOT[1] - 0.45 * 1080 * ch / cw
    elif tall:
        ww, cx, cy = 900, A.SPOT[0] - 110, A.SPOT[1] - 520
    else:
        ww, cx, cy = 830, A.SPOT[0] - 120, A.SPOT[1] - 380
    c, P, s = garden_view(cw, ch, ww, cx, cy)
    top_shade(c, 0.45, 160)
    x, y = P(*A.SPOT)
    if not land:
        s *= 1.3
    if land:
        x, y = cw * 0.66, ch * 0.96
        s = (ch * 0.9) / A.TREE_H
    # le jeune arbre fraîchement planté, terre retournée au pied, pelle plantée à côté
    shadow(c, x + 30 * s, y, 230 * s, 80)
    lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([x - 125 * s, y - 32 * s, x + 125 * s, y + 30 * s], fill=(70, 48, 32, 240))
    c.alpha_composite(lay)
    ob(c, A.TAS, x - 250 * s, y + 18 * s, 250 * s, anchor="bottom")
    A.tree(c, A.NU, x, y, A.TREE_H * s, 0.0)
    ob(c, A.PELLE, x + 190 * s, y + 12 * s, 62 * s, anchor="bottom", rot=-5)
    leaves(c, 9 if not land else 7, 4)
    cal = A.calendar_img(380)
    if land:
        put(c, cal, cw * 0.9, ch * 0.3, 0.5, -6)
        titles(c, [("À LA SAINTE-", YEL, 120, -3), ("CATHERINE…", YEL, 120, -3), ("TOUT BOIS", WHITE, 120, -3),
                   ("PREND RACINE !", LIGHT_GREEN, 112, -4)], cw * 0.25, ch * 0.08, cw * 0.47, 0.88)
    else:
        top = 300 if tall else int(ch * 0.04)
        yb = titles(c, [("À LA SAINTE-CATHERINE…", YEL, 150, -3), ("TOUT BOIS", WHITE, 150, -3),
                        ("PREND RACINE !", LIGHT_GREEN, 150, -4)], cw / 2, top, cw * 0.94, 0.88)
        put(c, cal, cw * 0.2, yb + (ch * 0.2 if not tall else 250), 0.78, -7)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for tg, fn in (("", scene_a), ("_b", scene_b)):
        for f, (cw, ch) in FORMATS.items():
            p = os.path.join(OUT, f"miniature_arbre_automne{tg}_{f}.jpg")
            fn(cw, ch).convert("RGB").save(p, quality=93)
            print(p)


if __name__ == "__main__":
    main()
