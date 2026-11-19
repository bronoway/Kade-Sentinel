# Kade Sentinel (කඩේ Sentinel)

A simple anti-theft system for small shops that keep their items on open trays.

In a lot of small shops in Sri Lanka the goods are put out on trays near the door and the shopkeeper is busy at the back. Someone can just grab something and walk off. CCTV is expensive and it only records the theft after it happened, so we made something cheaper that actually makes a noise when it happens.

## How it works

1. The shopkeeper opens the web dashboard and gives a customer access to a tray (2 minutes).
2. The customer picks their items.
3. A PIR motion sensor on the tray is connected to an ESP32. When it sees a hand it asks the backend if access was given.
4. If not, the buzzer and the red LED go off and the dashboard turns red. The alert is saved with a time.

On the dashboard each tray is in one of three states:

- **SAFE** (green): nothing is happening, the tray is armed
- **GRANTED** (yellow): the shopkeeper allowed access, shows when it ends
- **BREACH** (red): someone reached in without permission

If a tray has a breach and a grant at the same time, it shows BREACH. A grant runs out by itself, but a breach stays red until the shopkeeper clicks "Acknowledge & re-arm".

## What's in the project

```
backend/    FastAPI + SQLite (main.py, database.py)
frontend/   React dashboard made with Vite (src/App.jsx)
wokwi/      ESP32 code (sketch.ino) and the circuit (diagram.json)
```

The backend also serves the built dashboard, so you only need to run one thing.

## Running it

You need Python 3.10+ and Node (only if you want to change the dashboard).

Backend:

```
cd backend
pip install -r requirements.txt
python main.py
```

Then open http://localhost:8000

Frontend (only if you edit it):

```
cd frontend
npm ci
npm run build
```

The build goes into `frontend/dist` and the backend picks it up. You can also use `npm run dev` while working on it.

To reset all the data, stop the backend and delete `backend/trays.db`.

## ESP32 / Wokwi

The simulation runs online so it can't reach `localhost`. We use a tunnel:

```
cloudflared tunnel --url http://localhost:8000
```

Copy the `https://....trycloudflare.com` link into `BASE_URL` in `sketch.ino` and start the simulation. The link changes every time you restart the tunnel, so you have to paste it again.

For real hardware, use `http://<your-laptop-ip>:8000` as the `BASE_URL` and put your own Wi-Fi name and password in `setup()`.

If the ESP32 can't reach the backend (Wi-Fi is down, etc.) it still sounds the alarm and keeps trying to send the alert every 10 seconds. We did this on purpose so the alarm doesn't just go quiet when the internet drops.

### Wiring

| ESP32 pin | Connected to |
|---|---|
| VIN, GND | PIR sensor power |
| D27 | PIR output |
| D26 | Buzzer |
| D25 (with 220 ohm) | Red LED |
| D33 (with 220 ohm) | Green LED |

## API

Everything is under `/api`. There are automatic docs at http://localhost:8000/docs

| Endpoint | Used by | What it does |
|---|---|---|
| `GET /trays` | dashboard | list trays with their status |
| `GET /alerts` | dashboard | alert history, newest first |
| `POST /trays/{id}/grant` | dashboard | give access for a few minutes |
| `POST /trays/{id}/reset` | dashboard | clear alerts and cancel access |
| `POST /trays/{id}/alert` | dashboard / ESP32 | add an alert (the dashboard uses it for the "Simulate theft" demo button, the ESP32 uses it to resend alerts) |
| `POST /trays/{id}/motion` | ESP32 | checks for access, saves an alert if there is none |

The database has three tables: `trays`, `permissions` and `alerts`. Times are saved in UTC and the dashboard shows them in your local time.

## Limitations

- There is no login. Anyone with the link can grant access or clear alerts, so it's only for demo use right now.
- The ESP32 code skips the HTTPS certificate check (`setInsecure()`) to keep the demo simple.
- It only knows about trays, access and alerts. There is no list of items or stock.
- Only one tray is added by default. For more, add them to the `trays` table and flash another ESP32 with a different `TRAY_ID`.
- The PIR sensor detects movement, not what was taken.
- The dashboard checks for updates every 2 seconds, so it can be a little behind.
