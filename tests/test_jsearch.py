import base64
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock,patch
from urllib.parse import parse_qs,urlsplit,quote

import jsearch_source as source
import jsearch_session as session
from job_search import parse_search
from web_service import WebService,seed_web_demo
from workspace_bundle import export_bundle,restore_bundle,recovered_database


def filters(**changes):return {'query':'data engineer','location':'Bengaluru','country':'IN','remote':False,'cursor':'','page':1}|changes


def raw_job(**changes):return {'job_id':'synthetic-original-id','job_title':'Data Engineer','employer_name':'Synthetic company','job_description':'Python required.',
    'job_country':'IN','job_location':'Bengaluru','job_is_remote':False,'job_apply_link':'https://example.invalid/apply','job_posted_at':'Synthetic fixture'}|changes


def response(rows=None,cursor=''):
    return json.dumps({'status':'OK','data':{'jobs':[raw_job()] if rows is None else rows,'cursor':cursor}}).encode()


class JSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.service=WebService(self.root/'jobs.db',demo=False)
        self.addCleanup(self.service.jsearch.shutdown)

    def completed(self,raw=None,public=None):
        preview=self.service.jsearch.preview(public or filters())
        with patch('jsearch_session.request',return_value=raw or response()) as provider:
            self.service.jsearch.send({'id':preview['id'],'sha256':preview['sha256'],'key':'synthetic-key-only','confirmed':True})
            self.service.jsearch.entries[preview['id']]['thread'].join(3)
        result=self.service.jsearch_status({'id':preview['id']});self.assertEqual(result['status'],'completed')
        return preview,result['result']

    def test_public_query_is_fixed_host_one_page_explicit_country_and_cursor(self):
        path=source.path(filters(remote=True));parsed=urlsplit(path);query=parse_qs(parsed.query)
        self.assertEqual(parsed.path,'/jsearch/search-v2');self.assertEqual(query['num_pages'],['1'])
        self.assertEqual(query['query'],['data engineer in Bengaluru']);self.assertEqual(query['country'],['in']);self.assertEqual(query['work_from_home'],['true'])
        self.assertEqual(parse_qs(urlsplit(source.path(filters(page=2,cursor='opaque+/='))).query)['cursor'],['opaque+/='])
        for bad in ({'country':''},{'remote':'true'},{'page':True},{'page':2},{'cursor':'unmatched'},{'query':'x'},{'location':'bad\nlocation'},{'cursor':'bad\ncursor','page':2}):
            with self.subTest(bad=bad),self.assertRaises(ValueError):source.path(filters(**bad))

    def test_original_bytes_wrapper_replay_and_long_provider_identity_hash(self):
        raw=response([raw_job(job_id='id'*600)]);snapshot=source.capture(raw,filters())
        record=json.loads(snapshot);result=parse_search(snapshot)
        self.assertEqual(base64.b64decode(record['response_base64']),raw)
        self.assertEqual(record['response_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['source_sha256'],hashlib.sha256(snapshot).hexdigest())
        self.assertEqual(result['jobs'][0]['id'],'jsearch:'+hashlib.sha256(('id'*600).encode()).hexdigest())
        self.assertIn('Location label: Bengaluru',result['jobs'][0]['posting']);self.assertIn('Returned description:\nPython required.',result['jobs'][0]['posting'])
        self.assertEqual(source.parse_source(snapshot),result)

    def test_bad_envelopes_raw_hash_cursor_and_record_count_fail_closed(self):
        original=json.loads(source.capture(response(),filters()))
        for change in ({'response_sha256':'0'*64},{'response_base64':'not base64!'},{'synthetic':1},{'extra':'bad'},{'observed_at':'2026-01-01T00:00:00'}):
            with self.subTest(change=change),self.assertRaises(ValueError):source.parse_source(json.dumps(original|change).encode())
        for raw in (response(cursor=False),response(cursor=0),response(cursor='x'*4097),response([raw_job(job_id=str(i)) for i in range(11)]),b'{"status":"ERROR","data":{}}',b'not JSON'):
            with self.assertRaises(ValueError):source.capture(raw,filters())
        with self.assertRaisesRegex(ValueError,'repeated'):source.capture(response(cursor='same'),filters(page=2,cursor='same'))

    def test_unsupported_country_remote_links_and_labels_are_reported_without_truncation(self):
        bad=[raw_job(job_country='US'),raw_job(job_is_remote='false'),raw_job(job_apply_link='javascript:alert(1)'),raw_job(job_location=0),raw_job(job_location='bad\nlabel'),raw_job(job_description='x'*50001)]
        result=source.parse_source(source.capture(response([r|{'job_id':str(i)} for i,r in enumerate(bad)]),filters()))
        self.assertEqual(result['jobs'],[]);self.assertEqual(len(result['excluded']),len(bad))
        result=source.parse_source(source.capture(response(),filters(remote=True)))
        self.assertEqual(len(result['excluded']),1)
        dup=source.parse_source(source.capture(response([raw_job(),raw_job()]),filters()));self.assertEqual(len(dup['jobs']),1);self.assertEqual(len(dup['excluded']),1)

    def test_preview_invalid_consent_and_second_send_make_no_extra_request(self):
        with patch('jsearch_session.request',return_value=response()) as provider:
            p=self.service.jsearch.preview(filters());provider.assert_not_called()
            for changed in ({'confirmed':False},{'sha256':'wrong'}):
                with self.assertRaises(ValueError):self.service.jsearch.send({'id':p['id'],'sha256':p['sha256'],'key':'synthetic-key-only','confirmed':True}|changed)
            provider.assert_not_called();self.service.jsearch.send({'id':p['id'],'sha256':p['sha256'],'key':'synthetic-key-only','confirmed':True});self.service.jsearch.entries[p['id']]['thread'].join(3)
            self.assertEqual(provider.call_count,1)
            with self.assertRaises(ValueError):self.service.jsearch.send({'id':p['id'],'sha256':p['sha256'],'key':'synthetic-key-only','confirmed':True})
            result=self.service.jsearch_status({'id':p['id']});self.assertNotIn('synthetic-key-only',json.dumps(result));self.assertNotIn('key',self.service.jsearch.entries[p['id']])

    def test_transport_fixed_host_header_no_redirect_retry_and_redacted_connection_errors(self):
        reply=Mock();reply.status=200;reply.getheader.return_value='application/json';reply.read1.side_effect=[response(),b''];reply.length=0
        connection=Mock();connection.getresponse.return_value=reply
        with patch('http.client.HTTPSConnection',return_value=connection) as factory:
            result=session.request(filters(),'synthetic-key-only',threading.Event())
        factory.assert_called_once_with('api.openwebninja.com',timeout=5);self.assertEqual(result,response())
        args,kwargs=connection.request.call_args;self.assertEqual(args[0],'GET');self.assertNotIn('synthetic-key-only',args[1]);self.assertEqual(kwargs['headers']['x-api-key'],'synthetic-key-only');connection.close.assert_called_once()
        for code in (301,401,429,500):
            reply.status=code;connection.reset_mock()
            with patch('http.client.HTTPSConnection',return_value=connection),self.assertRaisesRegex(ValueError,'HTTP '+str(code)):session.request(filters(),'synthetic-key-only',threading.Event())
            self.assertEqual(connection.request.call_count,1)
        with patch('http.client.HTTPSConnection',side_effect=OSError('PRIVATE secret connection text')),self.assertRaisesRegex(ValueError,'connection failed') as caught:session.request(filters(),'synthetic-key-only',threading.Event())
        self.assertNotIn('PRIVATE',str(caught.exception))

    def test_secret_echo_content_type_truncated_size_and_before_connect_cancel_fail(self):
        for value in ('synthetic-key-only',quote('secret+token/',safe='')):
            key='secret+token/' if value.startswith('secret') else 'synthetic-key-only'
            with self.assertRaisesRegex(ValueError,'credential'):session.reject_echo(json.dumps({'nested':[value]}).encode(),key)
        reply=Mock();reply.status=200;reply.length=1;reply.getheader.return_value='application/json';reply.read1.side_effect=[response(),b''];connection=Mock();connection.getresponse.return_value=reply
        with patch('http.client.HTTPSConnection',return_value=connection),self.assertRaisesRegex(ValueError,'declared length'):session.request(filters(),'synthetic-key-only',threading.Event())
        reply.length=0;reply.getheader.return_value='text/html'
        with patch('http.client.HTTPSConnection',return_value=connection),self.assertRaisesRegex(ValueError,'JSON'):session.request(filters(),'synthetic-key-only',threading.Event())
        reply.getheader.return_value='application/json';reply.read1.side_effect=[b'x'*(source.RAW_LIMIT+1)]
        with patch('http.client.HTTPSConnection',return_value=connection),self.assertRaisesRegex(ValueError,'4MiB'):session.request(filters(),'synthetic-key-only',threading.Event())
        cancel=threading.Event();cancel.set()
        with patch('http.client.HTTPSConnection') as factory,self.assertRaises(ValueError):session.request(filters(),'synthetic-key-only',cancel)
        factory.assert_not_called()

    def test_late_cancel_drops_observation_and_blocks_new_send_until_thread_finishes(self):
        started,release=threading.Event(),threading.Event()
        def slow(*args):started.set();release.wait(3);return response()
        with patch('jsearch_session.request',side_effect=slow):
            p=self.service.jsearch.preview(filters());self.service.jsearch.send({'id':p['id'],'sha256':p['sha256'],'key':'synthetic-key-only','confirmed':True});self.assertTrue(started.wait(1));self.service.jsearch.cancel({'id':p['id']})
            next_p=self.service.jsearch.preview(filters())
            with self.assertRaisesRegex(ValueError,'earlier'):self.service.jsearch.send({'id':next_p['id'],'sha256':next_p['sha256'],'key':'synthetic-key-only','confirmed':True})
            release.set();self.service.jsearch.entries[p['id']]['thread'].join(3)
        self.assertEqual(self.service.jsearch_status({'id':p['id']})['status'],'cancelled');self.assertNotIn('snapshot',self.service.jsearch.entries[p['id']])

    def test_exact_result_import_archive_idempotency_and_recovery(self):
        p,result=self.completed();row=result['jobs'][0]
        with self.assertRaises(ValueError):self.service.save_search_job({'search_id':p['id'],'job_id':'unknown','market':'india_remote'})
        args={'search_id':p['id'],'job_id':row['id'],'market':'india_remote'};job=self.service.save_search_job(args)
        self.assertEqual(self.service.save_search_job(args)['id'],job['id']);self.assertEqual(job['posting'],row['posting'])
        snapshot=(self.service.artifacts/'sources'/(result['source_sha256']+'.json')).read_bytes();self.assertEqual(base64.b64decode(json.loads(snapshot)['response_base64']),response())
        bundle=export_bundle(self.service.store,self.service.artifacts);restored=restore_bundle(bundle,self.root/'recovered');other=WebService(recovered_database(self.root/'recovered',restored['id']))
        self.assertEqual(other.job(job['id'])['posting'],job['posting']);self.assertEqual((other.artifacts/'sources'/(result['source_sha256']+'.json')).read_bytes(),snapshot)

    def test_metadata_changes_create_fresh_review_and_do_not_inherit_applied(self):
        p,result=self.completed();row=result['jobs'][0];first=self.service.save_search_job({'search_id':p['id'],'job_id':row['id'],'market':'india_remote'})
        self.service.track({'job_id':first['id'],'stage':'applied','note':'Synthetic observation only','follow_up':'','expected_revision':0})
        for changed in ({'job_title':'Changed role'},{'employer_name':'Changed employer'},{'job_location':'London'},{'job_is_remote':True}):
            p,result=self.completed(response([raw_job(**changed)]));second=self.service.save_search_job({'search_id':p['id'],'job_id':result['jobs'][0]['id'],'market':'india_remote'})
            self.assertNotEqual(second['id'],first['id']);self.assertEqual(second['history'],[])

    def test_expiry_and_bounded_observations_preserve_already_saved_artifacts(self):
        p,result=self.completed();job=self.service.save_search_job({'search_id':p['id'],'job_id':result['jobs'][0]['id'],'market':'india_remote'})
        self.service.jsearch.entries[p['id']]['at']-=601
        with self.assertRaisesRegex(ValueError,'expired'):self.service.jsearch_status({'id':p['id']})
        self.assertEqual(self.service.job(job['id'])['id'],job['id'])
        for i in range(6):self.completed(public=filters(query='query '+str(i)))
        self.assertLessEqual(len(self.service.jsearch.entries),5)

    def test_rehashed_wrapper_with_wrong_original_response_hash_is_rejected_by_recovery(self):
        p,result=self.completed();self.service.save_search_job({'search_id':p['id'],'job_id':result['jobs'][0]['id'],'market':'india_remote'})
        path=self.service.artifacts/'sources'/(result['source_sha256']+'.json');r=json.loads(path.read_bytes());r['response_sha256']='0'*64;changed=json.dumps(r).encode();path.unlink();(path.parent/(hashlib.sha256(changed).hexdigest()+'.json')).write_bytes(changed)
        with self.assertRaisesRegex(ValueError,'fingerprint'):export_bundle(self.service.store,self.service.artifacts)
