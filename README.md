# Retail Store Item Tray Security

A small PIR-based system that stops walk-away theft from open item trays in small shops. The storekeeper **grants** a customer temporary access to a tray from a web dashboard; if anyone reaches that tray **without** a grant, the tray's ESP32 sounds a buzzer and the dashboard raises a breach alert.

```
 PIR sensor ─▶ ESP32 ──HTTPS──▶ FastAPI backend ◀──HTTP── React dashboard (storekeeper)
 (motion)     (buzzer, LEDs)     └─ SQLite (trays.db)
```

One process serves everything: FastAPI exposes `/api/*` **and** the built dashboard at `/`, so you need one port and (for the ESP32) one tunnel.

## Folder layout

| Path | What it is |
|---|---|
| `backend/main.py` | API routes + status logic; also serves `frontend/dist` |
| `backend/database.py` | SQLite schema, per-request connection, UTC timestamp helper |
| `frontend/src/App.jsx` | The whole dashboard (single component file) |
| `frontend/vite.config.js` | Dev-only proxy of `/api` → `localhost:8000` |
| `wokwi/sketch.ino`, `diagram.json` | ESP32 firmware and the Wokwi circuit |

## How it behaves

### Tray status (derived, never stored)
Every `GET /api/trays` recomputes status from the tables, so it can never get out of sync:

| Status | Condition | Dashboard |
|---|---|---|
| **BREACH** | at least one *unacknowledged* alert exists for the tray | red, pulsing |
| **GRANTED** | an active, unexpired permission exists | amber, shows "access until HH:MM:SS" |
| **SAFE** | neither | green, tray is armed |

BREACH wins over GRANTED. A grant expires by itself; a breach stays until the storekeeper clicks **Acknowledge & re-arm**.

### Storekeeper actions
- **Grant access (2 min)** – inserts a permission row expiring in 2 minutes (the backend accepts 1–60; 2 is a demo assumption set in `App.jsx` as `GRANT_MINUTES`).
- **Acknowledge & re-arm** – marks open alerts acknowledged (history is kept) and cancels any open grant.
- **Simulate theft (demo)** – raises an alert without hardware, regardless of grants. Clearly labelled as a demo control.

### The ESP32 (firmware)
1. The PIR output goes HIGH → the sketch reacts once per **rising edge** (one check per motion pulse, not one per loop).
2. It sends a single `POST /api/trays/1/motion`. The backend checks for a live grant and, if there is none, writes the alert itself, then replies `{"granted": true|false}`.
3. **Granted** → green LED for 3 s. **Not granted** → red LED for 3 s and a 2.5 kHz buzzer for 1 s; the alert is already in the database, so the dashboard turns red within its 2-second poll.
4. **Fail-secure:** if the backend can't be reached (no Wi-Fi, tunnel down, timeout), the device *treats the motion as unauthorised*, sounds the local alarm and retries delivering the alert every 10 s until it succeeds. A security device should not go silent when the network drops.

Timings (`INDICATOR_MS`, `ALARM_MS`, `RETRY_MS`, `HTTP_TIMEOUT_MS`) are constants at the top of the sketch.

### Wiring (matches `diagram.json`)
| ESP32 | Part |
|---|---|
| VIN / GND | PIR VCC / GND |
| D27 | PIR OUT |
| D26 | Buzzer (+), other leg to GND |
| D25 → 220 Ω | Red LED (unauthorised) → GND |
| D33 → 220 Ω | Green LED (authorised) → GND |

## API

All under `/api`. Interactive docs: `http://localhost:8000/docs`.

| Method & path | Used by | Purpose |
|---|---|---|
| `GET /trays` | dashboard | Trays with derived `status` and `granted_until` (UTC) |
| `GET /alerts?limit=50` | dashboard | Newest alerts first (default 50, max 500) |
| `POST /trays/{id}/grant?minutes=2` | dashboard | Grant access (1–60 min) |
| `POST /trays/{id}/reset` | dashboard | Acknowledge alerts + cancel grants |
| `POST /trays/{id}/alert` | dashboard (demo) | Force an alert |
| `POST /trays/{id}/motion` | ESP32 | Check grant, log alert if none → `{"granted": bool}` |

An unknown tray id returns `404`; out-of-range `minutes` returns `422`.

### Database (`backend/trays.db`, created on first run)
- `trays(id, name, location)` – seeded with "Tray 1 - Biscuits".
- `permissions(id, tray_id, granted_at, expires_at, active)`
- `alerts(id, tray_id, message, created_at, acknowledged)` – the time-stamped alert history the plan asks for.

All timestamps are **UTC ISO-8601** (`2026-11-18T09:15:56Z`); the dashboard converts them to the viewer's local time.

## Running it

**Requirements:** Python 3.10+, Node 20.19+ or 22.12+ (Vite 8). Node is only needed to rebuild the dashboard.

```bash
# 1. Backend (serves API + dashboard)
cd backend
pip install -r requirements.txt
python main.py                      # or: uvicorn main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000

# 2. Frontend – only when you change it
cd frontend
npm ci
npm run build                       # output in frontend/dist, picked up by the backend
npm run dev                         # optional hot-reload on :5173, proxies /api to :8000
```

**Connecting the Wokwi/ESP32 device:** expose the backend with a tunnel, e.g. `cloudflared tunnel --url http://localhost:8000`, paste the printed `https://….trycloudflare.com` URL into `BASE_URL` in `sketch.ino` (no trailing slash), and run the simulation. A quick tunnel gets a new URL each restart, so update the sketch each time. On real hardware over a hotspot, use `http://<laptop-ip>:8000` instead (the sketch picks TLS or plain HTTP from the URL prefix) and set your Wi-Fi SSID/password in `setup()`.

**Reset the demo data:** stop the backend and delete `backend/trays.db`.

## Known limitations (worth stating to a panel)
- **No authentication.** Anyone who has the URL can grant access or clear alerts. Fine for a lab demo; a real deployment needs at least a storekeeper login and a device key on `/motion`. A public tunnel makes this more important, not less.
- **Demo-grade TLS on the device:** `setInsecure()` skips certificate validation. Pin a CA certificate before real use.
- **No item/stock inventory yet.** The project plan envisions a UI listing available items; the current code tracks trays, grants and alerts only.
- **One PIR per tray, one tray in the seed data.** Adding trays means inserting into `trays` and flashing another device with a different `TRAY_ID`.
- **PIR limits:** it detects motion/heat in its cone, not *what* was taken, and `delayTime`/`inhibitTime` (Wokwi simulation values 5 s / 1.2 s) control how often it can retrigger. Those values are simulation settings, not measured figures.
- Polling every 2 s means the dashboard lags the device by up to ~2 s.
