"""Bounded byte-exact discovery archives. Integrity does not establish authenticity."""
import base64
import binascii
from datetime import datetime
import hashlib
import json
from pathlib import Path
from discovery import MAX_FEED_BYTES
from network_io import json_object
from provider_boards import parse_source
from safe_export import publish_bytes
MAX_ARCHIVE_BYTES = 12 * 1024 * 1024

def archive_bytes(feed):
    raw = feed.get("source_snapshot")
    if not isinstance(raw, bytes):
        raise ValueError("Original response unavailable; fetch again before exporting")
    replay = parse_source(raw, feed["provider"], feed["token"])
    if replay["jobs"] != feed["jobs"] or replay["response_sha256"] != feed["response_sha256"]:
        raise ValueError("Results no longer match original response bytes")
    try:
        if datetime.fromisoformat(feed["fetched_at"]).utcoffset() is None:
            raise ValueError()
    except (TypeError, ValueError):
        raise ValueError("Observation time requires timezone") from None
    return json.dumps({"format": "roleweave-discovery-v1", "provider": feed["provider"],
        "token": feed["token"], "observed_at": feed["fetched_at"],
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_base64": base64.b64encode(raw).decode("ascii")}, indent=2).encode()

def export_archive(feed, destination):
    publish_bytes(destination, archive_bytes(feed))

def load_archive(source):
    with Path(source).open("rb") as handle:
        snapshot = handle.read(MAX_ARCHIVE_BYTES + 1)
    if len(snapshot) > MAX_ARCHIVE_BYTES:
        raise ValueError("Discovery archive exceeds 12 MiB")
    data = json_object(snapshot)
    keys = {"format", "provider", "token", "observed_at", "source_sha256", "source_base64"}
    if not isinstance(data, dict) or set(data) != keys or data["format"] != "roleweave-discovery-v1":
        raise ValueError("Unsupported discovery archive")
    try:
        raw = base64.b64decode(data["source_base64"], validate=True)
    except (ValueError, TypeError, binascii.Error):
        raise ValueError("Invalid archive source encoding") from None
    if len(raw) > MAX_FEED_BYTES or hashlib.sha256(raw).hexdigest() != data["source_sha256"]:
        raise ValueError("Archive source fingerprint mismatch")
    feed = parse_source(raw, data["provider"], data["token"])
    feed["fetched_at"] = data["observed_at"]
    archive_bytes(feed)
    return feed


def compare_observations(before, after):
    if (before["provider"], before["token"]) != (after["provider"], after["token"]):
        raise ValueError("Compare observations of the same provider and board only")
    old = {row["id"]: row for row in before["jobs"]}
    new = {row["id"]: row for row in after["jobs"]}
    result = []
    for identifier in sorted(old.keys() | new.keys(), key=str):
        left, right = old.get(identifier), new.get(identifier)
        state = "added" if left is None else "not_observed" if right is None else "unchanged" if left == right else "changed"
        row = right if right is not None else left
        result.append({"state": state, "id": identifier, "title": row["title"], "url": row["url"]})
    return result


