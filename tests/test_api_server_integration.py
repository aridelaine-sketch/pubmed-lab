import json
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "demo"))

from app.config import Config
from app.decision_model.fake_backend import FakeBackend
from app.ui.api_server import start_server
from mock_pubmed import MockPubMedEngine


def post(url, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def test_api_run_and_save_over_real_http():
    tmp = Path(tempfile.mkdtemp())
    cfg = Config(
        db_path=str(tmp / "test.db"),
        obsidian_vault_path=str(tmp / "vault"),
    )
    model = FakeBackend()
    server = start_server(model, cfg, port=8799, engine_factory=lambda: MockPubMedEngine())
    time.sleep(0.2)  # let the listener bind

    try:
        # real HTTP GET for the static UI
        with urllib.request.urlopen("http://127.0.0.1:8799/", timeout=5) as resp:
            html = resp.read().decode()
            assert "<title>PubMed Lab</title>" in html

        # real HTTP POST that exercises the entire pipeline
        run_result = post("http://127.0.0.1:8799/api/run", {
            "text": "Why does Eisenmenger syndrome cause hemoptysis?"
        })
        assert run_result["note_type"] == "question"
        assert "PMID:" in run_result["markdown"]
        assert "Eisenmenger" in run_result["markdown"]

        save_result = post("http://127.0.0.1:8799/api/save", {
            "markdown": run_result["markdown"], "topic": run_result["topic"],
        })
        saved_path = Path(save_result["saved_path"])
        assert saved_path.exists()
        assert saved_path.read_text() == run_result["markdown"]
    finally:
        server.shutdown()


if __name__ == "__main__":
    test_api_run_and_save_over_real_http()
    print("OK: real HTTP round trip through the desktop app's local server works.")
