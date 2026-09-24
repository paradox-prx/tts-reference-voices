import json, sys
sys.path.insert(0, '.')
import jiwer
from whisper_normalizers import BasicTextNormalizer
from tts_textnorm import UrduNormalizer, nospace
R = '/home/vector/tts-reference-voices'
un, b0, b1 = UrduNormalizer(), BasicTextNormalizer(), BasicTextNormalizer(remove_diacritics=True)
ref = json.load(open(f'{R}/voices/shehbaz/references/references.json'))['qwen3-tts']['text']
seg = ref.replace('خود مختاری', 'خودمختاری').replace('لیڈرشپ', 'لیڈر شپ')
hyp = seg.replace('ی', 'ي').replace('ک', 'ك').replace('ُ', '').replace('ِ', '').replace('۔', '.')
print('ref words', len(un(ref).split()))
for label, h in [('orthographic variants only', ref.replace('ی', 'ي').replace('ک', 'ك').replace('ُ', '').replace('ِ', '').replace('۔', '.')),
                 ('+ 2 segmentation variants', hyp)]:
    for name, f in [('raw', lambda s: s), ('whisper basic', b0), ('whisper basic rd', b1), ('urdu', un)]:
        r_, h_ = f(ref), f(h)
        print(f'{label:28} {name:17} WER={jiwer.wer(r_, h_):.3f} CER={jiwer.cer(r_, h_):.3f} CER-nospace={jiwer.cer(nospace(r_), nospace(h_)):.3f}')
