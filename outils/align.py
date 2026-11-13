"""Aligne le texte exact (<dossier>/script.txt) sur l'horodatage zipformer → <dossier>/words.json.
Ensuite : temps -0,25 s (la reconnaissance est en retard) et ponctuation collée au mot → assets/audio/<projet>/voix_mots.json."""
import json, sys, unicodedata, difflib
S = sys.argv[1]
z = json.load(open(S + "/zf.json"))
def norm(c):
    c = unicodedata.normalize('NFD', c.lower()); return ''.join(ch for ch in c if ch.isalnum())
zc = []; zt = []
for tok, t in zip(z["tokens"], z["ts"]):
    for ch in norm(tok.replace('▁', '')): zc.append(ch); zt.append(t)
NUM = {"1": "un", "2": "deux", "3": "trois", "4": "quatre", "5": "cinq", "10": "dix", "20": "vingt", "200": "deuxcents", "300": "troiscents", "450": "quatrecentcinquante", "cm": "centimètres", "cm,": "centimètres", "2/3": "deuxtiers"}
words = open(S + "/script.txt").read().split()
sc = []; owner = []
for i, w in enumerate(words):
    for ch in norm(NUM.get(w, w)): sc.append(ch); owner.append(i)
sm = difflib.SequenceMatcher(None, ''.join(sc), ''.join(zc), autojunk=False)
mapt = [None] * len(sc)
for a, b, n in sm.get_matching_blocks():
    for k in range(n): mapt[a + k] = zt[b + k]
out = []
for i, w in enumerate(words):
    ts = [mapt[k] for k in range(len(sc)) if owner[k] == i and mapt[k] is not None]
    out.append({"w": w, "s": min(ts) if ts else None, "e": max(ts) if ts else None})
for i, o in enumerate(out):
    if o["s"] is None:
        p = next((out[j]["e"] for j in range(i - 1, -1, -1) if out[j]["e"] is not None), 0)
        n = next((out[j]["s"] for j in range(i + 1, len(out)) if out[j]["s"] is not None), p + 0.3)
        o["s"] = p; o["e"] = n
json.dump(out, open(S + "/words.json", "w"), ensure_ascii=False, indent=0)
if len(sys.argv) > 2:      # écrit aussi le fichier du projet
    res = []
    for o in out:
        if o["w"] in "?!:" and res:
            res[-1]["w"] += " " + o["w"]; continue
        res.append(dict(w=o["w"], s=round(max(0, o["s"] - 0.25), 2), e=round(max(0, o["e"] - 0.25) + 0.1, 2)))
    json.dump(res, open(sys.argv[2], "w"), ensure_ascii=False, indent=0)
print(' '.join(f"{o['w']}@{o['s']:.2f}" for o in out))
