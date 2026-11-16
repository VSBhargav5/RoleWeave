"""Reviewed local email drafts with exact frozen recipient PDFs; never sends mail."""
from datetime import datetime, timezone
from email import policy
from email.errors import HeaderParseError
from email.headerregistry import Address
from email.message import EmailMessage
import hashlib
import json
import re

from career_profile import unique_json
from cover_letter import letter_snapshot
from resume_versions import decoded, encoded, job_context, resume_snapshot
from roleweave import text

MAX_EMAIL_SNAPSHOT = 8 * 1024 * 1024
FIELDS = {"job_id", "resume_id", "letter_id", "sender", "recipient", "subject", "body"}


def address(value):
    if not isinstance(value, str) or not 3 <= len(value) <= 254 or not value.isascii() or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("Enter one plain email address without display names or extra headers")
    try:
        parsed = Address(addr_spec=value)
        if parsed.addr_spec != value or not parsed.username or "." not in parsed.domain:
            raise ValueError()
    except (ValueError, IndexError, HeaderParseError):
        raise ValueError("Enter one plain email address without display names or extra headers") from None
    return value


def validate_values(values):
    if not isinstance(values, dict) or set(values) != FIELDS:
        raise ValueError("Unsupported or missing application email fields")
    for key in ("job_id", "resume_id"):
        text(values[key], key)
        if len(values[key]) > 200: raise ValueError("Invalid source identity")
    if not isinstance(values["letter_id"], str) or (values["letter_id"] and not re.fullmatch(r"[a-f0-9]{32}", values["letter_id"])):
        raise ValueError("Invalid letter identity")
    address(values["sender"]); address(values["recipient"])
    for key, limit in (("subject", 200), ("body", 10000)):
        text(values[key], "Email " + key)
        if len(values[key]) > limit: raise ValueError("Email " + key + " exceeds its limit")
    if any(ord(c) < 32 or ord(c) == 127 for c in values["subject"]):
        raise ValueError("Email subject must be one line")
    return values


def documents(store, values, letter=b""):
    validate_values(values)
    item = store.load_resume(values["resume_id"])
    resume, digest = resume_snapshot(item["snapshot"])
    if item["snapshot_sha256"] != digest or resume["job_context"] != job_context(store.load(values["job_id"])):
        raise ValueError("Choose a resume frozen for this exact saved review")
    pdf = decoded(resume["pdf_base64"], 8 * 1024 * 1024)
    if not pdf: raise ValueError("Choose a frozen PDF resume")
    attachments = [("resume.pdf", pdf)]
    if bool(values["letter_id"]) != bool(letter): raise ValueError("Selected letter source is missing or unexpected")
    if letter:
        record, _ = letter_snapshot(letter)
        if record["job_context"] != resume["job_context"] or record["profile_id"] != resume["profile_id"] or record["profile_sha256"] != resume["profile_sha256"]:
            raise ValueError("Cover letter and resume must use the same exact review and frozen profile")
        pdf = decoded(record.get("pdf_base64", ""), 2 * 1024 * 1024)
        if not pdf: raise ValueError("Choose a matching PDF cover letter, or no letter")
        attachments.append(("cover-letter.pdf", pdf))
    return digest, attachments


def mime_bytes(values, attachments):
    message = EmailMessage(policy=policy.SMTP)
    message["From"] = address(values["sender"]); message["To"] = address(values["recipient"])
    message["Subject"] = values["subject"]; message["X-Unsent"] = "1"
    message.set_content(values["body"].replace("\r\n", "\n").replace("\r", "\n"), charset="utf-8")
    for name, payload in attachments:
        message.add_attachment(payload, maintype="application", subtype="pdf", filename=name)
    binding = {"values": values, "files": [(n, hashlib.sha256(b).hexdigest()) for n, b in attachments]}
    message.set_boundary("roleweave-" + hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest())
    payload = message.as_bytes()
    if len(payload) > 16 * 1024 * 1024: raise ValueError("Email draft exceeds 16 MiB")
    return payload


def email_snapshot(snapshot):
    if not isinstance(snapshot, bytes) or len(snapshot) > MAX_EMAIL_SNAPSHOT: raise ValueError("Application email record exceeds 8 MiB")
    try: record = json.loads(snapshot, object_pairs_hook=unique_json)
    except (ValueError, UnicodeError, RecursionError): raise ValueError("Invalid application email record") from None
    keys = {"format", "values", "resume_sha256", "letter_base64", "eml_sha256", "created_at"}
    if not isinstance(record, dict) or set(record) != keys or record["format"] != "roleweave-application-email-v1":
        raise ValueError("Unsupported application email record")
    validate_values(record["values"])
    for key in ("resume_sha256", "eml_sha256"):
        if not isinstance(record[key], str) or not re.fullmatch(r"[a-f0-9]{64}", record[key]): raise ValueError("Invalid email source fingerprint")
    letter = decoded(record["letter_base64"], 4 * 1024 * 1024)
    if letter: letter_snapshot(letter)
    if bool(letter) != bool(record["values"]["letter_id"]): raise ValueError("Invalid saved letter binding")
    try:
        if not isinstance(record["created_at"], str) or len(record["created_at"]) > 100 or datetime.fromisoformat(record["created_at"]).utcoffset() is None: raise ValueError()
    except ValueError: raise ValueError("Invalid draft creation timestamp") from None
    return record


def make_email_snapshot(store, values, letter=b""):
    digest, attachments = documents(store, values, letter)
    payload = mime_bytes(values, attachments)
    record = {"format": "roleweave-application-email-v1", "values": values, "resume_sha256": digest,
              "letter_base64": encoded(letter), "eml_sha256": hashlib.sha256(payload).hexdigest(),
              "created_at": datetime.now(timezone.utc).isoformat()}
    snapshot = json.dumps(record, ensure_ascii=True).encode()
    email_snapshot(snapshot)
    return snapshot


def replay_email(store, snapshot):
    record = email_snapshot(snapshot)
    digest, attachments = documents(store, record["values"], decoded(record["letter_base64"], 4 * 1024 * 1024))
    payload = mime_bytes(record["values"], attachments)
    if digest != record["resume_sha256"] or hashlib.sha256(payload).hexdigest() != record["eml_sha256"]:
        raise ValueError("Application email document or message fingerprint differs")
    return record, payload, [{"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in attachments]


def preview_fingerprint(record):
    return hashlib.sha256(json.dumps({k: v for k, v in record.items() if k != "created_at"}, sort_keys=True).encode()).hexdigest()
