"""Append-only local posting snapshots. No network or qualification inference."""
from contextlib import closing
import base64
import binascii
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4

from roleweave import MARKETS, MAX_BYTES, review_snapshot, text
from applications import EVENT_FIELDS, STAGES, follow_up_date, validate_event, validate_history
from preparation_pack import build_pack
from calendar_export import follow_up_calendar
from safe_export import publish_bytes
from resume_render import resume_text
from career_profile import profile_snapshot
from resume_versions import MAX_RESUME_SNAPSHOT, make_resume_version, resume_snapshot, decoded, encoded

MAX_BACKUP_BYTES = 64 * 1024 * 1024
BACKUP_FORMAT = "roleweave-backup-v3"


def archived_version(record, parser, limit):
    keys = {"id", "created_at", "snapshot_sha256", "snapshot_base64"}
    if not isinstance(record, dict) or set(record) != keys:
        raise ValueError("Invalid archived version fields")
    text(record["id"], "Version ID")
    text(record["created_at"], "Version time")
    try:
        if datetime.fromisoformat(record["created_at"]).tzinfo is None:
            raise ValueError("Version time requires a timezone")
    except ValueError as exc:
        raise ValueError("Invalid archived version timestamp") from exc
    snapshot = decoded(record["snapshot_base64"], limit)
    _content, digest = parser(snapshot)
    if digest != record["snapshot_sha256"]:
        raise ValueError("Archived version fingerprint mismatch")
    return (record["id"], record["created_at"], digest, snapshot)


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


SCHEMA_APPLICATION_ID = 0x52575645  # RWVE; local file-format identity, not authentication.
SCHEMA_VERSION = 1
SCHEMA = (
    """CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL,
                source_url TEXT NOT NULL, market TEXT NOT NULL,
                captured_at TEXT NOT NULL, input_sha256 TEXT NOT NULL,
                snapshot BLOB NOT NULL,
                UNIQUE(title, company, source_url, input_sha256))""",
    """CREATE TABLE IF NOT EXISTS application_events (
                id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id),
                revision INTEGER NOT NULL, stage TEXT NOT NULL, note TEXT NOT NULL,
                follow_up TEXT NOT NULL, recorded_at TEXT NOT NULL,
                UNIQUE(job_id, revision))""",
    """CREATE TABLE IF NOT EXISTS career_profiles (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
                snapshot_sha256 TEXT NOT NULL, snapshot BLOB NOT NULL)""",
    "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    """CREATE TABLE IF NOT EXISTS resume_versions (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
                snapshot_sha256 TEXT NOT NULL, snapshot BLOB NOT NULL)""",
)


def initialize_schema(db):
    """Refuse unsupported files before writes; adopt known legacy shelves atomically."""
    db.execute("BEGIN IMMEDIATE")
    identity = db.execute("PRAGMA application_id").fetchone()[0]
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if (identity, version) not in ((0, 0), (SCHEMA_APPLICATION_ID, SCHEMA_VERSION)):
        raise ValueError("Unsupported database identity or newer schema. Use the matching RoleWeave version; do not overwrite this file.")
    objects = db.execute("SELECT type, name, sql FROM sqlite_master WHERE name NOT GLOB 'sqlite_*'").fetchall()
    with closing(sqlite3.connect(":memory:")) as reference:
        for statement in SCHEMA:
            reference.execute(statement)
        expected = dict(reference.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"))
    existing = {}
    def normalized(sql):
        return " ".join(sql.casefold().split()).replace("if not exists ", "")
    for kind, name, sql in objects:
        if kind != "table" or name not in expected or normalized(sql) != normalized(expected[name]):
            raise ValueError("Unsupported database structure. Keep the original file and restore a verified backup into a separate shelf.")
        existing[name] = sql
    if existing and "jobs" not in existing:
        raise ValueError("Database is not a recognized RoleWeave shelf; original file preserved.")
    if identity == SCHEMA_APPLICATION_ID and set(existing) != set(expected):
        raise ValueError("RoleWeave schema is incomplete. Keep the original file and restore a verified backup into a separate shelf.")
    if identity == SCHEMA_APPLICATION_ID:
        return
    for statement in SCHEMA:
        db.execute(statement)
    db.execute(f"PRAGMA application_id={SCHEMA_APPLICATION_ID}")
    db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


class JobStore:
    @staticmethod
    def inspect_backup(source):
        """Validate in an isolated shelf; never touch the user's current database."""
        with tempfile.TemporaryDirectory(prefix="roleweave-inspect-") as folder:
            checked = JobStore(Path(folder) / "check.db")
            checked.restore(source)
            jobs = checked.list_jobs()
            return {"saved_reviews": len(jobs), "profiles": len(checked.list_profiles()),
                    "resumes": len(checked.list_resumes()),
                    "history_entries": sum(len(checked.application_history(row["id"])) for row in jobs)}

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            initialize_schema(db)

    def create_resume(self, profile_id, identifiers, label, job_id=None, include_pdf=True, confirmed=False):
        if confirmed is not True:
            raise ValueError("Review and explicitly approve the resume content before saving")
        profile = self.load_profile(profile_id)
        job = self.load(job_id) if job_id is not None else None
        snapshot = make_resume_version(profile, identifiers, label, job, include_pdf)
        _record, digest = resume_snapshot(snapshot)
        identifier = str(uuid4())
        with closing(sqlite3.connect(self.path)) as db, db:
            if db.execute("SELECT 1 FROM resume_versions WHERE snapshot_sha256=?", (digest,)).fetchone():
                raise ValueError("This resume version already exists; select it to export")
            db.execute("INSERT INTO resume_versions VALUES (?, ?, ?, ?)",
                       (identifier, datetime.now(timezone.utc).isoformat(), digest, snapshot))
        return identifier

    def load_resume(self, identifier):
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM resume_versions WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise ValueError("Saved resume version was not found")
        item = dict(row)
        record, digest = resume_snapshot(item["snapshot"])
        if digest != item["snapshot_sha256"]:
            raise ValueError("Saved resume version fingerprint mismatch")
        profile = self.load_profile(record["profile_id"])
        if profile["snapshot_sha256"] != record["profile_sha256"]:
            raise ValueError("Saved resume profile reference mismatch")
        item["resume"] = record
        return item

    def list_resumes(self, job_id=None):
        if job_id is not None:
            self.load(job_id)
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute("SELECT id FROM resume_versions ORDER BY created_at DESC, id").fetchall()
        result = []
        for row in rows:
            item = self.load_resume(row[0])
            context = item["resume"]["job_context"]
            if job_id is not None and (context is None or context["id"] != job_id):
                continue
            result.append({"id": row[0], "created_at": item["created_at"], "label": item["resume"]["label"],
                           "has_pdf": bool(item["resume"]["pdf_base64"])})
        return result

    def export_resume(self, identifier, destination, format):
        if format not in ("html", "pdf", "txt"):
            raise ValueError("Choose HTML, PDF or plain text")
        suffixes = (".html", ".htm") if format == "html" else ("." + format,)
        if Path(destination).suffix.lower() not in suffixes:
            raise ValueError("Choose a filename ending in " + suffixes[0])
        record = self.load_resume(identifier)["resume"]
        if format == "pdf" and not record["pdf_base64"]:
            raise ValueError("This saved version is HTML-only; print the HTML from your browser")
        if format == "txt":
            profile, _digest = profile_snapshot(decoded(record["profile_snapshot_base64"], MAX_BYTES))
            payload = resume_text(profile, record["selected_fact_ids"]).encode("utf-8")
        else:
            payload = decoded(record[format + "_base64"], 8 * 1024 * 1024)
        publish_bytes(destination, payload)
        return hashlib.sha256(payload).hexdigest()

    def save_profile(self, snapshot):
        _data, digest = profile_snapshot(snapshot)
        identifier = str(uuid4())
        with closing(sqlite3.connect(self.path)) as db, db:
            current = db.execute("SELECT value FROM app_settings WHERE key='active_profile'").fetchone()
            if current and db.execute("SELECT 1 FROM career_profiles WHERE id=? AND snapshot_sha256=?", (current[0], digest)).fetchone():
                raise ValueError("This profile is unchanged; no new version was saved")
            db.execute("INSERT INTO career_profiles VALUES (?, ?, ?, ?)",
                       (identifier, datetime.now(timezone.utc).isoformat(), digest, snapshot))
            db.execute("INSERT OR REPLACE INTO app_settings VALUES ('active_profile', ?)", (identifier,))
        return identifier

    def load_profile(self, identifier):
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM career_profiles WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise ValueError("Career profile version was not found")
        item = dict(row)
        data, digest = profile_snapshot(item["snapshot"])
        if digest != item["snapshot_sha256"]:
            raise ValueError("Career profile fingerprint mismatch")
        item["profile"] = data
        return item

    def active_profile(self):
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT value FROM app_settings WHERE key='active_profile'").fetchone()
        return self.load_profile(row[0]) if row else None

    def list_profiles(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT id, created_at, snapshot_sha256 FROM career_profiles ORDER BY created_at DESC, id")]

    def activate_profile(self, identifier):
        self.load_profile(identifier)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT OR REPLACE INTO app_settings VALUES ('active_profile', ?)", (identifier,))

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

    def list_jobs(self, market=None, stage=None, query="", due_on=None, search_posting=False, sort="newest"):
        if sort not in ("newest", "oldest", "title", "company", "follow_up"):
            raise ValueError("Unknown job sort order")
        if type(search_posting) is not bool:
            raise ValueError("Posting search must be explicitly enabled or disabled")
        if market is not None and (not isinstance(market, str) or market not in MARKETS):
            raise ValueError("Unknown market")
        if stage is not None and (not isinstance(stage, str) or stage not in STAGES):
            raise ValueError("Unknown application stage")
        if not isinstance(query, str) or len(query) > 500:
            raise ValueError("Search must be text of at most 500 characters")
        if due_on is not None:
            follow_up_date(due_on)
            if not due_on:
                raise ValueError("Due filter requires a date")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.row_factory = sqlite3.Row
            rows = db.execute("""SELECT j.id, j.title, j.company, j.source_url, j.market, j.captured_at,
                j.input_sha256, e.id AS event_id, e.revision, e.stage, e.note, e.follow_up, e.recorded_at
                FROM jobs j LEFT JOIN application_events e ON e.job_id=j.id AND e.revision=
                (SELECT MAX(revision) FROM application_events WHERE job_id=j.id)
                ORDER BY j.captured_at DESC, j.id""").fetchall()
        result = []
        for row in rows:
            item = dict(row)
            event = {"id": item.pop("event_id"), "job_id": item["id"],
                     **{key: item.pop(key) for key in ("revision", "stage", "note", "follow_up", "recorded_at")}}
            if event["id"] is not None:
                validate_event(event)
            item.update(stage=event["stage"] or "saved", follow_up=event["follow_up"] or "",
                        decision_note=event["note"] or "")
            if market is not None and item["market"] != market:
                continue
            if stage is not None and item["stage"] != stage:
                continue
            haystack = "\n".join(item[key] for key in ("title", "company", "source_url", "decision_note"))
            if search_posting and query.strip():
                haystack += "\n" + json.loads(self.load(item["id"])["snapshot"])["posting"]
            if query.strip().casefold() not in haystack.casefold():
                continue
            if due_on is not None and (not item["follow_up"] or item["follow_up"] > due_on
                                       or item["stage"] in ("closed", "withdrawn")):
                continue
            result.append(item)
        if sort == "oldest":
            result.sort(key=lambda item: (item["captured_at"], item["id"]))
        elif sort in ("title", "company"):
            result.sort(key=lambda item: (item[sort].casefold(), item["title"].casefold(), item["id"]))
        if sort == "follow_up" or (due_on is not None and sort == "newest"):
            result.sort(key=lambda item: (item["follow_up"], item["captured_at"], item["id"]))
            if sort == "follow_up":
                result.sort(key=lambda item: not bool(item["follow_up"]))
        return result

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
        publish_bytes(destination, item["snapshot"])

    def export_preparation_pack(self, identifier, destination):
        payload = build_pack(self.load(identifier), self.application_history(identifier))
        publish_bytes(destination, payload)

    def export_follow_up(self, identifier, destination):
        path = Path(destination)
        if path.suffix.lower() != ".ics":
            raise ValueError("Choose an .ics calendar filename")
        payload = follow_up_calendar(self.load(identifier), self.application_history(identifier))
        publish_bytes(path, payload)

    def application_history(self, identifier):
        self.load(identifier)
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM application_events WHERE job_id=? ORDER BY revision", (identifier,))
            events = [dict(row) for row in rows]
        validate_history(events)
        return events

    def record_application(self, identifier, stage, note="", follow_up="", *, expected_revision=None):
        if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 0):
            raise ValueError("Expected history revision must be a nonnegative integer")
        self.load(identifier)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT * FROM application_events WHERE job_id=? ORDER BY revision", (identifier,)).fetchall()
            history = [dict(zip(EVENT_FIELDS, row)) for row in rows]
            validate_history(history)
            if expected_revision is not None and expected_revision != len(history):
                raise ValueError("Application history changed; reload and review the latest stage/follow-up before recording")
            event = {"id": str(uuid4()), "job_id": identifier, "revision": len(history) + 1,
                     "stage": stage, "note": note, "follow_up": follow_up,
                     "recorded_at": datetime.now(timezone.utc).isoformat()}
            validate_event(event)
            db.execute("INSERT INTO application_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                       tuple(event[field] for field in EVENT_FIELDS))
        return event

    def backup(self, destination):
        records = []
        # Read one consistent SQLite snapshot, including concurrent tracking updates.
        with closing(sqlite3.connect(self.path)) as db, db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN")
            jobs = [dict(row) for row in db.execute("SELECT * FROM jobs ORDER BY captured_at DESC, id")]
            events = [dict(row) for row in db.execute("SELECT * FROM application_events ORDER BY job_id, revision")]
            profiles = [dict(row) for row in db.execute("SELECT * FROM career_profiles ORDER BY created_at, id")]
            resumes = [dict(row) for row in db.execute("SELECT * FROM resume_versions ORDER BY created_at, id")]
            active = db.execute("SELECT value FROM app_settings WHERE key='active_profile'").fetchone()
        validate_history(events)
        job_ids = {job["id"] for job in jobs}
        if any(event["job_id"] not in job_ids for event in events):
            raise ValueError("Application history references a missing snapshot")
        active_id = active[0] if active else None
        profile_ids = {row["id"]: row["snapshot_sha256"] for row in profiles}
        if active_id is not None and active_id not in profile_ids:
            raise ValueError("Active career profile is missing")
        archives = []
        for rows, parser, limit in ((profiles, profile_snapshot, MAX_BYTES), (resumes, resume_snapshot, MAX_RESUME_SNAPSHOT)):
            archive = []
            for row in rows:
                record = {key: row[key] for key in ("id", "created_at", "snapshot_sha256")}
                record["snapshot_base64"] = encoded(row["snapshot"])
                archived_version(record, parser, limit)
                if parser is resume_snapshot:
                    resume, _digest = resume_snapshot(row["snapshot"])
                    if profile_ids.get(resume["profile_id"]) != resume["profile_sha256"]:
                        raise ValueError("Resume references a missing or changed career profile")
                archive.append(record)
            archives.append(archive)
        extra = {"career_profiles": archives[0], "resume_versions": archives[1], "active_profile_id": active_id}
        size = len(json.dumps({"format": BACKUP_FORMAT, "jobs": [], "application_events": [], **extra}).encode("utf-8"))
        for item in jobs:
            record = {key: item[key] for key in ("id", "title", "company", "source_url", "market", "captured_at", "input_sha256")}
            record["snapshot_base64"] = base64.b64encode(item["snapshot"]).decode("ascii")
            backup_record(record)
            size += len(json.dumps(record, ensure_ascii=True).encode("utf-8")) + 2
            if size > MAX_BACKUP_BYTES:
                raise ValueError("Backup exceeds 64 MiB; no file was created")
            records.append(record)
        for event in events:
            size += len(json.dumps(event, ensure_ascii=True).encode("utf-8")) + 2
            if size > MAX_BACKUP_BYTES:
                raise ValueError("Backup exceeds 64 MiB; no file was created")
        payload = json.dumps({"format": BACKUP_FORMAT, "jobs": records, "application_events": events, **extra}, ensure_ascii=True).encode("utf-8")
        if len(payload) > MAX_BACKUP_BYTES:
            raise ValueError("Backup exceeds 64 MiB; no file was created")
        publish_bytes(destination, payload)
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
        if not isinstance(data, dict) or not isinstance(data.get("format"), str):
            raise ValueError("Unsupported backup format")
        legacy = data["format"] == "roleweave-backup-v1"
        current = data["format"] == BACKUP_FORMAT
        keys = {"format", "jobs"} if legacy else {"format", "jobs", "application_events"}
        if current:
            keys |= {"career_profiles", "resume_versions", "active_profile_id"}
        if set(data) != keys or data["format"] not in ("roleweave-backup-v1", "roleweave-backup-v2", BACKUP_FORMAT) or not isinstance(data["jobs"], list):
            raise ValueError("Unsupported backup format")
        events = [] if legacy else data["application_events"]
        if not isinstance(events, list):
            raise ValueError("Application history must be a list")
        validate_history(events)
        records = [backup_record(record) for record in data["jobs"]]
        identifiers = {row[0] for row in records}
        if len(identifiers) != len(records):
            raise ValueError("Duplicate job ID in backup")
        if any(event["job_id"] not in identifiers for event in events):
            raise ValueError("Application history references a missing backup job")
        profile_rows, resume_rows = [], []
        active_id = None
        if current:
            if not isinstance(data["career_profiles"], list) or not isinstance(data["resume_versions"], list):
                raise ValueError("Archived profiles and resumes must be lists")
            profile_rows = [archived_version(record, profile_snapshot, MAX_BYTES) for record in data["career_profiles"]]
            resume_rows = [archived_version(record, resume_snapshot, MAX_RESUME_SNAPSHOT) for record in data["resume_versions"]]
            if len({row[0] for row in profile_rows}) != len(profile_rows) or len({row[0] for row in resume_rows}) != len(resume_rows):
                raise ValueError("Duplicate archived version ID")
            profile_ids = {row[0]: row[2] for row in profile_rows}
            active_id = data["active_profile_id"]
            if active_id is not None and (not isinstance(active_id, str) or active_id not in profile_ids):
                raise ValueError("Backup active profile does not exist")
            for row in resume_rows:
                resume, _digest = resume_snapshot(row[3])
                if profile_ids.get(resume["profile_id"]) != resume["profile_sha256"]:
                    raise ValueError("Backup resume references a missing or changed profile")
        added, skipped = 0, 0
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA foreign_keys=ON")
            mapped_ids = {}
            for row in records:
                existing = db.execute("SELECT * FROM jobs WHERE id = ?", (row[0],)).fetchone()
                if existing is not None:
                    if existing != row:
                        raise ValueError("Backup job ID conflicts with an existing snapshot; nothing restored")
                    skipped += 1
                    mapped_ids[row[0]] = row[0]
                    continue
                duplicate = db.execute("SELECT id FROM jobs WHERE title=? AND company=? AND source_url=? AND input_sha256=?",
                                       (row[1], row[2], row[3], row[6])).fetchone()
                if duplicate:
                    skipped += 1
                    mapped_ids[row[0]] = duplicate[0]
                    continue
                db.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row)
                mapped_ids[row[0]] = row[0]
                added += 1
            for event in events:
                mapped = {**event, "job_id": mapped_ids[event["job_id"]]}
                row = tuple(mapped[field] for field in EVENT_FIELDS)
                existing = db.execute("SELECT * FROM application_events WHERE id=?", (event["id"],)).fetchone()
                if existing is not None:
                    if existing != row:
                        raise ValueError("Application event ID conflict; nothing restored")
                    continue
                if db.execute("SELECT id FROM application_events WHERE job_id=? AND revision=?",
                              (mapped["job_id"], mapped["revision"])).fetchone():
                    raise ValueError("Application history diverges from existing history; nothing restored")
                db.execute("INSERT INTO application_events VALUES (?, ?, ?, ?, ?, ?, ?)", row)
            for identifier in set(mapped_ids.values()):
                history = db.execute("SELECT * FROM application_events WHERE job_id=? ORDER BY revision", (identifier,)).fetchall()
                validate_history([dict(zip(EVENT_FIELDS, row)) for row in history])
            for table, rows in (("career_profiles", profile_rows), ("resume_versions", resume_rows)):
                for row in rows:
                    existing = db.execute(f"SELECT * FROM {table} WHERE id=?", (row[0],)).fetchone()
                    if existing is not None:
                        if existing != row:
                            raise ValueError("Archived version ID conflicts; nothing restored")
                        continue
                    db.execute(f"INSERT INTO {table} VALUES (?, ?, ?, ?)", row)
            if active_id is not None and db.execute("SELECT value FROM app_settings WHERE key='active_profile'").fetchone() is None:
                db.execute("INSERT INTO app_settings VALUES ('active_profile', ?)", (active_id,))
        return added, skipped
