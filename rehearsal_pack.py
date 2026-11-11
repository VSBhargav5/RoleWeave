"""Export selected source questions; answer drafts are opt-in private content."""
import argparse
from pathlib import Path

from rehearsal_cards import practice_cards
from rehearsal_journal import read_rehearsal, rehearsal_snapshot, rehearsal_source_item
from safe_export import publish_bytes

MAX_PACK_BYTES = 8 * 1024 * 1024


def render_pack(snapshot, *, include_answers=False):
    if type(include_answers) is not bool:
        raise ValueError("Choose whether to include private answer drafts")
    record, digest = rehearsal_snapshot(snapshot)
    context = record["job_context"]
    cards = {card["requirement_id"]: card for card in practice_cards(rehearsal_source_item(record))}
    lines = ["RoleWeave - Private rehearsal pack", "Not a resume or verified learning record.",
             "Company: " + context["company"], "Role: " + context["title"],
             "Exact review: " + context["id"], "Input SHA-256: " + context["input_sha256"],
             "Journal SHA-256: " + digest, "Version recorded: " + record["recorded_at"],
             "Locally recorded seconds (unverified): " + str(record["elapsed_seconds"]),
             "Answer drafts included: " + str(include_answers), ""]
    for number, entry in enumerate(record["answers"], 1):
        card = cards[entry["requirement_id"]]
        lines.extend([str(number) + ". " + card["quote"], "Requirement ID: " + entry["requirement_id"],
                      card["prompt"], "Linked source evidence:", card["evidence"]])
        if include_answers:
            lines.extend(["Your unverified answer draft:", entry["answer"], "Your reflection:", entry["reflection"]])
        lines.append("")
    payload = "\n".join(lines).encode("utf-8")
    if len(payload) > MAX_PACK_BYTES:
        raise ValueError("Rehearsal pack exceeds 8 MiB")
    return payload


def export_pack(snapshot, destination, *, include_answers=False, confirmed=False):
    if confirmed is not True:
        raise ValueError("Confirm export of this private source/evidence pack")
    if Path(destination).suffix.lower() != ".txt":
        raise ValueError("Choose a .txt rehearsal pack filename")
    publish_bytes(destination, render_pack(snapshot, include_answers=include_answers))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--include-answers", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    export_pack(read_rehearsal(args.journal)[0], args.output,
                include_answers=args.include_answers, confirmed=args.confirm)
