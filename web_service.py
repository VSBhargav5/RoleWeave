"""Local web application operations; reuses the existing validated domain models."""
from datetime import date
from board_workspace import BoardWorkspace, PREFIX as BOARD_PREFIX
from discovery_store import DiscoveryStore
from model_preferences import read_settings, save_settings
from workflow_insights import insights
from resume_theme import parse_theme, validate_theme
import base64
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import threading
import time
from uuid import uuid4

from application_draft import list_drafts, load_draft
from application_email import FIELDS as EMAIL_FIELDS, MAX_EMAIL_SNAPSHOT, email_snapshot, make_email_snapshot, replay_email, preview_fingerprint
from application_dossier import build_dossier
from career_profile import imported_career_facts, profile_snapshot, SECTIONS
from career_entries import SCHEMAS, fact_text
from cover_letter import make_letter, letter_snapshot
from demo_data import seed_practice
from job_search import JobSearch, search_path
from job_store import JobStore
from recipient_bundle import recipient_bytes
from resume_render import resume_text
from resume_versions import decoded, make_resume_version
from resume_import import extract_in_worker, document_name, MAX_FILE
from roleweave import MAX_BYTES, MARKETS, review_snapshot
from rehearsal_cards import practice_cards
from rehearsal_journal import make_rehearsal, rehearsal_snapshot, bound_rehearsal, MAX_REHEARSAL_BYTES
from runtime_paths import APP_VERSION
from safe_export import publish_bytes
from source_links import source_link
from submission_receipt import record_basic_submission
from tailoring_session import TailoringSession
from workspace_bundle import export_bundle, inspect_bundle, restore_bundle, recovered_database, recovery_list, no_link


def require(data, allowed, required=()):
    if not isinstance(data, dict) or set(data) - set(allowed) or not set(required) <= set(data):
        raise ValueError("Unsupported or missing request fields")
    return data


def confirmed(data):
    if data.get("confirmed") is not True:
        raise ValueError("Review the content and explicitly confirm this action")


def browser_profile(profile):
    values = {"full_name": profile.get("name", ""), "first_name": profile.get("first_name", ""),
              "last_name": profile.get("last_name", ""), "email": profile.get("email", ""),
              "phone": profile.get("phone", ""), "location": profile.get("location", ""),
              "linkedin": profile.get("linkedin", ""), "website": profile.get("website", "")}
    for key, value in values.items():
        if not isinstance(value, str) or len(value) > 2000 or any(ord(c) < 32 for c in value):
            raise ValueError("Use single-line contact values for browser filling")
        if value and key in ("linkedin", "website"):
            source_link(value)
    return {"format": "roleweave-browser-profile-v1", "fields": values}


class WebService:
    def __init__(self, path, demo=False):
        self.store = JobStore(path)
        self.demo = demo
        self.searcher = JobSearch()
        self.boards = BoardWorkspace(self.store,demo=demo)
        self.searches = {}
        self.lock = threading.RLock()
        self.imports = {}
        self.pending_recovery = None
        self.tailoring = TailoringSession(self.store,demo=self.demo)
        self.artifacts = self.store.path.parent / "web-artifacts"
        self.discovery = DiscoveryStore(self.store.path.with_suffix(".discovery.db"))

    def profile(self):
        item = self.store.active_profile()
        if item is None:
            return None
        return {key: item[key] for key in ("id", "created_at", "snapshot_sha256", "profile")}

    def bootstrap(self):
        jobs = self.store.list_jobs()
        today = date.today().isoformat()
        label='Recovered workspace · '+self.store.path.parent.name[:8] if self.store.path.parent.parent.name=='recovered' else 'Main workspace'
        return {"version": APP_VERSION, "demo": self.demo, "workspace_label": 'Synthetic practice' if self.demo else label,
                "profile": self.profile(), "jobs": jobs, "career_sections":SECTIONS,"entry_fields":SCHEMAS, "ai_provider": read_settings(self.store),
                "resumes": self.store.list_resumes(), "letters": self.letters(),
                "recoveries": recovery_list(self.store.path.parent/'recovered'), "stats": {
                    "saved": len(jobs), "active": sum(j["stage"] in ("applied", "interview", "offer") for j in jobs),
                    "interviews": sum(j["stage"] == "interview" for j in jobs),
                    "due": sum(bool(j["follow_up"]) and j["follow_up"] <= today and j["stage"] not in ("closed", "withdrawn") for j in jobs)}}

    def board_action(self,data):
        require(data,('action','provider','token','id','row_id','company','market','sha256','confirmed','before','after'))
        action=data.get('action')
        keys={'fetch':{'action','provider','token','confirmed'},'close':{'action','id'},'import':{'action','id','row_id','company','market','sha256','confirmed'},'compare':{'action','before','after'}}
        if action not in keys or set(data)!=keys[action]:raise ValueError('Invalid board action fields')
        if action=='fetch':return self.boards.start(data['provider'],data['token'],data['confirmed'])
        if action=='close':return self.boards.close(data['id'])
        if action=='compare':
            from discovery_archive import compare_observations
            with self.boards.lock:return {'items':compare_observations(self.boards.ready(data['before'])['feed'],self.boards.ready(data['after'])['feed'])}
        return self.boards.import_row(data['id'],data['row_id'],data['company'],data['market'],data['sha256'],data['confirmed'])

    def resume_theme(self, data):
        require(data, ('theme','source'))
        if set(data)=={'theme'}:return {'theme':validate_theme(data['theme'])}
        if set(data)=={'source'} and isinstance(data['source'],str):return {'theme':parse_theme(data['source'].encode('utf-8'))}
        raise ValueError('Choose exactly one theme or JSON source')

    def workflow_insights(self, data):
        require(data, ('month', 'market'))
        return insights(self.store, data.get('month'), data.get('market','all'))

    def save_model_settings(self, data):
        require(data, ('config', 'expected_sha256'), ('config', 'expected_sha256'))
        if not isinstance(data['expected_sha256'], str) or not re.fullmatch('[a-f0-9]{64}', data['expected_sha256']):
            raise ValueError('Refresh provider preferences before saving')
        return save_settings(self.store, data['config'], data['expected_sha256'])

    def job(self, identifier):
        item = self.store.load(identifier)
        data = json.loads(item["snapshot"])
        return {key: item[key] for key in ("id", "title", "company", "source_url", "market", "captured_at", "input_sha256")} | {
            "posting": data["posting"], "review_data": data, "review": item["review"],
            "history": self.store.application_history(identifier), "resumes": self.store.list_resumes(identifier),
            "letters": self.letters(identifier), "drafts": list_drafts(self.store,identifier),
            "practice_cards": practice_cards(item), "rehearsals": self.rehearsals(identifier),
            "email_drafts": self.email_drafts(identifier)}

    def save_job(self, data):
        require(data, ("title", "company", "source_url", "market", "posting"), ("title", "company", "market", "posting"))
        if isinstance(data['posting'],str) and data['posting'].startswith(BOARD_PREFIX):raise ValueError('Use employer-board replay/import for reserved source evidence; do not paste its protocol header')
        if data.get("source_url"):
            source_link(data["source_url"])
        snapshot = json.dumps({"market": data["market"], "posting": data["posting"], "facts": [], "requirements": []}, ensure_ascii=False).encode()
        identifier = self.store.save(snapshot, data["title"], data["company"], data.get("source_url", ""))
        return self.job(identifier)

    def career_entry(self,data):
        require(data,('fact',),('fact',))
        # Validate in the existing whole-profile contract, without writing or inference.
        item=data['fact'];base={k:'' for k in ('name','headline','email','phone','location','links','summary')};base.update(name='Entry preview',facts=[item])
        profile_snapshot(json.dumps(base,ensure_ascii=True).encode())
        return {'fact':item,'text':fact_text(item)}

    def save_profile(self, data):
        require(data, ("profile", "confirmed", "expected_active_sha256"), ("profile", "confirmed"))
        confirmed(data)
        snapshot = json.dumps(data["profile"], ensure_ascii=False).encode()
        active = self.store.active_profile()
        expected=data.get('expected_active_sha256')
        if expected is not None and (not isinstance(expected,str) or expected!=(active['snapshot_sha256'] if active else '')):
            raise ValueError('The active profile changed in another window. Keep your draft and reload the current profile before saving.')
        if active and active["profile"] == data["profile"]:
            return self.profile()
        self.store.save_profile(snapshot, expected_active_sha256=expected)
        return self.profile()

    def preview_resume_import(self, data):
        require(data, ('name','base64'), ('name','base64'))
        document_name(data['name'])
        if not isinstance(data['base64'],str) or len(data['base64'])>6*1024*1024:
            raise ValueError('Resume must contain at most 4 MiB')
        payload=base64.b64decode(data['base64'],validate=True)
        if len(payload)>MAX_FILE:raise ValueError('Resume must contain at most 4 MiB')
        result=extract_in_worker(payload,data['name'])
        identifier=uuid4().hex
        with self.lock:
            self.imports={k:v for k,v in self.imports.items() if time.monotonic()-v['at']<600}
            if len(self.imports)>=5:raise ValueError('Too many pending imports. Finish one or retry after ten minutes')
            self.imports[identifier]={'at':time.monotonic(),'payload':payload,'name':data['name'],'result':result}
        return result | {'id':identifier,'name':data['name']}

    def commit_resume_import(self, data):
        require(data, ('id','selected','confirmed'), ('id','selected','confirmed'))
        confirmed(data)
        with self.lock:
            entry=self.imports.get(data['id'])
            if entry is None or time.monotonic()-entry['at']>=600:
                raise ValueError('Resume preview expired. Select the file again and review it')
            rows=data['selected']
            if not isinstance(rows,list) or not 1<=len(rows)<=100:
                raise ValueError('Select between 1 and 100 reviewed excerpts')
            blocks={b['id']:b for b in entry['result']['blocks']}
            seen=set();facts=[]
            for row in rows:
                require(row,('id','section'),('id','section'))
                if not isinstance(row['id'],str) or row['id'] in seen or row['id'] not in blocks or row['section'] not in SECTIONS:
                    raise ValueError('Select distinct observed excerpts and choose each section')
                seen.add(row['id']);block=blocks[row['id']];digest=entry['result']['sha256']
                facts.append({'id':'resume:'+digest+':'+row['id']+':'+hashlib.sha256(block['text'].encode()).hexdigest()[:16],
                              'claim':block['text'],'source':f"{entry['name']}; original SHA256 {digest}; extracted block {row['id']}. Human-selected excerpt, not independently verified.",
                              'reviewed':True,'section':row['section']})
            directory=self.artifacts/'resume-imports'
            no_link(self.artifacts);no_link(directory)
            directory.mkdir(parents=True,exist_ok=True)
            path=directory/(entry['result']['sha256']+Path(entry['name']).suffix.lower())
            if path.exists():
                if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['result']['sha256']:
                    raise ValueError('Existing resume source fingerprint differs; no file was overwritten')
            else:publish_bytes(path,entry['payload'])
            return {'facts':facts,'source_sha256':entry['result']['sha256']}

    def save_review(self, data):
        require(data, ("id", "review", "confirmed"), ("id", "review", "confirmed"))
        confirmed(data)
        original = self.store.load(data["id"])
        snapshot = json.dumps(data["review"], ensure_ascii=False).encode()
        review_snapshot(snapshot)
        old = json.loads(original["snapshot"])
        if data["review"]["posting"] != old["posting"] or data["review"]["market"] != old["market"]:
            raise ValueError("This review must preserve its original posting and market")
        if old == data["review"]:
            return self.job(original["id"])
        identifier=None
        if old['posting'].startswith(BOARD_PREFIX):
            for candidate in self.store.list_jobs():
                if all(candidate[k]==original[k] for k in ('title','company','source_url','market')) and self.store.load(candidate['id'])['snapshot']==snapshot:identifier=candidate['id'];break
        if identifier is None:identifier = self.store.save(snapshot, original["title"], original["company"], original["source_url"])
        self.boards.inherit_receipt(original['id'],identifier)
        return self.job(identifier)

    def save_discovery_search(self, data):
        fields = {"id", "name", "query", "location", "country", "remote", "market", "archived"}
        require(data, fields | {"expected_revision"}, fields - {"id"} | {"expected_revision"})
        return self.discovery.save_search({k: v for k, v in data.items() if k in fields}, data["expected_revision"])

    def _archive_search_source(self, result):
        digest = result.get("source_sha256")
        if not digest: return
        snapshot = self.searcher.snapshots.get(digest)
        if snapshot is None or hashlib.sha256(snapshot).hexdigest() != digest:
            raise ValueError("Original source evidence expired; repeat the search")
        directory = self.artifacts / "sources"
        no_link(self.artifacts); no_link(directory)
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / (digest + ".json")
        no_link(destination)
        if destination.exists():
            if destination.read_bytes() != snapshot: raise ValueError("Existing source evidence does not match")
        else: publish_bytes(destination, snapshot)

    def _existing_observation(self, row, market):
        for saved in self.store.list_jobs():
            if saved["source_url"] == row["url"] and saved["market"] == market and saved["title"] == row["title"] and saved["company"] == row["company"]:
                item = self.store.load(saved["id"])
                if json.loads(item["snapshot"])["posting"] == row["posting"]: return saved["id"]
        return ""

    def run_discovery(self, data):
        require(data, ("id", "expected_revision", "confirmed"), ("id", "expected_revision", "confirmed")); confirmed(data)
        run = self.discovery.begin_run(data["id"], data["expected_revision"])
        try:
            saved = run["search"]
            if self.demo:
                rows = [{"id": "practice-" + str(i), "title": "Practice " + saved["query"].title() + " " + str(i),
                         "company": "Synthetic discovery employer", "posting": "Python required. Synthetic saved-search practice only; no live opportunity.",
                         "url": "https://example.invalid/discovery/" + str(i), "location": saved["location"] or "Synthetic location",
                         "work_mode": "remote" if saved["remote"] else "Not stated", "posted_at": "Synthetic fixture", "source": "Synthetic preview"} for i in (1, 2)]
                result = {"jobs": rows, "excluded": [], "page": {"has_next": False}, "source": "Synthetic preview"}
            else:
                result = self.search({key: saved[key] for key in ("query", "location", "country", "remote")})
            self._archive_search_source(result)
            return self.discovery.finish_run(run["id"], result)
        except (ValueError, OSError, sqlite3.Error) as exc:
            message = str(exc) if isinstance(exc, ValueError) else "Discovery could not complete; existing queue preserved"
            current = self.discovery.read()
            if any(r["id"] == run["id"] and r["status"] == "running" for r in current["runs"]):
                self.discovery.finish_run(run["id"], error=message)
            raise ValueError(message) from None

    def discovery_decision(self, data):
        require(data, ("id", "action", "expected_revision", "confirmed"), ("id", "action", "expected_revision", "confirmed")); confirmed(data)
        if data["action"] == "interrupt": return self.discovery.interrupt(data["id"], data["expected_revision"])
        if data["action"] == "forget": return self.discovery.forget(data["id"], data["expected_revision"])
        if data["action"] != "save":
            actions = {"keep": "kept", "dismiss": "dismissed", "reopen": "pending"}
            if data["action"] not in actions: raise ValueError("Unsupported queue action")
            return self.discovery.decide(data["id"], actions[data["action"]], data["expected_revision"])
        with self.discovery.edit(data["expected_revision"]) as state:
            item = next((c for c in state["candidates"] if c["id"] == data["id"]), None)
            if item is None: raise ValueError("Queue observation unavailable")
            if item["status"] == "saved":
                self.store.load(item["saved_job_id"])
            else:
                row, market = item["row"], item["market"]
                job_id = self._existing_observation(row, market)
                if not job_id:
                    snapshot = json.dumps({"market": market, "posting": row["posting"], "facts": [], "requirements": []}, ensure_ascii=False).encode()
                    job_id = self.store.save(snapshot, row["title"], row["company"], row["url"])
                item.update(status="saved", saved_job_id=job_id)
        return self.discovery.read()

    def search(self, data):
        require(data, ("query", "location", "country", "remote", "offset"), ("query",))
        search_path(data["query"], data.get("location", ""), data.get("country", ""), data.get("remote", False), data.get("offset", 0))
        if self.demo:
            rows = []
            for row in self.store.list_jobs():
                item = self.job(row["id"])
                if all(word.casefold() in (row["title"] + " " + item["posting"]).casefold() for word in data["query"].split()):
                    rows.append({"id": row["id"], "title": row["title"], "company": row["company"], "posting": item["posting"],
                                 "url": row["source_url"], "location": "India / remote · synthetic", "work_mode": "remote", "posted_at": "Synthetic fixture", "source": "Synthetic preview"})
            offset, total = data.get("offset", 0), len(rows)
            result = {"jobs": rows[offset:offset+20], "excluded": [], "total": total,
                      "page": {"offset": offset, "returned": len(rows[offset:offset+20]), "has_next": offset+20 < total},
                      "source": "Synthetic preview", "source_url": "", "notice": "Synthetic preview. No provider contacted."}
        else:
            result = self.searcher.search(data["query"], data.get("location", ""), data.get("country", ""), data.get("remote", False), data.get("offset", 0))
        identifier = uuid4().hex
        with self.lock:
            if len(self.searches) >= 30:
                self.searches.clear()
            self.searches[identifier] = result
        return result | {"search_id": identifier}

    def save_search_job(self, data):
        require(data, ("search_id", "job_id", "market"), ("search_id", "job_id", "market"))
        if data["market"] not in MARKETS:
            raise ValueError("Choose your application market explicitly")
        with self.lock:
            result = self.searches.get(data["search_id"])
        if result is None:
            raise ValueError("Search results expired locally. Search again before saving.")
        row = next((item for item in result["jobs"] if item["id"] == data["job_id"]), None)
        if row is None:
            raise ValueError("That job does not belong to the reviewed search result")
        # The application destination comes from the observed provider record, never a pasted board URL.
        for old in self.store.list_jobs():
            if old["source_url"] == row["url"] and old["market"] == data["market"] and self.job(old["id"])["posting"] == row["posting"]:
                return self.job(old["id"])
        self._archive_search_source(result)
        return self.save_job({"title": row["title"], "company": row["company"], "source_url": row["url"], "market": data["market"], "posting": row["posting"]})

    def resume(self, data, freeze=False):
        require(data, ("profile_id", "profile_sha256", "job_id", "fact_ids", "label", "theme", "preview_sha256", "confirmed"), ("profile_id", "profile_sha256", "job_id", "fact_ids"))
        profile = self.store.load_profile(data["profile_id"])
        if profile["snapshot_sha256"] != data["profile_sha256"]:
            raise ValueError("Profile evidence changed; reload and review it")
        job=self.store.load(data["job_id"])
        theme=data.get("theme", "classic")
        snapshot=make_resume_version(profile,data["fact_ids"],data.get("label", "Reviewed application resume"),job,True,theme)
        record=json.loads(snapshot)
        digest=hashlib.sha256(snapshot).hexdigest()
        text = resume_text(profile["profile"], data["fact_ids"])
        if not freeze:
            return {"text": text, "html": decoded(record["html_base64"],8*1024*1024).decode("utf-8"),
                    "pdf_base64": record["pdf_base64"], "preview_sha256": digest,
                    "profile_id": profile["id"], "profile_sha256": profile["snapshot_sha256"]}
        confirmed(data)
        if ("theme" in data or "preview_sha256" in data) and data.get("preview_sha256") != digest:
            raise ValueError("Resume preview changed; preview and review the current layout and selection again")
        identifier = self.store.create_resume(profile["id"], data["fact_ids"], data.get("label", "Reviewed application resume"), data["job_id"], include_pdf=True, confirmed=True, theme=theme)
        return {"id": identifier, "text": text}

    def get_resume(self, identifier):
        record = self.store.load_resume(identifier)["resume"]
        profile, _ = profile_snapshot(decoded(record["profile_snapshot_base64"], MAX_BYTES))
        return {"profile": profile, "profile_id": record["profile_id"], "profile_sha256": record["profile_sha256"],
                "selected_fact_ids": record["selected_fact_ids"]}

    def review_from_profile(self, data):
        require(data, ("job_id", "profile_id", "profile_sha256", "quote", "fact_ids", "confirmed"),
                ("job_id", "profile_id", "profile_sha256", "quote", "fact_ids", "confirmed"))
        confirmed(data)
        profile = self.store.load_profile(data["profile_id"])
        if profile["snapshot_sha256"] != data["profile_sha256"]:
            raise ValueError("Reload the profile before selecting evidence")
        facts = imported_career_facts(profile, data["fact_ids"])
        original = self.store.load(data["job_id"])
        review = json.loads(original["snapshot"])
        existing = {fact["id"] for fact in review["facts"]}
        review["facts"].extend(fact for fact in facts if fact["id"] not in existing)
        review["requirements"].append({"id": uuid4().hex, "quote": data["quote"], "fact_ids": [fact["id"] for fact in facts]})
        return self.save_review({"id": original["id"], "review": review, "confirmed": True})

    def email_drafts(self, job_id):
        directory = self.artifacts / "emails"
        no_link(self.artifacts); no_link(directory)
        if not directory.exists(): return []
        items = []; total = 0
        for index, path in enumerate(directory.iterdir()):
            no_link(path)
            if index >= 1000 or not re.fullmatch(r"[a-f0-9]{32}\.json", path.name):
                raise ValueError("Unsupported or excessive email draft files")
            total += path.stat().st_size
            if total > 64 * 1024 * 1024: raise ValueError("Email draft collection exceeds 64 MiB")
            with path.open("rb") as source: record = email_snapshot(source.read(MAX_EMAIL_SNAPSHOT + 1))
            if record["values"]["job_id"] == job_id:
                items.append({"id": path.stem, "subject": record["values"]["subject"], "created_at": record["created_at"]})
        return sorted(items, key=lambda row: (row["created_at"], row["id"]), reverse=True)

    def get_email(self, identifier, job_id=None):
        with self._artifact("emails", identifier).open("rb") as source: snapshot = source.read(MAX_EMAIL_SNAPSHOT + 1)
        record, payload, attachments = replay_email(self.store, snapshot)
        if job_id is not None and record["values"]["job_id"] != job_id:
            raise ValueError("Email draft belongs to another exact saved review")
        return {"id": identifier, "values": record["values"], "attachments": attachments,
                "eml_sha256": record["eml_sha256"], "sent": False}

    def email(self, data, freeze=False):
        require(data, EMAIL_FIELDS | {"preview_sha256", "confirmed"}, EMAIL_FIELDS - {"letter_id"})
        values = {key: data.get(key, "") for key in EMAIL_FIELDS}
        letter = self._letter_bytes(values["letter_id"]) if values["letter_id"] else b""
        snapshot = make_email_snapshot(self.store, values, letter)
        record, payload, attachments = replay_email(self.store, snapshot)
        fingerprint = preview_fingerprint(record)
        if not freeze:
            return {"values": values, "attachments": attachments, "preview_sha256": fingerprint,
                    "eml_sha256": record["eml_sha256"], "bytes": len(payload), "sent": False}
        confirmed(data)
        if data.get("preview_sha256") != fingerprint:
            raise ValueError("Email or attachments changed; preview and review again")
        with self.lock:
            directory = self.artifacts / "emails"
            no_link(self.artifacts); no_link(directory)
            count = 0; total = len(snapshot)
            if directory.exists():
                for path in directory.iterdir():
                    no_link(path); count += 1; total += path.stat().st_size
                    if count >= 1000 or total > 64 * 1024 * 1024:
                        raise ValueError("Email draft capacity reached; no draft was written")
            identifier = uuid4().hex
            publish_bytes(self._artifact("emails", identifier), snapshot)
        return {"id": identifier, "sent": False}

    def rehearsal(self, identifier, job_id=None):
        path = self._artifact("rehearsals", identifier)
        with path.open("rb") as source:
            snapshot = source.read(MAX_REHEARSAL_BYTES + 1)
        record, digest = rehearsal_snapshot(snapshot)
        bound_rehearsal(self.store, record)
        if job_id is not None and record["job_context"]["id"] != job_id:
            raise ValueError("Rehearsal belongs to another exact saved review")
        return {"id": identifier, "sha256": digest, "record": record}

    def rehearsals(self, job_id):
        directory = self.artifacts / "rehearsals"
        no_link(self.artifacts); no_link(directory)
        if not directory.exists():
            return []
        result = []; total = 0
        for index, path in enumerate(directory.iterdir()):
            no_link(path)
            if index >= 1000 or not re.fullmatch(r"[a-f0-9]{32}\.json", path.name):
                raise ValueError("Unsupported or excessive rehearsal files")
            total += path.stat().st_size
            if total > 64 * 1024 * 1024:
                raise ValueError("Rehearsal collection exceeds 64 MiB")
            saved = self.rehearsal(path.stem)
            record = saved["record"]
            if record["job_context"]["id"] == job_id:
                result.append({"id": path.stem, "recorded_at": record["recorded_at"],
                               "questions": len(record["answers"]), "sha256": saved["sha256"]})
        return sorted(result, key=lambda row: (row["recorded_at"], row["id"]), reverse=True)

    def save_rehearsal(self, data):
        require(data, ("job_id", "answers", "confirmed"), ("job_id", "answers", "confirmed"))
        confirmed(data)
        item = self.store.load(data["job_id"])
        snapshot = make_rehearsal(item, data["answers"], confirmed=True)
        with self.lock:
            directory = self.artifacts / "rehearsals"
            no_link(self.artifacts); no_link(directory)
            count = 0; total = len(snapshot)
            if directory.exists():
                for path in directory.iterdir():
                    no_link(path)
                    count += 1; total += path.stat().st_size
                    if count >= 1000 or total > 64 * 1024 * 1024:
                        raise ValueError("Rehearsal capacity reached; no new version was written")
            identifier = uuid4().hex
            publish_bytes(self._artifact("rehearsals", identifier), snapshot)
        return {"id": identifier, "learning_verified": False}

    def _artifact(self, kind, identifier):
        if kind not in ("letters", "packets", "rehearsals", "emails") or not isinstance(identifier, str) or not re.fullmatch(r"[a-f0-9]{32}", identifier):
            raise ValueError("Invalid saved artifact identity")
        directory = self.artifacts / kind
        no_link(self.artifacts); no_link(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (identifier + (".zip" if kind == "packets" else ".json"))
        if path.is_symlink():
            raise ValueError("Linked artifacts are unsupported")
        return path

    def _letter_bytes(self, identifier):
        with self._artifact("letters", identifier).open("rb") as source:
            payload = source.read(4 * 1024 * 1024 + 1)
        letter_snapshot(payload)
        return payload

    def letters(self, job_id=None):
        """Discover saved versions after restart; never treat an invalid file as a document."""
        if job_id is not None:
            self.store.load(job_id)
        directory = self.artifacts / "letters"
        if not directory.exists():
            return {"items": [], "issues": []}
        if directory.is_symlink():
            raise ValueError("Linked letter directories are unsupported")
        items, issues, total = [], [], 0
        for index, path in enumerate(directory.iterdir()):
            if index >= 1000:
                issues.append("Letter catalog exceeds 1000 entries; not all files were inspected.")
                break
            if not re.fullmatch(r"[a-f0-9]{32}\.json", path.name):
                continue
            try:
                total += path.stat().st_size
                if total > 64 * 1024 * 1024:
                    issues.append("Letter catalog exceeds 64 MiB; not all files were inspected.")
                    break
                record, _ = letter_snapshot(self._letter_bytes(path.stem))
                context = record["job_context"]
                if job_id is None or context["id"] == job_id:
                    items.append({"id": path.stem, "job_id": context["id"], "title": context["title"],
                                  "company": context["company"], "profile_id": record["profile_id"],
                                  "profile_sha256": record["profile_sha256"], "text_sha256": record["text_sha256"], "has_pdf": "pdf_base64" in record})
            except (OSError, ValueError):
                issues.append("A saved letter failed verification; its original file was preserved.")
        return {"items": sorted(items, key=lambda item: (item["company"], item["title"], item["id"])), "issues": issues}

    def get_letter(self, identifier):
        record, _ = letter_snapshot(self._letter_bytes(identifier))
        return {"text": record["text"], "job_id": record["job_context"]["id"], "text_sha256": record["text_sha256"], "has_pdf": "pdf_base64" in record}

    def letter(self, data, freeze=True):
        require(data, ("job_id", "resume_id", "fact_ids", "motivation", "closing", "include_pdf", "preview_sha256", "confirmed"), ("job_id", "resume_id", "fact_ids", "motivation", "closing", "confirmed"))
        if freeze:
            confirmed(data)
        resume = self.store.load_resume(data["resume_id"])
        if not resume["resume"]["job_context"] or resume["resume"]["job_context"]["id"] != data["job_id"]:
            raise ValueError("Choose a resume frozen for this exact job")
        profile = self.store.load_profile(resume["resume"]["profile_id"])
        snapshot = make_letter(profile, data["fact_ids"], self.store.load(data["job_id"]), data["motivation"], data["closing"], confirmed=True, include_pdf=data.get("include_pdf",False))
        if not freeze:
            record=letter_snapshot(snapshot)[0]
            return {"text": record["text"], "pdf_base64": record.get("pdf_base64", ""), "preview_sha256": hashlib.sha256(snapshot).hexdigest()}
        if (data.get("include_pdf") or "preview_sha256" in data) and data.get("preview_sha256") != hashlib.sha256(snapshot).hexdigest():
            raise ValueError("Letter preview changed; preview and review it again")
        identifier = uuid4().hex
        publish_bytes(self._artifact("letters", identifier), snapshot)
        return {"id": identifier, "text": letter_snapshot(snapshot)[0]["text"]}

    def packet(self, data):
        require(data, ("job_id", "resume_id", "letter_id", "formats", "confirmed"), ("job_id", "resume_id", "formats", "confirmed"))
        confirmed(data)
        letter = self._letter_bytes(data["letter_id"]) if data.get("letter_id") else None
        dossier = build_dossier(self.store.load(data["job_id"]), self.store.load_resume(data["resume_id"]), self.store.application_history(data["job_id"]), letter=letter)
        payload = recipient_bytes(dossier, data["formats"])
        identifier = uuid4().hex
        publish_bytes(self._artifact("packets", identifier), payload)
        return {"id": identifier}

    def track(self, data):
        require(data, ("job_id", "stage", "note", "follow_up", "expected_revision"), ("job_id", "stage", "note", "follow_up", "expected_revision"))
        if type(data["expected_revision"]) is not int or data["expected_revision"] < 0:
            raise ValueError("Review the current tracking revision before saving")
        return self.store.record_application(data["job_id"], data["stage"], data["note"], data["follow_up"], expected_revision=data["expected_revision"])

    def submit_observation(self, data):
        require(data, ("job_id", "submitted_on", "channel", "reference", "note", "follow_up", "expected_revision", "confirmed"),
                ("job_id", "submitted_on", "channel", "reference", "note", "follow_up", "expected_revision", "confirmed"))
        if type(data["expected_revision"]) is not int or data["expected_revision"] < 0:
            raise ValueError("Review the current tracking revision before saving")
        return record_basic_submission(self.store, data["job_id"], data["submitted_on"], data["channel"], data["reference"], data["note"], confirmed=data["confirmed"], follow_up=data["follow_up"], expected_revision=data["expected_revision"])

    def backup(self):
        with tempfile.TemporaryDirectory(prefix="roleweave-backup-") as folder:
            path = Path(folder) / "backup.json"
            self.store.backup(path)
            return path.read_bytes()

    def workspace_bundle(self):
        return export_bundle(self.store,self.artifacts)

    def preview_recovery(self, payload):
        _,summary=inspect_bundle(payload)
        identifier=uuid4().hex
        with self.lock:self.pending_recovery={'id':identifier,'at':time.monotonic(),'payload':payload,'summary':summary}
        return {'id':identifier,'summary':summary}

    def restore_recovery(self, data):
        require(data,('id','sha256','confirmed'),('id','sha256','confirmed'));confirmed(data)
        with self.lock:
            pending=self.pending_recovery
            if pending is None or pending['id']!=data['id'] or pending['summary']['sha256']!=data['sha256'] or time.monotonic()-pending['at']>=600:
                raise ValueError('Recovery preview expired or differs. Choose and review the bundle again')
            result=restore_bundle(pending['payload'],self.store.path.parent/'recovered')
            self.pending_recovery=None
            return result

    def recovery_database(self, data):
        require(data,('id','confirmed'),('id','confirmed'));confirmed(data)
        return recovered_database(self.store.path.parent/'recovered',data['id'])

    def restore(self, payload):
        with tempfile.TemporaryDirectory(prefix="roleweave-restore-") as folder:
            path = Path(folder) / "backup.json"
            path.write_bytes(payload)
            added, skipped = self.store.restore(path)
            return {"added": added, "skipped": skipped}

    def download(self, kind, identifier, format="pdf"):
        if kind == "email":
            with self._artifact("emails", identifier).open("rb") as source:
                snapshot = source.read(MAX_EMAIL_SNAPSHOT + 1)
            record, payload, attachments = replay_email(self.store, snapshot)
            return payload, "message/rfc822", "application-draft.eml"
        if kind == "rehearsal":
            with self._artifact("rehearsals", identifier).open("rb") as source:
                snapshot = source.read(MAX_REHEARSAL_BYTES + 1)
            bound_rehearsal(self.store, rehearsal_snapshot(snapshot)[0])
            return snapshot, "application/json", "private-rehearsal.json"
        if kind == "resume":
            record = self.store.load_resume(identifier)["resume"]
            if format == "txt":
                profile = self.store.load_profile(record["profile_id"])["profile"]
                return resume_text(profile, record["selected_fact_ids"]).encode(), "text/plain; charset=utf-8", "resume.txt"
            if format not in ("pdf", "html"):
                raise ValueError("Choose PDF, HTML or TXT")
            value = decoded(record[format + "_base64"], 8 * 1024 * 1024)
            if not value:
                raise ValueError("That format is unavailable in this frozen version")
            return value, "application/pdf" if format == "pdf" else "text/html; charset=utf-8", "resume." + format
        if kind == "letter":
            record, _ = letter_snapshot(self._letter_bytes(identifier))
            if format=="pdf" and "pdf_base64" in record:
                return decoded(record["pdf_base64"],2*1024*1024), "application/pdf", "cover-letter.pdf"
            if format not in ("txt", "pdf"):
                raise ValueError("Choose letter PDF or TXT")
            if format=="pdf":raise ValueError("This older letter has no frozen PDF; download TXT or create a new PDF letter")
            return record["text"].encode(), "text/plain; charset=utf-8", "cover-letter.txt"
        if kind == "packet":
            return self._artifact("packets", identifier).read_bytes(), "application/zip", "application-documents.zip"
        raise ValueError("Unknown download type")


def seed_web_demo(path):
    store = JobStore(path)
    job = seed_practice(store)
    profile = store.active_profile()
    data = dict(profile["profile"], first_name="Synthetic", last_name="Candidate", phone="+0 000 000 0000", website="https://example.invalid/portfolio", linkedin="https://example.invalid/profile")
    store.save_profile(json.dumps(data).encode())
    original = store.load(job)["snapshot"]
    analyst = store.save(original, "Synthetic Analytics Engineer", "Northstar · synthetic", "https://example.invalid/analytics")
    ai = store.save(original, "Synthetic Applied AI Engineer", "Linear Labs · synthetic", "https://example.invalid/ai")
    store.record_application(job, "interview", "Synthetic practice interview. No employer contacted.", date.today().isoformat())
    store.record_application(analyst, "applied", "Synthetic practice application. Nothing submitted.", "")
    profile = store.active_profile()
    store.create_resume(profile["id"], ["project-python", "sql-practice"], "Synthetic data engineering resume", job, confirmed=True)
