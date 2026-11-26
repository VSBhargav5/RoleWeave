"""Transactional personal discovery configurations and review queue, separate from the shelf."""
from contextlib import closing, contextmanager
import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from career_profile import unique_json
from job_search import search_path, parse_search
from roleweave import MARKETS, text
from source_links import source_link
from job_fit_filters import preferences, filter_result

MAX_BYTES = 16 * 1024 * 1024
APPLICATION_ID = 0x52574453
CONFIG_FIELDS = {"id", "revision", "name", "query", "location", "country", "remote", "market", "archived"}
ROW_FIELDS = {"id", "title", "company", "posting", "url", "location", "work_mode", "posted_at", "source"}
ROW_OPTIONAL = {"source_url", "observed_at", "source_sha256"}


def now(): return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    if not isinstance(value, str) or len(value) > 100: raise ValueError("Invalid discovery timestamp")
    try:
        result = datetime.fromisoformat(value)
        if result.utcoffset() is None: raise ValueError()
        return result
    except ValueError: raise ValueError("Discovery timestamps require a timezone") from None


def identifier(value, size=32):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{" + str(size) + "}", value):
        raise ValueError("Invalid discovery identity")


def config(value):
    if not isinstance(value, dict) or not CONFIG_FIELDS<=set(value) or set(value)-CONFIG_FIELDS-{'preferences'}: raise ValueError('Invalid saved search')
    if 'preferences' in value:preferences(value['preferences'])
    identifier(value["id"])
    if type(value["revision"]) is not int or value["revision"] < 1: raise ValueError("Invalid saved-search revision")
    text(value["name"], "Search name")
    if len(value["name"]) > 80 or type(value["archived"]) is not bool or not isinstance(value["market"], str) or value["market"] not in MARKETS: raise ValueError("Invalid saved search name or market")
    search_path(value["query"], value["location"], value["country"], value["remote"])
    return value


def row(value):
    if not isinstance(value, dict) or not ROW_FIELDS <= set(value) or set(value) - ROW_FIELDS - ROW_OPTIONAL:
        raise ValueError("Unsupported queue observation")
    for key, limit in (("id", 500), ("title", 500), ("company", 500), ("posting", 50000), ("location", 1000), ("work_mode", 100), ("posted_at", 100), ("source", 100)):
        text(value[key], "Observed " + key)
        if len(value[key]) > limit: raise ValueError("Queue observation exceeds its limit")
    source_link(value["url"])
    if len(value["url"]) > 2000: raise ValueError("Queue source URL exceeds its limit")
    if "source_url" in value: source_link(value["source_url"])
    if "observed_at" in value: timestamp(value["observed_at"])
    if "source_sha256" in value: identifier(value["source_sha256"], 64)
    return value


def candidate_key(value, market):
    return hashlib.sha256(json.dumps([value[k] for k in ("url", "title", "company", "posting", "location", "work_mode", "posted_at", "source")] + [market], ensure_ascii=True).encode()).hexdigest()


def empty_state(): return {"format": "roleweave-discovery-v1", "revision": 0, "searches": [], "candidates": [], "runs": []}


def validate(state):
    if not isinstance(state, dict) or set(state) != {"format", "revision", "searches", "candidates", "runs"} or state["format"] != "roleweave-discovery-v1": raise ValueError("Unsupported discovery snapshot")
    if type(state["revision"]) is not int or state["revision"] < 0: raise ValueError("Invalid discovery revision")
    for name, limit in (("searches", 20), ("candidates", 200), ("runs", 100)):
        if not isinstance(state[name], list) or len(state[name]) > limit: raise ValueError("Discovery " + name + " exceeds capacity")
    search_ids = set()
    for saved in state["searches"]:
        config(saved)
        if saved["id"] in search_ids: raise ValueError("Duplicate saved search")
        search_ids.add(saved["id"])
    if sum(not s["archived"] for s in state["searches"]) > 3: raise ValueError("At most three active named searches")
    seen = set()
    for item in state["candidates"]:
        keys={"id", "row", "market", "status", "saved_job_id", "first_seen", "last_seen", "first_search", "last_search", "search_ids", "source_sha256"}
        if not isinstance(item, dict) or not keys<=set(item) or set(item)-keys-{'source_offset'}: raise ValueError("Invalid queue entry")
        offset=item.get('source_offset',0)
        if type(offset) is not int or not 0<=offset<=500 or offset%20:raise ValueError('Invalid queue source page')
        row(item["row"]); config(item["first_search"]); config(item["last_search"])
        if not isinstance(item["market"], str) or item["market"] not in MARKETS or item["id"] != candidate_key(item["row"], item["market"]) or item["id"] in seen: raise ValueError("Queue identity differs from its observation")
        seen.add(item["id"])
        timestamp(item["first_seen"]); timestamp(item["last_seen"])
        if item["status"] not in ("pending", "kept", "dismissed", "saved"): raise ValueError("Unsupported queue decision")
        if not isinstance(item["saved_job_id"], str) or len(item["saved_job_id"]) > 200 or bool(item["saved_job_id"]) != (item["status"] == "saved"): raise ValueError("Invalid queue application reference")
        if not isinstance(item["search_ids"], list) or not item["search_ids"] or any(not isinstance(k, str) for k in item["search_ids"]) or len(item["search_ids"]) != len(set(item["search_ids"])) or not set(item["search_ids"]) <= search_ids: raise ValueError("Invalid search attribution")
        if item["first_search"]["id"] not in item["search_ids"] or item["last_search"]["id"] not in item["search_ids"]: raise ValueError("Missing frozen search attribution")
        if item["source_sha256"]: identifier(item["source_sha256"], 64)
        if item["first_search"]["market"] != item["market"] or item["last_search"]["market"] != item["market"]: raise ValueError("Queue market differs from frozen searches")
        if item["row"].get("source_sha256", "") != item["source_sha256"]: raise ValueError("Queue source fingerprint differs")
    seen = set()
    for run in state["runs"]:
        keys = {"id", "search", "started_at", "finished_at", "status", "found", "added", "repeated", "excluded", "has_next", "error", "source_sha256"}
        if not isinstance(run, dict) or not keys<=set(run) or set(run)-keys-{'offset','previous_run'}: raise ValueError("Invalid discovery run")
        offset=run.get('offset',0)
        if type(offset) is not int or not 0<=offset<=500 or offset%20:raise ValueError('Invalid saved-search page offset')
        if 'previous_run' in run:identifier(run['previous_run'])
        if bool(offset)!=bool(run.get('previous_run')):raise ValueError('Continuation needs its previous page identity')
        identifier(run["id"]); config(run["search"]); timestamp(run["started_at"])
        if run["id"] in seen or run["search"]["id"] not in search_ids: raise ValueError("Invalid run identity")
        seen.add(run["id"])
        if run["status"] not in ("running", "succeeded", "failed", "interrupted"): raise ValueError("Invalid run status")
        if run["finished_at"]: timestamp(run["finished_at"])
        if (run["status"] == "running") != (run["finished_at"] == ""): raise ValueError("Run completion differs from its status")
        for key in ("found", "added", "repeated", "excluded"):
            if type(run[key]) is not int or not 0 <= run[key] <= 20: raise ValueError("Invalid run counts")
        if run["found"] + run["excluded"] > 20 or (run["status"] == "succeeded" and run["added"] + run["repeated"] != run["found"]): raise ValueError("Run counts do not reconcile")
        if type(run["has_next"]) is not bool or not isinstance(run["error"], str) or len(run["error"]) > 500: raise ValueError("Invalid run summary")
        if run["source_sha256"]: identifier(run["source_sha256"], 64)
    if sum(r["status"] == "running" for r in state["runs"]) > 1: raise ValueError("More than one active discovery run")
    return state


def snapshot_bytes(state):
    validate(state)
    payload = json.dumps(state, ensure_ascii=True, sort_keys=True).encode()
    if len(payload) > MAX_BYTES: raise ValueError("Discovery snapshot exceeds 16 MiB; no changes saved")
    return payload


def parse_snapshot(payload):
    if not isinstance(payload, bytes) or len(payload) > MAX_BYTES: raise ValueError("Discovery snapshot exceeds 16 MiB")
    try: state = json.loads(payload, object_pairs_hook=unique_json)
    except (ValueError, UnicodeError, RecursionError): raise ValueError("Invalid discovery JSON") from None
    return validate(state)


class DiscoveryStore:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.is_symlink() or (hasattr(self.path, "is_junction") and self.path.is_junction()): raise ValueError("Linked discovery storage unsupported")
        existed = self.path.exists(); self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            if existed:
                if db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID or db.execute("PRAGMA user_version").fetchone()[0] != 1: raise ValueError("Unsupported discovery database; existing file preserved")
                tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if tables != [("discovery_state",)]: raise ValueError("Unsupported discovery schema")
            else:
                db.execute("CREATE TABLE discovery_state (id INTEGER PRIMARY KEY CHECK(id=1), snapshot BLOB NOT NULL)")
                db.execute("INSERT INTO discovery_state VALUES (1, ?)", (snapshot_bytes(empty_state()),))
                db.execute("PRAGMA application_id=" + str(APPLICATION_ID)); db.execute("PRAGMA user_version=1")
            parse_snapshot(db.execute("SELECT snapshot FROM discovery_state WHERE id=1").fetchone()[0])

    def read(self):
        with closing(sqlite3.connect(self.path)) as db:
            return parse_snapshot(db.execute("SELECT snapshot FROM discovery_state WHERE id=1").fetchone()[0])

    def snapshot(self): return snapshot_bytes(self.read())

    @contextmanager
    def edit(self, expected_revision=None):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            state = parse_snapshot(db.execute("SELECT snapshot FROM discovery_state WHERE id=1").fetchone()[0])
            if expected_revision is not None and (type(expected_revision) is not int or state["revision"] != expected_revision): raise ValueError("Discovery changed; refresh and review again")
            yield state
            state["revision"] += 1
            db.execute("UPDATE discovery_state SET snapshot=? WHERE id=1", (snapshot_bytes(state),))

    def save_search(self, data, expected_revision):
        with self.edit(expected_revision) as state:
            old = next((s for s in state["searches"] if s["id"] == data.get("id")), None)
            if data.get("id") and old is None: raise ValueError("Saved search unavailable")
            value = config({**data, "id": old["id"] if old else uuid4().hex, "revision": old["revision"] + 1 if old else 1})
            if old: state["searches"][state["searches"].index(old)] = value
            else: state["searches"].append(value)
        return self.read()

    def begin_run(self, search_id, expected_revision, selection=None, previous_run=None):
        with self.edit(expected_revision) as state:
            saved = next((s for s in state["searches"] if s["id"] == search_id and not s["archived"]), None)
            if saved is None: raise ValueError("Choose an active saved search")
            effective=copy.deepcopy(saved)
            if selection is not None:
                selection=preferences(selection)
                if 'preferences' in saved and saved['preferences']!=selection:raise ValueError('Saved filters changed; edit and review the search before running')
                effective['preferences']=selection
            if any(r["status"] == "running" for r in state["runs"]): raise ValueError("A discovery run is active; wait or explicitly mark an interrupted run")
            offset=0
            if previous_run is not None:
                identifier(previous_run)
                previous=next((r for r in state['runs'] if r['id']==previous_run),None)
                if previous is None or previous['status']!='succeeded' or not previous['has_next'] or previous['search']!=effective:
                    raise ValueError('Continue only a successful page with unchanged saved filters and more source results')
                offset=previous.get('offset',0)+20
                if offset>500:raise ValueError('Saved search reached its 26-page observation limit; start a new run')
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            if sum(timestamp(r["started_at"]) > cutoff for r in state["runs"]) >= 3: raise ValueError("Saved discovery allows three run attempts per rolling 24 hours, including failures")
            run = {"id": uuid4().hex, "search": effective, "started_at": now(), "finished_at": "", "status": "running", "found": 0, "added": 0, "repeated": 0, "excluded": 0, "has_next": False, "error": "", "source_sha256": ""}
            if previous_run is not None:run.update(offset=offset,previous_run=previous_run)
            state["runs"] = (state["runs"] + [run])[-100:]
        return run

    def finish_run(self, run_id, result=None, error=""):
        with self.edit() as state:
            run = next((r for r in state["runs"] if r["id"] == run_id), None)
            if run is None or run["status"] != "running": raise ValueError("Run was interrupted; returned results were not queued")
            run["finished_at"] = now()
            if result is not None and result.get('page',{}).get('offset',0)!=run.get('offset',0):raise ValueError('Returned page differs from the requested saved-search page')
            if result is None:
                run.update(status="failed", error=error[:500])
            else:
                if not isinstance(result, dict) or not isinstance(result.get("jobs"), list) or len(result["jobs"]) > 20: raise ValueError("Unsupported saved-search page")
                for observed in result["jobs"]:
                    row(observed)
                    key = candidate_key(observed, run["search"]["market"])
                    old = next((c for c in state["candidates"] if c["id"] == key), None)
                    if old:
                        old["last_seen"] = run["finished_at"]; old["last_search"] = copy.deepcopy(run["search"])
                        if run["search"]["id"] not in old["search_ids"]: old["search_ids"].append(run["search"]["id"])
                        run["repeated"] += 1
                    else:
                        state["candidates"].append({"id": key, "row": copy.deepcopy(observed), "market": run["search"]["market"], "status": "pending", "saved_job_id": "", "first_seen": run["finished_at"], "last_seen": run["finished_at"], "first_search": copy.deepcopy(run["search"]), "last_search": copy.deepcopy(run["search"]), "search_ids": [run["search"]["id"]], "source_sha256": result.get("source_sha256", "")})
                        if run.get('offset'):state['candidates'][-1]['source_offset']=run['offset']
                        run["added"] += 1
                run.update(status="succeeded", found=len(result["jobs"]), excluded=len(result.get("excluded", [])), has_next=result.get("page", {}).get("has_next", False), source_sha256=result.get("source_sha256", ""))
        return self.read()

    def interrupt(self, run_id, expected_revision):
        with self.edit(expected_revision) as state:
            run = next((r for r in state["runs"] if r["id"] == run_id and r["status"] == "running"), None)
            if run is None: raise ValueError("No active run with that identity")
            run.update(status="interrupted", finished_at=now(), error="Interrupted locally; provider processing cannot be undone")
        return self.read()

    def decide(self, candidate_id, action, expected_revision, saved_job_id=""):
        with self.edit(expected_revision) as state:
            item = next((c for c in state["candidates"] if c["id"] == candidate_id), None)
            if item is None or item["status"] == "saved" or action not in ("pending", "kept", "dismissed", "saved"): raise ValueError("Unsupported or stale queue decision")
            item.update(status=action, saved_job_id=saved_job_id if action == "saved" else "")
        return self.read()

    def forget(self, candidate_id, expected_revision):
        with self.edit(expected_revision) as state:
            item = next((c for c in state["candidates"] if c["id"] == candidate_id and c["status"] in ("dismissed", "saved")), None)
            if item is None: raise ValueError("Resolve a candidate before explicitly removing its cached observation")
            state["candidates"].remove(item)
        return self.read()

    def restore(self, payload):
        state = parse_snapshot(payload)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if self.read() != empty_state(): raise ValueError("Restore discovery only into a new empty workspace")
            db.execute("UPDATE discovery_state SET snapshot=? WHERE id=1", (snapshot_bytes(state),))


def verify_bindings(state, store, parts):
    """Replay provider observations and saved application references without network access."""
    validate(state)
    parsed = {}
    def evidence(digest,offset=0):
        key=(digest,offset)
        if key not in parsed:
            payload = parts.get("web-artifacts/sources/" + digest + ".json")
            if payload is None or hashlib.sha256(payload).hexdigest() != digest: raise ValueError("Original discovery source is missing or differs")
            parsed[key] = parse_search(payload,offset)
        return parsed[key]
    for item in state["candidates"]:
        if item["source_sha256"]:
            expected = next((r for r in evidence(item["source_sha256"],item.get('source_offset',0))["jobs"] if r["id"] == item["row"]["id"]), None)
            if expected is None or any(expected.get(k) != item["row"].get(k) for k in ROW_FIELDS | {"source_sha256", "source_url"}): raise ValueError("Queued posting differs from its original source")
        if item["status"] == "saved":
            job = store.load(item["saved_job_id"])
            if job["market"] != item["market"] or job["title"] != item["row"]["title"] or job["company"] != item["row"]["company"] or job["source_url"] != item["row"]["url"] or json.loads(job["snapshot"])["posting"] != item["row"]["posting"]:
                raise ValueError("Queue reference differs from its exact saved application")
    for run in state["runs"]:
        if run["source_sha256"]:
            result = filter_result(evidence(run["source_sha256"],run.get('offset',0)),run["search"].get("preferences"),run["search"]["remote"])
            if result['page']['offset']!=run.get('offset',0):raise ValueError('Saved-search page differs from its original source')
            if run["status"] != "succeeded" or run["found"] != len(result["jobs"]) or run["excluded"] != len(result["excluded"]) or run["has_next"] != result["page"]["has_next"]: raise ValueError("Run summary differs from its original observation")
