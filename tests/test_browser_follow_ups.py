import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from calendar_session import CalendarSession
from test_mail_observation import synthetic_mail
from web_server import LocalServer
from web_service import WebService, seed_web_demo


class BrowserFollowUpTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'jobs.db'
        seed_web_demo(self.path)
        self.service = WebService(self.path, demo=True)
        self.job = self.service.store.list_jobs()[0]['id']
        self.service.store.record_application(self.job, 'interview', 'Private existing note', '2026-12-03')
        self.calendar = CalendarSession(self.service.store)
        self.addCleanup(self.cleanup_sessions)

    def cleanup_sessions(self):
        for identifier in list(self.calendar.entries):
            self.calendar.close({'id': identifier})
        for identifier in list(self.service.mail_previews):
            self.service.close_correspondence({'id': identifier})

    def mail(self):
        preview = self.service.preview_correspondence(self.job, synthetic_mail())
        return preview, {'id': preview['id'], 'job_id': self.job, 'sha256': preview['source_sha256'],
                         'expected_revision': preview['expected_revision'], 'quote': 'Please suggest a time',
                         'note': 'My observation', 'confirmed': True}

    def open_calendar(self):
        result = self.calendar.open({'job_id': self.job, 'include_details': False})
        self.addCleanup(self.calendar.close, {'id': result['id']})
        return result['id']

    def connected(self):
        identifier = self.open_calendar()
        self.calendar.entries[identifier]['credentials'] = SimpleNamespace(valid=True, token='NEVER_RETURN_THIS_TOKEN')
        self.calendar.entries[identifier]['status'] = 'connected'
        return identifier

    def run_action(self, identifier, action, **extra):
        result = self.calendar.action({'id': identifier, 'action': action, 'confirmed': True, **extra})
        self.assertEqual(result['status'], 'running')
        self.calendar.worker.join(2)
        self.assertFalse(self.calendar.worker.is_alive())
        return self.calendar.status({'id': identifier})

    def prepared(self):
        identifier = self.connected()
        with patch('calendar_session.read_remote', return_value=None):
            result = self.run_action(identifier, 'prepare', calendar_id='synthetic@group.calendar.google.com')
        self.assertEqual(result['status'], 'prepared')
        return identifier, result['plan']

    def test_mail_exact_excerpt_consumed_and_recoverable_without_original(self):
        before = self.service.store.application_history(self.job)
        preview, data = self.mail()
        self.assertNotIn('HTML', preview['body'])
        self.assertEqual(preview['ignored_attachment_names'], ['do-not-open.exe'])
        self.service.save_correspondence(data)
        self.assertNotIn(preview['id'], self.service.mail_previews)
        history = self.service.store.application_history(self.job)
        self.assertEqual(len(history), len(before) + 1)
        self.assertEqual(history[-1]['stage'], before[-1]['stage'])
        self.assertEqual(history[-1]['follow_up'], before[-1]['follow_up'])
        self.assertIn('Please suggest a time', history[-1]['note'])
        self.assertNotIn('untrusted attachment', history[-1]['note'])
        self.assertNotIn('discuss the data role', history[-1]['note'])
        self.assertFalse(self.service.artifacts.exists())
        with self.assertRaises(ValueError):
            self.service.save_correspondence(data)
        backup = self.path.parent / 'backup.json'
        self.service.store.backup(backup)
        self.assertIn('Please suggest a time', backup.read_text())

    def test_mail_confirmation_quote_binding_and_revision_fail_closed(self):
        preview, data = self.mail()
        before = self.service.store.application_history(self.job)
        for change in ({'confirmed': False}, {'quote': 'Invented job offer'}, {'sha256': '0' * 64},
                       {'job_id': 'another-job'}, {'expected_revision': True}, {'extra': 'refused'}):
            with self.assertRaises(ValueError):
                self.service.save_correspondence(data | change)
        self.assertEqual(self.service.store.application_history(self.job), before)
        self.service.store.record_application(self.job, 'closed', 'New observation', '')
        with self.assertRaisesRegex(ValueError, 'history changed'):
            self.service.save_correspondence(data)
        self.assertEqual(len(self.service.store.application_history(self.job)), len(before) + 1)

    def test_mail_preview_expiry_close_and_capacity(self):
        preview, data = self.mail()
        self.service.mail_previews[preview['id']]['at'] -= 601
        with self.assertRaisesRegex(ValueError, 'expired'):
            self.service.save_correspondence(data)
        for _ in range(3):
            self.mail()
        with self.assertRaisesRegex(ValueError, 'three'):
            self.mail()
        identifier = next(iter(self.service.mail_previews))
        self.service.close_correspondence({'id': identifier})
        self.mail()

    def test_calendar_local_preview_does_not_connect_or_expose_notes(self):
        with patch('calendar_session.connect_session') as connect:
            identifier = self.open_calendar()
        connect.assert_not_called()
        serialized = json.dumps(self.calendar.status({'id': identifier}))
        self.assertNotIn('Private existing note', serialized)
        self.assertFalse(self.calendar.status({'id': identifier})['connected'])
        with self.assertRaises(ValueError):
            self.calendar.open({'job_id': self.job, 'include_details': 'yes'})

    def test_calendar_file_is_private_reminder_without_notes_or_remote_requests(self):
        with patch('calendar_session.connect_session') as connect:
            payload, content_type, filename = self.service.download('calendar', self.job)
        self.assertEqual(filename, 'follow-up.ics')
        self.assertEqual(content_type, 'text/calendar; charset=utf-8')
        self.assertIn(b'DTSTART;VALUE=DATE:20261203', payload)
        self.assertIn(b'CLASS:PRIVATE', payload)
        self.assertNotIn(b'Private existing note', payload)
        connect.assert_not_called()
        self.service.store.record_application(self.job, 'closed', 'Closed', '')
        with self.assertRaises(ValueError):
            self.service.download('calendar', self.job)

    def test_calendar_creation_has_separate_confirmation_and_no_local_history_change(self):
        identifier = self.connected()
        before = self.service.store.application_history(self.job)
        with patch('calendar_session.create_calendar', return_value='new@group.calendar.google.com') as create:
            with self.assertRaises(ValueError):
                self.calendar.action({'id': identifier, 'action': 'create', 'confirmed': False})
            create.assert_not_called()
            state = self.run_action(identifier, 'create')
        self.assertEqual(state['calendar_id'], 'new@group.calendar.google.com')
        self.assertEqual(create.call_count, 1)
        self.assertEqual(self.service.store.application_history(self.job), before)

    def test_calendar_consent_and_demo_refuse_any_remote_work(self):
        identifier = self.open_calendar()
        with patch('calendar_session.connect_session') as connect:
            for action in ({'action': 'connect', 'client_id': 'id', 'client_secret': 'secret', 'confirmed': False},
                           {'action': 'send', 'confirmed': True}, {'action': 'create', 'confirmed': True}):
                with self.assertRaises(ValueError):
                    self.calendar.action({'id': identifier, **action})
            connect.assert_not_called()
            self.calendar.demo = True
            with self.assertRaisesRegex(ValueError, 'Offline practice'):
                self.calendar.action({'id': identifier, 'action': 'connect', 'client_id': 'id', 'client_secret': 'secret', 'confirmed': True})

    def test_calendar_connect_keeps_secrets_out_of_results_and_clears_on_close(self):
        identifier = self.open_calendar()
        with patch('calendar_session.connect_session', return_value=SimpleNamespace(valid=True, token='TOKEN_SECRET')) as connect:
            result = self.run_action(identifier, 'connect', client_id='CLIENT_ID', client_secret='CLIENT_SECRET')
        self.assertTrue(result['connected'])
        self.assertEqual(connect.call_args.kwargs['confirmed'], True)
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertNotIn('client_secret', self.calendar.entries[identifier])
        entry = self.calendar.entries[identifier]
        self.calendar.close({'id': identifier})
        self.assertNotIn('credentials', entry)
        self.assertTrue(entry['cancel'].is_set())

    def test_calendar_one_shot_server_plan_prevents_duplicate_writes(self):
        identifier, plan = self.prepared()
        with patch('google_calendar_sync.api_request', return_value={'id': plan['event']['id']}) as send:
            result = self.run_action(identifier, 'send')
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['result']['operation'], 'create')
            with self.assertRaises(ValueError):
                self.calendar.action({'id': identifier, 'action': 'send', 'confirmed': True})
            self.assertEqual(send.call_count, 1)
        self.assertNotIn('plan', self.calendar.entries[identifier])

    def test_calendar_stale_history_and_forged_plan_cannot_write(self):
        identifier, plan = self.prepared()
        with self.assertRaises(ValueError):
            self.calendar.action({'id': identifier, 'action': 'send', 'confirmed': True, 'plan': plan})
        self.service.store.record_application(self.job, 'interview', 'Changed', '2026-12-04')
        with patch('google_calendar_sync.api_request') as send:
            state = self.run_action(identifier, 'send')
            self.assertEqual(state['status'], 'failed')
            send.assert_not_called()
        self.assertNotIn('plan', state)

    def test_calendar_remote_conflict_consumes_plan_without_retry_or_secret_error(self):
        identifier, plan = self.prepared()
        with patch('google_calendar_sync.api_request', side_effect=ValueError('SECRET_REMOTE_ERROR')) as send:
            state = self.run_action(identifier, 'send')
            self.assertEqual(state['status'], 'failed')
            self.assertNotIn('SECRET', state['error'])
            self.assertEqual(send.call_count, 1)
        with self.assertRaises(ValueError):
            self.calendar.action({'id': identifier, 'action': 'send', 'confirmed': True})

    def test_calendar_unchanged_and_owned_etag_update(self):
        identifier = self.connected()
        local = self.calendar.entries[identifier]['event']
        existing = copy.deepcopy(local) | {'etag': '"version1"'}
        with patch('calendar_session.read_remote', return_value=existing):
            result = self.run_action(identifier, 'prepare', calendar_id='synthetic@group.calendar.google.com')
        self.assertEqual(result['plan']['operation'], 'unchanged')
        with patch('google_calendar_sync.api_request') as send:
            self.run_action(identifier, 'send')
            send.assert_not_called()
        existing['start'] = {'date': '2026-12-02'}
        with patch('calendar_session.read_remote', return_value=existing):
            result = self.run_action(identifier, 'prepare', calendar_id='synthetic@group.calendar.google.com')
        self.assertEqual(result['plan']['operation'], 'update')
        with patch('google_calendar_sync.api_request', return_value={'id': local['id']}) as send:
            self.run_action(identifier, 'send')
        self.assertEqual(send.call_args.args[1], 'PATCH')
        self.assertEqual(send.call_args.kwargs['etag'], '"version1"')

    def test_calendar_cancel_during_consent_discards_late_credentials_and_bounds_workers(self):
        identifier = self.open_calendar()
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def slow(*args, **kwargs):
            started.set()
            release.wait(2)
            return SimpleNamespace(valid=True, token='LATE_TOKEN')
        with patch('calendar_session.connect_session', side_effect=slow):
            self.calendar.action({'id': identifier, 'action': 'connect', 'client_id': 'id', 'client_secret': 'secret', 'confirmed': True})
            self.assertTrue(started.wait(1))
            entry = self.calendar.entries[identifier]
            self.calendar.close({'id': identifier})
            other = self.open_calendar()
            with self.assertRaises(ValueError):
                self.calendar.action({'id': other, 'action': 'connect', 'client_id': 'id', 'client_secret': 'secret', 'confirmed': True})
            release.set()
            self.calendar.worker.join(2)
        self.assertNotIn('credentials', entry)

    def test_calendar_expiry_clears_credentials_and_plan(self):
        identifier, _ = self.prepared()
        entry = self.calendar.entries[identifier]
        entry['expires'] -= 601
        with self.assertRaisesRegex(ValueError, 'expired'):
            self.calendar.status({'id': identifier})
        self.assertNotIn('credentials', entry)
        self.assertNotIn('plan', entry)
        identifier = self.connected()
        entry = self.calendar.entries[identifier]
        entry['expires'] -= 601
        self.open_calendar()  # Opening another dialog must also clear expired credentials.
        self.assertTrue(entry['cancel'].is_set())
        self.assertNotIn('credentials', entry)

    def test_browser_routes_require_session_origin_bounded_binary_and_strict_fields(self):
        server = LocalServer(('127.0.0.1', 0), self.service)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def request(path, body, content='application/json', **headers):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            self.addCleanup(connection.close)
            connection.request('POST', path, body, {'Content-Type': content, **headers})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        path = '/api/correspondence/preview?job_id=' + self.job
        raw = synthetic_mail()
        self.assertEqual(request(path, raw, 'application/octet-stream')[0], 401)
        headers = {'X-RoleWeave-Token': server.token}
        self.assertEqual(request(path, raw, 'application/octet-stream', Origin='https://evil.invalid', **headers)[0], 403)
        # Reject the declared size before streaming a body; sending a full refused body
        # can reset the socket on Windows before its HTTP error reaches the client.
        oversized = headers | {'Content-Length': str(2 * 1024 * 1024 + 1)}
        self.assertEqual(request(path, b'', 'application/octet-stream', **oversized)[0], 400)
        status, preview = request(path, raw, 'application/octet-stream', **headers)
        self.assertEqual(status, 200)
        self.assertEqual(request('/api/correspondence/close', json.dumps({'id': preview['id']}), **headers)[0], 200)
        status, local = request('/api/calendar/open', json.dumps({'job_id': self.job, 'include_details': False}), **headers)
        self.assertEqual(status, 200)
        self.addCleanup(self.service.calendar.close, {'id': local['id']})
        self.assertEqual(request('/api/calendar/status', json.dumps({'id': local['id']}), **headers)[0], 200)
        self.assertEqual(request('/api/calendar/action', json.dumps({'id': local['id'], 'action': 'create', 'confirmed': True}), **headers)[0], 400)
        self.assertEqual(request('/api/calendar/open', '{"job_id":1,"job_id":2}', **headers)[0], 400)
