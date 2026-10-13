import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError, fmtTime, type Config, type Delivery, type Voice } from "../api";
import Player, { drawWave } from "../components/Player";
import TagEditor, { type TagEditorHandle } from "../components/TagEditor";
import { avatarColor, LANGS, langByCode } from "../lib/lang";
import { LivePcmPlayer } from "../lib/livepcm";

type UploadMeta = { id: string; filename: string; seconds: number; peaks: number[]; warning?: string };
type TakeState = {
  id: string; seed: number; stream: boolean; state: "queued" | "running" | "done" | "error";
  parts: number; partsDone: number; partsSeen: number[]; queuePos: number | null; error?: string; busy?: boolean;
  result?: { seconds: number; ok: boolean; reasons: string[]; peaks: number[]; seed: number };
  live?: "waiting" | "playing" | "ended"; fav?: boolean; startedAt: number; firstAudio?: number;
};

const SPEEDS = ["very_slow", "slow", "normal", "fast", "very_fast"];
const SPEED_LABEL: Record<string, string> = { very_slow: "Very slow", slow: "Slow", normal: "Normal", fast: "Fast", very_fast: "Very fast" };
const GROUPS: { key: string; label: string; cat: string }[] = [
  { key: "emotion", label: "Emotion", cat: "emotion" }, { key: "prosody", label: "Delivery", cat: "prosody" },
  { key: "style", label: "Style", cat: "style" }, { key: "sfx", label: "Sound effects", cat: "sfx" },
];
const DEFAULT_DELIVERY: Delivery = { speed: "normal", expressiveness: "normal", pitch: "normal", emotion: "", strength: "light" };

function Seg({ value, options, onChange, label }: { value: string; options: [string, string][]; onChange: (v: string) => void; label: string }) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map(([v, l]) => (
        <button key={v} type="button" aria-pressed={value === v} onClick={() => onChange(v)}>{l}</button>
      ))}
    </div>
  );
}

function TrimControl({ meta, start, end, onChange, maxSel }: { meta: UploadMeta; start: number; end: number;
  onChange: (s: number, e: number) => void; maxSel: number }) {
  const c = useRef<HTMLCanvasElement>(null);
  const audio = useRef<HTMLAudioElement>(null);
  useEffect(() => {
    if (c.current) drawWave(c.current, meta.peaks, 0, getComputedStyle(document.documentElement).getPropertyValue("--faint"), "");
  }, [meta]);
  const dur = meta.seconds;
  const play = () => {
    const a = audio.current!;
    a.currentTime = start;
    a.play();
    const stopAt = () => { if (a.currentTime >= end) { a.pause(); a.removeEventListener("timeupdate", stopAt); } };
    a.addEventListener("timeupdate", stopAt);
  };
  return (
    <div className="grid" style={{ display: "grid", gap: 6 }}>
      <div className="trim">
        <canvas ref={c} />
        <div className="sel" style={{ left: `${(start / dur) * 100}%`, width: `${((end - start) / dur) * 100}%` }} />
      </div>
      <audio ref={audio} src={`/api/uploads/${meta.id}.wav`} preload="auto" />
      <label className="field">Start {start.toFixed(1)}s
        <input className="slider" type="range" min={0} max={dur} step={0.1} value={start}
          onChange={(e) => { const s = Math.min(+e.target.value, end - 3); onChange(s, Math.min(end, s + maxSel)); }} />
      </label>
      <label className="field">End {end.toFixed(1)}s
        <input className="slider" type="range" min={0} max={dur} step={0.1} value={end}
          onChange={(e) => { const en = Math.max(+e.target.value, start + 3); onChange(Math.max(start, en - maxSel), en); }} />
      </label>
      <div className="row small"><button className="btn sm" onClick={play}>▶ Play selection</button>
        <span className={end - start > maxSel + 0.05 ? "bad" : "muted"}>{(end - start).toFixed(1)}s selected (max {maxSel.toFixed(0)}s)</span></div>
    </div>
  );
}

export default function Studio({ cfg }: { cfg: Config }) {
  const [lang, setLang] = useState(() => { try { return localStorage.getItem("studio.lang") || "ur"; } catch { return "ur"; } });
  const L = langByCode(lang);
  const [text, setText] = useState("");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [showAll, setShowAll] = useState(false);
  const [voiceId, setVoiceId] = useState<string>("");
  const [mode, setMode] = useState<"preset" | "upload">("preset");
  const [upload, setUpload] = useState<UploadMeta | null>(null);
  const [trim, setTrim] = useState<[number, number]>([0, 0]);
  const [transcript, setTranscript] = useState("");
  const [uploadErr, setUploadErr] = useState("");
  const [delivery, setDelivery] = useState<Delivery>(DEFAULT_DELIVERY);
  const [preset, setPreset] = useState("");
  const [nTakes, setNTakes] = useState(1);
  const [lockSeed, setLockSeed] = useState(false);
  const [seed, setSeed] = useState<number>(() => Math.floor(Math.random() * 1e9));
  const [exact, setExact] = useState(false);
  const [stream, setStream] = useState(true);
  const [est, setEst] = useState<{ seconds: number; parts: number; errors: string[] }>({ seconds: 0, parts: 0, errors: [] });
  const [takes, setTakes] = useState<TakeState[]>([]);
  const [error, setError] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const editor = useRef<TagEditorHandle>(null);
  const live = useRef<LivePcmPlayer | null>(null);
  const sources = useRef<EventSource[]>([]);

  useEffect(() => { api.get("/api/voices").then(setVoices).catch((e) => setError(String(e))); }, []);
  useEffect(() => { try { localStorage.setItem("studio.lang", lang); } catch { /* storage blocked */ } }, [lang]);
  useEffect(() => {
    const close = (e: MouseEvent) => { if (!(e.target as HTMLElement).closest(".popover-wrap")) setOpen(null); };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);

  const suggested = useMemo(() => voices.filter((v) => v.language === lang), [voices, lang]);
  const listed = showAll || suggested.length === 0 ? voices : suggested;
  useEffect(() => {  // pick a suggested voice for the language
    if (mode === "preset" && (!voiceId || !listed.find((v) => v.id === voiceId)) && listed.length) chooseVoice(listed[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, voices, showAll]);

  const chooseVoice = (v: Voice) => { setVoiceId(v.id); setMode("preset"); setDelivery({ ...DEFAULT_DELIVERY, ...v.delivery }); setPreset(""); };
  const voice = voices.find((v) => v.id === voiceId);

  useEffect(() => {  // live duration estimate (server-side, with the voice's pace)
    const t = setTimeout(() => {
      if (!text.trim()) { setEst({ seconds: 0, parts: 0, errors: [] }); return; }
      api.post("/api/studio/estimate", { text, voice: mode === "preset" ? voiceId : null }).then(setEst).catch(() => undefined);
    }, 350);
    return () => clearTimeout(t);
  }, [text, voiceId, mode]);

  const patchTake = (id: string, p: Partial<TakeState> | ((t: TakeState) => Partial<TakeState>)) =>
    setTakes((ts) => ts.map((t) => (t.id === id ? { ...t, ...(typeof p === "function" ? p(t) : p) } : t)));

  const follow = useCallback((t: TakeState) => {
    const es = new EventSource(`/api/studio/takes/${t.id}/events`);
    sources.current.push(es);
    es.onmessage = (m) => {
      const ev = JSON.parse(m.data);
      if (ev.type === "planned") patchTake(t.id, { parts: ev.parts.length, state: "running" });
      else if (ev.type === "queued") patchTake(t.id, { queuePos: ev.position });
      else if (ev.type === "part_started") patchTake(t.id, { queuePos: null, state: "running" });
      else if (ev.type === "part_done") patchTake(t.id, (x) => {
        const seen = x.partsSeen.includes(ev.part) ? x.partsSeen : [...x.partsSeen, ev.part];
        return { partsSeen: seen, partsDone: seen.length };
      });
      else if (ev.type === "done") { patchTake(t.id, { state: "done", result: ev.result, queuePos: null }); es.close(); }
      else if (ev.type === "error") { patchTake(t.id, { state: "error", error: ev.error, busy: ev.busy }); es.close(); }
    };
    es.onerror = () => es.close();
    if (t.stream) {
      live.current?.stop();
      const p = new LivePcmPlayer(24000);
      live.current = p;
      patchTake(t.id, { live: "waiting" });
      p.onFirstAudio = () => patchTake(t.id, { live: "playing", firstAudio: (performance.now() - t.startedAt) / 1000 });
      p.onEnd = () => patchTake(t.id, { live: "ended" });
      p.play(`/api/studio/takes/${t.id}/live.pcm`).catch(() => patchTake(t.id, { live: "ended" }));
    }
  }, []);

  const generate = async (opts?: { seedOverride?: number; replace?: string }) => {
    setError("");
    if (!text.trim()) { setError("Type some text first."); editor.current?.focus(); return; }
    if (est.errors.length) { setError(est.errors.join(" · ")); return; }
    let v: any;
    if (mode === "preset") {
      if (!voiceId) { setError("Choose a voice."); return; }
      v = { preset: voiceId };
    } else {
      if (!upload) { setError("Upload a reference clip."); return; }
      if (!transcript.trim()) { setError("Type the exact transcript of the uploaded reference."); return; }
      v = { upload: upload.id, start: trim[0], end: trim[1], transcript };
    }
    const s = opts?.seedOverride ?? (lockSeed ? seed : Math.floor(Math.random() * 2 ** 31));
    if (!lockSeed && opts?.seedOverride === undefined) setSeed(s);
    setBusy(true);
    try {
      const r = await api.post("/api/studio/generate", { text, voice: v, delivery, takes: opts?.replace ? 1 : nTakes, seed: s,
        exact, stream: stream && !opts?.replace });
      const now = performance.now();
      const fresh: TakeState[] = r.takes.map((t: any) => ({ id: t.id, seed: t.seed, stream: t.stream, state: "queued",
        parts: r.parts, partsDone: 0, partsSeen: [], queuePos: null, startedAt: now }));
      if (opts?.replace) setTakes((ts) => ts.map((t) => (t.id === opts.replace ? fresh[0] : t)));
      else { sources.current.forEach((e) => e.close()); sources.current = []; setTakes(fresh); }
      fresh.forEach(follow);
    } catch (e) {
      const err = e as ApiError;
      setError(err.status === 503 ? `Server busy: ${err.message}` : err.message);
    } finally { setBusy(false); }
  };

  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); generate(); } };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  });

  const onUpload = async (f: File | undefined) => {
    if (!f) return;
    setUploadErr("");
    try {
      const m: UploadMeta = await api.upload("/api/studio/upload", f);
      if (m.seconds > 60.5) throw new Error("clips must be 60 s or shorter");
      setUpload(m); setMode("upload");
      setTrim([0, Math.min(m.seconds, cfg.limits.max_ref_s)]);
    } catch (e) { setUploadErr((e as Error).message); }
  };

  const applyPreset = (k: string) => {
    setPreset(k);
    if (k && cfg.delivery_presets[k]) { const { label: _label, ...d } = cfg.delivery_presets[k]; setDelivery(d as Delivery); }
  };
  const anyRunning = takes.some((t) => t.state === "queued" || t.state === "running");

  return (
    <div className="studio">
      <main className="studio-main">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div role="tablist" aria-label="Language" className="seg">
            {LANGS.map((l) => (
              <button key={l.code} role="tab" aria-pressed={lang === l.code} aria-selected={lang === l.code} onClick={() => setLang(l.code)}>{l.name}</button>
            ))}
          </div>
          <span className="small faint">Write English loanwords in Latin script (package, sir) for natural speech.</span>
        </div>

        <div className="toolbar" aria-label="Insert tags">
          {GROUPS.map((g) => (
            <div key={g.key} className="popover-wrap">
              <button className="btn sm" aria-expanded={open === g.key} onClick={(e) => { e.stopPropagation(); setOpen(open === g.key ? null : g.key); }}>
                <span className={`chip ${g.cat}`} style={{ margin: 0, padding: "0 7px" }}>{g.label}</span> ▾
              </button>
              {open === g.key && (
                <div className="popover" role="menu">
                  {cfg.tags[g.cat].map((v) => (
                    <button key={v} role="menuitem" className={`opt chip-${g.cat}`} style={{ color: `var(--c-${g.cat})` }}
                      onClick={() => { editor.current?.insertTag(g.cat, v, g.cat === "sfx" ? cfg.sfx_sounds[v] : undefined); setOpen(null); }}>
                      {v.replace(/_/g, " ")}
                    </button>
                  ))}
                  <div className="small faint" style={{ width: "100%" }}>
                    {g.cat === "sfx" ? "Inserted at the cursor with a sound placeholder: edit the word after the chip." :
                      g.cat === "prosody" ? "Speed, pitch and expressiveness go at the start of the sentence under the cursor; pauses go at the cursor." :
                      "Inserted at the start of the sentence under the cursor (Higgs reads tags there)."}
                  </div>
                </div>
              )}
            </div>
          ))}
          <span className="spacer" style={{ flex: 1 }} />
          <button className="btn ghost sm" onClick={() => setText("")} disabled={!text}>Clear</button>
        </div>

        <TagEditor ref={editor} value={text} onChange={setText} vocab={cfg.tags} dir={L.dir} font={L.font}
          placeholder={L.placeholder} onSubmit={() => generate()} label={`Text to speak (${L.name})`} />
        <div className="editor-foot">
          <div className="examples">
            {L.examples.map((ex) => <button key={ex} className="example" dir={L.dir} onClick={() => setText(ex)} title={ex}>{ex}</button>)}
          </div>
          <span aria-live="polite">
            {text.length} chars · ~{fmtTime(est.seconds)} {est.parts > 1 && <>· split into {est.parts} parts (≤ {cfg.limits.max_part_s}s each)</>}
            {est.errors.length > 0 && <span className="bad"> · {est.errors.length} tag problem{est.errors.length > 1 ? "s" : ""}</span>}
          </span>
        </div>
        {est.errors.length > 0 && <div className="error-box small">{est.errors.map((e) => <div key={e}>{e}</div>)}</div>}

        <div className="gen-bar">
          <button className="btn primary big" onClick={() => generate()} disabled={busy}>
            {busy ? "Sending…" : nTakes > 1 ? `Generate ${nTakes} takes` : anyRunning ? "Generate again" : "Generate"} <span className="kbd" style={{ color: "inherit", borderColor: "currentColor" }}>Ctrl ↵</span>
          </button>
          <div className="row small muted" title="How many versions to generate side by side, each with its own seed">Takes
            <Seg label="Number of takes" value={String(nTakes)} options={[["1", "1"], ["2", "2"], ["3", "3"]]} onChange={(v) => setNTakes(+v)} />
          </div>
          {takes.length > 0 && !anyRunning && nTakes !== takes.length &&
            <span className="small warn">Press Generate to make {nTakes} take{nTakes > 1 ? "s" : ""} (showing {takes.length}).</span>}
          <label className="row small muted"><input type="checkbox" checked={stream} onChange={(e) => setStream(e.target.checked)} /> Stream</label>
          {error && <div className="error-box small" role="alert">{error}</div>}
        </div>

        {takes.length > 0 && (
          <section aria-label="Results" className="takes">
            {takes.map((t, i) => (
              <article key={t.id} className={`card take ${t.fav ? "fav" : ""}`}>
                <div className="take-head">
                  <strong>Take {String.fromCharCode(65 + i)}</strong>
                  <div className="row">
                    {t.state === "done" && t.result && (
                      <span className={`badge ${t.result.ok ? "ok" : "warn"}`} title={t.result.reasons.join("\n")}>{t.result.ok ? "QC ok" : "QC warning"}</span>
                    )}
                    <button className="btn ghost sm" aria-pressed={!!t.fav} onClick={() => setTakes((ts) => ts.map((x) => ({ ...x, fav: x.id === t.id ? !x.fav : false })))}
                      title="Pick as favourite">{t.fav ? "★ Favourite" : "☆"}</button>
                  </div>
                </div>
                {t.state === "done" && t.result ? (
                  <Player url={`/api/studio/takes/${t.id}.wav`} peaks={t.result.peaks} label={`take ${i + 1}`} onPlay={() => live.current?.stop()} />
                ) : t.state === "error" ? (
                  <div className="error-box small">{t.busy ? "Server busy: " : ""}{t.error}</div>
                ) : (
                  <div style={{ display: "grid", gap: 6 }}>
                    <div className={`progress ${t.parts ? "" : "indet"}`}><div style={{ width: `${t.parts ? Math.max(6, (t.partsDone / t.parts) * 100) : 30}%` }} /></div>
                    <span className="small muted" aria-live="polite">
                      {t.queuePos ? `Server busy, position ${t.queuePos} in queue…` :
                        t.live === "playing" ? `▶ Playing while generating… (first audio after ${t.firstAudio?.toFixed(2)}s)` :
                          t.parts > 1 ? `Generating part ${Math.min(t.partsDone + 1, t.parts)} of ${t.parts}…` : "Generating…"}
                    </span>
                  </div>
                )}
                <div className="kv">
                  <span>seed {t.seed}</span>
                  {t.result && <span>{t.result.seconds.toFixed(1)}s</span>}
                  {t.result && !t.result.ok && <span className="warn">{t.result.reasons[0]}</span>}
                </div>
                <div className="row">
                  {t.state === "done" && <>
                    <a className="btn sm" href={`/api/studio/takes/${t.id}.wav`} download>⭳ WAV</a>
                    <a className="btn sm" href={`/api/studio/takes/${t.id}.mp3`} download>⭳ MP3</a>
                  </>}
                  <button className="btn sm" onClick={() => { setLockSeed(true); setSeed(t.seed); }} title="Use this seed for the next generation">🔒 Lock seed</button>
                  <button className="btn sm" onClick={() => generate({ seedOverride: Math.floor(Math.random() * 2 ** 31), replace: t.id })}
                    disabled={t.state === "queued" || t.state === "running"}>↻ New seed</button>
                </div>
              </article>
            ))}
          </section>
        )}
      </main>

      <aside className="studio-side" aria-label="Voice and delivery settings">
        <section>
          <h2 className="section-title">Voice</h2>
          <div className="seg" role="group" aria-label="Voice source" style={{ marginBottom: 8 }}>
            <button aria-pressed={mode === "preset"} onClick={() => setMode("preset")}>Presets</button>
            <button aria-pressed={mode === "upload"} onClick={() => setMode("upload")}>Your reference</button>
          </div>
          {mode === "preset" ? (
            <>
              <div className="voices">
                {listed.map((v) => (
                  <div key={v.id} className="voice" role="button" tabIndex={0} aria-pressed={voiceId === v.id}
                    onClick={() => chooseVoice(v)} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), chooseVoice(v))}>
                    <div className="avatar" style={{ background: avatarColor(v.id) }} aria-hidden>{v.name[0]}</div>
                    <div>
                      <div className="name">{v.name} <span className="small faint">· {v.role}</span></div>
                      <div className="desc">{v.language_name}{v.public_figure ? " · real public figure, internal research only" : ""}</div>
                      {v.warnings.length > 0 && <div className="small warn">{v.warnings[0]}</div>}
                    </div>
                    <button className="mini-play" aria-label={`Preview ${v.name}`} onClick={(e) => {
                      e.stopPropagation();
                      const a = new Audio(v.preview_url);
                      document.querySelectorAll("audio").forEach((o) => o.pause());
                      a.play();
                    }}>▶</button>
                  </div>
                ))}
              </div>
              {suggested.length > 0 && suggested.length < voices.length && (
                <button className="btn ghost sm" style={{ marginTop: 6 }} onClick={() => setShowAll(!showAll)}>
                  {showAll ? `Only ${L.name} voices` : `Show all ${voices.length} voices`}</button>
              )}
              {voice && <p className="small muted" style={{ marginBottom: 0 }}>{voice.description}</p>}
            </>
          ) : (
            <div className="upload">
              <label className="btn sm" style={{ justifySelf: "start" }}>Upload WAV/MP3 (5–60 s)
                <input type="file" accept="audio/*,.wav,.mp3,.ogg,.m4a" className="sr-only" onChange={(e) => onUpload(e.target.files?.[0])} />
              </label>
              {uploadErr && <div className="error-box small">{uploadErr}</div>}
              {upload && <>
                <div className="small muted">{upload.filename} · {upload.seconds.toFixed(1)}s {upload.warning && <span className="warn">· {upload.warning}</span>}</div>
                <TrimControl meta={upload} start={trim[0]} end={trim[1]} maxSel={cfg.limits.max_ref_s} onChange={(s, e) => setTrim([s, e])} />
                <label className="field">Exact transcript of the selected part
                  <textarea className="input" dir="auto" value={transcript} onChange={(e) => setTranscript(e.target.value)}
                    placeholder="Type exactly what is said in the selection (no auto-transcription)" />
                </label>
                <div className="small faint">The clone copies the reference's pace and energy: a calm clip gives calm speech.</div>
              </>}
            </div>
          )}
        </section>

        <section>
          <h2 className="section-title">Delivery</h2>
          <div style={{ display: "grid", gap: 12 }}>
            <label className="field">Preset
              <select className="input" value={preset} onChange={(e) => applyPreset(e.target.value)}>
                <option value="">{voice ? `${voice.name}'s defaults` : "Custom"}</option>
                {Object.entries(cfg.delivery_presets).map(([k, p]) => <option key={k} value={k}>{p.label}</option>)}
              </select>
            </label>
            <label className="field">Speed: {SPEED_LABEL[delivery.speed]}
              <input className="slider" type="range" min={0} max={4} step={1} value={SPEEDS.indexOf(delivery.speed)}
                onChange={(e) => setDelivery({ ...delivery, speed: SPEEDS[+e.target.value] })} aria-valuetext={SPEED_LABEL[delivery.speed]} />
              <span className="slider-labels"><span>Very slow</span><span>Normal</span><span>Very fast</span></span>
            </label>
            <div className="field">Expressiveness
              <Seg label="Expressiveness" value={delivery.expressiveness} onChange={(v) => setDelivery({ ...delivery, expressiveness: v })}
                options={[["low", "Low"], ["normal", "Normal"], ["high", "High"]]} />
            </div>
            <div className="field">Pitch
              <Seg label="Pitch" value={delivery.pitch} onChange={(v) => setDelivery({ ...delivery, pitch: v })}
                options={[["low", "Low"], ["normal", "Normal"], ["high", "High"]]} />
            </div>
            <label className="field">Emotion (every sentence)
              <select className="input" value={delivery.emotion} onChange={(e) => setDelivery({ ...delivery, emotion: e.target.value })}>
                <option value="">None</option>
                {cfg.tags.emotion.map((e) => <option key={e} value={e}>{e}</option>)}
              </select>
            </label>
            <div className="field">Tag strength
              <Seg label="Tag strength" value={delivery.strength} onChange={(v) => setDelivery({ ...delivery, strength: v })}
                options={[["none", "None"], ["light", "Light"], ["strong", "Strong"]]} />
              <span className="small faint">{delivery.strength === "none" ? "Only the tags in your text." :
                delivery.strength === "light" ? "Delivery tags once, at the start." : "Delivery restated at every sentence."}</span>
              {delivery.strength === "strong" && <div className="hint">Strong tags hold the mood better, but stacking strong tags can make the voice drift away from the reference.</div>}
            </div>
          </div>
        </section>

        <section>
          <h2 className="section-title">Seed</h2>
          <div style={{ display: "grid", gap: 8 }}>
            <div className="row">
              <label className="row small"><input type="checkbox" checked={lockSeed} onChange={(e) => setLockSeed(e.target.checked)} /> Lock seed</label>
              <input className="input" style={{ width: 150 }} type="number" value={seed} onChange={(e) => setSeed(+e.target.value)} disabled={!lockSeed} aria-label="Seed" />
              <button className="btn sm ghost" onClick={() => setSeed(Math.floor(Math.random() * 2 ** 31))} title="New random seed">🎲</button>
            </div>
            <label className="row small"><input type="checkbox" checked={exact} onChange={(e) => setExact(e.target.checked)} /> Exact reproduction</label>
            <span className="small faint">A seed reproduces a take only when it runs alone on the server (batching changes the
              numbers). Exact mode waits for the server to be free, then runs alone.</span>
          </div>
        </section>
      </aside>
    </div>
  );
}
