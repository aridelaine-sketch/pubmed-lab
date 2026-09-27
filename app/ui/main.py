from __future__ import annotations

import os

from app.config import Config, env_override
from app.decision_model.ensure_model import ModelNotAvailable, ensure_model
from app.decision_model.ollama_backend import OllamaBackend
from app.ui.api_server import start_server

PORT = 8756


def main() -> None:
    import webview  # imported here so the rest of the app has no GUI dependency

    cfg = env_override(Config.load())

    try:
        ensure_model(cfg.ollama_model, cfg.ollama_host)
    except ModelNotAvailable as exc:
        print(f"error: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)

    model = OllamaBackend(model=cfg.ollama_model, host=cfg.ollama_host)

    start_server(model, cfg, port=PORT)

    # The AppImage vendors PyQt5 + QtWebEngine specifically so the app doesn't
    # depend on the host having GTK3/WebKit2GTK installed. When running from
    # source instead, pywebview will auto-detect whatever's available (GTK,
    # Qt, ...) unless PUBMED_LAB_GUI overrides it.
    gui = os.environ.get("PUBMED_LAB_GUI", "qt")
    webview.create_window(
        "PubMed Lab", f"http://127.0.0.1:{PORT}/", width=760, height=880, min_size=(480, 600)
    )
    webview.start(gui=gui if gui != "auto" else None)


if __name__ == "__main__":
    main()
