// Opt-in LIVE public search through the actual Windows package and browser form.
const {chromium}=require(process.env.ROLEWEAVE_PLAYWRIGHT||'playwright');
const {spawn}=require('node:child_process');
const net=require('node:net');
const fs=require('node:fs/promises');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
 const executable=path.resolve(process.argv[2]||'out/portable/RoleWeave/RoleWeave.exe');
 const folder=await fs.mkdtemp(path.resolve('out/live-packaged-search-'));
 const listener=net.createServer();await new Promise(resolve=>listener.listen(0,'127.0.0.1',resolve));const port=listener.address().port;await new Promise(resolve=>listener.close(resolve));
 const origin='http://127.0.0.1:'+port;
 const child=spawn(executable,['--db',path.join(folder,'synthetic.db'),'--port',String(port),'--no-browser'],{windowsHide:true,stdio:'ignore'});
 let browser,page;
 try{
  let health;
  for(let i=0;i<100;i++){try{health=await(await fetch(origin+'/health')).json();break}catch{await new Promise(resolve=>setTimeout(resolve,100))}}
  assert.equal(health?.app,'roleweave-local-v1');
  browser=await chromium.launch({headless:true});page=await browser.newPage({viewport:{width:1440,height:1000}});
  await page.goto(origin);await page.locator('nav [data-action=discover]').click();
  await page.locator('[name=query]').fill('data engineer');await page.locator('[name=location]').fill('london');
  const [response]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/search'),{timeout:70000}),page.getByRole('button',{name:'Search jobs',exact:true}).click()]);
  const result=await response.json();assert.equal(response.status(),200,result.error||'Public search failed');assert.ok(result.jobs.length>0,'No accepted results in this public observation');
  await page.getByRole('button',{name:'Review & save',exact:true}).first().waitFor();
  await page.screenshot({path:path.join(folder,'search-results.png'),fullPage:true});
  console.log(JSON.stringify({version:health.version,frozen_browser_search:true,status:response.status(),accepted:result.jobs.length,excluded:result.excluded.length,screenshot:path.join(folder,'search-results.png')}));
 }finally{
  if(page){try{await page.evaluate(async()=>fetch('/api/quit',{method:'POST',headers:{'Content-Type':'application/json','X-RoleWeave-Token':document.querySelector('meta[name=roleweave-session]').content},body:'{"confirmed":true}'}))}catch{}}
  if(browser)await browser.close();if(child.exitCode===null)child.kill();
 }
})().catch(error=>{console.error(error);process.exitCode=1});
