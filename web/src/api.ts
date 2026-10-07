export type Delivery = { speed: string; expressiveness: string; pitch: string; emotion: string; strength: string };
export type Voice = {
  id: string; folder: string; name: string; role: string; language: string; language_name: string; gender: string;
  description: string; delivery: Delivery; hidden: boolean; public_figure: boolean; preview_url: string;
  transcript_ok: boolean; warnings: string[]; source_seconds: number;
};
export type Config = {
  tags: Record<string, string[]>; sfx_sounds: Record<string, string>; events: string[];
  languages: Record<string, { name: string; dir: string }>;
  delivery_presets: Record<string, Delivery & { label: string }>;
  defaults: any; limits: any; speeds: string[];
};
export type QC = { seconds: number; expected_s: number; pace_ratio: number; max_gap_s: number; clip_frac: number;
  ok: boolean; reasons: string[] };

export class ApiError extends Error {
  status: number; detail: any;
  constructor(status: number, detail: any) {
    super(typeof detail === "string" ? detail : detail?.tag_errors ? detail.tag_errors.join("; ") : JSON.stringify(detail));
    this.status = status; this.detail = detail;
  }
}

async function handle(r: Response) {
  if (!r.ok) {
    let d: any = r.statusText;
    try { d = (await r.json()).detail ?? d; } catch { /* not json */ }
    throw new ApiError(r.status, d);
  }
  return r.json();
}

export const api = {
  get: (url: string) => fetch(url).then(handle),
  post: (url: string, body?: any) =>
    fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) }).then(handle),
  del: (url: string) => fetch(url, { method: "DELETE" }).then(handle),
  upload: (url: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch(url, { method: "POST", body: fd }).then(handle);
  },
};

export function fmtTime(s: number | null | undefined) {
  if (s == null || !isFinite(s)) return "–";
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60), r = Math.round(s % 60);
  if (m < 60) return `${m}m ${r}s`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

export function download(url: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  a.remove();
}
