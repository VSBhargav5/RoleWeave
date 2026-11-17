import copy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader
from document_locale import checked_locale, label, month, options
from career_entries import fact_text, fact_heading
from cover_letter import letter_snapshot
from resume_render import resume_html, resume_pdf, resume_text
from resume_versions import decoded, encoded, resume_snapshot
from web_service import WebService, seed_web_demo
from workspace_bundle import restore_bundle, recovered_database
from test_career_entries import entry
from test_profile import synthetic_profile


class DocumentLocaleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.path = self.root / 'main/jobs.db'
        seed_web_demo(self.path); self.service = WebService(self.path, demo=True)
        data = synthetic_profile()
        data['facts'] = [entry('Experience', 'exp', title='Data Engineer', organization='Synthetic Co',
                               started='2024-03', current=True, skills='Python', about='Human-authored context.'),
                         entry('Additional', 'custom', heading='My custom heading', title='My original title')]
        data['facts'][0]['claim'] = 'Original exact claim: 17 synthetic rows.'
        self.pid = self.service.store.save_profile(json.dumps(data).encode())
        self.profile = self.service.store.load_profile(self.pid); self.job = self.service.store.list_jobs()[0]['id']
        self.args = dict(profile_id=self.pid, profile_sha256=self.profile['snapshot_sha256'], job_id=self.job,
                         fact_ids=['exp','custom'], label='Localized synthetic document', theme='slate')

    def save_resume(self, locale):
        args = self.args | {'locale':locale}; preview = self.service.resume(args)
        saved = self.service.resume(args | {'preview_sha256':preview['preview_sha256'],'confirmed':True},freeze=True)
        return saved['id'], preview

    def letter_args(self, rid, locale):
        return dict(job_id=self.job,resume_id=rid,fact_ids=['exp'],motivation='My unchanged introduction.',
                    closing='My unchanged closing.',include_pdf=True,locale=locale,confirmed=True)

    def test_catalog_labels_and_all_months_render_in_bundled_font(self):
        self.assertEqual(len(options()),9)
        for choice in options():
            code = choice['id']
            with self.subTest(locale=code):
                data = copy.deepcopy(self.profile['profile'])
                # Exercise every structured section and month, not only ASCII claims.
                from career_entries import SCHEMAS
                data['facts'] = [entry(section,section.lower(),**({'started':'2024-03'} if any(k=='started' for k,*_ in fields) else {})) for section,fields in SCHEMAS.items()]
                pdf = resume_pdf(data,[f['id'] for f in data['facts']],locale=code)
                text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
                for section in SCHEMAS:self.assertIn(label(section,code),text)
                for number in range(1,13):
                    from resume_render import prepare_pdf_fonts
                    prepare_pdf_fonts(month('2024-'+str(number).zfill(2),code))
                self.assertIn('lang="'+code+'"',resume_html(data,[f['id'] for f in data['facts']],locale=code).decode())

    def test_localized_dates_and_labels_do_not_translate_or_rewrite_user_content(self):
        fact=self.profile['profile']['facts'][0]
        text=fact_text(fact,locale='de')
        for exact in ('Data Engineer','Synthetic Co','Human-authored context.','Original exact claim: 17 synthetic rows.','Python'):
            self.assertIn(exact,text)
        self.assertIn('März 2024 - Heute',text);self.assertNotIn('2024-03',text)
        self.assertIn('2024-03 - Present',fact_text(fact))
        self.assertEqual(fact_heading(self.profile['profile']['facts'][1],'de'),'My custom heading')
        self.assertEqual(fact_text(fact,for_model=True),fact_text(fact))
        self.assertEqual(month('2024-03','en-US'),'March 2024')
        self.assertEqual(month('2024-03','en'),'2024-03')

    def test_strict_locale_and_date_contracts_reject_injection_or_silent_fallback(self):
        for value in ('DE','fr-FR','zh','../../de','<script>',None,False,[],{}):
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'document language'):checked_locale(value)
        for value in ('2024-3','2024-13','0000-01','2024-00',None):
            with self.subTest(value=value),self.assertRaises(ValueError):month(value,'de')
        with self.assertRaises(ValueError):self.service.resume(self.args|{'locale':'../../de'})
        self.assertEqual(self.service.store.list_resumes(self.job),[])

    def test_resume_preview_hash_covers_locale_and_requires_fresh_approval(self):
        preview=self.service.resume(self.args|{'locale':'de'})
        for value in ('fr','en'):
            with self.assertRaisesRegex(ValueError,'preview changed'):
                self.service.resume(self.args|{'locale':value,'preview_sha256':preview['preview_sha256'],'confirmed':True},freeze=True)
        with self.assertRaisesRegex(ValueError,'preview changed'):
            self.service.resume(self.args|{'locale':'de','confirmed':True},freeze=True)
        rid,preview=self.save_resume('de')
        self.assertIn('Berufserfahrung',preview['text']);self.assertIn('März 2024',preview['text'])
        self.assertEqual(self.service.store.load_resume(rid)['resume']['locale'],'de')
        self.assertEqual(self.service.download('resume',rid)[0],decoded(preview['pdf_base64'],8*1024*1024))
        txt=self.service.download('resume',rid,format='txt')[0].decode()
        self.assertEqual(txt,preview['text'])
        path=self.root/'resume.txt';self.service.store.export_resume(rid,path,'txt')
        self.assertEqual(path.read_text(encoding='utf-8'),txt)
        with self.assertRaises(FileExistsError):self.service.store.export_resume(rid,path,'txt')

    def test_locale_change_cannot_keep_old_resume_pdf_even_with_recomputed_hash(self):
        rid,_=self.save_resume('de');record=copy.deepcopy(self.service.store.load_resume(rid)['resume'])
        record['locale']='fr'
        record['html_base64']=encoded(resume_html(self.profile['profile'],['exp','custom'],'slate','fr'))
        record['html_sha256']=hashlib.sha256(decoded(record['html_base64'],8*1024*1024)).hexdigest()
        with self.assertRaisesRegex(ValueError,'PDF does not replay'):resume_snapshot(json.dumps(record).encode())

    def test_letter_locale_is_reviewed_and_replays_text_pdf_and_metadata(self):
        rid,_=self.save_resume('de');args=self.letter_args(rid,'fr');preview=self.service.letter(args,freeze=False)
        self.assertIn('Madame, Monsieur,',preview['text']);self.assertIn('My unchanged introduction.',preview['text'])
        with self.assertRaisesRegex(ValueError,'preview changed'):
            self.service.letter(args|{'locale':'es','preview_sha256':preview['preview_sha256']})
        saved=self.service.letter(args|{'preview_sha256':preview['preview_sha256']})
        record,_=letter_snapshot(self.service._letter_bytes(saved['id']))
        self.assertEqual(record['format'],'roleweave-letter-v3');self.assertEqual(record['locale'],'fr')
        pdf=decoded(record['pdf_base64'],2*1024*1024);reader=PdfReader(BytesIO(pdf))
        self.assertIn('Lettre de motivation',reader.metadata.title)
        self.assertIn('Expérience','\n'.join(p.extract_text() for p in reader.pages))
        changed=copy.deepcopy(record);changed['locale']='es'
        with self.assertRaisesRegex(ValueError,'replay'):letter_snapshot(json.dumps(changed).encode())
        self.assertEqual(self.service.get_letter(saved['id'])['locale'],'fr')

    def test_all_letter_labels_are_renderable_and_legacy_versions_keep_their_contract(self):
        from cover_letter import make_letter
        from resume_versions import make_resume_version
        for option in options():
            code=option['id']
            with self.subTest(locale=code):
                snapshot=make_letter(self.profile,['exp'],self.service.store.load(self.job),'Exact intro','Exact closing',confirmed=True,include_pdf=True,locale=code)
                record,_=letter_snapshot(snapshot)
                self.assertIn('Exact intro',record['text']);self.assertIn('Exact closing',record['text'])
                reader=PdfReader(BytesIO(decoded(record['pdf_base64'],2*1024*1024)))
                self.assertIn('Original exact claim: 17 synthetic rows.',reader.pages[0].extract_text())
        for theme,expected in [('classic','roleweave-resume-v1'),('slate','roleweave-resume-v2')]:
            record,_=resume_snapshot(make_resume_version(self.profile,['exp'],'Legacy default',theme=theme))
            self.assertEqual(record['format'],expected);self.assertNotIn('locale',record)
            self.assertIn('2024-03',decoded(record['html_base64'],8*1024*1024).decode())
        for include_pdf,expected in [(False,'roleweave-letter-v1'),(True,'roleweave-letter-v2')]:
            record,_=letter_snapshot(make_letter(self.profile,['exp'],self.service.store.load(self.job),'Intro','Closing',confirmed=True,include_pdf=include_pdf))
            self.assertEqual(record['format'],expected);self.assertNotIn('locale',record)

    def test_localized_documents_and_recipient_bytes_survive_managed_recovery(self):
        rid,preview=self.save_resume('es');args=self.letter_args(rid,'es');letter=self.service.letter(args,freeze=False)
        lid=self.service.letter(args|{'preview_sha256':letter['preview_sha256']})['id']
        kit=self.service.packet(dict(job_id=self.job,resume_id=rid,letter_id=lid,formats=['pdf','letter-pdf'],confirmed=True))
        result=restore_bundle(self.service.workspace_bundle(),self.root/'recovered')
        restored=WebService(recovered_database(self.root/'recovered',result['id']))
        self.assertEqual(restored.store.load_resume(rid)['snapshot'],self.service.store.load_resume(rid)['snapshot'])
        self.assertEqual(restored.get_letter(lid),self.service.get_letter(lid))
        self.assertEqual(restored.download('packet',kit['id'])[0],self.service.download('packet',kit['id'])[0])
        self.assertEqual(restored.download('resume',rid,format='txt')[0].decode(),preview['text'])

    def test_unsupported_content_still_fails_pdf_without_silent_substitution(self):
        data=copy.deepcopy(self.profile['profile']);data['name']='Unsupported \U0001f680'
        with self.assertRaisesRegex(ValueError,'font cannot render'):resume_pdf(data,['exp'],locale='fr')
        self.assertIn('🚀',resume_html(data,['exp'],locale='fr').decode())
