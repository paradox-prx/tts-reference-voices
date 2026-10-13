import json
from tokenizers import Tokenizer, models, pre_tokenizers, normalizers, decoders, Regex
QWEN = r"""(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+"""
MISTRAL = r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+|[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*|\p{N}| ?[^\s\p{L}\p{N}]+[\r\n/]*|\s*[\r\n]+|\s+(?!\S)|\s+"
def mk(pat):
    t = Tokenizer(models.BPE.from_file("hf/vocab.json", "hf/merges.txt"))
    t.normalizer = normalizers.NFC()
    t.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Split(Regex(pat), behavior="isolated"), pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False)])
    t.decoder = decoders.ByteLevel()
    return t
q, m = mk(QWEN), mk(MISTRAL)
for lang, f in [("ur","bench/pools/ur.json"),("en","bench/pools/en.json"),("ur-auralis","bench/pools/auralis_ur.json")]:
    pool = json.load(open("/home/vector/tts-reference-voices/"+f))
    n=diff=0; tq=tm=0; ex=None
    for size in ["short","medium","long","xlong"]:
        for s in pool.get(size, []):
            a=q.encode(s).ids; b=m.encode(s).ids; n+=1; tq+=len(a); tm+=len(b)
            if a!=b:
                diff+=1
                if ex is None: ex=(s,[q.decode([i]) for i in a],[m.decode([i]) for i in b])
    print(f"{lang}: texts={n} differ={diff} ({100*diff/max(n,1):.1f}%) tokens qwen={tq} mistral={tm}")
    if ex:
        s,a,b=ex
        # show first differing window
        k=next(i for i,(x,y) in enumerate(zip(a,b)) if x!=y) if any(x!=y for x,y in zip(a,b)) else min(len(a),len(b))
        print("  example:", s[:120]); print("   qwen   :", a[max(0,k-3):k+6]); print("   mistral:", b[max(0,k-3):k+6])
for s in ["McDonald's DON'T iPhone", "وطنِ عزیز", "پُرعزم"]:
    print(repr(s), [q.decode([i]) for i in q.encode(s).ids], [m.decode([i]) for i in m.encode(s).ids])
for v in ["shehbaz","trump"]:
    r=json.load(open(f"/home/vector/tts-reference-voices/voices/{v}/references/references.json"))["qwen3-tts"]["text"]
    print(v, "ref text same tokens:", q.encode(r).ids==m.encode(r).ids, len(q.encode(r).ids), len(m.encode(r).ids))
