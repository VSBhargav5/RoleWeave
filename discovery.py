"""One explicit public Greenhouse board; no aggregation or inferred eligibility."""
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlsplit

from network_io import json_object, request_bytes
from roleweave import MARKETS, review_snapshot

MAX_FEED_BYTES = 8 * 1024 * 1024


def board_path(token):
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", token):
        raise ValueError("Use the employer's Greenhouse board token, not a URL")
    return f"/v1/boards/{token}/jobs?content=true"


class PlainPosting(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag in ("p", "div", "li", "br", "h1", "h2", "h3", "tr") and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        elif tag in ("p", "div", "li", "h1", "h2", "h3", "tr") and not self.hidden:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_posting(content):
    if not isinstance(content, str) or len(content) > 200000:
        raise ValueError("Unsupported posting content size")
    # Greenhouse can entity-encode the HTML wrapper. Decode that wrapper only;
    # do not turn escaped technical text inside real HTML into tags.
    if not re.search(r"<(?:p|div|li|br|h[1-6])\b", content, re.I) and re.search(r"&lt;(?:p|div|li|br|h[1-6])\b", content, re.I):
        content = html.unescape(content)
    parser = PlainPosting()
    parser.feed(content)
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def parse_board(snapshot, token):
    board_path(token)
    if len(snapshot) > MAX_FEED_BYTES:
        raise ValueError("Board exceeds 8 MiB")
    data = json_object(snapshot)
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list) or len(data["jobs"]) > 10000:
        raise ValueError("Unsupported job-board response")
    if not isinstance(data.get("meta"), dict) or type(data["meta"].get("total")) is not int or data["meta"]["total"] != len(data["jobs"]):
        raise ValueError("Board total does not match returned posts; import refused")
    rows, seen = [], set()
    for job in data["jobs"]:
        if not isinstance(job, dict) or "internal_job_id" not in job:
            raise ValueError("Unsupported job record")
        if job["internal_job_id"] is None:  # prospect posts are not vacancies
            continue
        if type(job.get("id")) is not int or job["id"] <= 0 or job["id"] in seen:
            raise ValueError("Invalid or duplicate Greenhouse post ID")
        seen.add(job["id"])
        for key in ("title", "absolute_url", "updated_at"):
            if not isinstance(job.get(key), str) or not job[key].strip() or len(job[key]) > 2000:
                raise ValueError("Missing or oversized posting metadata")
        parsed = urlsplit(job["absolute_url"])
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Posting source must be an HTTPS URL without credentials")
        try:
            if datetime.fromisoformat(job["updated_at"].replace("Z", "+00:00")).tzinfo is None:
                raise ValueError()
        except ValueError:
            raise ValueError("Provider updated_at requires an explicit timezone") from None
        location = job.get("location")
        if not isinstance(location, dict) or not isinstance(location.get("name"), str) or len(location["name"]) > 2000:
            raise ValueError("Missing posting location label")
        body = plain_posting(job.get("content"))
        if not body:
            raise ValueError("Posting description is empty")
        digest = hashlib.sha256(json.dumps(job, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
        posting = (f"Greenhouse board: {token}\nPost ID: {job['id']}\nSource: {job['absolute_url']}\n"
                   f"Provider updated_at (not publication date): {job['updated_at']}\nLocation label: {location['name']}\n"
                   f"Provider record SHA256 (normalized JSON): {digest}\n\n{body}")
        if len(posting) > 50000:
            raise ValueError("Posting exceeds the local 50000-character limit")
        rows.append({"id": job["id"], "title": job["title"], "url": job["absolute_url"],
                     "location": location["name"], "updated_at": job["updated_at"], "posting": posting})
    return {"jobs": rows, "token": token, "fetched_at": datetime.now(timezone.utc).isoformat(),
            "response_sha256": hashlib.sha256(snapshot).hexdigest()}


def fetch_board(token, cancel=None):
    return parse_board(request_bytes("boards-api.greenhouse.io", board_path(token), cancel=cancel, limit=MAX_FEED_BYTES), token)


def discovered_snapshot(row, market):
    if market not in MARKETS:
        raise ValueError("Choose the market explicitly; a location label does not establish eligibility")
    snapshot = json.dumps({"market": market, "posting": row["posting"], "facts": [], "requirements": []}, ensure_ascii=False).encode()
    review_snapshot(snapshot)
    return snapshot
