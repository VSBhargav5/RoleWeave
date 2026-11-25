import base64
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock

import model_providers as providers
from resume_import import extract_text
from resume_structure import suggest_structure, make_groups
from web_service import WebService


RESUME = b'''Synthetic Candidate
candidate@example.invalid | +91 98765 43210
Professional Summary
Data engineer building reliable pipelines.
Technical Skills
Python, SQL
Airflow, Git
Work Experience
Data Engineer | Example Co | 2023 - 2025
- Built data quality checks.
- Reduced manual reconciliation work.

Projects
Pipeline Monitor
- Built a Python dashboard.
Education
B.Tech Computer Science | Synthetic Institute
2020 - 2024
'''


class ResumeStructureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = WebService(Path(self.temp.name) / 'jobs.db')
        with patch('web_service.extract_in_worker', side_effect=extract_text):
            self.preview = self.service.preview_resume_import({'name': 'resume.txt', 'base64': base64.b64encode(RESUME).decode()})
        self.organizer = self.service.resume_organization

    def test_local_sections_combine_related_bullets_and_separate_contacts_summary(self):
        structure = self.preview['structure']
        groups = {g['section']: g for g in structure['groups']}
        self.assertEqual(set(groups), {'Skills', 'Experience', 'Projects', 'Education'})
        self.assertEqual(groups['Skills']['text'], 'Python, SQL\nAirflow, Git')
        self.assertIn('Data Engineer | Example Co', groups['Experience']['text'])
        self.assertIn('- Built data quality checks.', groups['Experience']['text'])
        self.assertIn('- Reduced manual reconciliation work.', groups['Experience']['text'])
        self.assertIn('2020 - 2024', groups['Education']['text'])
        fields = {f['field']: f['value'] for f in structure['profile_suggestions']}
        self.assertEqual(fields['name'], 'Synthetic Candidate')
        self.assertEqual(fields['email'], 'candidate@example.invalid')
        self.assertEqual(fields['summary'], 'Data engineer building reliable pipelines.')
        self.assertNotIn('candidate@example.invalid', json.dumps(structure['groups']))

    def test_inline_headings_and_unknown_content_are_not_lost(self):
        result = extract_text(b'Skills: Python, SQL\nUnusualHeading\nSomething to review\nPage 1 of 2', 'resume.txt')
        structure = suggest_structure(result)
        self.assertIn('Skills: Python, SQL', json.dumps(structure['groups']))
        self.assertIn('Something to review', json.dumps(structure['groups']))
        self.assertTrue(any(row['reason'].startswith('Possible page') for row in structure['omitted']))

    def test_reviewed_groups_keep_original_text_provenance_and_explicit_fields(self):
        group = next(g for g in self.preview['structure']['groups'] if g['section'] == 'Experience')
        email = next(f for f in self.preview['structure']['profile_suggestions'] if f['field'] == 'email')
        data = {'id': self.preview['id'], 'selected': [{'id': group['id'], 'section': 'Experience'}],
                'selected_fields': [email['id']], 'confirmed': True}
        with self.assertRaises(ValueError):
            self.service.commit_resume_import(data | {'confirmed': False})
        result = self.service.commit_resume_import(data)
        self.assertEqual(result['facts'][0]['claim'], group['text'])
        self.assertIn(', '.join(group['block_ids']), result['facts'][0]['source'])
        self.assertEqual(result['profile_fields'], {'email': 'candidate@example.invalid'})
        self.assertIsNone(self.service.profile())
        source = self.service.bootstrap()['resume_sources']['items'][0]
        self.assertEqual(self.service.download('resume-source', source['id'])[0], RESUME)
        for identifier in ('../resume.txt', 'x' * 64 + '.txt'):
            with self.assertRaises((ValueError, OSError)):
                self.service.download('resume-source', identifier)

    def test_overlapping_groups_forged_contacts_and_duplicate_field_choices_are_refused(self):
        group = next(g for g in self.preview['structure']['groups'] if len(g['block_ids']) > 1)
        args = {'id': self.preview['id'], 'selected': [{'id': group['id'], 'section': group['section']},
                {'id': group['block_ids'][0], 'section': group['section']}], 'confirmed': True}
        with self.assertRaises(ValueError):self.service.commit_resume_import(args)
        with self.assertRaises(ValueError):
            self.service.commit_resume_import({'id': self.preview['id'], 'selected': [], 'selected_fields': ['invented'], 'confirmed': True})
        self.assertFalse(self.service.artifacts.exists())

    def test_contact_only_review_does_not_invent_a_career_fact(self):
        name = next(f for f in self.preview['structure']['profile_suggestions'] if f['field'] == 'name')
        result = self.service.commit_resume_import({'id': self.preview['id'], 'selected': [], 'selected_fields': [name['id']], 'confirmed': True})
        self.assertEqual(result['facts'], [])
        self.assertEqual(result['profile_fields'], {'name': 'Synthetic Candidate'})

    def complete(self, mutation=None):
        p = self.organizer.preview({'id': self.preview['id']})
        rows = [{'section': g['section'], 'block_ids': g['block_ids']} for g in self.preview['structure']['groups']]
        if mutation:rows = mutation(copy.deepcopy(rows))
        response = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': json.dumps({'groups': rows})}}]}).encode()
        with patch('resume_organization.providers.request_model', return_value=response):
            self.organizer.send({'id': p['id'], 'sha256': p['sha256'], 'key': 'SYNTHETIC_ONE_REQUEST_KEY', 'confirmed': True})
            self.organizer.worker.join(2)
        return self.organizer.status({'id': p['id']})

    def test_ai_request_excludes_contact_summary_and_requires_exact_review(self):
        p = self.organizer.preview({'id': self.preview['id']})
        self.assertNotIn('candidate@example.invalid', p['payload'])
        self.assertNotIn('Data engineer building reliable pipelines.', p['payload'])
        self.assertEqual(p['model'], 'openrouter/free')
        with patch('resume_organization.providers.request_model') as send:
            for change in ({'confirmed': False}, {'sha256': '0' * 64}):
                with self.assertRaises(ValueError):
                    self.organizer.send({'id': p['id'], 'sha256': p['sha256'], 'key': 'SYNTHETIC', 'confirmed': True} | change)
            send.assert_not_called()
        result = self.complete()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['structure']['method'], 'model')
        self.assertIsNone(self.service.profile())

    def test_ai_unknown_duplicate_dropped_ids_and_rewritten_claims_fail_closed(self):
        original = copy.deepcopy(self.preview['structure'])
        for mutation in (lambda rows: rows[:-1],
                         lambda rows: rows + [rows[0]],
                         lambda rows: [{'section': 'Skills', 'block_ids': ['invented']}],
                         lambda rows: [dict(rows[0], text='Invented qualification')]):
            state = self.complete(mutation)
            self.assertEqual(state['status'], 'failed')
            self.assertEqual(self.service.imports[self.preview['id']]['result']['structure'], original)

    def test_cancelled_ai_result_is_not_adopted(self):
        p = self.organizer.preview({'id': self.preview['id']})
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def slow(*args):
            started.set();release.wait(2)
            raise ValueError('SECRET_BODY_MUST_NOT_APPEAR')
        with patch('resume_organization.providers.request_model', side_effect=slow):
            self.organizer.send({'id': p['id'], 'sha256': p['sha256'], 'key': 'SYNTHETIC', 'confirmed': True})
            self.assertTrue(started.wait(1))
            with self.assertRaisesRegex(ValueError, 'Wait for organization'):
                self.service.commit_resume_import({'id': p['id'], 'selected': [{'id': '6', 'section': 'Skills'}], 'confirmed': True})
            self.organizer.cancel({'id': p['id']})
            release.set();self.organizer.worker.join(2)
        self.assertEqual(self.organizer.status({'id': p['id']})['status'], 'cancelled')
        self.assertEqual(self.service.imports[p['id']]['result']['structure']['method'], 'local')

    def test_original_source_catalog_reports_corruption_and_never_serves_it(self):
        name = self.preview['structure']['profile_suggestions'][0]['id']
        self.service.commit_resume_import({'id': self.preview['id'], 'selected': [], 'selected_fields': [name], 'confirmed': True})
        item = self.service.resume_sources()['items'][0]
        (self.service.artifacts / 'resume-imports' / item['id']).write_bytes(b'Tampered')
        self.assertEqual(self.service.resume_sources()['items'], [])
        self.assertTrue(self.service.resume_sources()['issues'])
        with self.assertRaises(ValueError):self.service.download('resume-source', item['id'])


class OpenRouterFreeTests(unittest.TestCase):
    def config(self, model='openrouter/free'):
        return {'kind': 'openrouter', 'model': model, 'port': 0}

    def payload(self):
        original = {'instructions': 'Use exact source IDs.', 'input': [{'content': 'Synthetic career text'}],
                    'text': {'format': {'schema': {'type': 'object'}}}}
        return providers.request_payload(json.dumps(original).encode(), self.config())

    def test_only_free_model_ids_and_zero_price_policy_are_allowed(self):
        providers.validate_config(self.config('synthetic/model:free'))
        for model in ('openrouter/auto', 'openai/gpt-4.1-mini', 'synthetic/model'):
            with self.assertRaises(ValueError):providers.validate_config(self.config(model))
        body = json.loads(self.payload())
        self.assertEqual(body['provider']['max_price'], {'prompt': 0, 'completion': 0, 'request': 0})
        self.assertFalse(body['provider']['allow_fallbacks'])
        self.assertTrue(body['provider']['require_parameters'])

    def test_exact_fixed_host_transport_and_tampered_paid_fallback_refusal(self):
        connection = MagicMock();response = connection.getresponse.return_value
        response.status = 200;response.getheader.return_value = 'application/json';response.length = 0
        response.read1.side_effect = [b'{}', b'']
        with patch('model_providers.http.client.HTTPSConnection', return_value=connection) as connect:
            providers.request_model(self.config(), self.payload(), 'SYNTHETIC_KEY', threading.Event())
            self.assertEqual(connect.call_args.args, ('openrouter.ai',))
            self.assertEqual(connection.request.call_args.args[:2], ('POST', '/api/v1/chat/completions'))
        body = json.loads(self.payload());body['models'] = ['paid/fallback']
        with patch('model_providers.http.client.HTTPSConnection') as connect:
            with self.assertRaises(ValueError):
                providers.request_model(self.config(), json.dumps(body).encode(), 'SYNTHETIC_KEY', threading.Event())
            connect.assert_not_called()

    def test_board_url_auto_detection_uses_fixed_provider_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            service = WebService(Path(directory) / 'jobs.db', demo=True)
            with patch.object(service.boards, 'start', return_value={}) as start:
                service.board_action({'action': 'fetch', 'provider': 'greenhouse', 'token': 'https://jobs.lever.co/synthetic', 'confirmed': True})
                start.assert_called_once_with('lever', 'synthetic', True)
                for url in ('https://evil.invalid/synthetic', 'https://jobs.lever.co/synthetic/job-id'):
                    with self.assertRaises(ValueError):
                        service.board_action({'action': 'fetch', 'provider': 'greenhouse', 'token': url, 'confirmed': True})
