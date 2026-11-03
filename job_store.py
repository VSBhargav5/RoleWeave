"""Append-only local posting snapshots. No network or qualification inference."""
from contextlib import closing
import base64
import binascii
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from roleweave import MARKETS, review_snapshot, text

MAX_BACKUP_BYTES = 64 * 1024 * 1024
BACKUP_FORMAT = "roleweave-backup-v1"


def backup_record(record):
    """Validate backup metadata and original review bytes before any writes."""
    keys = {"id", "title", "company", "source_url", "market", "captured_at", "input_sha256", "snapshot_base64"}
    if not isinstance(record, dict) or set(record) != keys:
        raise ValueError("Invalid backup job fields")
    for key in ("id", "title", "company", "captured_at", "input_sha256"):
        text(record[key], key)
    if not isinstance(record["source_url"], str) or len(record["source_url"]) > 50000:
        raise ValueError("Invalid backup source URL")
    try:
        captured = datetime.fromisoformat(record["captured_at"])
        if captured.tzinfo is None:
            raise ValueError("Capture time requires a timezone")
        if not isinstance(record["snapshot_base64"], str):
            raise ValueError("Invalid backup source encoding")
        snapshot = base64.b64decode(record["snapshot_base64"], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid backup time or source encoding") from exc
    result = review_snapshot(snapshot)
    if result["input_sha256"] != record["input_sha256"] or result["market"] != record["market"]:
        raise ValueError("Backup source fingerprint or market does not match")
    return (record["id"], record["title"], record["company"], record["source_url"],
            record["market"], record["captured_at"], record["input_sha256"], snapshot)


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

    def backup(self, destination):
        records = []
        size = len(json.dumps({"format": BACKUP_FORMAT, "jobs": []}).encode("utf-8"))
        for summary in self.list_jobs():
            item = self.load(summary["id"])
            record = {key: item[key] for key in ("id", "title", "company", "source_url", "market", "captured_at", "input_sha256")}
            record["snapshot_base64"] = base64.b64encode(item["snapshot"]).decode("ascii")
            backup_record(record)
            size += len(json.dumps(record, ensure_ascii=True).encode("utf-8")) + 2
            if size > MAX_BACKUP_BYTES:
                raise ValueError("Backup exceeds 64 MiB; no file was created")
            records.append(record)
        payload = json.dumps({"format": BACKUP_FORMAT, "jobs": records}, ensure_ascii=True).encode("utf-8")
        if len(payload) > MAX_BACKUP_BYTES:
            raise ValueError("Backup exceeds 64 MiB; no file was created")
        with Path(destination).open("xb") as target:
            target.write(payload)
        return len(records)

    def restore(self, source):
        with Path(source).open("rb") as handle:
            payload = handle.read(MAX_BACKUP_BYTES + 1)
        if len(payload) > MAX_BACKUP_BYTES:
            raise ValueError("Backup exceeds 64 MiB")

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate backup JSON key")
                result[key] = value
            return result

        try:
            data = json.loads(payload, object_pairs_hook=unique)
        except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            raise ValueError("Invalid backup JSON") from exc
        if not isinstance(data, dict) or set(data) != {"format", "jobs"} or data["format"] != BACKUP_FORMAT or not isinstance(data["jobs"], list):
            raise ValueError("Unsupported backup format")
        records = [backup_record(record) for record in data["jobs"]]
        if len({row[0] for row in records}) != len(records):
            raise ValueError("Duplicate job ID in backup")
        added, skipped = 0, 0
        with closing(sqlite3.connect(self.path)) as db, db:
            for row in records:
                existing = db.execute("SELECT * FROM jobs WHERE id = ?", (row[0],)).fetchone()
                if existing is not None:
                    if existing != row:
                        raise ValueError("Backup job ID conflicts with an existing snapshot; nothing restored")
                    skipped += 1
                    continue
                duplicate = db.execute("SELECT id FROM jobs WHERE title=? AND company=? AND source_url=? AND input_sha256=?",
                                       (row[1], row[2], row[3], row[6])).fetchone()
                if duplicate:
                    skipped += 1
                    continue
                db.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row)
                added += 1
        return added, skipped
