"""Deterministic reviewed cover-letter versions, without generated career claims."""
import hashlib
import json
from pathlib import Path

from career_profile import profile_snapshot, unique_json
from resume_render import selected_facts
from letter_render import letter_pdf
from resume_versions import decoded, encoded, job_context, validate_job_context as checked_context
from roleweave import MAX_BYTES, text
from safe_export import publish_bytes

MAX_LETTER_BYTES = 4 * 1024 * 1024


def render_letter(profile, identifiers, context, motivation, closing):
    checked_context(context)
    facts = selected_facts(profile, identifiers)
    for value, label, limit in ((motivation, "Your introduction", 6000), (closing, "Your closing", 2000)):
        text(value, label)
        if len(value) > limit:
            raise ValueError(label + " exceeds its length limit")
    lines = [profile["name"], " | ".join(profile[key] for key in ("email", "phone") if profile[key]), "",
             "Dear hiring team,", "",
             f"I am applying for the {context['title']} role at {context['company']}.", "",
             motivation, "", "Selected examples from my reviewed record:", ""]
    for fact in facts:
        lines.extend([fact["section"] + ": " + fact["claim"], ""])
    lines.extend([closing, "", profile["name"], ""])
    payload = "\n".join(lines).encode("utf-8")
    if len(payload) > 65536:
        raise ValueError("Cover letter exceeds 64 KiB; select fewer claims")
    return payload


def make_letter(profile_item, identifiers, job, motivation, closing, *, confirmed=False, include_pdf=False):
    if type(include_pdf) is not bool:
        raise ValueError("Choose whether to include PDF")
    if confirmed is not True:
        raise ValueError("Review and confirm the cover letter before freezing it")
    profile, digest = profile_snapshot(profile_item["snapshot"])
    if digest != profile_item["snapshot_sha256"]:
        raise ValueError("Career profile fingerprint mismatch")
    context = checked_context(job_context(job))
    payload = render_letter(profile, identifiers, context, motivation, closing)
    record = {"format": "roleweave-letter-v1", "profile_id": profile_item["id"],
              "profile_sha256": digest, "profile_snapshot_base64": encoded(profile_item["snapshot"]),
              "job_context": context, "selected_fact_ids": identifiers, "motivation": motivation,
              "closing": closing, "text": payload.decode("utf-8"), "text_sha256": hashlib.sha256(payload).hexdigest()}
    if include_pdf:
        pdf = letter_pdf(profile["name"], record["text"])
        record.update(format="roleweave-letter-v2", pdf_base64=encoded(pdf), pdf_sha256=hashlib.sha256(pdf).hexdigest())
    snapshot = json.dumps(record, ensure_ascii=True, indent=2).encode()
    letter_snapshot(snapshot)
    return snapshot


def letter_snapshot(snapshot):
    if not isinstance(snapshot, bytes) or len(snapshot) > MAX_LETTER_BYTES:
        raise ValueError("Private letter version exceeds 4 MiB")
    try:
        record = json.loads(snapshot, object_pairs_hook=unique_json)
    except (UnicodeError, json.JSONDecodeError, TypeError, RecursionError):
        raise ValueError("Invalid cover-letter JSON") from None
    keys = {"format", "profile_id", "profile_sha256", "profile_snapshot_base64", "job_context",
            "selected_fact_ids", "motivation", "closing", "text", "text_sha256"}
    if isinstance(record, dict) and record.get("format") == "roleweave-letter-v2":
        keys.update(("pdf_base64", "pdf_sha256"))
    if not isinstance(record, dict) or set(record) != keys or record["format"] not in ("roleweave-letter-v1", "roleweave-letter-v2"):
        raise ValueError("Unsupported cover-letter version")
    text(record["profile_id"], "Profile version ID")
    profile, digest = profile_snapshot(decoded(record["profile_snapshot_base64"], MAX_BYTES))
    if digest != record["profile_sha256"]:
        raise ValueError("Cover-letter profile fingerprint mismatch")
    payload = render_letter(profile, record["selected_fact_ids"], record["job_context"], record["motivation"], record["closing"])
    if record["text"] != payload.decode("utf-8") or record["text_sha256"] != hashlib.sha256(payload).hexdigest():
        raise ValueError("Cover letter does not replay from its reviewed sources")
    if record["format"] == "roleweave-letter-v2":
        pdf = decoded(record["pdf_base64"], 2*1024*1024)
        if hashlib.sha256(pdf).hexdigest() != record["pdf_sha256"] or pdf != letter_pdf(profile["name"], record["text"]):
            raise ValueError("Cover-letter PDF does not replay from reviewed text")
    return record, hashlib.sha256(snapshot).hexdigest()


def read_letter(path):
    with Path(path).open("rb") as handle:
        snapshot = handle.read(MAX_LETTER_BYTES + 1)
    return snapshot, letter_snapshot(snapshot)[0]


def export_letter(snapshot, destination, format, *, confirmed=False):
    if confirmed is not True:
        raise ValueError("Review and confirm letter export")
    record, _digest = letter_snapshot(snapshot)
    if format not in ("json", "txt", "pdf") or Path(destination).suffix.lower() != "." + format:
        raise ValueError("Choose a matching .json private version, .txt or .pdf document filename")
    if format == "pdf" and "pdf_base64" not in record:
        raise ValueError("This older letter has no frozen PDF; create a new PDF letter version")
    publish_bytes(destination, snapshot if format == "json" else decoded(record["pdf_base64"],2*1024*1024) if format == "pdf" else record["text"].encode("utf-8"))
