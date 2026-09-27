"""
Run with:  python -m demo.run_demo

Everything here is the real app code EXCEPT the PubMed engine (mocked,
see mock_pubmed.py, because this sandbox cannot reach eutils.ncbi.nlm.nih.gov)
and the decision model (FakeBackend, a deterministic stand-in for
OllamaBackend -- see app/decision_model/fake_backend.py for why).

Swap MockPubMedEngine -> PubMedEngine and FakeBackend -> OllamaBackend
and this is the production code path.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.decision_model.fake_backend import FakeBackend
from app.export.markdown import save_to_vault
from app.orchestrator import modes
from app.storage.db import Store
from demo.mock_pubmed import MockPubMedEngine


def run_case(label: str, model, engine, store, fn, *args):
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    result = fn(model, engine, store, *args)
    print(result.markdown)
    return result


def main():
    tmp_dir = Path(tempfile.mkdtemp(prefix="pubmed_lab_demo_"))
    db_path = tmp_dir / "demo.db"
    vault_path = tmp_dir / "vault"

    model = FakeBackend()
    engine = MockPubMedEngine()
    store = Store(db_path)

    saved_paths = []

    r1 = run_case(
        "MODE: QUESTION — 'Why does Eisenmenger syndrome cause hemoptysis?'",
        model, engine, store, modes.run_question,
        "Why does Eisenmenger syndrome cause hemoptysis?",
    )
    saved_paths.append(save_to_vault(r1.markdown, vault_path, r1.topic))

    r2 = run_case(
        "MODE: CLAIM — 'COPD is associated with pulmonary hypertension.'",
        model, engine, store, modes.run_claim,
        "COPD is associated with pulmonary hypertension.",
    )
    saved_paths.append(save_to_vault(r2.markdown, vault_path, r2.topic))

    r3 = run_case(
        "MODE: LEARN — 'pulmonary hypertension'",
        model, engine, store, modes.run_learn,
        "pulmonary hypertension",
    )
    saved_paths.append(save_to_vault(r3.markdown, vault_path, r3.topic))

    print(f"\n{'=' * 70}\nSaved {len(saved_paths)} notes to: {vault_path}")
    for p in saved_paths:
        print(" -", p)
    print(f"SQLite store at: {db_path}")

    import sqlite3
    conn = sqlite3.connect(db_path)
    n_papers = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    n_evidence = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
    n_queries = conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
    print(f"DB contents -> queries: {n_queries}, papers cached: {n_papers}, evidence rows: {n_evidence}")
    conn.close()

    return tmp_dir


if __name__ == "__main__":
    main()
