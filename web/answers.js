const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const normalized=v=>v.toLowerCase().replace(/[*:]/g,'').replace(/\s+/g,' ').trim();

export class AnswerLibraryPanel {
 constructor({root,api,onDirty=()=>{}}){
  this.root=root;this.api=api;this.onDirty=onDirty;this.alive=true;this.state=null;this.dirty=false;
  root.innerHTML='<p role="status">Loading saved answers…</p>';
  this.load().catch(e=>{if(this.alive)root.textContent=e.message});
 }
 close(){this.alive=false}
 async load(){this.state=await this.api('answers',{action:'read'});if(this.alive)this.render()}
 status(message){this.root.querySelector('[data-answer-status]').textContent=message}
 render(){
  this.root.innerHTML=`<div class="panel-head"><h2>Reusable application answers</h2><button type="button" class="btn" data-answer="export">Download answers JSON</button></div><p>Save reviewed professional answers once, then reuse them in the helper. This library is stored in your workspace and included in recovery ZIPs. Export here to import in the helper; export from the helper and import here to back up newly captured answers. Nothing fills an employer form from this page.</p><div class="actions"><button class="btn primary" type="button" data-answer="new">Add an answer</button><label class="btn">Import helper answers JSON<input type="file" data-answer-file accept=".json,application/json" hidden></label><button class="btn" type="button" data-answer="refresh">Refresh library</button></div><div data-answer-import hidden></div><p data-answer-status role="status" aria-live="polite">${this.state.library.answers.length} saved answers. Exported files and extension storage are separate copies.</p><form data-answer-form hidden><h3 data-answer-title>Add a reviewed answer</h3><input name="id" type="hidden"><label class="field">Question<textarea name="question" required maxlength="500" rows="2"></textarea></label><label class="field">Your answer<textarea name="answer" required maxlength="5000" rows="5"></textarea></label><details><summary>Other wordings for this question</summary><label class="field">One alias per line, up to 10<textarea name="aliases" maxlength="5000" rows="2"></textarea></label></details><div class="field-grid"><label class="field">Reuse scope<select name="scope"><option value="page">This application page only</option><option value="site">This site</option><option value="all">All sites</option></select></label><label class="field">Application URL (HTTPS; required for page or site scope)<input name="url" type="url" maxlength="4000"></label></div><p class="footnote">Keep employer-specific answers page-only. Review dates and years of experience before reuse. Legal, sensitive and salary questions stay manual.</p><label class="fact-choice"><input name="confirmed" type="checkbox" required>I reviewed this answer and its reuse scope.</label><div class="actions"><button class="btn primary" type="submit">Save reviewed answer</button><button class="btn" type="submit" name="next" value="yes">Save and add another</button><button class="btn" type="button" data-answer="cancel">Close editor</button></div><p data-answer-save-status role="status" aria-live="polite"></p></form><label class="field">Find a saved question or answer<input data-answer-search type="search" maxlength="500" placeholder="Python, projects, employer…"></label><div data-answer-list></div>`;
  this.list();
  this.root.querySelector('[data-answer-search]').oninput=()=>this.list();
  this.root.querySelector('[data-answer-file]').onchange=e=>this.importFile(e.target);
  this.root.querySelector('[data-answer-form]').onsubmit=e=>this.save(e);
  this.root.querySelector('[data-answer-form]').oninput=e=>{if(e.target.name!=='confirmed')e.currentTarget.elements.confirmed.checked=false;this.dirty=true;this.onDirty(true)};
  this.root.onclick=e=>{const b=e.target.closest('[data-answer]');if(b)this.action(b).catch(error=>this.status(error.message))};
 }
 list(){
  const query=this.root.querySelector('[data-answer-search]').value.toLocaleLowerCase();
  const rows=this.state.library.answers.filter(a=>[a.question,a.answer,a.host,...a.aliases].join(' ').toLocaleLowerCase().includes(query));
  this.root.querySelector('[data-answer-list]').innerHTML=rows.map(a=>`<article class="fact-card"><h3>${esc(a.question)}</h3><p style="white-space:pre-wrap">${esc(a.answer)}</p><small>${esc(a.page||a.host)} · updated ${esc(a.updated_at.slice(0,10))}</small><div class="actions"><button class="btn" type="button" data-answer="edit" data-id="${esc(a.id)}">Edit answer</button><button class="btn" type="button" data-answer="delete" data-id="${esc(a.id)}">Delete answer</button></div></article>`).join('')||'<p>No matching saved answers.</p>';
 }
 edit(row=null){
  if(this.dirty&&!confirm('Discard the unsaved answer draft before opening another?'))return;this.dirty=false;this.onDirty(false);
  const f=this.root.querySelector('[data-answer-form]');f.hidden=false;f.reset();
  for(const key of ['id','question','answer'])f.elements[key].value=row?.[key]||'';
  f.elements.aliases.value=row?.aliases.join('\n')||'';
  f.elements.scope.value=row?(row.page?'page':row.host==='*'?'all':'site'):'page';
  f.elements.url.value=row?.page||(row&&row.host!=='*'?'https://'+row.host+'/':'');
  this.root.querySelector('[data-answer-title]').textContent=row?'Edit reviewed answer':'Add a reviewed answer';
  this.root.querySelector('[data-answer-save-status]').textContent='';f.elements.question.focus();f.scrollIntoView({block:'start'});
 }
 async save(event){
  event.preventDefault();event.stopPropagation();const f=event.currentTarget,out=f.querySelector('[data-answer-save-status]');
  const buttons=[...f.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
  try{
   if(!f.elements.confirmed.checked)throw Error('Review this answer and its scope before saving.');
   const d=Object.fromEntries(new FormData(f)),u=d.url?new URL(d.url):null;
   if(d.scope!=='all'&&!u)throw Error('Enter the application URL for page or site scope.');
   const row={id:d.id||crypto.randomUUID(),question:d.question.trim(),answer:d.answer.trim(),aliases:d.aliases.split('\n').map(v=>v.trim()).filter(Boolean),host:d.scope==='all'?'*':u.hostname,page:d.scope==='page'?u.href.split('#')[0]:'',updated_at:new Date().toISOString()};
   if(this.state.library.answers.some(a=>a.id!==row.id&&a.host===row.host&&a.page===row.page&&normalized(a.question)===normalized(row.question)))throw Error('This question is already saved for this scope. Edit the existing answer.');
   this.state=await this.api('answers',{action:'save',answer:row,expected_sha256:this.state.sha256,confirmed:true});if(!this.alive)return;
   this.dirty=false;this.onDirty(false);
   if(event.submitter?.name==='next')this.edit();else f.elements.id.value=row.id;
   this.list();const message='Answer saved in this workspace and included in recovery ZIPs. '+this.state.library.answers.length+' saved answers. Download JSON to update the helper.';
   out.textContent=message;this.status(message);
  }catch(error){if(this.alive)out.textContent='Not saved: '+error.message}
  finally{buttons.forEach(b=>b.disabled=false)}
 }
 async importFile(input){
  try{
   const file=input.files[0];if(!file)return;if(file.size>1024*1024)throw Error('Answer library exceeds 1 MiB');
   const bank=JSON.parse(await file.text());
   if(bank?.format!=='roleweave-answers-v1'||!Array.isArray(bank.answers))throw Error('Choose an exported RoleWeave answers JSON file.');
   this.incoming=bank;const box=this.root.querySelector('[data-answer-import]');box.hidden=false;
   box.innerHTML=`<h3>Review imported answers</h3><p>${bank.answers.length} incoming answers. Existing answers are kept unless you explicitly replace conflicting IDs.</p><details><summary>Inspect incoming questions and scope</summary>${bank.answers.map(a=>`<p><strong>${esc(a.question)}</strong><br>${esc(a.answer)}<br><small>${esc(a.page||a.host)}</small></p>`).join('')}</details><label class="fact-choice"><input data-answer-replace type="checkbox">Replace conflicting saved IDs with these reviewed imported answers</label><button class="btn primary" type="button" data-answer="import">Import reviewed answers</button><button class="btn" type="button" data-answer="cancel-import">Cancel import</button>`;
   box.scrollIntoView({block:'start'});
  }catch(e){this.status(e.message)}finally{input.value=''}
 }
 async action(button){
  const action=button.dataset.answer,row=this.state.library.answers.find(a=>a.id===button.dataset.id);
  if(action==='new'||action==='edit'){this.edit(row);return}
  if(action==='cancel'){if(this.dirty&&!confirm('Close the editor and discard any unsaved changes?'))return;this.dirty=false;this.onDirty(false);this.root.querySelector('[data-answer-form]').hidden=true;return}
  if(action==='cancel-import'){this.incoming=null;this.root.querySelector('[data-answer-import]').hidden=true;return}
  if(action==='refresh'){if(this.dirty&&!confirm('Refresh the library and discard any unsaved answer draft?'))return;this.dirty=false;this.onDirty(false);await this.load();return}
  if(action==='export'){
   const url=URL.createObjectURL(new Blob([JSON.stringify(this.state.library,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='RoleWeave-answers.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);this.status('Answers JSON downloaded. It contains unencrypted professional answers.');return;
  }
  if(['delete','import'].includes(action)&&this.dirty&&!confirm('Discard the unsaved answer draft before changing the library?'))return;
  if(action==='delete'&&!confirm('Delete this saved answer from the workspace? Exported files and the extension are unchanged.'))return;
  button.disabled=true;
  try{
   const data=action==='import'?{library:this.incoming,replace:this.root.querySelector('[data-answer-replace]').checked}:{id:row.id};
   this.state=await this.api('answers',{action,...data,expected_sha256:this.state.sha256,confirmed:true});
   if(this.alive){this.dirty=false;this.onDirty(false);this.incoming=null;this.render();this.status(action==='import'?'Reviewed answers imported and included in workspace recovery.':'Answer deleted from this workspace.');}
  }finally{button.disabled=false}
 }
}
