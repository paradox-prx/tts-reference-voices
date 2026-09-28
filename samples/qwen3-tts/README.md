# Qwen3-TTS voice-clone samples (AI-generated)

> **Every file in this folder is AI-generated speech.** It imitates the voices of real people (`trump`: Donald Trump,
> `shehbaz`: Shehbaz Sharif) using Qwen/Qwen3-TTS-12Hz-1.7B-Base voice cloning. **None of it is a real recording, and
> the speakers never said these words:** the texts are the fictional, deliberately apolitical benchmark prompts of this
> repository. Each FLAC carries the label in its metadata (Vorbis `COMMENT` and `TITLE`). Do not present, cut or
> redistribute these clips as anything other than labelled AI-generated benchmark samples.

These are ten of the best takes from the benchmark in [`server/REPORT.md`](../../server/REPORT.md), one per voice and
text length, generated with the recommended production configuration: vLLM-Omni 0.28.0 on one RTX 3090, bf16, sampling
0.9 / 50 / repetition_penalty 1.05; Urdu with `non_streaming_mode=true` where noted, the ~60 s texts through the
gateway's 60-word sentence splitting. "Best" means clean on every automatic check (no skipped passage, loop, garble,
pace or speaker problem) with the highest speaker similarity and the lowest recognition error for their size. They show
the ceiling, not the average: see the report for failure rates (English 0-2% severe; Urdu 7.7% per take with
`non_streaming_mode`).

| file | voice | lang | length | SIM WavLM-Large / base-plus-sv | ASR error (stock Whisper large-v3) | pace ratio | benchmark run |
|---|---|---|---|---|---|---|---|
| [trump_short.flac](trump_short.flac) | trump | en | 3.7 s | 0.84 / 0.98 | WER 0.00 | 0.97 | `P3_stream` |
| [trump_medium.flac](trump_medium.flac) | trump | en | 7.9 s | 0.88 / 0.99 | WER 0.00 | 1.02 | `P2_matrix` |
| [trump_long.flac](trump_long.flac) | trump | en | 18.1 s | 0.91 / 0.99 | WER 0.00 | 1.00 | `P2_matrix` |
| [trump_30s.flac](trump_30s.flac) | trump | en | 30.0 s | 0.90 / 0.99 | WER 0.00 | 0.99 | `P5_urdu_rp105` |
| [trump_60s.flac](trump_60s.flac) | trump | en | 66.4 s | 0.88 / 0.99 | WER 0.00 | 1.00 | `X7_split_60` |
| [shehbaz_short.flac](shehbaz_short.flac) | shehbaz | ur | 5.1 s | 0.82 / 0.98 | CER-nospace 0.05 | 1.07 | `P3_stream` |
| [shehbaz_medium.flac](shehbaz_medium.flac) | shehbaz | ur | 8.2 s | 0.82 / 0.98 | CER-nospace 0.07 | 0.98 | `P2_matrix` |
| [shehbaz_long.flac](shehbaz_long.flac) | shehbaz | ur | 25.0 s | 0.83 / 0.98 | CER-nospace 0.10 | 1.07 | `P2_matrix` |
| [shehbaz_30s.flac](shehbaz_30s.flac) | shehbaz | ur | 36.2 s | 0.86 / 0.98 | CER-nospace 0.11 | 0.99 | `P5_urdu_nsm` |
| [shehbaz_60s.flac](shehbaz_60s.flac) | shehbaz | ur | 74.1 s | 0.87 / 0.99 | CER-nospace 0.11 | 1.03 | `X8_split_nsm` |

SIM is cosine similarity to the voice's reference clip (`voices/<id>/references/qwen3-tts.wav`); for scale, real
same-speaker recordings score 0.90-0.94 (Large) and different speakers 0.10-0.18. Urdu error is mostly accent: the same
Whisper scores this speaker's real recordings at CER-nospace 0.04. Pace ratio = seconds per letter / the voice's
calibrated pace (1.0 = typical). Per-sample numbers and source paths: [`samples.json`](samples.json).

## Texts

- **trump_short.flac**: You know, I look out at this room and I see the most beautiful people.
- **trump_medium.flac**: It closed a long time ago. They built a bank there, a boring bank. And I've eaten in the finest restaurants in the world since then, the finest.
- **trump_long.flac**: Okay. They gave me this paper, and they said I have to read it, so I'm going to read it. The terms and conditions of the golf club membership. Section one. Members must wear collared shirts at all times. Section two. Members must replace all divots on the fairway. Section three. Carts must remain on the cart path near the greens.
- **trump_30s.flac**: Let me explain how a deal works, because a lot of people don't understand it. First, you never want to look like you need the deal. Never. Second, you aim very high, and then you keep pushing. Third, you always have a way out. Always. And fourth, and this is the most important one, you have to know the other side better than they know themselves. That's it. That's the whole thing. It's very simple, but very few people can do it. Very few. Most people give up too soon. They get tired. You can't get tired. You have to be patient, very patient, and then you strike.
- **trump_60s.flac**: So they hand me this new phone, and they say, sir, it's very easy, all your pictures are in the cloud. The cloud? What cloud? I looked up, there's no cloud. It was a beautiful day. And they say, no, sir, it's not that kind of cloud, it's a digital cloud. A digital cloud. Okay. So where is it? Nobody knows! It's somewhere. It's floating around. And I said, well, if it's floating, can it rain on my pictures? And they looked at me, and they didn't know. Nobody knows how it works. I don't think they know. And then they told me the cloud is actually in a big building somewhere in the desert. So it's not even a cloud! Sometimes, late at night, I sit out on the terrace and I look at the ocean, and I think about things. Big things. What does it all mean? What's the secret to a great deal? And you know what I've come to realize? It's not the money. Everybody thinks it's the money. It's the timing. It's knowing when to walk away, and knowing when to stay at the table. Maybe life is like that too. Maybe life is one very long negotiation. I don't know. I think about it a lot. More than people would think. Maybe the ocean knows. It's been around a long time, longer than me, believe it or not. It doesn't negotiate. It just keeps coming back, every single day.
- **shehbaz_short.flac**: جو آدمی ہر کام وقت پر کرنے کا عادی ہو، وہ ایسے میں کیا کرے؟
- **shehbaz_medium.flac**: آپ سب نے مجھے واقعی حیران کر دیا۔ میں بہت شکر گزار ہوں۔ مگر ایک شرط ہے، کیک کھانے کے بعد سب واپس کام پر!
- **shehbaz_long.flac**: آپ کو ایک بات بتاؤں؟ پچھلے سال میں ایک دور دراز علاقے میں جا رہا تھا، ایک چھوٹے سے جہاز میں۔ اچانک موسم خراب ہو گیا۔ کالے بادل، تیز ہوا، اور جہاز اوپر نیچے ہونے لگا۔ کھڑکی سے باہر کچھ نظر نہیں آ رہا تھا۔ میرے ساتھ بیٹھے افسر کا رنگ پیلا پڑ گیا۔ سچ پوچھیں تو میرا دل بھی بیٹھ گیا تھا۔
- **shehbaz_30s.flac**: کل شام مجھے ایک تقریب میں پہنچنا تھا۔ لوگ دو گھنٹے سے انتظار کر رہے تھے۔ اور ہم ایک ٹریفک جام میں پھنس گئے۔ آگے گاڑیاں، پیچھے گاڑیاں، دائیں بائیں گاڑیاں۔ ایک انچ بھی آگے نہیں بڑھ سکتے تھے۔ میں نے فون کیا، پیغام بھیجا، مگر کچھ نہیں ہو سکتا تھا۔ میں بس کھڑکی سے باہر دیکھتا رہا۔ مجھے بہت بے بسی محسوس ہوئی۔ جو آدمی ہر کام وقت پر کرنے کا عادی ہو، وہ ایسے میں کیا کرے؟ اس دن میں نے سوچا، روز کتنے لوگ اسی طرح پھنستے ہوں گے۔ اس کا حل نکالنا ہو گا۔
- **shehbaz_60s.flac**: میں پچھلے ہفتے شمالی علاقوں میں گیا۔ صبح سویرے جب سورج کی پہلی کرن برف پوش پہاڑوں پر پڑی، تو میں خاموش کھڑا دیکھتا رہا۔ سبحان اللہ۔ اتنے بلند پہاڑ، اتنی صاف ندیاں، اتنی گہری وادیاں۔ ایسا لگتا تھا جیسے قدرت نے اپنا سارا حسن ایک جگہ جمع کر دیا ہو۔ میرے ساتھ جو لوگ تھے، وہ بھی کچھ نہیں بول رہے تھے۔ کوئی بول بھی کیسے سکتا تھا؟ میں نے سوچا، اللہ نے ہمیں کتنی بڑی نعمت دی ہے۔ یہ پاکستان ہے۔ یہ ہمارا وطن ہے۔ ہمیں اس کی قدر کرنی ہے، اس کی حفاظت کرنی ہے۔ آپ کو معلوم ہے اس سکول کی کہانی کیا ہے؟ پچیس سال پہلے اس کی بنیاد رکھی گئی تھی۔ پچیس سال! تختی لگی، تصویریں کھنچیں، تقریریں ہوئیں، اور پھر سب بھول گئے۔ بچے درختوں کے نیچے بیٹھ کر پڑھتے رہے۔ سردی میں، گرمی میں، بارش میں۔ کسی نے پلٹ کر نہیں پوچھا کہ ان بچوں کا کیا بنا۔ یہ دیواریں آدھی کھڑی رہیں، اور خواب ادھورے رہ گئے۔ مجھے یہ سب دیکھ کر بہت دکھ ہوتا ہے۔ وعدے کرنا آسان ہے، نبھانا مشکل۔ مگر یہ قوم اب مزید انتظار نہیں کرے گی۔
