"""Bounded Hacker News jobs index/item observations, with exact byte replay."""
import base64
from datetime import datetime, timezone
import hashlib
import json
import re
import time

from discovery import plain_posting
from network_io import json_object, request_bytes

HOST = 'hacker-news.firebaseio.com'
FORMAT = 'roleweave-hn-jobs-v1'
ITEM_LIMIT = 128 * 1024
SNAPSHOT_LIMIT = 2 * 1024 * 1024
PAGE_SIZE = 10


def offset_for(token):
    if not isinstance(token, str) or not re.fullmatch(r'jobs-(?:0|[1-9][0-9]?0)', token):
        raise ValueError('Choose a supported startup index batch')
    offset = int(token[5:])
    if offset % PAGE_SIZE or offset > 190 or token != 'jobs-' + str(offset):
        raise ValueError('Choose startup index positions in batches of ten, up to200')
    return offset


def index_ids(raw):
    if not isinstance(raw, bytes) or len(raw) > 4096:
        raise ValueError('Startup index exceeds4KiB')
    values = json_object(raw)
    if not isinstance(values, list) or len(values) > 200 or any(type(v) is not int or not 0 < v < 10**12 for v in values) or len(set(values)) != len(values):
        raise ValueError('Unsupported Hacker News job index')
    return values


def encoded(raw):
    return dict(sha256=hashlib.sha256(raw).hexdigest(), base64=base64.b64encode(raw).decode('ascii'))


def decoded(record, limit):
    if not isinstance(record, dict) or set(record) != {'sha256', 'base64'} or not isinstance(record['base64'], str) or len(record['base64']) > (limit + 2) // 3 * 4:
        raise ValueError('Unsupported startup byte evidence')
    try:
        raw = base64.b64decode(record['base64'], validate=True)
    except (ValueError, TypeError):
        raise ValueError('Invalid startup byte encoding') from None
    if len(raw) > limit or hashlib.sha256(raw).hexdigest() != record['sha256']:
        raise ValueError('Startup original-byte fingerprint differs')
    return raw


def snapshot(index_raw, items, token, synthetic=False):
    raw = json.dumps(dict(format=FORMAT, token=token, synthetic=synthetic, index=encoded(index_raw),
                          items=[dict(id=identifier, response=encoded(body)) for identifier, body in items]), ensure_ascii=True).encode()
    parse_snapshot(raw, token)
    return raw


def fetch_snapshot(token, cancel=None):
    offset = offset_for(token)
    deadline = time.monotonic() + 90
    index_raw = request_bytes(HOST, '/v0/jobstories.json', cancel=cancel, limit=4096, deadline=deadline)
    identifiers = index_ids(index_raw)
    if offset and offset >= len(identifiers):
        raise ValueError('That index batch is not present in this observation')
    items = []
    for identifier in identifiers[offset:offset + PAGE_SIZE]:
        body = request_bytes(HOST, '/v0/item/' + str(identifier) + '.json', cancel=cancel, limit=ITEM_LIMIT, deadline=deadline)
        items.append((identifier, body))
    return snapshot(index_raw, items, token)


def parse_snapshot(raw, token):
    offset = offset_for(token)
    if not isinstance(raw, bytes) or len(raw) > SNAPSHOT_LIMIT:
        raise ValueError('Startup source snapshot exceeds2MiB')
    data = json_object(raw)
    if not isinstance(data, dict) or set(data) != {'format','token','synthetic','index','items'} or data['format'] != FORMAT or data['token'] != token or type(data['synthetic']) is not bool:
        raise ValueError('Unsupported startup observation contract')
    ids = index_ids(decoded(data['index'], 4096))
    if offset and offset >= len(ids):
        raise ValueError('Startup index batch is absent')
    selected = ids[offset:offset + PAGE_SIZE]
    if not isinstance(data['items'], list) or len(data['items']) != len(selected):
        raise ValueError('Startup observation is missing requested items')
    rows, excluded = [], []
    for expected, entry in zip(selected, data['items']):
        if not isinstance(entry, dict) or set(entry) != {'id','response'} or type(entry['id']) is not int or entry['id'] != expected:
            raise ValueError('Startup item order/identity differs from the captured index')
        body = decoded(entry['response'], ITEM_LIMIT)
        record = json_object(body)
        try:
            if not isinstance(record, dict) or type(record.get('id')) is not int or record['id'] != expected:
                raise ValueError('Item unavailable or identity changed')
            if any(key in record and type(record[key]) is not bool for key in ('deleted','dead')):
                raise ValueError('Unsupported item status')
            if record.get('deleted') or record.get('dead'):
                raise ValueError('Deleted or dead source item')
            if record.get('type') != 'job':
                raise ValueError('Source item is not a job notice')
            title_raw = record.get('title')
            if not isinstance(title_raw, str) or not title_raw.strip() or len(title_raw) > 2000:
                raise ValueError('Unsupported startup title')
            title = plain_posting(title_raw)
            if not title or len(title) > 500:
                raise ValueError('Unsupported normalized startup title')
            content = record.get('text', '')
            if not isinstance(content, str) or len(content) > 100000:
                raise ValueError('Unsupported startup notice text')
            destination = record.get('url', '')
            if not isinstance(destination, str) or len(destination) > 2000 or any(ord(c) < 32 for c in destination):
                raise ValueError('Unsupported source destination label')
            created = record.get('time')
            if type(created) is not int or not 0 <= created <= 253402300799:
                raise ValueError('Unsupported item creation time')
            label = datetime.fromtimestamp(created, timezone.utc).isoformat()
            # Mutable votes/extra API fields do not manufacture a new posting revision.
            relevant = {k:record.get(k) for k in ('id','title','text','url','time')}
            relevant_sha = hashlib.sha256(json.dumps(relevant,sort_keys=True,ensure_ascii=True).encode()).hexdigest()
            permalink = 'https://news.ycombinator.com/item?id=' + str(expected)
            text = plain_posting(content) or '(No description was returned; review the original source notice.)'
            posting = ('Hacker News job notice observation\nSource: ' + permalink + '\nSource title: ' + title +
                       '\nItem creation time (not verified vacancy date): ' + label + '\nDestination label (not fetched): ' +
                       (destination or 'Not supplied') + '\nRelevant source fields SHA256: ' + relevant_sha +
                       '\nScope: source notice only; full job description, employer identity, eligibility and availability are not verified.\n\n' + text)
            if len(posting) > 50000:
                raise ValueError('Startup notice and source metadata exceed50000 characters; no truncation')
            rows.append(dict(id='hn-' + str(expected), title=title, url=permalink,
                             location='Not normalized; read the notice', updated_at=label, posting=posting))
        except (ValueError, TypeError, OverflowError, OSError):
            excluded.append(dict(id=expected, reason='Unsupported, unavailable, oversized or removed job notice'))
    return dict(provider='hackernews', token=token, jobs=rows, excluded=excluded,
                synthetic=data['synthetic'], index_count=len(ids), index_offset=offset,
                returned=len(selected), has_more_index=offset + PAGE_SIZE < len(ids),
                fetched_at=datetime.now(timezone.utc).isoformat(),
                response_sha256=hashlib.sha256(raw).hexdigest(), source_snapshot=raw)


def synthetic_snapshot(token):
    offset_for(token)
    ids = list(range(900001, 900023))
    return snapshot(json.dumps(ids).encode(),[(i,json.dumps(dict(id=i,type='job',title='Synthetic startup Data Engineer ' + str(i),
                    time=1794873600,text='<p>Python and SQL. Synthetic notice, not a live role.</p>',url='https://example.invalid/startup')).encode())
                    for i in ids[offset_for(token):offset_for(token)+PAGE_SIZE]],token,synthetic=True)
