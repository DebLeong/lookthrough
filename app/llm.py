"""LLM access through the local `claude` CLI (user's Claude subscription).

Usage is deliberately gentle:
  * a cross-process file lock => one call at a time on this machine
  * a minimum gap between calls and a per-minute ceiling
  * every response cached by prompt hash, so re-runs make zero calls
"""
from __future__ import annotations

import fcntl
import json
import re
import subprocess
import tempfile
import time
from collections import deque

from .cache import cached, ledger
from .config import DATA, LLM_FAST_MODEL, LLM_MAX_PER_MINUTE, LLM_MIN_INTERVAL_S

_LOCK_FILE = DATA / ".llm.lock"
_STAMP_FILE = DATA / ".llm.stamps"
_SANDBOX = tempfile.mkdtemp(prefix="lookthrough-llm-")  # neutral cwd: no project CLAUDE.md/settings


class LLMError(RuntimeError):
    pass


def _throttle() -> None:
    """Called while holding the lock. Enforces min interval and per-minute cap across processes."""
    try:
        stamps = deque(float(x) for x in _STAMP_FILE.read_text().split())
    except FileNotFoundError:
        stamps = deque()
    now = time.time()
    while stamps and now - stamps[0] > 60:
        stamps.popleft()
    wait = 0.0
    if stamps:
        wait = max(wait, LLM_MIN_INTERVAL_S - (now - stamps[-1]))
    if len(stamps) >= LLM_MAX_PER_MINUTE:
        wait = max(wait, 60 - (now - stamps[0]) + 0.5)
    if wait > 0:
        time.sleep(wait)
    stamps.append(time.time())
    _STAMP_FILE.write_text(" ".join(f"{s:.3f}" for s in list(stamps)[-LLM_MAX_PER_MINUTE:]))


def _call_cli(prompt: str, system: str, model: str, timeout: int) -> str:
    cmd = [
        "claude", "-p",
        "--model", model,
        "--output-format", "json",
        "--max-turns", "1",
        "--tools", "",
        "--append-system-prompt", system,
    ]
    _LOCK_FILE.touch()
    with _LOCK_FILE.open("r") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            _throttle()
            t0 = time.time()
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=_SANDBOX)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
    if proc.returncode != 0:
        raise LLMError(f"claude CLI exit {proc.returncode}: {proc.stderr[:400] or proc.stdout[:400]}")
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise LLMError(f"unparseable CLI output: {proc.stdout[:300]}") from e
    if out.get("is_error"):
        raise LLMError(f"claude CLI error: {str(out.get('result'))[:300]}")
    ledger({"kind": "llm", "model": model, "latency_s": round(time.time() - t0, 2),
            "usd_list_price": out.get("total_cost_usd")})
    return out.get("result", "")


def complete(prompt: str, *, system: str = "", model: str | None = None, timeout: int = 180) -> str:
    model = model or LLM_FAST_MODEL
    val, _hit = cached("llm", {"p": prompt, "s": system, "m": model}, lambda: _call_cli(prompt, system, model, timeout))
    return val


_JSON_RE = re.compile(r"(\{.*\}|\[.*\])", re.S)


def complete_json(prompt: str, *, system: str = "", model: str | None = None, timeout: int = 180):
    """Ask for JSON and parse it; one repair retry if the model wraps it in prose."""
    sys = (system + "\n\nRespond with a single valid JSON value only. No prose, no markdown fences.").strip()
    text = complete(prompt, system=sys, model=model, timeout=timeout)
    for candidate in (text, *(m.group(1) for m in [_JSON_RE.search(text)] if m)):
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
    fixed = complete(f"Convert this into valid JSON only, preserving content:\n\n{text}", system=sys, model=LLM_FAST_MODEL)
    m = _JSON_RE.search(fixed)
    if not m:
        raise LLMError(f"model did not return JSON: {text[:200]}")
    return json.loads(m.group(1))
