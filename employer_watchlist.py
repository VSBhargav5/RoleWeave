"""Portable employer-board choices and local filters; opening never fetches."""
import argparse
import json
from pathlib import Path

from network_io import json_object
from provider_boards import source_endpoint
from roleweave import MARKETS, text
from safe_export import publish_bytes

MAX_WATCHLIST_BYTES = 1024 * 1024


def validate_board(board):
    if not isinstance(board, dict) or set(board) != {"provider", "token", "company", "market"}:
        raise ValueError("Each board needs provider, token, company and a user-chosen market")
    source_endpoint(board["provider"], board["token"])
    text(board["company"], "Employer label")
    if len(board["company"]) > 2000:
        raise ValueError("Employer label exceeds 2000 characters")
    if not isinstance(board["market"], str) or board["market"] not in MARKETS:
        raise ValueError("Choose a board's default market explicitly; eligibility is not inferred")
    return board


def validate_filters(filters):
    if not isinstance(filters, dict) or set(filters) != {"include", "exclude", "search_description"}:
        raise ValueError("Filters require include, exclude and search_description")
    for key in ("include", "exclude"):
        value = filters[key]
        if not isinstance(value, str) or len(value) > 2000:
            raise ValueError("Filter phrases must be text of at most 2000 characters")
        if value:
            text(value, "Filter phrase")
    if type(filters["search_description"]) is not bool:
        raise ValueError("Description search must be an explicit boolean")
    return filters


def validate_watchlist(data):
    if not isinstance(data, dict) or set(data) != {"format", "name", "boards", "filters"} or data["format"] != "roleweave-watchlist-v1":
        raise ValueError("Unsupported employer watchlist")
    text(data["name"], "Watchlist name")
    if len(data["name"]) > 2000 or not isinstance(data["boards"], list) or not 1 <= len(data["boards"]) <= 100:
        raise ValueError("Watchlist needs a name within 2000 characters and 1-100 boards")
    seen = set()
    for board in data["boards"]:
        validate_board(board)
        identity = (board["provider"], board["token"])
        if identity in seen:
            raise ValueError("Duplicate provider/board token; choose the market per job when importing")
        seen.add(identity)
    validate_filters(data["filters"])
    return data


def read_watchlist(path):
    with Path(path).open("rb") as handle:
        snapshot = handle.read(MAX_WATCHLIST_BYTES + 1)
    if len(snapshot) > MAX_WATCHLIST_BYTES:
        raise ValueError("Watchlist exceeds 1 MiB")
    return validate_watchlist(json_object(snapshot))


def save_watchlist(data, destination):
    validate_watchlist(data)
    if Path(destination).suffix.lower() != ".json":
        raise ValueError("Choose a .json watchlist filename")
    payload = json.dumps(data, ensure_ascii=True, sort_keys=True, indent=2).encode()
    if len(payload) > MAX_WATCHLIST_BYTES:
        raise ValueError("Watchlist exceeds 1 MiB")
    publish_bytes(destination, payload)


def filter_postings(rows, filters):
    validate_filters(filters)
    include, exclude = filters["include"].casefold(), filters["exclude"].casefold()
    result = []
    for row in rows:
        value = row["title"] + " " + row["location"]
        if filters["search_description"]:
            value += " " + row["posting"]
        value = value.casefold()
        if include in value and (not exclude or exclude not in value):
            result.append(row)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("watchlist", type=Path)
    parser.add_argument("--export", type=Path, help="Write a new validated portable file; existing paths refused")
    args = parser.parse_args()
    data = read_watchlist(args.watchlist)
    if args.export:
        save_watchlist(data, args.export)
    print(json.dumps(data, ensure_ascii=True, indent=2))
