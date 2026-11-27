const $=id=>document.getElementById(id);let preview=null,editorPage='',questionQueue=[],editorQuestion=null,savingAnswer=false;
const emptyLibrary=()=>({format:'roleweave-answers-v1',answers:[]});
const targetId=Number(new URLSearchParams(location.search).get('tab'));
async function targetTab(){if(Number.isInteger(targetId)&&targetId>0)return chrome.tabs.get(targetId);const [tab]=await chrome.tabs.query({active:true,currentWindow:true});if(!tab||tab.url?.startsWith('chrome-extension:')||tab.url?.startsWith('extension:'))throw Error('Open the companion from the toolbar on your application tab.');return tab}
function status(text){$('status').textContent=text}
async function run(action,data){const tab=await targetTab();if(!tab?.id)throw Error('Open an application tab first');if(action==='scan')return RoleWeaveFrames.scan(tab,data);if(action==='fill')return RoleWeaveFrames.fill(tab,preview,data.ids);const result=await RoleWeaveFrames.invoke(tab.id,{frameId:0},action,data);const {frameId,documentId,...value}=result;return value}
function importedContact(data){const allowed=['full_name','first_name','last_name','email','phone','location','linkedin','website'];if(!data||data.format!=='roleweave-browser-profile-v1'||!data.fields||Array.isArray(data.fields)||typeof data.fields!=='object'||Object.keys(data).some(k=>!['format','fields'].includes(k))||Object.keys(data.fields).some(k=>!allowed.includes(k)))throw Error('Choose a RoleWeave contact JSON file, not a resume or workspace backup');for(const value of Object.values(data.fields))if(typeof value!=='string'||value.length>2000||/[\x00-\x1f]/.test(value))throw Error('Unsupported contact value');return {format:data.format,fields:{...data.fields}}}
async function readLibrary(){return RoleWeaveAnswers.library((await chrome.storage.local.get('answerLibrary')).answerLibrary||emptyLibrary())}
function invalidate(){preview=null;$('preview').hidden=true;$('consent').checked=false;$('fill').disabled=true}
function selection(){const n=$('fields').querySelectorAll('input:checked').length;$('field-count').textContent=preview?.fields.length?`${n} of ${preview.fields.length} fields selected.`:'No fillable fields were detected on this page.';$('consent').disabled=!preview?.fields.length;$('fill').disabled=!preview||!n||!$('consent').checked}
$('fields').onchange=()=>{$('consent').checked=false;selection()};$('consent').onchange=selection;
$('contact-file').onchange=async()=>{invalidate();try{const file=$('contact-file').files[0];if(!file)return;if(file.size>20000)throw Error('Contact file exceeds 20 KB');const contact=importedContact(JSON.parse(await file.text()));await chrome.storage.session.set({contact});await refresh();status('Contact sheet imported. Review this employer form next. No fields have been filled.')}catch(error){status(error.message)}finally{$('contact-file').value=''}};
async function refresh(){const {contact}=await chrome.storage.session.get('contact'),bank=await readLibrary();$('scan').disabled=!contact&&!bank.answers.length;$('profile-status').textContent=contact?'Reviewed contact sheet loaded for this browser session.':'No contact sheet loaded.';$('library-status').textContent=`${bank.answers.length} saved answers. Export JSON for a backup.`;$('saved-answers').replaceChildren();for(const row of bank.answers){const item=document.createElement('div'),name=document.createElement('p'),edit=document.createElement('button'),remove=document.createElement('button');name.textContent=row.question+' — '+(row.page?'this application page':row.host==='*'?'all sites':row.host);edit.textContent='Edit answer';edit.onclick=()=>openEditor(row);remove.textContent='Delete answer';remove.onclick=async()=>{try{const current=await readLibrary();await chrome.storage.local.set({answerLibrary:{...current,answers:current.answers.filter(a=>a.id!==row.id)}});invalidate();await refresh();status('Answer deleted locally. Exported files are unchanged.')}catch(e){status(e.message)}};item.append(name,edit,remove);$('saved-answers').append(item)}}
async function openEditor(row=null,question=null){try{const tab=await targetTab(),u=new URL(tab.url);if(u.protocol!=='https:'&&!(u.protocol==='http:'&&u.hostname==='127.0.0.1'))throw Error('Open the helper on the application page to save an answer.');editorQuestion=question;editorPage=question?.frameHref||row?.page||(row?.host&&row.host!=='*'?'https://'+row.host+'/':u.href.split('#')[0]);editorPage=editorPage.split('#')[0];$('answer-id').value=row?.id||'';$('answer-question').value=row?.question||question?.question||'';$('answer-aliases').value=row?.aliases.join('\n')||'';$('answer-text').value=row?.answer||question?.answer||'';$('answer-scope').value=row?(row.page?'page':row.host==='*'?'all':'site'):'page';$('answer-destination').textContent='Application context: '+editorPage;$('editor-status').textContent='';$('question-progress').textContent=questionQueue.length?`${questionQueue.length} detected questions left to save. You can edit the question and answer.`:'Add a question and answer, then Save and next to add another.';if(!$('answer-editor').open)$('answer-editor').showModal();$(question?'answer-text':'answer-question').focus();$(question?'answer-text':'answer-question').scrollIntoView({block:'nearest'})}catch(e){status(e.message)}}
$('new-answer').onclick=()=>openEditor();
$('close-editor').onclick=()=>$('answer-editor').close();
$('answer-form').onsubmit=async event=>{
 event.preventDefault();if(savingAnswer)return;savingAnswer=true;
 for(const id of ['save-answer','save-next','close-editor'])$(id).disabled=true;
 try{
  if(!editorPage)throw Error('Choose New answer or a detected question first.');
  const bank=await readLibrary(),scope=$('answer-scope').value,u=new URL(editorPage),id=$('answer-id').value||crypto.randomUUID();
  const row={id,question:$('answer-question').value.trim(),aliases:$('answer-aliases').value.split('\n').map(v=>v.trim()).filter(Boolean),answer:$('answer-text').value.trim(),host:scope==='all'?'*':u.hostname,page:scope==='page'?editorPage:'',updated_at:new Date().toISOString()};
  const duplicate=bank.answers.find(a=>a.id!==id&&a.host===row.host&&a.page===row.page&&RoleWeaveAnswers.normalized(a.question)===RoleWeaveAnswers.normalized(row.question));
  if(duplicate)throw Error('This question is already saved for this scope. Close this editor and use Edit answer in your library.');
  const next=RoleWeaveAnswers.library({...bank,answers:[...bank.answers.filter(a=>a.id!==id),row]});
  await chrome.storage.local.set({answerLibrary:next});
  questionQueue=questionQueue.filter(q=>q!==editorQuestion);
  invalidate();await refresh();$('answer-id').value=id;
  const message='Reviewed answer saved locally. '+next.answers.length+' saved answers. Review this form again to propose it.';
  status(message);
  if(event.submitter?.id==='save-next')await openEditor(null,questionQueue[0]||null);
  $('editor-status').textContent=message;
  if(event.submitter?.id==='save-next')$(editorQuestion?'answer-text':'answer-question').scrollIntoView({block:'nearest'});
 }catch(e){$('editor-status').textContent='Not saved: '+e.message}
 finally{savingAnswer=false;for(const id of ['save-answer','save-next','close-editor'])$(id).disabled=false}
};
$('answers-file').onchange=async()=>{try{const file=$('answers-file').files[0];if(!file)return;if(file.size>1024*1024)throw Error('Answer library exceeds 1 MiB');const incoming=RoleWeaveAnswers.library(JSON.parse(await file.text())),bank=await readLibrary(),merged=new Map(bank.answers.map(a=>[a.id,a]));for(const row of incoming.answers){if(merged.has(row.id)&&JSON.stringify(merged.get(row.id),Object.keys(row).sort())!==JSON.stringify(row,Object.keys(row).sort())&&!$('replace-answers').checked)throw Error('An imported answer ID conflicts with a saved answer. Your library was not changed.');merged.set(row.id,row)}await chrome.storage.local.set({answerLibrary:RoleWeaveAnswers.library({...bank,answers:[...merged.values()]})});invalidate();await refresh();status('Answers imported locally. Review this form to see matches.')}catch(e){status(e.message)}finally{$('answers-file').value=''}};
$('export-answers').onclick=async()=>{try{const bank=await readLibrary(),url=URL.createObjectURL(new Blob([JSON.stringify(bank,null,2)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='RoleWeave-answers.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),30000);status('Answer JSON exported. It contains your unencrypted saved answers.')}catch(e){status(e.message)}};
for(const action of ['load','clear','scan','fill'])$(action).onclick=async()=>{for(const b of document.querySelectorAll('button'))b.disabled=true;try{
 if(action==='load'){const contact=await run('load');await chrome.storage.session.set({contact});invalidate();status('Contact sheet loaded. Open the employer application form next.')}
 if(action==='clear'){await chrome.storage.session.clear();invalidate();status('Contact sheet cleared. Saved answers retained.')}
 if(action==='scan'){
  invalidate();const {contact}=await chrome.storage.session.get('contact');preview=await run('scan',{contact,library:await readLibrary()});$('destination').textContent=preview.href;$('fields').replaceChildren();
  for(const f of preview.fields){const label=document.createElement('label'),check=document.createElement('input'),name=document.createElement('strong'),value=document.createElement('small');check.type='checkbox';check.value=f.id;check.checked=f.kind!=='answer';name.textContent=f.label+(f.frameId?' · embedded application':'');value.textContent=f.value+(f.frameId?'\nDestination: '+new URL(f.frameHref).host:'')+(f.updated_at?' (saved '+f.updated_at.slice(0,10)+')':'');label.append(check,name,value);$('fields').append(label)}
  questionQueue=[...(preview.questions||[])];$('questions').replaceChildren();for(const q of questionQueue){const item=document.createElement('div'),text=document.createElement('p'),button=document.createElement('button');text.textContent=q.question;button.textContent='Save an answer for this question';button.onclick=()=>openEditor(null,q);item.append(text,button);$('questions').append(item)}
  if(!preview.questions?.length)$('questions').textContent='No new supported questions detected. Use New answer to add one manually.';
  $('frame-help').replaceChildren();
  for(const route of preview.routes.filter(r=>r.frameId)){const p=document.createElement('p');p.textContent='Embedded application destination: '+route.href;$('frame-help').append(p)}
  for(const frame of preview.pending||[]){
   const box=document.createElement('div'),text=document.createElement('p'),button=document.createElement('button'),link=document.createElement('a');
   text.textContent='Embedded application found on '+frame.origin+'. Browser access is required to read its fields.';
   button.textContent='Allow embedded form on '+new URL(frame.href).hostname;button.type='button';button.disabled=!chrome.permissions?.request;
   button.onclick=()=>{
    invalidate();
    // Call request immediately in the click handler; Chrome requires this gesture.
    const request=chrome.permissions.request({permissions:['webNavigation'],origins:[RoleWeaveFrames.originPattern(frame.href)]});
    request.then(granted=>{if(granted){status('Embedded-site access granted. Reviewing application fields…');$('scan').click()}else status('Access was not granted. No fields were filled. You can retry or open the embedded form directly.');}).catch(e=>status(e.message));
   };
   link.href=frame.href;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Open embedded form directly';box.append(text,button,link);$('frame-help').append(box);
  }
  for(const item of [...preview.errors||[],...preview.skipped||[]]){const p=document.createElement('p');p.textContent=(item.label||item.href)+': '+(item.message||item.reason);$('frame-help').append(p)}
  $('preview').hidden=false;status(preview.fields.length?`${preview.fields.length} supported empty fields. Review each value.`:`No supported empty native fields found (${preview.controls||0} controls on this page). ${preview.pending?.length?'Embedded application access is needed; use Allow embedded form above.':'Existing answers, unlabeled fields and custom widgets stay manual.'}`);if(preview.conflicts)status($('status').textContent+` ${preview.conflicts} ambiguous saved answers were not selected.`);
 }
 if(action==='fill'){if(!preview||!$('consent').checked)throw Error('Review the destination and explicitly consent first');const ids=[...$('fields').querySelectorAll('input:checked')].map(i=>i.value);if(!ids.length)throw Error('Select a checkbox beside a field above first.');const current=await targetTab();if(current?.url!==preview.href)throw Error('Destination changed; review this form again');const r=await run('fill',{nonce:preview.nonce,ids,confirmed:true});invalidate();status(`${r.filled} fields filled. Check them, upload documents and submit yourself.`)}
}catch(e){invalidate();status(e.message)}finally{for(const b of document.querySelectorAll('button'))b.disabled=false;await refresh();selection()}};
refresh().catch(e=>status(e.message));
