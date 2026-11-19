import { useCallback, useEffect, useState } from "react";

const API = "/api";
const POLL_MS = 2000;
const GRANT_MINUTES = 2;

const STATUS = {
  SAFE: { label: "Safe", hint: "Armed. Any motion will sound the alarm." },
  GRANTED: { label: "Access granted", hint: "Customer may take items." },
  BREACH: { label: "Breach", hint: "Someone reached this tray without permission." },
};

const clock = (iso) => new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" });
const day = (iso) => new Date(iso).toLocaleDateString([], { day: "numeric", month: "short" });
const mmss = (secs) => `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;

async function request(path, options) {
  const res = await fetch(`${API}${path}`, options);
  if (!res.ok) throw new Error(`${options?.method ?? "GET"} ${path} failed (${res.status})`);
  return res.json();
}

export default function App() {
  const [trays, setTrays] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [online, setOnline] = useState(true);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [now, setNow] = useState(() => Date.now()); // ticks every second for the grant countdown

  const refresh = useCallback(async (signal) => {
    try {
      const [t, a] = await Promise.all([request("/trays", { signal }), request("/alerts", { signal })]);
      setTrays(t);
      setAlerts(a);
      setUpdatedAt(new Date());
      setOnline(true);
      setError(null);
    } catch (e) {
      if (e.name !== "AbortError") setOnline(false);
    }
  }, []);

  useEffect(() => {
    const ctrl = new AbortController();
    const tick = () => document.visibilityState === "visible" && refresh(ctrl.signal);
    tick();
    const poll = setInterval(tick, POLL_MS);
    const clockTick = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      clearInterval(poll);
      clearInterval(clockTick);
      ctrl.abort();
    };
  }, [refresh]);

  const act = async (path) => {
    try {
      await request(path, { method: "POST" });
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  };

  const trayName = (id) => trays.find((t) => t.id === id)?.name ?? `Tray ${id}`;
  const breached = trays.filter((t) => t.status === "BREACH");
  const count = (s) => trays.filter((t) => t.status === s).length;

  return (
    <main>
      <header className="top">
        <div>
          <h1 lang="si-LK">කඩේ Sentinel</h1>
          <p className="summary">
            {trays.length} {trays.length === 1 ? "tray" : "trays"} monitored: {count("SAFE")} safe, {count("GRANTED")} granted,{" "}
            {count("BREACH")} breached
          </p>
        </div>
        <p className={`live ${online ? "on" : "off"}`} role="status">
          <span className="dot" aria-hidden="true" />
          {online
            ? updatedAt ? `Live, updated ${updatedAt.toLocaleTimeString()}` : "Connecting..."
            : "Server unreachable. Retrying..."}
        </p>
      </header>

      {error && <p className="notice" role="alert">{error}</p>}

      {breached.length > 0 && (
        <p className="banner" role="alert">
          Unauthorised access at {breached.map((t) => t.name).join(", ")}. Check the shop floor, then acknowledge.
        </p>
      )}

      <div className="trays">
        {trays.map((t) => {
          const { label, hint } = STATUS[t.status];
          const remaining = t.granted_until ? Math.max(0, Math.round((new Date(t.granted_until) - now) / 1000)) : 0;
          const pct = Math.min(100, (remaining / (GRANT_MINUTES * 60)) * 100);
          return (
            <article key={t.id} className={`tray ${t.status}`}>
              <div className="plate">
                <span>{label}</span>
              </div>
              <div className="body">
                <h2>{t.name}</h2>
                {t.location && <p className="where">{t.location}</p>}
                <p className="hint">{hint}</p>

                {t.status === "GRANTED" && remaining > 0 && (
                  <div className="timer">
                    <p>
                      Access ends in <strong>{mmss(remaining)}</strong> (at {clock(t.granted_until)})
                    </p>
                    <div className="bar" aria-hidden="true"><i style={{ width: `${pct}%` }} /></div>
                  </div>
                )}

                <div className="actions">
                  <button
                    className={t.status === "BREACH" ? "" : "primary"}
                    onClick={() => act(`/trays/${t.id}/grant?minutes=${GRANT_MINUTES}`)}
                  >
                    Grant access for {GRANT_MINUTES} min
                  </button>
                  <button
                    className={t.status === "BREACH" ? "primary" : ""}
                    onClick={() => act(`/trays/${t.id}/reset`)}
                  >
                    Acknowledge &amp; re-arm
                  </button>
                  <button className="demo" onClick={() => act(`/trays/${t.id}/alert`)}>
                    Simulate theft (demo)
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      <section className="log">
        <h2>Alert log</h2>
        {alerts.length === 0 ? (
          <p className="empty">No alerts yet. Alerts appear here when a tray is reached without a grant.</p>
        ) : (
          <ul>
            {alerts.map((a) => (
              <li key={a.id}>
                <time dateTime={a.created_at}>
                  <strong>{clock(a.created_at)}</strong>
                  <small>{day(a.created_at)}</small>
                </time>
                <span className="what">
                  {trayName(a.tray_id)}
                  <small>{a.message}</small>
                </span>
                <span className={`chip ${a.acknowledged ? "done" : "open"}`}>{a.acknowledged ? "Acknowledged" : "Open"}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="note">Times are shown in your local time. Latest 50 alerts.</p>
      </section>
    </main>
  );
}
