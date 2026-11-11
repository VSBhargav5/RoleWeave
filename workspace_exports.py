"""Explicit private exports of the currently selected review list."""
import csv
from io import StringIO

from safe_export import publish_bytes
from calendar_export import follow_up_calendar
from applications import current_application


def spreadsheet_cell(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def review_list_csv(rows, destination):
    output = StringIO(newline="")
    writer = csv.writer(output)
    keys = ("id", "title", "company", "market", "stage", "follow_up", "source_url")
    writer.writerow(keys)
    for row in rows:
        values = [spreadsheet_cell(row[key]) for key in keys]
        writer.writerow(values)
    publish_bytes(destination, output.getvalue().encode("utf-8-sig"))


def follow_up_list(store, rows, destination):
    events, seen = [], set()
    for row in rows:
        if row["id"] in seen:
            raise ValueError("Duplicate saved review in calendar selection")
        seen.add(row["id"])
        history = store.application_history(row["id"])
        current = current_application(history)
        if current["follow_up"] and current["stage"] not in ("closed", "withdrawn"):
            events.append(follow_up_calendar(store.load(row["id"]), history, event_only=True))
    if not events:
        raise ValueError("No active dated follow-ups in this filtered list")
    payload = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//RoleWeave//Follow-ups//EN\r\n" + b"".join(events) + b"END:VCALENDAR\r\n"
    if len(payload) > 1024 * 1024:
        raise ValueError("Calendar selection exceeds 1 MiB")
    publish_bytes(destination, payload)
    return len(events)
