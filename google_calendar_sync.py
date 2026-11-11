"""Explicit one-way follow-ups in an app-created calendar. No delete or invitations."""
from datetime import date, timedelta
import hashlib
import http.client
import json
import re
import time
from urllib.parse import quote

from applications import current_application, validate_history
from roleweave import review_snapshot
from network_io import Cancelled, json_object

SCOPE = "https://www.googleapis.com/auth/calendar.app.created"
MAX_RESPONSE_BYTES = 1024 * 1024


def calendar_path(calendar_id):
    if not isinstance(calendar_id, str) or not 1 <= len(calendar_id) <= 1024 or calendar_id == "primary" or any(ord(c) < 33 or ord(c) > 126 for c in calendar_id):
        raise ValueError("Enter the ID of a RoleWeave app-created secondary calendar; primary is refused")
    return "/calendar/v3/calendars/" + quote(calendar_id, safe="") + "/events"


def desired_event(item, events, *, include_details=False):
    if type(include_details) is not bool:
        raise ValueError("Choose whether to include role/company text")
    source = review_snapshot(item["snapshot"])
    if source["input_sha256"] != item["input_sha256"]:
        raise ValueError("Saved review fingerprint mismatch")
    validate_history(events)
    if any(row["job_id"] != item["id"] for row in events):
        raise ValueError("Follow-up history belongs to another review")
    current = current_application(events)
    if not current["follow_up"] or current["stage"] in ("closed", "withdrawn"):
        raise ValueError("Record an active follow-up date first; this integration never deletes remote events")
    start = date.fromisoformat(current["follow_up"])
    try:
        end = start + timedelta(days=1)
    except OverflowError:
        raise ValueError("Follow-up date is too late for an exclusive end") from None
    identity = hashlib.sha256(item["id"].encode()).hexdigest()
    title = "Follow up: " + item["company"] + " - " + item["title"] if include_details else "RoleWeave follow-up"
    if len(title) > 1000:
        raise ValueError("Calendar summary exceeds 1000 characters; use the generic summary")
    return {"id": "re" + identity, "summary": title, "description": "Manual follow-up reminder. Not proof of an application or outcome.",
            "start": {"date": start.isoformat()}, "end": {"date": end.isoformat()},
            "visibility": "private", "transparency": "transparent", "reminders": {"useDefault": False},
            "extendedProperties": {"private": {"rwOwner": "roleweave-v1", "rwJob": identity,
                                               "rwSource": item["input_sha256"], "rwRevision": str(current["revision"])}}}


def prepare_sync(item, events, calendar_id, existing=None, *, include_details=False):
    calendar_path(calendar_id)
    desired = desired_event(item, events, include_details=include_details)
    operation, etag = "create", None
    if existing is not None:
        if not isinstance(existing, dict) or existing.get("id") != desired["id"] or existing.get("status") == "cancelled":
            raise ValueError("Remote event identity/status changed; nothing prepared")
        properties = existing.get("extendedProperties", {})
        if not isinstance(properties, dict):
            raise ValueError("Remote ownership properties are malformed")
        owned = properties.get("private", {})
        expected = desired["extendedProperties"]["private"]
        if not isinstance(owned, dict) or any(owned.get(key) != expected[key] for key in ("rwOwner", "rwJob", "rwSource")):
            raise ValueError("Remote event is not owned by this exact RoleWeave source; nothing overwritten")
        if existing.get("attendees") or existing.get("recurrence") or existing.get("recurringEventId") or existing.get("eventType", "default") != "default":
            raise ValueError("Invited, recurring or special remote events are not supported")
        etag = existing.get("etag")
        if not isinstance(etag, str) or not re.fullmatch(r'"[!#-~]{1,250}"', etag):
            raise ValueError("Remote event needs a safe ETag for conflict detection")
        operation = "unchanged" if all(existing.get(key) == value for key, value in desired.items()) else "update"
    return {"format": "roleweave-google-follow-up-v1", "calendar_id": calendar_id,
            "job_id": item["id"], "include_details": include_details,
            "operation": operation, "etag": etag, "event": desired}


def api_request(credentials, method, path, *, body=None, etag=None, cancel=None, allow_missing=False):
    if method not in ("GET", "POST", "PATCH") or not path.startswith("/calendar/v3/calendars") or not path.isascii() or any(ord(c) < 33 for c in path):
        raise ValueError("Unsupported Calendar request")
    if credentials is None or not credentials.valid:
        raise ValueError("Connect a fresh session first; no automatic token refresh")
    token = credentials.token
    if not isinstance(token, str) or not 1 <= len(token) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise ValueError("Invalid session token")
    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    if etag is not None:
        if not isinstance(etag, str) or not re.fullmatch(r'"[!#-~]{1,250}"', etag):
            raise ValueError("Invalid Calendar ETag")
        headers["If-Match"] = etag
    payload = None if body is None else json.dumps(body, ensure_ascii=True, allow_nan=False).encode()
    if payload is not None:
        if len(payload) > 65536:
            raise ValueError("Calendar request exceeds 64 KiB")
        headers["Content-Type"] = "application/json"
    connection = http.client.HTTPSConnection("www.googleapis.com", timeout=5)
    deadline = time.monotonic() + 45
    def check():
        if cancel is not None and cancel.is_set():
            raise Cancelled("Cancelled locally; a sent Calendar write may still have completed")
        if time.monotonic() >= deadline:
            raise ValueError("Calendar local deadline reached; inspect remote state before retrying")
    try:
        check()
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        if response.status == 404 and allow_missing and method == "GET":
            return None
        if response.status not in (200, 201):
            raise ValueError("Calendar returned HTTP " + str(response.status) + "; re-preview before retrying. No automatic retry or redirect.")
        if "application/json" not in response.getheader("Content-Type", "").lower():
            raise ValueError("Calendar returned unsupported content")
        chunks, size = [], 0
        while True:
            check()
            part = response.read1(min(65536, MAX_RESPONSE_BYTES + 1 - size))
            if not part:
                break
            chunks.append(part)
            size += len(part)
            if size > MAX_RESPONSE_BYTES:
                raise ValueError("Calendar response exceeds 1 MiB")
        check()
        result = json_object(b"".join(chunks))
        if not isinstance(result, dict):
            raise ValueError("Calendar returned an unsupported response")
        return result
    finally:
        connection.close()


def read_remote(credentials, calendar_id, event_id, *, cancel=None):
    if not isinstance(event_id, str) or not re.fullmatch(r"re[0-9a-f]{64}", event_id):
        raise ValueError("Invalid source-bound Calendar event ID")
    return api_request(credentials, "GET", calendar_path(calendar_id) + "/" + event_id, cancel=cancel, allow_missing=True)


def apply_sync(store, plan, credentials, *, confirmed=False, cancel=None):
    if confirmed is not True:
        raise ValueError("Review and confirm the exact Calendar event plan")
    item, events = store.load(plan["job_id"]), store.application_history(plan["job_id"])
    desired = desired_event(item, events, include_details=plan["include_details"])
    if desired != plan["event"]:
        raise ValueError("Local source/history changed; re-preview before sending")
    path = calendar_path(plan["calendar_id"])
    operation = plan["operation"]
    if operation == "unchanged":
        return {"operation": "unchanged", "id": desired["id"]}
    if operation == "create" and plan["etag"] is None:
        result = api_request(credentials, "POST", path + "?sendUpdates=none", body=desired, cancel=cancel)
    elif operation == "update" and plan["etag"] is not None:
        body = {key: value for key, value in desired.items() if key != "id"}
        result = api_request(credentials, "PATCH", path + "/" + desired["id"] + "?sendUpdates=none", body=body, etag=plan["etag"], cancel=cancel)
    else:
        raise ValueError("Unsupported Calendar plan; re-preview")
    if result.get("id") != desired["id"]:
        raise ValueError("Calendar write response could not be verified; inspect remote state before retrying")
    return {"operation": operation, "id": desired["id"]}
