"""Read-only review-level observations, never inferred employer outcomes."""
from collections import Counter
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
import re
import sqlite3

from applications import STAGES, validate_history
from roleweave import MARKETS


def records(store):
    with closing(sqlite3.connect(store.path)) as db:
        db.row_factory=sqlite3.Row;db.execute('BEGIN')
        jobs=[dict(r) for r in db.execute('SELECT id,title,company,market,captured_at FROM jobs ORDER BY id LIMIT 10001')]
        events=[dict(r) for r in db.execute('SELECT * FROM application_events ORDER BY job_id,revision LIMIT 50001')]
    if len(jobs)>10000 or len(events)>50000:raise ValueError('Insights support at most10000 reviews and50000 history observations; no partial chart shown')
    validate_history(events)
    job_ids={j['id'] for j in jobs}
    if any(e['job_id'] not in job_ids for e in events):raise ValueError('History references a missing review')
    return jobs,events


def insights(store,month=None,market='all',today=None):
    today=today or datetime.now(timezone.utc).date()
    if not isinstance(market,str) or (market!='all' and market not in MARKETS):raise ValueError('Unknown insights market')
    month=today.strftime('%Y-%m') if month is None else month
    if not isinstance(month,str) or not re.fullmatch(r'(19\d{2}|20\d{2}|2100)-(0[1-9]|1[0-2])',month):raise ValueError('Choose a calendar month between1900 and2100')
    year,number=map(int,month.split('-'));first=date(year,number,1)
    jobs,events=records(store);jobs=[j for j in jobs if market=='all' or j['market']==market]
    history={j['id']:[] for j in jobs}
    for event in events:
        if event['job_id'] in history:history[event['job_id']].append(event)
    current=Counter();observed={stage:set() for stage in STAGES};first_applied={};reminders={};overdue=[]
    for job in jobs:
        rows=history[job['id']];latest=rows[-1] if rows else {'stage':'saved','follow_up':''}
        current[latest['stage']]+=1;observed['saved'].add(job['id'])
        for event in rows:
            observed[event['stage']].add(job['id'])
            if event['stage']=='applied' and job['id'] not in first_applied:
                first_applied[job['id']]=datetime.fromisoformat(event['recorded_at']).astimezone(timezone.utc).date()
        due=latest['follow_up']
        if due and latest['stage'] not in ('closed','withdrawn'):
            item={k:job[k] for k in ('id','title','company','market')};item.update(date=due,stage=latest['stage'])
            reminders.setdefault(due,[]).append(item)
            if due<today.isoformat():overdue.append(item)
    monday=today-timedelta(days=today.weekday());weeks=[]
    for index in range(11,-1,-1):
        start=monday-timedelta(weeks=index);end=start+timedelta(days=7)
        weeks.append({'start':start.isoformat(),'end_exclusive':end.isoformat(),'count':sum(start<=day<end and day<=today for day in first_applied.values())})
    grid=first-timedelta(days=first.weekday());days=[]
    for offset in range(42):
        day=grid+timedelta(days=offset)
        days.append({'date':day.isoformat(),'day':day.day,'in_month':day.month==number and day.year==year,'today':day==today,'items':reminders.get(day.isoformat(),[])})
    return {'month':month,'market':market,'today':today.isoformat(),'reviews':len(jobs),
            'current':[{'stage':stage,'count':current[stage]} for stage in STAGES],
            'observed':[{'stage':stage,'count':len(observed[stage])} for stage in STAGES],
            'weeks':weeks,'days':days,'overdue':sorted(overdue,key=lambda i:(i['date'],i['company'],i['id'])),
            'month_due':sum(len(items) for day,items in reminders.items() if day.startswith(month+'-'))}
