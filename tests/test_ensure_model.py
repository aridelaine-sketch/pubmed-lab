"""
Ollama isn't installed in this sandbox, so this test stands up a tiny
HTTP server that speaks Ollama's actual documented API shape
(GET /api/tags, POST /api/pull with NDJSON streaming progress) and
points ensure_model.py's real client code at it. This is the same
approach used for the PubMed layer: the client code is real and
written against the real documented API; only the *server on the
other end* is swapped for something reachable from here.
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.decision_model.ensure_model import ModelNotAvailable, is_model_present, pull_model


def make_fake_ollama(installed_models, pull_events):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_GET(self):
            if self.path == "/api/tags":
                body = json.dumps({"models": [{"name": n} for n in installed_models]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path == "/api/pull":
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                for event in pull_events:
                    self.wfile.write((json.dumps(event) + "\n").encode())
                    self.wfile.flush()
            else:
                self.send_error(404)

    return Handler


def start(handler_cls, port):
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_is_model_present_true_when_tag_matches():
    server = start(make_fake_ollama(["qwen3:8b", "llama3.2:3b"], []), 8801)
    try:
        assert is_model_present("qwen3:8b", host="http://127.0.0.1:8801") is True
        assert is_model_present("qwen3", host="http://127.0.0.1:8801") is True  # bare name matches tag
    finally:
        server.shutdown()


def test_is_model_present_false_when_missing():
    server = start(make_fake_ollama(["llama3.2:3b"], []), 8802)
    try:
        assert is_model_present("qwen3:8b", host="http://127.0.0.1:8802") is False
    finally:
        server.shutdown()


def test_is_model_present_raises_when_ollama_unreachable():
    with pytest.raises(ModelNotAvailable):
        is_model_present("qwen3:8b", host="http://127.0.0.1:1")  # nothing listening


def test_pull_model_streams_progress_events_in_order():
    events = [
        {"status": "pulling manifest"},
        {"status": "downloading", "completed": 50, "total": 100},
        {"status": "downloading", "completed": 100, "total": 100},
        {"status": "success"},
    ]
    server = start(make_fake_ollama([], events), 8803)
    seen = []
    try:
        pull_model("qwen3:8b", host="http://127.0.0.1:8803", on_progress=lambda p: seen.append(p))
    finally:
        server.shutdown()

    assert [e.status for e in seen] == ["pulling manifest", "downloading", "downloading", "success"]
    assert seen[1].fraction == 0.5
    assert seen[2].fraction == 1.0


def test_pull_model_raises_on_error_event():
    events = [{"status": "pulling manifest"}, {"error": "model not found"}]
    server = start(make_fake_ollama([], events), 8804)
    try:
        with pytest.raises(RuntimeError, match="model not found"):
            pull_model("nonexistent:1b", host="http://127.0.0.1:8804")
    finally:
        server.shutdown()
