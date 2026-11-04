"""Publish complete exports without replacing existing files (NTFS/POSIX links)."""
import os
from pathlib import Path
import tempfile


def publish_bytes(destination, payload):
    destination = Path(destination)
    descriptor, name = tempfile.mkstemp(prefix=".roleweave-", dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        # Atomic exclusive publication. Unsupported filesystems fail closed.
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
