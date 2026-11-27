const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const btn=(label,action)=>`<button type="button" class="btn" data-follow-up="${action}">${label}</button>`;
const consent=(name,label)=>`<label class="fact-choice"><input type="checkbox" name="${name}">${label}</label>`;

export class CorrespondencePanel {
 constructor({root,api,upload,job,onSaved,onDirty}){
  Object.assign(this,{root,api,upload,job,onSaved,onDirty});this.alive=true;this.busy=false;
  root.innerHTML=`<p>Choose a permitted local .eml file (up to 2 MiB). Only inline plaintext is read. HTML, attachments and embedded messages are ignored; headers do not authenticate the sender.</p><label class="field">Local email<input type="file" name="mail_file" accept=".eml"></label><div data-mail-preview></div><p class="mail-status" role="status" aria-live="polite"></p><p class="mail-error error" role="alert"></p>`;
  root.addEventListener('change',e=>{if(e.target.name==='mail_file')this.load(e.target.files[0]).catch(e=>this.error(e.message))});
  root.addEventListener('input',e=>{this.onDirty();if(e.target.name!=='mail_confirmed'){const c=root.querySelector('[name=mail_confirmed]');if(c)c.checked=false}});
  root.addEventListener('click',e=>{const action=e.target.closest('[data-follow-up]')?.dataset.followUp;if(!action)return;e.preventDefault();if(action==='mail-save')this.save().catch(e=>this.error(e.message));if(action==='mail-selection'){const body=root.querySelector('[name=mail_body]');root.querySelector('[name=mail_quote]').value=body.value.slice(body.selectionStart,body.selectionEnd);root.querySelector('[name=mail_confirmed]').checked=false}});
 }
 error(message){if(this.alive)this.root.querySelector('.mail-error').textContent=message}
 async load(file){
  if(this.busy||!file)return;this.busy=true;this.error('');const input=this.root.querySelector('[name=mail_file]');input.disabled=true;
  try{
   if(this.preview){await this.api('correspondence/close',{id:this.preview.id});this.preview=null}
   this.root.querySelector('[data-mail-preview]').innerHTML='';
   if(file.size>2*1024*1024)throw Error('Email exceeds 2 MiB.');
   const p=await this.upload('correspondence/preview?'+new URLSearchParams({job_id:this.job.id}),file);
   if(!this.alive){await this.api('correspondence/close',{id:p.id});return}this.preview=p;this.onDirty();
   this.root.querySelector('[data-mail-preview]').innerHTML=`<dl>${Object.entries(p.headers).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl><p class="footnote">Ignored attachments/messages: ${p.ignored_attachment_names.length}. Original SHA256: ${esc(p.source_sha256)}</p><label class="field">Original plaintext<textarea name="mail_body" rows="9" readonly>${esc(p.body)}</textarea></label>${btn('Use selected body excerpt','mail-selection')}<label class="field">Exact body excerpt (up to 1400 characters)<textarea name="mail_quote" rows="4" maxlength="1400"></textarea></label><label class="field">Your observation (optional)<textarea name="mail_note" rows="3" maxlength="1000"></textarea></label>${consent('mail_confirmed','I reviewed this permitted correspondence and exact excerpt. Store this excerpt and observation in private application history.')}${btn('Record reviewed excerpt','mail-save')}<p class="footnote">The original email and attachments are not saved. Only the selected excerpt, header labels, source hash and your observation enter history and backups. Stage and follow-up stay as recorded.</p>`;
  }finally{this.busy=false;if(this.alive)input.disabled=false}
 }
 async save(){
  if(this.busy||!this.preview)return;this.busy=true;this.error('');const p=this.preview,get=n=>this.root.querySelector(`[name=${n}]`);
  const controls=[...this.root.querySelectorAll('input,textarea,button')];
  try{
   const data={id:p.id,job_id:this.job.id,sha256:p.source_sha256,expected_revision:p.expected_revision,quote:get('mail_quote').value,note:get('mail_note').value,confirmed:get('mail_confirmed').checked};
   controls.forEach(e=>e.disabled=true);await this.api('correspondence',data);this.preview=null;
   if(this.alive){this.root.querySelector('[data-mail-preview]').innerHTML='';this.root.querySelector('.mail-status').textContent='Excerpt recorded. Stage and follow-up retained. Original email discarded from this preview.';await this.onSaved()}
  }finally{this.busy=false;if(this.alive)controls.filter(e=>e.isConnected).forEach(e=>e.disabled=false)}
 }
 close(){this.alive=false;if(this.preview)this.api('correspondence/close',{id:this.preview.id}).catch(()=>{});this.preview=null;this.root.replaceChildren()}
}

export class CalendarPanel {
 constructor({root,api,job}){
  Object.assign(this,{root,api,job});this.alive=true;this.busy=false;
  root.innerHTML=`<p>Preview one all-day follow-up. Nothing is sent until you connect, read remote state and confirm an exact plan. Uses only an app-created secondary calendar; no invitations or automatic deletion.</p>${consent('calendar_details','Include company and role in the event title (generic title by default).')}${btn('Preview local reminder','local')}<div data-calendar-preview></div><p class="calendar-status" role="status" aria-live="polite"></p><p class="calendar-error error" role="alert"></p>`;
  root.addEventListener('click',e=>{const action=e.target.closest('[data-follow-up]')?.dataset.followUp;if(!action)return;e.preventDefault();this.action(action).catch(error=>{if(this.alive)this.root.querySelector('.calendar-error').textContent=error.message})});
  root.addEventListener('input',e=>{
   if(e.target.name==='calendar_details'){this.disconnect();root.querySelector('[data-calendar-preview]').innerHTML='';return}
   const names=e.target.name==='calendar_id'?['read_consent','send_consent']:e.target.name.startsWith('client_')?['connect_consent']:[];
   for(const name of names){const c=this.get(name);if(c)c.checked=false}
   if(e.target.name==='calendar_id'){this.plan=null;const node=root.querySelector('[data-calendar-plan]');if(node)node.innerHTML=''}
  });
 }
 get(name){return this.root.querySelector(`[name=${name}]`)}
 status(text){if(this.alive)this.root.querySelector('.calendar-status').textContent=text}
 async action(action){
  if(this.busy)return;this.busy=true;this.root.querySelector('.calendar-error').textContent='';
  try{
   if(action==='disconnect'){this.disconnect();this.root.querySelector('[data-calendar-preview]').innerHTML='';this.status('Disconnected locally. Existing Google events and consent remain.');return}
   if(action==='local'){
    this.disconnect();const generation=this.generation;const p=await this.api('calendar/open',{job_id:this.job.id,include_details:this.get('calendar_details').checked});
    if(!this.alive||generation!==this.generation){await this.api('calendar/close',{id:p.id});return}this.session=p.id;
    this.root.querySelector('[data-calendar-preview]').innerHTML=`<h3>Exact local reminder</h3><pre class="posting">${esc(JSON.stringify(p.event,null,2))}</pre>${p.offline_demo?'<p>Offline practice: local preview only. Open your regular workspace for optional Google setup.</p>':`<p class="footnote">Requires your own Google Desktop OAuth client with Calendar API enabled. Scope: ${esc(p.scope)}. Session lasts at most ten minutes; credentials/configuration are never saved. Reconnect on expiry. Google setup instructions are in docs/google-calendar.md.</p><label class="field">Desktop OAuth client ID<input name="client_id" autocomplete="off" maxlength="300"></label><label class="field">Desktop OAuth client secret<input name="client_secret" type="password" autocomplete="off" maxlength="1000"></label>${consent('connect_consent','I reviewed the app-created Calendar scope and want to open Google consent.')}${btn('Connect in browser','connect')}<hr><label class="field">App-created secondary calendar ID<input name="calendar_id" autocomplete="off" maxlength="1024"></label>${consent('create_consent','Create ONE new RoleWeave Follow-ups calendar in my Google account. Repeating this creates another calendar.')}${btn('Create separate calendar','create')}${consent('read_consent','Read this exact remote reminder to prepare a proposed change.')}${btn('Read remote and prepare','prepare')}<div data-calendar-plan></div>`}${btn('Disconnect Calendar session','disconnect')}`;
    this.status('Local preview only. No Google request made.');return
   }
   if(!this.session)throw Error('Preview the local reminder first.');
   const consentName={connect:'connect_consent',create:'create_consent',prepare:'read_consent',send:'send_consent'}[action];
   if(!consentName||!this.get(consentName)?.checked)throw Error('Explicitly confirm this Calendar action first.');
   const data={id:this.session,action,confirmed:true};
   if(action==='connect'){data.client_id=this.get('client_id').value;data.client_secret=this.get('client_secret').value;this.get('client_secret').value='';this.get('client_id').value=''}
   if(action==='prepare')data.calendar_id=this.get('calendar_id').value;
   this.get(consentName).checked=false;
   this.root.querySelector('[data-calendar-plan]').innerHTML='';
   this.pending=action;
   const controls=[...this.root.querySelectorAll('input,button')].filter(e=>e.dataset.followUp!=='disconnect');
   controls.forEach(e=>e.disabled=true);
   try{await this.api('calendar/action',data);this.status('Calendar action in progress…');this.poll()}
   catch(error){if(this.alive)controls.filter(e=>e.isConnected).forEach(e=>e.disabled=false);throw error}
  }finally{this.busy=false}
 }
 async poll(){
  const id=this.session;if(!this.alive||!id)return;
  try{
   const state=await this.api('calendar/status',{id});if(!this.alive||this.session!==id)return;
   this.root.querySelectorAll('[data-follow-up]').forEach(e=>{e.disabled=state.status==='running'&&e.dataset.followUp!=='disconnect'});
   this.root.querySelectorAll('input').forEach(e=>e.disabled=state.status==='running');
   if(state.status==='running'){this.timer=setTimeout(()=>this.poll(),400);return}
   if(state.calendar_id&&this.pending==='create')this.get('calendar_id').value=state.calendar_id;
   if(state.error)throw Error(state.error);
   this.status(state.status==='completed'?`Reviewed operation: ${state.result.operation}. Verify the date in Google. No local stage change.`:state.connected?'Calendar session connected. Review each read or write separately.':'Disconnected or expired. Reconnect for remote actions.');
   if(state.plan){this.plan=state.plan;this.root.querySelector('[data-calendar-plan]').innerHTML=`<h3>Review exact ${esc(state.plan.operation)} plan</h3><pre class="posting">${esc(JSON.stringify(state.plan,null,2))}</pre><p class="footnote">Remote ownership and ETag checked. A local or remote change can refuse this write. No automatic retry; a lost response may still mean a completed write.</p>${consent('send_consent','I reviewed the target calendar, operation and exact payload. Authorize this one operation.')}${btn('Send reviewed follow-up','send')}`}
  }catch(error){if(this.alive&&this.session===id)this.root.querySelector('.calendar-error').textContent=error.message}
 }
 disconnect(){this.generation=(this.generation||0)+1;clearTimeout(this.timer);if(this.session)this.api('calendar/close',{id:this.session}).catch(()=>{});this.session=null;this.plan=null;this.root.querySelectorAll('input,button').forEach(e=>e.disabled=false)}
 close(){this.alive=false;this.disconnect();this.root.replaceChildren()}
}
