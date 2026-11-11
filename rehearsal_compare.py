"""Compare private drafts against one exact frozen source; no skill scoring."""
import argparse
from datetime import datetime
import json
from pathlib import Path

from rehearsal_journal import read_rehearsal, rehearsal_snapshot
from safe_export import publish_bytes

MAX_COMPARISON_BYTES = 8 * 1024 * 1024


def compare_rehearsals(earlier, later):
    before, before_hash = rehearsal_snapshot(earlier)
    after, after_hash = rehearsal_snapshot(later)
    if before["job_context"] != after["job_context"]:
        raise ValueError("Rehearsals must use the same exact frozen job review")
    if datetime.fromisoformat(before["recorded_at"]) > datetime.fromisoformat(after["recorded_at"]):
        raise ValueError("Choose the earlier recorded version first")
    left = {entry["requirement_id"]: entry for entry in before["answers"]}
    right = {entry["requirement_id"]: entry for entry in after["answers"]}
    changes = []
    for key in sorted(left.keys() | right.keys()):
        old, new = left.get(key), right.get(key)
        state = "added" if old is None else "not_selected" if new is None else "unchanged" if old == new else "draft_changed"
        changes.append({"requirement_id": key, "state": state, "earlier": old, "later": new})
    return {"format": "roleweave-rehearsal-comparison-v1", "exact_review_id": before["job_context"]["id"],
            "earlier_sha256": before_hash, "later_sha256": after_hash,
            "earlier_recorded_at": before["recorded_at"], "later_recorded_at": after["recorded_at"],
            "elapsed_seconds_delta": after["elapsed_seconds"] - before["elapsed_seconds"],
            "learning_verified": False, "questions": changes,
            "limitation": "Private draft differences and local elapsed time do not establish improvement or learning."}


def comparison_bytes(earlier, later):
    payload = json.dumps(compare_rehearsals(earlier, later), ensure_ascii=True, indent=2).encode()
    if len(payload) > MAX_COMPARISON_BYTES:
        raise ValueError("Private rehearsal comparison exceeds 8 MiB")
    return payload


def export_comparison(earlier, later, destination, *, confirmed=False):
    if confirmed is not True:
        raise ValueError("Confirm private answer/reflection comparison export")
    if Path(destination).suffix.lower() != ".json":
        raise ValueError("Choose a .json comparison filename")
    publish_bytes(destination, comparison_bytes(earlier, later))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("earlier", type=Path)
    parser.add_argument("later", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    before, after = read_rehearsal(args.earlier)[0], read_rehearsal(args.later)[0]
    if args.output:
        export_comparison(before, after, args.output, confirmed=args.confirm)
    print(comparison_bytes(before, after).decode())
