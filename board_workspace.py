"""Ephemeral browser observation sessions for the existing public-board adapters."""
import hashlib
import json
import re
import threading
import time
from uuid import uuid4
from discovery_archive import archive_bytes, parse_archive, MAX_ARCHIVE_BYTES
from provider_boards import source_endpoint, fetch_source, parse_source
from discovery import discovered_snapshot
from roleweave import MARKETS, review_snapshot
from safe_export import publish_bytes

PREFIX='RoleWeave board observation v1\n\n'


def read_bounded(path,limit):
    with path.open('rb') as source:payload=source.read(limit+1)
    if len(payload)>limit:raise ValueError('Existing board evidence exceeds its size limit; original preserved')
    return payload


def imported_snapshot(row,market):
    data=json.loads(discovered_snapshot(row,market));data['posting']=PREFIX+data['posting']
    payload=json.dumps(data,ensure_ascii=True).encode();review_snapshot(payload);return payload


def parse_receipt(payload):
    from career_profile import unique_json
    if not isinstance(payload,bytes) or len(payload)>16384:raise ValueError('Board import receipt exceeds16KiB')
    data=json.loads(payload,object_pairs_hook=unique_json)
    if not isinstance(data,dict) or set(data)!={'format','job_id','input_sha256','archive_sha256','row_id'} or data['format']!='roleweave-board-import-v1':raise ValueError('Invalid board import receipt')
    if not isinstance(data['job_id'],str) or not re.fullmatch('[a-f0-9-]{36}',data['job_id']):raise ValueError('Invalid board receipt review ID')
    for key in ('input_sha256','archive_sha256'):
        if not isinstance(data[key],str) or not re.fullmatch('[a-f0-9]{64}',data[key]):raise ValueError('Invalid board receipt fingerprint')
    if not isinstance(data['row_id'],str) or not 1<=len(data['row_id'])<=2000:raise ValueError('Invalid board receipt row ID')
    return data


def verify_imports(store,parts):
    archives={}
    receipts={}
    for path,raw in parts.items():
        if path.startswith('web-artifacts/board-imports/'):
            receipt=parse_receipt(raw)
            if path!='web-artifacts/board-imports/'+receipt['job_id']+'.json':raise ValueError('Board receipt filename differs')
            receipts[receipt['job_id']]=receipt
    for job in store.list_jobs():
        item=store.load(job['id']);posting=json.loads(item['snapshot'])['posting']
        if not posting.startswith(PREFIX) and item['id'] not in receipts:continue
        receipt=receipts.pop(item['id'],None)
        if receipt is None or receipt['input_sha256']!=item['input_sha256']:raise ValueError('Board import receipt missing or changed')
        digest=receipt['archive_sha256'];raw=parts.get('web-artifacts/board-observations/'+digest+'.json')
        if raw is None or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Board import source evidence missing or changed')
        if digest not in archives:archives[digest]=parse_archive(raw)
        candidates=[row for row in archives[digest]['jobs'] if str(row['id'])==receipt['row_id'] and row['title']==item['title'] and row['url']==item['source_url']]
        if not any(json.loads(imported_snapshot(row,item['market']))['posting']==posting for row in candidates):raise ValueError('Saved board posting differs from original observation')
    if receipts:raise ValueError('Board receipt references a missing saved review')


class BoardWorkspace:
    def __init__(self,store,demo=False):
        self.store=store;self.demo=demo;self.entries={};self.lock=threading.RLock()

    def entry(self,identifier):
        if not isinstance(identifier,str) or identifier not in self.entries:raise ValueError('Board observation unavailable; fetch or replay again')
        entry=self.entries[identifier]
        if time.monotonic()-entry['at']>=1200:raise ValueError('Board observation expired; fetch or replay again')
        return entry

    def reserve(self,provider,token):
        source_endpoint(provider,token)
        with self.lock:
            self.entries={k:v for k,v in self.entries.items() if time.monotonic()-v['at']<1200 or (v.get('thread') and v['thread'].is_alive())}
            if any(e['status']=='loading' or (e.get('thread') and e['thread'].is_alive()) for e in self.entries.values()):raise ValueError('Wait for the previous board request to finish/cancel')
            if len(self.entries)>=3:raise ValueError('Keep at most three observations; close one before fetching/replaying another')
            identifier=uuid4().hex;entry={'id':identifier,'at':time.monotonic(),'provider':provider,'token':token,'status':'loading','cancel':threading.Event()}
            self.entries[identifier]=entry;return entry

    def start(self,provider,token,confirmed):
        if confirmed is not True:raise ValueError('Explicitly authorize one public board GET')
        entry=self.reserve(provider,token)
        def work():
            try:
                if self.demo:
                    record={'id':'synthetic-board-job','text':'Synthetic board Data Engineer','hostedUrl':'https://example.invalid/board/job','categories':{'location':'Remote, eligibility not verified'},'descriptionPlain':'Python and SQL required. Synthetic practice only, not a live vacancy.'}
                    if provider in ('lever','lever-eu'):raw=json.dumps([record]).encode()
                    elif provider=='ashby':raw=json.dumps({'apiVersion':'1','jobs':[{'title':record['text'],'jobUrl':record['hostedUrl'],'location':'Synthetic location','isListed':True,'isRemote':True,'descriptionPlain':record['descriptionPlain'],'publishedAt':'2026-11-16T00:00:00Z'}]}).encode()
                    else:raw=json.dumps({'jobs':[{'id':1,'internal_job_id':1,'title':record['text'],'absolute_url':record['hostedUrl'],'updated_at':'2026-11-16T00:00:00Z','location':{'name':'Synthetic location'},'content':'<p>'+record['descriptionPlain']+'</p>'}],'meta':{'total':1}}).encode()
                    feed=parse_source(raw,provider,token)
                else:feed=fetch_source(provider,token,entry['cancel'])
                payload=archive_bytes(feed)
                with self.lock:
                    if not entry['cancel'].is_set():entry.update(status='ready',feed=feed,archive=payload,sha256=hashlib.sha256(payload).hexdigest())
            except Exception:
                with self.lock:
                    if not entry['cancel'].is_set():entry.update(status='failed',error='Board fetch failed or exceeded its contract. No partial result or application was imported. Check the provider/token and retry explicitly.')
        entry['thread']=threading.Thread(target=work,daemon=True);entry['thread'].start();return {'id':entry['id']}

    def replay(self,payload):
        feed=parse_archive(payload)
        with self.lock:
            entry=self.reserve(feed['provider'],feed['token'])
            entry.update(status='ready',feed=feed,archive=payload,sha256=hashlib.sha256(payload).hexdigest(),replayed=True)
            return {'id':entry['id']}

    def listing(self):
        with self.lock:
            return {'items':[{'id':e['id'],'provider':e['provider'],'token':e['token'],'status':e['status'],'expired':time.monotonic()-e['at']>=1200,
                             'count':len(e.get('feed',{}).get('jobs',[])),'observed_at':e.get('feed',{}).get('fetched_at',''),'sha256':e.get('sha256',''),'error':e.get('error',''),'replayed':e.get('replayed',False)} for e in self.entries.values()]}

    def ready(self,identifier):
        entry=self.entry(identifier)
        if entry['status']!='ready':raise ValueError('Board observation is not ready')
        return entry

    def page(self,identifier,query='',exclude='',descriptions=False,offset=0):
        if not isinstance(query,str) or not isinstance(exclude,str) or len(query)>200 or len(exclude)>200 or type(descriptions) is not bool or type(offset) is not int or offset<0 or offset%20:raise ValueError('Invalid local board filters/page')
        with self.lock:
            entry=self.ready(identifier);rows=[]
            for row in entry['feed']['jobs']:
                text=(row['title']+' '+row['location']+(' '+row['posting'] if descriptions else '')).casefold()
                if all(word.casefold() in text for word in query.split()) and (not exclude or exclude.casefold() not in text):rows.append(row)
            return {'id':identifier,'total':len(rows),'offset':offset,'items':[{k:str(row[k]) for k in ('id','title','url','location','updated_at')} for row in rows[offset:offset+20]],'has_next':offset+20<len(rows)}

    def row(self,identifier,row_id):
        with self.lock:
            entry=self.ready(identifier);row=next((r for r in entry['feed']['jobs'] if str(r['id'])==row_id),None)
            if row is None:raise ValueError('Observed posting unavailable')
            return dict(row)

    def close(self,identifier):
        with self.lock:
            if not isinstance(identifier,str) or identifier not in self.entries:raise ValueError('Observation unavailable')
            entry=self.entries[identifier];entry['cancel'].set();entry['status']='cancelled';entry.pop('feed',None);entry.pop('archive',None)
            if not (entry.get('thread') and entry['thread'].is_alive()):self.entries.pop(identifier)
        return self.listing()

    def import_row(self,identifier,row_id,company,market,digest,confirmed):
        if confirmed is not True:raise ValueError('Review employer identity, posting and market before saving')
        if not isinstance(company,str) or not company.strip() or len(company)>200 or any(ord(c)<32 for c in company):raise ValueError('Enter your checked employer label')
        if not isinstance(market,str) or market not in MARKETS:raise ValueError('Choose an application market explicitly')
        with self.lock:
            entry=self.ready(identifier)
            if entry['sha256']!=digest:raise ValueError('Board source changed; review again')
            row=self.row(identifier,row_id);snapshot=imported_snapshot(row,market)
            directory=self.store.path.parent/'web-artifacts'/'board-observations'
            from workspace_bundle import no_link
            no_link(directory.parent);no_link(directory);directory.mkdir(parents=True,exist_ok=True);path=directory/(digest+'.json');no_link(path)
            if path.exists():
                if read_bounded(path,MAX_ARCHIVE_BYTES)!=entry['archive']:raise ValueError('Existing board evidence differs; preserved without overwrite')
            else:publish_bytes(path,entry['archive'])
            job_id=None
            for old in self.store.list_jobs():
                if old['title']==row['title'] and old['company']==company and old['source_url']==row['url'] and old['market']==market and self.store.load(old['id'])['snapshot']==snapshot:job_id=old['id'];break
            existing=job_id is not None
            if job_id is None:job_id=self.store.save(snapshot,row['title'],company,row['url'])
            receipts=directory.parent/'board-imports';no_link(receipts);receipts.mkdir(exist_ok=True);receipt_path=receipts/(job_id+'.json');no_link(receipt_path)
            if receipt_path.exists():
                receipt=parse_receipt(read_bounded(receipt_path,16384))
                if receipt['job_id']!=job_id or receipt['input_sha256']!=self.store.load(job_id)['input_sha256']:raise ValueError('Existing board receipt differs; original preserved')
                original=directory/(receipt['archive_sha256']+'.json');no_link(original)
                original_bytes=read_bounded(original,MAX_ARCHIVE_BYTES)
                if hashlib.sha256(original_bytes).hexdigest()!=receipt['archive_sha256']:raise ValueError('Existing board evidence differs; original preserved')
                original_feed=parse_archive(original_bytes)
                if not any(str(r['id'])==receipt['row_id'] and imported_snapshot(r,market)==snapshot for r in original_feed['jobs']):raise ValueError('Existing receipt no longer matches original observation')
            else:
                receipt={'format':'roleweave-board-import-v1','job_id':job_id,'input_sha256':self.store.load(job_id)['input_sha256'],'archive_sha256':digest,'row_id':str(row['id'])}
                publish_bytes(receipt_path,json.dumps(receipt,sort_keys=True).encode())
            return {'id':job_id,'already_saved':existing}

    def inherit_receipt(self,original_id,new_id):
        original=self.store.load(original_id);child=self.store.load(new_id)
        posting=json.loads(original['snapshot'])['posting']
        if not posting.startswith(PREFIX):return
        if json.loads(child['snapshot'])['posting']!=posting or any(child[k]!=original[k] for k in ('title','company','source_url','market')):raise ValueError('Derived board review must preserve its exact posting identity')
        from workspace_bundle import no_link
        root=self.store.path.parent/'web-artifacts';receipts=root/'board-imports';sources=root/'board-observations'
        for path in (root,receipts,sources,receipts/(original_id+'.json')):no_link(path)
        receipt=parse_receipt(read_bounded(receipts/(original_id+'.json'),16384))
        if receipt['job_id']!=original_id or receipt['input_sha256']!=original['input_sha256']:raise ValueError('Original board receipt changed')
        source=sources/(receipt['archive_sha256']+'.json');no_link(source);raw=read_bounded(source,MAX_ARCHIVE_BYTES)
        if hashlib.sha256(raw).hexdigest()!=receipt['archive_sha256']:raise ValueError('Original board evidence changed')
        feed=parse_archive(raw)
        if not any(str(row['id'])==receipt['row_id'] and json.loads(imported_snapshot(row,original['market']))['posting']==posting for row in feed['jobs']):raise ValueError('Original board evidence differs')
        record=dict(receipt,job_id=new_id,input_sha256=child['input_sha256']);payload=json.dumps(record,sort_keys=True).encode();parse_receipt(payload)
        destination=receipts/(new_id+'.json');no_link(destination)
        if destination.exists():
            if parse_receipt(read_bounded(destination,16384))!=record:raise ValueError('Derived board receipt differs; original preserved')
        else:publish_bytes(destination,payload)

    def shutdown(self):
        with self.lock:
            for e in self.entries.values():e['cancel'].set()
