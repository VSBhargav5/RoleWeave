"""Manual application observations, never proof of submission or eligibility."""
from datetime import date, datetime

from roleweave import text

STAGES = ("saved", "shortlisted", "applied", "interview", "offer", "closed", "withdrawn")
EVENT_FIELDS = ("id", "job_id", "revision", "stage", "note", "follow_up", "recorded_at")


def follow_up_date(value):
    if value == "":
        return value
    if not isinstance(value, str):
        raise ValueError("Follow-up date must be YYYY-MM-DD or blank")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Follow-up date must be YYYY-MM-DD or blank") from exc
    if parsed.isoformat() != value:
        raise ValueError("Follow-up date must be YYYY-MM-DD or blank")
    return value


def validate_event(event):
    if not isinstance(event, dict) or set(event) != set(EVENT_FIELDS):
        raise ValueError("Invalid application history fields")
    text(event["id"], "Event ID")
    text(event["job_id"], "Saved snapshot ID")
    if type(event["revision"]) is not int or not 1 <= event["revision"] <= 2147483647:
        raise ValueError("Application revision must be a positive integer")
    if not isinstance(event["stage"], str) or event["stage"] not in STAGES:
        raise ValueError("Unknown application stage")
    if not isinstance(event["note"], str) or len(event["note"]) > 4000:
        raise ValueError("Decision note must be text of at most 4000 characters")
    follow_up_date(event["follow_up"])
    text(event["recorded_at"], "Recorded time")
    try:
        if datetime.fromisoformat(event["recorded_at"]).tzinfo is None:
            raise ValueError("Recorded time needs a timezone")
    except ValueError as exc:
        raise ValueError("Recorded time needs a valid timezone-aware timestamp") from exc
    return event


def validate_history(events):
    revisions, identifiers = {}, set()
    for event in events:
        validate_event(event)
        if event["id"] in identifiers:
            raise ValueError("Duplicate application event ID")
        identifiers.add(event["id"])
        expected = revisions.get(event["job_id"], 0) + 1
        if event["revision"] != expected:
            raise ValueError("Application revisions must be contiguous and ordered per snapshot")
        revisions[event["job_id"]] = expected


def current_application(events):
    validate_history(events)
    return events[-1] if events else {"stage": "saved", "note": "", "follow_up": ""}
