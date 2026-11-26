"""One-shot, in-memory AI jobs bound to reviewed request and source versions."""
import hashlib
import json
import threading
import time
from uuid import uuid4

from ai_tailoring import request_payload, propose, reviewed_variant, synthetic_draft, task_result, task_fields, FIELDS, SectionDraftError
import model_providers
from model_preferences import read_settings
from resume_render import selected_facts
from application_draft import save_draft, load_draft
import refinement_history


def fields(data,allowed,required):
    if not isinstance(data,dict) or set(data)-set(allowed) or not set(required)<=set(data):
        raise ValueError('Unsupported or missing tailoring fields')


class TailoringSession:
    def __init__(self,store,demo=False):
        self.demo=demo
        self.store=store;self.entries={};self.lock=threading.RLock()
        self.cooldowns={}

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
        fields(data,('profile_id','profile_sha256','job_id','fact_ids','instruction','previous','retain_history','parent_id','task','base_draft_id'),('profile_id','profile_sha256','job_id','fact_ids','instruction'))
        task=data.get('task');base=None
        if task is not None:task_fields(task)
        if data.get('base_draft_id'):
            base=load_draft(self.store,data['base_draft_id'])
            if base['job_id']!=data['job_id'] or base['profile']['id']!=data['profile_id']:raise ValueError('Continue from the same saved application draft and job')
        retain=data.get('retain_history',False);parent_id=data.get('parent_id','')
        if type(retain) is not bool:raise ValueError('Choose whether to retain conversation history')
        refinement_history.identifier(parent_id,empty=True)
        if retain:refinement_history.check_capacity(self.store)
        if parent_id and (not retain or data.get('previous') is None):raise ValueError('A retained revision needs its prior proposal')
        if parent_id:
            parent=refinement_history.load_turn(self.store,parent_id)
            if parent.get('task')!=task:raise ValueError('Start a new conversation when changing the section task')
            if base is None:base=parent.get('application')
            if refinement_history.verify_chain(parent,lambda i:refinement_history.read_turn(self.store,i))>=refinement_history.MAX_TURNS:
                raise ValueError('Conversation reached50 turns on this path; start a new conversation before sending')
            if parent['profile_id']!=data['profile_id'] or parent['profile_sha256']!=data['profile_sha256'] or parent['job_id']!=data['job_id'] or parent['fact_ids']!=data['fact_ids']:
                raise ValueError('Retained revision sources differ; start a new conversation')
        profile=self.store.load_profile(data['profile_id'])
        if profile['snapshot_sha256']!=data['profile_sha256']:raise ValueError('Profile changed; reload before preview')
        job=self.store.load(data['job_id']);job=dict(job,posting=json.loads(job['snapshot'])['posting'])
        config=read_settings(self.store)['config']
        payload=model_providers.request_payload(request_payload(job,profile['profile'],data['fact_ids'],data['instruction'],data.get('previous'),task),config)
        with self.lock:
            self.entries={k:v for k,v in self.entries.items() if (time.monotonic()-v['at']<600 and v['status']!='cancelled') or (v.get('thread') and v['thread'].is_alive())}
            if len(self.entries)>=5:raise ValueError('Finish existing draft sessions or retry after ten minutes')
            identifier=uuid4().hex;digest=model_providers.request_fingerprint(payload,config)
            self.entries[identifier]={'at':time.monotonic(),'profile':profile,'job':job,'ids':list(data['fact_ids']),
                                      'provider':config,'payload':payload,'sha256':digest,'status':'preview','cancel':threading.Event(),
                                      'instruction':data['instruction'],'previous':data.get('previous'),'retain_history':retain,'parent_id':parent_id,'task':task,'base':base}
        return {'id':identifier,'sha256':digest,'payload':payload.decode(),'model':config['model'],'endpoint':model_providers.destination(config),'provider':model_providers.KINDS[config['kind']],'local':config['kind'] in model_providers.LOCAL,'offline_demo':self.demo,'retain_history':retain}

    def send(self,data):
        fields(data,('id','sha256','key','confirmed'),('id','sha256','key','confirmed'))
        if data['confirmed'] is not True:raise ValueError('Review the exact request and authorize this one send')
        key=data['key']
        with self.lock:
            entry=self._entry(data['id'])
            route=(entry['provider']['kind'],entry['provider']['model'])
            remaining=self.cooldowns.get(route,0)-time.monotonic()
            if remaining>0:raise model_providers.ModelError('cooldown',429,int(remaining)+1)
            if entry['parent_id']:refinement_history.load_turn(self.store,entry['parent_id'])
            model_providers.validate_key(entry['provider'],key,self.demo)
            if entry['status']!='preview' or entry['sha256']!=data['sha256']:raise ValueError('Request preview changed or was already used')
            if any(v.get('thread') and v['thread'].is_alive() for v in self.entries.values()):raise ValueError('Wait for the previous AI request to finish cancelling')
            entry['status']='running'
            thread=threading.Thread(target=self._run,args=(entry,key),daemon=True)
            entry['thread']=thread;thread.start()
        return {'id':data['id'],'status':'running'}

    def _run(self,entry,key):
        try:
            facts=selected_facts(entry['profile']['profile'],entry['ids'])
            if entry.get('task'):
                task=entry['task']
                if self.demo:
                    raw=synthetic_draft(facts)
                    for key in FIELDS:raw[key]['text']=raw[key]['text'][:{'headline':120,'summary':600,'letter_intro':900,'letter_closing':300}[key]]
                    raw['bullets']=[dict(row,text=row['text'][:700]) for row in raw['bullets'][:3]]
                    result=task_result({k:raw[k] for k in (*task_fields(task),'questions')},facts,task)
                else:
                    result=task_result(model_providers.structured_response(model_providers.request_model(entry['provider'],entry['payload'],key,entry['cancel']),entry['provider']),facts,task)
            elif self.demo: result=synthetic_draft(facts)
            elif entry['provider']['kind']=='openai': result=propose(entry['payload'],facts,key,entry['cancel'])
            else: result=model_providers.propose(entry['provider'],entry['payload'],facts,key,entry['cancel'])
            with self.lock:
                if not entry['cancel'].is_set():
                    entry['draft']=result;entry['result_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=True).encode()).hexdigest()
                    if entry['retain_history']:
                        try:entry['history_id']=refinement_history.save_turn(self.store,entry,self.demo)
                        except (OSError,ValueError,KeyError,TypeError,RecursionError):entry['history_warning']='The proposal is available for this session, but local history completion could not be confirmed. A file may exist. Keep a copy before closing; no automatic retry.'
                    entry['status']='completed'
        except Exception as exc:
            with self.lock:
                if not entry['cancel'].is_set():
                    entry['status']='failed'
                    if isinstance(exc,SectionDraftError):exc=model_providers.ModelError('section_'+exc.code)
                    entry['failure']=model_providers.failure_info(exc,'invalid_output' if isinstance(exc,ValueError) else 'internal')
                    if isinstance(exc,model_providers.ModelError) and exc.code=='rate_limited':
                        delay=exc.retry_after or 60
                        entry['failure']=model_providers.failure_info(model_providers.ModelError('rate_limited',exc.http_status,delay))
                        self.cooldowns[(entry['provider']['kind'],entry['provider']['model'])]=time.monotonic()+delay
        finally:
            key=None  # Never kept in entries, results, history or files.

    def status(self,data):
        fields(data,('id',),('id',))
        with self.lock:
            entry=self._entry(data['id']);result={'id':data['id'],'status':entry['status']}
            if entry['status']=='completed':
                result.update(draft=entry['draft'],result_sha256=entry['result_sha256'])
                for key in ('history_id','history_warning'):
                    if key in entry:result[key]=entry[key]
            if entry['status']=='failed':result.update(entry.get('failure',model_providers.failure_info(None)))
            return result

    def history(self,data):
        fields(data,('job_id','offset'),('job_id',))
        return refinement_history.listing(self.store,data['job_id'],data.get('offset',0))

    def remove_history(self,data):
        fields(data,('conversation_id','job_id','confirmed'),('conversation_id','job_id','confirmed'))
        if data['confirmed'] is not True:raise ValueError('Confirm removing this complete local conversation')
        with self.lock:
            if any(v.get('thread') and v['thread'].is_alive() for v in self.entries.values()):raise ValueError('Wait for the current request to finish before removing history')
            return refinement_history.remove_conversation(self.store,data['conversation_id'],data['job_id'])

    def reopen(self,data):
        fields(data,('id','job_id'),('id','job_id'))
        record=refinement_history.load_turn(self.store,data['id'])
        if record['job_id']!=data['job_id']:raise ValueError('This conversation belongs to another exact job review')
        profile,job=refinement_history.bound_sources(self.store,record)
        with self.lock:
            self.entries={k:v for k,v in self.entries.items() if (time.monotonic()-v['at']<600 and v['status']!='cancelled') or (v.get('thread') and v['thread'].is_alive())}
            if len(self.entries)>=5:raise ValueError('Finish existing draft sessions or retry after ten minutes')
            identifier=uuid4().hex
            self.entries[identifier]={'at':time.monotonic(),'profile':profile,'job':job,'ids':record['fact_ids'],
                'provider':record['provider'],'payload':record['payload'].encode(),'sha256':record['request_sha256'],
                'status':'completed','cancel':threading.Event(),'draft':record['draft'],'result_sha256':record['result_sha256'],
                'instruction':record['instruction'],'previous':record['previous'],'retain_history':True,
                'parent_id':record['parent_id'],'history_id':record['id'],'task':record.get('task'),'base':record.get('application')}
        return {'id':identifier,'sha256':record['request_sha256'],'payload':record['payload'],'draft':record['draft'],
            'result_sha256':record['result_sha256'],'history_id':record['id'],'instruction':record['instruction'],
            'profile':{k:profile[k] for k in ('id','snapshot_sha256','profile')},'fact_ids':record['fact_ids'],
            'offline_demo':record['offline_demo'],'provider':record['provider'],'retain_history':True,'task':record.get('task')}

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
            snapshot,letter=reviewed_variant(entry['profile'],entry['job']['id'],data['fact_edits'],data['fields'],entry['sha256'],edit_about=entry.get('task')=='experience')
            profile=entry.get('pending_profile',entry['profile'])
            if 'pending_profile' not in entry and json.loads(snapshot)!=profile['profile']:
                profile=self.store.load_profile(self.store.save_profile(snapshot,activate=False))
            entry['pending_profile']=profile;entry['acceptance_sha256']=acceptance
            selected=[r['id'] for r in data['fact_edits']] or entry['ids']
            if entry.get('task'):
                selected=list(dict.fromkeys([r['id'] for r in data['fact_edits']]+(entry['base']['selected_fact_ids'] if entry.get('base') else
                    [f['id'] for f in profile['profile']['facts'] if f['reviewed']])))[:20]
                letter={**(entry['base']['letter'] if entry.get('base') else {}),**letter}
            draft_id=save_draft(self.store,{'job_id':entry['job']['id'],'job_sha256':entry['job']['input_sha256'],
                'profile_id':profile['id'],'profile_sha256':profile['snapshot_sha256'],
                'source_profile_id':entry['profile']['id'],'source_profile_sha256':entry['profile']['snapshot_sha256'],
                'provider':entry['provider'],'selected_fact_ids':selected,'letter':letter,'request_sha256':entry['sha256'],'result_sha256':entry['result_sha256']})
            entry['status']='accepted'
            result={'draft_id':draft_id,'profile':{k:profile[k] for k in ('id','snapshot_sha256','profile')},
                    'selected_fact_ids':selected,'letter':letter,
                    'job_id':entry['job']['id']}
            entry['accepted_result']=result
            return result

    def shutdown(self):
        with self.lock:
            for entry in self.entries.values():entry['cancel'].set()
