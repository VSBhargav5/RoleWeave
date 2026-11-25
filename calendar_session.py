"""Bounded browser Calendar sessions with one-shot, server-held change plans."""
import threading
import time
from uuid import uuid4

from google_calendar_auth import connect_session, create_calendar
from google_calendar_sync import SCOPE, desired_event, prepare_sync, read_remote, apply_sync


def fields(data, names):
    if not isinstance(data, dict) or set(data) != set(names):
        raise ValueError("Unsupported or missing Calendar fields")


class CalendarSession:
    def __init__(self, store, demo=False):
        self.store, self.demo = store, demo
        self.entries = {}
        self.lock = threading.RLock()
        self.worker = None

    def open(self, data):
        fields(data, ('job_id', 'include_details'))
        event = desired_event(self.store.load(data['job_id']), self.store.application_history(data['job_id']),
                              include_details=data['include_details'])
        with self.lock:
            for identifier, entry in list(self.entries.items()):
                if entry['expires'] <= time.monotonic():
                    self._expire(identifier)
            if len(self.entries) >= 4:
                raise ValueError("Close an existing Calendar session first")
            identifier = uuid4().hex
            entry = {'job_id': data['job_id'], 'include_details': data['include_details'], 'event': event,
                     'status': 'disconnected', 'cancel': threading.Event(), 'expires': time.monotonic() + 600}
            self.entries[identifier] = entry
            timer = threading.Timer(600, self._expire, args=(identifier,))
            timer.daemon = True
            entry['timer'] = timer
            timer.start()
            return {'id': identifier, 'event': event, 'scope': SCOPE, 'offline_demo': self.demo}

    def _expire(self, identifier):
        with self.lock:
            entry = self.entries.pop(identifier, None)
            if entry:
                entry['timer'].cancel()
                entry['cancel'].set()
                entry.pop('credentials', None)
                entry.pop('plan', None)

    def _entry(self, identifier):
        if not isinstance(identifier, str) or identifier not in self.entries:
            raise ValueError("Calendar session unavailable; open a fresh preview")
        entry = self.entries[identifier]
        if entry['expires'] <= time.monotonic():
            self._expire(identifier)
            raise ValueError("Calendar session expired; open a fresh preview")
        return entry

    def status(self, data):
        fields(data, ('id',))
        with self.lock:
            entry = self._entry(data['id'])
            credentials = entry.get('credentials')
            result = {'status': entry['status'], 'connected': bool(credentials and credentials.valid)}
            for key in ('calendar_id', 'plan', 'result', 'error'):
                if key in entry:
                    result[key] = entry[key]
            return result

    def close(self, data):
        fields(data, ('id',))
        if not isinstance(data['id'], str):
            raise ValueError("Invalid Calendar session")
        self._expire(data['id'])
        return {'status': 'disconnected'}

    def action(self, data):
        action = data.get('action') if isinstance(data, dict) else None
        extra = {'connect': ('client_id', 'client_secret'), 'create': (), 'prepare': ('calendar_id',), 'send': ()}
        if action not in extra:
            raise ValueError("Unsupported Calendar action")
        fields(data, ('id', 'action', 'confirmed') + extra[action])
        if data['confirmed'] is not True:
            raise ValueError("Review and explicitly confirm this one Calendar action")
        if self.demo:
            raise ValueError("Offline practice supports local previews only; no Google connection is made")
        with self.lock:
            entry = self._entry(data['id'])
            if self.worker and self.worker.is_alive():
                raise ValueError("Wait for the current Calendar action or disconnect")
            if action != 'connect':
                credentials = entry.get('credentials')
                if credentials is None or not credentials.valid:
                    raise ValueError("Connect a fresh Calendar session first")
            if action == 'send' and entry['status'] != 'prepared':
                raise ValueError("Read remote state and review a fresh Calendar plan first")
            if action == 'prepare':
                from google_calendar_sync import calendar_path
                calendar_path(data['calendar_id'])
            # Consume the plan before dispatch. Neither double clicks nor failure retry a write.
            plan = entry.pop('plan', None)
            if action == 'connect':
                entry.pop('credentials', None)
            entry.pop('error', None)
            entry.pop('result', None)
            entry['status'] = 'running'
            worker = threading.Thread(target=self._run, args=(entry, action, dict(data), plan), daemon=True)
            self.worker = worker
            worker.start()
        return {'status': 'running'}

    def _run(self, entry, action, data, plan):
        try:
            cancel = entry['cancel']
            if action == 'connect':
                result = connect_session(data['client_id'], data['client_secret'], confirmed=True, cancel=cancel)
                key, state = 'credentials', 'connected'
            elif action == 'create':
                result = create_calendar(entry['credentials'], confirmed=True, cancel=cancel)
                key, state = 'calendar_id', 'connected'
            elif action == 'prepare':
                item = self.store.load(entry['job_id'])
                history = self.store.application_history(entry['job_id'])
                event = desired_event(item, history, include_details=entry['include_details'])
                if event != entry['event']:
                    raise ValueError("Local follow-up changed")
                existing = read_remote(entry['credentials'], data['calendar_id'], event['id'], cancel=cancel)
                result = prepare_sync(item, history, data['calendar_id'], existing, include_details=entry['include_details'])
                key, state = 'plan', 'prepared'
            else:
                result = apply_sync(self.store, plan, entry['credentials'], confirmed=True, cancel=cancel)
                key, state = 'result', 'completed'
            with self.lock:
                if not cancel.is_set():
                    entry[key], entry['status'] = result, state
        except Exception:
            with self.lock:
                if not entry['cancel'].is_set():
                    entry['status'] = 'failed'
                    entry['error'] = ("Calendar action failed or conflicted. Local state may have changed. "
                                      "Inspect Google before retrying a write or calendar creation; open a fresh preview. "
                                      "No automatic retry was made.")
        finally:
            data.clear()  # Client configuration is never retained in session state or diagnostics.
