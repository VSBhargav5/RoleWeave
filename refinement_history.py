"""Opt-in immutable local refinement turns; no credentials or implicit provider calls."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

from ai_tailoring import bounded, validate_draft, task_fields, task_result
from career_profile import unique_json
from model_providers import validate_config, request_fingerprint
from resume_render import selected_facts
from safe_export import publish_bytes

LIMIT=1024*1024
MAX_TURNS=50


def identifier(value,empty=False):
    if not isinstance(value,str) or not ((empty and value=='') or re.fullmatch('[a-f0-9]{32}',value)):
        raise ValueError('Invalid refinement history identity')
    return value


def directory(store):
    root=store.path.parent/'web-artifacts';folder=root/'refinements'
    for path in (root,folder):
        if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):raise ValueError('Linked refinement history paths are unsupported')
    return folder


def check_capacity(store):
    folder=directory(store)
    if folder.exists():
        for index,_path in enumerate(folder.iterdir()):
            if index>=999:raise ValueError('Refinement history reached1000 files; remove a conversation before retaining another')


def snapshot(payload):
    if not isinstance(payload,bytes) or len(payload)>LIMIT:raise ValueError('Refinement turn exceeds1MiB')
    record=json.loads(payload,object_pairs_hook=unique_json)
    keys={'format','id','conversation_id','parent_id','created_at','job_id','job_sha256','profile_id','profile_sha256','fact_ids','instruction','previous','provider','payload','request_sha256','draft','result_sha256','offline_demo'}
    if isinstance(record,dict) and record.get('format')=='roleweave-refinement-turn-v2':
        keys.update(('task','application'));task_fields(record.get('task'))
        application=record.get('application')
        if not isinstance(application,dict) or set(application)!={'selected_fact_ids','letter'}:raise ValueError('Invalid section application context')
        selected=application['selected_fact_ids']
        if not isinstance(selected,list) or not 1<=len(selected)<=20 or any(not isinstance(i,str) for i in selected) or len(selected)!=len(set(selected)):raise ValueError('Invalid section resume selection')
        if not isinstance(application['letter'],dict) or set(application['letter'])-{'letter_intro','letter_closing'}:raise ValueError('Invalid section letter context')
        for key,value in application['letter'].items():bounded(value,key,2500 if key=='letter_intro' else 1000,False)
    if not isinstance(record,dict) or set(record)!=keys or record['format'] not in ('roleweave-refinement-turn-v1','roleweave-refinement-turn-v2'):raise ValueError('Unsupported refinement turn')
    for key in ('id','conversation_id'):identifier(record[key])
    identifier(record['parent_id'],empty=True)
    if record['parent_id']==record['id'] or (not record['parent_id'] and record['id']!=record['conversation_id']):raise ValueError('Invalid refinement conversation root')
    for key in ('job_id','profile_id'):bounded(record[key],key,200,False)
    for key in ('job_sha256','profile_sha256','request_sha256','result_sha256'):
        if not isinstance(record[key],str) or not re.fullmatch('[a-f0-9]{64}',record[key]):raise ValueError('Invalid refinement fingerprint')
    stamp=datetime.fromisoformat(record['created_at'])
    if stamp.utcoffset() is None:raise ValueError('Refinement time requires a timezone')
    if type(record['offline_demo']) is not bool:raise ValueError('Invalid refinement practice marker')
    ids=record['fact_ids']
    if not isinstance(ids,list) or not 1<=len(ids)<=20 or any(not isinstance(i,str) for i in ids) or len(ids)!=len(set(ids)):raise ValueError('Invalid refinement source selection')
    facts=[{'id':i} for i in ids]
    validate_draft(record['draft'],facts)
    if record.get('task'):
        normalized=task_result({k:record['draft'][k] for k in (*task_fields(record['task']),'questions')},facts,record['task'])
        if normalized!=record['draft']:raise ValueError('Section history contains wording outside its task')
    if record['previous'] is not None:validate_draft(record['previous'],facts)
    bounded(record['instruction'],'Refinement instruction',2000,False)
    validate_config(record['provider'])
    if not isinstance(record['payload'],str) or len(record['payload'].encode())>256*1024:raise ValueError('Invalid refinement request bytes')
    if not isinstance(json.loads(record['payload'],object_pairs_hook=unique_json),dict):raise ValueError('Invalid refinement request JSON')
    if request_fingerprint(record['payload'].encode(),record['provider'])!=record['request_sha256']:raise ValueError('Refinement request fingerprint differs')
    if hashlib.sha256(json.dumps(record['draft'],sort_keys=True,ensure_ascii=True).encode()).hexdigest()!=record['result_sha256']:raise ValueError('Refinement proposal fingerprint differs')
    return record


def bound_sources(store,record):
    profile=store.load_profile(record['profile_id']);job=store.load(record['job_id'])
    if profile['snapshot_sha256']!=record['profile_sha256'] or job['input_sha256']!=record['job_sha256']:raise ValueError('Refinement source fingerprint differs')
    selected_facts(profile['profile'],record['fact_ids'])
    if record.get('application'):selected_facts(profile['profile'],record['application']['selected_fact_ids'])
    return profile,dict(job,posting=json.loads(job['snapshot'])['posting'])


def read_turn(store,turn_id):
    path=directory(store)/(identifier(turn_id)+'.json')
    if path.is_symlink():raise ValueError('Linked refinement turn is unsupported')
    with path.open('rb') as source:record=snapshot(source.read(LIMIT+1))
    if record['id']!=turn_id:raise ValueError('Refinement filename and identity differ')
    bound_sources(store,record)
    return record


def verify_chain(record,read):
    seen=set();current=record
    while True:
        if current['id'] in seen or len(seen)>=MAX_TURNS:raise ValueError('Refinement conversation cycle or50-turn limit')
        seen.add(current['id'])
        if not current['parent_id']:break
        parent=read(current['parent_id'])
        if parent.get('task')!=current.get('task'):raise ValueError('Refinement parent section differs')
        for key in ('conversation_id','job_id','job_sha256','profile_id','profile_sha256','fact_ids'):
            if parent[key]!=current[key]:raise ValueError('Refinement parent sources differ')
        current=parent
    if current['id']!=record['conversation_id']:raise ValueError('Refinement root differs')
    return len(seen)


def load_turn(store,turn_id):
    record=read_turn(store,turn_id);verify_chain(record,lambda i:read_turn(store,i));return record


def save_turn(store,entry,offline_demo):
    parent=load_turn(store,entry['parent_id']) if entry['parent_id'] else None
    turn_id=uuid4().hex
    record={'format':'roleweave-refinement-turn-v1','id':turn_id,'conversation_id':parent['conversation_id'] if parent else turn_id,
            'parent_id':entry['parent_id'],'created_at':datetime.now(timezone.utc).isoformat(),
            'job_id':entry['job']['id'],'job_sha256':entry['job']['input_sha256'],
            'profile_id':entry['profile']['id'],'profile_sha256':entry['profile']['snapshot_sha256'],
            'fact_ids':entry['ids'],'instruction':entry['instruction'],'previous':entry['previous'],
            'provider':entry['provider'],'payload':entry['payload'].decode(),'request_sha256':entry['sha256'],
            'draft':entry['draft'],'result_sha256':entry['result_sha256'],'offline_demo':offline_demo}
    if entry.get('task'):
        application=entry.get('base') or {'selected_fact_ids':[f['id'] for f in entry['profile']['profile']['facts'] if f['reviewed']][:20],'letter':{}}
        record.update(format='roleweave-refinement-turn-v2',task=entry['task'],application={k:application[k] for k in ('selected_fact_ids','letter')})
    payload=json.dumps(record,ensure_ascii=False,indent=2).encode();snapshot(payload);bound_sources(store,record)
    verify_chain(record,lambda i:read_turn(store,i))
    folder=directory(store);folder.mkdir(parents=True,exist_ok=True)
    check_capacity(store)
    publish_bytes(folder/(turn_id+'.json'),payload)
    return turn_id


def listing(store,job_id,offset=0):
    store.load(job_id)
    if type(offset) is not int or offset<0 or offset>1000 or offset%20:raise ValueError('Invalid refinement history page')
    folder=directory(store);items=[];issues=[]
    if folder.exists():
        for index,path in enumerate(folder.iterdir()):
            if index>=1000:issues.append('History scan reached1000 files.');break
            try:
                record=load_turn(store,path.stem)
                if record['job_id']==job_id:items.append({k:record[k] for k in ('id','conversation_id','parent_id','created_at','instruction','profile_id','offline_demo')})
            except (OSError,ValueError,KeyError,TypeError,RecursionError):issues.append('A refinement turn failed verification; its original file was preserved.')
    items.sort(key=lambda r:(r['created_at'],r['id']),reverse=True)
    return {'items':items[offset:offset+20],'total':len(items),'offset':offset,'issues':issues}


def verify_bundle(store,parts):
    turns={}
    for name,payload in parts.items():
        if name.startswith('web-artifacts/refinements/'):
            record=snapshot(payload)
            if Path(name).stem!=record['id']:raise ValueError('Refinement filename and identity differ')
            bound_sources(store,record);turns[record['id']]=record
    for record in turns.values():verify_chain(record,lambda i:turns[i])


def remove_conversation(store,conversation_id,job_id):
    root=load_turn(store,identifier(conversation_id))
    if root['parent_id'] or root['job_id']!=job_id:raise ValueError('Conversation belongs to another exact job review')
    paths=[]
    for index,path in enumerate(directory(store).iterdir()):
        if index>=1000:raise ValueError('History exceeds1000 files; deletion was not started')
        record=read_turn(store,path.stem)
        if record['conversation_id']==conversation_id:paths.append(path)
    # Validate the entire selection before any unlink; caller serializes against request completion.
    for path in sorted(paths,key=lambda p:p.stem==conversation_id):path.unlink()
    return {'removed':len(paths)}
