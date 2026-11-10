"""Explicit public employer boards, with bounded offline replay and source identity."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from discovery import MAX_FEED_BYTES, board_path, parse_board, plain_posting
from network_io import json_object, request_bytes
from roleweave import text
from source_links import source_link

PROVIDERS = ("greenhouse", "lever", "lever-eu")


def source_endpoint(provider, token):
    board_path(token)  # shared conservative token grammar, never arbitrary URLs
    if provider == "greenhouse":
        return "boards-api.greenhouse.io", board_path(token)
    if provider in ("lever", "lever-eu"):
        host = "api.lever.co" if provider == "lever" else "api.eu.lever.co"
        return host, f"/v0/postings/{token}?mode=json&limit=1000"
    raise ValueError("Unsupported discovery provider")


def field(value, label, *, optional=False):
    if optional and value in (None, ""):
        return "Not stated"
    text(value, label)
    if len(value) > 2000:
        raise ValueError(label + " exceeds 2000 characters")
    return value


def source_row(provider, token, record, identifier, title, url, location, observed_time, body):
    source_link(url)
    text(body, "Posting description")
    digest = hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    posting = (f"Provider: {provider}\nBoard: {token}\nPost identity: {identifier}\nSource: {url}\n"
               f"Provider time label: {observed_time}\nLocation label: {location}\n"
               f"Provider record SHA256 (normalized JSON): {digest}\n\n{body}")
    text(posting, "Posting")
    return {"id": identifier, "title": field(title, "Title"), "url": url,
            "location": location, "updated_at": observed_time, "posting": posting}


def parse_source(snapshot, provider, token):
    source_endpoint(provider, token)
    if len(snapshot) > MAX_FEED_BYTES:
        raise ValueError("Board exceeds 8 MiB")
    if provider == "greenhouse":
        feed = parse_board(snapshot, token)
    else:
        records = json_object(snapshot)
        if not isinstance(records, list) or len(records) >= 1000:
            raise ValueError("Unsupported or potentially truncated Lever board (1000-post limit)")
        rows, seen = [], set()
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Unsupported Lever record")
            identifier = field(record.get("id"), "Lever ID")
            if identifier in seen:
                raise ValueError("Duplicate Lever ID")
            seen.add(identifier)
            categories = record.get("categories")
            if not isinstance(categories, dict):
                raise ValueError("Missing Lever categories")
            body = text(record.get("descriptionPlain"), "Lever description")
            lists = record.get("lists", [])
            if not isinstance(lists, list) or len(lists) > 100:
                raise ValueError("Unsupported Lever description lists")
            for section in lists:
                if not isinstance(section, dict):
                    raise ValueError("Unsupported Lever list")
                body += "\n\n" + field(section.get("text"), "List title") + "\n" + plain_posting(section.get("content"))
            for key in ("additionalPlain", "salaryDescriptionPlain"):
                value = record.get(key, "")
                if value:
                    body += "\n\n" + text(value, key)
            rows.append(source_row(provider, token, record, identifier, record.get("text"),
                                   record.get("hostedUrl"), field(categories.get("location"), "Location", optional=True),
                                   "Not supplied by this Lever adapter", body))
        feed = {"jobs": rows, "token": token, "fetched_at": datetime.now(timezone.utc).isoformat(),
                "response_sha256": hashlib.sha256(snapshot).hexdigest()}
    feed.update(provider=provider, source_snapshot=snapshot)
    return feed


def fetch_source(provider, token, cancel=None):
    host, path = source_endpoint(provider, token)
    return parse_source(request_bytes(host, path, cancel=cancel, limit=MAX_FEED_BYTES), provider, token)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=PROVIDERS, required=True)
    parser.add_argument("--token", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Replay one saved raw provider JSON without networking")
    source.add_argument("--fetch", action="store_true", help="Explicitly GET a public employer board")
    args = parser.parse_args()
    if args.input:
        with args.input.open("rb") as handle:
            snapshot = handle.read(MAX_FEED_BYTES + 1)
        feed = parse_source(snapshot, args.provider, args.token)
    else:
        feed = fetch_source(args.provider, args.token)
    print(json.dumps({k: v for k, v in feed.items() if k != "source_snapshot"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
