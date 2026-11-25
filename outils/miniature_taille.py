"""Miniatures « tailler ses fruitiers en hiver » : python3 outils/miniature_taille.py
→ output/miniatures/miniature_taille{,_b}_{3x4,9x16,16x9}.jpg
A : la prairie givrée, le pommier nu, le sécateur barré : « TU TAILLES EN PLEIN GEL ? ARRÊTE ! ».
B : fond beige, la coupe éclatée par le gel ✗ / la coupe nette un jour sans gel ✓."""
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from gfx import YEL, RED, WHITE, BLUE, GREEN, DARK, F_TITLE, title_img, icon, put, tag_img, text_img, W, H  # noqa
from scenes_citron import photo_hd  # noqa: E402
from scenes_fumier import Cam  # noqa: E402
from scenes_arrosage_soir import thermo_cold  # noqa: E402
import scenes_taille as T  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "miniatures")
FORMATS = {"3x4": (1080, 1440), "9x16": (1080, 1920), "16x9": (1280, 720)}


def titles(c, lines, cx, y0, maxw, gap=0.9):
    y = y0
    for txt, col, size, rot in lines:
        im = title_img(txt, col, size, maxw)
        put(c, im, cx, y + im.height / 2, 1.0, rot)
        y += im.height * gap
    return y


def frozen_layer():
    """Verger nu, pommier devant, cerisier, sécateur barré (calque transparent, cadre plein écran)."""
    cam = Cam(1.0, 540, 1100)
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    T.orchard(c, cam, 3)
    T.tree(c, cam, T.POM[2], T.P_SPOT)
    T.tree(c, cam, T.CER[3], T.C_SPOT)
    X, Y = T.on_tree(cam, *T.SNIP_PTS[1])
    T.secateur(c, X, Y, 0.0, 620, rot=-20)
    put(c, icon("nosign", 300), X + 90, Y + 40, 1.0)
    return c


def darken_top(c, frac=0.4, a=0.45):
    arr = np.asarray(c).astype(np.float32)
    h = arr.shape[0]
    yy = np.arange(h)[:, None]
    arr[..., :3] *= (1 - np.clip((h * frac - yy) / (h * frac), 0, 1) ** 1.4 * a)[..., None]
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def frozen_scene():
    c = photo_hd(T.GIVRE).resize((W, H), Image.LANCZOS).convert("RGBA")
    c.alpha_composite(frozen_layer())
    return darken_top(c, 700 / H)


def fit(img, cw, ch, cy):
    k = cw / img.width
    im = img.resize((cw, int(img.height * k)), Image.LANCZOS)
    y0 = int(min(max(cy * k - ch / 2, 0), im.height - ch))
    return im.crop((0, y0, cw, y0 + ch))


def scene_a(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    full = frozen_scene() if not land else None
    if land:
        bg = photo_hd(T.GIVRE).convert("RGBA")
        bg = bg.resize((cw, int(bg.height * cw / bg.width)), Image.LANCZOS)
        y0 = int(bg.height * 0.52 - ch / 2)
        c = bg.crop((0, y0, cw, y0 + ch))
        lay = frozen_layer()
        lay = lay.crop(lay.getbbox())
        k = ch * 0.98 / lay.height
        put(c, lay, cw * 0.32, ch / 2 + 6, k)
        c = darken_top(c, 0.35, 0.3)
        titles(c, [("TU TAILLES", WHITE, 120, -3), ("EN PLEIN GEL ?", BLUE, 115, -3), ("ARRÊTE !", RED, 150, -4)],
               cw * 0.76, ch * 0.08, cw * 0.44, 0.86)
    else:
        c = fit(full, cw, ch, 1000 if tall else 1080).copy()
        yb = titles(c, [("TU TAILLES EN PLEIN GEL ?", WHITE, 140, -3), ("ARRÊTE !", RED, 190, -4)],
                    cw / 2, 290 if tall else ch * 0.04, cw * 0.94, 0.9)
        put(c, thermo_cold(150), cw * 0.88, yb + 120, 1.0)
        put(c, text_img("-5 °C", F_TITLE, 80, BLUE, 7, DARK), cw * 0.88, yb + 260, 1.0)
    return c


def beige(cw, ch):
    return T.beige().resize((cw, ch), Image.LANCZOS)


def branches_img():
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, (nm, y, good, lbl) in enumerate(((T.BR[3], 700, False, "EN PLEIN GEL"),
                                           (T.BR[1], 1200, True, "UN JOUR SANS GEL"))):
        T.branch(c, nm, 470, y, 1000, rot=(-3, 3)[i])
        cx, cy = T.cut_pt(470, y, 1000, nm)
        put(c, icon("check" if good else "cross", 150), cx - 20, cy - 190, 1.0)
        put(c, tag_img(lbl, 60), 330, y + 190, 1.0, (-5, 4)[i])
    return c.crop(c.getbbox())


def scene_b(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    c = beige(cw, ch)
    p = branches_img()
    if land:
        k = min(ch * 0.9 / p.height, cw * 0.52 / p.width)
        put(c, p, cw * 0.7, ch / 2, k)
        titles(c, [("LE GEL FAIT", WHITE, 120, -3), ("ÉCLATER", RED, 150, -4), ("TES COUPES !", RED, 120, -4)],
               cw * 0.23, ch * 0.1, cw * 0.42, 0.86)
    else:
        yb = titles(c, [("LE GEL FAIT ÉCLATER", WHITE, 140, -3), ("TES COUPES !", RED, 170, -4)],
                    cw / 2, 290 if tall else ch * 0.04, cw * 0.94, 0.9)
        bottom = 1640 if tall else ch - 30
        k = min((bottom - yb - 40) / p.height, cw * 0.96 / p.width)
        put(c, p, cw / 2, (yb + 20 + bottom) / 2, k)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for tg, fn in (("", scene_a), ("_b", scene_b)):
        for f, (cw, ch) in FORMATS.items():
            path = os.path.join(OUT, f"miniature_taille{tg}_{f}.jpg")
            fn(cw, ch).convert("RGB").save(path, quality=93)
            print(path)


if __name__ == "__main__":
    main()
