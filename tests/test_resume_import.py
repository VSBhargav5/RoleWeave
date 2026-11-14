from io import BytesIO
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from pypdf import PdfWriter
from reportlab.pdfgen import canvas
from resume_import import extract_text, extract_in_worker, worker, MAX_FILE


def pdf_fixture():
    stream=BytesIO();pdf=canvas.Canvas(stream)
    pdf.drawString(60,760,'Synthetic Candidate')
    pdf.drawString(60,735,'Built a Python reconciliation project.')
    pdf.save();return stream.getvalue()


def docx_fixture(xml):
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:archive.writestr('word/document.xml',xml)
    return stream.getvalue()


class ResumeImportTests(unittest.TestCase):
    def test_txt_bom_newlines_and_original_hash(self):
        import hashlib
        data=b'\xef\xbb\xbfSynthetic Candidate\r\nBuilt a Python project.\rSQL practice'
        result=extract_text(data,'resume.txt')
        self.assertEqual(result['blocks'][1],{'id':'2','text':'Built a Python project.'})
        self.assertEqual(result['sha256'],hashlib.sha256(data).hexdigest())

    def test_pdf_and_docx_selectable_text_without_inferred_fields(self):
        pdf=extract_text(pdf_fixture(),'resume.pdf')
        self.assertIn('Built a Python reconciliation project.',pdf['text'])
        self.assertEqual(set(pdf),{'text','blocks','sha256'})
        docx=docx_fixture('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Synthetic </w:t></w:r><w:r><w:t>Candidate</w:t></w:r></w:p><w:p><w:r><w:t>Python project</w:t></w:r></w:p></w:body></w:document>')
        self.assertEqual(extract_text(docx,'resume.docx')['text'],'Synthetic Candidate\nPython project')

    def test_scanned_encrypted_oversized_and_unsupported_inputs_refused(self):
        writer=PdfWriter();writer.add_blank_page(width=100,height=100);blank=BytesIO();writer.write(blank)
        with self.assertRaisesRegex(ValueError,'No selectable text'):extract_text(blank.getvalue(),'scan.pdf')
        writer.encrypt('synthetic-password');encrypted=BytesIO();writer.write(encrypted)
        with self.assertRaisesRegex(ValueError,'unencrypted'):extract_text(encrypted.getvalue(),'protected.pdf')
        for data,name in [(b'x'*(MAX_FILE+1),'large.txt'),(b'x','resume.exe'),(b'x','../resume.txt'),(b'\xff','bad.txt')]:
            with self.assertRaises((ValueError,UnicodeError)):extract_text(data,name)

    def test_docx_declarations_and_large_text_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'XML declarations'):
            extract_text(docx_fixture('<!DOCTYPE a [<!ENTITY x "secret">]><a>&x;</a>'),'resume.docx')
        with self.assertRaises(ValueError):extract_text(b'x'*100001,'resume.txt')

    def test_actual_isolated_worker_parses_pdf_and_does_not_leak_parser_errors(self):
        self.assertIn('Synthetic Candidate',extract_in_worker(pdf_fixture(),'resume.pdf')['text'])
        with self.assertRaisesRegex(ValueError,'Could not extract'):
            extract_in_worker(b'private malformed content','resume.pdf')

    def test_timeout_kills_only_owned_parser_and_is_actionable(self):
        with patch('resume_import.subprocess.run',side_effect=subprocess.TimeoutExpired('worker',20)):
            with self.assertRaisesRegex(ValueError,'timed out'):extract_in_worker(b'Synthetic','resume.txt')

