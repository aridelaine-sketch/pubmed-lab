"""
Model bootstrap.

We deliberately do NOT ship model weights in this repository or in the
AppImage. A quantized 8B model (what this app recommends, see README)
is roughly 4.5-5.5 GB -- GitHub hard-blocks any single file over 100 MB
without Git LFS, and LFS's free tier (1 GB storage / 1 GB bandwidth per
month) would be exhausted by a single clone. More importantly, it's the
wrong place for it: every local-model tool (Ollama, LM Studio, GPT4All)
keeps weights in their own model store, decoupled from application code,
so a model update or a different quantization choice doesn't mean
re-cloning a multi-gigabyte git repo.

What we do instead: check whether the configured model is already
pulled, and if not, pull it automatically through Ollama's own HTTP
API and report progress -- so "the model isn't included" never becomes
the user's problem to solve by hand.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Callable, Iterator

import httpx


@dataclass
class PullProgress:
    status: str
    completed: int = 0
    total: int = 0

    @property
    def fraction(self) -> float | None:
        if self.total > 0:
            return self.completed / self.total
        return None


class ModelNotAvailable(RuntimeError):
    """Raised when Ollama itself isn't reachable at all (not installed / not running)."""


def is_model_present(model: str, host: str = "http://localhost:11434", timeout: float = 5.0) -> bool:
    try:
        resp = httpx.get(f"{host}/api/tags", timeout=timeout)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise ModelNotAvailable(
            f"Could not reach Ollama at {host}. Is it installed and running? "
            f"See README.md 'Setup'. ({exc})"
        ) from exc
    names = {m.get("name", "") for m in resp.json().get("models", [])}
    # Ollama tags carry an implicit ":latest"; match either form.
    return model in names or f"{model}:latest" in names or any(n.split(":")[0] == model for n in names)


def pull_model(
    model: str, host: str = "http://localhost:11434",
    on_progress: Callable[[PullProgress], None] | None = None, timeout: float = 1800.0,
) -> None:
    """Streams POST /api/pull, which returns newline-delimited JSON progress
    events, and calls on_progress for each one. Raises on failure."""
    with httpx.stream(
        "POST", f"{host}/api/pull", json={"name": model, "stream": True}, timeout=timeout
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            event = json.loads(line)
            if "error" in event:
                raise RuntimeError(f"Ollama pull failed for {model!r}: {event['error']}")
            progress = PullProgress(
                status=event.get("status", ""),
                completed=event.get("completed", 0),
                total=event.get("total", 0),
            )
            if on_progress:
                on_progress(progress)


def _print_progress(p: PullProgress) -> None:
    if p.fraction is not None:
        pct = p.fraction * 100
        sys.stdout.write(f"\r  {p.status}: {pct:5.1f}%")
        sys.stdout.flush()
        if pct >= 100:
            print()
    else:
        print(f"  {p.status}")


def ensure_model(model: str, host: str = "http://localhost:11434") -> None:
    """Call at app startup. Pulls the model with console progress if it's
    missing; does nothing (fast) if it's already present."""
    if is_model_present(model, host):
        return
    print(f"Model {model!r} not found locally. Pulling via Ollama (one-time download)...")
    pull_model(model, host, on_progress=_print_progress)
    print(f"Done: {model!r} is ready.")
