"""Typed human-authored career entries; selected facts remain the evidence unit."""
from datetime import date
import re
from source_links import source_link

# name, label, control, required. These definitions also drive the browser form.
TIMELINE=(('started','Started','month',False),('ended','Ended','month',False),('current','Current / ongoing','bool',False))
TITLE=('title','Title / role','text',True)
ORG=('organization','Organization','text',True)
ABOUT=('about','About / context','long',False)
SKILLS=('skills','Skills used','text',False)
URL=('url','HTTPS link','url',False)
SCHEMAS={
 'Experience':(TITLE,ORG,('location','Location','text',False),*TIMELINE,ABOUT,SKILLS),
 'Volunteering':(TITLE,ORG,('location','Location','text',False),*TIMELINE,ABOUT,SKILLS),
 'Projects':(('title','Project','text',True),URL,*TIMELINE,ABOUT,SKILLS),
 'Education':(('title','Degree / course','text',True),('organization','School / institution','text',True),*TIMELINE,ABOUT),
 'Certifications':(('title','Certification','text',True),('organization','Issuer','text',True),('started','Issued','month',False),('ended','Expires','month',False),('credential_id','Credential ID','text',False),URL,ABOUT),
 'Publications':(('title','Publication / citation','text',True),('organization','Publisher / venue','text',False),('started','Published','month',False),URL,ABOUT),
 'References':(('title','Reference name','text',True),('relationship','Relationship','text',False),('organization','Company','text',False),('email','Reference email','email',False),('phone','Reference phone','text',False)),
 'Skills':(('title','Skill','text',True),('group','Skill group','text',False),('level','Self-described level','text',False)),
 'Languages':(('title','Language','text',True),('level','Self-described proficiency','text',False)),
 'Additional':(('heading','Custom section heading','text',False),TITLE,URL,ABOUT),
}
FORMAT='roleweave-career-entry-v1'


def validate_details(details,section):
    if not isinstance(details,dict) or set(details)!={'format','fields'} or details['format']!=FORMAT or section not in SCHEMAS:raise ValueError('Unsupported structured career entry')
    fields=details['fields'];schema=SCHEMAS[section]
    if not isinstance(fields,dict) or set(fields)!={r[0] for r in schema}:raise ValueError('Structured entry fields do not match its section')
    for key,label,kind,required in schema:
        value=fields[key]
        if kind=='bool':
            if type(value) is not bool:raise ValueError(label+' must be boolean')
            continue
        limit=2000 if kind in ('long','url') else 200
        if not isinstance(value,str) or len(value)>limit or (required and not value.strip()):raise ValueError(label+' is missing or exceeds its limit')
        try:value.encode('utf-8')
        except UnicodeError:raise ValueError(label+' contains unsupported Unicode') from None
        if any(ord(c)<32 and (kind!='long' or c not in '\n\r\t') for c in value):raise ValueError(label+' contains unsupported controls')
        if not value:continue
        if kind=='month':
            if not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])',value):raise ValueError(label+' must be YYYY-MM or blank')
            date(int(value[:4]),int(value[5:]),1)
        if kind=='url':source_link(value)
        if kind=='email' and not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',value):raise ValueError('Use a plain reference email address')
    if fields.get('current') and fields.get('ended'):raise ValueError('Ongoing entry must not have an end month')
    if fields.get('started') and fields.get('ended') and fields['ended']<fields['started']:raise ValueError('End month precedes start month')
    return details


def public_context(fact):
    details=fact.get('details')
    if details is None:return None
    validate_details(details,fact['section'])
    return {k:v for k,v in details['fields'].items() if k not in ('email','phone') and v not in ('',False)}


def entry_lines(fact,for_model=False):
    if 'details' not in fact:return []
    d=validate_details(fact['details'],fact['section'])['fields']
    title=d['title'];organization=d.get('organization','')
    lines=[title+(' - '+organization if organization else '')]
    period=' - '.join(v for v in (d.get('started',''), 'Present' if d.get('current') else d.get('ended','')) if v)
    if period:lines.append(period)
    if d.get('location'):lines.append(d['location'])
    if d.get('about'):lines.append(d['about'])
    for key,label in (('skills','Skills'),('group','Group'),('level','Self-described level'),('credential_id','Credential'),('relationship','Relationship'),('url','Link'),('email','Email'),('phone','Phone')):
        if d.get(key) and not (for_model and key in ('email','phone')):lines.append(label+': '+d[key])
    return lines


def fact_text(fact,for_model=False):
    return '\n'.join([*entry_lines(fact,for_model),*([fact['claim']] if fact['claim'] else [])])


def fact_heading(fact):
    if fact['section']=='Additional' and fact.get('details',{}).get('fields',{}).get('heading'):return fact['details']['fields']['heading']
    return fact['section']
