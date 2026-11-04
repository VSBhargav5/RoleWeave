"""Read-only SQLite storage checks; no source-authenticity or recovery guarantee."""
from contextlib import closing
from pathlib import Path
import sqlite3


def inspect_database(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError("Database does not exist; no file was created")
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as database:
            result = database.execute("PRAGMA quick_check(1)").fetchone()
            if result is None or result[0] != "ok":
                raise ValueError("SQLite storage check failed; preserve the file and recover from a verified backup")
            return {table: database.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in ("jobs", "career_profiles", "resume_versions", "application_events")}
    except sqlite3.DatabaseError:
        raise ValueError("Database structure could not be read; current file was not modified") from None
