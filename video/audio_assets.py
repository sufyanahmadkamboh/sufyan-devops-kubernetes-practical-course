"""Original music and sound effects for the video, generated from code (no samples, no third-party audio).

Everything here is synthesised with numpy/scipy: a calm 84 BPM background bed (pads, bass, a plucked arpeggio and
soft drums, arranged in 8-bar sections) and a small set of interface sound effects. Because nothing is sampled or
downloaded, there is no licensing question: the audio is part of this repository (see video/ASSETS-AND-LICENSES.md).

    python video/audio_assets.py preview      writes a 60-second music preview and every sound effect to video/out/preview/

build.py calls render_mix() during the "post" stage: music + sound effects + the cleaned voice, with the music ducked
under the voice.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, oaconvolve, resample_poly, sosfilt

SR = 48000
BPM = 84
BEAT = 60 / BPM
BAR = 4 * BEAT

# close voicings (MIDI note numbers) so the chords move smoothly; bass roots one or two octaves lower
CHORDS = {
    "Am": ((57, 60, 64), 45), "F": ((53, 57, 60), 41), "C": ((55, 60, 64), 48), "G": ((55, 59, 62), 43),
    "Em": ((55, 59, 64), 40), "Dm": ((53, 57, 62), 38),
}
PROGRESSIONS = [["Am", "F", "C", "G"], ["F", "G", "Em", "Am"], ["Dm", "Am", "F", "G"], ["Am", "Em", "F", "G"]]


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def t_axis(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * SR)) / SR


def lowpass(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, cutoff, "lowpass", fs=SR, output="sos"), x, axis=0)


def highpass(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, cutoff, "highpass", fs=SR, output="sos"), x, axis=0)


def bandpass(x: np.ndarray, lo: float, hi: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x, axis=0)


def stereo(x: np.ndarray, pan: float = 0.0) -> np.ndarray:
    """Mono to stereo with an equal-power pan (-1 left .. +1 right)."""
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


class Reverb:
    """A small synthetic room: decorrelated, darkened, exponentially decaying noise as the impulse response."""

    def __init__(self, seconds: float = 1.6, decay: float = 0.42, seed: int = 7):
        rng = np.random.default_rng(seed)
        t = t_axis(seconds)
        ir = rng.standard_normal((len(t), 2)) * np.exp(-t / decay)[:, None]
        ir[: int(0.012 * SR)] = 0                                   # 12 ms pre-delay
        ir = lowpass(ir, 5200)
        self.ir = (ir / np.sqrt((ir ** 2).sum(axis=0))).astype(np.float32)

    def __call__(self, x: np.ndarray, wet: float) -> np.ndarray:
        x2 = x if x.ndim == 2 else stereo(x)
        pad = np.zeros((len(self.ir), 2), dtype=np.float32)
        dry = np.vstack([x2, pad])
        tail = np.zeros_like(dry)
        for c in range(2):
            wet_c = oaconvolve(x2[:, c], self.ir[:, c])[: len(dry)]
            tail[: len(wet_c), c] = wet_c
        return (1 - wet) * dry + wet * tail


ROOM = Reverb()


# ----------------------------------------------------------------------------------------------- instruments
def pad_chord(notes: tuple[int, ...], seconds: float) -> np.ndarray:
    """Warm pad: three slightly detuned, softened saw voices per note, panned apart, slow attack and release."""
    t = t_axis(seconds + 1.4)
    out = np.zeros((len(t), 2))
    for n in notes:
        for cents, pan in ((-7, -0.55), (0, 0.0), (7, 0.55)):
            f = hz(n) * 2 ** (cents / 1200)
            wave_ = sum(np.sin(2 * np.pi * f * k * t + k) / k * np.exp(-k / 3.5) for k in range(1, 9))
            out += stereo(wave_, pan)
    env = np.minimum(1, t / 0.6) * np.clip((seconds + 1.4 - t) / 1.4, 0, 1)
    out = lowpass(out * env[:, None], 2700)
    return ROOM(out / np.abs(out).max(), wet=0.3)


def bass_note(root: int, seconds: float) -> np.ndarray:
    t = t_axis(seconds)
    f = hz(root)
    x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    env = np.minimum(1, t / 0.03) * np.exp(-t / 2.2) * np.clip((seconds - t) / 0.15, 0, 1)
    return stereo(lowpass(x * env, 400))


def pluck(midi: int) -> np.ndarray:
    t = t_axis(1.1)
    f = hz(midi)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    env = np.minimum(1, t / 0.004) * np.exp(-t / 0.26)
    return lowpass(x * env, 3800)


def kick() -> np.ndarray:
    t = t_axis(0.45)
    f = 45 + 70 * np.exp(-t / 0.035)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    return x


def hat(rng) -> np.ndarray:
    t = t_axis(0.08)
    return highpass(rng.standard_normal(len(t)), 7000) * np.exp(-t / 0.018)


def snare(rng) -> np.ndarray:
    t = t_axis(0.3)
    body = 0.5 * np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05)
    noise = bandpass(rng.standard_normal(len(t)), 1200, 5000) * np.exp(-t / 0.085)
    return lowpass(body + noise, 6000)


def place(buf: np.ndarray, sig: np.ndarray, start: float, gain: float, pan: float = 0.0) -> None:
    s = int(start * SR)
    if s >= len(buf):
        return
    x = sig if sig.ndim == 2 else stereo(sig, pan)
    n = min(len(x), len(buf) - s)
    buf[s:s + n] += gain * x[:n].astype(np.float32)


# ----------------------------------------------------------------------------------------------- music
def music(total: float, seed: int = 1) -> np.ndarray:
    """A calm bed as long as the video: 8-bar sections, varied progressions and layers, a gentle fade at the end."""
    rng = np.random.default_rng(seed)
    buf = np.zeros((int((total + 3) * SR), 2), dtype=np.float32)
    # pads one octave up and the arpeggio two: both sit above the voice's fundamental, the bass carries the low end
    pads = {name: pad_chord(tuple(n + 12 for n in notes), BAR) for name, (notes, _) in CHORDS.items()}
    basses = {name: bass_note(root, BAR / 2) for name, (_, root) in CHORDS.items()}
    plucks = {}
    k, hats, snares = kick(), [hat(rng) for _ in range(4)], [snare(rng) for _ in range(3)]
    bar, section = 0, 0
    while bar * BAR < total + 2:
        prog = PROGRESSIONS[(section * 3 + seed) % len(PROGRESSIONS)]
        layers = [{"arp"}, {"arp", "drums"}, {"arp", "drums"}, {"drums"}][section % 4] if section else set()
        pattern = rng.permutation([0, 1, 2, 1, 2, 0, 1, 2])
        for b in range(8):
            t0 = bar * BAR
            name = prog[b % 4]
            notes, root = CHORDS[name]
            place(buf, pads[name], t0, 0.22)
            place(buf, basses[name], t0, 0.17)
            place(buf, basses[name], t0 + 2 * BEAT, 0.12)
            if "arp" in layers:
                for e in range(8):
                    if rng.random() < 0.18:
                        continue                                       # leave some air
                    m = notes[pattern[e]] + 24
                    plucks.setdefault(m, ROOM(pluck(m), wet=0.35))
                    place(buf, plucks[m], t0 + e * BEAT / 2, 0.15 * (0.8 + 0.4 * rng.random()), 0)
            if "drums" in layers:
                for beat in range(4):
                    if beat in (0, 2):
                        place(buf, k, t0 + beat * BEAT, 0.26)
                    if beat in (1, 3):
                        place(buf, snares[rng.integers(3)], t0 + beat * BEAT, 0.10, 0.1)
                    place(buf, hats[rng.integers(4)], t0 + (beat + 0.5) * BEAT, 0.045, 0.35)
            bar += 1
        section += 1
    buf = buf[: int((total + 0.5) * SR)]
    buf = highpass(buf, 70, order=4).astype(np.float32)               # no rumble under the narration
    # leave room for the voice: a gentle dip where speech is most intelligible (about 1-3 kHz)
    buf = (buf - 0.3 * bandpass(buf, 1000, 3200)).astype(np.float32)
    fade = int(3.0 * SR)
    buf[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
    buf[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))[:, None]
    rms = np.sqrt(np.mean(buf ** 2)) + 1e-9
    return buf * (10 ** (-29 / 20) / rms)                              # bed at about -29 dBFS RMS before ducking


# ----------------------------------------------------------------------------------------------- sound effects
def whoosh(seconds: float, lo: float, hi: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = t_axis(seconds)
    noise = rng.standard_normal(len(t))
    out = np.zeros(len(t))
    blocks = 24
    size = len(t) // blocks
    win = np.hanning(size * 2)
    for b in range(blocks - 1):
        f = lo * (hi / lo) ** (b / blocks)
        seg = bandpass(noise[b * size: b * size + 2 * size], f * 0.7, min(f * 1.4, SR / 2 - 100))
        out[b * size: b * size + len(seg)] += seg * win[: len(seg)]
    env = np.sin(np.pi * np.clip(t / seconds, 0, 1)) ** 1.5
    x = out * env
    x = stereo(x / np.abs(x).max(), 0)
    x[:, 0] *= np.linspace(1.0, 0.6, len(t))                          # a slight left-to-right movement
    x[:, 1] *= np.linspace(0.6, 1.0, len(t))
    return x


def bell(freq: float, seconds: float, decay: float) -> np.ndarray:
    t = t_axis(seconds)
    partials = ((1, 1.0, 1.0), (2.76, 0.45, 0.6), (5.40, 0.22, 0.35), (8.93, 0.10, 0.2))
    x = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t / (decay * d)) for r, a, d in partials)
    return x * np.minimum(1, t / 0.003)


def sfx(kind: str, seed: int = 3) -> np.ndarray:
    if kind == "scene":
        return whoosh(0.5, 500, 3500, seed) * 0.5
    if kind == "chapter":
        return whoosh(0.8, 300, 4500, seed + 1) * 0.75
    if kind == "success":                                              # two rising bell notes
        x = np.zeros(int(1.6 * SR))
        for i, f in enumerate((1318.5, 1760.0)):
            b = bell(f, 1.4, 0.45)
            s = int(i * 0.09 * SR)
            x[s:s + len(b)] += b[: len(x) - s]
        return ROOM(x / np.abs(x).max() * 0.55, wet=0.3)
    if kind == "error":                                                # two soft falling tones
        t = t_axis(0.2)
        x = np.zeros(int(0.5 * SR))
        for i, f in enumerate((392.0, 311.1)):
            tone = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 3, 5)) * np.exp(-t / 0.07) * np.minimum(1, t / 0.004)
            s = int(i * 0.14 * SR)
            x[s:s + len(tone)] += tone
        return ROOM(lowpass(x / np.abs(x).max() * 0.6, 2800), wet=0.15)
    if kind == "pop":
        t = t_axis(0.09)
        f = 700 + 600 * np.exp(-t / 0.02)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.025)
        return ROOM(x * 0.5, wet=0.2)
    if kind == "intro":                                                # soft impact + shimmering A major arpeggio
        t = t_axis(2.8)
        boom = np.sin(2 * np.pi * np.cumsum(50 + 60 * np.exp(-t / 0.06)) / SR) * np.exp(-t / 0.7)
        x = 0.9 * boom
        for i, f in enumerate((880.0, 1108.7, 1318.5, 1760.0)):
            b = bell(f, 2.4, 0.7) * 0.25
            s = int((0.05 + i * 0.07) * SR)
            x[s:s + len(b)] += b[: len(x) - s]
        return ROOM(lowpass(x / np.abs(x).max() * 0.8, 9000), wet=0.4)
    if kind == "outro":                                                # a gentle closing chord
        x = np.zeros(int(3.6 * SR))
        for i, f in enumerate((440.0, 554.4, 659.3, 880.0)):
            b = bell(f, 3.2, 1.0) * 0.3
            s = int(i * 0.12 * SR)
            x[s:s + len(b)] += b[: len(x) - s]
        return ROOM(x / np.abs(x).max() * 0.7, wet=0.45)
    raise ValueError(kind)


SFX_GAIN = {"scene": 0.07, "chapter": 0.11, "success": 0.16, "error": 0.15, "pop": 0.10, "intro": 0.30, "outro": 0.22}


# ----------------------------------------------------------------------------------------------- mixing
def duck_gain(voice: np.ndarray, depth_db: float = 8.0) -> np.ndarray:
    """Music gain per sample: down by depth_db while the voice speaks (fast attack, slow release)."""
    hop = int(0.02 * SR)
    frames = len(voice) // hop + 1
    v = np.pad(voice, (0, frames * hop - len(voice)))
    rms = np.sqrt(np.mean(v.reshape(frames, hop) ** 2, axis=1))
    active = 20 * np.log10(rms + 1e-9) > -42
    # hold: short pauses between sentences keep the music down; only real pauses (scene changes, cards) let it rise
    hold = int(0.9 / 0.02)
    recent = np.convolve(active.astype(float), np.ones(hold), mode="full")[:frames] > 0
    target = np.where(recent, 10 ** (-depth_db / 20), 1.0)
    g, out = 1.0, np.empty(frames)
    for i, tg in enumerate(target):
        coef = 0.30 if tg < g else 0.025                               # ~70 ms down, ~0.8 s back up
        g += (tg - g) * coef
        out[i] = g
    return np.interp(np.arange(len(voice)), np.arange(frames) * hop, out).astype(np.float32)


def render_mix(voice_path: Path, out_path: Path, total: float, events: list[tuple[float, str]], seed: int = 1) -> None:
    rate, voice = wavfile.read(voice_path)
    voice = voice.astype(np.float32) / (32768.0 if voice.dtype == np.int16 else 1.0)
    if voice.ndim == 2:
        voice = voice.mean(axis=1)
    if rate != SR:
        voice = resample_poly(voice, SR, rate).astype(np.float32)
    n = max(len(voice), int(total * SR))
    voice = np.pad(voice, (0, n - len(voice)))
    bed = music(n / SR, seed)[:n]
    bed = np.pad(bed, ((0, n - len(bed)), (0, 0)))
    bed *= duck_gain(voice)[:, None]
    fx = np.zeros((n, 2), dtype=np.float32)
    cache: dict[str, np.ndarray] = {}
    for when, kind in events:
        cache.setdefault(kind, sfx(kind))
        lead = 0.25 if kind in ("scene", "chapter") else 0.0           # whooshes peak on the cut
        place(fx, cache[kind], max(0.0, when - lead), SFX_GAIN[kind])
    mix = stereo(voice) * 1.0 + bed + fx
    peak = np.abs(mix).max()
    if peak > 0.98:
        mix *= 0.98 / peak
    wavfile.write(out_path, SR, mix.astype(np.float32))


if __name__ == "__main__" and sys.argv[1:] == ["preview"]:
    out = Path(__file__).resolve().parent / "out" / "preview"
    out.mkdir(parents=True, exist_ok=True)
    wavfile.write(out / "music-60s.wav", SR, music(60, 1).astype(np.float32))
    for kind in SFX_GAIN:
        x = sfx(kind)
        wavfile.write(out / f"sfx-{kind}.wav", SR, (x if x.ndim == 2 else stereo(x)).astype(np.float32))
    print("preview written to", out)
