import copy
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock

import model_providers as providers
from model_preferences import read_settings, save_settings, settings_bytes, parse_settings
from web_service import WebService, seed_web_demo
from tailoring_session import TailoringSession
from application_draft import draft_snapshot
from workspace_bundle import export_bundle, restore_bundle, recovered_database, inspect_bundle
from test_ai_tailoring import proposed, response


def config(kind='ollama',port=11434):
    return {'kind':kind,'model':'synthetic-model','port':port if kind in providers.LOCAL else 0}


def wrapped(kind,draft=None):
    text=json.dumps(draft or proposed())
    if kind=='openai': return response(draft or proposed())
    if kind=='anthropic': result={'type':'message','role':'assistant','stop_reason':'end_turn','content':[{'type':'text','text':text}]}
    elif kind=='ollama': result={'done':True,'done_reason':'stop','message':{'role':'assistant','content':text}}
    else: result={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':text}}]}
    return json.dumps(result).encode()


class ModelProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.service=WebService(self.root/'jobs.db')
        seed_web_demo(self.service.store.path);self.addCleanup(self.service.tailoring.shutdown)
        self.store=self.service.store;self.profile=self.service.profile();self.job=self.store.list_jobs()[0]['id']
        self.facts=[self.profile['profile']['facts'][0]]
        self.args={'profile_id':self.profile['id'],'profile_sha256':self.profile['snapshot_sha256'],'job_id':self.job,'fact_ids':['project-python'],'instruction':'Use only reviewed project experience.'}

    def test_default_and_strict_config_no_credentials_endpoints_or_coerced_ports(self):
        self.assertEqual(read_settings(self.store)['config'],providers.DEFAULT)
        for value in ({**config(),'key':'SECRET'},{**config(),'endpoint':'https://other.invalid'},config(port=True),config(port=0),config(port=65536),{**config(),'model':'bad\nheader'},{**config(),'kind':[]},config('other'),{**config('openai'),'port':80}):
            with self.subTest(value=value),self.assertRaises(ValueError):providers.validate_config(value)
        for key in (' space','bad\nheader',None,'x'*1001):
            with self.assertRaises(ValueError):providers.validate_key(config(),key)
        providers.validate_key(config(),'')
        with self.assertRaises(ValueError):providers.validate_key(config('openai'),'')

    def test_save_is_local_secret_free_and_compare_and_swap(self):
        first=read_settings(self.store)
        with patch('http.client.HTTPConnection') as local,patch('http.client.HTTPSConnection') as cloud:
            saved=self.service.save_model_settings({'config':config(),'expected_sha256':first['sha256']})
            local.assert_not_called();cloud.assert_not_called()
        self.assertEqual(saved['config'],config())
        with self.assertRaises(ValueError):self.service.save_model_settings({'config':config('mistral'),'expected_sha256':first['sha256']})
        with self.assertRaises(ValueError):self.service.save_model_settings({'config':config(),'expected_sha256':saved['sha256'],'key':'SECRET'})
        self.assertEqual(WebService(self.store.path).bootstrap()['ai_provider'],saved)

    def test_preferences_snapshot_duplicate_keys_extra_fields_and_limit_rejected(self):
        self.assertEqual(parse_settings(settings_bytes(config())),config())
        for data in (b'x'*2049,b'{}',b'{"format":"a","format":"b"}',settings_bytes(config()).replace(b'"config":',b'"key":"SECRET","config":')):
            with self.assertRaises(ValueError):parse_settings(data)

    def test_each_payload_keeps_sources_schema_and_no_tools(self):
        original=self.service.tailoring.preview(self.args)['payload'].encode()
        for kind in providers.KINDS:
            with self.subTest(kind=kind):
                payload=providers.request_payload(original,config(kind));data=json.loads(payload)
                self.assertEqual(data['model'],'synthetic-model');self.assertNotIn('tools',data)
                self.assertIn('project-python',payload.decode());self.assertNotIn(self.profile['profile']['email'],payload.decode())
                if kind=='openai': self.assertFalse(data['store'])
                elif kind=='anthropic': self.assertEqual(data['output_config']['format']['type'],'json_schema')
                elif kind=='ollama': self.assertEqual(data['format']['type'],'object');self.assertFalse(data['stream'])
                else:self.assertTrue(data['response_format']['json_schema']['strict'])

    def test_each_response_validates_citations_and_complete_text(self):
        for kind in providers.KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(providers.parse_provider_response(wrapped(kind),self.facts,config(kind)),proposed())
                bad=proposed();bad['bullets'][0]['fact_id']='invented'
                with self.assertRaises(ValueError):providers.parse_provider_response(wrapped(kind,bad),self.facts,config(kind))
                for data in (b'{}',b'not json',b'x'*(1024*1024+1)):
                    with self.assertRaises(ValueError):providers.parse_provider_response(data,self.facts,config(kind))

    def test_truncated_refused_tool_and_multiple_message_results_fail_closed(self):
        for kind in ('anthropic','mistral','lmstudio','ollama'):
            data=json.loads(wrapped(kind));bad=[]
            if kind=='anthropic':
                v=copy.deepcopy(data);v['stop_reason']='max_tokens';bad.append(v)
                v=copy.deepcopy(data);v['content'].append({'type':'tool_use'});bad.append(v)
            elif kind=='ollama':
                v=copy.deepcopy(data);v['done_reason']='length';bad.append(v)
                v=copy.deepcopy(data);v['message']['tool_calls']=[{}];bad.append(v)
            else:
                v=copy.deepcopy(data);v['choices'][0]['finish_reason']='length';bad.append(v)
                v=copy.deepcopy(data);v['choices'][0]['message']['refusal']='refused';bad.append(v)
                v=copy.deepcopy(data);v['choices']*=2;bad.append(v)
            for value in bad:
                with self.subTest(kind=kind),self.assertRaises(ValueError):providers.parse_provider_response(json.dumps(value).encode(),self.facts,config(kind))

    def test_preview_freezes_destination_even_when_settings_change_and_key_not_retained(self):
        save_settings(self.store,config('lmstudio'))
        preview=self.service.tailoring.preview(self.args);entry=self.service.tailoring.entries[preview['id']]
        save_settings(self.store,config('mistral'))
        self.assertTrue(preview['local']);self.assertIn(':11434/',preview['endpoint'])
        self.assertNotEqual(providers.request_fingerprint(entry['payload'],config('lmstudio',1234)),preview['sha256'])
        with patch('model_providers.propose',return_value=proposed()) as call:
            self.service.tailoring.send({'id':preview['id'],'sha256':preview['sha256'],'key':'SYNTHETIC-SECRET','confirmed':True})
            entry['thread'].join(3)
            self.assertEqual(call.call_args.args[0],config('lmstudio'))
        self.assertNotIn('SYNTHETIC-SECRET',repr(entry))
        self.assertEqual(entry['status'],'completed')
        self.assertNotIn(b'SYNTHETIC-SECRET',self.store.path.read_bytes())

    def test_accept_records_provider_provenance_and_recovery_preserves_nonsecret_preferences(self):
        save_settings(self.store,config('ollama'))
        session=TailoringSession(self.store,demo=True);self.addCleanup(session.shutdown)
        preview=session.preview(self.args);session.send({'id':preview['id'],'sha256':preview['sha256'],'key':'','confirmed':True})
        session.entries[preview['id']]['thread'].join(3);result=session.status({'id':preview['id']})
        accepted=session.accept({'id':preview['id'],'result_sha256':result['result_sha256'],'fact_edits':[],'fields':{'letter_closing':'Thank you for reviewing my synthetic project.'},'confirmed':True})
        raw=(self.service.artifacts/'drafts'/(accepted['draft_id']+'.json')).read_bytes();record,_=draft_snapshot(raw)
        self.assertEqual(record['provider'],config());self.assertEqual(record['format'],'roleweave-application-draft-v2')
        archive=export_bundle(self.store,self.service.artifacts);parts,summary=inspect_bundle(archive)
        self.assertIn('model-settings.json',parts)
        restored=restore_bundle(archive,self.root/'recovered');path=recovered_database(self.root/'recovered',restored['id'])
        self.assertEqual(WebService(path).bootstrap()['ai_provider'],read_settings(self.store))
        self.assertEqual((path.parent/'web-artifacts/drafts'/(accepted['draft_id']+'.json')).read_bytes(),raw)

    def test_tampered_provider_in_saved_draft_rejected(self):
        save_settings(self.store,config());session=TailoringSession(self.store,demo=True);self.addCleanup(session.shutdown)
        p=session.preview(self.args);session.send({'id':p['id'],'sha256':p['sha256'],'key':'','confirmed':True});session.entries[p['id']]['thread'].join(3)
        r=session.status({'id':p['id']});a=session.accept({'id':p['id'],'result_sha256':r['result_sha256'],'fact_edits':[],'fields':{'letter_closing':'Thank you for reviewing my synthetic project.'},'confirmed':True})
        data=json.loads((self.service.artifacts/'drafts'/(a['draft_id']+'.json')).read_bytes());data['provider']['key']='SECRET'
        with self.assertRaises(ValueError):draft_snapshot(json.dumps(data).encode())

    def test_transport_fixed_cloud_headers_no_redirect_or_retry_and_redacted_failure(self):
        connection=MagicMock();r=connection.getresponse.return_value;r.status=200;r.length=0;r.getheader.return_value='application/json';r.read1.side_effect=[b'{}',b'']
        with patch('model_providers.http.client.HTTPSConnection',return_value=connection) as factory:
            self.assertEqual(providers.request_model(config('anthropic'),b'{}','SYNTHETIC-SECRET',threading.Event()),b'{}')
            self.assertEqual(factory.call_args.args,('api.anthropic.com',));headers=connection.request.call_args.kwargs['headers']
            self.assertEqual(headers['anthropic-version'],'2026-10-21');self.assertEqual(headers['Authorization'],'Bearer SYNTHETIC-SECRET')
        for status,ctype,parts,length in ((302,'application/json',[],0),(200,'text/html',[],0),(200,'application/json',[b'x'*(1024*1024+1)],0),(200,'application/json',[b''],3)):
            connection.reset_mock();r.status=status;r.getheader.return_value=ctype;r.read1.side_effect=parts;r.length=length
            with patch('model_providers.http.client.HTTPSConnection',return_value=connection),self.assertRaises(ValueError):providers.request_model(config('mistral'),b'{}','SYNTHETIC-SECRET',threading.Event())
            self.assertEqual(connection.request.call_count,1);connection.close.assert_called_once()
        with patch('model_providers.http.client.HTTPSConnection',side_effect=OSError('SYNTHETIC-SECRET')):
            with self.assertRaisesRegex(ValueError,'no automatic retry') as caught:providers.request_model(config('mistral'),b'{}','SYNTHETIC-SECRET',threading.Event())
            self.assertNotIn('SYNTHETIC-SECRET',str(caught.exception))

    def test_cancel_before_connect_and_while_reading(self):
        stop=threading.Event();stop.set()
        with patch('model_providers.http.client.HTTPConnection') as connect,self.assertRaises(ValueError):providers.request_model(config(),b'{}','',stop)
        connect.assert_not_called();stop.clear();connection=MagicMock();r=connection.getresponse.return_value;r.status=200;r.getheader.return_value='application/json'
        def read(size):stop.set();return b'{}'
        r.read1.side_effect=read
        with patch('model_providers.http.client.HTTPConnection',return_value=connection),self.assertRaises(ValueError):providers.request_model(config(),b'{}','',stop)
        connection.close.assert_called_once()

    def test_actual_numeric_loopback_http_roundtrip_without_external_network(self):
        seen=[]
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append((self.path,self.rfile.read(int(self.headers['Content-Length'])),self.headers.get('Authorization')))
                data=wrapped('ollama');self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            result=providers.propose(config('ollama',server.server_port),b'{"synthetic":true}',self.facts,'',threading.Event())
            self.assertEqual(result,proposed());self.assertEqual(seen,[('/api/chat',b'{"synthetic":true}',None)])
        finally:server.shutdown();server.server_close();thread.join()

