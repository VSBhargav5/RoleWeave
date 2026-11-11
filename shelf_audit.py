"""Bounded read-only source/reference checks; never repair or authenticate a shelf."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from applications import validate_history
from career_profile import profile_snapshot
from job_store import backup_record
from resume_versions import MAX_RESUME_SNAPSHOT, encoded, job_context, resume_snapshot
from roleweave import MAX_BYTES, text
from safe_export import publish_bytes

MAX_AUDIT_ROWS = 10000
MAX_AUDIT_BYTES = 64 * 1024 * 1024
TABLES = ("jobs", "career_profiles", "resume_versions", "application_events", "app_settings")


def audit_database(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError("Database does not exist; no file was created")
    issues, jobs, profiles = [], {}, {}
    def issue(table, identifier, code):
        issues.append({"table": table, "record_id": str(identifier)[:128], "code": code})
    def version(row, parser, limit):
        text(row["id"], "Version ID")
        if datetime.fromisoformat(row["created_at"]).utcoffset() is None:
            raise ValueError("Version timestamp needs a timezone")
        if not isinstance(row["snapshot"], bytes) or len(row["snapshot"]) > limit:
            raise ValueError("Version snapshot exceeds its size limit")
        record, digest = parser(row["snapshot"])
        if digest != row["snapshot_sha256"]:
            raise ValueError("Version fingerprint mismatch")
        return record
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN")  # one consistent read snapshot, including reference checks
            check = db.execute("PRAGMA quick_check(1)").fetchone()
            if check is None or check[0] != "ok":
                raise ValueError("SQLite structure check failed; preserve the file")
            counts, total_bytes = {}, 0
            for table in TABLES:
                columns = [row[1] for row in db.execute("PRAGMA table_info(" + table + ")")]
                if not columns:
                    raise ValueError("Required shelf table is missing")
                sizes = " + ".join('COALESCE(length(CAST("' + column.replace('"', '""') + '" AS BLOB)), 0)' for column in columns)
                count, size = db.execute("SELECT COUNT(*), COALESCE(SUM(" + sizes + "), 0) FROM " + table).fetchone()
                counts[table] = count
                total_bytes += size
            if sum(counts.values()) > MAX_AUDIT_ROWS or total_bytes > MAX_AUDIT_BYTES:
                raise ValueError("Shelf audit limit exceeded (10000 rows / 64 MiB field bytes); nothing was changed")
            for raw in db.execute("SELECT * FROM jobs ORDER BY id"):
                row = dict(raw)
                try:
                    context = job_context(row)
                    backup_record(context)
                    jobs[row["id"]] = context
                except (ValueError, TypeError, KeyError, UnicodeError):
                    issue("jobs", row.get("id"), "invalid_source_or_metadata")
            for raw in db.execute("SELECT * FROM career_profiles ORDER BY id"):
                row = dict(raw)
                try:
                    version(row, profile_snapshot, MAX_BYTES)
                    profiles[row["id"]] = row
                except (ValueError, TypeError, KeyError, UnicodeError):
                    issue("career_profiles", row.get("id"), "invalid_source_or_metadata")
            for raw in db.execute("SELECT * FROM resume_versions ORDER BY id"):
                row = dict(raw)
                try:
                    record = version(row, resume_snapshot, MAX_RESUME_SNAPSHOT)
                    source = profiles.get(record["profile_id"])
                    if source is None or source["snapshot_sha256"] != record["profile_sha256"] or encoded(source["snapshot"]) != record["profile_snapshot_base64"]:
                        issue("resume_versions", row["id"], "profile_reference_mismatch")
                    context = record["job_context"]
                    if context is not None and jobs.get(context["id"]) != context:
                        issue("resume_versions", row["id"], "job_reference_mismatch")
                except (ValueError, TypeError, KeyError, UnicodeError):
                    issue("resume_versions", row.get("id"), "invalid_source_or_metadata")
            history = [dict(row) for row in db.execute("SELECT * FROM application_events ORDER BY job_id, revision")]
            for event in history:
                if event["job_id"] not in jobs:
                    issue("application_events", event["id"], "job_reference_unavailable")
            try:
                validate_history(history)
            except (ValueError, TypeError, KeyError, UnicodeError):
                issue("application_events", "history", "invalid_events_or_revision_sequence")
            for row in db.execute("SELECT * FROM app_settings WHERE key='active_profile'"):
                if row["value"] not in profiles:
                    issue("app_settings", "active_profile", "profile_reference_unavailable")
    except sqlite3.DatabaseError:
        raise ValueError("Shelf could not be audited; no repair or write was attempted") from None
    return {"format": "roleweave-shelf-audit-v1", "audited_at": datetime.now(timezone.utc).isoformat(),
            "ok": not issues, "counts": counts, "field_bytes": total_bytes, "issues": issues,
            "limitation": "Checks stored source fingerprints, metadata, history and references in one read snapshot. Does not authenticate claims, replay PDF rendering, inspect separate files, or guarantee recovery."}


def export_audit(report, destination, *, confirmed=False):
    if confirmed is not True:
        raise ValueError("Confirm export of the private shelf identifiers/check results")
    if Path(destination).suffix.lower() != ".json":
        raise ValueError("Choose a .json audit filename")
    publish_bytes(destination, json.dumps(report, ensure_ascii=True, indent=2).encode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    report = audit_database(args.database)
    if args.output:
        export_audit(report, args.output, confirmed=args.confirm)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    raise SystemExit(0 if report["ok"] else 2)
