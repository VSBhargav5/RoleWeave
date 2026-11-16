from io import BytesIO
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader
from resume_theme import DEFAULT, validate_theme, parse_theme, theme_bytes
from resume_render import resume_html, resume_pdf
from resume_versions import resume_snapshot
from web_service import WebService, seed_web_demo
from workspace_bundle import export_bundle, restore_bundle, recovered_database
from test_profile import synthetic_profile


class ResumeThemeTests(unittest.TestCase):
    def setUp(self):self.theme=dict(DEFAULT);self.profile=synthetic_profile();self.ids=['project-python']

    def test_strict_portable_contract_contrast_and_integer_bounds(self):
        self.assertEqual(parse_theme(theme_bytes(self.theme)),self.theme)
        invalid=[{'extra':'not CSS'}, {'accent':'#ffffff'},{'accent':'red;url(https://bad.invalid)'},{'body_size':8},{'body_size':True},{'body_size':10.5},{'name_size':31},{'margin_mm':13},{'font':'remote-font'},{'page':'unbounded'}]
        for change in invalid:
            with self.subTest(change=change),self.assertRaises(ValueError):validate_theme({**self.theme,**change})
        for payload in (b'x'*2049,b'{}',b'{"format":"a","format":"b"}'):
            with self.assertRaises(ValueError):parse_theme(payload)

    def test_all_old_preset_html_bytes_remain_exact(self):
        expected={'classic':'fe03c04a7ca88dd6d596771b0c27324aa9810854fdcf36fef42296233ca8550d','slate':'bb04b6c3c267c99a13c1ba7b4042f7cf4c332195d5ce439eaab2fb2c69009d42','editorial':'9a66eb4f88038cac85a093c21a62ed1ffe7fa16e598cb2ae50321c3e6c5476fe'}
        for name,digest in expected.items():self.assertEqual(hashlib.sha256(resume_html(self.profile,self.ids,name)).hexdigest(),digest)

    def test_custom_html_escapes_claims_contains_bounded_layout_and_no_private_sources(self):
        self.profile['name']='<script>not executable</script>';theme={**self.theme,'font':'serif','body_size':12,'margin_mm':24,'page':'Letter'}
        html=resume_html(self.profile,self.ids,theme).decode()
        self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)
        self.assertIn('size:Letter;margin:24mm',html);self.assertIn('font:12pt/1.4 Georgia',html)
        self.assertNotIn(self.profile['facts'][0]['source'],html);self.assertNotIn('Unreviewed draft',html)

    def test_pdf_both_paper_sizes_fonts_deterministic_and_only_selected_text(self):
        for font,page,width,height in (('sans','A4',595.2756,841.8898),('serif','Letter',612,792)):
            with self.subTest(font=font):
                theme={**self.theme,'font':font,'page':page,'body_size':11,'name_size':28,'margin_mm':20}
                data=resume_pdf(self.profile,self.ids,theme);self.assertEqual(data,resume_pdf(self.profile,self.ids,theme))
                reader=PdfReader(BytesIO(data));self.assertAlmostEqual(float(reader.pages[0].mediabox.width),width,places=3);self.assertAlmostEqual(float(reader.pages[0].mediabox.height),height,places=3)
                text=''.join(p.extract_text() for p in reader.pages)
                self.assertIn(self.profile['facts'][0]['claim'],text);self.assertNotIn('Unreviewed draft',text)

    def test_serif_unsupported_characters_fail_instead_of_silent_substitution(self):
        self.profile['name']='Synthetic Omega \u03a9'
        with self.assertRaisesRegex(ValueError,'Serif PDF font supports'):resume_pdf(self.profile,self.ids,{**self.theme,'font':'serif'})
        self.assertTrue(resume_pdf(self.profile,self.ids,self.theme).startswith(b'%PDF-'))

    def test_long_document_paginates_preserving_claims_and_margin(self):
        for i in range(8):self.profile['facts'].append({'id':'long-'+str(i),'section':'Projects','claim':('Synthetic project detail with exact source. '*30)+'END-'+str(i),'source':'Synthetic only','reviewed':True})
        data=resume_pdf(self.profile,['long-'+str(i) for i in range(8)],{**self.theme,'body_size':12,'margin_mm':24})
        reader=PdfReader(BytesIO(data));self.assertGreater(len(reader.pages),1)
        text=''.join(p.extract_text() for p in reader.pages)
        for i in range(8):self.assertIn('END-'+str(i),text)

    def test_frozen_custom_resume_restores_and_rehashed_wrong_style_fails_html_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'jobs.db';seed_web_demo(path);service=WebService(path);profile=service.profile();job=service.store.list_jobs()[0]['id']
            args={'profile_id':profile['id'],'profile_sha256':profile['snapshot_sha256'],'job_id':job,'fact_ids':['project-python'],'label':'Synthetic custom','theme':self.theme}
            preview=service.resume(args);saved=service.resume({**args,'preview_sha256':preview['preview_sha256'],'confirmed':True},freeze=True)
            version=service.store.load_resume(saved['id']);self.assertEqual(version['resume']['theme'],self.theme)
            archive=export_bundle(service.store,service.artifacts);recovery=restore_bundle(archive,root/'recovered');other=WebService(recovered_database(root/'recovered',recovery['id']))
            self.assertEqual(other.store.load_resume(saved['id'])['snapshot'],version['snapshot'])
            data=json.loads(version['snapshot']);data['theme']['body_size']=12
            with self.assertRaisesRegex(ValueError,'HTML'):resume_snapshot(json.dumps(data).encode())
            with self.assertRaisesRegex(ValueError,'preview changed'):service.resume({**args,'theme':{**self.theme,'margin_mm':24},'preview_sha256':preview['preview_sha256'],'confirmed':True},freeze=True)

    def test_share_api_rejects_duplicate_keys_credentials_and_bad_source_without_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            service=WebService(Path(folder)/'jobs.db');before=service.store.path.read_bytes()
            self.assertEqual(service.resume_theme({'source':theme_bytes(self.theme).decode()})['theme'],self.theme)
            for value in ({'theme':{**self.theme,'api_key':'NO'}},{'theme':self.theme,'source':'{}'},{'source':'{"format":"a","format":"b"}'}):
                with self.assertRaises(ValueError):service.resume_theme(value)
            self.assertEqual(before,service.store.path.read_bytes())
