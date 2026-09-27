# Contributing

This project stays deliberately small. Before adding a feature, check
whether it fits the core loop:

```
User → Local Decision Model → PubMed/PMC → Evidence → Markdown → Obsidian
```

If it doesn't obviously belong in that loop, it probably belongs in a
different tool, not here — see the "Not required" list in the project's
original design notes for what was deliberately left out (chat UI, a
built-in note editor, accounts/sync, gamification).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Before opening a PR

- `python -m pytest tests/ -v` passes (CI runs this on 3.10/3.11/3.12).
- `python -m demo.run_demo` still runs clean — it's the offline proof
  that the orchestrator, evidence extractor, storage, and markdown
  export all still work together.
- If you touch `app/decision_model/schemas.py`, remember the whole
  point of this app is that the model only ever returns indices/enums
  into data the caller already owns — never free text that ends up
  directly in a note.
- If you add a new `DecisionModel` backend, it should need zero changes
  to `app/orchestrator/`, `app/pubmed/`, or `app/ui/` — that boundary is
  load-bearing, not decorative.

## Reporting issues

Please include: what mode you were in (Learn/Question/Claim), the
model + runtime you were using (`OLLAMA_MODEL`, Ollama vs. something
else), and whether the issue reproduces in `demo/run_demo.py` (which
isolates the bug from anything network/model-related).
