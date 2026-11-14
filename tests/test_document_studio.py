from io import BytesIO
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from pypdf import PdfReader
from application_dossier import build_dossier, verify_dossier_bytes
from cover_letter import make_letter, letter_snapshot, export_letter
from job_store import JobStore
from recipient_bundle import recipient_bytes
from resume_render import resume_html, resume_pdf, THEMES
from resume_versions import decoded, encoded, resume_snapshot
from test_profile import synthetic_profile


class DocumentStudioTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.store=JobStore(self.root/'jobs.db')
        self.job=self.store.save((Path(__file__).parents[1]/'examples/synthetic.json').read_bytes(),'Engineer','Synthetic Co')
        profile=synthetic_profile()
        profile['facts'].append({'id':'second-project','section':'Projects','claim':'Second synthetic project.','source':'Synthetic fixture.','reviewed':True})
        self.profile_id=self.store.save_profile(json.dumps(profile).encode())
        self.profile=self.store.load_profile(self.profile_id)
        self.ids=['second-project','project-python']

    def test_layouts_keep_exact_selected_text_and_order_with_distinct_appearance(self):
        pdfs=[]
        for theme in THEMES:
            pdf=resume_pdf(self.profile['profile'],self.ids,theme);pdfs.append(pdf)
            self.assertEqual(pdf,resume_pdf(self.profile['profile'],self.ids,theme))
            text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
            self.assertLess(text.index('Second synthetic project.'),text.index('Built a synthetic Python'))
            self.assertNotIn('Synthetic project exercise, not employment',text)
            self.assertNotIn('Unreviewed draft',text)
        self.assertEqual(len(set(pdfs)),3)
        with self.assertRaises(ValueError):resume_html(self.profile['profile'],self.ids,'<script>')

    def test_old_and_new_versions_replay_and_recover_with_layout_bound_to_documents(self):
        for theme in THEMES:
            rid=self.store.create_resume(self.profile_id,self.ids,'Layout '+theme,self.job,confirmed=True,theme=theme)
            item=self.store.load_resume(rid);record,_=resume_snapshot(item['snapshot'])
            self.assertEqual(record['format'],'roleweave-resume-v1' if theme=='classic' else 'roleweave-resume-v2')
            dossier=build_dossier(self.store.load(self.job),item,[])
            verify_dossier_bytes(dossier)
            if theme!='classic':
                changed=copy.deepcopy(record);changed['theme']='editorial' if theme=='slate' else 'slate'
                with self.assertRaisesRegex(ValueError,'HTML'):resume_snapshot(json.dumps(changed).encode())
        backup=self.root/'backup.json';self.store.backup(backup)
        restored=JobStore(self.root/'restored.db');restored.restore(backup)
        self.assertEqual(len(restored.list_resumes()),3)
        for row in restored.list_resumes():self.assertEqual(restored.load_resume(row['id'])['snapshot'],self.store.load_resume(row['id'])['snapshot'])

    def test_letter_pdf_is_frozen_replayed_and_recipient_kit_contains_only_selected_documents(self):
        rid=self.store.create_resume(self.profile_id,self.ids,'Slate',self.job,confirmed=True,theme='slate')
        snapshot=make_letter(self.profile,self.ids,self.store.load(self.job),'My synthetic motivation.','Thank you.',confirmed=True,include_pdf=True)
        record,_=letter_snapshot(snapshot);pdf=decoded(record['pdf_base64'],2*1024*1024)
        text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        self.assertIn('My synthetic motivation.',text);self.assertIn('Second synthetic project.',text)
        self.assertNotIn('Synthetic fixture.',text)
        path=self.root/'letter.pdf';export_letter(snapshot,path,'pdf',confirmed=True)
        self.assertEqual(path.read_bytes(),pdf)
        with self.assertRaises(FileExistsError):export_letter(snapshot,path,'pdf',confirmed=True)
        dossier=build_dossier(self.store.load(self.job),self.store.load_resume(rid),[],letter=snapshot)
        verify_dossier_bytes(dossier)
        kit=recipient_bytes(dossier,['pdf','letter-pdf'])
        with zipfile.ZipFile(BytesIO(kit)) as archive:
            self.assertEqual(set(archive.namelist()),{'resume.pdf','cover-letter.pdf'})
            self.assertEqual(archive.read('cover-letter.pdf'),pdf)
        changed=copy.deepcopy(record);changed['pdf_base64']=encoded(b'%PDF-forged');changed['pdf_sha256']=hashlib.sha256(b'%PDF-forged').hexdigest()
        with self.assertRaisesRegex(ValueError,'replay'):letter_snapshot(json.dumps(changed).encode())

    def test_legacy_letters_still_work_without_inventing_frozen_pdf(self):
        snapshot=make_letter(self.profile,self.ids,self.store.load(self.job),'Synthetic introduction.','Thanks.',confirmed=True)
        record,_=letter_snapshot(snapshot);self.assertEqual(record['format'],'roleweave-letter-v1')
        with self.assertRaisesRegex(ValueError,'older letter'):export_letter(snapshot,self.root/'old.pdf','pdf',confirmed=True)
        self.assertFalse((self.root/'old.pdf').exists())

    def test_long_letter_paginate_without_losing_last_text_and_unsupported_glyph_fails(self):
        snapshot=make_letter(self.profile,self.ids,self.store.load(self.job),'Detailed synthetic introduction. '*150,'FINAL LETTER END',confirmed=True,include_pdf=True)
        record,_=letter_snapshot(snapshot);reader=PdfReader(BytesIO(decoded(record['pdf_base64'],2*1024*1024)))
        self.assertGreater(len(reader.pages),1)
        self.assertIn('FINAL LETTER END','\n'.join(p.extract_text() for p in reader.pages))
        with self.assertRaisesRegex(ValueError,'font cannot render'):
            make_letter(self.profile,self.ids,self.store.load(self.job),'Unsupported \U0001f680','Thanks.',confirmed=True,include_pdf=True)
