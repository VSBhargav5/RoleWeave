"""Explicit private exports of the currently selected review list."""
import csv
from io import StringIO

from safe_export import publish_bytes


def review_list_csv(rows, destination):
    output = StringIO(newline="")
    writer = csv.writer(output)
    keys = ("id", "title", "company", "market", "stage", "follow_up", "source_url")
    writer.writerow(keys)
    for row in rows:
        values = []
        for key in keys:
            value = str(row[key])
            # Spreadsheet formula prevention, including leading whitespace.
            if value.lstrip().startswith(("=", "+", "-", "@")):
                value = "'" + value
            values.append(value)
        writer.writerow(values)
    publish_bytes(destination, output.getvalue().encode("utf-8-sig"))
