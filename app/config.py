"""Configuration: loads keys from .env, tolerant of the variable spellings used locally."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE_DIR = DATA / "cache"
LISTS_DIR = DATA / "lists"
RUNS_DIR = DATA / "runs"
for _d in (CACHE_DIR, LISTS_DIR, RUNS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

_env = {k.lower(): v for k, v in dotenv_values(ROOT / ".env").items() if v}
_env.update({k.lower(): v for k, v in os.environ.items() if v})


def _key(*names: str) -> str | None:
    for n in names:
        if v := _env.get(n.lower()):
            return v.strip()
    return None


TELEM_API_KEY = _key("TELEM_API_KEY", "Telem_API_key")
# Hackathon deployment (per Telem): keys from hack.telem.ai, base URL below.
TELEM_BASE_URL = _key("TELEM_BASE_URL") or "https://hack.telem.ai/api"
TAVILY_API_KEY = _key("TAVILY_API_KEY", "Tavliy_API_key", "Tavily_API_key")

# LLM runs through the local `claude` CLI on the user's subscription.
LLM_FAST_MODEL = os.environ.get("LLM_FAST_MODEL", "haiku")
LLM_SMART_MODEL = os.environ.get("LLM_SMART_MODEL", "sonnet")
LLM_MIN_INTERVAL_S = float(os.environ.get("LLM_MIN_INTERVAL_S", "3.0"))
LLM_MAX_PER_MINUTE = int(os.environ.get("LLM_MAX_PER_MINUTE", "12"))

# Hard spend guard for a single look-through run (USD, estimated).
RUN_BUDGET_USD = float(os.environ.get("RUN_BUDGET_USD", "0.75"))
