"""Reviewed professional answers, compatible with the browser helper JSON format."""
from contextlib import closing
from datetime import datetime
import hashlib
import json
import re
import sqlite3
from urllib.parse import urlsplit

from career_profile import unique_json

LIMIT = 1024 * 1024
MANUAL = re.compile(r'password|social security|passport|national id|date of birth|\bssn\b|gender|pronoun|\brace\b|ethnic|disabilit|veteran|criminal|convict|sponsor|visa|immigration|authoriz|authoris|citizen|legally|consent|privacy|personal data|data processing|^ai policy|terms|salary|compensation', re.I)


def empty():
    return {'format': 'roleweave-answers-v1', 'answers': []}


def parse(payload):
    if not isinstance(payload, bytes) or len(payload) > LIMIT:
        raise ValueError('Answer library exceeds 1 MiB')
    try:
        bank = json.loads(payload, object_pairs_hook=unique_json)
        if not isinstance(bank, dict) or set(bank) != {'format', 'answers'} or bank['format'] != 'roleweave-answers-v1' or not isinstance(bank['answers'], list) or len(bank['answers']) > 100:
            raise ValueError('Choose a RoleWeave answer library with up to 100 answers')
        ids = set()
        for row in bank['answers']:
            if not isinstance(row, dict) or set(row) != {'id', 'question', 'aliases', 'answer', 'host', 'page', 'updated_at'}:
                raise ValueError('Unsupported answer record')
            for key, limit in (('id', 100), ('question', 500), ('answer', 5000), ('host', 253), ('updated_at', 40)):
                value = row[key]
                if not isinstance(value, str) or not value.strip() or len(value) > limit or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', value):
                    raise ValueError('Unsupported answer value')
            if not re.fullmatch(r'[A-Za-z0-9-]+', row['id']) or row['id'] in ids:
                raise ValueError('Duplicate or invalid answer identity')
            ids.add(row['id'])
            if datetime.fromisoformat(row['updated_at']).utcoffset() is None:
                raise ValueError('Answer date needs a timezone')
            if row['host'] != '*' and not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]*[a-z0-9])?', row['host']):
                raise ValueError('Use an exact site hostname or *')
            if not isinstance(row['page'], str) or len(row['page']) > 4000 or re.search(r'[\x00-\x20]', row['page']):
                raise ValueError('Invalid answer page scope')
            if row['page']:
                u = urlsplit(row['page'])
                if u.hostname != row['host'] or u.username or u.password or not (u.scheme == 'https' or u.scheme == 'http' and u.hostname in ('127.0.0.1', 'localhost')):
                    raise ValueError('Answer page must match its site and use HTTPS')
            aliases = row['aliases']
            if not isinstance(aliases, list) or len(aliases) > 10 or any(not isinstance(v, str) or not v.strip() or len(v) > 500 or re.search(r'[\x00-\x1f]', v) for v in aliases):
                raise ValueError('Use up to 10 question aliases')
            if any(MANUAL.search(v) for v in [row['question'], *aliases]):
                raise ValueError('Legal, sensitive and salary questions stay manual')
        return bank
    except (TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
        raise ValueError('Invalid answer-library JSON') from None


def encoded(bank):
    payload = json.dumps(bank, ensure_ascii=False, sort_keys=True).encode()
    parse(payload)
    return payload


def stored(store):
    with closing(sqlite3.connect(store.path)) as db:
        row = db.execute("SELECT value FROM app_settings WHERE key='answer_library'").fetchone()
    return encoded(parse(row[0].encode())) if row else None


def read(store):
    payload = stored(store) or encoded(empty())
    return {'library': parse(payload), 'sha256': hashlib.sha256(payload).hexdigest()}


def save(store, bank, expected_sha256=None):
    payload = encoded(bank)
    with closing(sqlite3.connect(store.path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute("SELECT value FROM app_settings WHERE key='answer_library'").fetchone()
        current = encoded(parse(row[0].encode())) if row else encoded(empty())
        if expected_sha256 is not None and hashlib.sha256(current).hexdigest() != expected_sha256:
            raise ValueError('Answer library changed; refresh before saving. Your draft was not saved')
        db.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES ('answer_library',?)", (payload.decode(),))
    return read(store)
