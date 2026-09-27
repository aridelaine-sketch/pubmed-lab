#!/usr/bin/env bash
# One-time setup: installs Ollama if it isn't already, then pulls the
# model this app is configured to use. Safe to re-run any time.
set -euo pipefail

MODEL="${OLLAMA_MODEL:-qwen3:8b}"

echo "== PubMed Lab setup =="

if ! command -v ollama >/dev/null 2>&1; then
    echo "Ollama not found. Installing (https://ollama.com/install.sh)..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama already installed: $(command -v ollama)"
fi

if ! pgrep -x "ollama" >/dev/null 2>&1; then
    echo "Starting the Ollama service..."
    (ollama serve >/tmp/ollama-serve.log 2>&1 &)
    sleep 2
fi

echo "Pulling model: $MODEL (this only downloads once; subsequent runs are instant)"
ollama pull "$MODEL"

echo ""
echo "Setup complete. Run the app with:"
echo "    python -m app.ui.main"
