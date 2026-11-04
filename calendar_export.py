"""RFC 5545 all-day follow-up export; no calendar account access or invitations."""
from datetime import date, datetime, timedelta, timezone
import hashlib

from applications import current_application, validate_history
from roleweave import review_snapshot


def calendar_text(value):
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ValueError("Calendar text contains unsupported control characters")
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def folded(line):
    """Fold to 75 UTF-8 octets without splitting a code point (RFC 5545 3.1)."""
    parts, current, size = [], "", 0
    for char in line:
        width = len(char.encode("utf-8"))
        if size + width > 75:
            parts.append(current)
            current, size = " ", 1
        current += char
        size += width
    parts.append(current)
    return "\r\n".join(parts)


def follow_up_calendar(item, events):
    source = review_snapshot(item["snapshot"])
    if source["input_sha256"] != item["input_sha256"]:
        raise ValueError("Saved review fingerprint mismatch")
    validate_history(events)
    if any(event["job_id"] != item["id"] for event in events):
        raise ValueError("Calendar history belongs to another saved review")
    current = current_application(events)
    if not current["follow_up"] or current["stage"] in ("closed", "withdrawn"):
        raise ValueError("Record an active follow-up date before calendar export")
    start = date.fromisoformat(current["follow_up"])
    try:
        end = start + timedelta(days=1)
    except OverflowError:
        raise ValueError("Follow-up date is too late for an exclusive calendar end date") from None
    stamp = datetime.fromisoformat(current["recorded_at"]).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    uid = hashlib.sha256(item["id"].encode("utf-8")).hexdigest() + "@roleweave.local"
    description = (f"RoleWeave saved review: {item['id']}\nManual stage: {current['stage']}\n"
                   f"History revision: {current['revision']}\nThis is a follow-up reminder, not an application submission. "
                   "Later corrections must be re-exported. Calendar import/update behavior depends on your calendar app.")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//RoleWeave//Follow-up Export//EN", "CALSCALE:GREGORIAN",
             "BEGIN:VEVENT", "UID:" + uid, "DTSTAMP:" + stamp, "SEQUENCE:" + str(current["revision"]),
             "DTSTART;VALUE=DATE:" + start.isoformat().replace("-", ""), "DTEND;VALUE=DATE:" + end.isoformat().replace("-", ""),
             "SUMMARY:" + calendar_text("Follow up: " + item["company"] + " - " + item["title"]),
             "DESCRIPTION:" + calendar_text(description), "CLASS:PRIVATE", "TRANSP:TRANSPARENT", "STATUS:CONFIRMED",
             "END:VEVENT", "END:VCALENDAR"]
    payload = ("\r\n".join(folded(line) for line in lines) + "\r\n").encode("utf-8")
    if len(payload) > 1024 * 1024:
        raise ValueError("Calendar export exceeds 1 MiB")
    return payload
