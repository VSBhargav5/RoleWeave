"""Validate a deliberate browser navigation; never launch files or custom schemes."""
from urllib.parse import urlsplit


def source_link(value):
    if not isinstance(value, str) or not value or any(ord(c) <= 32 for c in value) or "\\" in value:
        raise ValueError("Use a public HTTPS posting URL without whitespace")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ValueError("Invalid posting URL") from None
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only HTTPS posting links without embedded credentials can be opened")
    return value
