import sys, wave, json, glob
import numpy as np
sys.path.insert(0, '.')
from tts_checks import audio_checks, text_checks
from tts_textnorm import UrduNormalizer
R = '/home/vector/tts-reference-voices/voices'
def load(p):
    with wave.open(p) as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        a = np.frombuffer(w.readframes(n), dtype={2: np.int16, 4: np.int32}[sw])
        return (a.reshape(-1, ch) if ch > 1 else a), sr
print('real human clips (calibration of pauses):')
for p in sorted(glob.glob(f'{R}/*/*.wav')) + sorted(glob.glob(f'{R}/*/references/qwen3-tts.wav')):
    a, sr = load(p)
    print(' ', p.split('voices/')[1], audio_checks(a, sr))
# synthetic: real clip + 4 s gap + trailing 6 s silence
a, sr = load(f'{R}/shehbaz/shehbaz_02.wav')
pad = np.concatenate([a, np.zeros(sr*4, a.dtype), a, np.zeros(sr*6, a.dtype)])
print('synthetic gap+trail:', audio_checks(pad, sr))
un = UrduNormalizer()
ref = un('میں آج ایک نہایت سنجیدہ صورتحال کے بارے میں آپ سے مخاطب ہوں اور یہ بہت اہم ہے۔')
loop = un('میں آج ایک ایک ایک ایک ایک ایک نہایت سنجیدہ صورتحال کے بارے میں آپ سے مخاطب ہوں آآآآآ')
skip = un('میں آج ایک نہایت سنجیدہ اور یہ بہت اہم ہے')
for name, h in [('good', ref), ('loop', loop), ('skip', skip)]:
    print(name, text_checks(ref, h))
