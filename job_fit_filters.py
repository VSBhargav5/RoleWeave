"""Version-one conservative text filters; source observations are never rewritten."""
import re

EXPERIENCE={'any':None,'0-2':(0,2),'3-5':(3,5),'6+':(6,40)}
DEFAULT={'version':1,'experience':'any','residence':'IN','include_unknown':False}
COUNTRIES={'IN':('india',),'CA':('canada',),'US':('united states','usa','u.s.a.','u.s.'),
           'GB':('united kingdom','great britain','uk'),'DE':('germany',),'AU':('australia',),
           'NZ':('new zealand',),'FR':('france',),'NL':('netherlands',),'IE':('ireland',),
           'SG':('singapore',),'JP':('japan',),'BR':('brazil',),'MX':('mexico',),
           'ES':('spain',),'IT':('italy',),'PL':('poland',),'PT':('portugal',),
           'SE':('sweden',),'NO':('norway',),'CH':('switzerland',),'ZA':('south africa',)}
YEARS=re.compile(r'(?<![\d.])(\d{1,2})(?:\s*(?:[-–—]|to)\s*(\d{1,2}))?\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:(?:relevant|professional|commercial|hands.on|industry|practical|related|working|data|software|engineering|development)\s+){0,3}experience\b',re.I)
BEFORE_YEARS=re.compile(r'\b(?:experience(?: required)?|minimum experience)\s*(?::|=|of|is)?\s*(\d{1,2})(?:\s*(?:[-–—]|to)\s*(\d{1,2}))?\s*\+?\s*(?:years?|yrs?)\b',re.I)
RESTRICTION=re.compile(r'(?:open to (?:candidates|applicants) (?:residing|living|based|located|in|from)|(?:candidates|applicants|you) (?:must |are required to |who )?(?:resid\w*|liv\w*|be based|based|located)|must (?:reside|live|be based)|remote (?:position |role )?(?:within|in)|remote[^.;\n]{0,80}?only (?:in|within)|(?:restricted|limited) to)[^.;\n]{0,150}',re.I)


def preferences(value):
    if not isinstance(value,dict):raise ValueError('Unsupported experience/location preferences')
    version=value.get('version')
    if type(version) is not int or version not in (1,2):raise ValueError('Unsupported search-filter version')
    if set(value)!=set(DEFAULT)|({'role_query'} if version==2 else set()):raise ValueError('Unsupported experience/location preferences')
    if version==2 and (not isinstance(value['role_query'],str) or len(value['role_query'])>160):raise ValueError('Unsupported role-title query')
    if not isinstance(value['experience'],str) or value['experience'] not in EXPERIENCE:raise ValueError('Choose an advertised experience band')
    if not isinstance(value['residence'],str) or not re.fullmatch('[A-Z]{2}',value['residence']):raise ValueError('Enter a two-letter remote-residence country')
    if type(value['include_unknown']) is not bool:raise ValueError('Choose whether to show unclear requirements')
    return dict(value)


def role_matches(title,query):
    """Title matching is explicit; body keyword matches are a separate search mode."""
    tokens=lambda text: re.findall(r'[a-z0-9]+',text.casefold())
    wanted=tokens(query);actual=tokens(title)
    if wanted==['data','engineer']:
        return bool(re.search(r'\b(?:data (?:integration |platform |warehouse |analytics )?engineer\w*|analytics engineer\w*|etl (?:developer|engineer)\w*)\b',' '.join(actual)))
    return all(word in actual for word in wanted)


def countries(value, codes=False):
    found={code for code,names in COUNTRIES.items() if any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',value,re.I) for name in names)}
    if codes:
        # CA alone can also mean California; do not certify it as Canada.
        found.update(code for code in ('IN','US','GB','UK','DE','AU','NZ','FR','NL','IE','SG','JP') if re.search(r'(?<![A-Za-z])'+code+r'(?![A-Za-z])',value))
        if 'UK' in found:found.remove('UK');found.add('GB')
    return found


def classify(row,version=1):
    posting=row.get('posting','');location=row.get('location','');title=row.get('title','')
    if version==2:posting=posting.replace('*','')
    # Preferred/bonus requirements do not establish a mandatory minimum.
    required=re.split(r'(?:\*\*|\n|^)(?:preferred(?: skills| qualifications)?|nice.to.have|bonus(?: points)?|desirable)\s*(?:\*\*|:|\n)',posting,flags=re.I)[0]
    matches=[]
    for match in [*YEARS.finditer(required),*BEFORE_YEARS.finditer(required)]:
        low=int(match[1]);high=int(match[2]) if match[2] else low
        left=max(required.rfind('.',max(0,match.start()-100),match.start()),required.rfind('\n',max(0,match.start()-100),match.start()))+1
        ends=[i for i in (required.find('.',match.end(),match.end()+100),required.find('\n',match.end(),match.end()+100)) if i>=0]
        context=required[max(left,match.start()-100):min(min(ends) if ends else len(required),match.end()+100)]
        if re.search(r'\b(?:we have|our company|company has|combined|collective|team with)\b',context,re.I):continue
        if low>40 or high<low or high>40 or re.search(r'(?:preferred|nice.to.have|bonus)',context,re.I):continue
        matches.append((low,high,match.group()))
    alternative=bool(len(matches)>1 and re.search(r'\b(?:bachelor|master|ph\.?d)\w*\b',required,re.I) and re.search(r'\bor\b',required,re.I))
    minimum=None if alternative or not matches else max(m[0] for m in matches)
    if minimum is None and re.search(r'no (?:prior |professional |work )?experience (?:is )?(?:required|necessary)',required,re.I):minimum=0
    quote=next((m[2] for m in matches if m[0]==minimum),'')
    remote='remote' in (row.get('work_mode','')+' '+title+' '+location).lower()
    if re.search(r'\b(?:remote (?:position|role)|work remotely|remote work)\b',posting,re.I):remote=True
    allowed=countries(location,True)
    if remote and countries(title,True):allowed=countries(title,True)
    restrictions=[m.group() for m in RESTRICTION.finditer(posting)]
    explicit=set().union(*(countries(part) for part in restrictions)) if restrictions else set()
    if restrictions:allowed=explicit
    worldwide=bool(re.search(r'^(?:worldwide|anywhere|global)$',location.strip(),re.I) or re.search(r'\b(?:worldwide remote|remote worldwide|work from anywhere|remote[ ,/-]+anywhere|open to candidates worldwide)\b',location+' '+posting,re.I))
    if worldwide and not restrictions:allowed=set()
    if re.search(r'\b(?:not (?:a )?remote|no remote work|remote work is not available)\b',posting,re.I) or any(label in row.get('work_mode','').lower() for label in ('hybrid','not marked remote','not remote')):remote=False
    return {'minimum':minimum,'experience_quote':quote,'remote':remote,'countries':sorted(allowed),
            'worldwide':worldwide and not restrictions,'location_quote':restrictions[0][:200] if explicit else location[:200]}


def decision(info,selection,remote_only=False):
    selection=preferences(selection);unclear=False
    band=EXPERIENCE[selection['experience']]
    if band:
        if info['minimum'] is None:unclear=True
        elif not band[0]<=info['minimum']<=band[1]:return 'excluded','Advertised experience minimum is outside the selected band'
    if remote_only and not info['remote']:return 'excluded','Not advertised as a remote role'
    if info['remote']:
        if info['countries']:
            if selection['residence'] not in info['countries']:return 'excluded','Remote location is restricted to '+', '.join(info['countries'])
        elif not info['worldwide']:unclear=True
    if unclear:return ('review' if selection['include_unknown'] else 'excluded'),'Experience or remote residence is not established by this observation'
    return 'match','Matches the selected source-text filters; not an eligibility guarantee'


def filter_result(result,selection,remote_only=False):
    if selection is None:return result
    selection=preferences(selection);jobs=[];excluded=list(result.get('excluded',[]));info={}
    for index,row in enumerate(result['jobs'],1):
        item=classify(row,selection['version']);state,reason=decision(item,selection,remote_only)
        if selection['version']==2 and not role_matches(row['title'],selection['role_query']):
            state,reason='excluded','Job title does not match the selected role; use keyword search for skills'
        info[row['id']]={**item,'title':row['title'],'state':state,'reason':reason}
        if state=='excluded':excluded.append({'row':index,'id':row['id'],'reason':reason})
        else:jobs.append(row)
    return {**result,'jobs':jobs,'excluded':excluded,'fit':{'preferences':selection,'rows':info},
            'notice':result.get('notice','')+' Local experience/residence filters apply to this observed page only. Counts and pagination are not whole-market coverage.'}


def discovery_view(state):
    return state|{'classifications':{item['id']:classify(item['row'],item['last_search'].get('preferences',DEFAULT)['version']) for item in state['candidates']}}
