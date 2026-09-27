"""
Deliberately built on Python's stdlib http.server instead of a web
framework. The whole API surface is two endpoints, so a framework
would add a dependency for no real benefit -- consistent with the
project's minimalism principle.
"""

from __future__ import annotations

import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from app.config import Config
from app.decision_model.base import DecisionModel
from app.export.markdown import save_to_vault
from app.orchestrator.modes import dispatch
from app.pubmed.engine import PubMedEngine
from app.storage.db import Store

WEB_DIR = Path(__file__).parent / "web"


def _default_engine_factory(cfg: Config):
    return PubMedEngine(email=cfg.ncbi_email, api_key=cfg.ncbi_api_key, try_full_text=cfg.try_full_text)


def make_handler(model: DecisionModel, cfg: Config, engine_factory: Callable[[], object] | None = None):
    """engine_factory is injectable so tests/demos can swap in a mock
    PubMed engine without touching this module's logic at all."""
    store = Store(cfg.db_path)
    engine_factory = engine_factory or (lambda: _default_engine_factory(cfg))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quieter default logging
            pass

        def _send_json(self, obj: dict, status: int = 200):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw or b"{}")

        def do_GET(self):
            if self.path == "/" or self.path == "":
                self.path = "/index.html"
            file_path = (WEB_DIR / self.path.lstrip("/")).resolve()
            if WEB_DIR not in file_path.parents and file_path != WEB_DIR:
                self.send_error(403)
                return
            if not file_path.exists():
                self.send_error(404)
                return
            content_type, _ = mimetypes.guess_type(str(file_path))
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path == "/api/run":
                body = self._read_json()
                text = (body.get("text") or "").strip()
                if not text:
                    return self._send_json({"error": "empty input"}, 400)
                engine = engine_factory()
                try:
                    result = dispatch(model, engine, store, text)
                finally:
                    engine.close()
                return self._send_json({
                    "markdown": result.markdown,
                    "note_type": result.note_type,
                    "topic": result.topic,
                })

            if self.path == "/api/save":
                body = self._read_json()
                path = save_to_vault(body["markdown"], cfg.obsidian_vault_path, body["topic"])
                return self._send_json({"saved_path": str(path)})

            self.send_error(404)

    return Handler


def start_server(
    model: DecisionModel, cfg: Config, port: int = 8756,
    engine_factory: Callable[[], object] | None = None,
) -> ThreadingHTTPServer:
    handler = make_handler(model, cfg, engine_factory=engine_factory)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
