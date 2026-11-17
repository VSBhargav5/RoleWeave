"""Explicit one-request JSearch credentials and cancellable fixed-host HTTPS."""
import hashlib
import http.client
import json
import threading
import time
from urllib.parse import unquote
from uuid import uuid4

from jsearch_source import HOST, RAW_LIMIT, SOURCE_URL, capture, filters, parse_source, path
from network_io import Cancelled, json_object
from runtime_paths import APP_VERSION


def credential(value):
    if not isinstance(value,str) or not value or len(value)>1000 or not value.isascii() or any(ord(c)<33 or ord(c)>126 for c in value):raise ValueError('Enter one valid JSearch API key without whitespace')


def reject_echo(raw,key):
    # This rejects literal/JSON/URL-encoded echoes, not arbitrary secret transformations.
    stack=[json_object(raw)]
    while stack:
        item=stack.pop()
        if isinstance(item,dict):stack.extend(item.keys());stack.extend(item.values())
        elif isinstance(item,list):stack.extend(item)
        elif isinstance(item,str) and (key in item or key in unquote(item)):raise ValueError('Provider echoed a request credential; response discarded')


def request(data,key,cancel):
    credential(key);public=filters(data)
    if key in json.dumps(public,ensure_ascii=False):raise ValueError('Remove the credential from public search terms')
    connection=None;deadline=time.monotonic()+60
    try:
        if cancel.is_set():raise Cancelled('Cancelled locally')
        connection=http.client.HTTPSConnection(HOST,timeout=5)
        if cancel.is_set():raise Cancelled('Cancelled locally')
        connection.request('GET',path(public),headers={'Accept':'application/json','User-Agent':'RoleWeave/'+APP_VERSION,'x-api-key':key})
        response=connection.getresponse()
        if response.status!=200:raise ValueError('JSearch returned HTTP '+str(response.status)+'; no redirect or retry')
        if response.getheader('Content-Type','').split(';',1)[0].strip().lower()!='application/json':raise ValueError('JSearch did not return JSON')
        parts=[];size=0
        while True:
            if cancel.is_set():raise Cancelled('Cancelled locally')
            if time.monotonic()>deadline:raise ValueError('JSearch exceeded its60-second local deadline')
            chunk=response.read1(min(65536,RAW_LIMIT+1-size))
            if not chunk:break
            parts.append(chunk);size+=len(chunk)
            if size>RAW_LIMIT:raise ValueError('JSearch response exceeds4MiB')
        if getattr(response,'length',None) not in (None,0):raise ValueError('JSearch response ended before its declared length')
        raw=b''.join(parts);reject_echo(raw,key);return raw
    except (OSError,http.client.HTTPException):raise ValueError('JSearch connection failed or timed out; no automatic retry') from None
    finally:
        if connection is not None:connection.close()
        key=None


def fixture(data):
    jobs=[]
    for i in (1,2):jobs.append({'job_id':'synthetic-jsearch-'+str(data['page'])+'-'+str(i),'job_title':'Synthetic JSearch Data Engineer '+str(i),'employer_name':'Synthetic source company',
        'job_description':'Python required. Synthetic provider fixture only; no live opportunity.',
        'job_country':data['country'].upper(),'job_location':data['location'] or 'Synthetic location','job_is_remote':data['remote'],
        'job_apply_link':'https://example.invalid/jsearch/'+str(data['page'])+'/'+str(i),'job_posted_at':'Synthetic fixture'})
    return json.dumps({'status':'OK','data':{'jobs':jobs,'cursor':'synthetic-next-cursor' if data['page']==1 else ''}}).encode()


def require(data,allowed):
    if not isinstance(data,dict) or set(data)!=set(allowed):raise ValueError('Unsupported JSearch request fields')


class JSearchSession:
    def __init__(self,demo=False):self.demo=demo;self.entries={};self.lock=threading.RLock()

    def entry(self,identifier):
        if not isinstance(identifier,str) or identifier not in self.entries or time.monotonic()-self.entries[identifier]['at']>=600:raise ValueError('JSearch preview/observation expired; review a new request')
        return self.entries[identifier]

    def preview(self,data):
        public=filters(data);public_path=path(public);digest=hashlib.sha256(json.dumps({'path':public_path,'filters':public},sort_keys=True).encode()).hexdigest()
        with self.lock:
            self.entries={k:e for k,e in self.entries.items() if (time.monotonic()-e['at']<600 and e['status']!='cancelled') or (e.get('thread') and e['thread'].is_alive())}
            if len(self.entries)>=5:
                completed=[k for k,e in self.entries.items() if e['status'] in ('completed','failed')]
                if not completed:raise ValueError('Finish or cancel another JSearch preview first')
                del self.entries[min(completed,key=lambda k:self.entries[k]['at'])]
            identifier=uuid4().hex;self.entries[identifier]={'at':time.monotonic(),'filters':public,'sha256':digest,'status':'preview','cancel':threading.Event()}
        return {'id':identifier,'sha256':digest,'filters':public,'url':'https://'+HOST+public_path,'offline_demo':self.demo,
                'notice':'One page, up to10 returned records; your provider plan/credits apply. Authentication is added only at send.'}

    def send(self,data):
        require(data,('id','sha256','key','confirmed'))
        if data['confirmed'] is not True:raise ValueError('Review this query and authorize one JSearch request')
        with self.lock:
            e=self.entry(data['id'])
            if not self.demo:credential(data['key'])
            if e['status']!='preview' or e['sha256']!=data['sha256']:raise ValueError('JSearch preview changed or already used')
            if any(v.get('thread') and v['thread'].is_alive() for v in self.entries.values()):raise ValueError('Wait for the earlier JSearch request to finish cancelling')
            e['status']='running';thread=threading.Thread(target=self.run,args=(e,data['key']),daemon=True);e['thread']=thread;thread.start()
        return {'id':data['id'],'status':'running'}

    def run(self,e,key):
        try:
            raw=fixture(e['filters']) if self.demo else request(e['filters'],key,e['cancel'])
            snapshot=capture(raw,e['filters'],synthetic=self.demo);result=parse_source(snapshot)
            with self.lock:
                if not e['cancel'].is_set():e.update(status='completed',snapshot=snapshot,result=result)
        except Exception:
            with self.lock:
                if not e['cancel'].is_set():e['status']='failed'
        finally:key=None

    def status(self,data):
        require(data,('id',))
        with self.lock:
            e=self.entry(data['id']);r={'id':data['id'],'status':e['status']}
            if e['status']=='completed':r['result']=e['result']|{'search_id':data['id']}
            if e['status']=='failed':r['error']='JSearch failed, was refused or returned an unsupported response. Nothing was saved; no automatic retry. Check filters, key and provider quota before a new request.'
            return r

    def cancel(self,data):
        require(data,('id',))
        with self.lock:
            e=self.entry(data['id']);e['cancel'].set();e['status']='cancelled';e.pop('snapshot',None);e.pop('result',None)
        return {'status':'cancelled'}

    def snapshot_for(self,digest):
        with self.lock:
            for e in self.entries.values():
                if e['status']=='completed' and time.monotonic()-e['at']<600 and e['result']['source_sha256']==digest:return e['snapshot']
        return None

    def shutdown(self):
        with self.lock:
            for e in self.entries.values():e['cancel'].set()
