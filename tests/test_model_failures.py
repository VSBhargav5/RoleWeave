import base64
import json
from pathlib import Path
import ssl
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

import model_providers as providers
from resume_import import extract_text
from web_service import WebService, seed_web_demo


class ModelFailureTests(unittest.TestCase):
    def test_retry_after_is_sanitized_and_second_send_is_held_locally(self):
        connection,response=self.connection(429)
        response.getheader.side_effect=lambda name,default='': '90' if name=='Retry-After' else 'application/json'
        with patch('model_providers.http.client.HTTPSConnection',return_value=connection):
            with self.assertRaises(providers.ModelError) as caught:
                providers.request_model(self.config,self.payload,'SYNTHETIC_KEY',threading.Event())
        self.assertEqual(providers.failure_info(caught.exception)['retry_after'],90)
        with patch('model_providers.request_model',side_effect=caught.exception) as send:
            self.service.tailoring.send({'id':self.preview['id'],'sha256':self.preview['sha256'],'key':'SYNTHETIC_KEY','confirmed':True})
            self.service.tailoring.entries[self.preview['id']]['thread'].join(2)
            next_preview=self.service.tailoring.preview(self.args|{'instruction':'Use source wording.'})
            with self.assertRaises(providers.ModelError):
                self.service.tailoring.send({'id':next_preview['id'],'sha256':next_preview['sha256'],'key':'SYNTHETIC_KEY','confirmed':True})
            self.assertEqual(send.call_count,1)

    def test_free_request_reasoning_and_complete_fenced_json(self):
        from test_ai_tailoring import proposed
        from test_model_providers import wrapped
        self.assertEqual(json.loads(self.payload)['reasoning'],{'effort':'minimal'})
        self.assertEqual(json.loads(self.payload)['plugins'],[{'id':'response-healing'}])
        body=json.loads(wrapped('openrouter'))
        body['choices'][0]['message']['content']='```json\n'+json.dumps(proposed())+'\n```'
        self.assertEqual(providers.structured_response(json.dumps(body).encode(),self.config),proposed())
        body['choices'][0]['message']['content']='```json\n{"broken":\n```'
        with self.assertRaises(providers.ModelError) as caught:
            providers.structured_response(json.dumps(body).encode(),self.config)
        self.assertEqual(providers.failure_info(caught.exception)['error_code'],'RW-AI-JSON')
        body['choices'][0]['finish_reason']='length'
        with self.assertRaises(providers.ModelError) as caught:
            providers.structured_response(json.dumps(body).encode(),self.config)
        self.assertEqual(providers.failure_info(caught.exception)['error_code'],'RW-AI-OUTPUT-LIMIT')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'jobs.db'
        seed_web_demo(self.path)
        self.service = WebService(self.path)
        self.addCleanup(self.service.tailoring.shutdown)
        self.addCleanup(self.service.assessment.shutdown)
        profile = self.service.profile()
        self.args = {'profile_id': profile['id'], 'profile_sha256': profile['snapshot_sha256'],
                     'job_id': self.service.store.list_jobs()[0]['id'], 'fact_ids': ['project-python']}
        self.preview = self.service.tailoring.preview(self.args | {'instruction': 'Use only the supplied facts.'})
        self.payload = self.preview['payload'].encode()
        self.config = {'kind': 'openrouter', 'model': 'openrouter/free', 'port': 0}

    def connection(self, status=200, payload=b'{}'):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = status
        response.length = 0
        response.getheader.return_value = 'application/json'
        response.read1.side_effect = [payload, b'']
        return connection, response

    def test_http_errors_keep_status_and_category_without_reading_or_exposing_body(self):
        for status, code in ((401, 'RW-AI-AUTH'), (402, 'RW-AI-ACCOUNT'), (403, 'RW-AI-PERMISSION'),
                             (404, 'RW-AI-UNAVAILABLE'), (429, 'RW-AI-RATE'), (400, 'RW-AI-REQUEST'),
                             (503, 'RW-AI-UNAVAILABLE'), (504, 'RW-AI-TIMEOUT')):
            connection, response = self.connection(status, b'SECRET_KEY_AND_PRIVATE_RESUME')
            with self.subTest(status=status), patch('model_providers.http.client.HTTPSConnection', return_value=connection):
                with self.assertRaises(providers.ModelError) as caught:
                    providers.request_model(self.config, self.payload, 'SYNTHETIC_KEY', threading.Event())
                safe = providers.failure_info(caught.exception)
                self.assertEqual(safe['error_code'], code)
                self.assertEqual(safe['http_status'], status)
                self.assertIn('HTTP ' + str(status), safe['error'])
                self.assertNotIn('SECRET', json.dumps(safe))
                response.read1.assert_not_called()
                self.assertEqual(connection.request.call_count, 1)
                connection.close.assert_called_once()

    def test_generation_uses_remaining_budget_instead_of_five_second_socket_timeout(self):
        connection, _ = self.connection()
        with patch('model_providers.time.monotonic', return_value=10), patch('model_providers.http.client.HTTPSConnection', return_value=connection) as create:
            self.assertEqual(providers.request_model(self.config, self.payload, 'SYNTHETIC_KEY', threading.Event()), b'{}')
        self.assertEqual(create.call_args.kwargs['timeout'], 5)
        connection.connect.assert_called_once()
        self.assertTrue(connection.sock.settimeout.call_args_list)
        for call in connection.sock.settimeout.call_args_list:
            self.assertGreater(call.args[0], 5)
            self.assertLessEqual(call.args[0], 60)

    def test_late_body_is_not_accepted_after_deadline(self):
        connection, response = self.connection()
        current = [0]
        def late(_size):
            current[0] = 61
            return b'{}'
        response.read1.side_effect = late
        with patch('model_providers.time.monotonic', side_effect=lambda: current[0]), patch('model_providers.http.client.HTTPSConnection', return_value=connection):
            with self.assertRaises(providers.ModelError) as caught:
                providers.request_model(self.config, self.payload, 'SYNTHETIC_KEY', threading.Event())
        self.assertEqual(providers.failure_info(caught.exception)['error_code'], 'RW-AI-TIMEOUT')
        self.assertEqual(response.read1.call_count, 1)

    def test_timeout_network_and_tls_exceptions_are_sanitized(self):
        for error, code in ((TimeoutError('SECRET_TOKEN'), 'RW-AI-TIMEOUT'),
                            (OSError('SECRET_TOKEN'), 'RW-AI-NETWORK'),
                            (ssl.SSLError('SECRET_TOKEN'), 'RW-AI-TLS')):
            connection, _ = self.connection()
            connection.getresponse.side_effect = error
            with self.subTest(code=code), patch('model_providers.http.client.HTTPSConnection', return_value=connection):
                with self.assertRaises(providers.ModelError) as caught:
                    providers.request_model(self.config, self.payload, 'SYNTHETIC_KEY', threading.Event())
            safe = providers.failure_info(caught.exception)
            self.assertEqual(safe['error_code'], code)
            self.assertNotIn('SECRET', json.dumps(safe))

    def test_http_200_error_envelopes_and_partial_output_are_not_success(self):
        envelopes = [({'error': {'code': 429, 'message': 'SECRET_RESUME_TOKEN'}}, 'RW-AI-RATE'),
                     ({'choices': [{'error': {'code': 401, 'message': 'SECRET_RESUME_TOKEN'}, 'finish_reason': 'error'}]}, 'RW-AI-AUTH'),
                     ({'choices': [{'finish_reason': 'length', 'message': {'role': 'assistant', 'content': '{}'}}]}, 'RW-AI-OUTPUT-LIMIT'),
                     ({'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'refusal': 'SECRET_RESUME_TOKEN'}}]}, 'RW-AI-REFUSED')]
        for body, code in envelopes:
            with self.subTest(code=code), self.assertRaises(providers.ModelError) as caught:
                providers.structured_response(json.dumps(body).encode(), self.config)
            safe = providers.failure_info(caught.exception)
            self.assertEqual(safe['error_code'], code)
            self.assertNotIn('SECRET', json.dumps(safe))

    def test_incompatible_json_and_source_references_have_safe_output_error(self):
        from test_model_providers import wrapped
        from test_ai_tailoring import proposed
        facts = self.service.profile()['profile']['facts'][:1]
        wrong = proposed();wrong['bullets'][0]['fact_id'] = 'SECRET_UNKNOWN_SOURCE'
        for raw in (b'PRIVATE_INVALID_JSON', wrapped('openrouter', wrong)):
            with self.assertRaises(providers.ModelError) as caught:
                providers.parse_provider_response(raw, facts, self.config)
            safe = providers.failure_info(caught.exception)
            self.assertEqual(safe['error_code'], 'RW-AI-OUTPUT')
            self.assertNotIn('PRIVATE', json.dumps(safe))
            self.assertNotIn('SECRET', json.dumps(safe))

    def test_tailoring_worker_status_exposes_safe_cause_without_key_or_payload(self):
        with patch('model_providers.request_model', side_effect=providers.http_error(429)) as send:
            self.service.tailoring.send({'id': self.preview['id'], 'sha256': self.preview['sha256'], 'key': 'SYNTHETIC_PRIVATE_KEY', 'confirmed': True})
            self.service.tailoring.entries[self.preview['id']]['thread'].join(2)
        state = self.service.tailoring.status({'id': self.preview['id']})
        self.assertEqual(state['status'], 'failed')
        self.assertEqual(state['error_code'], 'RW-AI-RATE')
        self.assertEqual(state['http_status'], 429)
        self.assertNotIn('PRIVATE', json.dumps(state))
        self.assertEqual(send.call_count, 1)
        self.assertNotIn('draft', state)

    def test_assessment_and_resume_organization_preserve_safe_provider_error(self):
        p = self.service.assessment.preview(self.args)
        with patch('model_providers.request_model', side_effect=providers.http_error(401)):
            self.service.assessment.send({'id': p['id'], 'sha256': p['sha256'], 'key': 'SYNTHETIC_KEY', 'confirmed': True})
            self.service.assessment.entries[p['id']]['thread'].join(2)
        self.assertEqual(self.service.assessment.status({'id': p['id']})['error_code'], 'RW-AI-AUTH')
        with patch('web_service.extract_in_worker', side_effect=extract_text):
            resume = self.service.preview_resume_import({'name': 'resume.txt', 'base64': base64.b64encode(b'Skills\nPython, SQL').decode()})
        p = self.service.resume_organization.preview({'id': resume['id']})
        with patch('model_providers.request_model', side_effect=providers.http_error(503)):
            self.service.resume_organization.send({'id': p['id'], 'sha256': p['sha256'], 'key': 'SYNTHETIC_KEY', 'confirmed': True})
            self.service.resume_organization.worker.join(2)
        state = self.service.resume_organization.status({'id': p['id']})
        self.assertEqual(state['error_code'], 'RW-AI-UNAVAILABLE')
        self.assertEqual(state['http_status'], 503)
        self.assertEqual(self.service.imports[p['id']]['result']['structure']['method'], 'local')

    def test_unknown_internal_errors_and_mutated_messages_never_echo_exception_text(self):
        exc = providers.ModelError('authentication', 401)
        exc.args = ('SECRET_CREDENTIAL_OR_RESPONSE',)
        self.assertNotIn('SECRET', json.dumps(providers.failure_info(exc)))
        self.assertNotIn('SECRET', json.dumps(providers.failure_info(RuntimeError('SECRET_CREDENTIAL_OR_RESPONSE'))))
