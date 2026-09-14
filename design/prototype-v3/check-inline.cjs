const {chromium}=require('C:/Users/Sebas/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1060,height:950}});page.setDefaultTimeout(5000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 // Inspect the iframe with remote optional helpers absent, using local Lucide.
 await page.route(/^https?:/,route=>route.abort());
 try{
  await page.goto(pathToFileURL(path.join(__dirname,'checks/inline-preview.html')).href);
  const frame=page.frames().find(f=>f!==page.mainFrame());
  const f=page.frameLocator('iframe');
  await frame.addScriptTag({content:fs.readFileSync('C:/Users/Sebas/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/lucide/dist/umd/lucide.min.js','utf8')});
  await frame.evaluate(()=>lucide.createIcons());
  await f.locator('[data-a=wine][data-id=cr23]').click();
  assert.equal(await f.locator('.wj-wine-highlights .wj-memory').count(),3);
  await f.locator('.wj-wine-highlights [data-a=occasion]').first().click();
  assert.equal(await f.locator('.wj-occasion-wine-heading .wj-art').count(),2);
  await f.locator('.wj-occasion-wine [data-a=wine][data-id=cr23]').click();await f.locator('[data-a=log]').first().click();
  await f.locator('[data-draft=date]').fill('2026-08-01');await f.locator('[data-draft=date]').press('Enter');
  assert.equal(await f.locator('.wj-record-history .wj-entry').count(),3);
  await f.locator('[data-a=log]').first().click();await f.locator('[data-form=entry] button[type=submit]').click();
  assert.equal(await f.locator('.wj-record-history .wj-entry').count(),4);
  await f.locator('[data-a=rating]').click();await f.locator('[name=rating]').selectOption('5');await f.locator('[data-form=rating] button[type=submit]').click();
  assert.equal(await f.locator('.wj-record-history .wj-entry').count(),4);
  await f.locator('[data-a=return-wine]').click();
  await page.locator('iframe').evaluate((e,h)=>e.style.height=h+'px',await frame.evaluate(()=>document.body.scrollHeight));
  await frame.evaluate(()=>window.scrollTo(0,0));
  await f.locator('#wine-journal-v3').screenshot({path:path.join(__dirname,'checks/inline-desktop.png')});
  await frame.evaluate(()=>document.getElementById('wine-journal-v3').classList.add('wj-phone','wj-list'));
  await page.locator('iframe').evaluate((e,h)=>e.style.height=h+'px',await frame.evaluate(()=>document.body.scrollHeight));
  await frame.evaluate(()=>window.scrollTo(0,0));
  const size=await f.locator('.wj-surface').evaluate(e=>({w:e.clientWidth,s:e.scrollWidth}));assert.ok(size.s<=size.w+1);
  await f.locator('#wine-journal-v3').screenshot({path:path.join(__dirname,'checks/inline-phone-list.png')});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(__dirname,'checks/inline-results.json'),JSON.stringify({passed:['Sandboxed iframe: Enter save, button save, rating update without extra entries.','Phone + List design option fits.'],errors,optionalRemoteHelpers:'blocked; local icons supplied for inspection'},null,2));
  console.log('PASS: inline iframe save flows, independent rating update, phone/list option, no runtime errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
