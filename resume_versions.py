"""Frozen, self-contained resume versions, including exact exported bytes."""
import base64
import binascii
import hashlib
import json

from career_profile import profile_snapshot, unique_json
from resume_render import MAX_RESUME_BYTES, resume_html, resume_pdf
from roleweave import MAX_BYTES, review_snapshot, text

MAX_RESUME_SNAPSHOT = 24 * 1024 * 1024


def encoded(value):
    return base64.b64encode(value).decode("ascii")


def decoded(value, limit):
    if not isinstance(value, str) or len(value) > ((limit + 2) // 3) * 4:
        raise ValueError("Invalid or oversized encoded resume content")
    try:
        result = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid encoded resume content") from exc
    if len(result) > limit:
        raise ValueError("Resume content exceeds size limit")
    return result


def job_context(item):
    if item is None:
        return None
    return {**{key: item[key] for key in ("id", "title", "company", "source_url", "market", "captured_at", "input_sha256")},
            "snapshot_base64": encoded(item["snapshot"])}


def validate_job_context(context):
    keys = {"id", "title", "company", "source_url", "market", "captured_at", "input_sha256", "snapshot_base64"}
    if not isinstance(context, dict) or set(context) != keys:
        raise ValueError("Document requires an exact saved job context")
    for key in ("id", "title", "company", "captured_at"):
        text(context[key], "Job context " + key)
    if not isinstance(context["source_url"], str) or len(context["source_url"]) > 50000:
        raise ValueError("Invalid job context URL")
    source = review_snapshot(decoded(context["snapshot_base64"], MAX_BYTES))
    if source["input_sha256"] != context["input_sha256"] or source["market"] != context["market"]:
        raise ValueError("Document job source fingerprint mismatch")
    return context


def make_resume_version(profile, identifiers, label, job=None, include_pdf=True):
    text(label, "Resume version label")
    if len(label) > 2000 or type(include_pdf) is not bool:
        raise ValueError("Invalid resume label or PDF selection")
    data, digest = profile_snapshot(profile["snapshot"])
    if digest != profile["snapshot_sha256"]:
        raise ValueError("Profile fingerprint mismatch")
    html = resume_html(data, identifiers)
    pdf = resume_pdf(data, identifiers) if include_pdf else b""
    record = {"format": "roleweave-resume-v1", "label": label, "profile_id": profile["id"],
              "profile_sha256": digest, "profile_snapshot_base64": encoded(profile["snapshot"]),
              "selected_fact_ids": identifiers, "job_context": job_context(job),
              "html_base64": encoded(html), "html_sha256": hashlib.sha256(html).hexdigest(),
              "pdf_base64": encoded(pdf), "pdf_sha256": hashlib.sha256(pdf).hexdigest() if pdf else ""}
    snapshot = json.dumps(record, ensure_ascii=True).encode("utf-8")
    resume_snapshot(snapshot)
    return snapshot


def resume_snapshot(snapshot):
    if not isinstance(snapshot, bytes) or len(snapshot) > MAX_RESUME_SNAPSHOT:
        raise ValueError("Resume version exceeds 24 MiB")
    try:
        record = json.loads(snapshot, object_pairs_hook=unique_json)
    except (UnicodeError, json.JSONDecodeError, RecursionError, TypeError) as exc:
        raise ValueError("Invalid resume version JSON") from exc
    keys = {"format", "label", "profile_id", "profile_sha256", "profile_snapshot_base64", "selected_fact_ids",
            "job_context", "html_base64", "html_sha256", "pdf_base64", "pdf_sha256"}
    if not isinstance(record, dict) or set(record) != keys or record["format"] != "roleweave-resume-v1":
        raise ValueError("Unsupported resume version")
    text(record["label"], "Resume label")
    text(record["profile_id"], "Profile version ID")
    if len(record["label"]) > 2000:
        raise ValueError("Resume label exceeds 2000 characters")
    profile, digest = profile_snapshot(decoded(record["profile_snapshot_base64"], MAX_BYTES))
    if digest != record["profile_sha256"]:
        raise ValueError("Resume source profile fingerprint mismatch")
    html = decoded(record["html_base64"], MAX_RESUME_BYTES)
    if hashlib.sha256(html).hexdigest() != record["html_sha256"] or html != resume_html(profile, record["selected_fact_ids"]):
        raise ValueError("Resume HTML does not match selected source claims")
    pdf = decoded(record["pdf_base64"], MAX_RESUME_BYTES)
    if (pdf and (not pdf.startswith(b"%PDF-") or hashlib.sha256(pdf).hexdigest() != record["pdf_sha256"])) or (not pdf and record["pdf_sha256"] != ""):
        raise ValueError("Resume PDF fingerprint mismatch")
    context = record["job_context"]
    if context is not None:
        validate_job_context(context)
    return record, hashlib.sha256(snapshot).hexdigest()
