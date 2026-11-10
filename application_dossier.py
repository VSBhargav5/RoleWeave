"""Private application dossiers bind an exact saved review to a frozen resume."""
import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import zipfile

from applications import validate_history
from career_profile import profile_snapshot
from preparation_pack import build_pack
from resume_render import resume_text
from resume_versions import decoded, resume_snapshot
from roleweave import MAX_BYTES, review_snapshot, text
from safe_export import publish_bytes

MAX_DOSSIER_BYTES = 64 * 1024 * 1024
JOB_FIELDS = ("id", "title", "company", "source_url", "market", "captured_at", "input_sha256")


def dossier_parts(item, resume_item, events):
    record, digest = resume_snapshot(resume_item["snapshot"])
    if digest != resume_item["snapshot_sha256"]:
        raise ValueError("Frozen resume fingerprint mismatch")
    context = record["job_context"]
    if context is None or {key: context[key] for key in JOB_FIELDS} != {key: item[key] for key in JOB_FIELDS}:
        raise ValueError("Select a resume frozen for this exact saved review")
    if decoded(context["snapshot_base64"], MAX_BYTES) != item["snapshot"]:
        raise ValueError("Resume context differs from the exact original review bytes")
    review_snapshot(item["snapshot"])
    validate_history(events)
    if any(event["job_id"] != item["id"] for event in events):
        raise ValueError("History belongs to a different saved review")
    profile, _digest = profile_snapshot(decoded(record["profile_snapshot_base64"], MAX_BYTES))
    parts = {"review.json": item["snapshot"], "resume-version.json": resume_item["snapshot"],
             "history.json": json.dumps(events, ensure_ascii=True).encode(),
             "preparation.txt": build_pack(item, events),
             "resume.html": decoded(record["html_base64"], 8 * 1024 * 1024),
             "resume.txt": resume_text(profile, record["selected_fact_ids"]).encode("utf-8")}
    if record["pdf_base64"]:
        parts["resume.pdf"] = decoded(record["pdf_base64"], 8 * 1024 * 1024)
    return parts


def build_dossier(item, resume_item, events):
    text(resume_item["id"], "Resume version ID")
    parts = dossier_parts(item, resume_item, events)
    manifest = {"format": "roleweave-dossier-v1", "contains_private_evidence": True,
                "submission_verified": False, "job": {key: item[key] for key in JOB_FIELDS},
                "resume_id": resume_item["id"], "resume_snapshot_sha256": resume_item["snapshot_sha256"],
                "history_revision": events[-1]["revision"] if events else 0,
                "files": {name: {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
                          for name, payload in parts.items()}}
    parts["manifest.json"] = json.dumps(manifest, ensure_ascii=True, indent=2).encode()
    if sum(map(len, parts.values())) > MAX_DOSSIER_BYTES - 16384:
        raise ValueError("Private dossier exceeds the 64 MiB limit")
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as output:
        for name, payload in parts.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            output.writestr(info, payload)
    payload = archive.getvalue()
    if len(payload) > MAX_DOSSIER_BYTES:
        raise ValueError("Private dossier exceeds the 64 MiB limit")
    return payload


def export_dossier(store, job_id, resume_id, destination, *, confirmed=False):
    if confirmed is not True:
        raise ValueError("Review and confirm private dossier export")
    if Path(destination).suffix.lower() != ".zip":
        raise ValueError("Choose a .zip filename")
    item = store.load(job_id)
    resume = store.load_resume(resume_id)
    payload = build_dossier(item, resume, store.application_history(job_id))
    publish_bytes(destination, payload)
    return hashlib.sha256(payload).hexdigest()


def main():
    from job_store import JobStore
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--resume", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-private", action="store_true")
    args = parser.parse_args()
    if not args.db.is_file():
        parser.error("Existing shelf database required; no database was created")
    if not args.confirm_private:
        parser.error("Private evidence export requires --confirm-private")
    print(export_dossier(JobStore(args.db), args.job, args.resume, args.output, confirmed=True))


if __name__ == "__main__":
    main()
