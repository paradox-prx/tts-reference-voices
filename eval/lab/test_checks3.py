import sys, wave, glob
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
for rel in (-40, -35, -30, -25):
    rows = []
    for p in sorted(glob.glob(f'{R}/*/*.wav')) + sorted(glob.glob(f'{R}/*/references/qwen3-tts.wav')):
        a, sr = load(p); c = audio_checks(a, sr, rel_db=rel)
        rows.append((p.split('/')[-1], c['speech_ratio'], c['max_internal_sil_s'], c['thr_db']))
    print(f'rel_db={rel}: ' + ' '.join(f'{n[:10]}:{sp}/{mx}s@{t}' for n, sp, mx, t in rows))
un = UrduNormalizer()
ref = un('میں آج ایک نہایت سنجیدہ صورتحال کے بارے میں آپ سے مخاطب ہوں اور یہ بہت اہم ہے۔')
for name, h in [('good', ref), ('loop', un('میں آج ایک ایک ایک ایک ایک ایک نہایت سنجیدہ صورتحال کے بارے میں آپ سے مخاطب ہوں آآآآآ')), ('skip', un('میں آج ایک نہایت سنجیدہ اور یہ بہت اہم ہے'))]:
    print(name, text_checks(ref, h))
