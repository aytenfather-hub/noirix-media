import numpy as np, wave
SR = 48000; BPM = 120; DUR = 15.0; N = int(SR * DUR)
t = np.arange(N) / SR; beat = 60 / BPM
out = np.zeros((N, 2), np.float32)
rng = np.random.default_rng(3)

def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR); j = min(N, i + len(sig))
    if i >= N: return
    l = np.sqrt(0.5 * (1 - pan)); r = np.sqrt(0.5 * (1 + pan))
    out[i:j, 0] += sig[:j - i] * gain * l; out[i:j, 1] += sig[:j - i] * gain * r

def env(n, a, d):
    e = np.ones(n, np.float32); ai = int(a * SR); e[:ai] = np.linspace(0, 1, ai) if ai else 1
    e *= np.exp(-np.arange(n) / (d * SR)); return e

def kick():
    n = int(0.45 * SR); tt = np.arange(n) / SR
    f = 48 + 90 * np.exp(-tt * 28); ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * env(n, 0.002, 0.16)).astype(np.float32)
def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR); x = rng.normal(0, 1, n)
    x = np.diff(np.concatenate([[0], x]))  # crude highpass
    return (x * env(n, 0.001, 0.08 if open_ else 0.018) * 0.35).astype(np.float32)
def clap():
    n = int(0.3 * SR); x = rng.normal(0, 1, n); e = env(n, 0.001, 0.07)
    for k in (0.0, 0.012, 0.024): e[int(k * SR):] += 0.0
    return (np.convolve(x, np.ones(30) / 30, 'same') * e * 0.9).astype(np.float32)
def note(freq, dur, kind='pad'):
    n = int(dur * SR); tt = np.arange(n) / SR
    if kind == 'pad':
        s = sum(np.sin(2 * np.pi * freq * m * tt + m) / m ** 1.6 for m in (1, 2, 3, 4)) + 0.4 * np.sin(2 * np.pi * freq * 1.003 * tt)
        e = np.minimum(1, tt / 0.35) * np.minimum(1, (dur - tt) / 0.4)
        return (s * e * 0.12).astype(np.float32)
    if kind == 'bass':
        s = np.sin(2 * np.pi * freq * tt) + 0.25 * np.sin(4 * np.pi * freq * tt)
        return (s * env(n, 0.005, 0.35) * 0.45).astype(np.float32)
    if kind == 'pluck':
        s = np.sin(2 * np.pi * freq * tt) + 0.5 * np.sin(4 * np.pi * freq * tt) * np.exp(-tt * 8)
        return (s * env(n, 0.002, 0.22) * 0.18).astype(np.float32)
def whoosh(dur=0.5):
    n = int(dur * SR); x = rng.normal(0, 1, n); tt = np.arange(n) / SR
    k = int(SR * 0.004); x = np.convolve(x, np.ones(k) / k, 'same')
    e = np.sin(np.pi * tt / dur) ** 2
    return (x * e * 0.6).astype(np.float32)
def shimmer(dur=1.2):
    n = int(dur * SR); tt = np.arange(n) / SR; s = np.zeros(n)
    for f in (2093, 2637, 3136, 4186): s += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 3)
    return (s * np.minimum(1, tt / 0.02) * 0.05).astype(np.float32)

A, F, C, G = 220.0, 174.61, 261.63, 196.0  # Am - F - C - G
chords = [(A, [220, 261.63, 329.63, 392]), (F, [174.61, 220, 261.63, 329.63]), (C, [261.63, 329.63, 392, 493.88]), (G, [196, 246.94, 293.66, 392])]
bar = beat * 4
for b in range(int(DUR / bar) + 1):
    root, ch = chords[b % 4]
    for f in ch: add(note(f, bar + 0.3), b * bar, 1.0, pan=(f % 7 - 3) / 6)
    for q in range(4):
        add(note(root / 2, beat * 0.9, 'bass'), b * bar + q * beat, 0.9)
# drums from 2.0s (after hook)
for i in range(int(DUR / beat)):
    s = i * beat
    if s < 2.0 or s >= 13.5: continue
    add(kick(), s, 0.9)
    if i % 2 == 1: add(clap(), s, 0.35)
    add(hat(), s + beat / 2, 0.8, 0.3); add(hat(), s, 0.4, -0.3)
# pluck motif in hook and outro
motif = [659.25, 587.33, 523.25, 493.88]
for k, f in enumerate(motif): add(note(f, 0.6, 'pluck'), 0.0 + k * 0.5, 1.0, 0.2)
for k, f in enumerate(motif[::-1]): add(note(f, 0.6, 'pluck'), 12.5 + k * 0.5, 1.0, -0.2)
add(shimmer(), 0.05, 1.0); add(shimmer(), 9.5, 1.0)
for cut in (2.0, 4.5, 6.5, 8.0, 8.5, 9.0, 9.5, 12.5): add(whoosh(0.45), cut - 0.3, 0.35)
# fade out
fo = int(1.2 * SR); out[-fo:] *= np.linspace(1, 0, fo)[:, None]
out /= np.max(np.abs(out)) * 1.1
with wave.open('/tmp/claude-0/-home-claude/75e13283-8b24-558c-93ac-5d18fcf984b9/scratchpad/clutch_ad/music.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())
print('ok')
