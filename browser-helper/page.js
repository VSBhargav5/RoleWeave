/* Explicit review only: no background form capture. */
(()=>{
 const allowed=['full_name','first_name','last_name','email','phone','location','linkedin','website'];
 const names={name:'full_name','full name':'full_name','your name':'full_name','first name':'first_name','given name':'first_name','preferred first name':'first_name','last name':'last_name','family name':'last_name','preferred last name':'last_name',email:'email','email address':'email',phone:'phone','phone number':'phone','mobile number':'phone',location:'location','location (city)':'location','city':'location','current location':'location',linkedin:'linkedin','linkedin url':'linkedin','linkedin profile':'linkedin',website:'website','personal website':'website',portfolio:'website','portfolio url':'website'};
 const autocomplete={name:'full_name','given-name':'first_name','family-name':'last_name',email:'email',tel:'phone'};
 const normalized=s=>s.toLowerCase().replace(/[*:]/g,'').replace(/\s+/g,' ').trim();
 const manual=s=>/password|social security|passport|national id|date of birth|\bssn\b|gender|pronoun|\brace\b|ethnic|disabilit|veteran|criminal|convict|sponsor|visa|immigration|authoriz|authoris|citizen|legally|consent|privacy|personal data|data processing|^ai policy|terms|salary|compensation/i.test(s);
 function library(data){
  if(!data||data.format!=='roleweave-answers-v1'||!Array.isArray(data.answers)||data.answers.length>100||Object.keys(data).some(k=>!['format','answers'].includes(k)))throw Error('Choose a RoleWeave answer-library JSON (up to 100 answers).');
  const ids=new Set();
  for(const row of data.answers){
   if(!row||typeof row!=='object'||Object.keys(row).sort().join(',')!=='aliases,answer,host,id,page,question,updated_at')throw Error('Unsupported answer record.');
   for(const [key,limit] of [['id',100],['question',500],['answer',5000],['host',253],['updated_at',40]])if(typeof row[key]!=='string'||!row[key].trim()||row[key].length>limit||/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(row[key]))throw Error('Unsupported answer value.');
   if(!/^[A-Za-z0-9-]+$/.test(row.id)||ids.has(row.id)||!Number.isFinite(Date.parse(row.updated_at)))throw Error('Invalid answer identity or date.');
   ids.add(row.id);
   if(typeof row.page!=='string'||row.page.length>4000)throw Error('Invalid page scope.');
   if(row.page){let u;try{u=new URL(row.page)}catch{throw Error('Invalid page scope.')}if(u.hostname!==row.host||u.username||u.password||(u.protocol!=='https:'&&!(u.protocol==='http:'&&['127.0.0.1','localhost'].includes(u.hostname))))throw Error('Invalid page scope.');}
   if(row.host!=='*'&&!/^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(row.host))throw Error('Use an exact site hostname or * for all sites.');
   if(!Array.isArray(row.aliases)||row.aliases.length>10||row.aliases.some(v=>typeof v!=='string'||!v.trim()||v.length>500||/[\x00-\x1f]/.test(v)))throw Error('Use up to 10 question aliases, one per line.');
   if([row.question,...row.aliases].some(manual))throw Error('Legal, sensitive and salary questions stay manual. Save professional experience questions here.');
  }
  return data;
 }
 globalThis.RoleWeaveAnswers={library,normalized,manual};
 function profile(data){if(!data||data.format!=='roleweave-browser-profile-v1'||!data.fields||Object.keys(data.fields).some(k=>!allowed.includes(k)))throw Error('Unsupported contact sheet');for(const v of Object.values(data.fields))if(typeof v!=='string'||v.length>2000||/[\x00-\x1f]/.test(v))throw Error('Unsupported contact value');return data}
 function visible(el){
  if(el.disabled||el.readOnly||!el.getClientRects().length)return false;
  for(let node=el;node;node=node.getRootNode()?.host){if(getComputedStyle(node).visibility==='hidden'||node.closest('[inert],[aria-hidden="true"]'))return false}
  return true;
 }
 function deep(selector){const values=[],roots=[document];let nodes=0;for(const root of roots){values.push(...root.querySelectorAll(selector));for(const el of root.querySelectorAll('*')){if(++nodes>30000)throw Error('This document is too large for assisted filling.');if(el.shadowRoot)roots.push(el.shadowRoot)}}return values}
 function eligible(el){return visible(el)&&(el instanceof HTMLTextAreaElement||el instanceof HTMLSelectElement&&!el.multiple||el instanceof HTMLInputElement&&['text','email','tel','url','search','number'].includes(el.type))}
 function labels(el){
  const values=[...el.labels||[]].map(l=>{const copy=l.cloneNode(true);copy.querySelectorAll('input,textarea,select,button').forEach(n=>n.remove());return copy.textContent});
  if(el.getAttribute('aria-label'))values.push(el.getAttribute('aria-label'));
  const labelled=el.getAttribute('aria-labelledby');
  if(labelled){const text=labelled.split(/\s+/).map(id=>el.getRootNode().getElementById(id)?.textContent||'').join(' ').trim();if(text)values.push(text)}
  return [...new Set(values.map(normalized).filter(Boolean))];
 }
 function mapping(el){const text=labels(el),byLabels=[...new Set(text.map(n=>names[n]).filter(Boolean))];const ac=(el.autocomplete||'').trim().split(/\s+/).at(-1),byAuto=autocomplete[ac];if(byLabels.length>1||byAuto&&byLabels.length&&byAuto!==byLabels[0])return null;if(text.length&&!byLabels.length)return null;const key=byAuto||byLabels[0];return key?{key,label:text.find(n=>names[n]===key)||ac}:null}
 function valueFits(el,value){
  if(el instanceof HTMLSelectElement){const options=[...el.options].filter(o=>!o.disabled&&(normalized(o.text)===normalized(value)||o.value===value));return options.length===1?options[0].value:null}
  if(el.maxLength>=0&&value.length>el.maxLength)return null;
  if(el instanceof HTMLInputElement&&el.type==='number'&&(!/^\d+(?:\.\d+)?$/.test(value)||(el.min!==''&&Number(value)<Number(el.min))||(el.max!==''&&Number(value)>Number(el.max))))return null;
  return value;
 }
 function empty(el){return el instanceof HTMLSelectElement?el.value===''||el.selectedIndex<0:!el.value.trim()}
 globalThis.RoleWeavePage=function(action,data){
  if(action==='load'){if(location.hostname!=='127.0.0.1'||location.protocol!=='http:'||document.querySelector('meta[name=roleweave-app]')?.content!=='1')throw Error('This button reads the RoleWeave tab only. On an employer page, import the contact JSON downloaded from RoleWeave instead.');const node=document.getElementById('roleweave-fill-profile');if(!node)throw Error('Prepare the reviewed contact sheet in RoleWeave first');return profile(JSON.parse(node.textContent))}
  if(action==='scan'){
   if(location.protocol!=='https:'&&!['127.0.0.1','localhost'].includes(location.hostname))throw Error('Use HTTPS application pages');
   const contact=data?.format==='roleweave-browser-profile-v1'?profile(data):data?.contact?profile(data.contact):{fields:{}};
   const answers=library(data?.library||{format:'roleweave-answers-v1',answers:[]}).answers;
   const inputs=deep('input,textarea,select');if(inputs.length>1000)throw Error('This form is too large for assisted filling');
   const fields=[],questions=[],skipped=[],refs=new Map();let conflicts=0,blocked=0;
   for(const el of inputs){
    if(!eligible(el))continue;
    const text=labels(el),question=text[0];if(text.some(manual)){blocked++;continue}
    const match=el instanceof HTMLInputElement&&el.type!=='number'?mapping(el):null;
    if(el.getAttribute('role')==='combobox'){skipped.push({label:question||match?.label||'Suggestion field',reason:'Choose a suggestion on the application page. Typing alone does not select a valid option.'});continue}
    let value=match?contact.fields[match.key]:null,answer=null;
    if(!value&&question){
     const candidates=answers.filter(a=>(a.host==='*'||a.host===location.hostname)&&(!a.page||a.page===location.href.split('#')[0])&&[a.question,...a.aliases].some(q=>text.includes(normalized(q))));
     const page=candidates.filter(a=>a.page),site=candidates.filter(a=>a.host===location.hostname),matches=page.length?page:site.length?site:candidates;
     if(matches.length===1){answer=matches[0];value=answer.answer}else if(matches.length>1)conflicts++;
    }
    const id=crypto.randomUUID();
    if(!value||!empty(el)||valueFits(el,value)===null){
     if(question&&!match&&(el.form||el.closest('[role=form],#application_form,.application-question,[data-testid*=application]'))&&questions.length<60)questions.push({id,question,answer:el.value.slice(0,5000),reason:value?'Existing answer or incompatible control; review manually.':'No unique saved answer for this question.'});
     continue;
    }
    const actual=valueFits(el,value);
    fields.push({id,key:match?.key||'answer',label:match?.label||question,value,kind:answer?'answer':'contact',updated_at:answer?.updated_at||''});
    refs.set(id,{el,value:actual,match:JSON.stringify({labels:text,mapping:match}),original:el.value,options:el instanceof HTMLSelectElement?JSON.stringify([...el.options].map(o=>[o.value,o.text,o.disabled])):null});
   }
   const frames=deep('iframe').filter(el=>el.getClientRects().length>0).map(el=>{try{const u=new URL(el.src,location.href);return (u.protocol==='https:'||u.protocol==='http:'&&['127.0.0.1','localhost'].includes(u.hostname))&&!u.username&&!u.password?{href:u.href,title:el.title||'Embedded form'}:null}catch{return null}}).filter(Boolean).slice(0,10);
   globalThis.RoleWeaveFillState={href:location.href,nonce:crypto.randomUUID(),refs};
   return {href:location.href,host:location.hostname,nonce:RoleWeaveFillState.nonce,fields,questions,skipped,frames,conflicts,blocked,controls:inputs.length};
  }
  if(action==='verify'){const refs=globalThis.RoleWeaveLastFill||[];return {filled:refs.filter(({el,value})=>el.isConnected&&el.value===value).length}}
  if(action==='fill'||action==='validate'){
   const state=globalThis.RoleWeaveFillState;
   if(!state||state.href!==location.href||state.nonce!==data.nonce||data.confirmed!==true||!Array.isArray(data.ids)||!data.ids.length||new Set(data.ids).size!==data.ids.length)throw Error('Form preview expired; review again');
   const selected=data.ids.map(id=>{const ref=state.refs.get(id);if(!ref||!ref.el.isConnected||!eligible(ref.el)||ref.el.value!==ref.original||JSON.stringify({labels:labels(ref.el),mapping:ref.el instanceof HTMLInputElement&&ref.el.type!=='number'?mapping(ref.el):null})!==ref.match||ref.options!==(ref.el instanceof HTMLSelectElement?JSON.stringify([...ref.el.options].map(o=>[o.value,o.text,o.disabled])):null)||valueFits(ref.el,ref.value)===null)throw Error('A field changed after preview; review again');return ref});
   if(action==='validate')return {ready:selected.length};
   globalThis.RoleWeaveLastFill=selected;delete globalThis.RoleWeaveFillState;
   for(const {el,value} of selected){const proto=el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:el instanceof HTMLSelectElement?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}))}
   return {filled:selected.length};
  }
  throw Error('Unknown helper action');
 };
})();
