import json
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from threading import RLock


class Store:
    """Small durable store. All mutations are serialized by the service lock."""

    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "state.sqlite3"
        self.lock = RLock()
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    def save(self, record):
        with self.lock, self.connect() as db:
            db.execute("INSERT INTO analyses VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                       (record["analysis_id"], json.dumps(record, ensure_ascii=False, allow_nan=False)))

    def get(self, analysis_id):
        with self.lock, self.connect() as db:
            row = db.execute("SELECT payload FROM analyses WHERE id=?", (analysis_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self):
        with self.lock, self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM analyses")]
