import "@fontsource/inter/400.css";
import "@fontsource/inter/600.css";
import "@fontsource/noto-nastaliq-urdu/400.css";
import "@fontsource/noto-naskh-arabic/400.css";
import "./styles.css";
import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, type Config } from "./api";
import Dev from "./pages/Dev";
import Studio from "./pages/Studio";

function useTheme(): [string, () => void] {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem("theme") || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"); }
    catch { return "dark"; }
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("theme", theme); } catch { /* storage blocked */ }
  }, [theme]);
  return [theme, () => setTheme(theme === "dark" ? "light" : "dark")];
}

function App() {
  const page = location.pathname.startsWith("/dev") ? "dev" : "studio";
  const [cfg, setCfg] = useState<Config | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [err, setErr] = useState("");
  const [theme, toggle] = useTheme();
  useEffect(() => { api.get("/api/config").then(setCfg).catch((e) => setErr(String(e))); }, []);
  useEffect(() => {
    const poll = () => api.get("/api/status").then(setStatus).catch(() => setStatus({ engine: false }));
    poll();
    const t = setInterval(poll, 5000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => { document.title = page === "dev" ? "Higgs Studio · Dataset" : "Higgs Studio"; }, [page]);
  const q = status?.queue;
  return (
    <>
      <header className="topbar">
        <div className="brand"><span className="logo" aria-hidden />Higgs Studio</div>
        <nav className="nav row" aria-label="Consoles">
          <a href="/studio" className={page === "studio" ? "active" : ""}>Studio</a>
          <a href="/dev" className={page === "dev" ? "active" : ""}>Dataset (dev)</a>
        </nav>
        <span className="spacer" />
        <span className="pill" title={status?.engine_url}>
          <span className={`dot ${status == null ? "" : status.engine ? "ok" : "bad"}`} />
          {status == null ? "connecting…" : status.engine ? "engine ready" : "engine offline"}
          {q && ` · ${q.inflight.customer + q.inflight.dev} running · ${q.waiting.customer + q.waiting.dev} queued`}
        </span>
        <span className="pill">AI-generated speech</span>
        <button className="btn ghost sm" onClick={toggle} aria-label="Toggle dark / light theme">{theme === "dark" ? "☀" : "☾"}</button>
      </header>
      {err && <div className="error-box" style={{ margin: 16 }}>{err}</div>}
      {cfg && (page === "dev" ? <Dev cfg={cfg} /> : <Studio cfg={cfg} />)}
    </>
  );
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
