# Higgs TTS 3 voice-clone samples (AI-generated)

> **Every file in this folder is AI-generated speech.** It imitates the voices of real people (`trump`: Donald Trump,
> `shehbaz`: Shehbaz Sharif) with Boson AI's Higgs TTS 3 (`bosonai/higgs-tts-3-4b`) voice cloning. **None of it is a
> real recording, and the speakers never said these words:** the texts are the fictional benchmark prompts of this
> repository. Each WAV carries the label in its metadata (LIST/INFO comment). Do not present, cut or redistribute
> these clips as anything other than labelled AI-generated benchmark samples. This audio was created with Boson AI's
> Higgs Audio (https://www.boson.ai/higgs-audio), under its research and non-commercial licence.

Takes from the benchmark in [`higgs/REPORT.md`](../../higgs/REPORT.md) (vLLM-Omni 0.28.0 on one RTX 3090, bf16,
sampling temperature 0.8 / top_k 50), chosen by `higgs/bench/pick_samples.py` from the scored takes of
`higgs/results/B0_baseline_flash_attn`:

- **[best/](best/)**: clean on every automatic check, the highest speaker similarity and lowest recognition error
  for their length (sizes spread from one sentence to ~30 s).
- **[mid/](mid/)**: the takes closest to each voice's median quality: what a typical request sounds like.
- **[worst/](worst/)**: the most extreme failure of each kind the evaluation found (mostly text dropped from ~30 s
  and ~60 s inputs; see the report).

Texts that read as political statements or official announcements were left out. SIM = cosine speaker similarity
to the voice's reference clip (WavLM-Large / WavLM base-plus-sv; real same-speaker recordings score 0.90-0.94 /
>= 0.975, different speakers 0.10-0.18 / 0.75-0.80). Errors are from stock Whisper large-v3 (WER for English,
CER-nospace for Urdu). Pace = seconds per letter / the voice's calibrated pace (1.0 = typical). Every clip's text,
transcript, metrics and source take are in [`samples.json`](samples.json).


## best

| file | voice | length | SIM Large / base | error | pace | notes | text |
|---|---|---|---|---|---|---|---|
| [best/shehbaz_short_01.wav](best/shehbaz_short_01.wav) | shehbaz | 5.0 s | 0.79 / 0.964 | CER-ns 0.000 | 0.99 | clean | ٹھیکیدار کو بلائیں، انجینئر کو بلائیں، سب کو یہاں بلائیں! |
| [best/shehbaz_medium_02.wav](best/shehbaz_medium_02.wav) | shehbaz | 12.2 s | 0.90 / 0.973 | CER-ns 0.009 | 1.01 | clean | آج میں آپ کو ایک بیٹی سے ملوانا چاہتا ہوں۔ یہ ایک چھوٹے سے گاؤں کی رہنے والی ہے۔ اس کے والد کھیتوں میں مزدوری … |
| [best/shehbaz_long_03.wav](best/shehbaz_long_03.wav) | shehbaz | 23.5 s | 0.86 / 0.972 | CER-ns 0.000 | 1.00 | clean | آپ کو ایک بات بتاؤں؟ پچھلے سال میں ایک دور دراز علاقے میں جا رہا تھا، ایک چھوٹے سے جہاز میں۔ اچانک موسم خراب ہ… |
| [best/shehbaz_30s_04.wav](best/shehbaz_30s_04.wav) | shehbaz | 35.7 s | 0.88 / 0.964 | CER-ns 0.003 | 1.01 | clean | آپ کو ایک بات بتاؤں؟ پچھلے سال میں ایک دور دراز علاقے میں جا رہا تھا، ایک چھوٹے سے جہاز میں۔ اچانک موسم خراب ہ… |
| [best/shehbaz_short_05.wav](best/shehbaz_short_05.wav) | shehbaz | 5.8 s | 0.80 / 0.969 | CER-ns 0.019 | 1.00 | clean | اس نے فوراً کہا، تو پھر آپ دونوں ہاتھ اٹھایا کریں، کام تو بہت زیادہ ہے! |
| [best/shehbaz_medium_06.wav](best/shehbaz_medium_06.wav) | shehbaz | 12.4 s | 0.88 / 0.981 | CER-ns 0.017 | 0.97 | clean | پورا ہال ہنسنے لگا۔ میں نے کہا، بیٹا، یہ انگلی ہمیں یاد دلاتی ہے کہ کام ابھی باقی ہے! اس نے فوراً کہا، تو پھر … |
| [best/trump_short_01.wav](best/trump_short_01.wav) | trump | 6.6 s | 0.84 / 0.989 | WER 0.000 | 1.05 | clean | You've been with me from the very beginning, through the good times and the tough times, and I never forget th… |
| [best/trump_30s_02.wav](best/trump_30s_02.wav) | trump | 32.0 s | 0.86 / 0.989 | WER 0.000 | 1.00 | clean | So they hand me this new phone, and they say, sir, it's very easy, all your pictures are in the cloud. The clo… |
| [best/trump_short_03.wav](best/trump_short_03.wav) | trump | 6.1 s | 0.84 / 0.990 | WER 0.000 | 1.06 | clean | It's not the buildings, it's not the golf, it's not even the cheeseburgers, and I love a good cheeseburger. |
| [best/trump_30s_04.wav](best/trump_30s_04.wav) | trump | 31.7 s | 0.86 / 0.992 | WER 0.000 | 1.03 | clean | A man came up to me the other day, big strong guy, a builder, hands like this. And he had tears in his eyes. A… |
| [best/trump_short_05.wav](best/trump_short_05.wav) | trump | 5.3 s | 0.84 / 0.966 | WER 0.000 | 1.12 | clean | I have very beautiful hair, and I have to stand under this thing for fifteen minutes. |
| [best/trump_30s_06.wav](best/trump_30s_06.wav) | trump | 32.2 s | 0.85 / 0.980 | WER 0.000 | 1.06 | clean | I miss the old days, I really do. When I was starting out, there was this little diner on the corner, and they… |

## mid

| file | voice | length | SIM Large / base | error | pace | notes | text |
|---|---|---|---|---|---|---|---|
| [mid/shehbaz_short_01.wav](mid/shehbaz_short_01.wav) | shehbaz | 6.0 s | 0.79 / 0.960 | CER-ns 0.000 | 1.12 | clean | کبھی کبھی رات کو جب سب سو جاتے ہیں، میں اکیلا بیٹھ کر سوچتا ہوں۔ |
| [mid/shehbaz_medium_02.wav](mid/shehbaz_medium_02.wav) | shehbaz | 12.1 s | 0.83 / 0.970 | CER-ns 0.011 | 1.18 | clean | میں پچھلے ہفتے شمالی علاقوں میں گیا۔ صبح سویرے جب سورج کی پہلی کرن برف پوش پہاڑوں پر پڑی، تو میں خاموش کھڑا دی… |
| [mid/shehbaz_long_03.wav](mid/shehbaz_long_03.wav) | shehbaz | 25.5 s | 0.88 / 0.990 | CER-ns 0.027 | 1.24 | clean | شکریہ، بہت بہت شکریہ۔ سُڑ۔ معاف کیجیے گا۔ یہ اسلام آباد کا موسم بہار ہے، ہر طرف پولن ہی پولن۔ سُڑ۔ ڈاکٹر نے کہ… |
| [mid/trump_short_01.wav](mid/trump_short_01.wav) | trump | 2.6 s | 0.79 / 0.981 | WER 0.000 | 1.30 | clean | I said, that's a very unfair question. |
| [mid/trump_30s_02.wav](mid/trump_30s_02.wav) | trump | 29.8 s | 0.80 / 0.975 | WER 0.049 | 0.98 | del_run>=3 | Listen to me. Listen very carefully. Because I'm only going to say this once. This is the greatest deal. In th… |
| [mid/trump_short_03.wav](mid/trump_short_03.wav) | trump | 2.0 s | 0.69 / 0.889 | WER 0.000 | 1.12 | clean | The best scores you've ever seen. |

## worst

| file | voice | length | SIM Large / base | error | pace | notes | text |
|---|---|---|---|---|---|---|---|
| [worst/shehbaz_short_01.wav](worst/shehbaz_short_01.wav) | shehbaz | 63.3 s | 0.12 / 0.467 | CER-ns 0.586 | 19.66 | pace>1.5, cer_nospace>0.3, long_word>2, word_gap>1.5, unaligned_tail>2, sim<0.5, sim_heldout<0.5 | میرا دل ابھی تک زور زور سے دھڑک رہا ہے! |
| [worst/shehbaz_60s_02.wav](worst/shehbaz_60s_02.wav) | shehbaz | 25.4 s | 0.86 / 0.991 | CER-ns 0.836 | 0.37 | lead_sil>1, speech_ratio<0.6, pace<0.7, cer_nospace>0.3, char_ratio<0.88, del_run>=6 | آج مجھے ایک بات کا اعتراف کرنا ہے، اور یہ میرے لیے آسان نہیں۔ آپ سب جانتے ہیں کہ میں وقت کا کتنا پابند ہوں۔ جو… |
| [worst/shehbaz_short_03.wav](worst/shehbaz_short_03.wav) | shehbaz | 2.8 s | 0.49 / 0.955 | CER-ns 0.444 | 1.42 | cer_nospace>0.3, char_ratio>1.12 | میں نے فون ہاتھ میں لیا۔ |
| [worst/shehbaz_short_04.wav](worst/shehbaz_short_04.wav) | shehbaz | 6.9 s | 0.30 / 0.915 | CER-ns 0.045 | 0.94 | sim<0.5, sim_heldout<0.5 | علامہ اقبال نے کہا تھا، ستاروں سے آگے جہاں اور بھی ہیں، ابھی عشق کے امتحاں اور بھی ہیں۔ |
| [worst/trump_30s_01.wav](worst/trump_30s_01.wav) | trump | 28.4 s | 0.84 / 0.977 | WER 0.310 | 0.68 | pace<0.7, wer>0.1, char_ratio<0.88, del_run>=3 | We have the best buildings, the best golf courses, the best hotels, the best restaurants, the best steaks, the… |
| [worst/trump_30s_02.wav](worst/trump_30s_02.wav) | trump | 26.4 s | 0.87 / 0.990 | WER 0.200 | 0.80 | wer>0.1, char_ratio<0.88, del_run>=3 | They told me it couldn't be done. They said, you'll never build a golf course on that land, it's too rocky, to… |
| [worst/trump_30s_03.wav](worst/trump_30s_03.wav) | trump | 30.9 s | 0.65 / 0.943 | WER 0.085 | 0.95 | del_run>=3 | We did it! We won! Eighteenth hole, the whole club watching, I'm down by one stroke, and I hit the most beauti… |
| [worst/trump_30s_04.wav](worst/trump_30s_04.wav) | trump | 30.1 s | 0.84 / 0.991 | WER 0.057 | 0.99 | ins_run>=3 | I have to admit something, and it's not easy for me. I don't admit things very often. Last week, I was playing… |

## tags

The same expressive-set prompts spoken from the plain text and from the text with Higgs control tags (`benchmarks/shehbaz_ur_expressive.json`, `higgs_text`): listen for whether the tag (shouting, whispering, sadness, laughter, slow, elation) is rendered. Both are AI-generated clones.

| pair | plain | with tags | tags used |
|---|---|---|---|
| 34_style-whispering | [tags/34_style-whispering_plain.wav](tags/34_style-whispering_plain.wav) (33 s) | [tags/34_style-whispering_tags.wav](tags/34_style-whispering_tags.wav) (36 s) | <|style:whispering|> |
| 36_sfx-laughter | [tags/36_sfx-laughter_plain.wav](tags/36_sfx-laughter_plain.wav) (23 s) | [tags/36_sfx-laughter_tags.wav](tags/36_sfx-laughter_tags.wav) (29 s) | <|emotion:amusement|> <|prosody:expressive_high|> <|sfx:laughter|> |
