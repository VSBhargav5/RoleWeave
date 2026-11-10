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


def fetch_watchlist(watchlist, indices, cancel=None):
    data = copy.deepcopy(validate_watchlist(watchlist))
    if not isinstance(indices, list) or not 1 <= len(indices) <= 5 or any(type(i) is not int or not 0 <= i < len(data["boards"]) for i in indices) or len(set(indices)) != len(indices):
        raise ValueError("Explicitly select 1-5 distinct board indices")
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
    return {"format": "roleweave-collection-v1", "watchlist": data, "selected_indices": list(indices),
            "feeds": feeds, "failures": failures, "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat()}


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
