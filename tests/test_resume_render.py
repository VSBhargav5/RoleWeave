from io import BytesIO
import unittest

from career_profile import validate_profile
from resume_render import PDF_AVAILABLE, resume_html, resume_pdf, resume_text
from test_profile import synthetic_profile


class ResumeRenderTests(unittest.TestCase):
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
