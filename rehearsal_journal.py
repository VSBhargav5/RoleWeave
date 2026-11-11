"""Private source-bound rehearsal drafts. Time and text do not verify learning."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from career_profile import unique_json
from resume_versions import decoded, job_context, validate_job_context
from roleweave import MAX_BYTES, review_snapshot, text
from safe_export import publish_bytes

MAX_REHEARSAL_BYTES = 4 * 1024 * 1024
MAX_PRACTICE_SECONDS = 86400


def validate_rehearsal(record):
    keys = {"format", "job_context", "answers", "recorded_at", "elapsed_seconds", "learning_verified"}
    if not isinstance(record, dict) or set(record) != keys or record["format"] != "roleweave-rehearsal-v1":
        raise ValueError("Unsupported rehearsal journal")
    context = validate_job_context(record["job_context"])
    source = review_snapshot(decoded(context["snapshot_base64"], MAX_BYTES))
    identifiers = {row["id"] for row in source["requirements"]}
    if not isinstance(record["answers"], list) or not 1 <= len(record["answers"]) <= 30:
        raise ValueError("Choose 1-30 exact requirement questions")
    seen = set()
    for answer in record["answers"]:
        if not isinstance(answer, dict) or set(answer) != {"requirement_id", "answer", "reflection"}:
            raise ValueError("Each rehearsal draft needs requirement_id, answer and reflection")
        identifier = answer["requirement_id"]
        if not isinstance(identifier, str) or identifier not in identifiers or identifier in seen:
            raise ValueError("Select distinct requirement IDs from the exact frozen review")
        seen.add(identifier)
        for key, limit in (("answer", 6000), ("reflection", 2000)):
            value = answer[key]
            if not isinstance(value, str) or len(value) > limit:
                raise ValueError("Rehearsal " + key + " exceeds its text limit")
            if value.strip():
                text(value, "Rehearsal " + key)
            elif any(char not in " \t\r\n" for char in value):
                raise ValueError("Rehearsal draft contains unsupported whitespace")
    seconds = record["elapsed_seconds"]
    if type(seconds) is not int or not 0 <= seconds <= MAX_PRACTICE_SECONDS:
        raise ValueError("Recorded practice time must be an integer from 0 to 86400 seconds")
    if record["learning_verified"] is not False:
        raise ValueError("A rehearsal journal cannot assert verified learning")
    if not isinstance(record["recorded_at"], str) or len(record["recorded_at"]) > 100:
        raise ValueError("Rehearsal recorded_at needs a timezone")
    try:
        if datetime.fromisoformat(record["recorded_at"]).utcoffset() is None:
            raise ValueError()
    except ValueError:
        raise ValueError("Rehearsal recorded_at needs a valid timezone") from None
    return record


def rehearsal_snapshot(snapshot):
    if not isinstance(snapshot, bytes) or len(snapshot) > MAX_REHEARSAL_BYTES:
        raise ValueError("Private rehearsal version exceeds 4 MiB")
    try:
        record = json.loads(snapshot, object_pairs_hook=unique_json)
    except (UnicodeError, json.JSONDecodeError, TypeError, RecursionError):
        raise ValueError("Invalid rehearsal JSON") from None
    return validate_rehearsal(record), hashlib.sha256(snapshot).hexdigest()


def make_rehearsal(item, answers, *, elapsed_seconds=0, confirmed=False):
    if confirmed is not True:
        raise ValueError("Review and confirm this private rehearsal version")
    record = {"format": "roleweave-rehearsal-v1", "job_context": job_context(item), "answers": answers,
              "recorded_at": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": elapsed_seconds,
              "learning_verified": False}
    validate_rehearsal(record)
    snapshot = json.dumps(record, ensure_ascii=True, indent=2).encode()
    rehearsal_snapshot(snapshot)
    return snapshot


def read_rehearsal(path):
    with Path(path).open("rb") as handle:
        snapshot = handle.read(MAX_REHEARSAL_BYTES + 1)
    return snapshot, rehearsal_snapshot(snapshot)[0]


def export_rehearsal(snapshot, destination, *, confirmed=False):
    if confirmed is not True:
        raise ValueError("Review and confirm private rehearsal export")
    rehearsal_snapshot(snapshot)
    if Path(destination).suffix.lower() != ".json":
        raise ValueError("Choose a .json rehearsal version filename")
    publish_bytes(destination, snapshot)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", type=Path)
    parser.add_argument("--export", type=Path)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    snapshot, record = read_rehearsal(args.journal)
    if args.export:
        export_rehearsal(snapshot, args.export, confirmed=args.confirm)
    print(json.dumps({"job": record["job_context"]["title"], "company": record["job_context"]["company"],
                      "questions": len(record["answers"]), "nonblank_drafts": sum(bool(row["answer"].strip()) for row in record["answers"]),
                      "elapsed_seconds": record["elapsed_seconds"], "learning_verified": False}, indent=2))
