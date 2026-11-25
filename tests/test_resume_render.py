from io import BytesIO
import unittest

from career_profile import validate_profile
from resume_render import PDF_AVAILABLE, resume_html, resume_pdf, resume_text
from test_profile import synthetic_profile


class ResumeRenderTests(unittest.TestCase):
    def test_refined_layout_removes_matching_heading_and_source_markers_only(self):
        from test_career_entries import entry
        from pypdf import PdfReader
        profile=synthetic_profile()
        fact=entry('Experience','source-one',title='Data Engineer',organization='Synthetic Labs',location='Pune',started='2023-07',ended='2024-09',
                   about='Data Engineer | Synthetic Labs | Pune | 2023-07 to 2024-09 — Built Python pipelines; delivered SQL analytics. [source-one]')
        profile['facts']=[fact];profile['summary']='Built reliable\nPython data platforms.'
        old=resume_html(profile,['source-one'],'jake')
        new=resume_html(profile,['source-one'],'jake2').decode()
        self.assertIn('Built reliable Python data platforms.',new)
        self.assertNotIn('[source-one]',new);self.assertNotIn('Engineer | Synthetic Labs',new)
        self.assertIn('Built Python pipelines',new);self.assertIn('delivered SQL analytics.',new)
        self.assertIn('[source-one]',old.decode(),'Earlier frozen layout semantics must remain unchanged')
        pdf=PdfReader(BytesIO(resume_pdf(profile,['source-one'],'jake2')))
        content='\n'.join(p.extract_text() for p in pdf.pages)
        self.assertNotIn('[source-one]',content);self.assertNotIn('Engineer | Synthetic Labs',content)
        self.assertIn('Built Python pipelines',content)
        self.assertEqual(resume_html(profile,['source-one'],'jake'),old)
        self.assertIn('[unknown-note]',resume_html({**profile,'summary':'Keep [unknown-note] intact.'},['source-one'],'jake2').decode())

    def test_jake_structured_headings_bullets_and_all_printable_fields(self):
        from test_career_entries import entry
        from pypdf import PdfReader
        profile=synthetic_profile()
        fact=entry('Experience',title='Data Engineer <reviewed>',organization='Synthetic Labs',
                   started='2023-07',ended='2024-09',location='Bengaluru',
                   about='Built Python pipelines across\nmultiple sources.\n• Added SQL validation.\n• Documented monitoring.',skills='Python, SQL')
        fact['claim']='Reduced manual checks using reviewed automation.'
        profile['facts']=[fact]
        output=resume_html(profile,[fact['id']],'jake').decode()
        self.assertIn('entry-heading',output);self.assertIn('&lt;reviewed&gt;',output)
        self.assertIn('<li>Built Python pipelines across multiple sources.</li>',output)
        self.assertNotIn(fact['source'],output)
        pdf=resume_pdf(profile,[fact['id']],'jake')
        self.assertEqual(pdf,resume_pdf(profile,[fact['id']],'jake'))
        reader=PdfReader(BytesIO(pdf));text='\n'.join(page.extract_text() for page in reader.pages)
        for value in ('Synthetic Labs','Bengaluru','2023-07','2024-09','SQL validation','Python, SQL',fact['claim']):self.assertIn(value,text)
        fact['claim']=('Preserved long accomplishment with concrete reviewed detail. '*55)+'FINAL JAKE END'
        import copy
        profile['facts']=[copy.deepcopy(fact) for _ in range(4)]
        for i,item in enumerate(profile['facts']):item['id']='long-'+str(i)
        long_pdf=PdfReader(BytesIO(resume_pdf(profile,[item['id'] for item in profile['facts']],'jake')))
        self.assertGreater(len(long_pdf.pages),1)
        self.assertIn('FINAL JAKE END','\n'.join(p.extract_text() for p in long_pdf.pages))

    def setUp(self):
        self.profile = synthetic_profile()
        self.selected = ["project-python"]

    def test_html_escapes_content_and_only_renders_selected_reviewed_claims(self):
        self.profile["name"] = '<img src="https://example.invalid/track"> & Candidate'
        output = resume_html(self.profile, self.selected).decode()
        self.assertIn("&lt;img", output)
        self.assertNotIn("<img", output)
        self.assertNotIn("<script", output)
        self.assertIn("default-src 'none'", output)
        self.assertNotIn("Unreviewed draft claim", output)
        self.assertNotIn("Synthetic project exercise, not employment", output)
        self.assertIn(self.profile["facts"][0]["claim"], output)

    def test_unknown_unreviewed_duplicate_and_empty_selections_fail(self):
        for values in ([], ["draft"], ["unknown"], ["project-python"] * 2, [None]):
            with self.assertRaises(ValueError):
                resume_html(self.profile, values)

    def test_plain_preview_preserves_name_and_claim_without_source_notes(self):
        output = resume_text(self.profile, self.selected)
        self.assertIn(self.profile["name"], output)
        self.assertIn(self.profile["facts"][0]["claim"], output)
        self.assertNotIn(self.profile["facts"][0]["source"], output)

    @unittest.skipUnless(PDF_AVAILABLE, "Install requirements.txt for PDF export")
    def test_pdf_is_extractable_and_deterministic(self):
        from pypdf import PdfReader
        self.profile["summary"] = "Human-authored example using Python & SQL."
        first = resume_pdf(self.profile, self.selected)
        self.assertEqual(first, resume_pdf(self.profile, self.selected))
        reader = PdfReader(BytesIO(first))
        self.assertEqual(len(reader.pages), 1)
        contents = reader.pages[0].extract_text()
        self.assertIn("Synthetic Candidate", contents)
        self.assertIn("Python & SQL", contents)
        self.assertIn(self.profile["facts"][0]["claim"], contents)
        self.assertNotIn("Unreviewed draft", contents)

    @unittest.skipUnless(PDF_AVAILABLE, "Install requirements.txt for PDF export")
    def test_unsupported_pdf_glyph_has_explicit_html_fallback(self):
        self.profile["name"] = "తెలుగు candidate"
        with self.assertRaisesRegex(ValueError, "HTML-only"):
            resume_pdf(self.profile, self.selected)
        self.assertIn("తెలుగు", resume_html(self.profile, self.selected).decode())

    @unittest.skipUnless(PDF_AVAILABLE, "Install requirements.txt for PDF export")
    def test_long_claim_splits_across_pages_without_losing_end(self):
        from pypdf import PdfReader
        self.profile["facts"][0]["claim"] = ("Worked on a synthetic data exercise with documented checks. " * 150) + "FINAL CLAIM END"
        reader = PdfReader(BytesIO(resume_pdf(self.profile, self.selected)))
        self.assertGreater(len(reader.pages), 1)
        self.assertIn("FINAL CLAIM END", "\n".join(page.extract_text() for page in reader.pages))
