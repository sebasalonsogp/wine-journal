// @replace art
  function art(w){
    const src=w.coverData||w.catalogCover;
    if(src)return `<span class="wj-art wj-cover-art"><img src="${esc(src)}" alt="${w.coverData?'Your bottle photo':'Catalog bottle image'} for ${esc(w.name)}"></span>`;
    return `<span class="wj-art ${w.art||''}" aria-hidden="true"><span class="wj-bottle"><span class="wj-bottle-label">${esc(w.mark)}<small>${esc(w.year.length<6?w.year:'173')}</small></span></span></span>`;
  }
// @replace wineCard
  function wineCard(w){
    const es=ownEntries(w.id);
    return `<button type="button" class="wj-wine-card" data-a="wine" data-id="${w.id}" aria-label="${esc(w.brand+' '+w.name+' '+w.year)}">
      ${art(w)}<span class="wj-card-content"><span class="wj-producer">${esc(w.brand)}</span>
      <span class="wj-wine-name">${esc(w.name)}</span><span class="wj-wine-sub">${esc(w.year)} · ${esc(w.grape)}</span>
      <span class="wj-small">${esc(w.region)}</span><span class="wj-card-bottom">${scoreText(w.id)}<span>Last tried ${shortDate(es[0].date)}</span></span></span></button>`;
  }
// @replace libraryCards
  function libraryCards(){
    let items=wines.filter(w=>entries.some(e=>e.wineId===w.id));
    items=items.filter(w=>(w.brand+' '+w.name+' '+w.grape+' '+w.region+' '+w.year).toLowerCase().includes(query.toLowerCase())&&(filter==='All'||w.type===filter));
    items.sort((a,b)=>sort==='rating'?(score(b.id)??-1)-(score(a.id)??-1):sort==='name'?a.name.localeCompare(b.name)||b.year.localeCompare(a.year):ownEntries(b.id)[0].date.localeCompare(ownEntries(a.id)[0].date)||a.name.localeCompare(b.name));
    if(!items.length)return empty('No wines match','Try a different search or filter.',textButton('Clear filters','clear-filters'));
    return '<div class="wj-grid">'+items.map(wineCard).join('')+(!query&&filter==='All'?'<button type="button" class="wj-add-card" data-a="find">'+icon('notebook-pen')+'<span class="wj-wine-name">Another wine to remember</span><span>Save a bottle or a glass you tried.</span><span class="wj-text-button">Log a wine '+icon('arrow-right')+'</span></button>':'')+'</div>';
  }
// @replace library
  function library(){
    if(!signedIn)return empty('Your journal starts with a wine.','Look up a bottle whenever you like. Sign in when you want to save your own memories.',button('Find a wine','find','','wj-primary')+' '+button('Sign in','auth'));
    const count=new Set(entries.map(e=>e.wineId)).size;
    return `<div class="wj-page-head"><div><h1>My wines</h1><p class="wj-subtitle wj-serif-subtitle">Wines you’ve tried. Moments worth keeping.</p></div><span class="wj-count">${count} wines · ${entries.length} entries</span></div>
    <div class="wj-toolbar"><label class="wj-search"><span class="wj-label">Search your wines</span><span class="wj-search-wrap">${icon('search')}<input class="wj-input" data-live="library" value="${esc(query)}" placeholder="Name, producer, vintage…" aria-label="Search your wines"></span></label>
    <label><span class="wj-label">Type</span><select class="wj-input" data-live="filter">${['All',...new Set(wines.filter(w=>ownEntries(w.id).length).map(w=>w.type))].map(v=>`<option${filter===v?' selected':''}>${esc(v)}</option>`).join('')}</select></label>
    <label><span class="wj-label">Sort by</span><select class="wj-input" data-live="sort">${[['recent','Recently tried'],['rating','My rating'],['name','Wine name']].map(([v,l])=>`<option value="${v}"${sort===v?' selected':''}>${l}</option>`).join('')}</select></label></div>
    <div id="wj-library-results">${libraryCards()}</div><div class="wj-footer"><span>${icon('lock-keyhole')} Your journal is private</span><span>Every vintage keeps its own story.</span></div>`;
  }
// @replace winePage
  function winePage(){
    const w=wine(selectedWine),es=ownEntries(w.id),r=score(w.id);
    return (captureOccasion?'':back(({library:'My wines',browse:'Browse wines',find:'Find a wine',occasion:'Occasion'})[wineReturn]||'My wines','return-wine'))+
      `<div class="wj-record-grid"><section class="wj-hero wj-record-hero">${art(w)}<div><p class="wj-producer">${esc(w.brand)}</p><h1>${esc(w.name)}</h1><p class="wj-release">${esc(w.year)} · ${esc(w.grape)}</p><p class="wj-muted">${icon('map-pin')} ${esc(w.region)}</p><div class="wj-actions">${button(icon('plus')+'Log this wine','log','data-id="'+w.id+'"','wj-primary')}${w.family==='barrel'?textButton('Other vintage '+icon('arrow-right'),'other-vintage'):''}</div></div></section>
      ${signedIn?`<section class="wj-panel wj-record-rating"><h2>My current rating</h2><div class="wj-rating-display"><span class="wj-rating-value">${r==null?'Not rated':r.toFixed(1)}</span>${r==null?'':`<span class="wj-small">/ 5</span>${icon('star')}`}</div><p class="wj-small">${r==null?'Add a rating when you’re ready.':'Your latest rating for this release.'}</p>${textButton('Rating & history '+icon('arrow-right'),'rating')}</section>`:''}
      <section class="wj-panel wj-record-history"><div class="wj-section-head"><h2>Your drinking history</h2>${signedIn?`<span class="wj-small">${es.length} ${es.length===1?'entry':'entries'}</span>`:''}</div>
      ${signedIn?(es.length?es.map(entryRow).join(''):empty('Your first glass, remembered.','Save the date you tried this wine. Notes can come later.',button('Log this wine','log','data-id="'+w.id+'"'))):empty('Keep your own wine story.','Log a wine when you want to save your own notes and memories.',button('Log this wine','log','data-id="'+w.id+'"'))}</section>
      <section class="wj-panel wj-record-specs"><h2>About the wine</h2><dl class="wj-specs"><div><dt>Origin</dt><dd>${esc(w.region)}</dd></div><div><dt>Style</dt><dd>${esc(w.type)}</dd></div><div><dt>Grape / blend</dt><dd>${esc(w.grape)}</dd></div><div><dt>Vintage / edition</dt><dd>${esc(w.year)}</dd></div></dl>
      ${w.url?`<a class="wj-producer-link" href="${esc(w.url)}" target="_blank" rel="noopener noreferrer">Visit producer ${icon('arrow-up-right')}</a>`:''}<p class="wj-small wj-availability">Price and purchase links are not available in this preview.</p></section></div>${winePhotoHighlights(w.id)}`;
  }
// @replace entryRow
  function entryRow(e){
    const o=occasion(e.occasionId);
    return `<article class="wj-entry"><div class="wj-row"><h3>${date(e.date)}</h3>${textButton('Open entry '+icon('arrow-up-right'),'edit-entry','data-id="'+e.id+'"')}</div>
    <div class="wj-entry-meta">${e.place?`<span>${icon('map-pin')} ${esc(e.place)}</span>`:''}${e.time?`<span>${icon('clock-3')} ${esc(e.time)}</span>`:''}${e.media.length?`<span>${icon('images')} ${e.media.length} ${e.media.length===1?'memory':'memories'}</span>`:''}</div>
    ${e.notes?`<p class="wj-entry-note">${esc(e.notes)}</p>`:'<p class="wj-small">Add a thought whenever you’re ready.</p>'}${o?textButton(icon('notebook')+esc(title(o)),'occasion','data-id="'+o.id+'"'):'<span class="wj-small">Everyday entry · no occasion</span>'}</article>`;
  }
// @replace selectedWineBlock
  function selectedWineBlock(id){const w=wine(id);return `<div class="wj-selected-wine">${icon('wine')}<div><div>${esc(w.brand)} · ${esc(w.name)}</div><div class="wj-small">${esc(w.year)} · ${esc(w.grape)}</div></div></div>`;}
// @replace entryPage
  function entryPage(){
    const o=captureParent()||occasion(draft.occasionId),inParent=Boolean(captureOccasion);
    return back(inParent?'Back to occasion':draft.id?'Cancel changes':'Cancel entry','cancel-capture')+
    `<form class="wj-form" data-form="entry"><div class="wj-page-head"><div><h1>${draft.id?'Your wine entry':'I tried this wine.'}</h1><p class="wj-subtitle">${draft.id?'Come back to the details, whenever you like.':'The wine and date are all you need.'}</p></div></div>
    ${selectedWineBlock(draft.wineId)}<label class="wj-date-field"><span class="wj-label">Date tried</span><input class="wj-input" type="date" required data-draft="date" value="${esc(draft.date)}"></label>
    ${o?`<p class="wj-small wj-context">For ${esc(title(o))}. This entry keeps its own date and place.</p>`:''}
    <label class="wj-quick-note"><span class="wj-label">${draft.id?'Personal notes':'Quick notes'} · optional</span><textarea class="wj-input" rows="2" data-draft="notes" placeholder="A first impression, the food, something to remember…">${esc(draft.notes)}</textarea></label>
    ${textButton(icon('sprout')+(guideOpen?'Hide tasting prompts':'Help me describe it'),'guide','aria-expanded="'+guideOpen+'"')}
    ${guideOpen?`<div class="wj-guide"><h2>Start with what you notice.</h2><p>What familiar smells or flavours come to mind?</p><div class="wj-descriptors">${['Fruit','Floral','Spice','Earthy'].map(t=>button(t,'descriptor','data-value="'+t+'" aria-pressed="'+draft.descriptors.includes(t)+'"')).join('')}</div><p class="wj-small">Body: weight in your mouth. Acidity: mouth-watering. Tannin: a drying feeling.</p></div>`:''}
    <details data-optional="entry"${entryDetailsOpen?' open':''}><summary>Add details <span class="wj-small">Time, place, occasion & memories</span></summary>
    <label><span class="wj-label">Time · optional</span><input class="wj-input" type="time" data-draft="time" value="${esc(draft.time)}"></label><div class="wj-field-space">${locationField('entry')}</div>
    ${!inParent?`<div class="wj-field-space"><label><span class="wj-label">Occasion · optional</span><select class="wj-input" data-draft="occasionId"${inlineOccasion?' disabled':''}><option value="">No occasion</option>${occasions.map(x=>`<option value="${x.id}"${draft.occasionId===x.id?' selected':''}>${esc(title(x))}</option>`).join('')}</select></label>
    ${!inlineOccasion?textButton(icon('plus')+'Create new occasion','inline-new'):`<section class="wj-inline-occasion"><div class="wj-row"><h2>New occasion</h2>${textButton('Cancel new occasion','inline-cancel')}</div>${occasionFields('inline')}<p class="wj-small">Save this occasion with your entry, then add more wines from its scrapbook.</p></section>`}</div>`:''}
    <section class="wj-field-space"><h2>Photos & videos <span class="wj-small">optional</span></h2>${memoryGrid(draft.media,'entry')}${uploadField('entry')}</section></details>
    <div class="wj-form-foot"><span class="wj-privacy">${icon('lock-keyhole')} Private to you</span><button class="wj-button wj-primary" type="submit"${mediaBusy?' disabled':''}>${captureOccasion==='@draft'?'Add to occasion':!signedIn?'Sign in to save':inlineOccasion?'Save entry & occasion':draft.id?'Save changes':'Save entry'}</button></div></form>`;
  }
// @replace ratingPage
  function ratingPage(){
    const w=wine(selectedWine),history=ratings[w.id]||[];
    return back('Wine record','rating-back')+`<form class="wj-form" data-form="rating"><div class="wj-page-head"><div><h1>My rating</h1><p class="wj-subtitle">${esc(w.brand)} · ${esc(w.name)} · ${esc(w.year)}</p></div></div>
    <div class="wj-panel"><label><span class="wj-label">Current personal rating</span><select class="wj-input" name="rating" required><option value="" disabled${score(w.id)==null?' selected':''}>Choose a rating</option>${Array.from({length:9},(_,i)=>1+i*.5).map(v=>`<option value="${v}"${score(w.id)===v?' selected':''}>${v.toFixed(1)} / 5</option>`).join('')}</select></label>
    <p class="wj-rating-help">Your latest opinion of this wine. Previous ratings stay in your history.</p><button type="submit" class="wj-button wj-primary">Update rating</button><p class="wj-small wj-context">Updating a rating does not add a drinking entry.</p></div>
    <div class="wj-section-head wj-history-heading"><h2>Rating history</h2><span class="wj-small">${history.length} ${history.length===1?'rating':'ratings'}</span></div>
    ${history.length?`<ol class="wj-rating-history">${history.slice().reverse().map((r,i)=>`<li><span class="wj-score">${icon('star')}${r.value.toFixed(1)}${i===0?' <span class="wj-chip">Current</span>':''}</span><span class="wj-small">${date(r.date)}${r.time?' · '+esc(r.time):''}</span></li>`).join('')}</ol>`:'<p class="wj-subtitle">Your first rating will appear here.</p>'}</form>`;
  }
// @replace cancelCapture
  function cancelCapture(){
    const parent=captureOccasion,fromEntry=Boolean(draft);
    draft=null;inlineOccasion=null;manualWine=null;manualDraft=null;placePicker=null;pending=null;captureOccasion='';mediaError='';
    if(parent==='@draft')go('occasion-form');else if(parent){selectedOccasion=parent;go('occasion');}
    else if(fromEntry&&wine(selectedWine))go('wine');else go('library');
  }
// @replace authPage
  function authPage(){
    const summary=pending==='entry'&&draft?selectedWineBlock(draft.wineId)+`<p class="wj-small wj-context">${date(draft.date)} · Your entry is ready to save.</p>`:'';
    return back(pending?'Back to your draft':'Keep browsing','auth-back')+`<form class="wj-form" data-form="auth"><div class="wj-page-head"><div><h1>Keep this one.</h1><p class="wj-subtitle">Sign in to save your wines and memories.</p></div></div>${summary}<label><span class="wj-label">Email</span><input class="wj-input" type="email" name="email" required autocomplete="email" placeholder="you@example.com"></label><button type="submit" class="wj-button wj-primary wj-field-space">Continue</button><p class="wj-small wj-context">Preview sign-in only. No email is sent.</p></form>`;
  }
// @replace memoryGrid
  function memoryGrid(media,context=''){
    return media.length?'<div class="wj-memory-grid">'+media.map((m,i)=>`<figure class="wj-memory">${memoryPreview(m,i)}<figcaption>${esc(m.name)}</figcaption>${m.ownerType==='entry'?'<p class="wj-memory-origin">'+esc(m.sourceName)+'</p>':''}${context?textButton('Remove','remove-memory','data-ctx="'+context+'" data-index="'+i+'"'):m.ownerType==='entry'?textButton('Open wine entry','edit-entry','data-id="'+m.ownerId+'"'):m.ownerType==='occasion'?textButton('Remove from occasion','remove-memory','data-ctx="occasion" data-index="'+m.ownerIndex+'"'):''}</figure>`).join('')+'</div>':'';
  }
// @replace occasionPage
  function occasionPage(){
    if(!signedIn)return occasionList();const o=occasion(selectedOccasion),es=entries.filter(e=>e.occasionId===o.id),wineIds=[...new Set(es.map(e=>e.wineId))];
    return back('Occasions','occasions')+`<div class="wj-occasion-head"><div class="wj-row"><h1>${esc(title(o))}</h1>${textButton(icon('pencil')+'Edit occasion','edit-occasion')}</div><div class="wj-row"><div class="wj-entry-meta"><span>${icon('calendar-days')} ${date(o.date)}</span>${o.time?'<span>'+icon('clock-3')+' '+esc(o.time)+'</span>':''}${o.place?'<span>'+icon('map-pin')+' '+esc(o.place)+'</span>':''}</div><span class="wj-privacy">${icon('lock-keyhole')} Private to you</span></div></div>
    ${o.notes?'<div class="wj-note-paper"><p>'+esc(o.notes)+'</p></div>':''}<section><div class="wj-section-head"><h2>The wines we tried</h2>${button(icon('plus')+'Add wine','occasion-add-wine','','wj-primary')}</div>
    ${es.length?'<div class="wj-occasion-wines">'+wineIds.map(id=>{const w=wine(id),related=es.filter(e=>e.wineId===id);return `<article class="wj-occasion-wine" data-wine-id="${id}"><div class="wj-occasion-wine-heading">${art(w)}<div><div class="wj-row"><span class="wj-producer">${esc(w.brand)}</span><span aria-label="Current personal rating">${scoreText(w.id)}</span></div><h3>${esc(w.name)}</h3><p class="wj-small">${esc(w.year)} · ${esc(w.grape)}</p>${textButton('Wine record '+icon('arrow-up-right'),'wine','data-id="'+w.id+'"')}</div></div>${related.map(e=>`<div class="wj-occasion-entry">${related.length>1?'<p class="wj-small">'+date(e.date)+(e.time?' · '+esc(e.time):'')+'</p>':''}<p class="wj-entry-note">${esc(e.notes||'Add your notes when you’re ready.')}</p>${textButton('Entry & notes','edit-entry','data-id="'+e.id+'"')}</div>`).join('')}</article>`;}).join('')+'</div>':empty('Add the first wine','Find a wine or link an entry you already saved.',button('Add wine','occasion-add-wine'))}${textButton('Link existing entries','edit-occasion')}</section>
    <section class="wj-memories-section wj-occasion-album"><h2>Little moments</h2><p class="wj-subtitle">The people, the place, the things worth keeping.</p>${memoryGrid(occasionMemories(o,es))}${uploadField('occasion')}</section>`;
  }
// @replace render
  function render(){
    const currentDetails=root.querySelector('details[data-optional="entry"]');
    if(currentDetails&&lastRenderedScreen===screen&&screen==='entry')entryDetailsOpen=currentDetails.open;
    const screens={library,wine:winePage,entry:entryPage,find:findPage,occasions:occasionList,occasion:occasionPage,'occasion-form':occasionForm,rating:ratingPage,auth:authPage,manual:manualPage,account:accountPage,browse:browsePage,guides:guidesPage,'guide-article':guidePage};
    const oldFocus=document.activeElement,focusAction=root.contains(oldFocus)?oldFocus.dataset.a:null,focusId=oldFocus?.dataset?.id;
    let body=(screens[screen]||library)();
    if(screen==='find'&&captureOccasion)body=back('Back to occasion','cancel-capture')+body;
    if(screen==='wine'&&captureOccasion)body=back('Back to wine search','context-find')+body;
    const nav=[['browse','compass','Browse'],['library','book-open','My wines'],['occasions','notebook','Occasions'],['guides','book-open-text','Guides']];
    const active=['wine','entry','rating'].includes(screen)?'library':['occasion','occasion-form'].includes(screen)?'occasions':screen==='guide-article'?'guides':screen;
    const navLinks=(mobile=false)=>nav.map(([id,ic,label])=>`<button type="button" data-a="${id}"${active===id?' aria-current="page"':''}>${mobile?icon(ic):''}<span>${!mobile&&id==='browse'?'Browse wines':label}</span></button>`).join('');
    app.innerHTML=`<header class="wj-topbar"><button type="button" class="wj-brand" data-a="library"><span class="wj-brand-mark">${icon('wine')}</span><span>Wine Journal</span></button><nav class="wj-nav" aria-label="Main navigation">${navLinks()}</nav><div class="wj-top-actions">${button(icon('plus')+'Log wine','find','','wj-primary')}<button type="button" class="wj-button wj-account" data-a="${signedIn?'account':'auth'}" aria-label="${signedIn?'Your account':'Sign in'}">${icon('user-round')}<span>${signedIn?'Account':'Sign in'}</span></button></div></header>
    <main class="wj-main" data-screen="${screen}">${notice?'<div class="wj-banner" role="status">'+icon('check')+esc(notice)+'</div>':''}${queuedNavigation?'<section class="wj-warning" role="alert"><h2>Leave this unfinished form?</h2><p>Your unsaved entry and occasion changes will be discarded.</p><div class="wj-actions">'+button('Keep editing','keep-editing')+button('Discard and continue','discard-navigation')+'</div></section>':''}${body}</main>
    <nav class="wj-mobile-nav" aria-label="Mobile navigation">${navLinks(true)}</nav><footer class="wj-preview-footer"><span>Design walkthrough · sample journal</span><span>Changes reset when you reload</span></footer>`;
    refreshIcons();updateContextWarning();
    if(focusAction&&lastRenderedScreen===screen){const match=Array.from(root.querySelectorAll('button[data-a]')).find(b=>b.dataset.a===focusAction&&b.dataset.id===focusId);if(match)match.focus({preventScroll:true});}
    if(lastRenderedScreen&&lastRenderedScreen!==screen){root.querySelector('main').scrollIntoView({block:'start'});const first=root.querySelector('main button,main input,main select');if(first)first.focus({preventScroll:true});}
    lastRenderedScreen=screen;
  }
// @extra
  let mediaBusy=false,mediaError='',lastRenderedScreen='',expandedWineMemories='';
  function memoryPreview(m,i=0){
    if(m.src)return m.type==='video'?`<video class="wj-media-preview" controls preload="metadata" playsinline src="${esc(m.src)}" aria-label="${esc(m.name)}"></video>`:`<img class="wj-media-preview" src="${esc(m.src)}" alt="${esc(m.name)}">`;
    return `<div class="wj-photo-block ${i%2?'wj-photo-olive':''}">${icon(m.type==='video'?'film':'image')}<span class="wj-small">${m.type==='video'?'Video memory':'Photo memory'} · sample</span></div>`;
  }
  function taggedMemories(owner,ownerType){
    const sourceName=ownerType==='occasion'?title(owner):wine(owner.wineId).name+' · '+wine(owner.wineId).year;
    return owner.media.map((m,i)=>({...m,ownerType,ownerId:owner.id,ownerIndex:i,sourceName,sourceDate:owner.date}));
  }
  function uniqueMemories(items){
    const seen=new Set();return items.filter(m=>{const key=m.src||m.id||(m.ownerType+':'+m.ownerId+':'+m.ownerIndex);if(seen.has(key))return false;seen.add(key);return true;});
  }
  function occasionMemories(o,es){return uniqueMemories([...taggedMemories(o,'occasion'),...es.flatMap(e=>taggedMemories(e,'entry'))]);}
  function winePhotoHighlights(id){
    if(!signedIn||captureOccasion)return '';
    const es=ownEntries(id),occasionIds=new Set(es.map(e=>e.occasionId).filter(Boolean));
    const photos=uniqueMemories([...occasions.filter(o=>occasionIds.has(o.id)).flatMap(o=>taggedMemories(o,'occasion')),...es.flatMap(e=>taggedMemories(e,'entry'))].filter(m=>m.type==='photo').sort((a,b)=>b.sourceDate.localeCompare(a.sourceDate)));
    if(!photos.length)return '';
    const expanded=expandedWineMemories===id,shown=expanded?photos:photos.slice(0,3);
    return `<section class="wj-memories-section wj-wine-highlights"><div class="wj-section-head"><div><h2>Moments with this wine</h2><p class="wj-subtitle">Photos from your entries and the occasions you shared.</p></div>${photos.length>3?textButton(expanded?'Show highlights':'View all '+photos.length+' photos','toggle-wine-memories','aria-expanded="'+expanded+'"'):''}</div><div class="wj-memory-grid">${shown.map((m,i)=>{const action=m.ownerType==='occasion'?'occasion':'edit-entry';return `<figure class="wj-memory"><button type="button" class="wj-memory-open" data-a="${action}" data-id="${m.ownerId}" aria-label="Open ${esc(m.sourceName)}: ${esc(m.name)}">${memoryPreview(m,i)}</button><figcaption>${esc(m.name)}</figcaption><p class="wj-memory-origin">${date(m.sourceDate)}</p>${textButton((m.ownerType==='occasion'?icon('notebook'):'')+esc(m.ownerType==='occasion'?m.sourceName:'Open wine entry'),action,'data-id="'+m.ownerId+'"')}</figure>`;}).join('')}</div></section>`;
  }
  function uploadField(context){return `<label class="wj-upload">${icon('images')} Add photos or a short video<input type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm" multiple data-files="${context}"${mediaBusy?' disabled':''}></label><p class="wj-small">Local preview · images up to 8 MB, videos up to 25 MB.</p>${mediaBusy?'<p role="status" class="wj-small">Preparing your memories…</p>':''}${mediaError?'<p role="alert" class="wj-error">'+esc(mediaError)+'</p>':''}`;}
  function loadMemories(input){
    const target=input.dataset.files==='entry'?draft:occasion(selectedOccasion),files=Array.from(input.files||[]),originScreen=screen;
    if(!target||!files.length||mediaBusy)return;
    const supported=f=>['image/jpeg','image/png','image/webp','video/mp4','video/webm'].includes(f.type)&&f.size<=(f.type.startsWith('video/')?25:8)*1024*1024;
    if(files.some(f=>!supported(f))){mediaError='Choose JPEG, PNG, or WebP images up to 8 MB, or MP4/WebM videos up to 25 MB. Try a smaller or supported file.';render();return;}
    mediaBusy=true;mediaError='';render();
    Promise.all(files.map(f=>new Promise((resolve,reject)=>{const r=new FileReader();r.onerror=()=>reject(new Error('Could not read this file.'));r.onload=()=>resolve({name:f.name,type:f.type.startsWith('video/')?'video':'photo',src:String(r.result)});r.readAsDataURL(f);}))).then(items=>{if(target===draft||occasions.includes(target)){const seen=new Set(target.media.map(m=>m.src).filter(Boolean));target.media.push(...items.filter(m=>{if(seen.has(m.src))return false;seen.add(m.src);return true;}));}}).catch(()=>{mediaError='Could not read these memories. Please try again.';}).finally(()=>{mediaBusy=false;if(screen===originScreen)render();});
  }
  root.addEventListener('click',function(event){
    const b=event.target.closest('button[data-a]');if(!b)return;
    if(b.dataset.a==='rating-back'){event.stopImmediatePropagation();go('wine');}
    if(b.dataset.a==='toggle-wine-memories'){event.stopImmediatePropagation();expandedWineMemories=expandedWineMemories===selectedWine?'':selectedWine;render();}
    if(b.dataset.a==='auth-back'){event.stopImmediatePropagation();if(pending==='entry')go('entry');else if(pending==='occasion')go('occasion-form');else go('browse');}
    if(b.dataset.a==='remove-memory'){event.stopImmediatePropagation();const owner=b.dataset.ctx==='entry'?draft:occasion(selectedOccasion);owner.media.splice(Number(b.dataset.index),1);render();}
  });
