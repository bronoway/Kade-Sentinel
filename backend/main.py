"""Tray Security API (FastAPI + SQLite).

Tray status is DERIVED from the tables on every read, never stored:
    BREACH  - the tray has at least one unacknowledged alert
    GRANTED - the storekeeper granted access and it has not expired
    SAFE    - otherwise (armed)

Also serves the built React dashboard, so one process / one port / one tunnel runs everything.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from database import get_db, init_db, utc_iso

ALERT_MESSAGE = "UNAUTHORIZED ACCESS"
DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Tray Security", lifespan=lifespan)
api = APIRouter(prefix="/api")


def require_tray(con, tray_id: int) -> None:
    if con.execute("SELECT 1 FROM trays WHERE id = ?", (tray_id,)).fetchone() is None:
        raise HTTPException(404, "Tray not found")


def is_granted(con, tray_id: int) -> bool:
    return con.execute(
        "SELECT 1 FROM permissions WHERE tray_id = ? AND active = 1 AND expires_at > ?",
        (tray_id, utc_iso()),
    ).fetchone() is not None


def record_alert(con, tray_id: int) -> None:
    con.execute(
        "INSERT INTO alerts (tray_id, message, created_at) VALUES (?, ?, ?)",
        (tray_id, ALERT_MESSAGE, utc_iso()),
    )


# ---------- Dashboard ----------

@api.get("/trays")
def list_trays(con=Depends(get_db)):
    rows = con.execute(
        """
        SELECT t.id, t.name, t.location,
               EXISTS (SELECT 1 FROM alerts a
                       WHERE a.tray_id = t.id AND a.acknowledged = 0) AS breach,
               (SELECT MAX(p.expires_at) FROM permissions p
                WHERE p.tray_id = t.id AND p.active = 1 AND p.expires_at > ?) AS granted_until
        FROM trays t
        ORDER BY t.id
        """,
        (utc_iso(),),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "location": r["location"],
            "status": "BREACH" if r["breach"] else "GRANTED" if r["granted_until"] else "SAFE",
            "granted_until": r["granted_until"],  # UTC; null unless GRANTED/BREACH-with-grant
        }
        for r in rows
    ]


@api.get("/alerts")
def list_alerts(limit: int = Query(50, ge=1, le=500), con=Depends(get_db)):
    rows = con.execute(
        "SELECT id, tray_id, message, created_at, acknowledged FROM alerts ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


@api.post("/trays/{tray_id}/grant")
def grant(tray_id: int, minutes: int = Query(2, ge=1, le=60), con=Depends(get_db)):
    require_tray(con, tray_id)
    expires = utc_iso(minutes)
    with con:
        con.execute(
            "INSERT INTO permissions (tray_id, granted_at, expires_at) VALUES (?, ?, ?)",
            (tray_id, utc_iso(), expires),
        )
    return {"ok": True, "expires_at": expires}


@api.post("/trays/{tray_id}/reset")
def reset(tray_id: int, con=Depends(get_db)):
    """Acknowledge alerts (history is kept) and cancel any open grant, re-arming the tray."""
    require_tray(con, tray_id)
    with con:
        con.execute("UPDATE alerts SET acknowledged = 1 WHERE tray_id = ? AND acknowledged = 0", (tray_id,))
        con.execute("UPDATE permissions SET active = 0 WHERE tray_id = ? AND active = 1", (tray_id,))
    return {"ok": True}


@api.post("/trays/{tray_id}/alert")
def simulate_theft(tray_id: int, con=Depends(get_db)):
    """Dashboard demo button: raise an alert regardless of any grant."""
    require_tray(con, tray_id)
    with con:
        record_alert(con, tray_id)
    return {"ok": True}


# ---------- ESP32 ----------

@api.post("/trays/{tray_id}/motion")
def motion(tray_id: int, con=Depends(get_db)):
    """Called by the PIR device on motion. One round trip: check the grant and, if none, log the alert.

    Returns {"granted": true|false}. The firmware matches this exact compact JSON.
    """
    require_tray(con, tray_id)
    granted = is_granted(con, tray_id)
    if not granted:
        with con:
            record_alert(con, tray_id)
    return {"granted": granted}


app.include_router(api)

# Must be registered last so it never shadows /api. Absent until `npm run build`; API still works.
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="dashboard")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
