"""Opt-in local daily recovery snapshots; no operating-system scheduler or network."""
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading
from uuid import uuid4

from career_profile import unique_json
from safe_export import publish_bytes
from workspace_bundle import export_bundle, inspect_bundle, no_link, storage_path, LIMIT

FORMAT = 'roleweave-automatic-backups-v1'
KEY = 'automatic_backups'
KEEP = 7
NAME = re.compile(r'(\d{4}-\d{2}-\d{2})_(\d{8}T\d{12}Z)_([a-f0-9]{32})_([a-f0-9]{64})\.zip')
DEFAULT = dict(format=FORMAT, enabled=False, revision=0, last_success=None,
               last_attempt=None, last_cycle=None, last_error='')


def cycle(now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError('Backup scheduling requires a timezone-aware local clock')
    return (now - timedelta(hours=2)).date().isoformat()


def read_state(db):
    row = db.execute('SELECT value FROM app_settings WHERE key=?', (KEY,)).fetchone()
    if row is None:
        return DEFAULT.copy()
    try:
        if len(row[0]) > 4096:
            raise ValueError()
        state = json.loads(row[0], object_pairs_hook=unique_json)
        if not isinstance(state, dict) or set(state) != set(DEFAULT) or state['format'] != FORMAT:
            raise ValueError()
        if type(state['enabled']) is not bool or type(state['revision']) is not int or not 0 <= state['revision'] <= 1000000:
            raise ValueError()
        for key in ('last_success', 'last_attempt'):
            value = state[key]
            if value is not None and (not isinstance(value, str) or len(value) > 50 or datetime.fromisoformat(value).utcoffset() is None):
                raise ValueError()
        if state['last_cycle'] is not None and date.fromisoformat(state['last_cycle']).isoformat() != state['last_cycle']:
            raise ValueError()
        if state['last_error'] not in ('', 'capture_failed', 'storage_failed', 'retention_failed'):
            raise ValueError()
        return state
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ValueError('Automatic-backup settings are invalid; manual recovery exports remain available') from None


def write_state(db, state):
    db.execute('INSERT OR REPLACE INTO app_settings(key,value) VALUES (?,?)',
               (KEY, json.dumps(state, sort_keys=True)))


class AutomaticBackups:
    def __init__(self, store, artifacts):
        self.store, self.artifacts = store, artifacts
        self.directory = storage_path(store.path.parent / 'automatic-backups')
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.running = False
        self.thread = None

    def state(self):
        with closing(sqlite3.connect(self.store.path)) as db:
            return read_state(db)

    def files(self):
        with self.lock:
            no_link(self.directory)
            if not self.directory.exists():
                return []
            result = []
            for index, path in enumerate(self.directory.iterdir()):
                if index >= KEEP + 1:
                    raise ValueError('Automatic-backup folder has too many entries; inspect it before retrying')
                no_link(path)
                match = NAME.fullmatch(path.name)
                if not match or not path.is_file() or not 0 < path.stat().st_size <= LIMIT:
                    raise ValueError('Unexpected or incomplete automatic-backup file; nothing was deleted')
                date.fromisoformat(match[1])
                created = datetime.strptime(match[2], '%Y%m%dT%H%M%S%fZ').replace(tzinfo=timezone.utc).isoformat()
                result.append(dict(id=path.name, cycle=match[1], created_at=created,
                                   bytes=path.stat().st_size, sha256=match[4]))
            return sorted(result, key=lambda row: (row['cycle'], row['created_at'], row['id']), reverse=True)

    def status(self):
        try:
            state = self.state()
        except (ValueError, OSError, sqlite3.Error):
            return dict(available=False, enabled=False, running=self.running, items=[], keep=KEEP,
                        error='Automatic-backup settings need attention. Manual recovery exports remain available.')
        result = state | dict(available=True, running=self.running, keep=KEEP,
                              directory=str(self.directory), local_time=datetime.now().astimezone().isoformat())
        try:
            return result | dict(items=self.files(), storage_error=False)
        except (ValueError, OSError):
            # A broken folder must not prevent the operator from disabling the schedule.
            return result | dict(items=[], storage_error=True,
                                 error='Backup storage needs attention. Disable the schedule or inspect the folder; no cleanup was attempted here.')

    def configure(self, data):
        if not isinstance(data, dict) or set(data) != {'enabled', 'expected_revision', 'confirmed'} or type(data['enabled']) is not bool or type(data['expected_revision']) is not int or data['confirmed'] is not True:
            raise ValueError('Review the local backup schedule and retention policy before saving')
        with self.lock, closing(sqlite3.connect(self.store.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            state = read_state(db)
            if state['revision'] != data['expected_revision']:
                raise ValueError('Backup preferences changed; refresh and review again')
            if state['revision'] >= 1000000:
                raise ValueError('Backup preference revision limit reached')
            state.update(enabled=data['enabled'], revision=state['revision'] + 1)
            write_state(db, state)
        self.wake.set()
        return self.status()

    def payload(self, identifier):
        if not isinstance(identifier, str) or not NAME.fullmatch(identifier):
            raise ValueError('Choose a completed automatic backup')
        no_link(self.directory)
        path = self.directory / identifier
        no_link(path)
        with path.open('rb') as handle:
            payload = handle.read(LIMIT + 1)
        if len(payload) > LIMIT or hashlib.sha256(payload).hexdigest() != NAME.fullmatch(identifier)[4]:
            raise ValueError('Automatic-backup fingerprint differs; no restore or deletion performed')
        inspect_bundle(payload)
        return payload

    def request(self, data):
        if not isinstance(data, dict) or set(data) != {'confirmed'} or data['confirmed'] is not True:
            raise ValueError('Confirm creating one local recovery snapshot')
        with self.lock:
            if self.running:
                raise ValueError('An automatic-backup snapshot is already running')
            if not self.state()['enabled']:
                raise ValueError('Enable and review the backup policy first')
            self.running = True
            thread = threading.Thread(target=self.perform, kwargs={'reserved': True}, daemon=True)
            thread.start()
        return self.status()

    def perform(self, now=None, *, scheduled=False, reserved=False):
        failure = 'capture_failed'
        owned = False
        try:
            now = now or datetime.now().astimezone()
            period = cycle(now)
            with self.lock:
                if self.running and not reserved:
                    return False
                state = self.state()
                if self.stop.is_set() or not state['enabled']:
                    return False
                if scheduled:
                    if state['last_cycle'] and state['last_cycle'] >= period:
                        return False
                    if state['last_attempt'] and (now - datetime.fromisoformat(state['last_attempt'])).total_seconds() < 900:
                        return False
                self.running = owned = True
                with closing(sqlite3.connect(self.store.path)) as db, db:
                    db.execute('BEGIN IMMEDIATE')
                    state = read_state(db)
                    state.update(last_attempt=now.astimezone(timezone.utc).isoformat(), last_error='')
                    write_state(db, state)
            payload = export_bundle(self.store, self.artifacts)
            inspect_bundle(payload)
            failure = 'storage_failed'
            # Verify every old managed snapshot before publishing/pruning anything.
            old = self.files()
            for item in old:
                self.payload(item['id'])
            digest = hashlib.sha256(payload).hexdigest()
            stamp = now.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            name = period + '_' + stamp + '_' + uuid4().hex + '_' + digest + '.zip'
            with self.lock:
                if self.stop.is_set() or not self.state()['enabled']:
                    return False
                no_link(self.directory)
                self.directory.mkdir(parents=True, exist_ok=True)
                publish_bytes(self.directory / name, payload)
                self.payload(name)
                with closing(sqlite3.connect(self.store.path)) as db, db:
                    db.execute('BEGIN IMMEDIATE')
                    current = read_state(db)
                    current.update(last_success=now.astimezone(timezone.utc).isoformat(),
                                   last_cycle=max(current['last_cycle'] or period, period), last_error='')
                    write_state(db, current)
                failure = 'retention_failed'
                # Keep this successful snapshot even if the system clock moved backwards.
                for item in old[KEEP - 1:]:
                    self.payload(item['id'])
                    (self.directory / item['id']).unlink()
            return True
        except Exception:
            # Background failures disclose a bounded category, never source contents/paths.
            try:
                with closing(sqlite3.connect(self.store.path)) as db, db:
                    db.execute('BEGIN IMMEDIATE')
                    current = read_state(db)
                    current['last_error'] = failure
                    write_state(db, current)
            except (ValueError, OSError, sqlite3.Error):
                pass
            return False
        finally:
            if owned or reserved:
                with self.lock:
                    self.running = False

    def start(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                return
            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()

    def loop(self):
        while not self.stop.is_set():
            try:
                self.perform(scheduled=True)
            except (ValueError, OSError, sqlite3.Error):
                pass  # Corrupt policy/storage is disclosed in status; never print private contents.
            self.wake.wait(30)
            self.wake.clear()

    def shutdown(self):
        self.stop.set()
        self.wake.set()
