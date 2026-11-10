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


def verify_dossier(source):
    """Read without extraction, check every member and replay document contracts."""
    from network_io import json_object
    with Path(source).open("rb") as handle:
        payload = handle.read(MAX_DOSSIER_BYTES + 1)
    if len(payload) > MAX_DOSSIER_BYTES:
        raise ValueError("Dossier exceeds 64 MiB")
    allowed = {"manifest.json", "review.json", "resume-version.json", "history.json",
               "preparation.txt", "resume.html", "resume.txt", "resume.pdf"}
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            entries = archive.infolist()
            names = [info.filename for info in entries]
            if len(names) != len(set(names)) or not 7 <= len(names) <= 8 or not set(names) <= allowed:
                raise ValueError("Unexpected or duplicate dossier members")
            if sum(info.file_size for info in entries) > MAX_DOSSIER_BYTES:
                raise ValueError("Expanded dossier exceeds 64 MiB")
            if any(info.flag_bits & 1 or info.compress_type != zipfile.ZIP_STORED for info in entries):
                raise ValueError("Unsupported encrypted or recompressed dossier")
            parts = {info.filename: archive.read(info) for info in entries}
        manifest = json_object(parts.pop("manifest.json"))
        keys = {"format", "contains_private_evidence", "submission_verified", "job",
                "resume_id", "resume_snapshot_sha256", "history_revision", "files"}
        if not isinstance(manifest, dict) or set(manifest) != keys or manifest["format"] != "roleweave-dossier-v1":
            raise ValueError("Unsupported dossier manifest")
        if manifest["contains_private_evidence"] is not True or manifest["submission_verified"] is not False:
            raise ValueError("Unsupported dossier privacy/submission declaration")
        if not isinstance(manifest["files"], dict) or set(manifest["files"]) != set(parts):
            raise ValueError("Manifest members do not match archive")
        for name, value in manifest["files"].items():
            if not isinstance(value, dict) or set(value) != {"sha256", "bytes"} or type(value["bytes"]) is not int:
                raise ValueError("Invalid member fingerprint")
            if value["bytes"] != len(parts[name]) or value["sha256"] != hashlib.sha256(parts[name]).hexdigest():
                raise ValueError("Dossier member fingerprint mismatch")
        record, digest = resume_snapshot(parts["resume-version.json"])
        events = json_object(parts["history.json"])
        if not isinstance(events, list) or type(manifest["history_revision"]) is not int:
            raise ValueError("Invalid dossier history")
        item = manifest["job"]
        if not isinstance(item, dict) or set(item) != set(JOB_FIELDS):
            raise ValueError("Invalid dossier job context")
        item = dict(item, snapshot=parts["review.json"])
        resume = {"id": manifest["resume_id"], "snapshot": parts["resume-version.json"],
                  "snapshot_sha256": manifest["resume_snapshot_sha256"]}
        text(resume["id"], "Resume version ID")
        expected = dossier_parts(item, resume, events)
        if parts != expected or manifest["history_revision"] != (events[-1]["revision"] if events else 0):
            raise ValueError("Dossier documents do not replay from frozen evidence")
        return {"job": manifest["job"], "resume_id": resume["id"],
                "history_revision": manifest["history_revision"], "file_count": len(parts),
                "sha256": hashlib.sha256(payload).hexdigest(), "submission_verified": False}
    except (zipfile.BadZipFile, KeyError, TypeError, RuntimeError, NotImplementedError) as exc:
        raise ValueError("Invalid or unsupported private dossier") from None


def main():
    from job_store import JobStore
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path, help="Verify an existing dossier without opening a shelf")
    parser.add_argument("--db", type=Path)
    parser.add_argument("--job")
    parser.add_argument("--resume")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--confirm-private", action="store_true")
    args = parser.parse_args()
    if args.verify:
        if any((args.db, args.job, args.resume, args.output, args.confirm_private)):
            parser.error("--verify cannot be combined with export arguments")
        print(json.dumps(verify_dossier(args.verify), indent=2))
        return
    if not all((args.db, args.job, args.resume, args.output)):
        parser.error("Export requires --db, --job, --resume and --output")
    if not args.db.is_file():
        parser.error("Existing shelf database required; no database was created")
    if not args.confirm_private:
        parser.error("Private evidence export requires --confirm-private")
    print(export_dossier(JobStore(args.db), args.job, args.resume, args.output, confirmed=True))


if __name__ == "__main__":
    main()
