import { useEffect, useMemo, useRef, useState } from "react";
import { api, download, fmtTime, type Config } from "../api";
import Player from "../components/Player";

type Spk = { upload: string; tag: string; filename: string; seconds: number; transcript: string; warnings: string[] };
type RowsInfo = { id: string; count: number; preview: any[]; pinned: Record<string, number>; with_tags: number;
  with_seed: number; tag_errors: { id: string; errors: string[] }[]; tag_error_count: number; filename: string };
type JobSummary = { id: string; name: string; status: string; total: number; counts: Record<string, number>;
  finished: number; per_speaker: Record<string, { total: number; done: number; flagged: number }>; audio_s: number;
  active_s: number; rtf_x: number | null; eta_s: number | null; errors: { t: number; msg: string }[] };

const STATUS_CLASS: Record<string, string> = { running: "ok", done: "ok", paused: "warn", queued: "", cancelled: "bad", error: "bad" };
const COLORS = ["#7c6cff", "#ff7ab6", "#3ccf91", "#f2b84b", "#6cc6ff", "#c39bff", "#ff8f6b", "#4fd1c5"];

function Num({ label, value, onChange, step = 1, min, max }: { label: string; value: number; onChange: (v: number) => void;
  step?: number; min?: number; max?: number }) {
  return <label className="field">{label}<input className="input" type="number" step={step} min={min} max={max} value={value}
    onChange={(e) => onChange(e.target.value === "" ? 0 : +e.target.value)} /></label>;
}

function Seg({ value, options, onChange, label }: { value: string; options: [string, string][]; onChange: (v: string) => void; label: string }) {
  return <div className="seg" role="group" aria-label={label}>{options.map(([v, l]) =>
    <button key={v} type="button" aria-pressed={value === v} onClick={() => onChange(v)}>{l}</button>)}</div>;
}

function Drop({ accept, multiple, onFiles, children }: { accept: string; multiple?: boolean; onFiles: (f: File[]) => void; children: React.ReactNode }) {
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  return (
    <div className={`drop ${over ? "over" : ""}`} role="button" tabIndex={0} onClick={() => input.current?.click()}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); onFiles(Array.from(e.dataTransfer.files)); }}>
      {children}
      <input ref={input} type="file" accept={accept} multiple={multiple} className="sr-only"
        onChange={(e) => { onFiles(Array.from(e.target.files ?? [])); e.target.value = ""; }} />
    </div>
  );
}

export default function Dev({ cfg }: { cfg: Config }) {
  const [speakers, setSpeakers] = useState<Spk[]>([]);
  const [rows, setRows] = useState<RowsInfo | null>(null);
  const [conf, setConf] = useState<any>(() => JSON.parse(JSON.stringify(cfg.defaults)));
  const [name, setName] = useState("dataset");
  const [dist, setDist] = useState<Record<string, number> | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "bad"; text: string } | null>(null);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [samples, setSamples] = useState<any[]>([]);
  const [sampleSeed, setSampleSeed] = useState(0);
  const [spkFilter, setSpkFilter] = useState("");
  const [uploading, setUploading] = useState(0);
  const [regen, setRegen] = useState<number | null>(null);
  const [zipFlagged, setZipFlagged] = useState("");   // "" = as set in the job's config
  const [zipExtra, setZipExtra] = useState("");

  const set = (path: string, v: any) => setConf((c: any) => {
    const n = JSON.parse(JSON.stringify(c));
    const ks = path.split(".");
    let o = n;
    for (const k of ks.slice(0, -1)) o = o[k];
    o[ks[ks.length - 1]] = v;
    return n;
  });

  // ---- speakers / rows ----
  const addSpeakers = async (files: File[]) => {
    const csv = files.find((f) => f.name.toLowerCase().endsWith(".csv"));
    const audio = files.filter((f) => !f.name.toLowerCase().endsWith(".csv"));
    setUploading((n) => n + audio.length);
    for (const f of audio) {
      try {
        const m = await api.upload("/api/dev/speakers", f);
        setSpeakers((s) => [...s.filter((x) => x.tag !== m.tag), { upload: m.id, tag: m.tag, filename: m.filename, seconds: m.seconds, transcript: "", warnings: m.warnings }]);
      } catch (e) { setMsg({ kind: "bad", text: `${f.name}: ${(e as Error).message}` }); }
      setUploading((n) => n - 1);
    }
    if (csv) await importSpeakersCsv(csv);
  };
  const importSpeakersCsv = async (f: File) => {
    try {
      const map: Record<string, string> = await api.upload("/api/dev/speakers_csv", f);
      setSpeakers((s) => s.map((x) => (map[x.tag] ? { ...x, transcript: map[x.tag] } : x)));
      setMsg({ kind: "ok", text: `speakers.csv: ${Object.keys(map).length} transcripts` });
    } catch (e) { setMsg({ kind: "bad", text: (e as Error).message }); }
  };
  const loadRows = async (files: File[]) => {
    const f = files[0];
    if (!f) return;
    try { setRows({ ...(await api.upload("/api/dev/rows", f)), filename: f.name }); setMsg(null); }
    catch (e) { setMsg({ kind: "bad", text: `${f.name}: ${(e as Error).message}` }); }
  };

  // ---- distribution preview ----
  const tags = speakers.map((s) => s.tag);
  useEffect(() => {
    if (!rows || !tags.length) { setDist(null); return; }
    const t = setTimeout(() => api.post("/api/dev/distribution", { rows: rows.id, speakers: tags, distribution: conf.distribution })
      .then((r) => setDist(r.counts)).catch((e) => { setDist(null); setMsg({ kind: "bad", text: (e as Error).message }); }), 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows?.id, tags.join(","), JSON.stringify(conf.distribution)]);

  // ---- jobs ----
  const refresh = () => api.get("/api/dev/jobs").then(setJobs).catch(() => undefined);
  useEffect(() => { refresh(); }, []);
  useEffect(() => {
    const live = jobs.some((j) => j.status === "running" || j.status === "queued");
    const t = setInterval(refresh, live ? 2000 : 8000);
    return () => clearInterval(t);
  }, [jobs]);
  const job = jobs.find((j) => j.id === sel) ?? null;
  const loadSamples = (seed = sampleSeed, spk = spkFilter) => {
    if (!sel) return;
    api.get(`/api/dev/jobs/${sel}/samples?n=50&seed=${seed}${spk ? `&speaker=${encodeURIComponent(spk)}` : ""}`).then(setSamples);
  };
  useEffect(() => { loadSamples(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [sel, spkFilter, job?.finished && Math.floor(job.finished / 25)]);

  const problems = useMemo(() => {
    const p: string[] = [];
    if (!speakers.length) p.push("add at least one speaker");
    speakers.forEach((s) => !s.transcript.trim() && p.push(`${s.tag}: transcript missing`));
    if (!rows) p.push("load a rows file");
    if (new Set(tags).size !== tags.length) p.push("duplicate speaker tags");
    return p;
  }, [speakers, rows, tags]);

  const start = async () => {
    if (problems.length) { setMsg({ kind: "bad", text: problems.join(" · ") }); return; }
    try {
      const j = await api.post("/api/dev/jobs", { name, config: conf, rows: rows!.id,
        speakers: speakers.map((s) => ({ upload: s.upload, tag: s.tag, transcript: s.transcript })) });
      const notes = Object.entries(j.speaker_notes || {}).map(([k, v]) => `${k}: ${v}`).join(" · ");
      setMsg({ kind: "ok", text: `Job ${j.id} started (${j.total} rows).${notes ? " Reference notes: " + notes : ""}` });
      setSel(j.id); refresh();
    } catch (e) { setMsg({ kind: "bad", text: (e as Error).message }); }
  };
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); start(); } };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  });

  const exportConfig = () => {
    const c = { ...conf, name, speakers: speakers.map((s) => ({ tag: s.tag, transcript: s.transcript, source: s.filename })) };
    const url = URL.createObjectURL(new Blob([JSON.stringify(c, null, 1)], { type: "application/json" }));
    const a = document.createElement("a"); a.href = url; a.download = `job_config_${name}.json`; a.click(); URL.revokeObjectURL(url);
  };
  const importConfig = async (files: File[]) => {
    try {
      const c = JSON.parse(await files[0].text());
      const merged = JSON.parse(JSON.stringify(cfg.defaults));
      for (const k of Object.keys(c)) merged[k] = typeof c[k] === "object" && !Array.isArray(c[k]) && merged[k] ? { ...merged[k], ...c[k] } : c[k];
      setConf(merged);
      if (c.name) setName(c.name);
      if (Array.isArray(c.speakers)) {
        const t: Record<string, string> = Object.fromEntries(c.speakers.map((s: any) => [s.tag, s.transcript]));
        setSpeakers((s) => s.map((x) => (t[x.tag] ? { ...x, transcript: t[x.tag] } : x)));
        const missing = c.speakers.filter((s: any) => !speakers.find((x) => x.tag === s.tag)).map((s: any) => s.tag);
        setMsg({ kind: "ok", text: `Config imported.${missing.length ? ` Upload the reference audio for: ${missing.join(", ")} (transcripts are applied when the tag matches).` : ""}` });
      } else setMsg({ kind: "ok", text: "Config imported." });
    } catch (e) { setMsg({ kind: "bad", text: `config: ${(e as Error).message}` }); }
  };

  const act = async (id: string, a: string) => { await api.post(`/api/dev/jobs/${id}/${a}`); refresh(); };
  const tagPool: string[] = conf.tags.pool ?? [];
  const togglePool = (t: string) => set("tags.pool", tagPool.includes(t) ? tagPool.filter((x) => x !== t) : [...tagPool, t]);

  return (
    <div className="dev">
      <aside className="dev-left" aria-label="New job">
        <details className="panel" open>
          <summary>1 · Speakers <span className="small faint">{speakers.length} {uploading > 0 && `· uploading ${uploading}…`}</span></summary>
          <div className="body">
            <Drop accept="audio/*,.wav,.mp3,.ogg,.flac,.csv" multiple onFiles={addSpeakers}>
              Drop reference WAVs here (+ optional <b>speakers.csv</b>: filename,transcript) or click
            </Drop>
            {speakers.map((s, i) => (
              <div key={s.upload} className="spk">
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <input className="input" style={{ width: 170 }} value={s.tag} aria-label="Speaker tag"
                    onChange={(e) => setSpeakers((x) => x.map((y, j) => (j === i ? { ...y, tag: e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, "_") } : y)))} />
                  <span className={`small ${s.seconds < 5 || s.seconds > 90 ? "warn" : "muted"}`}>{s.seconds.toFixed(1)}s</span>
                  <button className="btn ghost sm danger" onClick={() => setSpeakers((x) => x.filter((_, j) => j !== i))} aria-label={`Remove ${s.tag}`}>✕</button>
                </div>
                <Player url={`/api/uploads/${s.upload}.wav`} small label={s.tag} />
                {s.warnings.map((w) => <div key={w} className="small warn">{w}</div>)}
                <textarea className="input" dir="auto" rows={2} placeholder="Exact transcript of this reference" value={s.transcript}
                  onChange={(e) => setSpeakers((x) => x.map((y, j) => (j === i ? { ...y, transcript: e.target.value } : y)))} />
              </div>
            ))}
          </div>
        </details>

        <details className="panel" open>
          <summary>2 · Rows <span className="small faint">{rows ? `${rows.count} rows` : ""}</span></summary>
          <div className="body">
            <Drop accept=".csv,.json,.jsonl,.tsv,.txt" onFiles={loadRows}>
              CSV / JSON / JSONL with a <b>text</b> column (optional id, speaker, tags, seed)
            </Drop>
            {rows && <>
              <div className="small muted">{rows.filename}: {rows.count} rows · {Object.values(rows.pinned).reduce((a, b) => a + b, 0)} pinned ·
                {" "}{rows.with_tags} with tags · {rows.with_seed} with seeds</div>
              {rows.tag_error_count > 0 && <div className="error-box small">{rows.tag_error_count} rows have invalid tags (they will be
                listed as errors), e.g. {rows.tag_errors[0].id}: {rows.tag_errors[0].errors[0]}</div>}
              <div style={{ maxHeight: 160, overflow: "auto" }}>
                <table className="t"><thead><tr><th>id</th><th>text</th><th>spk</th></tr></thead><tbody>
                  {rows.preview.slice(0, 8).map((r) => <tr key={r.id}><td>{r.id}</td><td className="text-cell">{r.text}</td><td>{r.speaker ?? ""}</td></tr>)}
                </tbody></table>
              </div>
            </>}
          </div>
        </details>

        <details className="panel" open>
          <summary>3 · Distribution</summary>
          <div className="body">
            <Seg label="Distribution mode" value={conf.distribution.mode} onChange={(v) => set("distribution.mode", v)}
              options={[["uniform", "Uniform random"], ["balanced", "Balanced"], ["weighted", "Weighted"]]} />
            {conf.distribution.mode === "weighted" && tags.map((t) => (
              <label key={t} className="row small">{t}<input className="input" style={{ width: 80 }} type="number" min={0}
                value={conf.distribution.weights?.[t] ?? 0} onChange={(e) => set("distribution.weights", { ...conf.distribution.weights, [t]: +e.target.value })} />%</label>
            ))}
            <Num label="Distribution seed" value={conf.distribution.seed} onChange={(v) => set("distribution.seed", v)} />
            {dist && <>
              <div className="bar" aria-hidden>{tags.map((t, i) => <div key={t} style={{ width: `${(100 * (dist[t] ?? 0)) / (rows?.count || 1)}%`, background: COLORS[i % COLORS.length] }} />)}</div>
              <div className="kv">{tags.map((t, i) => <span key={t}><span style={{ color: COLORS[i % COLORS.length] }}>■</span> {t}: {dist[t]}</span>)}</div>
              <div className="small faint">Pinned rows keep their speaker in every mode.</div>
            </>}
          </div>
        </details>

        <details className="panel">
          <summary>4 · Sampling & seeds</summary>
          <div className="body">
            <div className="grid2">
              <Num label="Temperature" step={0.05} value={conf.sampling.temperature} onChange={(v) => set("sampling.temperature", v)} />
              <Num label="top_k" value={conf.sampling.top_k} onChange={(v) => set("sampling.top_k", v)} />
              <Num label="top_p (1 = off)" step={0.05} value={conf.sampling.top_p} onChange={(v) => set("sampling.top_p", v)} />
              <Num label="Takes per row (best kept)" min={1} max={5} value={conf.takes} onChange={(v) => set("takes", Math.max(1, v))} />
            </div>
            <Seg label="Seeds" value={conf.seeds.mode} onChange={(v) => set("seeds.mode", v)} options={[["base", "Base + row index"], ["random", "Random (logged)"]]} />
            {conf.seeds.mode === "base" && <Num label="Base seed" value={conf.seeds.base} onChange={(v) => set("seeds.base", v)} />}
            <div className="small faint">A row's own seed column wins. Seeds are logged per row; under load (batched requests) the same seed does not give identical audio.</div>
          </div>
        </details>

        <details className="panel">
          <summary>5 · Splitting, reference, audio</summary>
          <div className="body grid2">
            <Num label="Max part seconds" step={1} value={conf.split.max_part_s} onChange={(v) => set("split.max_part_s", v)} />
            <Num label="Join gap (s)" step={0.05} value={conf.split.gap_s} onChange={(v) => set("split.gap_s", v)} />
            <Num label="Max reference seconds (≤ 29.5)" step={0.5} max={29.5} value={conf.reference.max_s} onChange={(v) => set("reference.max_s", Math.min(29.5, v))} />
            <label className="field">Loudness target (LUFS)
              <select className="input" value={conf.audio.loudness_lufs ?? "off"} onChange={(e) => set("audio.loudness_lufs", e.target.value === "off" ? null : +e.target.value)}>
                {[-16, -18, -20, -23, -26].map((v) => <option key={v} value={v}>{v}</option>)}<option value="off">off (peak only)</option>
              </select>
            </label>
            <label className="field">Output sample rate
              <select className="input" value={conf.audio.sample_rate} onChange={(e) => set("audio.sample_rate", +e.target.value)}>
                {[24000, 16000, 22050, 44100, 48000].map((v) => <option key={v} value={v}>{v === 24000 ? "24 kHz (native)" : `${v / 1000} kHz (resampled)`}</option>)}
              </select>
            </label>
          </div>
        </details>

        <details className="panel">
          <summary>6 · Tags</summary>
          <div className="body">
            <label className="field">Tag mode
              <select className="input" value={conf.tags.mode} onChange={(e) => set("tags.mode", e.target.value)}>
                <option value="none">None: text as written, ignore the tags column</option>
                <option value="keep">Keep CSV tags (tags column + inline)</option>
                <option value="random">Random injection</option>
                <option value="strip">Strip all tags</option>
              </select>
            </label>
            {(conf.tags.mode === "keep" || conf.tags.mode === "random") && (
              <div className="field">Strength
                <Seg label="Tag strength" value={conf.tags.strength} onChange={(v) => set("tags.strength", v)}
                  options={[["light", "Light (once)"], ["strong", "Strong (every sentence)"]]} />
                {conf.tags.strength === "strong" && <div className="hint">Strong tags can make the voice drift from the reference.</div>}
              </div>
            )}
            {conf.tags.mode === "random" && <>
              <Num label="% of rows" min={0} max={100} value={conf.tags.random_pct} onChange={(v) => set("tags.random_pct", v)} />
              <div className="small muted">Allowed tag pool ({tagPool.length})</div>
              {(["emotion", "prosody", "style"] as const).map((c) => (
                <div key={c} className="row" style={{ gap: 4 }}>
                  {cfg.tags[c].filter((v) => !(c === "prosody" && v.includes("pause"))).map((v) => {
                    const t = `${c}:${v}`;
                    return <button key={t} className="opt chip" aria-pressed={tagPool.includes(t)} onClick={() => togglePool(t)}
                      style={{ color: `var(--c-${c})`, opacity: tagPool.includes(t) ? 1 : 0.45, cursor: "pointer" }}>{v.replace(/_/g, " ")}</button>;
                  })}
                </div>
              ))}
            </>}
            <label className="field">Exported transcript
              <Seg label="Exported transcript" value={conf.tags.export_text} onChange={(v) => set("tags.export_text", v)}
                options={[["keep", "Keep tags"], ["strip", "Strip tags"]]} />
            </label>
          </div>
        </details>

        <details className="panel">
          <summary>7 · QC <span className="small faint">{conf.qc.enabled ? "on" : "off"}</span></summary>
          <div className="body">
            <label className="row small"><input type="checkbox" checked={conf.qc.enabled} onChange={(e) => set("qc.enabled", e.target.checked)} /> QC enabled</label>
            <label className="row small"><input type="checkbox" checked={conf.qc.duration} disabled={!conf.qc.enabled} onChange={(e) => set("qc.duration", e.target.checked)} /> Duration sanity (vs words/s estimate from the reference's pace)</label>
            <label className="row small"><input type="checkbox" checked={conf.qc.silence} disabled={!conf.qc.enabled} onChange={(e) => set("qc.silence", e.target.checked)} /> Silence (gaps &gt; 2.5 s, near-silent takes)</label>
            <label className="row small"><input type="checkbox" checked={conf.qc.clipping} disabled={!conf.qc.enabled} onChange={(e) => set("qc.clipping", e.target.checked)} /> Clipping</label>
            <Num label="Retries with a new seed" min={0} max={5} value={conf.qc.retries} onChange={(v) => set("qc.retries", v)} />
            <label className="row small"><input type="checkbox" checked={conf.qc.include_flagged} onChange={(e) => set("qc.include_flagged", e.target.checked)} /> Include flagged rows in the zip</label>
            <div className="small faint">No ASR check: Whisper is not part of this deployment.</div>
          </div>
        </details>

        <div className="card" style={{ padding: 10, display: "grid", gap: 8 }}>
          <label className="field">Job name<input className="input" value={name} onChange={(e) => setName(e.target.value)} /></label>
          <div className="row">
            <button className="btn primary" onClick={start} disabled={!!problems.length}>Start job <span className="kbd" style={{ color: "inherit" }}>Ctrl ↵</span></button>
            <button className="btn sm" onClick={exportConfig}>Export config</button>
            <label className="btn sm">Import config<input type="file" accept=".json" className="sr-only" onChange={(e) => e.target.files && importConfig(Array.from(e.target.files))} /></label>
          </div>
          {problems.length > 0 && <div className="small faint">To start: {problems.join(" · ")}</div>}
          {msg && <div className={msg.kind === "bad" ? "error-box small" : "small ok"} role="status">{msg.text}</div>}
        </div>
      </aside>

      <main className="dev-main">
        <h2 className="section-title">Jobs</h2>
        {jobs.length === 0 && <div className="muted">No jobs yet. Set up speakers and rows on the left, then start a job.</div>}
        <div style={{ display: "grid", gap: 8 }}>
          {jobs.map((j) => {
            const c = j.counts;
            const pct = (k: string) => `${(100 * (c[k] ?? 0)) / Math.max(1, j.total)}%`;
            return (
              <div key={j.id} className="card job" aria-selected={sel === j.id} role="button" tabIndex={0}
                onClick={() => setSel(j.id)} onKeyDown={(e) => e.key === "Enter" && setSel(j.id)}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div className="row"><strong>{j.name}</strong><span className="small faint">{j.id}</span>
                    <span className={`badge ${STATUS_CLASS[j.status] ?? ""}`}>{j.status}</span></div>
                  <div className="row" onClick={(e) => e.stopPropagation()}>
                    {j.status === "running" && <button className="btn sm" onClick={() => act(j.id, "pause")}>Pause</button>}
                    {["paused", "cancelled", "error", "done"].includes(j.status) && j.finished < j.total &&
                      <button className="btn sm" onClick={() => act(j.id, "resume")}>Resume</button>}
                    {["running", "paused", "queued"].includes(j.status) && <button className="btn sm danger" onClick={() => act(j.id, "cancel")}>Cancel</button>}
                    <button className="btn sm" onClick={() => download(`/api/dev/jobs/${j.id}/download.zip?${new URLSearchParams({
                      ...(zipFlagged && { include_flagged: zipFlagged }), ...(zipExtra && { extra_format: zipExtra }) })}`)}>⭳ Zip</button>
                    <a className="btn sm ghost" href={`/api/dev/jobs/${j.id}/config`}>config</a>
                    {!["running"].includes(j.status) && <button className="btn sm ghost danger" onClick={async () => {
                      if (confirm(`Delete job ${j.name} and its audio?`)) { await api.del(`/api/dev/jobs/${j.id}`); if (sel === j.id) setSel(null); refresh(); }
                    }}>Delete</button>}
                  </div>
                </div>
                <div className="bar" aria-label={`${j.finished} of ${j.total} rows finished`}>
                  <div style={{ width: pct("done"), background: "var(--ok)" }} />
                  <div style={{ width: pct("flagged"), background: "var(--warn)" }} />
                  <div style={{ width: pct("error"), background: "var(--bad)" }} />
                </div>
                <div className="kv">
                  <span>{j.finished}/{j.total} rows</span><span className="ok">{c.done ?? 0} done</span>
                  <span className="warn">{c.flagged ?? 0} flagged</span><span className="bad">{c.error ?? 0} errors</span>
                  <span>{fmtTime(j.audio_s)} audio</span><span>RTF {j.rtf_x ? `${j.rtf_x}× realtime` : "–"}</span>
                  <span>ETA {j.status === "running" ? fmtTime(j.eta_s) : "–"}</span><span>active {fmtTime(j.active_s)}</span>
                </div>
              </div>
            );
          })}
        </div>
        {jobs.length > 0 && <div className="row small muted">
          <label className="row">Zip: flagged rows
            <select className="input" style={{ width: 170 }} value={zipFlagged} onChange={(e) => setZipFlagged(e.target.value)}>
              <option value="">as set in the job</option><option value="true">include</option><option value="false">exclude</option>
            </select></label>
          <label className="row">extra format
            <select className="input" style={{ width: 220 }} value={zipExtra} onChange={(e) => setZipExtra(e.target.value)}>
              <option value="">none</option><option value="pipe_csv">metadata_pipe.csv (qwen-train)</option>
            </select></label>
        </div>}

        {job && <>
          <h2 className="section-title" style={{ marginTop: 10 }}>{job.name}: per speaker</h2>
          <table className="t" style={{ maxWidth: 560 }}><thead><tr><th>speaker</th><th>rows</th><th>done</th><th>flagged</th></tr></thead><tbody>
            {Object.entries(job.per_speaker).map(([k, v]) => <tr key={k}><td>{k}</td><td>{v.total}</td><td>{v.done}</td><td>{v.flagged}</td></tr>)}
          </tbody></table>
          {job.errors.length > 0 && <>
            <h2 className="section-title">Error log</h2>
            <div className="log">{job.errors.slice().reverse().map((e, i) => <div key={i}>{new Date(e.t * 1000).toLocaleTimeString()} {e.msg}</div>)}</div>
          </>}
          <div className="row" style={{ justifyContent: "space-between", marginTop: 6 }}>
            <h2 className="section-title" style={{ margin: 0 }}>Samples ({samples.length}, stratified across speakers)</h2>
            <div className="row">
              <select className="input" style={{ width: 170 }} value={spkFilter} onChange={(e) => setSpkFilter(e.target.value)} aria-label="Filter by speaker">
                <option value="">All speakers</option>{Object.keys(job.per_speaker).map((k) => <option key={k}>{k}</option>)}
              </select>
              <button className="btn sm" onClick={() => { const s = sampleSeed + 1; setSampleSeed(s); loadSamples(s); }}>↻ Reshuffle</button>
            </div>
          </div>
          <div className="samples">
            {samples.map((s) => {
              const rtl = /[؀-ۿ]/.test(s.text);
              return (
                <div key={`${s.idx}-${s.audio_url}`} className="card sample">
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <span className="small"><b>{s.speaker}</b> · {s.id}</span>
                    <span className={`badge ${s.status === "done" ? "ok" : "warn"}`} title={s.qc?.reasons?.join("\n")}>{s.status === "done" ? "QC pass" : "flagged"}</span>
                  </div>
                  <Player url={s.audio_url} small label={s.id} />
                  <div className={`txt ${rtl ? "rtl" : ""}`} dir="auto">{s.text}</div>
                  <div className="kv"><span>seed {s.seed}</span><span>{s.seconds?.toFixed(1)}s</span>{s.tags && <span>{s.tags}</span>}
                    <span>attempts {s.attempts}</span>{s.qc?.reasons?.length > 0 && <span className="warn">{s.qc.reasons[0]}</span>}</div>
                  <button className="btn sm" disabled={regen === s.idx} onClick={async () => {
                    setRegen(s.idx);
                    try { await api.post(`/api/dev/jobs/${sel}/rows/${s.idx}/regenerate`); loadSamples(); refresh(); }
                    catch (e) { setMsg({ kind: "bad", text: (e as Error).message }); }
                    setRegen(null);
                  }}>{regen === s.idx ? "Regenerating…" : "↻ Regenerate row"}</button>
                </div>
              );
            })}
          </div>
        </>}
      </main>
    </div>
  );
}
