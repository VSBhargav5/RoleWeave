"""Bounded private collection archives replay original source bytes without network."""
import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path

from discovery import MAX_FEED_BYTES
from employer_watchlist import validate_watchlist
from network_io import json_object
from provider_boards import parse_source
from safe_export import publish_bytes
from watchlist_fetch import MAX_COLLECTION_SOURCE_BYTES, collection_rows, validate_collection, validate_selection

MAX_ARCHIVE_BYTES = 24 * 1024 * 1024


def collection_archive_bytes(collection):
    validate_collection(collection)
    sources = []
    for entry in collection["feeds"]:
        feed = entry["feed"]
        sources.append({"board_index": entry["board_index"], "provider": feed["provider"], "token": feed["token"],
                        "fetched_at": feed["fetched_at"], "response_sha256": feed["response_sha256"],
                        "source_base64": base64.b64encode(feed["source_snapshot"]).decode("ascii")})
    data = {"format": "roleweave-collection-archive-v1", "watchlist": collection["watchlist"],
            "selected_indices": collection["selected_indices"], "sources": sources,
            "failures": collection["failures"], "started_at": collection["started_at"],
            "finished_at": collection["finished_at"]}
    payload = json.dumps(data, ensure_ascii=True, indent=2).encode()
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise ValueError("Private collection archive exceeds 24 MiB")
    return payload


def archive_collection(collection, destination):
    if Path(destination).suffix.lower() != ".json":
        raise ValueError("Choose a .json collection archive filename")
    publish_bytes(destination, collection_archive_bytes(collection))


def replay_collection_archive(snapshot):
    if not isinstance(snapshot, bytes) or len(snapshot) > MAX_ARCHIVE_BYTES:
        raise ValueError("Private collection archive must be bytes of at most 24 MiB")
    data = json_object(snapshot)
    keys = {"format", "watchlist", "selected_indices", "sources", "failures", "started_at", "finished_at"}
    if not isinstance(data, dict) or set(data) != keys or data["format"] != "roleweave-collection-archive-v1":
        raise ValueError("Unsupported collection archive")
    watchlist = validate_watchlist(data["watchlist"])
    selected = validate_selection(watchlist, data["selected_indices"])
    if not isinstance(data["sources"], list) or len(data["sources"]) > 5:
        raise ValueError("Unsupported archive source count")
    seen, feeds, total = set(), [], 0
    for entry in data["sources"]:
        keys = {"board_index", "provider", "token", "fetched_at", "response_sha256", "source_base64"}
        if not isinstance(entry, dict) or set(entry) != keys:
            raise ValueError("Unsupported archived source fields")
        index = entry["board_index"]
        if type(index) is not int or index not in selected or index in seen:
            raise ValueError("Duplicate or out-of-scope archived board")
        seen.add(index)
        board = watchlist["boards"][index]
        if entry["provider"] != board["provider"] or entry["token"] != board["token"]:
            raise ValueError("Archived source identity differs from watchlist")
        encoded = entry["source_base64"]
        if not isinstance(encoded, str) or len(encoded) > ((MAX_FEED_BYTES + 2) // 3) * 4:
            raise ValueError("Archived source encoding exceeds 8 MiB")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError, binascii.Error):
            raise ValueError("Invalid archived source encoding") from None
        total += len(raw)
        if len(raw) > MAX_FEED_BYTES or total > MAX_COLLECTION_SOURCE_BYTES:
            raise ValueError("Archived source byte budget exceeded")
        if hashlib.sha256(raw).hexdigest() != entry["response_sha256"]:
            raise ValueError("Archived source fingerprint mismatch")
        feed = parse_source(raw, board["provider"], board["token"])
        feed["fetched_at"] = entry["fetched_at"]
        feeds.append({"board_index": index, "feed": feed})
    collection = {"format": "roleweave-collection-v1", "watchlist": watchlist,
                  "selected_indices": selected, "feeds": feeds, "failures": data["failures"],
                  "started_at": data["started_at"], "finished_at": data["finished_at"]}
    return validate_collection(collection)


def read_collection_archive(path):
    with Path(path).open("rb") as handle:
        snapshot = handle.read(MAX_ARCHIVE_BYTES + 1)
    return replay_collection_archive(snapshot)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--export", type=Path, help="Write a new verified archive without overwriting")
    args = parser.parse_args()
    data = read_collection_archive(args.archive)
    if args.export:
        archive_collection(data, args.export)
    print(json.dumps({"watchlist": data["watchlist"]["name"], "selected_boards": len(data["selected_indices"]),
                      "observed_sources": len(data["feeds"]), "failures": data["failures"],
                      "filtered_rows": len(collection_rows(data))}, indent=2))
