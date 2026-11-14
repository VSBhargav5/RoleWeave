"""One-shot, in-memory AI jobs bound to reviewed request and source versions."""
import hashlib
import json
import threading
import time
from uuid import uuid4

from ai_tailoring import request_payload, propose, reviewed_variant, synthetic_draft, FIELDS
from ai_requirements import MODEL,ENDPOINT
from resume_render import selected_facts
from application_draft import save_draft


def fields(data,allowed,required):
    if not isinstance(data,dict) or set(data)-set(allowed) or not set(required)<=set(data):
        raise ValueError('Unsupported or missing tailoring fields')


class TailoringSession:
    def __init__(self,store,demo=False):
        self.demo=demo
        self.store=store;self.entries={};self.lock=threading.RLock()

    def _entry(self,identifier,check_sources=True):
        if not isinstance(identifier,str) or identifier not in self.entries:raise ValueError('Draft session unavailable; preview again')
        entry=self.entries[identifier]
        if time.monotonic()-entry['at']>=600:raise ValueError('Draft session expired; preview again')
        if check_sources:self._sources(entry)
        return entry

    def _sources(self,entry):
        profile=self.store.load_profile(entry['profile']['id']);job=self.store.load(entry['job']['id'])
        if profile['snapshot_sha256']!=entry['profile']['snapshot_sha256'] or job['input_sha256']!=entry['job']['input_sha256']:
            raise ValueError('Draft sources changed; reload and preview again')

    def preview(self,data):
        fields(data,('profile_id','profile_sha256','job_id','fact_ids','instruction','previous'),('profile_id','profile_sha256','job_id','fact_ids','instruction'))
        profile=self.store.load_profile(data['profile_id'])
        if profile['snapshot_sha256']!=data['profile_sha256']:raise ValueError('Profile changed; reload before preview')
        job=self.store.load(data['job_id']);job=dict(job,posting=json.loads(job['snapshot'])['posting'])
        payload=request_payload(job,profile['profile'],data['fact_ids'],data['instruction'],data.get('previous'))
        with self.lock:
            self.entries={k:v for k,v in self.entries.items() if (time.monotonic()-v['at']<600 and v['status']!='cancelled') or (v.get('thread') and v['thread'].is_alive())}
            if len(self.entries)>=5:raise ValueError('Finish existing draft sessions or retry after ten minutes')
            identifier=uuid4().hex;digest=hashlib.sha256(payload).hexdigest()
            self.entries[identifier]={'at':time.monotonic(),'profile':profile,'job':job,'ids':list(data['fact_ids']),
                                      'payload':payload,'sha256':digest,'status':'preview','cancel':threading.Event()}
        return {'id':identifier,'sha256':digest,'payload':payload.decode(),'model':MODEL,'endpoint':ENDPOINT,'offline_demo':self.demo}

    def send(self,data):
        fields(data,('id','sha256','key','confirmed'),('id','sha256','key','confirmed'))
        if data['confirmed'] is not True:raise ValueError('Review the exact request and authorize this one send')
        key=data['key']
        if not self.demo and (not isinstance(key,str) or not 1<=len(key)<=1000 or not key.isascii() or any(ord(c)<33 or ord(c)>126 for c in key)):
            raise ValueError('Enter a valid one-request API key')
        with self.lock:
            entry=self._entry(data['id'])
            if entry['status']!='preview' or entry['sha256']!=data['sha256']:raise ValueError('Request preview changed or was already used')
            if any(v.get('thread') and v['thread'].is_alive() for v in self.entries.values()):raise ValueError('Wait for the previous AI request to finish cancelling')
            entry['status']='running'
            thread=threading.Thread(target=self._run,args=(entry,key),daemon=True)
            entry['thread']=thread;thread.start()
        return {'id':data['id'],'status':'running'}

    def _run(self,entry,key):
        try:
            facts=selected_facts(entry['profile']['profile'],entry['ids'])
            result=synthetic_draft(facts) if self.demo else propose(entry['payload'],facts,key,entry['cancel'])
            with self.lock:
                if not entry['cancel'].is_set():
                    entry['draft']=result;entry['result_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=True).encode()).hexdigest();entry['status']='completed'
        except Exception:
            with self.lock:
                if not entry['cancel'].is_set():entry['status']='failed'
        finally:
            key=None  # Never kept in entries, results, history or files.

    def status(self,data):
        fields(data,('id',),('id',))
        with self.lock:
            entry=self._entry(data['id']);result={'id':data['id'],'status':entry['status']}
            if entry['status']=='completed':result.update(draft=entry['draft'],result_sha256=entry['result_sha256'])
            if entry['status']=='failed':result['error']='The request failed, was refused or returned an unsupported draft. Nothing was accepted. Review the request before a new attempt.'
            return result

    def cancel(self,data):
        fields(data,('id',),('id',))
        with self.lock:
            entry=self._entry(data['id'],False)
            if entry['status']=='accepted':raise ValueError('This reviewed application version is already saved; cancellation cannot undo it')
            entry['cancel'].set();entry['status']='cancelled';entry.pop('draft',None);entry.pop('result_sha256',None)
        return {'status':'cancelled'}

    def accept(self,data):
        fields(data,('id','result_sha256','fact_edits','fields','confirmed'),('id','result_sha256','fact_edits','fields','confirmed'))
        if data['confirmed'] is not True:raise ValueError('Review the selected wording and confirm its factual accuracy')
        with self.lock:
            entry=self._entry(data['id'])
            acceptance=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=True).encode()).hexdigest()
            if entry['status']=='accepted' and entry.get('acceptance_sha256')==acceptance:return entry['accepted_result']
            if entry.get('acceptance_sha256') and entry['acceptance_sha256']!=acceptance:raise ValueError('A save is already pending; retry the same reviewed wording')
            if entry['status']!='completed' or data['result_sha256']!=entry['result_sha256']:raise ValueError('Draft result changed, expired or was already accepted')
            allowed={row['fact_id'] for row in entry['draft']['bullets']}
            if not isinstance(data['fact_edits'],list) or any(not isinstance(row,dict) or not isinstance(row.get('id'),str) or row['id'] not in allowed for row in data['fact_edits']):
                raise ValueError('Accept only facts in this reviewed proposal')
            if not isinstance(data['fields'],dict) or any(key not in FIELDS or not entry['draft'][key]['text'] for key in data['fields']):
                raise ValueError('Accept only proposed document fields')
            snapshot,letter=reviewed_variant(entry['profile'],entry['job']['id'],data['fact_edits'],data['fields'],entry['sha256'])
            profile=entry.get('pending_profile',entry['profile'])
            if 'pending_profile' not in entry and json.loads(snapshot)!=profile['profile']:
                profile=self.store.load_profile(self.store.save_profile(snapshot,activate=False))
            entry['pending_profile']=profile;entry['acceptance_sha256']=acceptance
            selected=[r['id'] for r in data['fact_edits']] or entry['ids']
            draft_id=save_draft(self.store,{'job_id':entry['job']['id'],'job_sha256':entry['job']['input_sha256'],
                'profile_id':profile['id'],'profile_sha256':profile['snapshot_sha256'],
                'source_profile_id':entry['profile']['id'],'source_profile_sha256':entry['profile']['snapshot_sha256'],
                'selected_fact_ids':selected,'letter':letter,'request_sha256':entry['sha256'],'result_sha256':entry['result_sha256']})
            entry['status']='accepted'
            result={'draft_id':draft_id,'profile':{k:profile[k] for k in ('id','snapshot_sha256','profile')},
                    'selected_fact_ids':[r['id'] for r in data['fact_edits']] or entry['ids'],'letter':letter,
                    'job_id':entry['job']['id']}
            entry['accepted_result']=result
            return result

    def shutdown(self):
        with self.lock:
            for entry in self.entries.values():entry['cancel'].set()
