const {chromium}=require('C:/Users/Sebas/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('node:path'),fs=require('node:fs'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1024,height:950}});page.setDefaultTimeout(5000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const click=a=>page.locator('[data-a="'+a+'"]').filter({visible:true}).first().click();
 const save=type=>page.locator('[data-form="'+type+'"] button[type=submit]').click();
 const wine=id=>page.locator('[data-a=wine][data-id="'+id+'"]').first().click();
 const picture={name:'Evening-photo.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jOioAAAAASUVORK5CYII=','base64')};
 const source=path.join(__dirname,'walkthrough.html');
 try{
  await page.goto(pathToFileURL(source).href);
  for(const nav of ['.wj-nav','.wj-mobile-nav'])assert.deepEqual(await page.locator(nav+' button').evaluateAll(es=>es.map(e=>e.dataset.a)),['browse','library','occasions','guides']);
  await wine('cr23');assert.equal(await page.locator('.wj-wine-highlights .wj-memory').count(),3);
  await page.locator('.wj-wine-highlights [data-a=occasion]').first().click();
  assert.equal(await page.locator('.wj-occasion-wine').count(),2);
  assert.equal(await page.locator('.wj-occasion-wine-heading .wj-art').count(),2);
  assert.equal(await page.getByRole('heading',{name:'From your wine entries'}).count(),0);
  assert.equal(await page.locator('.wj-occasion-album .wj-memory').count(),4);
  await click('occasion-add-wine');await wine('cr23');await click('log');await save('entry');
  assert.equal(await page.locator('.wj-occasion-wine').count(),2);
  assert.equal(await page.locator('[data-wine-id=cr23] .wj-occasion-entry').count(),2);
  await wine('cr23');assert.equal(await page.locator('.wj-wine-highlights .wj-memory').count(),3);
  await page.locator('.wj-wine-highlights [data-a=occasion]').first().click();
  await page.locator('[data-files=occasion]').setInputFiles([picture,picture]);
  await page.locator('.wj-occasion-album img.wj-media-preview').waitFor();
  assert.equal(await page.locator('.wj-occasion-album img.wj-media-preview').count(),1);
  await wine('cr23');await click('toggle-wine-memories');
  assert.equal(await page.locator('.wj-wine-highlights .wj-memory').count(),4);
  assert.equal(await page.locator('.wj-wine-highlights img.wj-media-preview').count(),1);
  await page.locator('.wj-wine-highlights .wj-memory').filter({hasText:'Evening-photo.png'}).locator('.wj-memory-open').click();
  await page.getByRole('heading',{name:'Dinner with Alex & Sam',exact:true}).waitFor();
  await page.locator('.wj-occasion-album .wj-memory').filter({hasText:'Evening-photo.png'}).locator('[data-a=remove-memory]').click();
  assert.equal(await page.locator('.wj-occasion-album img.wj-media-preview').count(),0);
  await click('library');await wine('cr24');assert.equal(await page.locator('.wj-wine-highlights').count(),0);
  await click('account');await click('signout');await click('find');await wine('cr23');assert.equal(await page.locator('.wj-wine-highlights').count(),0);
  // An isolated data fixture checks image precedence without changing the prototype's sample catalog.
  const imageSrc='data:image/png;base64,'+picture.buffer.toString('base64');
  const fixture=path.join(__dirname,'checks/catalog-cover-fixture.html');
  fs.writeFileSync(fixture,fs.readFileSync(source,'utf8').replace("id:'cr23',brand:","id:'cr23',catalogCover:'"+imageSrc+"',brand:"));
  await page.goto(pathToFileURL(fixture).href);await click('occasions');await page.locator('[data-a=occasion][data-id=o1]').click();
  assert.match(await page.locator('[data-wine-id=cr23] .wj-cover-art img').getAttribute('alt'),/^Catalog bottle image/);
  assert.equal(await page.locator('[data-wine-id=cr23] .wj-cover-art img').evaluate(e=>e.naturalWidth),1);
  fs.writeFileSync(fixture,fs.readFileSync(source,'utf8').replace("id:'cr23',brand:","id:'cr23',coverData:'"+imageSrc+"',catalogCover:'data:image/png;base64,unused',brand:"));
  await page.reload();await click('occasions');await page.locator('[data-a=occasion][data-id=o1]').click();
  assert.match(await page.locator('[data-wine-id=cr23] .wj-cover-art img').getAttribute('alt'),/^Your bottle photo/);
  await page.goto(pathToFileURL(source).href);
  for(const width of [320,390,1024]){
   await page.setViewportSize({width,height:950});await click('library');await wine('cr23');
   const assertFits=async()=>assert.ok(await page.evaluate(()=>document.body.scrollWidth<=innerWidth+1));
   await assertFits();if(width!==320)await page.screenshot({path:path.join(__dirname,'checks/memories-'+width+'-wine.png'),fullPage:true});
   await page.locator('.wj-wine-highlights [data-a=occasion]').first().click();await assertFits();
   if(width!==320)await page.screenshot({path:path.join(__dirname,'checks/memories-'+width+'-occasion.png'),fullPage:true});
  }
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(__dirname,'checks/memory-results.json'),JSON.stringify({passed:['Browse first in both navigation layouts.','One occasion card per wine release, with its bottle cover.','One combined occasion album; duplicates omitted.','Wine photo highlights from its own entries and linked occasion albums.','Repeated entries in one occasion do not repeat its photos.','Repeated uploads in the same album do not make removal ineffective.','View all and return to the source occasion.','Unrelated releases and guests have no personal highlights.','Personal cover precedes catalog image; catalog image precedes placeholder.','Phone and desktop layout fit.'],errors},null,2));
  console.log('PASS: navigation, consolidated occasion wines/media, photo highlights, deduplication, source links, cover precedence, guest privacy, and responsive layouts.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
