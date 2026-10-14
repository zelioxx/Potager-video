"""Discreet background bed, synthesised so it is ours to use.

The reference shorts carry a very quiet sustained bed under the voice (a held note around
370 Hz, i.e. F#4: the third of D major) plus chimes on reveals. This writes a soft D-major
pad (D - Bm - G - A, 96 BPM) with a light plucked arpeggio, fades at both ends.
"""
import numpy as np
import soundfile as sf
from scipy.signal import lfilter

SR = 44100
BPM = 96
BEAT = 60 / BPM
CHORDS = [  # MIDI notes
    (50, 54, 57, 62, 66),  # D
    (47, 54, 59, 62, 66),  # Bm
    (43, 55, 59, 62, 67),  # G
    (45, 52, 57, 61, 64),  # A
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pad_voice(f, n, rng):
    t = np.arange(n) / SR
    detune = [1.0, 1.0035, 0.9968]
    out = np.zeros(n)
    for d in detune:
        ph = rng.uniform(0, 2 * np.pi)
        for k, amp in ((1, 1.0), (2, 0.32), (3, 0.12), (4, 0.05)):
            out += amp * np.sin(2 * np.pi * f * d * k * t + ph * k)
    return out / len(detune)


def envelope(n, attack, release):
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    e[:a] = np.linspace(0, 1, a) ** 2
    e[-r:] *= np.linspace(1, 0, r) ** 2
    return e


def make_music(path, duration):
    rng = np.random.default_rng(7)
    total = int((duration + 0.5) * SR)
    pad = np.zeros(total)
    pluck = np.zeros(total)
    bar = 4 * BEAT
    i = 0
    while i * bar < duration + bar:
        notes = CHORDS[i % len(CHORDS)]
        start = int(i * bar * SR)
        if start >= total:
            break
        n = int((bar + 1.2) * SR)  # overlap into the next chord
        seg = sum(pad_voice(hz(m), n, rng) * (0.9 if m < 52 else 0.55) for m in notes)
        seg *= envelope(n, 0.7, 1.4)
        end = min(total, start + n)
        pad[start:end] += seg[: end - start]
        # plucked arpeggio, eighth notes, two octaves up, every other bar half density
        arp = [notes[1] + 12, notes[2] + 12, notes[3] + 12, notes[4] + 12, notes[3] + 12, notes[2] + 12, notes[4] + 12, notes[3] + 12]
        for j, m in enumerate(arp):
            if i % 2 and j % 2:
                continue
            s0 = start + int(j * BEAT / 2 * SR)
            ln = int(0.9 * SR)
            if s0 >= total:
                break
            t = np.arange(ln) / SR
            f = hz(m)
            tone = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 5.5)
            tone[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
            e = min(total, s0 + ln)
            pluck[s0:e] += tone[: e - s0]
        i += 1
    # gentle low-pass on the pad (one-pole) to keep it warm and out of the voice's way
    a = np.exp(-2 * np.pi * 1800 / SR)
    lp = lfilter([1 - a], [1, -a], pad)
    mix = lp / np.max(np.abs(lp)) * 0.55 + pluck / np.max(np.abs(pluck)) * 0.22
    fade_in, fade_out = int(0.8 * SR), int(2.0 * SR)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)
    end = int(duration * SR)
    mix[end - fade_out:end] *= np.linspace(1, 0, fade_out)
    mix[end:] = 0
    mix = mix[:end]
    mix = mix / np.max(np.abs(mix)) * 0.8
    sf.write(path, np.stack([mix, mix], axis=1).astype(np.float32), SR)


if __name__ == "__main__":
    import sys
    make_music(sys.argv[1], float(sys.argv[2]))
