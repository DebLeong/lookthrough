"""Content-addressed disk cache + a call ledger.

Every external call (Telem, Tavily, LLM) goes through `cached()`. Re-running a
look-through costs nothing, and demo mode replays entirely from disk.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any, Callable

from .config import CACHE_DIR, DATA

_LEDGER = DATA / "ledger.jsonl"
_lock = threading.Lock()


def _path(namespace: str, payload: Any):
    h = hashlib.sha256(json.dumps([namespace, payload], sort_keys=True, default=str).encode()).hexdigest()
    d = CACHE_DIR / namespace
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{h[:32]}.json"


def cached(namespace: str, payload: Any, fn: Callable[[], Any], *, offline: bool = False) -> tuple[Any, bool]:
    """Return (value, was_cache_hit). In offline mode a miss raises instead of calling out."""
    p = _path(namespace, payload)
    if p.exists():
        return json.loads(p.read_text()), True
    if offline:
        raise LookupError(f"offline cache miss: {namespace}")
    value = fn()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, default=str))
    tmp.replace(p)
    return value, False


def ledger(event: dict) -> None:
    event = {"ts": time.time(), **event}
    with _lock, _LEDGER.open("a") as f:
        f.write(json.dumps(event, default=str) + "\n")
