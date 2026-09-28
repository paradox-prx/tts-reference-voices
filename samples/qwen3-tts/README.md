# Qwen3-TTS voice-clone samples (AI-generated)

> **Every file in this folder is AI-generated speech.** It imitates the voices of real people (`trump`: Donald Trump,
> `shehbaz`: Shehbaz Sharif) using Qwen/Qwen3-TTS-12Hz-1.7B-Base voice cloning. **None of it is a real recording, and
> the speakers never said these words:** the texts are fictional benchmark prompts of this repository. Each FLAC carries
> the label in its metadata (Vorbis `COMMENT` and `TITLE`). Do not present, cut or redistribute these clips as anything
> other than labelled AI-generated benchmark samples.

Forty takes from the benchmark in [`server/REPORT.md`](../../server/REPORT.md) (vLLM-Omni 0.28.0 on one RTX 3090, bf16,
sampling 0.9 / 50 / repetition_penalty 1.05), chosen by `server/eval/pick_samples.py` from ~4,300 scored takes:

- **[best/](best/)** (10 per voice): clean on every automatic check, the highest speaker similarity and lowest
  recognition error for their length; the recommended configuration's runs first (Urdu with `non_streaming_mode`,
  the ~60 s texts through the gateway's 60-word splitting).
- **[mid/](mid/)** (5 per voice): the takes closest to each voice's median quality: what a typical request sounds like.
- **[worst/](worst/)** (5 per voice): the most extreme failure of each kind the evaluation found. They come from all
  benchmark settings, including ones the recommended configuration avoids (see "run"); with that configuration Urdu
  still fails like this in ~6-8% of takes and English in ~1% (mostly the wrong-voice case).

Texts that read as political statements, official announcements or claims about public projects were left out.
SIM = cosine speaker similarity to the voice's reference clip (WavLM-Large / WavLM base-plus-sv; real same-speaker
recordings score 0.90-0.94 / >= 0.975, different speakers 0.10-0.18 / 0.75-0.80). Errors are from stock Whisper
large-v3; Urdu error is mostly accent (the same Whisper scores this speaker's real recordings at CER-nospace 0.04).
Pace = seconds per letter / the voice's calibrated pace (1.0 = typical). Every clip's text, transcript, metrics and
source take are in [`samples.json`](samples.json).


## best

| file | lang | length | SIM Large / base | error | pace | run |
|---|---|---|---|---|---|---|
| [trump_short_1.flac](best/trump_short_1.flac) | en | 3.7 s | 0.84 / 0.98 | WER 0.00 | 0.97 | `P3_stream` |
| [trump_medium_1.flac](best/trump_medium_1.flac) | en | 7.9 s | 0.88 / 0.99 | WER 0.00 | 1.02 | `P2_matrix` |
| [trump_long_1.flac](best/trump_long_1.flac) | en | 18.1 s | 0.91 / 0.99 | WER 0.00 | 1.00 | `P2_matrix` |
| [trump_30s_1.flac](best/trump_30s_1.flac) | en | 30.5 s | 0.89 / 0.99 | WER 0.00 | 1.00 | `P3_stream` |
| [trump_60s_1.flac](best/trump_60s_1.flac) | en | 66.4 s | 0.88 / 0.99 | WER 0.00 | 1.00 | `X7_split_60` |
| [trump_short_2.flac](best/trump_short_2.flac) | en | 5.2 s | 0.84 / 0.98 | WER 0.00 | 0.96 | `P3_stream` |
| [trump_medium_2.flac](best/trump_medium_2.flac) | en | 11.8 s | 0.87 / 0.98 | WER 0.00 | 1.01 | `P2_matrix` |
| [trump_long_2.flac](best/trump_long_2.flac) | en | 15.4 s | 0.87 / 0.99 | WER 0.00 | 1.00 | `P2_matrix` |
| [trump_30s_2.flac](best/trump_30s_2.flac) | en | 30.3 s | 0.89 / 0.99 | WER 0.00 | 1.01 | `P3_stream` |
| [trump_60s_2.flac](best/trump_60s_2.flac) | en | 65.8 s | 0.88 / 0.99 | WER 0.00 | 1.02 | `X7_split_60` |
| [shehbaz_short_1.flac](best/shehbaz_short_1.flac) | ur | 5.1 s | 0.82 / 0.98 | CER-nospace 0.05 | 1.07 | `P3_stream` |
| [shehbaz_medium_1.flac](best/shehbaz_medium_1.flac) | ur | 9.8 s | 0.85 / 0.98 | CER-nospace 0.06 | 1.06 | `P2_matrix` |
| [shehbaz_long_1.flac](best/shehbaz_long_1.flac) | ur | 19.2 s | 0.83 / 0.98 | CER-nospace 0.11 | 0.96 | `P2_matrix` |
| [shehbaz_30s_1.flac](best/shehbaz_30s_1.flac) | ur | 36.2 s | 0.86 / 0.98 | CER-nospace 0.11 | 0.99 | `P5_urdu_nsm` |
| [shehbaz_60s_1.flac](best/shehbaz_60s_1.flac) | ur | 72.5 s | 0.86 / 0.99 | CER-nospace 0.09 | 1.05 | `X8_split_nsm` |
| [shehbaz_short_2.flac](best/shehbaz_short_2.flac) | ur | 2.6 s | 0.74 / 0.93 | CER-nospace 0.00 | 0.99 | `P3_stream` |
| [shehbaz_medium_2.flac](best/shehbaz_medium_2.flac) | ur | 8.2 s | 0.82 / 0.98 | CER-nospace 0.07 | 0.98 | `P2_matrix` |
| [shehbaz_long_2.flac](best/shehbaz_long_2.flac) | ur | 25.0 s | 0.83 / 0.98 | CER-nospace 0.10 | 1.07 | `P2_matrix` |
| [shehbaz_30s_2.flac](best/shehbaz_30s_2.flac) | ur | 35.0 s | 0.82 / 0.98 | CER-nospace 0.09 | 1.02 | `P5_urdu_nsm` |
| [shehbaz_60s_2.flac](best/shehbaz_60s_2.flac) | ur | 70.7 s | 0.86 / 0.99 | CER-nospace 0.19 | 1.00 | `X7_split_60` |

## mid

| file | lang | length | SIM Large / base | error | pace | run |
|---|---|---|---|---|---|---|
| [trump_short_1.flac](mid/trump_short_1.flac) | en | 5.2 s | 0.79 / 0.98 | WER 0.00 | 1.08 | `P3_stream` |
| [trump_medium_1.flac](mid/trump_medium_1.flac) | en | 6.4 s | 0.77 / 0.98 | WER 0.00 | 1.03 | `P2_matrix` |
| [trump_long_1.flac](mid/trump_long_1.flac) | en | 16.6 s | 0.81 / 0.99 | WER 0.00 | 1.12 | `P2_matrix` |
| [trump_30s_1.flac](mid/trump_30s_1.flac) | en | 31.9 s | 0.78 / 0.97 | WER 0.00 | 0.94 | `P3_stream` |
| [trump_60s_1.flac](mid/trump_60s_1.flac) | en | 60.0 s | 0.79 / 0.98 | WER 0.00 | 0.95 | `P2_matrix` |
| [shehbaz_short_1.flac](mid/shehbaz_short_1.flac) | ur | 9.7 s | 0.80 / 0.98 | CER-nospace 0.15 | 1.18 | `P2_matrix` |
| [shehbaz_medium_1.flac](mid/shehbaz_medium_1.flac) | ur | 8.2 s | 0.67 / 0.97 | CER-nospace 0.03 | 1.17 | `P2_matrix` |
| [shehbaz_long_1.flac](mid/shehbaz_long_1.flac) | ur | 22.4 s | 0.79 / 0.98 | CER-nospace 0.20 | 1.04 | `P2_matrix` |
| [shehbaz_30s_1.flac](mid/shehbaz_30s_1.flac) | ur | 35.8 s | 0.73 / 0.98 | CER-nospace 0.14 | 0.94 | `P5_urdu_nsm` |
| [shehbaz_60s_1.flac](mid/shehbaz_60s_1.flac) | ur | 61.7 s | 0.78 / 0.98 | CER-nospace 0.14 | 0.96 | `X6_nsm_long_urdu` |

## worst

| file | lang | length | SIM Large / base | error | pace | what went wrong | run |
|---|---|---|---|---|---|---|---|
| [trump_60s_1.flac](worst/trump_60s_1.flac) | en | 63.4 s | -0.09 / 0.71 | WER 0.04 | 1.06 | wrong voice (another speaker) | `P2_matrix` |
| [trump_medium_1.flac](worst/trump_medium_1.flac) | en | 14.1 s | 0.04 / 0.76 | WER 0.05 | 1.30 | wrong voice (another speaker) | `P2_high_c` |
| [trump_short_1.flac](worst/trump_short_1.flac) | en | 4.5 s | 0.09 / 0.77 | WER 0.00 | 1.05 | wrong voice (another speaker) | `P3_stream` |
| [trump_short_2.flac](worst/trump_short_2.flac) | en | 2.7 s | 0.62 / 0.97 | WER 0.00 | 2.43 | far too long for its text (padding / drawn out) | `P2_matrix` |
| [trump_30s_1.flac](worst/trump_30s_1.flac) | en | 30.9 s | 0.85 / 0.99 | WER 0.09 | 1.15 | phrase skipped | `P8_quality_guard_fast` |
| [shehbaz_long_1.flac](worst/shehbaz_long_1.flac) | ur | 23.2 s | 0.72 / 0.97 | CER-nospace 0.97 | 1.06 | garbled speech | `P7_gateway` |
| [shehbaz_30s_1.flac](worst/shehbaz_30s_1.flac) | ur | 34.9 s | 0.81 / 0.99 | CER-nospace 0.35 | 0.98 | skipped passage at a normal duration | `P5_urdu_rp110` |
| [shehbaz_30s_2.flac](worst/shehbaz_30s_2.flac) | ur | 47.0 s | 0.72 / 0.98 | CER-nospace 0.40 | 1.22 | loop Whisper hears as one long word | `P2_high_c` |
| [shehbaz_30s_3.flac](worst/shehbaz_30s_3.flac) | ur | 31.8 s | 0.81 / 0.98 | CER-nospace 0.93 | 0.99 | long voiced gap (filler / babble) | `P5_urdu_rp105` |
| [shehbaz_short_1.flac](worst/shehbaz_short_1.flac) | ur | 8.3 s | 0.72 / 0.97 | CER-nospace 0.15 | 1.87 | pace far off (cut short or padded) | `P2_high_c` |

## Texts

- **best/trump_short_1.flac**: You know, I look out at this room and I see the most beautiful people.
- **best/trump_medium_1.flac**: It closed a long time ago. They built a bank there, a boring bank. And I've eaten in the finest restaurants in the world since then, the finest.
- **best/trump_long_1.flac**: Okay. They gave me this paper, and they said I have to read it, so I'm going to read it. The terms and conditions of the golf club membership. Section one. Members must wear collared shirts at all times. Section two. Members must replace all divots on the fairway. Section three. Carts must remain on the cart path near the greens.
- **best/trump_30s_1.flac**: Listen to me. Listen very carefully. Because I'm only going to say this once. This is the greatest deal. In the history of deals. Maybe ever. Nobody has seen anything like it. Nobody. And when people look back on this day, many years from now, they're going to say, that was the day. That was the day everything changed. Remember where you were. Remember who you were with. Because this is history, folks. Write it down. Tell your children. Tell your grandchildren. They will ask. This is the day. The greatest day. Believe me, folks. Nobody will ever forget it.
- **best/trump_60s_1.flac**: So they hand me this new phone, and they say, sir, it's very easy, all your pictures are in the cloud. The cloud? What cloud? I looked up, there's no cloud. It was a beautiful day. And they say, no, sir, it's not that kind of cloud, it's a digital cloud. A digital cloud. Okay. So where is it? Nobody knows! It's somewhere. It's floating around. And I said, well, if it's floating, can it rain on my pictures? And they looked at me, and they didn't know. Nobody knows how it works. I don't think they know. And then they told me the cloud is actually in a big building somewhere in the desert. So it's not even a cloud! Sometimes, late at night, I sit out on the terrace and I look at the ocean, and I think about things. Big things. What does it all mean? What's the secret to a great deal? And you know what I've come to realize? It's not the money. Everybody thinks it's the money. It's the timing. It's knowing when to walk away, and knowing when to stay at the table. Maybe life is like that too. Maybe life is one very long negotiation. I don't know. I think about it a lot. More than people would think. Maybe the ocean knows. It's been around a long time, longer than me, believe it or not. It doesn't negotiate. It just keeps coming back, every single day.
- **best/trump_short_2.flac**: When I was a young man, I used to look at these buildings from across the river, and I'd say, someday.
- **best/trump_medium_2.flac**: Never. Second, you aim very high, and then you keep pushing. Third, you always have a way out. Always. And fourth, and this is the most important one, you have to know the other side better than they know themselves.
- **best/trump_long_2.flac**: And my friend says, don't worry, it's friendly. Friendly? There's no such thing as a friendly shark! I stayed in the middle of the boat for three hours. Three hours! I didn't move. I'm telling you, never again. Now when I see the ocean, I look at it from the beach. From far away. Very far away.
- **best/trump_30s_2.flac**: Let me tell you something, and I want you to listen. There are people out there, competitors, who think they can beat us. They think they can take what we built. Let me be very clear. That's not going to happen. Not today, not tomorrow, not ever. We know who they are. We know what they're doing. And when the time comes, we will be ready. We are always ready. So to those people, I have a very simple message. Don't even try. You'll lose. You'll lose big. And we will win. We always win. They have been warned. This is their only warning. There won't be another one.
- **best/trump_60s_2.flac**: I miss the old days, I really do. When I was starting out, there was this little diner on the corner, and they made the best burger I ever had. Every Saturday I'd go there, sit at the counter, and the old man would say, the usual? And I'd say, the usual. It closed a long time ago. They built a bank there, a boring bank. And I've eaten in the finest restaurants in the world since then, the finest. But I would give a lot, a lot, to sit at that counter one more time. Just one more time. Sometimes I still drive past that corner. I look at the bank, and I remember the burger. Look at this building. Look at it. Fifty eight floors of the finest glass, the finest marble, the finest everything. When I started, people laughed at me. They said, you'll never do it, kid. And I did it. I built it. My name is right there on the front, in gold letters, big gold letters, and you can see it from three blocks away. People come from all over the world just to take a picture of it. And I tell them, go ahead, take the picture. Take two. It's the most beautiful building in the city, and everybody knows it. And inside, the lobby, the waterfall, the beautiful pink marble. There's nothing like it anywhere in the world.
- **mid/trump_short_1.flac**: I stood on top of the tower last night, the very top, and I looked out over the whole city.
- **mid/trump_medium_1.flac**: That's it. That's the whole secret. Maybe some ice cream later. Two scoops. Everybody else gets one scoop, I get two.
- **mid/trump_long_1.flac**: So a reporter comes up to me, very nice guy, not so smart, and he says, sir, what's your golf handicap? And I said, what handicap? I don't have a handicap. I've won eighteen club championships. Eighteen! And he looks at me, and he says, sir, how many of those were at your own clubs?
- **mid/trump_30s_1.flac**: Folks, I have some tremendous news today. We are opening a brand new restaurant, and it's going to be the best burger restaurant in the history of burgers. The buns are going to be golden, the meat is going to be perfect, and the fries, oh, the fries are going to be crispy, very crispy. We have the best chefs, the best recipes, and the prices are going to be very reasonable. Very reasonable. People are already lining up, and we haven't even opened. You're going to love it. You're going to come back again and again. It's going to be huge! And the milkshakes, the milkshakes are going to be so thick, you'll need two straws.
- **mid/trump_60s_1.flac**: Can you feel it? Can you feel the energy in this room? My heart is pounding, your heart is pounding, everybody's heart is pounding! I've been to a lot of events, the biggest events, the most incredible events, but this one, this one is on fire! The lights, the music, the people standing on their chairs! Look at that guy, he's jumping up and down! I love it! I'm telling you, the electricity in here could power the whole city for a year. Maybe two years. Nobody has ever seen energy like this. Nobody! Everybody, put your hands up! Higher! Higher! Let me hear you! This is what it's all about, folks. This is it! I stood on top of the tower last night, the very top, and I looked out over the whole city. The lights. Millions of lights, as far as you can see. And I thought, wow. Just, wow. When I was a young man, I used to look at these buildings from across the river, and I'd say, someday. Someday. And now, here I am, standing on top of one of them, and it's so quiet up there. So quiet. You can see the clouds moving. It's the most magnificent thing I've ever seen. Truly magnificent. I stayed up there for an hour. Nobody said a word. Sometimes you just have to stand there and look.
- **worst/trump_60s_1.flac**: Hmm, hmm, hmm. Oh, hello, I didn't see you there. I was just humming a little tune. I always hum when I'm on the putting green, it relaxes me. Very relaxing. Mmm, mmm. My golf coach says it's bad, he says it makes me lose focus. I said, how can it be bad? Look, the ball goes in every time. Well, almost every time. Hmm, hmm. See? Right in the cup. Beautiful. The humming works, believe me. Everybody should hum. It's good for the soul, and it's great for your putting. Hmm, hmm, hmm. Okay, next hole. I'll hum all the way there. So they give me the new schedule for tomorrow. Six in the morning, breakfast meeting. Seven, another meeting. Eight, phone calls. Nine, more meetings. Uh. Ten, a lunch meeting, at ten in the morning. Who has lunch at ten in the morning? Ahh. And then golf, they say, maybe, if there's time. If there's time! There's never time. I love my job, I really do, I love it, but sometimes, Ahh, sometimes you just want to sit down and have a cheeseburger. That's all. Just one cheeseburger, in peace. Maybe tomorrow. Maybe the day after tomorrow. We'll see. They'll probably add another meeting. Uh. Okay. Let's go to the meeting.
- **worst/trump_medium_1.flac**: Ahh. And then golf, they say, maybe, if there's time. If there's time! There's never time. I love my job, I really do, I love it, but sometimes, Ahh, sometimes you just want to sit down and have a cheeseburger.
- **worst/trump_short_1.flac**: My heart is pounding, your heart is pounding, everybody's heart is pounding!
- **worst/trump_short_2.flac**: I give it zero stars.
- **worst/trump_30s_1.flac**: Hmm, hmm, hmm. Oh, hello, I didn't see you there. I was just humming a little tune. I always hum when I'm on the putting green, it relaxes me. Very relaxing. Mmm, mmm. My golf coach says it's bad, he says it makes me lose focus. I said, how can it be bad? Look, the ball goes in every time. Well, almost every time. Hmm, hmm. See? Right in the cup. Beautiful. The humming works, believe me. Everybody should hum. It's good for the soul, and it's great for your putting. Hmm, hmm, hmm. Okay, next hole. I'll hum all the way there.
- **best/shehbaz_short_1.flac**: جو آدمی ہر کام وقت پر کرنے کا عادی ہو، وہ ایسے میں کیا کرے؟
- **best/shehbaz_medium_1.flac**: ہم سب دوست وہاں بیٹھتے، باتیں کرتے، ہنستے۔ وہ دکان اب نہیں رہی، بابا جی بھی نہیں رہے۔ وقت کتنی جلدی گزر جاتا ہے۔
- **best/shehbaz_long_1.flac**: ارے! یہ کیا ہے؟ یہ سب کیا ہو رہا ہے؟ میں تو سمجھا تھا کوئی ضروری اجلاس ہے! یہ کیک؟ یہ پھول؟ یہ غبارے؟ آپ لوگوں نے یہ سب کب کیا؟ مجھے تو بالکل خبر نہیں ہوئی! سچ کہوں، میں تو اپنی سالگرہ ہی بھول گیا تھا۔ اتنا کام ہوتا ہے کہ تاریخیں یاد ہی نہیں رہتیں۔
- **best/shehbaz_30s_1.flac**: کل شام مجھے ایک تقریب میں پہنچنا تھا۔ لوگ دو گھنٹے سے انتظار کر رہے تھے۔ اور ہم ایک ٹریفک جام میں پھنس گئے۔ آگے گاڑیاں، پیچھے گاڑیاں، دائیں بائیں گاڑیاں۔ ایک انچ بھی آگے نہیں بڑھ سکتے تھے۔ میں نے فون کیا، پیغام بھیجا، مگر کچھ نہیں ہو سکتا تھا۔ میں بس کھڑکی سے باہر دیکھتا رہا۔ مجھے بہت بے بسی محسوس ہوئی۔ جو آدمی ہر کام وقت پر کرنے کا عادی ہو، وہ ایسے میں کیا کرے؟ اس دن میں نے سوچا، روز کتنے لوگ اسی طرح پھنستے ہوں گے۔ اس کا حل نکالنا ہو گا۔
- **best/shehbaz_60s_1.flac**: آج مجھے ایک بات کا اعتراف کرنا ہے، اور یہ میرے لیے آسان نہیں۔ آپ سب جانتے ہیں کہ میں وقت کا کتنا پابند ہوں۔ جو افسر پانچ منٹ دیر سے آئے، میں اس سے جواب مانگتا ہوں۔ مگر کل، کل میں خود ایک اجلاس میں پندرہ منٹ دیر سے پہنچا۔ جب میں کمرے میں داخل ہوا تو سب افسر خاموش بیٹھے میری طرف دیکھ رہے تھے۔ کسی نے کچھ نہیں کہا، مگر ان کی آنکھیں سب کچھ کہہ رہی تھیں۔ مجھے بہت شرمندگی ہوئی۔ میں نے سب سے معافی مانگی۔ اصول سب کے لیے ایک ہے، میرے لیے بھی۔ ارے! یہ کیا ہے؟ یہ سب کیا ہو رہا ہے؟ میں تو سمجھا تھا کوئی ضروری اجلاس ہے! یہ کیک؟ یہ پھول؟ یہ غبارے؟ آپ لوگوں نے یہ سب کب کیا؟ مجھے تو بالکل خبر نہیں ہوئی! سچ کہوں، میں تو اپنی سالگرہ ہی بھول گیا تھا۔ اتنا کام ہوتا ہے کہ تاریخیں یاد ہی نہیں رہتیں۔ اور یہ کیک پر میری تصویر؟ ماشاءاللہ! کس نے بنوایا ہے یہ؟ آپ سب نے مجھے واقعی حیران کر دیا۔ میں بہت شکر گزار ہوں۔ مگر ایک شرط ہے، کیک کھانے کے بعد سب واپس کام پر!
- **best/shehbaz_short_2.flac**: سب ایک دوسرے کی طرف دیکھنے لگے۔
- **best/shehbaz_medium_2.flac**: آپ سب نے مجھے واقعی حیران کر دیا۔ میں بہت شکر گزار ہوں۔ مگر ایک شرط ہے، کیک کھانے کے بعد سب واپس کام پر!
- **best/shehbaz_long_2.flac**: آپ کو ایک بات بتاؤں؟ پچھلے سال میں ایک دور دراز علاقے میں جا رہا تھا، ایک چھوٹے سے جہاز میں۔ اچانک موسم خراب ہو گیا۔ کالے بادل، تیز ہوا، اور جہاز اوپر نیچے ہونے لگا۔ کھڑکی سے باہر کچھ نظر نہیں آ رہا تھا۔ میرے ساتھ بیٹھے افسر کا رنگ پیلا پڑ گیا۔ سچ پوچھیں تو میرا دل بھی بیٹھ گیا تھا۔
- **best/shehbaz_30s_2.flac**: لب پہ آتی ہے دعا بن کے تمنا میری، زندگی شمع کی صورت ہو خدایا میری۔ دور دنیا کا مرے دم سے اندھیرا ہو جائے، ہر جگہ میرے چمکنے سے اجالا ہو جائے۔ ہو مرے دم سے یونہی میرے وطن کی زینت، جس طرح پھول سے ہوتی ہے چمن کی زینت۔ زندگی ہو مری پروانے کی صورت یا رب، علم کی شمع سے ہو مجھ کو محبت یا رب۔ ہو مرا کام غریبوں کی حمایت کرنا، درد مندوں سے ضعیفوں سے محبت کرنا۔ مرے اللہ! برائی سے بچانا مجھ کو، نیک جو راہ ہو اس رہ پہ چلانا مجھ کو۔
- **best/shehbaz_60s_2.flac**: پچھلے ہفتے میں ایک نئے پارک کا معائنہ کر رہا تھا۔ سب کچھ ٹھیک چل رہا تھا، درخت، پودے، راستے، سب شاندار۔ میں ایک جھاڑی کے قریب گیا تاکہ پھولوں کو دیکھ سکوں۔ اچانک جھاڑی میں کچھ ہلا، اور ایک لمبا سا سانپ باہر نکل آیا! آآآ! میں ایک دم پیچھے کودا، میرے ساتھ کھڑے افسر بھی بھاگے! آآآآ! پھر مالی بابا آئے، مسکرائے، اور بولے، صاحب، ڈریں نہیں، یہ بے ضرر ہے، یہ یہاں کا پرانا رہائشی ہے۔ سب کی جان میں جان آئی۔ میں نے کہا، ٹھیک ہے، مگر اس کے لیے الگ جگہ بنا دیں۔ آج صبح لاہور کا اصل ناشتہ کیا۔ حلوہ پوری، چنے، اور ایک بڑا گلاس میٹھی لسی۔ واہ، کیا بات ہے! لاہور کا ناشتہ دنیا میں کہیں نہیں ملتا۔ ارپ۔ اوہ، معاف کیجیے گا۔ یہ لسی کا کمال ہے۔ بہت گاڑھی تھی۔ ارپ۔ معذرت، معذرت۔ ڈاکٹر کہتے ہیں اتنا بھاری ناشتہ نہیں کرنا چاہیے۔ مگر ڈاکٹر صاحب کبھی لاہور کی لسی پی کر دیکھیں، پھر بات کریں گے۔ ٹھیک ہے، اب کام کی بات کرتے ہیں۔ اور یہ حصہ ریکارڈنگ سے نکال دیں، پلیز۔ کسی نے کچھ نہیں سنا۔
- **mid/shehbaz_short_1.flac**: بچپن میں ہم سکول سے واپس آتے تو گلی کے نکڑ پر ایک بابا جی کی دکان تھی، جو سب سے میٹھی لسی بناتے تھے۔
- **mid/shehbaz_medium_1.flac**: پورے صوبے میں! مجھے اس بیٹی پر فخر ہے، اس کے والدین پر فخر ہے، اس کے استادوں پر فخر ہے۔
- **mid/shehbaz_long_1.flac**: مجھے پرانا لاہور بہت یاد آتا ہے۔ وہ تنگ گلیاں، وہ پرانے دروازے، صبح سویرے تنوروں سے اٹھتی ہوئی تازہ روٹی کی خوشبو۔ بچپن میں ہم سکول سے واپس آتے تو گلی کے نکڑ پر ایک بابا جی کی دکان تھی، جو سب سے میٹھی لسی بناتے تھے۔ ہم سب دوست وہاں بیٹھتے، باتیں کرتے، ہنستے۔
- **mid/shehbaz_30s_1.flac**: ساتھیو، کل ایک سکول میں گیا تو ایک چھوٹے سے بچے نے ہاتھ کھڑا کیا اور بڑی سنجیدگی سے پوچھا، انکل، آپ تقریر کرتے ہوئے ہر وقت انگلی کیوں اٹھاتے ہیں؟ پورا ہال ہنسنے لگا۔ میں نے کہا، بیٹا، یہ انگلی ہمیں یاد دلاتی ہے کہ کام ابھی باقی ہے! اس نے فوراً کہا، تو پھر آپ دونوں ہاتھ اٹھایا کریں، کام تو بہت زیادہ ہے! اب بتائیں، اس بچے کو کیا جواب دیتا؟ میں نے اس کے استاد سے کہا، اس بچے کا خاص خیال رکھیں، یہ بڑا ہو کر بہت بڑا افسر بنے گا، شاید مجھ سے بھی زیادہ سوال پوچھے گا۔
- **mid/shehbaz_60s_1.flac**: میرے سامنے آج فائلوں کا یہ ڈھیر دیکھیں۔ ایک، دو، تین، پچاس، سو، شاید دو سو فائلیں۔ آہ۔ ہر فائل میں کسی کا مسئلہ ہے، کسی کی امید ہے۔ کسی کی پنشن، کسی کا تبادلہ، کسی کا مکان۔ آہ۔ میں چاہتا ہوں کہ ہر فائل آج ہی نمٹ جائے، مگر رات کے گیارہ بج چکے ہیں۔ چائے ٹھنڈی ہو گئی ہے، آنکھیں بھاری ہو رہی ہیں۔ آہ۔ خیر، کوئی بات نہیں۔ یہ لوگ ہم سے امید لگائے بیٹھے ہیں۔ ایک اور کپ چائے منگوائیں، اور اگلی فائل لائیں۔ شکریہ، بہت بہت شکریہ۔ سُڑ۔ معاف کیجیے گا۔ یہ اسلام آباد کا موسم بہار ہے، ہر طرف پولن ہی پولن۔ سُڑ۔ ڈاکٹر نے کہا تھا گولی کھا کر آئیں، میں بھول گیا۔ کام کی جلدی میں بہت کچھ بھول جاتا ہوں۔ سُڑ۔ ہاں تو، یہ شجرکاری مہم بہت ضروری ہے۔ ہمیں لاکھوں درخت لگانے ہیں۔ مگر ایک گزارش ہے، اس بار ایسے درخت لگائیں جن کا پولن کم ہو۔ سُڑ۔ ورنہ اگلے سال یہ تقریر بھی ایسے ہی ہو گی۔ آپ سب ہنس رہے ہیں، مگر میں سنجیدہ ہوں۔
- **worst/shehbaz_long_1.flac**: ہممم، ہممم، ہممم۔ اوہ، آپ آ گئے؟ میں ذرا پودوں کو پانی دے رہا تھا۔ جب بھی میں اپنے باغ میں ہوتا ہوں، کوئی نہ کوئی پرانا گیت گنگنانے لگتا ہوں۔ ہممم، ہممم۔ یہ گلاب دیکھیں، پچھلے سال لگایا تھا، اب کتنا بڑا ہو گیا ہے۔ اور یہ موتیا، اس کی خوشبو تو سارا دن دماغ تازہ رکھتی ہے۔
- **worst/shehbaz_30s_1.flac**: ذرا قریب آئیں، ایک راز کی بات بتاتا ہوں۔ کسی کو بتانا نہیں۔ اس پورے دفتر میں سب سے اچھی چائے کون بناتا ہے؟ کوئی بڑا خانساماں نہیں۔ ہمارے پرانے چپڑاسی، بشیر صاحب۔ وہ چائے میں تھوڑی سی الائچی ڈالتے ہیں، اور دودھ کو خوب پکاتے ہیں۔ میں روز شام کو چپکے سے ان سے ایک کپ منگواتا ہوں۔ اگر یہ بات باہر نکل گئی نا، تو سارے افسر ان کے کمرے کے باہر قطار لگا لیں گے، اور میری چائے کی باری ہی نہیں آئے گی۔ تو بس، یہ بات ہمارے درمیان رہے۔ ٹھیک ہے؟
- **worst/shehbaz_30s_2.flac**: ساتھیو، ایک دلچسپ واقعہ سناتا ہوں۔ پچھلے ہفتے میں صبح سویرے ایک دفتر کا اچانک دورہ کرنے گیا۔ سات بجے تھے۔ دفتر میں صرف چوکیدار موجود تھا، اور وہ بھی سو رہا تھا! ہاہاہا۔ میں نے اسے جگایا تو اس نے آنکھیں ملتے ہوئے کہا، صاحب، اتنی صبح تو کوئی نہیں آتا! ہاہا۔ میں نے کہا، بھائی، میں تو آ گیا ہوں! پھر آٹھ بجے افسران آنا شروع ہوئے، اور ہر ایک کا چہرہ دیکھنے والا تھا۔ Haha، ایک صاحب تو اپنی چائے کا کپ لیے دروازے پر ہی رک گئے۔ میں نے کہا، جناب، چائے بعد میں، کام پہلے! Hahaha۔
- **worst/shehbaz_30s_3.flac**: شکریہ، بہت بہت شکریہ۔ سُڑ۔ معاف کیجیے گا۔ یہ اسلام آباد کا موسم بہار ہے، ہر طرف پولن ہی پولن۔ سُڑ۔ ڈاکٹر نے کہا تھا گولی کھا کر آئیں، میں بھول گیا۔ کام کی جلدی میں بہت کچھ بھول جاتا ہوں۔ سُڑ۔ ہاں تو، یہ شجرکاری مہم بہت ضروری ہے۔ ہمیں لاکھوں درخت لگانے ہیں۔ مگر ایک گزارش ہے، اس بار ایسے درخت لگائیں جن کا پولن کم ہو۔ سُڑ۔ ورنہ اگلے سال یہ تقریر بھی ایسے ہی ہو گی۔ آپ سب ہنس رہے ہیں، مگر میں سنجیدہ ہوں۔
- **worst/shehbaz_short_1.flac**: بس، اتنا ہی، اب اگلے اجلاس میں جانا ہے، چلیں، چلیں، چلیں!
