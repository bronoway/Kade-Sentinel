# Demo Day Guide (Thursday 19 Nov, panels from 8:30 AM)

Keep this open on a second screen. Everything below is in the order you do it.

---

## A. Tonight (do this once, 10 minutes)

- [ ] Unzip the latest `kade-sentinel.zip` into a **fresh** folder. Open it in VS Code.
- [ ] Run the system once end to end (Section B) and make sure it works.
- [ ] Charge the laptop. Plug the charger into your bag.
- [ ] Windows: Settings > Power > set **Sleep to Never** while plugged in.
- [ ] Push the code to GitHub (private repo) as a backup.
- [ ] Open your Wokwi project and keep it signed in. Save a copy of the final `sketch.ino` and `diagram.json` on your laptop too.

## B. Start-up, in this order (5 minutes, 10 minutes before the panel arrives)

You will use **3 windows**: two terminals and a browser.

**Step 1. Start the app (Terminal 1)**
```
cd tray-security\backend
python main.py
```
Wait for `Uvicorn running on http://0.0.0.0:8000`.
Open **http://localhost:8000**. You should see Tray 1 in green (**Safe**).

**Step 2. Start the tunnel (Terminal 2)**
```
cloudflared tunnel --url http://localhost:8000
```
It prints a link like `https://something-random.trycloudflare.com`. Copy it.
> The link is **new every time**. Do not reuse last night's.

**Step 3. Give the link to the device**
1. Open the Wokwi project. Open `sketch.ino`.
2. Replace the address in `BASE_URL` with the new link. **No slash at the end.**
3. Press the green **Play** button.

**Step 4. Confirm it is connected**
In the Wokwi serial monitor you must see: `WiFi connected. Ready for motion.`

**Step 5. Quick test (30 seconds)**
1. Click the PIR sensor in Wokwi, with no permission granted. The red LED and buzzer fire, and the dashboard turns red.
2. On the dashboard click **Acknowledge & re-arm**. It goes green.
3. Click **Grant access for 2 min**, then click the PIR again. The green LED lights, with no alarm and no new alert.
4. Click **Acknowledge & re-arm** once more so the demo starts clean.

If all four worked, you are ready.

---

## C. The demo (about 2 minutes)

Say the problem first, then show it:

1. **The problem.** "Small shops in Sri Lanka keep trays open on the pavement. The shopkeeper is inside and CCTV is rarely watched, so items walk away unnoticed."
2. **Armed (green).** "Each tray has a PIR sensor. With no permission, it is armed."
3. **Theft.** Click the PIR with no permission. "Someone reaches in without permission. The buzzer sounds and the shopkeeper's screen turns red with a time-stamped alert."
4. **Re-arm.** Click **Acknowledge & re-arm**. "The shopkeeper checks, then re-arms. Alert history is kept."
5. **Permission.** "A customer hands over a list. The shopkeeper grants 2 minutes of access." Click **Grant access**. Show the countdown.
6. **Authorised.** Click the PIR. "Green light, no alarm, no false alert."
7. **Limits (be honest, panels like this).** "No login yet, one tray in the demo, and it does not know *what* was taken. Next step: more trays, stock tracking, a login."

**Number honesty (the brief's golden rule):**
- The **2-minute grant** is an assumption (a labelled setting), not measured data.
- The PIR timings are **simulation settings** from Wokwi, not real measurements.
- The **Simulate theft (demo)** button is labelled as a demo control.
- Alert times are real, from the database.

---

## D. If something goes wrong

| What you see | Do this |
|---|---|
| Dashboard won't open | Terminal 1 not running. Run `python main.py` again from the `backend` folder. |
| `No module named fastapi` | `python -m pip install -r requirements.txt` in `backend`, then run again. |
| Wokwi shows `HTTP status: -1` or "UNKNOWN" | The tunnel link is old or mistyped. Copy the **current** link from Terminal 2 into `BASE_URL` and press Play again. |
| Tunnel keeps failing or Wi-Fi is bad | Use the **Simulate theft (demo)** button on the dashboard. It shows the same alert flow without hardware. Say so openly. |
| Wokwi stuck on "Connecting" | Stop and press Play again. If it still fails, check the venue Wi-Fi works. A phone hotspot is the backup. |
| Dashboard looks old/wrong | Hard refresh: **Ctrl + Shift + R**. |
| Alert log full of old test rows | Stop Terminal 1, delete `backend\trays.db`, run `python main.py` again. |
| Tunnel dropped mid-demo | Restart it, get the new link, update `BASE_URL`, press Play. About 1 minute. |

**Fail-secure behaviour (a talking point):** if the device cannot reach the server, it sounds the local alarm anyway and keeps retrying to send the alert.

---

## E. Pack-up
- Press Ctrl+C in both terminals.
- Do not delete `trays.db` if you want to keep the demo history.
- Submit all deliverables to the submission folder **before 8:30 AM** (software, hardware, business case, field visit photos, video).
