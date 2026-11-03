"""Deterministic plain-text preparation pack; no resume generation or rewriting."""
import textwrap

from applications import current_application
from roleweave import review_snapshot

MAX_PACK_BYTES = 8 * 1024 * 1024


def build_pack(item, events):
    result = review_snapshot(item["snapshot"])
    if result["input_sha256"] != item["input_sha256"] or result["market"] != item["market"]:
        raise ValueError("Saved source fingerprint or market does not match")
    if any(event["job_id"] != item["id"] for event in events):
        raise ValueError("Tracking history belongs to another saved snapshot")
    current = current_application(events)
    lines = ["ROLEWEAVE APPLICATION PREPARATION PACK · v1",
             "Human-selected evidence and manually recorded observations.",
             "Not a submitted application, verified qualification, resume or ATS score.", ""]

    def field(label, value):
        lines.append(label)
        lines.append(textwrap.indent(str(value), "  ", lambda _line: True))

    for label, value in (("Job title", item["title"]), ("Company", item["company"]),
                         ("Source URL", item["source_url"] or "Not recorded"),
                         ("Market label (eligibility unverified)", item["market"]),
                         ("Saved snapshot ID", item["id"]), ("Captured at", item["captured_at"]),
                         ("Original JSON SHA-256", result["input_sha256"]),
                         ("Posting SHA-256", result["posting_sha256"]),
                         ("Manual stage", current["stage"]), ("Follow-up date", current["follow_up"] or "None"),
                         ("History revision included", events[-1]["revision"] if events else 0)):
        field(label, value)
    lines.extend(["", "REQUIREMENT QUOTES AND SELECTED LINKS"])
    selected = {}
    for requirement in result["requirements"]:
        field(f"Requirement {requirement['id']} · {requirement['state']}", requirement["quote"])
        field("Selected fact IDs", ", ".join(fact["id"] for fact in requirement["evidence"]) or "None · needs human review; not proof of a missing skill")
        for fact in requirement["evidence"]:
            selected[fact["id"]] = fact
    if not result["requirements"]:
        lines.append("No requirements have been recorded. Completeness is unknown.")
    lines.extend(["", "SELECTED CLAIMS · copied exactly, not independently verified"])
    for fact in selected.values():
        field(f"Fact {fact['id']}", fact["claim"])
        field("Claim source / provenance", fact["source"])
    if not selected:
        lines.append("No reviewed linked claims selected.")
    lines.extend(["", "MANUAL APPLICATION OBSERVATIONS"])
    for event in events:
        field(f"Revision {event['revision']} · {event['recorded_at']} · {event['stage']}", event["note"] or "No note")
        field("Follow-up", event["follow_up"] or "None")
    if not events:
        lines.append("No observations recorded. No submission has been verified.")
    lines.extend(["", "CHECK BEFORE USING", "Confirm eligibility, source freshness and each selected claim yourself.",
                  "An open requirement is a review question. A link is not proof of relevance or qualification.",
                  "Keep this unencrypted pack private; it includes job details and any recorded notes.", ""])
    payload = "\n".join(lines).encode("utf-8")
    if len(payload) > MAX_PACK_BYTES:
        raise ValueError("Preparation pack exceeds 8 MiB; no file created")
    return payload
