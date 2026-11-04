"""Bounded HTTPS for two explicit providers; no redirects, proxies or retries."""
import http.client
import json
import time


class Cancelled(ValueError):
    pass


def request_bytes(host, path, *, body=None, key=None, cancel=None, limit=1024 * 1024):
    if host not in ("boards-api.greenhouse.io", "api.openai.com") or not path.startswith("/"):
        raise ValueError("Unsupported provider endpoint")
    if cancel is not None and cancel.is_set():
        raise Cancelled("Cancelled locally")
    headers = {"Accept": "application/json", "User-Agent": "RoleWeave/0.4"}
    if key is not None:
        if not isinstance(key, str) or not key or len(key) > 1000 or not key.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in key):
            raise ValueError("Enter a valid session API key")
        headers["Authorization"] = "Bearer " + key
    if body is not None:
        headers["Content-Type"] = "application/json"
    connection = http.client.HTTPSConnection(host, timeout=5)
    deadline = time.monotonic() + 60
    try:
        if cancel is not None and cancel.is_set():
            raise Cancelled("Cancelled locally")
        connection.request("POST" if body is not None else "GET", path, body=body, headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f"Provider returned HTTP {response.status}; no redirect or retry was attempted")
        content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Provider did not return JSON")
        parts, size = [], 0
        while True:
            if cancel is not None and cancel.is_set():
                raise Cancelled("Cancelled locally")
            if time.monotonic() > deadline:
                raise ValueError("Provider request exceeded the local deadline")
            part = response.read1(min(65536, limit + 1 - size))
            if not part:
                break
            parts.append(part)
            size += len(part)
            if size > limit:
                raise ValueError("Provider response exceeds the size limit")
        return b"".join(parts)
    except (OSError, http.client.HTTPException) as exc:
        # Never propagate provider response bodies, keys or arbitrary error text.
        raise ValueError("Provider connection failed or timed out; no automatic retry") from None
    finally:
        connection.close()


def json_object(snapshot):
    def unique(pairs):
        values = {}
        for key, value in pairs:
            if key in values:
                raise ValueError("Duplicate provider JSON key")
            values[key] = value
        return values
    try:
        return json.loads(snapshot.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError, RecursionError, TypeError) as exc:
        raise ValueError("Invalid provider JSON") from None
