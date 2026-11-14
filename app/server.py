"""HTTP API + live event stream (Server-Sent Events) for the LookThrough UI."""
from __future__ import annotations

import asyncio
import os
import json
import queue
import threading
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import LookThrough
from .cache import ledger
from .config import ROOT, RUNS_DIR, TELEM_API_KEY, TELEM_BASE_URL

app = FastAPI(title="LookThrough")
READONLY = os.environ.get("LOOKTHROUGH_READONLY") == "1"          # public tunnel: replays only, no spend
PUBLIC_LIVE = os.environ.get("LOOKTHROUGH_PUBLIC_LIVE") == "1"     # public tunnel: guarded live runs
PUBLIC_MAX_FRESH_PER_HOUR = int(os.environ.get("LOOKTHROUGH_PUBLIC_MAX_PER_HOUR", "6"))
_public_lock = threading.Lock()
_public_stamps: list[float] = []
app.mount("/media", StaticFiles(directory=ROOT / "media"), name="media")


def _public_refusal() -> str | None:
    """Why a public live run would be refused right now (None = allowed)."""
    if not PUBLIC_LIVE:
        return None
    now = time.time()
    _public_stamps[:] = [t for t in _public_stamps if now - t < 3600]
    if len(_public_stamps) >= PUBLIC_MAX_FRESH_PER_HOUR:
        return "Live slots for this hour are used up. Try a saved company like DeepSeek or Manus AI."
    if _public_lock.locked():
        return "Another live run is in progress. Try again in about a minute."
    return None
_monitors: dict[str, dict] = {}


def _sse(evt: dict) -> str:
    return f"data: {json.dumps(evt, default=str)}\n\n"


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/story")
def story():
    return FileResponse(ROOT / "web" / "story.html")


@app.get("/compare")
def compare():
    return FileResponse(ROOT / "web" / "compare.html")


@app.get("/pitch")
def pitch():
    return FileResponse(ROOT / "web" / "pitch.html")


@app.get("/api/health")
def health():
    status = {"telem": "unknown", "llm": "claude-cli", "readonly": READONLY, "public": PUBLIC_LIVE}
    if READONLY:
        status["telem"] = "ok (replay mode)"
        return status
    try:
        from telem import Telem
        Telem(base_url=TELEM_BASE_URL, api_key=TELEM_API_KEY, timeout=15).fetch(["https://example.com"], tier="minimalist")
        status["telem"] = "ok"
    except Exception as e:  # noqa: BLE001
        status["telem"] = f"error: {str(e)[:120]}"
    return status


@app.get("/api/run")
async def run(root: str, policy: str = "", kind: str = "company", depth: int = 2, nodes: int = 6,
              budget: float = 0.75, offline: bool = False, as_of: str = ""):
    if READONLY:
        raise HTTPException(403, "Public demo is replay-only. Pick a saved run.")
    if PUBLIC_LIVE:
        depth, nodes, budget = min(depth, 1), min(nodes, 2), min(budget, 0.5)
        why = _public_refusal()
        if why or not _public_lock.acquire(blocking=False):
            raise HTTPException(429, why or "Another live run is in progress.")
    q: queue.Queue = queue.Queue()

    def work():
        try:
            r = LookThrough(root, policy=policy, root_kind=kind, max_depth=depth, max_nodes=nodes,
                        budget_usd=budget, offline=offline, emit=q.put, as_of=as_of or None).run()
        except Exception as e:  # noqa: BLE001
            q.put({"type": "error", "msg": f"{type(e).__name__}: {e}"})
            if PUBLIC_LIVE and r["meter"]["spent_usd"] > 0:   # cached replays don't use a slot
                _public_stamps.append(time.time())
        finally:
            if PUBLIC_LIVE and _public_lock.locked():
                _public_lock.release()
            q.put(None)

    threading.Thread(target=work, daemon=True).start()

    async def stream():
        while True:
            try:
                evt = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.1)
                yield ": keepalive\n\n"
                continue
            if evt is None:
                break
            yield _sse(evt)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/can_run")
def can_run():
    if READONLY:
        return {"ok": False, "reason": "Public demo is replay-only."}
    why = _public_refusal()
    return {"ok": why is None, "reason": why}


@app.get("/api/runs")
def runs():
    out = []
    for p in sorted(RUNS_DIR.glob("*.json"), key=lambda p: -p.stat().st_mtime):
        try:
            d = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        out.append({"run_id": d["run_id"], "root": d["root"], "nodes": len(d["nodes"]), "as_of": d.get("as_of"),
                    "red": sum(n["risk"] == "red" for n in d["nodes"]), "elapsed_s": d.get("elapsed_s"),
                    "spent_usd": d["meter"]["spent_usd"], "mtime": p.stat().st_mtime})
    return out


@app.get("/api/replay/{run_id}")
async def replay(run_id: str, speed: float = 4.0):
    p = RUNS_DIR / f"{run_id}.json"
    if not p.exists():
        raise HTTPException(404)
    d = json.loads(p.read_text())
    events = d.pop("events", [])

    async def stream():
        last = 0.0
        for e in events:
            await asyncio.sleep(min(1.2, max(0.0, (e["t"] - last) / speed)))
            last = e["t"]
            yield _sse(e)
        yield _sse({"type": "done", "result": d})

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/report/{run_id}")
def report(run_id: str):
    p = RUNS_DIR / f"{run_id}.json"
    if not p.exists():
        raise HTTPException(404)
    d = json.loads(p.read_text())
    d.pop("events", None)
    return d


# ---- Telem Monitors: continuous re-screening of flagged nodes ---------------
class MonitorReq(BaseModel):
    name: str
    run_id: str | None = None


@app.post("/api/monitor")
def create_monitor(req: MonitorReq):
    if READONLY or PUBLIC_LIVE:
        raise HTTPException(403, "Public demo is replay-only.")
    from telem import Telem
    query = (f"New sanctions designations, export-control listings, government investigations, ownership "
             f"changes or military-link reports involving {req.name}")
    try:
        m = Telem(base_url=TELEM_BASE_URL, api_key=TELEM_API_KEY).monitors.create(query, frequency="1h", ttl="7d")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Telem monitor create failed: {e}") from e
    mid = getattr(m, "id", None) or str(m)
    _monitors[mid] = {"id": mid, "name": req.name, "query": query, "created": time.time(), "run_id": req.run_id}
    ledger({"kind": "monitor_create", "id": mid, "name": req.name})
    return _monitors[mid]


@app.get("/api/monitors")
def list_monitors():
    return list(_monitors.values())


@app.get("/api/monitor/{mid}/changes")
def monitor_changes(mid: str):
    from telem import Telem
    try:
        changes = list(Telem(base_url=TELEM_BASE_URL, api_key=TELEM_API_KEY).monitors.iter_changes(mid))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, str(e)) from e
    return [c.model_dump() if hasattr(c, "model_dump") else c for c in changes][:50]
