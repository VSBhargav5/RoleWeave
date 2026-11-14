import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from datetime import date

from career_profile import profile_snapshot
from job_search import parse_search, search_path
from web_server import LocalServer
from web_service import WebService, browser_profile, seed_web_demo


class WebWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'jobs.db'
        seed_web_demo(self.path)
        self.service = WebService(self.path, demo=True)

    def test_profile_optional_contact_fields_and_old_snapshots(self):
        profile = self.service.profile()['profile']
        for key in ('first_name', 'last_name', 'linkedin', 'website'):
            profile.pop(key)
        profile_snapshot(json.dumps(profile).encode())
        profile['first_name'] = 'Synthetic'
        profile_snapshot(json.dumps(profile).encode())
        profile['secret'] = 'never accepted'
        with self.assertRaises(ValueError):
            profile_snapshot(json.dumps(profile).encode())

    def test_resume_import_requires_observed_selection_section_and_confirmation(self):
        import base64
        payload=b'Synthetic Candidate\nBuilt a Python pipeline.'
        old=self.service.profile()
        preview=self.service.preview_resume_import({'name':'resume.txt','base64':base64.b64encode(payload).decode()})
        self.assertEqual(self.service.profile(),old)
        args={'id':preview['id'],'selected':[{'id':'2','section':'Projects'}],'confirmed':True}
        for changes in [{'confirmed':False},{'selected':[{'id':'invented','section':'Projects'}]},
                        {'selected':[{'id':'2','section':'Unknown'}]},{'selected':[]}]:
            with self.assertRaises(ValueError):self.service.commit_resume_import(args|changes)
        result=self.service.commit_resume_import(args)
        self.assertEqual(result['facts'][0]['claim'],'Built a Python pipeline.')
        self.assertIn(hashlib.sha256(payload).hexdigest(),result['facts'][0]['source'])
        self.assertEqual(self.service.profile(),old)  # Still a draft; no automatic profile write.
        self.assertEqual((self.service.artifacts/'resume-imports'/(preview['sha256']+'.txt')).read_bytes(),payload)
        self.service.imports[preview['id']]['at']-=601
        with self.assertRaisesRegex(ValueError,'expired'):self.service.commit_resume_import(args)

    def test_contact_sheet_contains_no_facts_or_tokens(self):
        sheet = browser_profile(self.service.profile()['profile'])
        self.assertEqual(set(sheet), {'format', 'fields'})
        self.assertNotIn('facts', sheet['fields'])
        for key, value in (('name', 'bad\nname'), ('website', 'javascript:alert(1)')):
            p = self.service.profile()['profile'] | {key: value}
            with self.assertRaises(ValueError):
                browser_profile(p)

    def test_full_review_resume_letter_packet_and_tracking(self):
        job = self.service.save_job({'title':'Synthetic engineer','company':'Fixture Co','market':'india_remote','posting':'Python required.'})
        p = self.service.profile()
        binding = {'profile_id':p['id'], 'profile_sha256':p['snapshot_sha256']}
        review = self.service.review_from_profile(binding | {'job_id':job['id'],'quote':'Python required.','fact_ids':['project-python'],'confirmed':True})
        self.assertNotEqual(review['id'], job['id'])
        self.assertEqual(len(review['review']['requirements'][0]['evidence']), 1)
        with self.assertRaises(ValueError):
            self.service.review_from_profile(binding | {'job_id':job['id'],'quote':'Invented requirement','fact_ids':[],'confirmed':True})
        args = binding | {'job_id':review['id'],'fact_ids':['project-python'],'label':'Reviewed test resume'}
        preview = self.service.resume(args)
        with self.assertRaises(ValueError):
            self.service.resume(args, freeze=True)
        resume = self.service.resume(args | {'confirmed':True}, freeze=True)
        self.assertEqual(preview['text'], resume['text'])
        self.assertTrue(self.service.download('resume',resume['id'])[0].startswith(b'%PDF'))
        letter_args = {'job_id':review['id'],'resume_id':resume['id'],'fact_ids':['project-python'],'motivation':'I enjoy careful engineering.','closing':'Thank you.','confirmed':True}
        letter = self.service.letter(letter_args)
        self.assertEqual(letter['text'],self.service.letter(letter_args,freeze=False)['text'])
        packet = self.service.packet({'job_id':review['id'],'resume_id':resume['id'],'formats':['pdf'],'confirmed':True})
        import zipfile
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(self.service.download('packet',packet['id'])[0])) as archive:
            self.assertEqual(archive.namelist(),['resume.pdf'])
        self.service.submit_observation({'job_id':review['id'],'submitted_on':date.today().isoformat(),'channel':'Employer portal','reference':'Synthetic','note':'No real application.','follow_up':'','expected_revision':0,'confirmed':True})
        self.assertEqual(self.service.job(review['id'])['history'][-1]['stage'],'applied')
        with self.assertRaises(ValueError):
            self.service.track({'job_id':review['id'],'stage':'interview','note':'','follow_up':'','expected_revision':0})

    def test_search_result_identity_and_expiry(self):
        result = self.service.search({'query':'Python'})
        self.assertTrue(result['jobs'])
        args = {'search_id':result['search_id'],'job_id':'invented','market':'india_remote'}
        with self.assertRaises(ValueError): self.service.save_search_job(args)
        args['job_id'] = result['jobs'][0]['id']
        self.assertTrue(self.service.save_search_job(args)['id'])
        self.service.searches.clear()
        with self.assertRaises(ValueError): self.service.save_search_job(args)

    def saved_letter(self):
        job = self.service.store.list_jobs()[0]
        profile = self.service.profile()
        resume = self.service.resume({'job_id':job['id'], 'profile_id':profile['id'],
                                     'profile_sha256':profile['snapshot_sha256'], 'fact_ids':['project-python'],
                                     'confirmed':True}, freeze=True)
        letter = self.service.letter({'job_id':job['id'], 'resume_id':resume['id'], 'fact_ids':['project-python'],
                                     'motivation':'Synthetic introduction.', 'closing':'Thank you.', 'confirmed':True})
        return job, resume, letter

    def test_saved_letter_reopens_after_restart_and_in_recipient_bundle(self):
        job, resume, letter = self.saved_letter()
        restarted = WebService(self.path)
        listing = restarted.letters(job['id'])
        self.assertEqual(listing['issues'], [])
        self.assertEqual(listing['items'][0]['id'], letter['id'])
        self.assertEqual(restarted.get_letter(letter['id'])['text'], letter['text'])
        packet = restarted.packet({'job_id':job['id'], 'resume_id':resume['id'], 'letter_id':letter['id'],
                                   'formats':['pdf','letter'], 'confirmed':True})
        from io import BytesIO
        import zipfile
        with zipfile.ZipFile(BytesIO(restarted.download('packet',packet['id'])[0])) as archive:
            self.assertEqual(set(archive.namelist()), {'resume.pdf','cover-letter.txt'})
            self.assertEqual(archive.read('cover-letter.txt').decode(), letter['text'])

    def test_letter_catalog_reports_corruption_without_hiding_the_workspace(self):
        job, resume, letter = self.saved_letter()
        path = self.service._artifact('letters',letter['id'])
        data = json.loads(path.read_bytes())
        data['text'] += 'tampered'
        path.write_text(json.dumps(data),encoding='utf-8')
        catalog = self.service.bootstrap()['letters']
        self.assertFalse(catalog['items'])
        self.assertEqual(len(catalog['issues']),1)
        self.assertTrue(path.exists())
        with self.assertRaises(ValueError):self.service.get_letter(letter['id'])
        with self.assertRaises(ValueError):self.service.get_letter('../outside')

    def test_letter_from_another_job_or_profile_is_refused_in_a_packet(self):
        job, resume, letter = self.saved_letter()
        other = next(item for item in self.service.store.list_jobs() if item['id'] != job['id'])
        profile = self.service.profile()
        other_resume = self.service.resume({'job_id':other['id'], 'profile_id':profile['id'],
                                            'profile_sha256':profile['snapshot_sha256'], 'fact_ids':['project-python'],
                                            'confirmed':True}, freeze=True)
        with self.assertRaises(ValueError):
            self.service.packet({'job_id':other['id'],'resume_id':other_resume['id'],'letter_id':letter['id'],
                                 'formats':['pdf','letter'],'confirmed':True})
        corrected = dict(profile['profile'], headline='Corrected synthetic headline')
        self.service.save_profile({'profile':corrected,'confirmed':True})
        newer = self.service.profile()
        newer_resume = self.service.resume({'job_id':job['id'], 'profile_id':newer['id'],
                                            'profile_sha256':newer['snapshot_sha256'], 'fact_ids':['project-python'],
                                            'confirmed':True}, freeze=True)
        with self.assertRaises(ValueError):
            self.service.packet({'job_id':job['id'],'resume_id':newer_resume['id'],'letter_id':letter['id'],
                                 'formats':['pdf','letter'],'confirmed':True})
    def test_loopback_authorization_assets_and_cross_site_rejection(self):
        server = LocalServer(('127.0.0.1',0),self.service)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def request(path, headers=None, method='GET', body=None):
            conn = http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
            try:
                conn.request(method,path,body=body,headers=headers or {})
                response = conn.getresponse()
                return response.status,response.read(),dict(response.getheaders())
            finally: conn.close()
        self.assertEqual(request('/api/bootstrap')[0],401)
        headers={'X-RoleWeave-Token':server.token}
        status,body,_ = request('/api/bootstrap',headers)
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['stats']['saved'],len(self.service.store.list_jobs()))
        self.assertEqual(request('/api/bootstrap',headers|{'Origin':'https://evil.invalid'})[0],403)
        self.assertEqual(request('/api/bootstrap',headers|{'Host':'evil.invalid'})[0],403)
        self.assertEqual(request('/api/bootstrap',headers|{'Sec-Fetch-Site':'cross-site'})[0],403)
        root=request('/')
        self.assertIn(server.token.encode(),root[1])
        self.assertIn("frame-ancestors 'none'",root[2]['Content-Security-Policy'])
        self.assertEqual(request('/app.js')[0],200)
        self.assertEqual(request('/api/browser-helper',headers)[0],200)
        self.assertEqual(request('/api/jobs',headers|{'Content-Type':'text/plain'},'POST','{}')[0],400)
        self.assertEqual(request('/api/jobs',headers|{'Content-Type':'application/json'},'POST','{"title":1,"title":2}')[0],400)
        status,payload,_=request('/api/workspace-bundle',headers)
        self.assertEqual(status,200)
        status,preview,_=request('/api/recovery/preview',headers|{'Content-Type':'application/octet-stream'},'POST',payload)
        self.assertEqual(status,200);preview=json.loads(preview)
        status,restored,_=request('/api/recovery/restore',headers|{'Content-Type':'application/json'},'POST',
                                  json.dumps({'id':preview['id'],'sha256':preview['summary']['sha256'],'confirmed':True}))
        self.assertEqual(status,200);restored=json.loads(restored)
        with patch('web_server.subprocess.Popen') as launch:
            self.assertEqual(request('/api/recovery/open',headers|{'Content-Type':'application/json'},'POST',
                                      json.dumps({'id':restored['id'],'confirmed':False}))[0],400)
            launch.assert_not_called()
            self.assertEqual(request('/api/recovery/open',headers|{'Content-Type':'application/json'},'POST',
                                      json.dumps({'id':restored['id'],'confirmed':True}))[0],200)
            self.assertIn('--db',launch.call_args.args[0])
            self.assertEqual(Path(launch.call_args.args[0][-1]),self.service.recovery_database({'id':restored['id'],'confirmed':True}))


class RoleSearchTests(unittest.TestCase):
    def fixture(self, **changes):
        row={'public_slug':'fixture-1','title':'Engineer','company':'Fixture','description':'Python required.','url':'https://example.invalid/apply','location':'India'}|changes
        return json.dumps({'data':[row],'meta':{'total':1}}).encode()

    def test_exact_search_filters(self):
        from urllib.parse import parse_qs,urlsplit
        query=parse_qs(urlsplit(search_path('Data engineer','Bengaluru','in',True,20)).query)
        self.assertEqual(query['q'],['Data engineer Bengaluru'])
        self.assertEqual(query['countries'],['IN'])
        self.assertEqual(query['work_mode'],['remote'])
        for args in [('',),('Python','','IND'),('Python','','',False,1),('Python','','',1)]:
            with self.assertRaises(ValueError):search_path(*args)

    def test_contract_fails_closed_and_preserves_hash(self):
        raw=self.fixture()
        parsed=parse_search(raw)
        self.assertEqual(parsed['source_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(parsed['jobs'][0]['posting'],'Python required.')
        for changes in [{'url':'javascript:bad'},{'description':'x'*50001},{'title':''}]:
            result=parse_search(self.fixture(**changes))
            self.assertFalse(result['jobs'])
            self.assertEqual(len(result['excluded']),1)
        with self.assertRaises(ValueError):parse_search(b'{"data":[],"meta":{"ignored_params":["countries"]}}')

    def test_page_boundary_uses_observed_rows_including_exclusions(self):
        row=json.loads(self.fixture())['data'][0]
        rows=[row | {'public_slug':str(i)} for i in range(20)]
        rows[0]['description']=''  # Rejected record still consumed one source position.
        raw=json.dumps({'data':rows,'meta':{'total':41,'limit':20,'offset':20}}).encode()
        page=parse_search(raw,20)
        self.assertEqual(len(page['jobs']),19)
        self.assertEqual(page['page'],{'offset':20,'returned':20,'has_next':True})
        last=parse_search(json.dumps({'data':[row],'meta':{'total':41,'limit':20,'offset':40}}).encode(),40)
        self.assertFalse(last['page']['has_next'])
        capped=parse_search(json.dumps({'data':rows,'meta':{'total':20000}}).encode(),9980)
        self.assertFalse(capped['page']['has_next'])

    def test_wrong_provider_page_and_invalid_offsets_are_refused(self):
        for meta in ({'offset':0}, {'offset':True}, {'limit':100}, {'limit':False}):
            with self.assertRaises(ValueError):parse_search(json.dumps({'data':[],'meta':meta}).encode(),20)
        for offset in (-20,1,10000,False):
            with self.assertRaises(ValueError):parse_search(self.fixture(),offset)

    def test_search_cache_preserves_page_scope_and_source_bytes(self):
        from job_search import JobSearch
        first=self.fixture()
        second=json.dumps({'data':json.loads(first)['data'],'meta':{'offset':20,'limit':20,'total':21}}).encode()
        searcher=JobSearch()
        with patch('job_search.request_bytes',side_effect=[first,second]) as request:
            one=searcher.search('Python',country='IN')
            two=searcher.search('Python',country='IN',offset=20)
            self.assertEqual(searcher.search('Python',country='IN'),one)
        self.assertEqual(request.call_count,2)
        self.assertEqual(two['page']['offset'],20)
        self.assertEqual(searcher.snapshots[two['source_sha256']],second)


if __name__=='__main__': unittest.main()
