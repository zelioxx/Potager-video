"""Rendu des vidéos verticales 1080x1920.

    python3 src/render.py [ail|poireau] [--preview t1,t2,...]
"""
import json
import math
import os
import re
import subprocess
import sys
import unicodedata
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx import (W, H, YEL, WHITE, DARK, F_CAP, text_img, put, ring_badge, clamp, ease_out_back, ease_io,  # noqa: E402
                 life, ROOT)
import importlib  # noqa: E402
import sfx  # noqa: E402

FPS = 30
WHIP = 0.24  # durée de la transition « whip » floutée
OUT = os.path.join(ROOT, "output")
AUD = os.path.join(ROOT, "assets", "audio")

PROJECTS = {
    "ail": dict(
        scenes="scenes", dur=71.6, voice=os.path.join(AUD, "voix.mp3"),
        words=os.path.join(AUD, "voix_mots.json"), out="ail_echalote_printemps_1080x1920.mp4",
        highlight="""échalotes automne pourrissent printemps pourquoi expliquer l'ail l'échalote bien racines tête
trois pièges 1 terre argileuse l'eau l'hiver bulbe l'humide pourrit 2 l'enfonces profond pareil étouffe bon
geste pointe affleurer surface 3 gourmands oiseaux picorer déterrer caïeux nuisibles régalent solution plante mars
réchauffe s'égoutte variétés ail printanor rose lautrec échalote jermor longor mikor humidité pourriture récolte
toi commentaire abonne-toi potager"""),
    "poireau": dict(
        scenes="scenes_poireau", dur=60.7, voice=os.path.join(AUD, "poireau", "voix.mp3"),
        words=os.path.join(AUD, "poireau", "voix_mots.json"), out="poireau_repousse_1080x1920.mp4",
        highlight="""stop jette poireau pousser montre cuisines pied racines coupe-le 4 5 cm moins verre d'eau pose
bas astuce couvrir pourrit fenêtre lumineuse change deux jours propre attend centre pousse verte semaine grandi
loin blanches longues replante-le pot potager terre nourrir grossir légume récoltes zéro gaspillage abonne-toi
commentaire repousser"""),
    "arrosage": dict(
        scenes="scenes_arrosage", dur=76.8, voice=os.path.join(AUD, "arrosage", "voix.mp3"),
        words=os.path.join(AUD, "arrosage", "voix_mots.json"), out="arrosage_plantes_1080x1920.mp4",
        highlight="""plante d'intérieur jaunit ramollit l'arroses plus mauvaise idée tue t'explique racines d'eau d'air
trop souvent gorgée étouffent l'excès d'humidité pourrir pourrie boit pieds l'eau meurt soif savoir feuilles
jaunes molles terre humide odeur marécage temps stop arrête d'arroser sécher sèche 2 3 centimètres test doigt
imparable tard rempote sors coupe noires saines fermes claires mélange respire tiers perlite fibres chips coco
terreau drainant respirer pot percé stagne soucoupe abonne-toi astuces commentaire plantes sauvetage"""),
    "bouture": dict(
        scenes="scenes_bouture", dur=39.9, voice=os.path.join(AUD, "bouture", "voix.mp3"),
        words=os.path.join(AUD, "bouture", "voix_mots.json"), out="bouture_petits_fruitiers_1080x1920.mp4",
        highlight="""tailles groseilliers jettes branches non plants gratuits cassissiers figuiers feuilles tombent
bouturent super facilement étape 1 2 3 4 branche l'année crayon coupe 20 cm bas biais bourgeon haut droit
au-dessus jamais l'envers enfonce-la 2/3 terre légère l'abri vent l'oublies l'hiver printemps racines nouveaux
abonne-toi astuces potager"""),
    "aromatiques": dict(
        scenes="scenes_aromatiques", dur=41.4, voice=os.path.join(AUD, "aromatiques", "voix.mp3"),
        words=os.path.join(AUD, "aromatiques", "voix_mots.json"), out="bouture_aromatiques_1080x1920.mp4",
        highlight="""romarin gratuits seule plante 10 thym lavande sauge sarriette maintenant bouturent menthe simple
verre d'eau racines étape 1 2 3 4 coupe tige cm fleurs retire feuilles bas plante-la terreau drainant secret
arrose peine détestent pieds mouillés l'abri froid patientes printemps nouveaux plants abonne-toi astuces
potager potagers louis"""),
    "compost": dict(
        scenes="scenes_compost", dur=37.8, voice=os.path.join(AUD, "compost", "voix.mp3"),
        words=os.path.join(AUD, "compost", "voix_mots.json"), out="compost_3_erreurs_1080x1920.mp4",
        highlight="""l'état composteur bien 3 erreurs erreur 1 2 épluchures humide pourrit mauvais ajoute sec feuilles
mortes carton brun branches viande poisson produits laitiers odeurs rats jamais remuer compost étouffe fourche
temps reparti tout abonne-toi astuces potager potagers louis"""),
    "ananas": dict(
        scenes="scenes_ananas", dur=68.4, voice=os.path.join(AUD, "ananas", "voix.mp3"),
        words=os.path.join(AUD, "ananas", "voix_mots.json"), out="ananas_bouture_1080x1920.mp4",
        highlight="""jettes tête ananas erreur pousser nouvel montre choisis feuilles vertes taches brunes fruit mûr
trop étape 1 2 3 4 tourne touffe détacher retire petites bas 2 3 cm tige secret sécher jours pourrit plonge base
verre d'eau chaud lumière change régulièrement semaines racines apparaissent plante-la pot terre drainante
chaleur arrosage léger attention pourrissent fleurit ans pomme mûre sac transparent gaz floraison patient
premier fierté croquer abonne-toi astuces"""),
    "ananas_v2": dict(
        scenes="scenes_ananas_v2", dur=68.4, voice=os.path.join(AUD, "ananas", "voix.mp3"),
        words=os.path.join(AUD, "ananas", "voix_mots.json"), out="ananas_bouture_v2_1080x1920.mp4",
        highlight="""jettes tête ananas erreur pousser nouvel montre choisis feuilles vertes taches brunes fruit mûr
trop étape 1 2 3 4 tourne touffe détacher retire petites bas 2 3 cm tige secret sécher jours pourrit plonge base
verre d'eau chaud lumière change régulièrement semaines racines apparaissent plante-la pot terre drainante
chaleur arrosage léger attention pourrissent fleurit ans pomme mûre sac transparent gaz floraison patient
premier fierté croquer abonne-toi astuces"""),
    "hortensia": dict(
        scenes="scenes_hortensia", dur=26.4, voice=os.path.join(AUD, "hortensia", "voix.mp3"),
        words=os.path.join(AUD, "hortensia", "voix_mots.json"), out="hortensia_bouture_1080x1920.mp4",
        highlight="""hortensia gratuit seule tige oui simple coupe l'année sans fleurs deux paires bourgeons retire
feuilles bas haut plante-la mélange terreau sable l'abri froid secret humide jamais détrempée printemps racines
nouvel abonne-toi astuces"""),
    "avocat": dict(
        scenes="scenes_avocat", dur=23.7, voice=os.path.join(AUD, "avocat", "voix.mp3"),
        words=os.path.join(AUD, "avocat", "voix_mots.json"), out="avocat_noyau_1080x1920.mp4",
        highlight="""jettes noyau d'avocat dommage arbre dort lave-le trois cure-dents verre d'eau plat bas moitié
immergé chaud lumière change l'eau semaine patience semaines fend racine tige abonne-toi astuces"""),
    "mangue": dict(
        scenes="scenes_mangue", dur=30.9, voice=os.path.join(AUD, "mangue", "voix.mp3"),
        words=os.path.join(AUD, "mangue", "voix_mots.json"), out="mangue_noyau_1080x1920.mp4",
        highlight="""jettes noyau mangue attention graine cachée étape 1 2 3 4 gratte chair sécher journée ouvre-le
délicatement ciseau côté grosse haricot géant enroule-la essuie-tout humide boîte fermée chaud patience
semaines racine sort planter pot abonne-toi astuces"""),
    "feuilles": dict(
        scenes="scenes_feuilles", dur=29.8, voice=os.path.join(AUD, "feuilles", "voix.mp3"),
        words=os.path.join(AUD, "feuilles", "voix_mots.json"), out="feuilles_mortes_paillage_1080x1920.mp4",
        highlight="""tempête austine vidé arbres bonne nouvelle paillage gratuit étalées potager feuilles mortes
protègent froid pluie dessous vers régalent printemps l'engrais souple conseil tondeuse broyées croûte
décomposent vite week-end râteau brouette abonne-toi astuces"""),
    "gingembre": dict(
        scenes="scenes_gingembre", dur=29.3, voice=os.path.join(AUD, "gingembre", "voix.mp3"),
        words=os.path.join(AUD, "gingembre", "voix_mots.json"), out="gingembre_repousse_1080x1920.mp4",
        highlight="""gingembre panier jette repousser étape 1 2 3 dodu yeux bourgeons tremper nuit l'eau tiède
couche-le pot haut surface secret chaleur peine humide semaines pousse verte terre abonne-toi astuces"""),
    "radiateur": dict(
        scenes="scenes_radiateur", dur=25.5, voice=os.path.join(AUD, "radiateur", "voix.mp3"),
        words=os.path.join(AUD, "radiateur", "voix_mots.json"), out="radiateur_pointes_brunes_1080x1920.mp4",
        highlight="""pointes brunissent chauffage coupable radiateur chaud sec boire vite robinet calcaire
s'accumule feuilles brûle éloigne-la plateau billes d'argile fond d'eau humidifie l'air arrose pluie
abonne-toi astuces plantes"""),
    "tulipes": dict(
        scenes="scenes_tulipes", dur=32.5, voice=os.path.join(AUD, "tulipes", "voix.mp3"),
        words=os.path.join(AUD, "tulipes", "voix_mots.json"), out="tulipes_bulbes_1080x1920.mp4",
        highlight="""printemps tulipes partout mêmes trop tard bonne nouvelle maintenant planter tulipe jonquille
crocus enterre bulbe 2 3 fois hauteur pointe haut l'envers drainante pourrit automne froid l'hiver fleurir
beaux parterres abonne-toi astuces"""),
    "citron": dict(
        scenes="scenes_citron", dur=29.6, voice=os.path.join(AUD, "citron", "voix.mp3"),
        words=os.path.join(AUD, "citron", "voix_mots.json"), out="citron_pepin_1080x1920.mp4",
        highlight="""jettes pépins citron arrête arbres simple germer frais rince-les retire délicatement peau
blanche secret deux fois vite sopalin humide boîte film transparent chaud lumière 2 3 semaines feuilles
sentent abonne-toi astuces"""),
    "avocat2": dict(
        scenes="scenes_avocat2", dur=20.9, voice=os.path.join(AUD, "avocat2", "voix.mp3"),
        words=os.path.join(AUD, "avocat2", "voix_mots.json"), out="avocat_noyau_v2_1080x1920.mp4",
        highlight="""jettes noyau d'avocat arbre savoir lave-le retire peau brune enroule-le essuie-tout humide
boîte fermée chaud attend semaines fend racine sort abonne-toi"""),
    "chrysantheme": dict(
        scenes="scenes_chrysantheme", dur=17.6, voice=os.path.join(AUD, "chrysantheme", "voix.mp3"),
        words=os.path.join(AUD, "chrysantheme", "voix_mots.json"), out="chrysanthemes_1080x1920.mp4",
        highlight="""chrysanthèmes gratuits acheter explique semaine milliers poubelle récupère-les coupe tiges
10 cm plante-les jardin l'automne prochain refleurissent gratuitement malin"""),
    "avocat3": dict(
        scenes="scenes_avocat3", dur=20.9, voice=os.path.join(AUD, "avocat2", "voix.mp3"),
        words=os.path.join(AUD, "avocat2", "voix_mots.json"), out="avocat_variante_1080x1920.mp4",
        highlight="""jettes noyau d'avocat arbre savoir lave-le retire peau brune enroule-le essuie-tout humide
boîte fermée chaud attend semaines fend racine sort abonne-toi"""),
    "mangue2": dict(
        scenes="scenes_mangue2", dur=23.6, voice=os.path.join(AUD, "mangue2", "voix.mp3"),
        words=os.path.join(AUD, "mangue2", "voix_mots.json"), out="mangue_noyau_v3_1080x1920.mp4",
        highlight="""jettes noyau mangue superbe plante d'intérieur nettoie graine l'eau ouvre coque ciseau côté
grosse haricot géant enroule-la essuie-tout humide boîte fermée chaud semaines racine sort magnifique abonnez-vous
astuces"""),
    "banane": dict(
        scenes="scenes_banane", dur=28.3, voice=os.path.join(AUD, "banane", "voix.mp3"),
        words=os.path.join(AUD, "banane", "voix_mots.json"), out="banane_engrais_1080x1920.mp4",
        highlight="""peau banane engrais vraiment surprendre oui potassium fleurs tomates adorent telle quelle
mois décomposer mouches rongeurs l'eau presque rien coupe-la petits morceaux compost décomposant vrais nutriments
abonnez-vous astuces"""),
}
PROJECT = next((a for a in sys.argv[1:] if a in PROJECTS), "ail")
CFG = PROJECTS[PROJECT]
scenes = importlib.import_module(CFG["scenes"])
DUR = CFG["dur"]
VOICE = CFG["voice"]
WORDS = json.load(open(CFG["words"]))

CAP_Y = 1545
CAP_SIZE = 76
HIGHLIGHT = CFG["highlight"].split()


def key(wd):
    return re.sub(r"[^\w'\-]", "", wd.lower())


HL = {key(x) for x in HIGHLIGHT}


# ------------------------------------------------------------- sous-titres
# style de sous-titres propre au projet (scenes.CAP_STYLE) : blocs de 3-4 mots, plus gros, affichés d'un coup
CAP_STYLE = getattr(scenes, "CAP_STYLE", None)
MAX_WORDS = CAP_STYLE["max_words"] if CAP_STYLE else 3
MAX_CHARS = CAP_STYLE["max_chars"] if CAP_STYLE else 20


def build_chunks():
    chunks, cur = [], []
    for i, o in enumerate(WORDS):
        if cur:
            prev = WORDS[cur[-1]]
            txt = " ".join(WORDS[j]["w"] for j in cur + [i])
            if (len(cur) >= MAX_WORDS or len(txt) > MAX_CHARS or re.search(r"[.,?!:]$", prev["w"])
                    or o["s"] - prev["e"] > 0.35):
                chunks.append(cur)
                cur = []
        cur.append(i)
    chunks.append(cur)
    out = []
    for k, ch in enumerate(chunks):
        start = WORDS[ch[0]]["s"] - 0.04
        nxt = WORDS[chunks[k + 1][0]]["s"] - 0.04 if k + 1 < len(chunks) else DUR
        end = min(nxt, WORDS[ch[-1]]["e"] + 0.7)
        out.append((start, end, ch))
    return out


CHUNKS = build_chunks()


def word_img(i, size):
    wd = WORDS[i]["w"]
    col = YEL if key(wd) in HL else WHITE
    return text_img(wd, F_CAP, size, col, 7, DARK, 7, DARK)


def captions_block(c, t):
    """Bloc de 3-4 mots affiché d'un coup (sur 1 ou 2 lignes), le mot prononcé légèrement grossi."""
    size, maxw = CAP_STYLE["size"], 990
    for start, end, ch in CHUNKS:
        if not (start <= t < end):
            continue
        imgs = [word_img(i, size) for i in ch]
        ov = 30 - 0.2 * size                   # chevauchement des marges ; garde une espace visible entre les mots
        lines, cur, cw = [], [], 0
        for i, im in zip(ch, imgs):
            add = im.width - (ov if cur else 0)
            if cur and cw + add > maxw:
                lines.append(cur)
                cur, cw = [], 0
                add = im.width
            cur.append((i, im))
            cw += add
        lines.append(cur)
        k = clamp((t - start) / 0.16)
        pop = 0.82 + 0.18 * ease_out_back(k, 2.0)
        lh = size * 1.12
        y0 = CAP_Y - (len(lines) - 1) * lh / 2
        for li, line in enumerate(lines):
            total = sum(im.width for _, im in line) - ov * (len(line) - 1)
            x = (W - total) / 2
            for i, im in line:
                ws, we = WORDS[i]["s"] - 0.04, WORDS[i]["e"]
                on = 1.08 if ws <= t < we + 0.05 else 1.0
                put(c, im, x + im.width / 2, y0 + li * lh + (1 - k) * 12, pop * on, 0, clamp(k * 3))
                x += im.width - ov


def captions(c, t):
    if t < getattr(scenes, "NO_CAPTION_UNTIL", 0.0):
        return
    if CAP_STYLE:
        captions_block(c, t)
        return
    for start, end, ch in CHUNKS:
        nc = getattr(scenes, "NO_CAPTION_UNTIL", 0.0)
        if not (start <= t < end) or (nc > 0 and start < nc):
            continue
        size = CAP_SIZE
        imgs = [word_img(i, size) for i in ch]
        total = sum(im.width for im in imgs) - 30 * (len(imgs) - 1)
        if total > 1000:
            size = int(size * 1000 / total)
            imgs = [word_img(i, size) for i in ch]
            total = sum(im.width for im in imgs) - 30 * (len(imgs) - 1)
        x = (W - total) / 2
        for i, im in zip(ch, imgs):
            ws = WORDS[i]["s"] - 0.04
            if t >= ws:
                k = clamp((t - ws) / 0.14)
                s = 0.7 + 0.3 * ease_out_back(k, 2.4)
                put(c, im, x + im.width / 2, CAP_Y + (1 - k) * 14, s, 0, clamp(k * 2.5))
            x += im.width - 30


# ------------------------------------------------------------- composition
def scene_at(t):
    for a, b, fn in scenes.SCENES:
        if a <= t < b:
            return a, b, fn
    return scenes.SCENES[-1]


def render_scene(fn, a, b, t):
    w, u = fn(t)
    # léger zoom avant continu sur le calque « monde »
    z = 1 + 0.035 * ease_io((t - a) / max(0.1, min(b, DUR) - a))
    if z > 1.001 and not getattr(fn, "raw", False):
        cw, ch = W / z, H / z
        x0, y0 = (W - cw) / 2, (H - ch) * 0.45
        w = w.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BILINEAR)
    w.alpha_composite(u)
    return w


def vblur(im, amount):
    if amount < 0.05:
        return im
    k = max(2, int(2 + amount * 60))
    return im.resize((W, max(8, H // k)), Image.BILINEAR).resize((W, H), Image.BILINEAR)


def frame(t):
    a, b, fn = scene_at(t)
    idx = [s[0] for s in scenes.SCENES].index(a)
    # transition « whip » verticale autour des coupes
    cut = None
    if idx > 0 and t < a + WHIP / 2:
        cut = a
        pa, pb, pfn = scenes.SCENES[idx - 1]
        prev = (pfn, pa, pb)
        nxt = (fn, a, b)
    elif t >= b - WHIP / 2 and idx + 1 < len(scenes.SCENES):
        cut = b
        prev = (fn, a, b)
        na, nb, nfn = scenes.SCENES[idx + 1]
        nxt = (nfn, na, nb)
    if cut is None:
        img = render_scene(fn, a, b, t)
    else:
        p = clamp((t - (cut - WHIP / 2)) / WHIP)
        e = ease_io(p)
        A = render_scene(prev[0], prev[1], prev[2], min(t, cut - 1e-3))
        B = render_scene(nxt[0], nxt[1], nxt[2], max(t, cut))
        blur = math.sin(math.pi * p)
        A, B = vblur(A, blur), vblur(B, blur)
        off = int(e * H)
        img = Image.new("RGBA", (W, H))
        img.paste(A, (0, -off))
        img.paste(B, (0, H - off))
    # badge piège (fixe)
    for n, t0, t1 in scenes.TRAPS:
        s = life(t, t0, t1, 0.35, 0.2)
        if s > 0:
            ring_badge(img, n, clamp((t - t0) / (t1 - t0)), s)
    captions(img, t)
    return img.convert("RGB")


def render_range(args):
    i0, i1, path = args
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                          "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(i0, i1):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return path


def build_audio(path):
    voice, sr = sf.read(VOICE, dtype="float32", always_2d=True)
    voice = voice.mean(1)
    if sr != sfx.SR:
        n = int(len(voice) * sfx.SR / sr)
        voice = np.interp(np.linspace(0, len(voice) - 1, n), np.arange(len(voice)), voice).astype(np.float32)
    n = int(DUR * sfx.SR)
    mix = np.zeros(n, np.float32)
    mix[: min(n, len(voice))] += voice[:n]
    cues = list(scenes.CUES)
    for a, b, fn in scenes.SCENES[1:]:
        cues.append((a - 0.2, "whoosh", getattr(scenes, "TRANS_GAIN", 0.32)))
    fx = sfx.render_track(cues, DUR)
    mix += fx * 0.55
    st = np.stack([mix, mix], 1)
    peak = np.abs(st).max()
    if peak > 0.98:
        st *= 0.98 / peak
    sf.write(path, st, sfx.SR)


# volume « TikTok » : voix compressée puis normalisée à ≈ -10 LUFS, limiteur pour ne jamais saturer
LOUD = ("highpass=f=70,acompressor=threshold=-24dB:ratio=4:attack=3:release=80:makeup=4,"
        "equalizer=f=3000:t=q:w=1:g=2,loudnorm=I=-10:TP=-1.5:LRA=7,"
        "volume=2dB,alimiter=limit=0.78:attack=2:release=40:level=false")   # ≈ -8 LUFS, pic < -0,5 dB


def main():
    os.makedirs(OUT, exist_ok=True)
    if "--preview" in sys.argv:
        for ts in sys.argv[sys.argv.index("--preview") + 1].split(","):
            frame(float(ts)).save(os.path.join(OUT, f"preview_{float(ts):05.2f}.jpg"), quality=88)
        return
    tmp = os.path.join(OUT, "tmp_" + PROJECT)
    os.makedirs(tmp, exist_ok=True)
    wav = os.path.join(tmp, "mix.wav")
    build_audio(wav)
    nf = int(DUR * FPS)
    nproc = os.cpu_count() or 4
    step = math.ceil(nf / nproc)
    jobs = [(i, min(nf, i + step), os.path.join(tmp, f"part{k:02d}.mp4")) for k, i in enumerate(range(0, nf, step))]
    with Pool(len(jobs)) as pool:
        parts = pool.map(render_range, jobs)
    lst = os.path.join(tmp, "parts.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    final = os.path.join(OUT, CFG["out"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                    "-c:v", "copy", "-af", LOUD, "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-shortest", "-movflags", "+faststart", final], check=True)
    print(final)


if __name__ == "__main__":
    main()
