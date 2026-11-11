"""Explicit bounded multi-board discovery; failures remain observations, not closure."""
import argparse
import copy
from datetime import datetime, timezone
import json
import time

from employer_watchlist import filter_postings, read_watchlist, validate_watchlist
from network_io import Cancelled
from provider_boards import fetch_source

MAX_COLLECTION_SOURCE_BYTES = 16 * 1024 * 1024


def validate_selection(data, indices):
    if not isinstance(indices, list) or not 1 <= len(indices) <= 5 or any(type(i) is not int or not 0 <= i < len(data["boards"]) for i in indices) or len(set(indices)) != len(indices):
        raise ValueError("Explicitly select 1-5 distinct board indices")
    return list(indices)


def observation_time(value, label):
    if not isinstance(value, str) or len(value) > 100:
        raise ValueError(label + " must be a timezone-aware timestamp")
    try:
        result = datetime.fromisoformat(value)
        if result.utcoffset() is None:
            raise ValueError()
    except ValueError:
        raise ValueError(label + " must be a timezone-aware timestamp") from None
    return result


def validate_collection(collection):
    from provider_boards import parse_source
    from roleweave import text
    keys = {"format", "watchlist", "selected_indices", "feeds", "failures", "started_at", "finished_at"}
    if not isinstance(collection, dict) or set(collection) != keys or collection["format"] != "roleweave-collection-v1":
        raise ValueError("Unsupported employer collection")
    data = validate_watchlist(collection["watchlist"])
    selected = validate_selection(data, collection["selected_indices"])
    started = observation_time(collection["started_at"], "Collection start")
    finished = observation_time(collection["finished_at"], "Collection finish")
    if finished < started:
        raise ValueError("Collection finish precedes its start")
    if not isinstance(collection["feeds"], list) or not isinstance(collection["failures"], list) or len(collection["feeds"]) + len(collection["failures"]) != len(selected):
        raise ValueError("Every selected board needs one success or failure observation")
    seen, total = set(), 0
    for entry in collection["feeds"]:
        if not isinstance(entry, dict) or set(entry) != {"board_index", "feed"}:
            raise ValueError("Unsupported collection source entry")
        index = entry["board_index"]
        if type(index) is not int or index not in selected or index in seen:
            raise ValueError("Duplicate or out-of-scope collection board")
        seen.add(index)
        board, feed = data["boards"][index], entry["feed"]
        if not isinstance(feed, dict) or set(feed) != {"jobs", "token", "fetched_at", "response_sha256", "provider", "source_snapshot"}:
            raise ValueError("Unsupported collection feed evidence")
        if feed["provider"] != board["provider"] or feed["token"] != board["token"]:
            raise ValueError("Collection feed belongs to another board")
        raw = feed["source_snapshot"]
        if not isinstance(raw, bytes):
            raise ValueError("Collection needs original response bytes")
        total += len(raw)
        if total > MAX_COLLECTION_SOURCE_BYTES:
            raise ValueError("Collection source bytes exceed 16 MiB")
        observed = observation_time(feed["fetched_at"], "Source observation")
        if not started <= observed <= finished:
            raise ValueError("Source observation lies outside the declared collection interval")
        replay = parse_source(raw, board["provider"], board["token"])
        if replay["jobs"] != feed["jobs"] or replay["response_sha256"] != feed["response_sha256"]:
            raise ValueError("Collection rows or fingerprint differ from original response bytes")
    for entry in collection["failures"]:
        if not isinstance(entry, dict) or set(entry) != {"board_index", "error"}:
            raise ValueError("Unsupported collection failure")
        index = entry["board_index"]
        if type(index) is not int or index not in selected or index in seen:
            raise ValueError("Duplicate or out-of-scope collection outcome")
        seen.add(index)
        text(entry["error"], "Source failure")
        if len(entry["error"]) > 2000:
            raise ValueError("Source failure exceeds its text limit")
    if seen != set(selected):
        raise ValueError("Selected board observations are incomplete")
    return collection


def fetch_watchlist(watchlist, indices, cancel=None):
    data = copy.deepcopy(validate_watchlist(watchlist))
    indices = validate_selection(data, indices)
    started = datetime.now(timezone.utc).isoformat()
    deadline = time.monotonic() + 60
    feeds, failures, total = [], [], 0
    def check():
        if cancel is not None and cancel.is_set():
            raise Cancelled("Collection cancelled locally")
        if time.monotonic() > deadline:
            raise ValueError("Collection exceeded the local observation budget")
    for index in indices:
        check()
        board = data["boards"][index]
        try:
            feed = fetch_source(board["provider"], board["token"], cancel)
        except Cancelled:
            raise
        except ValueError as exc:
            failures.append({"board_index": index, "error": str(exc)})
            continue
        check()
        if feed["provider"] != board["provider"] or feed["token"] != board["token"]:
            raise ValueError("Provider result does not match selected board identity")
        total += len(feed["source_snapshot"])
        if total > MAX_COLLECTION_SOURCE_BYTES:
            raise ValueError("Collection source bytes exceed 16 MiB")
        feeds.append({"board_index": index, "feed": feed})
    result = {"format": "roleweave-collection-v1", "watchlist": data, "selected_indices": list(indices),
            "feeds": feeds, "failures": failures, "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat()}
    return validate_collection(result)


def collection_rows(collection, filters=None):
    rows = []
    for entry in collection["feeds"]:
        index, feed = entry["board_index"], entry["feed"]
        board = collection["watchlist"]["boards"][index]
        for row in feed["jobs"]:
            rows.append(dict(row, board_index=index, provider=board["provider"], token=board["token"],
                             company=board["company"], market=board["market"],
                             fetched_at=feed["fetched_at"], response_sha256=feed["response_sha256"]))
    return filter_postings(rows, filters if filters is not None else collection["watchlist"]["filters"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("watchlist")
    parser.add_argument("--boards", nargs="+", type=int, required=True, help="Zero-based selected board indices, at most five")
    parser.add_argument("--fetch", action="store_true", required=True, help="Explicitly authorize public-board GETs")
    args = parser.parse_args()
    result = fetch_watchlist(read_watchlist(args.watchlist), args.boards)
    print(json.dumps({"started_at": result["started_at"], "finished_at": result["finished_at"],
                      "successful_boards": len(result["feeds"]), "failures": result["failures"],
                      "rows": collection_rows(result)}, ensure_ascii=True, indent=2))
