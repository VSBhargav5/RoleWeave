"""Private, immutable reviewed application drafts bound to exact local sources."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

from ai_tailoring import bounded,FIELDS
from career_profile import unique_json
from resume_render import selected_facts
from safe_export import publish_bytes

LIMIT=65536


def directory(store):
    root=store.path.parent/'web-artifacts';folder=root/'drafts'
    for path in (root,folder):
        if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):raise ValueError('Linked draft paths are unsupported')
    return folder


def draft_snapshot(payload):
    if not isinstance(payload,bytes) or len(payload)>LIMIT:raise ValueError('Application draft exceeds 64 KiB')
    record=json.loads(payload,object_pairs_hook=unique_json)
    keys={'format','job_id','job_sha256','profile_id','profile_sha256','source_profile_id','source_profile_sha256',
          'selected_fact_ids','letter','request_sha256','result_sha256','created_at','user_reviewed'}
    if not isinstance(record,dict) or set(record)!=keys or record['format']!='roleweave-application-draft-v1' or record['user_reviewed'] is not True:
        raise ValueError('Unsupported reviewed application draft')
    for key in ('job_sha256','profile_sha256','source_profile_sha256','request_sha256','result_sha256'):
        if not isinstance(record[key],str) or not re.fullmatch('[a-f0-9]{64}',record[key]):raise ValueError('Invalid application draft fingerprint')
    for key in ('job_id','profile_id','source_profile_id'):bounded(record[key],key,200,False)
    if not isinstance(record['selected_fact_ids'],list) or not 1<=len(record['selected_fact_ids'])<=20 or any(not isinstance(v,str) for v in record['selected_fact_ids']) or len(record['selected_fact_ids'])!=len(set(record['selected_fact_ids'])):
        raise ValueError('Invalid application draft fact selection')
    if not isinstance(record['letter'],dict) or set(record['letter'])-{'letter_intro','letter_closing'}:raise ValueError('Invalid draft letter fields')
    for key,value in record['letter'].items():bounded(value,key,FIELDS[key],False)
    stamp=datetime.fromisoformat(record['created_at'])
    if stamp.utcoffset() is None:raise ValueError('Draft timestamp needs timezone')
    return record,hashlib.sha256(payload).hexdigest()


def bound_profile(store,record):
    profile=store.load_profile(record['profile_id']);source=store.load_profile(record['source_profile_id']);job=store.load(record['job_id'])
    if profile['snapshot_sha256']!=record['profile_sha256'] or source['snapshot_sha256']!=record['source_profile_sha256'] or job['input_sha256']!=record['job_sha256']:
        raise ValueError('Application draft source fingerprint differs')
    selected_facts(profile['profile'],record['selected_fact_ids'])
    return profile


def save_draft(store,record):
    record=dict(record,format='roleweave-application-draft-v1',user_reviewed=True,created_at=datetime.now(timezone.utc).isoformat())
    payload=json.dumps(record,ensure_ascii=True,indent=2).encode();draft_snapshot(payload);bound_profile(store,record)
    folder=directory(store);folder.mkdir(parents=True,exist_ok=True);identifier=uuid4().hex
    publish_bytes(folder/(identifier+'.json'),payload)
    return identifier


def load_draft(store,identifier):
    if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):raise ValueError('Invalid application draft ID')
    path=directory(store)/(identifier+'.json')
    if path.is_symlink():raise ValueError('Linked application draft is unsupported')
    with path.open('rb') as source:payload=source.read(LIMIT+1)
    record,_=draft_snapshot(payload);profile=bound_profile(store,record)
    return {'id':identifier,'job_id':record['job_id'],'profile':{k:profile[k]for k in ('id','snapshot_sha256','profile')},
            'selected_fact_ids':record['selected_fact_ids'],'letter':record['letter'],'created_at':record['created_at']}


def list_drafts(store,job_id):
    folder=directory(store)
    if not folder.exists():return {'items':[],'issues':[]}
    items=[];issues=[]
    for index,path in enumerate(folder.iterdir()):
        if index>=1000:
            issues.append('Application draft listing reached 1000 entries.');break
        if not re.fullmatch(r'[a-f0-9]{32}\.json',path.name):continue
        try:
            draft=load_draft(store,path.stem)
            if draft['job_id']==job_id:items.append({'id':draft['id'],'created_at':draft['created_at'],'profile_id':draft['profile']['id'],'headline':draft['profile']['profile']['headline']})
        except (ValueError,OSError,KeyError,TypeError,RecursionError):issues.append('A saved draft failed verification; its original file was preserved.')
    return {'items':sorted(items,key=lambda x:(x['created_at'],x['id']),reverse=True),'issues':issues}
