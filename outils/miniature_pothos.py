"""Miniatures « plante d'intérieur qui jaunit en hiver » : python3 outils/miniature_pothos.py
→ output/miniatures/miniature_pothos_lumiere{,_b}_{3x4,9x16,16x9}.jpg
3x4 : TikTok et grille Instagram ; 9x16 : couverture Reels Instagram / Facebook, YouTube Shorts ;
16x9 : vignette YouTube classique.
A : le pothos qui jaunit sur le meuble du salon, le soir à la lampe ; « ce n'est pas l'eau » (goutte barrée).
B : fond beige, les deux pots en coupe : racines saines ✓ / racines pourries dans l'eau qui stagne ✗."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from gfx import YEL, RED, WHITE, DARK, CREAM, title_img, icon, put, tag_img  # noqa: E402
from scenes_citron import photo_hd  # noqa: E402
import scenes_pothos_lumiere as P  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "miniatures")
FORMATS = {"3x4": (1080, 1440), "9x16": (1080, 1920), "16x9": (1280, 720)}


def titles(c, lines, cx, y0, maxw, gap=0.9):
    y = y0
    for txt, col, size, rot in lines:
        im = title_img(txt, col, size, maxw)
        put(c, im, cx, y + im.height / 2, 1.0, rot)
        y += im.height * gap
    return y


def evening_salon(cw, ch, ww, cx, cy):
    """Salon de l'orchidée recadré (fenêtre ww de large, coordonnées plein écran), ambiance soirée à la lampe."""
    hd = photo_hd(P.SALON).convert("RGB")
    k = hd.width / 1080
    hh = ww * ch / cw
    x0 = min(max(cx - ww / 2, 0), 1080 - ww)
    y0 = min(max(cy - hh / 2, 0), 1920 - hh)
    im = hd.crop((int(x0 * k), int(y0 * k), int((x0 + ww) * k), int((y0 + hh) * k))).resize((cw, ch), Image.LANCZOS)
    s = cw / ww
    a = np.asarray(im).astype(np.float32) / 255
    out = a * np.array([1.0, 0.86, 0.7], np.float32) * 0.62
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    lx, ly = (P.LAMP[0] - x0) * s, (P.LAMP[1] - y0) * s
    r = 650 * s
    glow = np.exp(-((xx - lx) ** 2 + (yy - ly) ** 2) / (2 * r * r))
    out += a * glow[..., None] * np.array([0.8, 0.6, 0.35], np.float32)
    vig = 1 - 0.35 * np.clip((xx - cw / 2) ** 2 / (cw * 0.75) ** 2 + (yy - ch / 2) ** 2 / (ch * 0.7) ** 2, 0, 1)
    out *= vig[..., None]
    img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    # haut assombri pour le titre
    al = (np.clip((ch * 0.4 - np.arange(ch)) / (ch * 0.4), 0, 1) ** 1.4 * 140)[:, None]
    sh = Image.new("RGBA", (cw, ch), (20, 14, 8, 0))
    sh.putalpha(Image.fromarray(np.repeat(al, cw, 1).astype("uint8")))
    img.alpha_composite(sh)
    return img, (lambda x, y: ((x - x0) * s, (y - y0) * s)), s


def scene_a(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    if land:
        c, Pt, s = evening_salon(cw, ch, 1080, 540, 1150)
        px, py, ph = cw * 0.72, ch * 0.98, ch * 0.9
    elif tall:
        c, Pt, s = evening_salon(cw, ch, 1080, 540, 960)
        px, py, ph = cw * 0.52, 1640, 900
    else:
        c, Pt, s = evening_salon(cw, ch, 1080, 540, 1000)
        px, py, ph = cw * 0.52, ch * 0.97, 880
    P.pothos(c, px, py, ph, 1.0)
    if land:
        titles(c, [("TA PLANTE", YEL, 150, -3), ("JAUNIT ?", YEL, 150, -3), ("CE N'EST PAS", WHITE, 110, -3),
                   ("L'EAU !", RED, 130, -4)], cw * 0.25, ch * 0.07, cw * 0.46, 0.86)
        put(c, icon("drop", 110), cw * 0.92, ch * 0.2, 1.0)
        put(c, icon("nosign", 160), cw * 0.92, ch * 0.2, 1.0)
    else:
        top = 290 if tall else int(ch * 0.04)
        yb = titles(c, [("TA PLANTE JAUNIT ?", YEL, 160, -3), ("CE N'EST PAS L'EAU !", RED, 140, -4)],
                    cw / 2, top, cw * 0.94, 0.9)
        put(c, icon("drop", 130), cw * 0.17, yb + 150, 1.0)
        put(c, icon("nosign", 190), cw * 0.17, yb + 150, 1.0)
    return c


def beige(cw, ch):
    c = Image.new("RGBA", (cw, ch), (238, 228, 208, 255))
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    v = 1 - 0.12 * np.clip(((xx - cw / 2) / cw) ** 2 + ((yy - ch * 0.45) / ch) ** 2, 0, 1) * 2
    a = np.asarray(c).astype(np.float32)
    a[..., :3] *= v[..., None]
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def section(c, name, x, y, h, good, lbl):
    P.soft_shadow(c, x, y + h * 0.01, h * 0.62, 80)
    P.sp(c, name, x, y, h, 0.5, 1.0)
    put(c, tag_img(lbl, int(h * 0.055)), x, y + h * 0.075, 1.0, -4 if good else 4)
    put(c, icon("check" if good else "cross", int(h * 0.17)), x, y - h * 1.04, 1.0)


def scene_b(cw, ch):
    land = cw > ch
    tall = ch / cw > 1.5
    c = beige(cw, ch)
    if land:
        h = ch * 0.6
        section(c, P.COUPE, cw * 0.555, ch * 0.86, h, True, "TERRE SÈCHE")
        section(c, P.COUPE_P, cw * 0.83, ch * 0.86, h, False, "EAU QUI STAGNE")
        titles(c, [("FEUILLES", YEL, 140, -3), ("JAUNES ?", YEL, 140, -3), ("ARROSE", RED, 130, -4),
                   ("MOINS !", RED, 130, -4)], cw * 0.2, ch * 0.08, cw * 0.38, 0.86)
    else:
        top = 290 if tall else int(ch * 0.04)
        yb = titles(c, [("FEUILLES JAUNES ?", YEL, 160, -3), ("ARROSE MOINS !", RED, 160, -4)],
                    cw / 2, top, cw * 0.94, 0.9)
        base = (1590 if tall else ch * 0.9)
        h = min(600, (base - yb - 150) / 1.04)
        section(c, P.COUPE, cw * 0.26, base, h, True, "TERRE SÈCHE")
        section(c, P.COUPE_P, cw * 0.74, base, h, False, "EAU QUI STAGNE")
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for tg, fn in (("", scene_a), ("_b", scene_b)):
        for f, (cw, ch) in FORMATS.items():
            p = os.path.join(OUT, f"miniature_pothos_lumiere{tg}_{f}.jpg")
            fn(cw, ch).convert("RGB").save(p, quality=93)
            print(p)


if __name__ == "__main__":
    main()
