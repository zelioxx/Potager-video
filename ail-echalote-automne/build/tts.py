# Generates one wav per script line, clause by clause, and records clause timings.
#   python3 -I build/tts.py <project> <voice_dir>
# <voice_dir> is a sherpa-onnx Piper voice (vits-piper-fr_FR-tom-medium from the k2-fsa/sherpa-onnx
# "tts-models" GitHub release). length_scale < 1 speeds the read up for a punchy delivery.
import glob, json, re, sys
import numpy as np, soundfile as sf, sherpa_onnx, parselmouth
from parselmouth.praat import call

P, VD = sys.argv[1], sys.argv[2]
LENGTH_SCALE, NOISE, NOISE_W = 0.84, 0.72, 0.9

model = glob.glob(f"{VD}/*.onnx")[0]
tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
    vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=model, tokens=f"{VD}/tokens.txt", data_dir=f"{VD}/espeak-ng-data",
                                               noise_scale=NOISE, noise_scale_w=NOISE_W, length_scale=LENGTH_SCALE),
    num_threads=4)))


# Intonation reshaping (Praat PSOLA). The reference narrator is a lively male voice: median ~138 Hz
# with pitch swinging over almost an octave; Piper's raw read is narrower (~142 Hz, p10-p90 115-172 Hz).
BASE_HZ, RAW_HZ, EXPAND = 136.0, 142.0, 1.5
ST = np.log(2) / 12


def liven(x, sr, clause):
    snd = parselmouth.Sound(x.astype(np.float64), sampling_frequency=sr)
    manip = call(snd, "To Manipulation", 0.01, 75, 350)
    pt = call(manip, "Extract pitch tier")
    n = call(pt, "Get number of points")
    if n < 3:
        return x
    dur = snd.get_total_duration()
    end = clause.strip()[-1]
    new = call("Create PitchTier", "lively", 0, dur)
    for i in range(1, n + 1):
        t = call(pt, "Get time from index", i)
        f = call(pt, "Get value at index", i)
        r = t / dur
        if end == "?":            # questions climb at the end
            c = -1.0 + 5.0 * max(0.0, r - 0.55) / 0.45
        elif end in ",:":          # French continuation rise on non-final clauses
            c = 2.5 - 1.0 * r + 3.0 * max(0.0, r - 0.7) / 0.3
        elif end == "!":           # exclamations: high start, strong fall
            c = 5.0 - 4.5 * r
        else:                      # statements: declination
            c = 4.0 - 3.5 * r
        g = np.exp(np.log(BASE_HZ) + EXPAND * (np.log(f) - np.log(RAW_HZ)) + c * ST)
        call(new, "Add point", t, float(np.clip(g, 95, 265)))
    call([new, manip], "Replace pitch tier")
    out = call(manip, "Get resynthesis (overlap-add)")
    return np.array(out.values[0], dtype=np.float32)


def trim(x, sr, thr=0.012):
    """Cut leading/trailing silence so clause timings match the audible speech."""
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx):
        return x
    a, b = max(0, idx[0] - int(0.02 * sr)), min(len(x), idx[-1] + int(0.04 * sr))
    return x[a:b]


lines = json.load(open(f"{P}/build/script.json"))
out = []
for ln in lines:
    clauses = [c.strip() for c in re.findall(r"[^,:;…?!.]+[,:;…?!.]*", ln["text"]) if c.strip()]
    pieces, info, t = [], [], 0.0
    for c in clauses:
        g = tts.generate(c.replace("…", ","), sid=0, speed=1.0)
        sr = g.sample_rate
        a = trim(liven(np.array(g.samples, dtype=np.float32), sr, c), sr)
        dur = len(a) / sr
        info.append({"text": c, "start": round(t, 3), "end": round(t + dur, 3)})
        pieces.append(a)
        gap = 0.26 if c[-1] in ".?!…" else (0.14 if c[-1] in ":," else 0.04)
        pieces.append(np.zeros(int(gap * sr), dtype=np.float32))
        t += dur + gap
    audio = np.concatenate(pieces[:-1])
    sf.write(f"{P}/assets/audio/{ln['id']}.wav", audio, sr)
    out.append({"id": ln["id"], "text": ln["text"], "duration": round(len(audio) / sr, 3), "sample_rate": sr, "clauses": info})
    print(ln["id"], round(len(audio) / sr, 2), "s")
json.dump(out, open(f"{P}/build/voice.json", "w"), ensure_ascii=False, indent=1)
print("total", round(sum(o["duration"] for o in out), 2))
