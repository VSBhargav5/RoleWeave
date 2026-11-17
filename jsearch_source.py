"""Versioned JSearch cursor observations with original response-byte evidence."""
import base64
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.parse import urlencode

from network_io import json_object
from roleweave import text
from source_links import source_link

FORMAT='roleweave-jsearch-v5-source-v1'
HOST='api.openwebninja.com'
SOURCE_URL='https://www.openwebninja.com/api/jsearch'
RAW_LIMIT=4*1024*1024
SNAPSHOT_LIMIT=6*1024*1024


def filters(data):
    if not isinstance(data,dict) or set(data)!={'query','location','country','remote','cursor','page'}:raise ValueError('Unsupported JSearch filters')
    if not isinstance(data['query'],str) or not 2<=len(data['query'].strip())<=160:raise ValueError('Enter a role or skill between2 and160 characters')
    if not isinstance(data['location'],str) or len(data['location'])>100:raise ValueError('Location exceeds100 characters')
    if not isinstance(data['country'],str) or not re.fullmatch('[A-Za-z]{2}',data['country']):raise ValueError('Choose a country for JSearch; the provider otherwise defaults to US')
    if type(data['remote']) is not bool or type(data['page']) is not int or not 1<=data['page']<=50:raise ValueError('Invalid JSearch remote filter or page')
    if not isinstance(data['cursor'],str) or len(data['cursor'])>4096 or any(ord(c)<33 or ord(c)>126 for c in data['cursor']):raise ValueError('Unsupported JSearch cursor')
    if bool(data['cursor'])!=(data['page']>1):raise ValueError('JSearch cursor and displayed page disagree')
    for key in ('query','location'):
        value=data[key];value.encode('utf-8')
        if any(ord(c)<32 for c in value):raise ValueError('Search terms contain unsupported controls')
    return {'query':data['query'].strip(),'location':data['location'].strip(),'country':data['country'].lower(),
            'remote':data['remote'],'cursor':data['cursor'],'page':data['page']}


def path(data):
    f=filters(data);query=f['query']+(' in '+f['location'] if f['location'] else '')
    params={'query':query,'country':f['country'],'num_pages':1,'work_from_home':'true' if f['remote'] else 'false'}
    if f['cursor']:params['cursor']=f['cursor']
    return '/jsearch/search-v2?'+urlencode(params)


def capture(raw,data,*,synthetic=False,observed_at=None):
    f=filters(data)
    if not isinstance(raw,bytes) or len(raw)>RAW_LIMIT:raise ValueError('JSearch response exceeds4MiB')
    if type(synthetic) is not bool:raise ValueError('Invalid source practice marker')
    record={'format':FORMAT,'filters':f,'synthetic':synthetic,
            'observed_at':observed_at or datetime.now(timezone.utc).isoformat(),
            'response_sha256':hashlib.sha256(raw).hexdigest(),'response_base64':base64.b64encode(raw).decode()}
    snapshot=json.dumps(record,ensure_ascii=True,indent=2).encode();parse_source(snapshot);return snapshot


def label(value,name,limit,fallback):
    if value is None or value=='':return fallback
    if not isinstance(value,str) or len(value)>limit or not value.strip():raise ValueError('Unsupported '+name)
    value.encode('utf-8')
    if any(ord(c)<32 for c in value):raise ValueError('Unsupported controls in '+name)
    return value


def parse_source(snapshot):
    if not isinstance(snapshot,bytes) or len(snapshot)>SNAPSHOT_LIMIT:raise ValueError('JSearch evidence snapshot exceeds6MiB')
    record=json_object(snapshot)
    if not isinstance(record,dict) or set(record)!={'format','filters','synthetic','observed_at','response_sha256','response_base64'} or record['format']!=FORMAT or type(record['synthetic']) is not bool:raise ValueError('Unsupported JSearch evidence snapshot')
    f=filters(record['filters'])
    if f!=record['filters']:raise ValueError('JSearch snapshot filters are not canonical')
    if not isinstance(record['observed_at'],str) or len(record['observed_at'])>100 or datetime.fromisoformat(record['observed_at']).utcoffset() is None:raise ValueError('Observation time requires timezone')
    if not isinstance(record['response_base64'],str) or len(record['response_base64'])>5600000:raise ValueError('Original response exceeds its evidence limit')
    try:raw=base64.b64decode(record['response_base64'],validate=True)
    except (ValueError,TypeError):raise ValueError('Invalid original response encoding') from None
    if len(raw)>RAW_LIMIT or hashlib.sha256(raw).hexdigest()!=record['response_sha256']:raise ValueError('Original JSearch response fingerprint differs')
    data=json_object(raw)
    if not isinstance(data,dict) or data.get('status')!='OK' or not isinstance(data.get('data'),dict) or not isinstance(data['data'].get('jobs'),list) or len(data['data']['jobs'])>10:raise ValueError('Unsupported JSearch cursor response; expected status OK and data.jobs of at most10')
    cursor=data['data'].get('cursor')
    if cursor is None:cursor=''
    if not isinstance(cursor,str) or len(cursor)>4096 or any(ord(c)<33 or ord(c)>126 for c in cursor):raise ValueError('Unsupported next-page cursor')
    if cursor and cursor==f['cursor']:raise ValueError('JSearch repeated its incoming cursor; no page accepted')
    digest=hashlib.sha256(snapshot).hexdigest();source='Synthetic JSearch fixture' if record['synthetic'] else 'JSearch (OpenWeb Ninja v5)'
    jobs=[];excluded=[];seen=set()
    for index,row in enumerate(data['data']['jobs'],1):
        try:
            if not isinstance(row,dict):raise ValueError('Unsupported job record')
            raw_id=text(row.get('job_id'),'Provider job identity')
            if len(raw_id)>10000:raise ValueError('Provider job identity exceeds10000 characters')
            identifier='jsearch:'+hashlib.sha256(raw_id.encode()).hexdigest()
            if identifier in seen:raise ValueError('Duplicate provider job identity')
            seen.add(identifier)
            title=text(row.get('job_title'),'Job title');company=text(row.get('employer_name'),'Employer label');description=text(row.get('job_description'),'Returned description')
            if len(title)>500 or len(company)>500:raise ValueError('Job metadata exceeds500 characters')
            country=row.get('job_country')
            if not isinstance(country,str) or country.lower()!=f['country']:raise ValueError('Provider country label is missing or differs from requested country')
            remote=row.get('job_is_remote')
            if remote is not None and type(remote) is not bool:raise ValueError('Unsupported provider remote label')
            if f['remote'] and remote is not True:raise ValueError('Provider record does not satisfy the requested remote label')
            location=label(row.get('job_location'),'location label',1000,'Location not stated')
            work='Remote (provider label; verify restrictions)' if remote is True else 'Not marked remote by provider' if remote is False else 'Not stated'
            url=source_link(row.get('job_apply_link'))
            if len(url)>2000:raise ValueError('Application URL exceeds2000 characters')
            posted=label(row.get('job_posted_at_datetime_utc'),'posting-time label',100,'') or label(row.get('job_posted_at'),'posting-time label',100,'Not stated')
            posting='Source observation: JSearch (OpenWeb Ninja)\nLocation label: '+location+'\nWork-mode label: '+work+'\n\nReturned description:\n'+description
            if len(posting)>50000:raise ValueError('Posting and source labels exceed50000 characters')
            jobs.append({'id':identifier,'title':title,'company':company,'posting':posting,'url':url,'location':location,'work_mode':work,'posted_at':posted,
                         'source':source,'source_url':SOURCE_URL,'source_sha256':digest,'observed_at':record['observed_at']})
        except (ValueError,TypeError,UnicodeError) as exc:excluded.append({'row':index,'reason':str(exc)})
    return {'jobs':jobs,'excluded':excluded,'total':None,'observed_at':record['observed_at'],'source':source,'source_url':SOURCE_URL,
            'source_sha256':digest,'response_sha256':record['response_sha256'],'provider_contract':FORMAT,'filters':f,
            'page':{'offset':(f['page']-1)*10,'page_number':f['page'],'returned':len(data['data']['jobs']),'has_next':bool(cursor) and f['page']<50,'next_cursor':cursor},
            'notice':('Synthetic fixture; no provider contacted. ' if record['synthetic'] else 'One JSearch cursor-page observation; provider credits/terms apply. ')+
                     'Country and remote labels are not eligibility or sponsorship checks. Coverage, freshness and direct-employer destination are not guaranteed.'}
