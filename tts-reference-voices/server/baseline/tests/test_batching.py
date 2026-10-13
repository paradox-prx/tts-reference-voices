"""Dynamic batching, grouping, seeds, per-row caps and the length policy, OOM splitting, queue limits, prompt cache."""

from __future__ import annotations

import asyncio

import pytest
import torch

import engine as eng
from conftest import data_url, wav_bytes
from fake_qwen_tts import SPF, FakeTTS, fake_embedding
from wavlabel import wav_pcm16


async def burst(h, bodies):
    return await asyncio.gather(*(h.speech(**b) for b in bodies))


async def test_concurrent_requests_share_one_batch(make_harness):
    fake = FakeTTS(delay=0.02)
    async with make_harness("--batch-window-ms", "200", fake=fake) as h:
        rs = await burst(h, [{"input": f"text {i} " + "w " * i, "voice": "alpha"} for i in range(4)])
    assert [r.status_code for r in rs] == [200] * 4
    assert [len(c["texts"]) for c in fake.calls] == [4]
    assert {r.headers["x-baseline-batch-size"] for r in rs} == {"4"}
    assert len({r.headers["x-baseline-batch-id"] for r in rs}) == 1
    # each row keeps its own length
    assert [int(r.headers["x-baseline-codec-frames"]) for r in rs] == [3 * (2 + i) for i in range(4)]


@pytest.mark.parametrize("max_batch, sizes", [("2", [2, 2]), ("1", [1, 1, 1, 1]), ("8", [4])])
async def test_max_batch(make_harness, max_batch, sizes):
    fake = FakeTTS(delay=0.02)
    async with make_harness("--max-batch", max_batch, "--batch-window-ms", "200", fake=fake) as h:
        rs = await burst(h, [{"input": f"t {i}", "voice": "alpha"} for i in range(4)])
        info = (await h.client.get("/v1/baseline/info")).json()
    assert all(r.status_code == 200 for r in rs)
    assert [len(c["texts"]) for c in fake.calls] == sizes
    assert sum(info["batcher"]["batch_sizes"].values()) == len(sizes)


async def test_batch_window_elapses_for_a_lone_request(make_harness):
    async with make_harness("--batch-window-ms", "60") as h:
        r = await h.speech(input="solo", voice="alpha")
    assert r.status_code == 200 and r.headers["x-baseline-batch-size"] == "1"
    assert float(r.headers["x-baseline-queue-ms"]) >= 55


async def test_grouping_by_sampling_and_mode_but_not_language_or_voice(make_harness):
    fake = FakeTTS(delay=0.02)
    hot = {"temperature": 0.7}
    bodies = [
        {"input": "a", "voice": "alpha"},                                   # defaults, English
        {"input": "b", "voice": "beta"},                                    # defaults, Auto, other voice
        {"input": "c", "voice": "alpha", "extra_params": hot},
        {"input": "d", "voice": "alpha", "non_streaming_mode": True},
        {"input": "e", "voice": "beta", "extra_params": hot},
        {"input": "f", "ref_audio": data_url(wav_bytes(2.0)), "ref_text": "r", "language": "German"},  # defaults
    ]
    async with make_harness("--batch-window-ms", "200", fake=fake) as h:
        rs = await burst(h, bodies)
    assert all(r.status_code == 200 for r in rs), [r.text for r in rs]
    groups = sorted((tuple(c["texts"]), tuple(c["languages"]), c["kwargs"]["temperature"], c["non_streaming_mode"])
                    for c in fake.calls)
    assert groups == [
        (("a", "b", "f"), ("English", "Auto", "German"), 0.9, False),
        (("c", "e"), ("English", "Auto"), 0.7, False),
        (("d",), ("English",), 0.9, True),
    ]


async def test_fifo_oldest_group_first(make_harness):
    fake = FakeTTS(delay=0.05)
    async with make_harness("--batch-window-ms", "0", fake=fake) as h:
        first = asyncio.create_task(h.speech(input="blocker", voice="alpha"))
        await asyncio.sleep(0.02)  # the worker is busy with 'blocker'; the rest queue up in this order
        rest = [asyncio.create_task(h.speech(**b)) for b in (
            {"input": "x1", "voice": "alpha", "extra_params": {"top_k": 10}},
            {"input": "y1", "voice": "alpha"},
            {"input": "x2", "voice": "alpha", "extra_params": {"top_k": 10}},
        )]
        await asyncio.gather(first, *rest)
    assert [c["texts"] for c in fake.calls] == [["blocker"], ["x1", "x2"], ["y1"]]


async def test_seeded_requests_run_alone_and_reproduce(make_harness, monkeypatch):
    seeds = []
    real = torch.manual_seed
    monkeypatch.setattr(torch, "manual_seed", lambda s: (seeds.append(s), real(s))[1])
    fake = FakeTTS(delay=0.02)
    async with make_harness("--batch-window-ms", "200", fake=fake) as h:
        rs = await burst(h, [{"input": "u1", "voice": "alpha"}, {"input": "s1", "voice": "alpha", "seed": 1234},
                             {"input": "u2", "voice": "alpha"}, {"input": "s2", "voice": "alpha", "seed": 1234}])
    assert all(r.status_code == 200 for r in rs)
    by_text = {tuple(c["texts"]): c for c in fake.calls}
    assert set(by_text) == {("u1", "u2"), ("s1",), ("s2",)}
    assert seeds == [1234, 1234]
    assert by_text[("s1",)]["rng"] == by_text[("s2",)]["rng"]      # same seed -> same RNG draw
    assert rs[1].headers["x-baseline-batch-size"] == "1"


async def test_batch_cap_is_max_of_rows_and_rows_keep_their_own_cap(make_harness):
    fake = FakeTTS(delay=0.02)
    async with make_harness("--batch-window-ms", "200", "--length-policy", "truncate", fake=fake) as h:
        rs = await burst(h, [
            {"input": "one two three four five six seven eight nine ten", "voice": "alpha", "max_new_tokens": 12},
            {"input": "one two three four five", "voice": "alpha", "max_new_tokens": 40},
            {"input": "short", "voice": "alpha"},
        ])
    assert [len(c["texts"]) for c in fake.calls] == [3]
    assert fake.calls[0]["kwargs"]["max_new_tokens"] == 192          # max(12, 40, 192 default)
    a, b, c = rs
    assert a.headers["x-baseline-max-new-tokens"] == "12" and a.headers["x-baseline-codec-frames"] == "12"
    assert a.headers["x-baseline-finish-reason"] == "length"          # natural 30 frames > its own cap of 12
    assert len(wav_pcm16(a.content)[0]) == 12 * SPF * 2               # trimmed to exactly 12 frames
    assert b.headers["x-baseline-codec-frames"] == "15" and b.headers["x-baseline-finish-reason"] == "stop"
    assert c.headers["x-baseline-codec-frames"] == "3" and c.headers["x-baseline-batch-max-new-tokens"] == "192"


async def test_length_error_policy_mirrors_vllm_omni(make_harness):
    fake = FakeTTS()
    async with make_harness(fake=fake) as h:
        # explicit max_new_tokens -> no retry -> 500
        r = await h.speech(input="one two three four five", voice="alpha", max_new_tokens=10)
        assert r.status_code == 500
        assert "did not emit codec EOS before its token budget (10/10" in r.json()["error"]["message"]
        assert len(fake.calls) == 1
        # runaway without seed/max_new_tokens -> retried once -> still runaway -> 500
        r = await h.speech(input="loop forever", voice="alpha")
        assert r.status_code == 500 and "(192/192" in r.json()["error"]["message"]
        assert len(fake.calls) == 3
        # seeded -> no retry
        r = await h.speech(input="loop again", voice="alpha", seed=5)
        assert r.status_code == 500 and len(fake.calls) == 4
        info = (await h.client.get("/v1/baseline/info")).json()
        assert info["batcher"]["stats"]["length_retries"] == 1 and info["batcher"]["stats"]["length_rows"] == 4


async def test_length_retry_can_succeed(make_harness):
    fake = FakeTTS(loop_first_n=1)
    async with make_harness(fake=fake) as h:
        r = await h.speech(input="maybe-loop text", voice="alpha")
    assert r.status_code == 200 and r.headers["x-baseline-retries"] == "1"
    assert len(fake.calls) == 2


async def test_no_length_retry_flag(make_harness):
    fake = FakeTTS(loop_first_n=1)
    async with make_harness("--no-length-retry", fake=fake) as h:
        r = await h.speech(input="maybe-loop text", voice="alpha")
    assert r.status_code == 500 and len(fake.calls) == 1


async def test_oom_splits_batch(make_harness):
    fake = FakeTTS(delay=0.01, oom_above=2)
    async with make_harness("--batch-window-ms", "200", fake=fake) as h:
        rs = await burst(h, [{"input": f"t {i}", "voice": "alpha"} for i in range(5)])
        info = (await h.client.get("/v1/baseline/info")).json()
    assert all(r.status_code == 200 for r in rs)
    assert sorted(len(c["texts"]) for c in fake.calls) == [1, 2, 2]
    assert sorted(int(r.headers["x-baseline-batch-size"]) for r in rs) == [1, 2, 2, 2, 2]
    assert info["engine"]["stats"]["oom_splits"] == 2


async def test_oom_single_row_fails_500(make_harness):
    fake = FakeTTS(oom_above=0)
    async with make_harness(fake=fake) as h:
        r = await h.speech(input="x", voice="alpha")
    assert r.status_code == 500 and "OutOfMemoryError" in r.json()["error"]["message"]


async def test_queue_full_503(make_harness):
    fake = FakeTTS(delay=0.2)
    async with make_harness("--max-queue", "1", "--max-batch", "1", "--batch-window-ms", "0", fake=fake) as h:
        rs = await burst(h, [{"input": f"t {i}", "voice": "alpha"} for i in range(4)])
    codes = sorted(r.status_code for r in rs)
    assert 200 in codes and 503 in codes
    assert all("queue full" in r.json()["error"]["message"] for r in rs if r.status_code == 503)


# ------------------------------------------------------------------------------------------------ prompt cache

async def test_prompt_cache_on(make_harness):
    fake = FakeTTS()
    async with make_harness(fake=fake) as h:
        startup_prompts = len(fake.prompt_calls)
        assert startup_prompts == 2                                    # one per repo voice, pinned
        for _ in range(3):
            assert (await h.speech(input="a", voice="alpha")).headers["x-baseline-prompt-cache"] == "hit"
        ref = data_url(wav_bytes(2.0, freq=300))
        heads = [(await h.speech(input="a", ref_audio=ref, ref_text="t")).headers["x-baseline-prompt-cache"]
                 for _ in range(3)]
        assert heads == ["miss", "hit", "hit"]
        # same audio, different transcript -> different ICL prompt
        assert (await h.speech(input="a", ref_audio=ref, ref_text="u")).headers["x-baseline-prompt-cache"] == "miss"
    assert len(fake.prompt_calls) == startup_prompts + 2


async def test_prompt_cache_off_recomputes_per_request(make_harness):
    fake = FakeTTS(delay=0.01)
    async with make_harness("--no-prompt-cache", "--batch-window-ms", "200", fake=fake) as h:
        assert fake.prompt_calls == []                                  # nothing prepared at startup
        rs = await burst(h, [{"input": f"t {i}", "voice": "alpha"} for i in range(3)])
        assert {r.headers["x-baseline-prompt-cache"] for r in rs} == {"off"}
        assert len(fake.calls) == 1 and len(fake.prompt_calls) == 3     # one prompt per request, even in one batch
        await h.speech(input="z", voice="alpha")
    assert len(fake.prompt_calls) == 4


async def test_prompt_cache_lru_eviction(make_harness):
    fake = FakeTTS()
    async with make_harness("--prompt-cache-size", "1", fake=fake) as h:
        r1, r2 = data_url(wav_bytes(2.0, freq=310)), data_url(wav_bytes(2.0, freq=320))
        heads = []
        for ref in (r1, r1, r2, r1, r1):
            heads.append((await h.speech(input="a", ref_audio=ref, ref_text="t")).headers["x-baseline-prompt-cache"])
        # pinned repo voices are not evicted by the LRU
        assert (await h.speech(input="a", voice="beta")).headers["x-baseline-prompt-cache"] == "hit"
    assert heads == ["miss", "hit", "miss", "miss", "hit"]


# ------------------------------------------------------------------------------------------------ averaged embedding

async def test_avg_embedding(make_harness, voices_dir):
    fake = FakeTTS()
    async with make_harness("--avg-embedding", fake=fake) as h:
        r = await h.speech(input="a", voice="alpha")
        info = (await h.client.get("/v1/baseline/info")).json()
        ref_bytes = (voices_dir / "alpha/references/qwen3-tts.wav").read_bytes()
        r_inline = await h.speech(input="a", ref_audio=data_url(ref_bytes),
                                  ref_text="hello world this is the reference")
    assert r.status_code == 200
    clips = []
    for p in ("alpha_01.wav", "alpha_02.wav"):
        audio, sr = eng.decode_audio((voices_dir / "alpha" / p).read_bytes())
        clips.append(fake_embedding(eng.to_24k(audio, sr)))
    e = torch.stack(clips)
    target = e.norm(dim=1).mean()
    want = e.mean(0) * (target / e.mean(0).norm())
    used = fake.calls[0]["items"][0].ref_spk_embedding
    assert torch.allclose(used, want, atol=1e-6)
    assert abs(float(used.norm()) - float(target)) < 1e-5
    st = next(v for v in info["startup"]["voices"] if v["voice"] == "alpha")["avg_embedding"]
    assert st["clips"] == ["alpha_01.wav", "alpha_02.wav"] and len(st["clip_norms"]) == 2
    assert abs(st["avg_norm"] - st["target_norm"]) < 1e-3
    # an inline request with the same audio bytes does NOT get the averaged embedding
    assert r_inline.headers["x-baseline-prompt-cache"] == "miss"
    assert not torch.allclose(fake.calls[-1]["items"][0].ref_spk_embedding, want)


async def test_avg_embedding_with_cache_off(make_harness):
    fake = FakeTTS()
    async with make_harness("--avg-embedding", "--no-prompt-cache", fake=fake) as h:
        await h.speech(input="a", voice="beta")
    clip = eng.decode_audio((h.st.args.voices_dir / "beta" / "beta_01.wav").read_bytes())
    want = fake_embedding(eng.to_24k(*clip))
    assert torch.allclose(fake.calls[0]["items"][0].ref_spk_embedding, want, atol=1e-6)  # 1 clip: avg == clip


async def test_cancelled_pending_request_is_dropped(make_harness):
    fake = FakeTTS(delay=0.2)
    async with make_harness("--batch-window-ms", "0", "--max-batch", "1", fake=fake) as h:
        busy = asyncio.create_task(h.speech(input="blocker", voice="alpha"))
        await asyncio.sleep(0.05)
        doomed = asyncio.create_task(h.speech(input="never", voice="alpha"))
        await asyncio.sleep(0.05)
        assert len(h.st.batcher.pending) == 1
        doomed.cancel()
        await asyncio.sleep(0.01)
        assert h.st.batcher.pending == [] and h.st.batcher.stats["cancelled_pending"] == 1
        assert (await busy).status_code == 200
        assert (await h.speech(input="after", voice="alpha")).status_code == 200
    assert [c["texts"] for c in fake.calls] == [["blocker"], ["after"]]
