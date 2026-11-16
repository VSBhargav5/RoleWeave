import copy
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader
from career_entries import FORMAT, SCHEMAS, fact_text
from career_profile import imported_career_facts, profile_snapshot
from resume_render import resume_text, resume_html, resume_pdf
from ai_tailoring import request_payload, reviewed_variant, synthetic_draft, validate_draft
from job_store import JobStore
from web_service import WebService, seed_web_demo
from workspace_bundle import export_bundle, restore_bundle, recovered_database
from test_profile import synthetic_profile


def entry(section, identifier=None, **values):
    fields={key:(False if kind=='bool' else '') for key,_label,kind,_required in SCHEMAS[section]}
    fields.update({key:'Synthetic '+key for key,_label,_kind,required in SCHEMAS[section] if required})
    fields.update(values)
    return {'id':identifier or section.lower(),'claim':'','source':'PRIVATE synthetic source only',
            'reviewed':True,'section':section,'details':{'format':FORMAT,'fields':fields}}


class CareerEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name);self.path=self.folder/'jobs.db'
        seed_web_demo(self.path);self.service=WebService(self.path,demo=True)
        self.profile=synthetic_profile()

    def snapshot(self,facts):
        return json.dumps(self.profile|{'facts':facts}).encode()

    def test_all_ten_sections_roundtrip_without_fabricated_accomplishments(self):
        facts=[entry(s) for s in SCHEMAS]
        decoded,_=profile_snapshot(self.snapshot(facts))
        self.assertEqual(decoded['facts'],facts)
        for fact in facts:
            self.assertIn(fact['details']['fields']['title'],fact_text(fact))
            self.assertEqual(fact['claim'],'')
        self.assertEqual(len(SCHEMAS),10)

    def test_dates_are_months_and_current_or_expiry_contract_is_explicit(self):
        for fields in ({'started':'2025-13'},{'started':'0000-01'},{'started':'2025-1'},
                       {'started':'2025-01','ended':'2024-12'},{'current':True,'ended':'2026-01'},
                       {'started':202501},{'current':'true'}):
            with self.subTest(fields=fields),self.assertRaises(ValueError):profile_snapshot(self.snapshot([entry('Experience',**fields)]))
        good=entry('Experience',started='2025-01',current=True)
        self.assertIn('2025-01',fact_text(good));self.assertIn('Present',fact_text(good))
        self.assertNotIn('years',fact_text(good))
        cert=entry('Certifications',started='2025-01',ended='2027-01',credential_id='DEMO-1')
        profile_snapshot(self.snapshot([cert]));self.assertIn('DEMO-1',fact_text(cert))

    def test_unknown_fields_controls_urls_types_and_limits_fail_closed(self):
        good=entry('Projects')
        invalid=[]
        for key,value in [('title',''),('title','x'*201),('url','javascript:alert(1)'),('about','bad\x00'),('skills',[]),('title','bad\ud800')]:
            f=copy.deepcopy(good);f['details']['fields'][key]=value;invalid.append(f)
        for mutation in ('extra','missing','format','section'):
            f=copy.deepcopy(good)
            if mutation=='extra':f['details']['fields']['invented']='no'
            if mutation=='missing':del f['details']['fields']['title']
            if mutation=='format':f['details']['format']='other'
            if mutation=='section':f['section']='Education'
            invalid.append(f)
        for f in invalid:
            with self.subTest(f=f),self.assertRaises(ValueError):profile_snapshot(self.snapshot([f]))
        profile_snapshot(self.snapshot([entry('Projects',url='https://example.invalid/project')]))
        with self.assertRaises(ValueError):profile_snapshot(self.snapshot([entry('References',email='bad email')]))
        legacy=copy.deepcopy(self.profile['facts'][0]);legacy['claim']=''
        with self.assertRaises(ValueError):profile_snapshot(self.snapshot([legacy]))
        many=[entry('Skills',str(i)) for i in range(201)]
        with self.assertRaisesRegex(ValueError,'200'):profile_snapshot(self.snapshot(many))

    def test_preview_is_validated_and_never_writes_or_infers_review(self):
        before=self.service.profile();f=entry('Education',started='2025-01');f['reviewed']=False
        preview=self.service.career_entry({'fact':f})
        self.assertEqual(preview['fact'],f);self.assertIn('2025-01',preview['text'])
        self.assertEqual(self.service.profile(),before)
        bad=copy.deepcopy(f);bad['details']['fields']['title']=''
        with self.assertRaises(ValueError):self.service.career_entry({'fact':bad})

    def test_selected_documents_print_metadata_in_order_and_escape_it(self):
        facts=[entry('Projects','first',title='First <project>',url='https://example.invalid'),
               entry('Projects','second',title='Second project'),entry('References',email='private@example.invalid'),
               entry('Additional',heading='Community work',title='Synthetic activity')]
        p=self.profile|{'facts':facts};ids=['second','first','additional']
        text=resume_text(p,ids);html=resume_html(p,ids).decode()
        self.assertLess(text.index('Second project'),text.index('First <project>'))
        self.assertIn('Community work',text);self.assertIn('https://example.invalid',text)
        self.assertIn('&lt;project&gt;',html);self.assertNotIn('<project>',html)
        self.assertNotIn('private@example.invalid',html);self.assertNotIn('PRIVATE',html)
        pdf=resume_pdf(p,ids);self.assertEqual(pdf,resume_pdf(p,ids))
        printed=''.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
        self.assertIn('First <project>',printed);self.assertIn('Community work',printed)
        facts[0]['reviewed']=False
        with self.assertRaises(ValueError):resume_text(p,['first'])

    def test_reference_contacts_are_explicitly_selected_but_never_structured_model_context(self):
        f=entry('References',email='reference@example.invalid',phone='+1 555 0100',relationship='Project mentor')
        p=self.profile|{'facts':[f]}
        self.assertIn(f['details']['fields']['email'],resume_text(p,[f['id']]))
        payload=request_payload({'title':'Engineer','company':'Demo','posting':'Python'},p,[f['id']],'Keep it accurate.')
        self.assertNotIn(b'reference@example.invalid',payload);self.assertNotIn(b'+1 555 0100',payload)
        self.assertNotIn(b'PRIVATE',payload);self.assertIn(b'Project mentor',payload)
        # Empty accomplishment text creates no fake practice bullet.
        validate_draft(synthetic_draft([f]),[f]);self.assertEqual(synthetic_draft([f])['bullets'],[])

    def test_ai_accepted_wording_preserves_human_structured_fields_and_old_snapshot(self):
        f=entry('Experience',started='2025-01',current=True);snapshot=self.snapshot([f])
        identifier=self.service.store.save_profile(snapshot);item=self.service.store.load_profile(identifier)
        updated,_=reviewed_variant(item,'job',[{'id':f['id'],'text':'Human reviewed accomplishment.'}],{},'a'*64)
        self.assertEqual(json.loads(updated)['facts'][0]['details'],f['details'])
        self.assertEqual(self.service.store.load_profile(identifier)['snapshot'],snapshot)

    def test_reuse_freezes_full_entry_and_later_removal_does_not_change_it(self):
        f=entry('Experience',started='2025-01',current=True)
        store=self.service.store;identifier=store.save_profile(self.snapshot([f]))
        original=store.load_profile(identifier);copied=imported_career_facts(original,[f['id']])
        store.save_profile(self.snapshot([]))
        self.assertIn('Present',copied[0]['claim']);self.assertIn(identifier,copied[0]['source'])
        self.assertEqual(store.load_profile(identifier)['snapshot'],original['snapshot'])
        self.assertEqual(store.active_profile()['profile']['facts'],[])

    def test_profile_save_rejects_stale_active_version_without_writing(self):
        old=self.service.profile();first=copy.deepcopy(old['profile']);first['headline']='New synthetic headline'
        self.service.save_profile({'profile':first,'confirmed':True,'expected_active_sha256':old['snapshot_sha256']})
        count=len(self.service.store.list_profiles())
        stale=copy.deepcopy(old['profile']);stale['headline']='Stale draft'
        with self.assertRaisesRegex(ValueError,'another window'):
            self.service.save_profile({'profile':stale,'confirmed':True,'expected_active_sha256':old['snapshot_sha256']})
        self.assertEqual(len(self.service.store.list_profiles()),count)
        # Transactional store check protects against a change after the service's read too.
        with self.assertRaisesRegex(ValueError,'another window'):
            self.service.store.save_profile(json.dumps(stale).encode(),expected_active_sha256=old['snapshot_sha256'])
        self.assertEqual(self.service.profile()['profile']['headline'],'New synthetic headline')

    def test_typed_profile_selected_resume_letter_and_managed_recovery_replay(self):
        p=self.service.profile();p['profile']['facts']=[entry('Experience',started='2025-01',current=True),entry('Languages',title='English',level='Self-described fluent')]
        self.service.save_profile({'profile':p['profile'],'confirmed':True,'expected_active_sha256':p['snapshot_sha256']})
        p=self.service.profile();binding={'profile_id':p['id'],'profile_sha256':p['snapshot_sha256']}
        job=self.service.store.list_jobs()[0];ids=['experience','languages']
        resume=self.service.resume(binding|{'job_id':job['id'],'fact_ids':ids,'label':'Structured synthetic','confirmed':True},freeze=True)
        letter=self.service.letter({'job_id':job['id'],'resume_id':resume['id'],'fact_ids':['experience'],'motivation':'Synthetic introduction.','closing':'Thank you.','confirmed':True})
        self.assertIn('Present',letter['text']);self.assertNotIn('PRIVATE',letter['text'])
        bundle=export_bundle(self.service.store,self.service.artifacts)
        restored=restore_bundle(bundle,self.folder/'recovered')
        service=WebService(recovered_database(self.folder/'recovered',restored['id']),demo=True)
        self.assertEqual(service.profile()['profile'],p['profile'])
        self.assertEqual(service.download('resume',resume['id'])[0],self.service.download('resume',resume['id'])[0])
        self.assertEqual(service.download('letter',letter['id'],'txt')[0],self.service.download('letter',letter['id'],'txt')[0])
