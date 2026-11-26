/* Explicit, frame-bound MV3 transport. Never registers background content scripts. */
(()=>{
 const canonical=href=>new URL(href).href.split('#')[0];
 const originPattern=href=>new URL(href).origin+'/*';
 const supported=href=>{try{const u=new URL(href);return !u.username&&!u.password&&(u.protocol==='https:'||u.protocol==='http:'&&['127.0.0.1','localhost'].includes(u.hostname))}catch{return false}};
 const family=href=>{try{return new URL(href).hostname.match(/(?:^|\.)(greenhouse\.io|lever\.co|ashbyhq\.com|myworkdayjobs\.com|workday\.com)$/)?.[1]||''}catch{return ''}};
 async function invoke(tabId,frame,action,data){
  const target={tabId,...(frame.documentId?{documentIds:[frame.documentId]}:{frameIds:[frame.frameId]})};
  const injected=await chrome.scripting.executeScript({target,files:['page.js']});
  const documentId=frame.documentId||injected[0]?.documentId;
  const bound={tabId,...(documentId?{documentIds:[documentId]}:{frameIds:[frame.frameId]})};
  const result=await chrome.scripting.executeScript({target:bound,func:(a,d)=>{try{return {ok:true,value:globalThis.RoleWeavePage(a,d)}}catch(e){return {ok:false,error:e.message}}},args:[action,data??null]});
  const item=result[0];if(!item?.result?.ok)throw Error(item?.result?.error||'This frame no longer permits assisted filling. Review again.');
  if(documentId&&item.documentId!==documentId)throw Error('Application frame changed. Review again.');
  return {...item.result.value,frameId:item.frameId??frame.frameId,documentId:item.documentId||documentId};
 }
 async function navigation(tab){if(!await chrome.permissions.contains({permissions:['webNavigation']}))return null;if(!chrome.webNavigation?.getAllFrames)throw Error('Reload the updated helper in the browser extensions page to enable embedded-form discovery.');return await chrome.webNavigation.getAllFrames({tabId:tab.id})}
 function sameFrame(current,expected){return current&&current.url===expected.href&&(!expected.documentId||current.documentId===expected.documentId)}
 function related(frame,hints){return hints.some(h=>{if(!supported(h.href))return false;return canonical(h.href)===canonical(frame.url)||family(h.href)&&family(h.href)===family(frame.url)})}
 async function scan(tab,data){
  const top=await invoke(tab.id,{frameId:0},'scan',data),routes=[top],pending=[],errors=[];
  const frames=await navigation(tab);if(frames?.length>64)throw Error('This page has too many frames. Open the application form directly.');
  const visited=new Set([0]);let changed=true;
  while(changed){changed=false;for(const frame of frames||[]){
   if(visited.has(frame.frameId)||!supported(frame.url))continue;
   const parent=routes.find(r=>r.frameId===frame.parentFrameId);if(!parent||!related(frame,parent.frames||[]))continue;
   visited.add(frame.frameId);changed=true;
   const same=new URL(frame.url).origin===new URL(tab.url).origin;
   const permitted=same||await chrome.permissions.contains({origins:[originPattern(frame.url)]});
   if(!permitted){pending.push({href:frame.url,origin:new URL(frame.url).origin,frameId:frame.frameId});continue}
   try{const proposal=await invoke(tab.id,frame,'scan',data);routes.push(proposal)}catch(error){errors.push({href:frame.url,message:error.message})}
  }}
  if(!frames)for(const hint of top.frames||[]){if(!supported(hint.href))continue;const u=new URL(hint.href);if(u.hostname==='boards.greenhouse.io'&&u.pathname==='/embed/job_app')u.hostname='job-boards.greenhouse.io';pending.push({href:u.href,origin:u.origin,needsDiscovery:true})}
  const current=await chrome.tabs.get(tab.id);if(current.url!==tab.url)throw Error('Application destination changed while scanning. Review again.');
  const latest=await navigation(tab);if(latest&&top.documentId&&!sameFrame(latest.find(f=>f.frameId===0),top))throw Error('Application page reloaded while scanning. Review again.');
  const fields=[],questions=[],skipped=[];
  for(const route of routes){
   for(const f of route.fields)fields.push({...f,id:route.frameId+':'+f.id,localId:f.id,frameId:route.frameId,frameHref:route.href});
   for(const q of route.questions||[])questions.push({...q,id:route.frameId+':'+q.id,frameHref:route.href});
   for(const s of route.skipped||[])skipped.push({...s,frameHref:route.href});
  }
  return {href:tab.url,fields,questions,skipped,pending,errors,routes,frames:top.frames,controls:routes.reduce((n,r)=>n+r.controls,0),conflicts:routes.reduce((n,r)=>n+r.conflicts,0)};
 }
 async function fill(tab,preview,ids){
  if(tab.url!==preview.href||!Array.isArray(ids)||!ids.length||new Set(ids).size!==ids.length)throw Error('Destination or selection changed. Review again.');
  const selected=ids.map(id=>{const field=preview.fields.find(f=>f.id===id);if(!field)throw Error('Unknown reviewed field. Review again.');return field});
  const groups=preview.routes.filter(r=>selected.some(f=>f.frameId===r.frameId)).map(r=>({route:r,ids:selected.filter(f=>f.frameId===r.frameId).map(f=>f.localId)}));
  async function check(){const current=await chrome.tabs.get(tab.id);if(current.url!==preview.href)throw Error('Application destination changed. Review again.');const now=await navigation(tab);if(!now){if(groups.some(g=>g.route.frameId))throw Error('Embedded-form discovery access changed. Allow and review again.');return}for(const g of groups)if(!sameFrame(now.find(f=>f.frameId===g.route.frameId),g.route))throw Error('An application frame navigated or was replaced. Review again.');const top=preview.routes.find(r=>r.frameId===0);if(top.documentId&&!sameFrame(now.find(f=>f.frameId===0),top))throw Error('The employer page reloaded. Review again.')}
  await check();
  // Validate every selected frame before the first write. Separate documents cannot
  // be an atomic transaction: later event-driven changes are reported honestly.
  for(const g of groups)await invoke(tab.id,g.route,'validate',{nonce:g.route.nonce,ids:g.ids,confirmed:true});
  let filled=0;
  try{
   for(const g of groups){await check();const result=await invoke(tab.id,g.route,'fill',{nonce:g.route.nonce,ids:g.ids,confirmed:true});filled+=result.filled}
   await new Promise(resolve=>setTimeout(resolve,120));await check();
   for(const g of groups){const result=await invoke(tab.id,g.route,'verify',null);if(result.filled!==g.ids.length)throw Error('The site did not retain every filled value.')}
  }catch(error){throw Error((filled?`${filled} fields were written before completion could be verified. Check them before another review. `:'No fields were written. ')+error.message)}
  return {filled};
 }
 globalThis.RoleWeaveFrames={scan,fill,invoke,originPattern,supported};
})();
