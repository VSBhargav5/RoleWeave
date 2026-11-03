"""Append-only local posting snapshots. No network or qualification inference."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
from uuid import uuid4

from roleweave import MARKETS, review_snapshot, text


class JobStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL,
                source_url TEXT NOT NULL, market TEXT NOT NULL,
                captured_at TEXT NOT NULL, input_sha256 TEXT NOT NULL,
                snapshot BLOB NOT NULL,
                UNIQUE(title, company, source_url, input_sha256))""")

    def save(self, snapshot, title, company, source_url=""):
        result = review_snapshot(snapshot)
        title = text(title, "Job title")
        company = text(company, "Company")
        if not isinstance(source_url, str) or len(source_url) > 50000:
            raise ValueError("Source URL must be text of at most 50000 characters")
        identifier = str(uuid4())
        with closing(sqlite3.connect(self.path)) as db, db:
            try:
                db.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                    identifier, title, company, source_url, result["market"],
                    datetime.now(timezone.utc).isoformat(), result["input_sha256"], snapshot))
            except sqlite3.IntegrityError as exc:
                raise ValueError("This exact review and job details are already saved") from exc
        return identifier

    def list_jobs(self, market=None):
        if market is not None and market not in MARKETS:
            raise ValueError("Unknown market")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.row_factory = sqlite3.Row
            query = "SELECT id, title, company, source_url, market, captured_at, input_sha256 FROM jobs"
            rows = db.execute(query + (" WHERE market = ?" if market else "")
                              + " ORDER BY captured_at DESC, id", (market,) if market else ())
            return [dict(row) for row in rows]

    def load(self, identifier):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM jobs WHERE id = ?", (identifier,)).fetchone()
        if row is None:
            raise ValueError("Saved job was not found")
        item = dict(row)
        if hashlib.sha256(item["snapshot"]).hexdigest() != item["input_sha256"]:
            raise ValueError("Saved snapshot fingerprint does not match")
        result = review_snapshot(item["snapshot"])
        if result["market"] != item["market"]:
            raise ValueError("Saved market does not match the original review")
        item["review"] = result
        return item

    def export(self, identifier, destination):
        item = self.load(identifier)
        # Exclusive creation prevents silently replacing an earlier export.
        with Path(destination).open("xb") as target:
            target.write(item["snapshot"])
