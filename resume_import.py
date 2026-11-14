"""Bounded local resume text extraction; no inferred or automatically reviewed claims."""
import base64
import hashlib
from io import BytesIO
import json
import logging
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from pypdf import PdfReader
from runtime_paths import RESOURCE_ROOT

MAX_FILE = 4 * 1024 * 1024
MAX_TEXT = 100000


class ResumeImportError(ValueError):
    pass


def document_name(name):
    if not isinstance(name, str) or not 1 <= len(name) <= 200 or any(c in name for c in '/\\') or any(ord(c)<32 for c in name):
        raise ResumeImportError('Choose a resume filename without paths or control characters')
    if Path(name).suffix.lower() not in ('.pdf','.docx','.txt'):
        raise ResumeImportError('Choose a text PDF, DOCX or UTF-8 TXT resume')
    return name


def extract_text(payload, name):
    document_name(name)
    if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_FILE:
        raise ResumeImportError('Resume must contain at most 4 MiB')
    suffix = Path(name).suffix.lower()
    if suffix == '.txt':
        text = payload.decode('utf-8-sig')
    elif suffix == '.docx':
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            entries = archive.infolist()
            if len(entries)>500 or len({e.filename for e in entries})!=len(entries):
                raise ResumeImportError('Unsupported DOCX archive structure')
            info = archive.getinfo('word/document.xml')
            if info.file_size>MAX_FILE or info.flag_bits & 1:
                raise ResumeImportError('DOCX document exceeds its limit or is encrypted')
            with archive.open(info) as source:
                xml = source.read(MAX_FILE+1)
            if len(xml)>MAX_FILE or b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
                raise ResumeImportError('Unsupported DOCX XML declarations or size')
            root = ET.fromstring(xml)
            ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            paragraphs=[]
            for p in root.iter(ns+'p'):
                pieces=[]
                for node in p.iter():
                    if node.tag==ns+'t':pieces.append(node.text or '')
                    elif node.tag in (ns+'br',ns+'cr'):pieces.append('\n')
                    elif node.tag==ns+'tab':pieces.append('\t')
                paragraphs.append(''.join(pieces))
            text='\n'.join(paragraphs)
    else:
        reader = PdfReader(BytesIO(payload))
        if reader.is_encrypted:
            raise ResumeImportError('Use an unencrypted local copy of your resume')
        if len(reader.pages)>20:
            raise ResumeImportError('Resume exceeds 20 pages')
        parts=[]
        for page in reader.pages:
            part=page.extract_text() or ''
            if sum(map(len,parts))+len(part)>MAX_TEXT:
                raise ResumeImportError('Extracted resume exceeds 100000 characters')
            parts.append(part)
        text='\n'.join(parts)
    text=text.replace('\r\n','\n').replace('\r','\n').strip()
    if not text:
        raise ResumeImportError('No selectable text found. Scanned PDFs need OCR outside RoleWeave, or use DOCX/TXT')
    if len(text)>MAX_TEXT or any(ord(c)<32 and c not in '\n\t' for c in text):
        raise ResumeImportError('Extracted text exceeds its limit or contains unsupported controls')
    blocks=[line.strip() for line in text.splitlines() if line.strip()]
    if len(blocks)>500 or any(len(line)>10000 for line in blocks):
        raise ResumeImportError('Resume has too many or oversized text blocks; use a shorter text copy')
    return {'text':text,'blocks':[{'id':str(i+1),'text':line} for i,line in enumerate(blocks)],
            'sha256':hashlib.sha256(payload).hexdigest()}


def worker(source, destination):
    # Parser diagnostics can include document content; do not persist/print them.
    logging.disable(logging.CRITICAL)
    try:
        data=json.loads(Path(source).read_bytes())
        payload=base64.b64decode(data['base64'],validate=True)
        result={'ok':True,'result':extract_text(payload,data['name'])}
    except ResumeImportError as exc:
        result={'ok':False,'error':str(exc)}
    except Exception:
        result={'ok':False,'error':'Could not extract this resume. Use a readable PDF, DOCX or UTF-8 TXT copy'}
    Path(destination).write_text(json.dumps(result,ensure_ascii=True),encoding='utf-8')
    return 0


def extract_in_worker(payload, name):
    document_name(name)
    if not isinstance(payload,bytes) or not 0<len(payload)<=MAX_FILE:
        raise ResumeImportError('Resume must contain at most 4 MiB')
    with tempfile.TemporaryDirectory(prefix='roleweave-resume-') as folder:
        source,destination=Path(folder)/'input.json',Path(folder)/'output.json'
        source.write_text(json.dumps({'name':name,'base64':base64.b64encode(payload).decode()}),encoding='utf-8')
        command=([sys.executable] if getattr(sys,'frozen',False) else [sys.executable,str(RESOURCE_ROOT/'desktop.py')])
        command+=['--extract-resume-worker',str(source),str(destination)]
        try:
            subprocess.run(command,check=True,timeout=20,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                           **({'creationflags':subprocess.CREATE_NO_WINDOW} if sys.platform=='win32' else {}))
        except subprocess.TimeoutExpired:
            raise ResumeImportError('Resume extraction timed out. Use a simpler PDF, DOCX or TXT copy') from None
        except (OSError,subprocess.CalledProcessError):
            raise ResumeImportError('The local resume parser could not start or finish') from None
        with destination.open('rb') as stream:raw=stream.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ResumeImportError('Extracted resume response exceeds its limit')
        result=json.loads(raw)
        if result.get('ok') is not True:raise ResumeImportError(result.get('error','Resume extraction failed'))
        return result['result']
