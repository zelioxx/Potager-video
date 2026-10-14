"""Builds index.html + assets/audio/voiceover.wav from build/voice.json.

Run after build/tts.py:  python3 -I build/build.py .
Every visual cue is pinned to a spoken word, so re-generating the voice re-times the video.
"""
import json, re, random, subprocess, sys
import numpy as np, soundfile as sf
sys.path.insert(0, f"{sys.argv[1]}/build")
from music import make_music

P = sys.argv[1]
voice = json.load(open(f"{P}/build/voice.json"))

# ---------------------------------------------------------------- timing
LEAD = 0.25
GAP = 0.32
SECTION_GAP = {"s3": 0.55, "s5": 1.15, "s7": 0.55, "s8": 0.55, "s9": 0.35, "s10": 0.75, "s11": 0.9}
TAIL = 1.4

starts, t = {}, LEAD
for ln in voice:
    t += SECTION_GAP.get(ln["id"], 0 if ln is voice[0] else GAP)
    starts[ln["id"]] = round(t, 3)
    t += ln["duration"]
DURATION = round(t + TAIL, 2)


def syllables(word):
    return max(1, len(re.findall(r"[aeiouyàâäéèêëîïôöùûüœ]+", word.lower())))


words = []  # {line, text, start, end}
for ln in voice:
    for cl in ln["clauses"]:
        toks = []
        for tok in cl["text"].split():  # French spacing: glue "?", "!", ":" onto the word before
            if toks and not re.search(r"\w", tok):
                toks[-1] += " " + tok
            else:
                toks.append(tok)
        weights = [syllables(w) + 0.35 for w in toks]
        a, b = cl["start"] + 0.03, cl["end"] - 0.04
        acc = a
        for tok, wgt in zip(toks, weights):
            d = (b - a) * wgt / sum(weights)
            words.append({"line": ln["id"], "text": tok, "start": round(starts[ln["id"]] + acc, 3),
                          "end": round(starts[ln["id"]] + acc + d, 3), "clause": id(cl)})
            acc += d


def W(line, frag, n=0):
    """Global start time of the n-th word of `line` containing `frag`."""
    hits = [w for w in words if w["line"] == line and frag.lower() in w["text"].lower()]
    return hits[n]["start"]


def L(line):
    return starts[line]


def LE(line):
    ln = next(v for v in voice if v["id"] == line)
    return round(starts[line] + ln["duration"], 3)


# ---------------------------------------------------------------- voiceover track
sr = voice[0]["sample_rate"]
track = np.zeros(int(DURATION * sr), dtype=np.float32)
for ln in voice:
    a, r = sf.read(f"{P}/assets/audio/{ln['id']}.wav", dtype="float32")
    assert r == sr, (ln["id"], r)
    i = int(starts[ln["id"]] * sr)
    track[i:i + len(a)] += a
peak = np.max(np.abs(track))
track = track / peak * 0.89
sf.write(f"{P}/build/voiceover_raw.wav", track, sr)
# punchier, social-media loudness: light compression, presence lift, then -14 LUFS
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{P}/build/voiceover_raw.wav", "-af",
                "acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=4,"
                "equalizer=f=3500:t=q:w=1.2:g=2.5,loudnorm=I=-12:TP=-1.5:LRA=7",
                "-ar", str(sr), f"{P}/assets/audio/voiceover.wav"], check=True)

# ---------------------------------------------------------------- captions (2–3 word groups)
groups = []
for ln in voice:
    for cl in ln["clauses"]:
        cw = [w for w in words if w["clause"] == id(cl)]
        sizes, n = [], len(cw)
        while n > 0:
            sizes.append(min(3, n)); n -= sizes[-1]
        if len(sizes) > 1 and sizes[-1] == 1:
            sizes[-1], sizes[-2] = 2, sizes[-2] - 1
        i = 0
        for s in sizes:
            groups.append(cw[i:i + s]); i += s
cap_html, cap_js = [], []
for gi, g in enumerate(groups):
    nxt = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else DURATION
    end = min(nxt, g[-1]["end"] + 0.55)
    spans = " ".join(f'<span class="w" id="w{gi}_{k}">{w["text"]}</span>' for k, w in enumerate(g))
    cap_html.append(f'<div class="cap" id="cap{gi}">{spans}</div>')
    cap_js.append(f'cap("#cap{gi}", {g[0]["start"]:.3f}, {end:.3f}, [{",".join(f"{w["start"]:.3f}" for w in g)}]);')

# ---------------------------------------------------------------- soil textures (seeded, static)
def specks(seed, colors, n=260):
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        x, y = rnd.uniform(0, 1080), rnd.uniform(14, 1160)
        rx = rnd.uniform(3, 9); ry = rx * rnd.uniform(0.55, 0.9)
        out.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{rnd.choice(colors)}"/>')
    return f'<svg class="specks" viewBox="0 0 1080 1160" width="1080" height="1160">{"".join(out)}</svg>'


SOIL_SPECKS = specks(7, ["#6b4a33", "#5a3c29", "#7a5840", "#3a2618"])
CLAY_SPECKS = specks(11, ["#b9784f", "#8a4f31", "#c88a5f", "#7a4229"])

# ---------------------------------------------------------------- cue table (all global seconds)
c = {
    # s1 – hook
    "garlic_in": L("s1") - 0.05, "shallot_in": W("s1", "l'échalote"),
    "pills1": W("s1", "planter"), "title_autumn": W("s1", "l'automne"),
    # s2
    "check": W("s2", "marcher"), "title3": W("s2", "trois"), "warn": W("s2", "pièges"),
    # s3/s4 – clay
    "b1": L("s3") - 0.3, "clay_up": W("s3", "terre"), "title_clay": W("s3", "argileuse"),
    "rain": W("s4", "garde"), "water": W("s4", "l'eau"), "humid": W("s4", "l'humidité"),
    "rot1": W("s4", "pourrit"),
    # s5/s6 – depth
    "b2": L("s5") - 0.3, "deep": W("s5", "trop"), "title_deep": W("s5", "enfoncé"),
    "choke": W("s6", "étouffe"), "rot2": W("s6", "pourrit"),
    "fix_depth": W("s6", "Pointe"), "fix_check": W("s6", "recouverte"),
    # s7 – pests
    "b3": L("s7") - 0.3, "title_pests": W("s7", "nuisibles"), "mouse": W("s7", "campagnols"),
    "fly": W("s7", "exemple"), "nibble": W("s7", "grignoter"), "winter": W("s7", "l'hiver"),
    # s8 – solution
    "sol": L("s8") - 0.3, "title_sol": W("s8", "solution"), "pills2": W("s8", "début"),
    "spring": W("s8", "printemps"), "adapted": W("s8", "variétés"),
    # s9/s10 – varieties
    "ail": L("s9") - 0.25, "tagA1": W("s9", "Printanor"), "tagA2": W("s9", "Rose"),
    "ech": L("s10") - 0.25, "tagE1": W("s10", "Jermor"), "tagE2": W("s10", "Longor"),
    # s11 – outro
    "out": L("s11") - 0.25, "out_humid": W("s11", "d'humidité"), "out_title": W("s11", "beaux"),
    "end": LE("s11"),
}
cue_js = "const C = " + json.dumps({k: round(v, 3) for k, v in c.items()}) + ";"

# ---------------------------------------------------------------- sfx
sfx = [  # (file, time, volume)
    ("pop", c["garlic_in"], .30), ("pop", c["shallot_in"], .30), ("click-soft", c["pills1"], .45),
    ("pop", c["title_autumn"], .25), ("pop", c["check"], .30), ("pop", c["title3"], .25),
    ("whoosh-short", c["b1"], .35), ("whoosh-short", c["clay_up"], .25), ("pop", c["rain"], .22),
    ("pop", c["rot1"], .25),
    ("whoosh-short", c["b2"], .35), ("pop", c["choke"], .22), ("whoosh-short", c["fix_depth"], .22),
    ("pop", c["fix_check"], .3),
    ("whoosh-short", c["b3"], .35), ("whoosh-short", c["mouse"], .22), ("pop", c["nibble"], .2),
    ("whoosh-short", c["sol"], .35), ("click-soft", c["pills2"], .45), ("sparkle", c["spring"], .22),
    ("whoosh-short", c["ail"], .3), ("pop", c["tagA1"], .28), ("pop", c["tagA2"], .28),
    ("whoosh-short", c["ech"], .3), ("pop", c["tagE1"], .28), ("pop", c["tagE2"], .28),
    ("whoosh-short", c["out"], .3), ("pop", c["out_title"], .25), ("pop", c["out_title"] + .12, .25),
    ("pop", c["out_title"] + .24, .25), ("chime", c["out_title"] + .3, .2),
]
durs = {"pop": .72, "whoosh-short": .57, "click-soft": .37, "sparkle": 1.8, "chime": 2.54}
sfx_html = "\n".join(
    f'      <audio id="sfx{i}" src="assets/audio/{f}.mp3" data-start="{t:.3f}" data-duration="{min(durs[f], DURATION - t):.2f}" '
    f'data-track-index="{3 + i % 4}" data-volume="{v}"></audio>'
    for i, (f, t, v) in enumerate(sfx))

make_music(f"{P}/assets/audio/music.wav", DURATION)

html = open(f"{P}/build/template.html").read()
html = (html.replace("%DURATION%", str(DURATION))
        .replace("%SOIL_SPECKS%", SOIL_SPECKS).replace("%CLAY_SPECKS%", CLAY_SPECKS)
        .replace("%CAPTIONS%", "\n      ".join(cap_html))
        .replace("%CAPTION_JS%", "\n      ".join(cap_js))
        .replace("%CUES%", cue_js).replace("%SFX%", sfx_html))
open(f"{P}/index.html", "w").write(html)
print("duration", DURATION, "captions", len(groups))
for k in ("s1", "s3", "s5", "s7", "s8", "s9", "s10", "s11"):
    print(k, starts[k])
