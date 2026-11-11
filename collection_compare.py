"""Compare observed board scopes; failed or unselected sources never imply closure."""
import argparse
from collections import Counter
import json
from pathlib import Path

from collection_archive import read_collection_archive
from discovery_archive import compare_observations
from safe_export import publish_bytes
from watchlist_fetch import observation_time, validate_collection

MAX_COMPARISON_BYTES = 8 * 1024 * 1024


def scoped_sources(collection):
    feeds = {entry["board_index"]: entry["feed"] for entry in collection["feeds"]}
    failures = {entry["board_index"]: entry["error"] for entry in collection["failures"]}
    result = {}
    for index in collection["selected_indices"]:
        board = collection["watchlist"]["boards"][index]
        result[(board["provider"], board["token"])] = {"board": board, "feed": feeds.get(index),
                                                      "failure": failures.get(index)}
    return result


def compare_collections(earlier, later):
    validate_collection(earlier)
    validate_collection(later)
    if observation_time(earlier["finished_at"], "Earlier finish") > observation_time(later["finished_at"], "Later finish"):
        raise ValueError("Choose the earlier observation first")
    before, after = scoped_sources(earlier), scoped_sources(later)
    sources = []
    for provider, token in sorted(before.keys() | after.keys()):
        left, right = before.get((provider, token)), after.get((provider, token))
        if left is None:
            state, changes = "scope_added", []
        elif right is None:
            state, changes = "scope_not_selected", []
        elif left["feed"] is None or right["feed"] is None:
            state, changes = "not_comparable", []
        else:
            state, changes = "compared", compare_observations(left["feed"], right["feed"])
        sources.append({"provider": provider, "token": token, "state": state,
                        "earlier_label": left["board"]["company"] if left else None,
                        "later_label": right["board"]["company"] if right else None,
                        "settings_changed": left is not None and right is not None and left["board"] != right["board"],
                        "earlier_failure": left["failure"] if left else None,
                        "later_failure": right["failure"] if right else None,
                        "earlier_sha256": left["feed"]["response_sha256"] if left and left["feed"] else None,
                        "later_sha256": right["feed"]["response_sha256"] if right and right["feed"] else None,
                        "posting_changes": changes})
    report = {"format": "roleweave-collection-comparison-v1", "earlier_finished_at": earlier["finished_at"],
              "later_finished_at": later["finished_at"], "sources": sources,
              "scope_counts": dict(Counter(source["state"] for source in sources))}
    if len(json.dumps(report, ensure_ascii=True).encode()) > MAX_COMPARISON_BYTES:
        raise ValueError("Collection comparison exceeds 8 MiB")
    return report


def export_comparison(earlier, later, destination):
    if Path(destination).suffix.lower() != ".json":
        raise ValueError("Choose a .json comparison filename")
    payload = json.dumps(compare_collections(earlier, later), ensure_ascii=True, indent=2).encode()
    if len(payload) > MAX_COMPARISON_BYTES:
        raise ValueError("Collection comparison exceeds 8 MiB")
    publish_bytes(destination, payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("earlier", type=Path)
    parser.add_argument("later", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    earlier, later = read_collection_archive(args.earlier), read_collection_archive(args.later)
    report = compare_collections(earlier, later)
    if args.output:
        export_comparison(earlier, later, args.output)
    print(json.dumps(report, ensure_ascii=True, indent=2))
