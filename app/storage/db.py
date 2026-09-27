from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    pmid TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    journal TEXT,
    year TEXT,
    authors TEXT,          -- JSON list
    doi TEXT,
    pmcid TEXT,
    abstract TEXT,
    has_full_text INTEGER DEFAULT 0,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_text TEXT NOT NULL,
    intent TEXT NOT NULL,
    category TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL REFERENCES queries(id),
    pmid TEXT NOT NULL REFERENCES papers(pmid),
    section TEXT,
    source_type TEXT,
    sentence_index INTEGER,
    sentence TEXT NOT NULL,
    relation TEXT NOT NULL,
    confidence REAL NOT NULL,
    note_section TEXT      -- which section of the generated note this belongs to (Learn mode)
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL REFERENCES queries(id),
    topic TEXT NOT NULL,
    note_type TEXT NOT NULL,   -- learn | question | claim
    markdown_path TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evidence_query ON evidence(query_id);
CREATE INDEX IF NOT EXISTS idx_evidence_pmid ON evidence(pmid);
"""


class Store:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False because the desktop app's local HTTP server
        # (ThreadingHTTPServer) handles each request on its own thread, while
        # this Store is constructed once in the main thread. SQLite connections
        # are not safe for *concurrent* use across threads, so every access is
        # serialized through self._lock below rather than trusting SQLite's
        # own locking, which is not enough on its own for this pattern.
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    @contextmanager
    def cursor(self):
        with self._lock:
            cur = self._conn.cursor()
            try:
                yield cur
                self._conn.commit()
            finally:
                cur.close()

    def upsert_paper(self, paper) -> None:
        import json
        with self.cursor() as cur:
            cur.execute("""
                INSERT INTO papers (pmid, title, journal, year, authors, doi, pmcid, abstract, has_full_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pmid) DO UPDATE SET
                    title=excluded.title, journal=excluded.journal, year=excluded.year,
                    authors=excluded.authors, doi=excluded.doi, pmcid=excluded.pmcid,
                    abstract=excluded.abstract, has_full_text=excluded.has_full_text
            """, (paper.pmid, paper.title, paper.journal, paper.year, json.dumps(paper.authors),
                  paper.doi, paper.pmcid, paper.abstract, int(paper.has_full_text)))

    def insert_query(self, user_text: str, intent: str, category: str) -> int:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO queries (user_text, intent, category) VALUES (?, ?, ?)",
                (user_text, intent, category),
            )
            return cur.lastrowid

    def insert_evidence(self, query_id: int, ev, note_section: str = "") -> None:
        with self.cursor() as cur:
            cur.execute("""
                INSERT INTO evidence (query_id, pmid, section, source_type, sentence_index,
                                       sentence, relation, confidence, note_section)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (query_id, ev.pmid, ev.section, ev.source_type, ev.sentence_index,
                  ev.sentence, ev.relation.value, ev.confidence, note_section))

    def insert_note(self, query_id: int, topic: str, note_type: str, markdown_path: str) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO notes (query_id, topic, note_type, markdown_path) VALUES (?, ?, ?, ?)",
                (query_id, topic, note_type, markdown_path),
            )

    def close(self) -> None:
        self._conn.close()
