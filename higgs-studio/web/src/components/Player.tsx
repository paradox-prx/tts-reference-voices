import { useEffect, useRef, useState } from "react";

const cache = new Map<string, number[]>();

async function computePeaks(url: string, n = 300): Promise<number[]> {
  if (cache.has(url)) return cache.get(url)!;
  const buf = await (await fetch(url)).arrayBuffer();
  const ctx = new OfflineAudioContext(1, 1, 24000);
  const audio = await ctx.decodeAudioData(buf);
  const d = audio.getChannelData(0);
  const k = Math.max(1, Math.floor(d.length / n));
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    let m = 0;
    for (let j = i * k; j < Math.min(d.length, (i + 1) * k); j++) m = Math.max(m, Math.abs(d[j]));
    out.push(m);
  }
  cache.set(url, out);
  return out;
}

export function drawWave(canvas: HTMLCanvasElement, peaks: number[], progress: number, color: string, played: string) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (!w || !h) return;
  canvas.width = w * dpr; canvas.height = h * dpr;
  const g = canvas.getContext("2d")!;
  g.scale(dpr, dpr);
  g.clearRect(0, 0, w, h);
  const n = peaks.length || 1, bw = w / n, max = Math.max(0.05, ...peaks);
  for (let i = 0; i < n; i++) {
    const v = (peaks[i] ?? 0) / max;
    const bh = Math.max(1.5, v * (h - 4));
    g.fillStyle = i / n < progress ? played : color;
    g.fillRect(i * bw + bw * 0.15, (h - bh) / 2, Math.max(1, bw * 0.7), bh);
  }
}

const css = (v: string) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

/** HTMLAudio player with a clickable waveform. peaks are loaded lazily (decoded from the file) unless given. */
export default function Player({ url, peaks: given, small, label, onPlay }:
  { url: string; peaks?: number[]; small?: boolean; label?: string; onPlay?: () => void }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [peaks, setPeaks] = useState<number[] | null>(given ?? null);
  const [playing, setPlaying] = useState(false);
  const [t, setT] = useState(0);
  const [dur, setDur] = useState(0);
  const visible = useRef(false);

  useEffect(() => { if (given) setPeaks(given); }, [given]);
  useEffect(() => {
    if (given || !canvas.current) return;
    const io = new IntersectionObserver((es) => {
      if (es[0].isIntersecting && !visible.current) {
        visible.current = true;
        computePeaks(url).then(setPeaks).catch(() => setPeaks([]));
      }
    });
    io.observe(canvas.current);
    return () => io.disconnect();
  }, [url, given]);
  useEffect(() => {
    if (canvas.current && peaks) drawWave(canvas.current, peaks, dur ? t / dur : 0, css("--line2"), css("--accent"));
  }, [peaks, t, dur]);
  useEffect(() => {
    const on = () => canvas.current && peaks && drawWave(canvas.current, peaks, dur ? t / dur : 0, css("--line2"), css("--accent"));
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  });

  const toggle = () => {
    const a = audioRef.current!;
    if (a.paused) { document.querySelectorAll("audio").forEach((o) => o !== a && o.pause()); a.play(); onPlay?.(); }
    else a.pause();
  };
  const seek = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const a = audioRef.current!, r = e.currentTarget.getBoundingClientRect();
    if (!a.duration) return;
    let f = (e.clientX - r.left) / r.width;
    a.currentTime = Math.max(0, Math.min(1, f)) * a.duration;
  };
  return (
    <div className="player">
      <audio ref={audioRef} src={url} preload="metadata" onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)} onTimeUpdate={(e) => setT(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) => setDur(e.currentTarget.duration)} />
      <button className={`play ${small ? "sm" : ""}`} onClick={toggle} aria-label={playing ? `Pause ${label ?? ""}` : `Play ${label ?? ""}`}>
        {playing ? "❚❚" : "▶"}
      </button>
      <canvas ref={canvas} onClick={seek} role="slider" aria-label="Seek" aria-valuemin={0} aria-valuemax={Math.round(dur)}
        aria-valuenow={Math.round(t)} tabIndex={0}
        onKeyDown={(e) => { const a = audioRef.current!; if (e.key === "ArrowRight") a.currentTime += 2; if (e.key === "ArrowLeft") a.currentTime -= 2; if (e.key === " ") { e.preventDefault(); toggle(); } }} />
      <span className="time">{t.toFixed(1)} / {dur ? dur.toFixed(1) : "–"}s</span>
    </div>
  );
}
