/* Application-specific proposal, deliberate request, review and revision UI. */
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const names={headline:'Application headline',summary:'Professional summary',letter_intro:'Letter introduction',letter_closing:'Letter closing'};
const limits={headline:200,summary:2000,letter_intro:2500,letter_closing:1000};
const btn=(name,action,primary=false)=>`<button type="button" class="btn ${primary?'primary':''}" data-ai="${action}">${name}</button>`;

export class TailoringPanel {
 constructor({root,api,profile,job,demo,onAccept}){
  Object.assign(this,{root,api,profile,job,demo,onAccept});this.alive=true;this.run=0;this.previous=null;this.selected=null;
  root.addEventListener('click',event=>{const action=event.target.closest('[data-ai]')?.dataset.ai;if(!action)return;event.preventDefault();this.action(action).catch(e=>this.error(e.message))});
  root.addEventListener('input',event=>{const review=root.querySelector('[name=ai_accuracy]');if(review&&event.target!==review)review.checked=false});
  this.sources();
 }
 header(step){return `<div class="ai-stepbar">${['Choose sources','Review request','Review wording'].map((label,i)=>`<span class="${i===step?'active':''}"><b>0${i+1}</b>${label}</span>`).join('')}</div>`}
 paint(step,body){if(!this.alive)return;this.root.innerHTML=this.header(step)+body+'<p class="ai-error modal-error" role="alert"></p>';this.root.closest('.modal-body').scrollTop=0;const heading=this.root.querySelector('h3');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true})}}
 error(message){const target=this.root.querySelector('.ai-error');if(target)target.textContent=message}
 sources(){const facts=this.profile.profile.facts.filter(f=>f.reviewed);this.paint(0,`<div class="ai-heading"><div><h3>Make the application sound like you.</h3><p>Choose the facts the assistant may use. Contact fields, private source notes and unselected facts are excluded.</p></div><span class="pill">${this.demo?'OFFLINE PRACTICE':'OpenAI · gpt-4.1-mini'}</span></div><div class="ai-source-list">${facts.map((f,i)=>`<label class="fact-choice"><input type="checkbox" name="ai_fact" value="${esc(f.id)}" ${(this.selected?this.selected.includes(f.id):i<20)?'checked':''}><span><small class="source">${esc(f.section)}</small>${esc(f.claim)}</span></label>`).join('')||'<p>No reviewed facts. Add and review your career profile first.</p>'}</div><label class="field full">What should this draft focus on?<textarea name="ai_instruction" rows="3" maxlength="2000">${esc(this.instruction||'Tailor the wording to this role. Keep project work distinct from employment. Do not add unprovided experience or metrics.')}</textarea></label>${this.previous?'<p class="footnote">The previous proposal is included in the next exact request. It is untrusted model wording, not additional evidence.</p>':''}<div class="ai-footer">${btn('Review provider request','preview',true)}<small>Nothing is sent by opening this workspace.</small></div>`)}
 async preview(previous=null){
  this.selected=[...this.root.querySelectorAll('[name=ai_fact]:checked')].map(e=>e.value);
  this.instruction=this.root.querySelector('[name=ai_instruction]').value;
  return this.prepare(this.instruction,previous);
 }
 async prepare(instruction,previous){
  const buttons=[...this.root.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
  try{
   const preview=await this.api('tailoring/preview',{profile_id:this.profile.id,profile_sha256:this.profile.snapshot_sha256,
    job_id:this.job.id,fact_ids:this.selected,instruction,...(previous?{previous}:{})});
   if(!this.alive)return;
   if(this.entry){try{await this.api('tailoring/cancel',{id:this.entry.id})}catch{}}
   this.entry=preview;this.previous=previous;this.instruction=instruction;this.request();
  }finally{buttons.forEach(b=>{if(b.isConnected)b.disabled=false})}
 }
 request(){const p=this.entry;this.paint(1,`<div class="ai-heading"><div><h3>${p.offline_demo?'Try a synthetic draft locally.':'Review this one provider request.'}</h3><p>${p.offline_demo?'Practice mode uses fixed wording. No model or API is called.':'Only the exact content below is sent after you consent and press Send.'}</p></div></div><div class="ai-request-meta"><span>Destination<strong>${p.offline_demo?'Local synthetic fixture':esc(p.endpoint)}</strong></span><span>Model<strong>${p.offline_demo?'No model':esc(p.model)}</strong></span><span>Output cap<strong>4096 tokens</strong></span></div><details class="ai-payload" open><summary>Exact request JSON · ${this.selected.length} selected facts</summary><pre>${esc(p.payload)}</pre></details>${p.offline_demo?'':`<label class="field full">API key for this request only<input name="ai_key" type="password" autocomplete="off" spellcheck="false" maxlength="1000"></label><p class="footnote">Charges may apply. store=false is not a zero-retention guarantee. Your key is cleared from this field when sent and is not saved or reused. Cancel cannot undo provider processing or charges.</p>`}<label class="fact-choice"><input name="ai_send_consent" type="checkbox">${p.offline_demo?'Run this reviewed request against the local synthetic fixture.':'I reviewed this exact payload and authorize this one request to OpenAI.'}</label><div class="ai-footer">${btn(p.offline_demo?'Run offline practice':'Send reviewed request','send',true)}${btn('Back to sources','sources')}</div>`)}
 async send(){
  if(!this.root.querySelector('[name=ai_send_consent]').checked)throw Error('Review the exact request and explicitly consent first.');
  let key=this.root.querySelector('[name=ai_key]')?.value||'';const input=this.root.querySelector('[name=ai_key]');if(input)input.value='';
  const button=this.root.querySelector('[data-ai=send]');button.disabled=true;
  try{
   await this.api('tailoring/send',{id:this.entry.id,sha256:this.entry.sha256,key,confirmed:true});key=null;
   if(!this.alive)return;this.paint(1,`<div class="ai-wait" role="status"><span class="ai-pulse" aria-hidden="true"></span><h3>${this.demo?'Preparing synthetic wording…':'Preparing your application draft…'}</h3><p>Nothing will enter your documents until you review and accept it.</p>${btn('Cancel request','cancel')}</div>`);
   const run=++this.run,started=Date.now();
   while(this.alive&&run===this.run){
    const result=await this.api('tailoring/status',{id:this.entry.id});if(!this.alive||run!==this.run)return;
    if(result.status==='completed'){this.result=result;this.review();return}
    if(result.status==='failed')throw Error(result.error);
    if(result.status==='cancelled'){this.sources();return}
    if(Date.now()-started>75000){await this.api('tailoring/cancel',{id:this.entry.id});throw Error('Local wait expired. No result was accepted. Remote processing or charges may already have occurred.')}
    await new Promise(resolve=>setTimeout(resolve,350));
   }
  }finally{key=null;if(button.isConnected)button.disabled=false}
 }
 citations(ids){const facts=new Map(this.profile.profile.facts.map(f=>[f.id,f]));return ids.length?`<details class="ai-citations"><summary>${ids.length} source reference${ids.length===1?'':'s'} · inspect</summary>${ids.map(id=>`<blockquote>${esc(facts.get(id)?.claim)}<small>${esc(id)}</small></blockquote>`).join('')}</details>`:'<small class="source">No factual source cited; review as a courtesy phrase only.</small>'}
 review(){const d=this.result.draft;this.paint(2,`<div class="ai-heading"><div><h3>Keep your voice. Check every claim.</h3><p>${this.demo?'Synthetic practice output — no model was called. ':''}Citations show the sources a proposal claims to use. They do not prove the wording is true. Only checked, reviewed edits are adopted.</p></div><span class="pill">Main profile stays unchanged</span></div><div class="ai-review-grid"><section><h4>Resume wording</h4>${['headline','summary'].map(k=>this.editField(k,d[k])).join('')}${d.bullets.map((b,i)=>{const original=this.profile.profile.facts.find(f=>f.id===b.fact_id);return `<article class="ai-edit"><div class="ai-edit-head"><label><input name="accept_fact" type="checkbox" value="${esc(b.fact_id)}">Use this claim</label><span>${esc(original.section)}</span></div><small class="source">Original reviewed fact</small><p class="ai-original">${esc(original.claim)}</p><label class="field">Proposed wording — edit before accepting<textarea name="claim_${i}" rows="3" maxlength="2000">${esc(b.text)}</textarea></label>${this.citations([b.fact_id])}</article>`}).join('')}</section><section><h4>Cover-letter wording</h4>${['letter_intro','letter_closing'].map(k=>this.editField(k,d[k])).join('')}<aside class="ai-questions"><h4>Questions to investigate</h4><p>Model suggestions, not verified gaps or eligibility decisions.</p><ul>${d.questions.map(q=>`<li>${esc(q)}</li>`).join('')}</ul></aside></section></div><section class="ai-refine"><label class="field full">Ask for a revision<textarea name="ai_revision" rows="2" maxlength="2000" placeholder="For example: make this shorter while preserving the project context."></textarea></label>${btn('Review revision request','refine')}<small>Another exact preview and consent are required. Current edited wording is included.</small></section><div class="ai-accept"><label class="fact-choice"><input name="ai_accuracy" type="checkbox">I checked the selected wording against its sources, corrected it, and confirm it is accurate. Save it for this application.</label>${btn('Use reviewed wording','accept',true)}</div>`)}
 editField(key,field){return `<article class="ai-edit"><div class="ai-edit-head"><label><input name="accept_field" type="checkbox" value="${key}" ${field.text?'':'disabled'}>${names[key]}</label></div>${key==='headline'||key==='summary'?`<small class="source">Current profile wording</small><p class="ai-original">${esc(this.profile.profile[key]||'Not provided')}</p>`:''}<label class="field">Proposed wording — edit before accepting<textarea name="field_${key}" rows="${key==='headline'?2:4}" maxlength="${limits[key]}">${esc(field.text)}</textarea></label>${this.citations(field.fact_ids)}</article>`}
 edited(){const draft=structuredClone(this.result.draft);for(const k of Object.keys(names))draft[k].text=this.root.querySelector(`[name=field_${k}]`).value;draft.bullets.forEach((b,i)=>b.text=this.root.querySelector(`[name=claim_${i}]`).value);return draft}
 async accept(){
  if(!this.root.querySelector('[name=ai_accuracy]').checked)throw Error('Review and explicitly confirm the selected wording.');
  const draft=this.edited(),ids=new Set([...this.root.querySelectorAll('[name=accept_fact]:checked')].map(e=>e.value)),chosen=[...this.root.querySelectorAll('[name=accept_field]:checked')].map(e=>e.value);
  const controls=[...this.root.querySelectorAll('input,textarea,button')].map(el=>[el,el.disabled]);for(const [el]of controls)el.disabled=true;
  try{const result=await this.api('tailoring/accept',{id:this.entry.id,result_sha256:this.result.result_sha256,
   fact_edits:draft.bullets.filter(b=>ids.has(b.fact_id)).map(b=>({id:b.fact_id,text:b.text})),
   fields:Object.fromEntries(chosen.map(k=>[k,draft[k].text])),confirmed:true});if(!this.alive)return;this.accepted=true;await this.onAccept(result)}
  finally{for(const [el,disabled]of controls)if(el.isConnected)el.disabled=disabled}
 }
 async action(action){
  if(action==='preview')return this.preview(this.previous);
  if(action==='send')return this.send();
  if(action==='accept')return this.accept();
  if(action==='refine'){const instruction=this.root.querySelector('[name=ai_revision]').value;if(!instruction.trim())throw Error('Describe the revision you want.');return this.prepare(instruction,this.edited())}
  if(action==='sources'||action==='cancel'){++this.run;if(this.entry){await this.api('tailoring/cancel',{id:this.entry.id});this.entry=null}this.sources()}
 }
 close(){this.alive=false;++this.run;const input=this.root.querySelector('[name=ai_key]');if(input)input.value='';if(this.entry&&!this.accepted)this.api('tailoring/cancel',{id:this.entry.id}).catch(()=>{})}
}
