"""Role/location discovery through the documented personal FreeHire read API."""
from datetime import datetime, timezone
import hashlib
import re
import threading
import time
from urllib.parse import urlencode

from network_io import json_object, request_bytes
from source_links import source_link
from roleweave import text

SOURCE = "FreeHire"
SOURCE_URL = "https://freehire.me"


def search_path(query, location="", country="", remote=False, offset=0):
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 160:
        raise ValueError("Enter a role or skill, between 2 and 160 characters")
    if not isinstance(location, str) or len(location) > 100:
        raise ValueError("Location exceeds its limit")
    if not isinstance(country, str) or country and not re.fullmatch(r"[A-Za-z]{2}", country):
        raise ValueError("Choose a two-letter country code or Anywhere")
    if type(remote) is not bool or type(offset) is not int or offset < 0 or offset > 9980 or offset % 20:
        raise ValueError("Invalid search page or remote filter")
    params = {"q": query.strip() + (" " + location.strip() if location.strip() else ""),
              "description_format": "text", "limit": 20, "offset": offset}
    if country:
        params["countries"] = country.upper()
    if remote:
        params["work_mode"] = "remote"
    return "/api/v1/agent/jobs/search?" + urlencode(params)


def parse_search(snapshot, offset=0):
    if type(offset) is not int or offset < 0 or offset > 9980 or offset % 20:
        raise ValueError("Unsupported search offset")
    data = json_object(snapshot)
    if not isinstance(data, dict) or not isinstance(data.get("data"), list) or len(data["data"]) > 20:
        raise ValueError("The search provider returned an unsupported response")
    meta = data.get("meta", {})
    if not isinstance(meta, dict) or meta.get("ignored_params"):
        raise ValueError("The provider ignored a requested filter; narrow your search before continuing")
    for key, expected in (("offset", offset), ("limit", 20)):
        if key in meta and (type(meta[key]) is not int or meta[key] != expected):
            raise ValueError("Provider pagination differs from the requested page")
    jobs, excluded, seen = [], [], set()
    observed = datetime.now(timezone.utc).isoformat()
    digest = hashlib.sha256(snapshot).hexdigest()
    for index, raw in enumerate(data["data"], 1):
        try:
            if not isinstance(raw, dict):
                raise ValueError("Unsupported record")
            identifier = text(raw.get("public_slug"), "Source job ID")
            if len(identifier) > 500 or identifier in seen:
                raise ValueError("Missing or duplicate source identity")
            title, company = text(raw.get("title"), "Job title"), text(raw.get("company"), "Company")
            description = text(raw.get("description"), "Job description")
            if len(title) > 500 or len(company) > 500:
                raise ValueError("Job metadata exceeds the supported limit")
            url = source_link(raw.get("url"))
            if len(url) > 2000:
                raise ValueError("Application URL exceeds the supported limit")
            location = raw.get("location") or "Location not stated"
            if not isinstance(location, str) or len(location) > 1000:
                raise ValueError("Unsupported location label")
            seen.add(identifier)
            jobs.append({"id": identifier, "title": title, "company": company, "posting": description,
                         "url": url, "location": location, "work_mode": str(raw.get("work_mode") or "Not stated")[:100],
                         "posted_at": str(raw.get("posted_at") or "Not stated")[:100], "source": SOURCE,
                         "source_url": SOURCE_URL, "observed_at": observed, "source_sha256": digest})
        except (ValueError, TypeError) as exc:
            excluded.append({"row": index, "reason": str(exc)})
    total = meta.get("total")
    if total is not None and (type(total) is not int or total < 0):
        raise ValueError("Unsupported source result count")
    return {"jobs": jobs, "excluded": excluded, "total": total, "observed_at": observed,
            "page": {"offset": offset, "returned": len(data["data"]),
                     "has_next": offset < 9980 and len(data["data"]) == 20 and (total is None or offset + 20 < total)},
            "source": SOURCE, "source_url": SOURCE_URL, "source_sha256": digest,
            "notice": "Source observations, not eligibility or sponsorship checks. FreeHire personal/non-commercial API."}


class JobSearch:
    def __init__(self):
        self.cache = {}
        self.snapshots = {}
        self.lock = threading.Lock()

    def search(self, query, location="", country="", remote=False, offset=0):
        path = search_path(query, location, country, remote, offset)
        with self.lock:
            cached = self.cache.get(path)
            if cached and time.monotonic() - cached[0] < 600:
                return cached[1]
            snapshot = request_bytes("freehire.me", path, limit=4 * 1024 * 1024)
            result = parse_search(snapshot, offset)
            if len(self.cache) >= 50:
                self.cache.clear()
                self.snapshots.clear()
            self.snapshots[result["source_sha256"]] = snapshot
            self.cache[path] = (time.monotonic(), result)
            return result
