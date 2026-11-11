"""Private metadata-only collection shortlist; full posting text remains excluded."""
import argparse
import csv
from io import StringIO
from pathlib import Path

from collection_archive import read_collection_archive
from safe_export import publish_bytes
from watchlist_fetch import collection_rows, validate_collection
from workspace_exports import spreadsheet_cell

MAX_CSV_BYTES = 8 * 1024 * 1024


def export_collection_csv(collection, destination):
    validate_collection(collection)
    if Path(destination).suffix.lower() != ".csv":
        raise ValueError("Choose a .csv shortlist filename")
    rows = collection_rows(collection)
    if not rows:
        raise ValueError("No observed postings match the local filters; no CSV was created")
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(("provider", "board_token", "your_employer_label", "your_market_default", "post_id",
                     "title", "provider_location_label", "provider_time_label", "source_url",
                     "observed_at", "response_sha256", "selected_source_count", "observed_source_count",
                     "failed_source_count"))
    for row in rows:
        values = (row["provider"], row["token"], row["company"], row["market"], row["id"],
                  row["title"], row["location"], row["updated_at"], row["url"], row["fetched_at"],
                  row["response_sha256"], len(collection["selected_indices"]), len(collection["feeds"]),
                  len(collection["failures"]))
        writer.writerow([spreadsheet_cell(value) for value in values])
        if output.tell() > MAX_CSV_BYTES:
            raise ValueError("Collection shortlist exceeds 8 MiB")
    payload = output.getvalue().encode("utf-8-sig")
    if len(payload) > MAX_CSV_BYTES:
        raise ValueError("Collection shortlist exceeds 8 MiB")
    publish_bytes(destination, payload)
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(export_collection_csv(read_collection_archive(args.archive), args.output))
