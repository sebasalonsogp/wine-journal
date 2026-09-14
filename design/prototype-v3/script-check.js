
(function(){
  const root=document.getElementById('wine-journal-v3');
  const app=root.querySelector('#wj-app');
  const TODAY='2026-09-14';
  const design={paper:'Cream',burgundy:'#722c40',olive:'#555e3f',brown:'#795f4b',frame:'Web',layout:'Cards'};
  const wines=[
    {id:'cr23',brand:'Calculated Risk',name:'Barrel Selection',grape:'Cabernet Sauvignon',region:'Napa Valley',year:'2023',type:'Red',mark:'CR',art:'',family:'barrel',url:'https://calculatedriskwinery.com/products/2023-cabernet-sauvignon-barrel-selection-napa-valley'},
    {id:'cr24',brand:'Calculated Risk',name:'Barrel Selection',grape:'Cabernet Sauvignon',region:'Napa Valley',year:'2024',type:'Red',mark:'CR',art:'wj-art-green',family:'barrel',url:'https://calculatedriskwinery.com/products/napa-valley-barrel-selection-cabernet-sauvignon-2024'},
    {id:'son23',brand:'Calculated Risk',name:'Sonoma County Reserve',grape:'Cabernet Sauvignon',region:'Sonoma County',year:'2023',type:'Red',mark:'CR',art:'wj-art-rose',family:'reserve',url:'https://calculatedriskwinery.com/products/2023-cabernet-sauvignon-reserve-sonoma-county'},
    {id:'hm23',brand:'Calculated Risk',name:'Howell Mountain',grape:'Cabernet Sauvignon',region:'Howell Mountain',year:'2023',type:'Red',mark:'CR',art:'wj-art-green',family:'howell',url:'https://calculatedriskwinery.com/products/howell-mountain-cabernet-sauvignon-2023'},
    {id:'krug',brand:'Krug',name:'Grande Cuvée',grape:'Champagne blend',region:'Champagne',year:'173rd edition · Multi-vintage',type:'Sparkling',mark:'K',art:'',family:'krug',url:'https://www.krug.com/en-int/champagne/krug-grande-cuvee-173eme-edition'}
  ];
  let entries=[
    {id:'e1',wineId:'cr23',date:'2026-09-12',time:'21:00',place:'Bar Sol',notes:'Dark fruit, a little spice, and a lovely long finish. My favourite of the evening.',descriptors:['Fruit','Spice'],occasionId:'o1',media:[{name:'The bottle on our table',type:'photo'}]},
    {id:'e2',wineId:'cr23',date:'2026-06-08',time:'',place:'Home',notes:'Opened with pasta. Would come back to this one.',descriptors:[],occasionId:'',media:[]},
    {id:'e3',wineId:'son23',date:'2026-09-12',time:'19:45',place:'Bar Sol',notes:'Soft and rounded. Really enjoyed this with dinner.',descriptors:['Fruit'],occasionId:'o1',media:[]},
    {id:'e4',wineId:'cr24',date:'2026-09-11',time:'',place:'Wine shop',notes:'A small sample at the counter. Want to spend more time with this vintage.',descriptors:[],occasionId:'',media:[]},
    {id:'e5',wineId:'hm23',date:'2026-06-04',time:'',place:'At home',notes:'Rich and structured. A bottle to remember.',descriptors:[],occasionId:'',media:[]}
  ];
  let occasions=[{id:'o1',title:'Dinner with Alex & Sam',date:'2026-09-12',time:'19:00',place:'Bar Sol',notes:'A long dinner, the corner table, and plenty to catch up on. The little things I want to remember.',media:[{name:'Around the table',type:'photo'},{name:'The last of the evening light',type:'photo'},{name:'A moment from dinner',type:'video'}]}];
  const ratings={cr23:[{value:4,date:'2026-06-08'},{value:4.5,date:'2026-09-12'}],cr24:[],son23:[{value:4,date:'2026-09-12'}],hm23:[{value:4.5,date:'2026-06-04'}]};
  let signedIn=true,screen='library',selectedWine='cr23',selectedOccasion='o1',draft=null,occasionDraft=null;
  let query='',catalogQuery='',filter='All',sort='recent',method='search',photoResults=false,scanFailure=false;
  let captureOccasion='',guideOpen=false,entryDetailsOpen=false,notice='',pending=null,uid=20;
  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon=n=>'<i data-lucide="'+n+'" aria-hidden="true"></i>';
  const wine=id=>wines.find(w=>w.id===id)||(draft?.wineData?.id===id?draft.wineData:null)||occasionDraft?.newEntries?.find(e=>e.wineData?.id===id)?.wineData||(manualWine?.id===id?manualWine:null);
  const occasion=id=>occasions.find(o=>o.id===id);
  const ownEntries=id=>entries.filter(e=>e.wineId===id).sort((a,b)=>b.date.localeCompare(a.date)||b.id.localeCompare(a.id));
  const score=id=>{const r=ratings[id]||[];return r.length?r[r.length-1].value:null;};
  const date=d=>d?new Date(d+'T12:00:00').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):'Date not set';
  const shortDate=d=>d?new Date(d+'T12:00:00').toLocaleDateString('en-GB',{day:'numeric',month:'short'}):'';
  const time=t=>t?t:'';
  const title=o=>o.title||('Occasion · '+shortDate(o.date));
  const button=(label,action,extra='',kind='')=>'<button type="button" class="wj-button '+kind+'" data-a="'+action+'" '+extra+'>'+label+'</button>';
  const textButton=(label,action,extra='')=>'<button type="button" class="wj-text-button" data-a="'+action+'" '+extra+'>'+label+'</button>';
  const back=(label,action,extra='')=>'<div class="wj-back">'+textButton(icon('arrow-left')+label,action,extra)+'</div>';
  const empty=(heading,body,action)=>'<div class="wj-empty"><h2>'+heading+'</h2><p>'+body+'</p>'+action+'</div>';
  const scoreText=id=>score(id)==null?'<span class="wj-small">Not rated</span>':'<span class="wj-score">'+icon('star')+score(id).toFixed(1)+'</span>';
  function art(w){
    const src=w.coverData||w.catalogCover;
    if(src)return `<span class="wj-art wj-cover-art"><img src="${esc(src)}" alt="${w.coverData?'Your bottle photo':'Catalog bottle image'} for ${esc(w.name)}"></span>`;
    return `<span class="wj-art ${w.art||''}" aria-hidden="true"><span class="wj-bottle"><span class="wj-bottle-label">${esc(w.mark)}<small>${esc(w.year.length<6?w.year:'173')}</small></span></span></span>`;
  }

  function wineCard(w){
    const es=ownEntries(w.id);
    return `<button type="button" class="wj-wine-card" data-a="wine" data-id="${w.id}" aria-label="${esc(w.brand+' '+w.name+' '+w.year)}">
      ${art(w)}<span class="wj-card-content"><span class="wj-producer">${esc(w.brand)}</span>
      <span class="wj-wine-name">${esc(w.name)}</span><span class="wj-wine-sub">${esc(w.year)} · ${esc(w.grape)}</span>
      <span class="wj-small">${esc(w.region)}</span><span class="wj-card-bottom">${scoreText(w.id)}<span>Last tried ${shortDate(es[0].date)}</span></span></span></button>`;
  }

  function selectedWineBlock(id){const w=wine(id);return `<div class="wj-selected-wine">${icon('wine')}<div><div>${esc(w.brand)} · ${esc(w.name)}</div><div class="wj-small">${esc(w.year)} · ${esc(w.grape)}</div></div></div>`;}

  function libraryCards(){
    let items=wines.filter(w=>entries.some(e=>e.wineId===w.id));
    items=items.filter(w=>(w.brand+' '+w.name+' '+w.grape+' '+w.region+' '+w.year).toLowerCase().includes(query.toLowerCase())&&(filter==='All'||w.type===filter));
    items.sort((a,b)=>sort==='rating'?(score(b.id)??-1)-(score(a.id)??-1):sort==='name'?a.name.localeCompare(b.name)||b.year.localeCompare(a.year):ownEntries(b.id)[0].date.localeCompare(ownEntries(a.id)[0].date)||a.name.localeCompare(b.name));
    if(!items.length)return empty('No wines match','Try a different search or filter.',textButton('Clear filters','clear-filters'));
    return '<div class="wj-grid">'+items.map(wineCard).join('')+(!query&&filter==='All'?'<button type="button" class="wj-add-card" data-a="find">'+icon('notebook-pen')+'<span class="wj-wine-name">Another wine to remember</span><span>Save a bottle or a glass you tried.</span><span class="wj-text-button">Log a wine '+icon('arrow-right')+'</span></button>':'')+'</div>';
  }

  function library(){
    if(!signedIn)return empty('Your journal starts with a wine.','Look up a bottle whenever you like. Sign in when you want to save your own memories.',button('Find a wine','find','','wj-primary')+' '+button('Sign in','auth'));
    const count=new Set(entries.map(e=>e.wineId)).size;
    return `<div class="wj-page-head"><div><h1>My wines</h1><p class="wj-subtitle wj-serif-subtitle">Wines you’ve tried. Moments worth keeping.</p></div><span class="wj-count">${count} wines · ${entries.length} entries</span></div>
    <div class="wj-toolbar"><label class="wj-search"><span class="wj-label">Search your wines</span><span class="wj-search-wrap">${icon('search')}<input class="wj-input" data-live="library" value="${esc(query)}" placeholder="Name, producer, vintage…" aria-label="Search your wines"></span></label>
    <label><span class="wj-label">Type</span><select class="wj-input" data-live="filter">${['All',...new Set(wines.filter(w=>ownEntries(w.id).length).map(w=>w.type))].map(v=>`<option${filter===v?' selected':''}>${esc(v)}</option>`).join('')}</select></label>
    <label><span class="wj-label">Sort by</span><select class="wj-input" data-live="sort">${[['recent','Recently tried'],['rating','My rating'],['name','Wine name']].map(([v,l])=>`<option value="${v}"${sort===v?' selected':''}>${l}</option>`).join('')}</select></label></div>
    <div id="wj-library-results">${libraryCards()}</div><div class="wj-footer"><span>${icon('lock-keyhole')} Your journal is private</span><span>Every vintage keeps its own story.</span></div>`;
  }

  function entryRow(e){
    const o=occasion(e.occasionId);
    return `<article class="wj-entry"><div class="wj-row"><h3>${date(e.date)}</h3>${textButton('Open entry '+icon('arrow-up-right'),'edit-entry','data-id="'+e.id+'"')}</div>
    <div class="wj-entry-meta">${e.place?`<span>${icon('map-pin')} ${esc(e.place)}</span>`:''}${e.time?`<span>${icon('clock-3')} ${esc(e.time)}</span>`:''}${e.media.length?`<span>${icon('images')} ${e.media.length} ${e.media.length===1?'memory':'memories'}</span>`:''}</div>
    ${e.notes?`<p class="wj-entry-note">${esc(e.notes)}</p>`:'<p class="wj-small">Add a thought whenever you’re ready.</p>'}${o?textButton(icon('notebook')+esc(title(o)),'occasion','data-id="'+o.id+'"'):'<span class="wj-small">Everyday entry · no occasion</span>'}</article>`;
  }

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

  function startEntry(id,oId=''){mediaError='';selectedWine=id;captureOccasion=oId;const o=captureParent();draft={id:'',wineId:id,date:o?o.date:TODAY,time:'',place:o?o.place:'',placeRef:copy(o?.placeRef||null),notes:'',descriptors:[],occasionId:o&&o.id?o.id:'',media:[],...(manualWine&&manualWine.id===id?{wineData:copy(manualWine)}:{})};inlineOccasion=null;placePicker=null;guideOpen=false;entryDetailsOpen=false;go('entry');}
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

  function catalogResults(){let found=wines.filter(w=>!w.ownerOnly).filter(w=>(w.brand+' '+w.name+' '+w.grape+' '+w.year+' '+w.region).toLowerCase().includes(catalogQuery.toLowerCase()));return found.length?found.map(w=>'<div class="wj-result">'+icon('wine')+'<div class="wj-result-info"><div class="wj-small">'+esc(w.brand)+'</div><h3>'+esc(w.name)+'</h3><p class="wj-small">'+esc(w.grape)+' · '+esc(w.year)+'<br>'+esc(w.region)+'</p></div>'+button('View','wine','data-id="'+w.id+'"')+'</div>').join(''):empty('No matching wine','Try a producer name, another spelling, or add the wine yourself.',button('Add wine manually','manual'));}
  function findPage(){const ctx=captureParent();return '<div class="wj-form"><div class="wj-page-head"><div><div class="wj-overline">Discover & remember</div><h1>Find a wine.</h1><p class="wj-subtitle">Scan a code, use a label photo, or search by name.</p></div></div>'+(ctx?'<div class="wj-banner">'+icon('notebook')+'Adding to '+esc(title(ctx))+'</div>':'')+'<div class="wj-methods" aria-label="Find a wine using">'+[['search','search','Search'],['barcode','scan-barcode','Barcode'],['photo','camera','Photo']].map(x=>'<button type="button" data-a="method" data-id="'+x[0]+'" aria-pressed="'+(method===x[0])+'">'+icon(x[1])+x[2]+'</button>').join('')+'</div>'+(method==='search'?'<label><span class="wj-label">Wine, producer, or label wording</span><span class="wj-search-wrap">'+icon('search')+'<input class="wj-input" data-live="catalog" value="'+esc(catalogQuery)+'" placeholder="Try Calculated Risk" aria-label="Search the wine catalog"></span></label><div style="margin-top:19px" id="wj-catalog-results">'+catalogResults()+'</div>':method==='barcode'?'<div class="wj-scan">'+icon('scan-barcode')+'<h3>Place the barcode in view</h3><span class="wj-small">Sample capture for this design walkthrough</span>'+button('Use sample barcode','sample-scan','','wj-primary')+'</div>'+textButton('Try a no-match result','scan-failure')+(scanFailure?'<div class="wj-warning">No wine found for this code. You can search by name or add the wine manually.</div>':''):'<div class="wj-scan">'+icon('camera')+'<h3>A clear photo of the label</h3><span class="wj-small">Sample capture for this design walkthrough</span>'+button('Use sample label photo','sample-photo','','wj-primary')+'</div>'+(photoResults?'<div style="margin-top:23px"><h2>Which bottle is yours?</h2><p class="wj-small" style="margin:8px 0 16px">Check the name, origin, and vintage.</p>'+catalogResults()+'</div>':''))+'<div class="wj-row" style="margin-top:20px"><span class="wj-small">Looking up a wine doesn’t add an entry.</span>'+textButton('Add wine manually','manual')+'</div></div>';}
  function memoryGrid(media,context=''){
    return media.length?'<div class="wj-memory-grid">'+media.map((m,i)=>`<figure class="wj-memory">${memoryPreview(m,i)}<figcaption>${esc(m.name)}</figcaption>${m.ownerType==='entry'?'<p class="wj-memory-origin">'+esc(m.sourceName)+'</p>':''}${context?textButton('Remove','remove-memory','data-ctx="'+context+'" data-index="'+i+'"'):m.ownerType==='entry'?textButton('Open wine entry','edit-entry','data-id="'+m.ownerId+'"'):m.ownerType==='occasion'?textButton('Remove from occasion','remove-memory','data-ctx="occasion" data-index="'+m.ownerIndex+'"'):''}</figure>`).join('')+'</div>':'';
  }

  function memoryScene(){return '<span class="wj-memory-scene" aria-hidden="true"><span class="wj-photo-frame"><span class="wj-photo-block">'+icon('image')+'</span></span><span class="wj-photo-frame"><span class="wj-photo-block wj-photo-olive">'+icon('image')+'</span></span></span>';}
  function occasionList(){if(!signedIn)return empty('Your occasions, kept together.','Sign in to keep your own wine memories.',button('Sign in','auth','','wj-primary'));return '<div class="wj-page-head"><div><div class="wj-overline">The stories around the wine</div><h1>Occasions</h1><p class="wj-subtitle">A dinner, a visit, an evening you want to keep.</p></div>'+button(icon('plus')+'New occasion','new-occasion','','wj-primary')+'</div><div class="wj-occasion-grid">'+occasions.slice().sort((a,b)=>b.date.localeCompare(a.date)).map(o=>'<button type="button" class="wj-occasion-card" data-a="occasion" data-id="'+o.id+'">'+memoryScene()+'<span class="wj-occasion-body"><span class="wj-small">'+date(o.date)+(o.place?' · '+esc(o.place):'')+'</span><span class="wj-wine-name">'+esc(title(o))+'</span><span class="wj-muted">'+entries.filter(e=>e.occasionId===o.id).length+' wine entries · '+o.media.length+' occasion memories</span></span></button>').join('')+'</div><div class="wj-footer"><span>'+icon('lock-keyhole')+' Private to you</span><span>Everyday entries are always in My wines.</span></div>';}
  function occasionPage(){
    if(!signedIn)return occasionList();const o=occasion(selectedOccasion),es=entries.filter(e=>e.occasionId===o.id),wineIds=[...new Set(es.map(e=>e.wineId))];
    return back('Occasions','occasions')+`<div class="wj-occasion-head"><div class="wj-row"><h1>${esc(title(o))}</h1>${textButton(icon('pencil')+'Edit occasion','edit-occasion')}</div><div class="wj-row"><div class="wj-entry-meta"><span>${icon('calendar-days')} ${date(o.date)}</span>${o.time?'<span>'+icon('clock-3')+' '+esc(o.time)+'</span>':''}${o.place?'<span>'+icon('map-pin')+' '+esc(o.place)+'</span>':''}</div><span class="wj-privacy">${icon('lock-keyhole')} Private to you</span></div></div>
    ${o.notes?'<div class="wj-note-paper"><p>'+esc(o.notes)+'</p></div>':''}<section><div class="wj-section-head"><h2>The wines we tried</h2>${button(icon('plus')+'Add wine','occasion-add-wine','','wj-primary')}</div>
    ${es.length?'<div class="wj-occasion-wines">'+wineIds.map(id=>{const w=wine(id),related=es.filter(e=>e.wineId===id);return `<article class="wj-occasion-wine" data-wine-id="${id}"><div class="wj-occasion-wine-heading">${art(w)}<div><div class="wj-row"><span class="wj-producer">${esc(w.brand)}</span><span aria-label="Current personal rating">${scoreText(w.id)}</span></div><h3>${esc(w.name)}</h3><p class="wj-small">${esc(w.year)} · ${esc(w.grape)}</p>${textButton('Wine record '+icon('arrow-up-right'),'wine','data-id="'+w.id+'"')}</div></div>${related.map(e=>`<div class="wj-occasion-entry">${related.length>1?'<p class="wj-small">'+date(e.date)+(e.time?' · '+esc(e.time):'')+'</p>':''}<p class="wj-entry-note">${esc(e.notes||'Add your notes when you’re ready.')}</p>${textButton('Entry & notes','edit-entry','data-id="'+e.id+'"')}</div>`).join('')}</article>`;}).join('')+'</div>':empty('Add the first wine','Find a wine or link an entry you already saved.',button('Add wine','occasion-add-wine'))}${textButton('Link existing entries','edit-occasion')}</section>
    <section class="wj-memories-section wj-occasion-album"><h2>Little moments</h2><p class="wj-subtitle">The people, the place, the things worth keeping.</p>${memoryGrid(occasionMemories(o,es))}${uploadField('occasion')}</section>`;
  }

  function newOccasion(edit=false){const o=edit?occasion(selectedOccasion):null;occasionDraft=o?copy(o):{id:'',title:'',date:TODAY,time:'',place:'',placeRef:null,notes:'',media:[]};occasionDraft.entryIds=o?entries.filter(e=>e.occasionId===o.id).map(e=>e.id):[];occasionDraft.newEntries=[];placePicker=null;captureOccasion='';go('occasion-form');}
  function occasionForm(){const d=occasionDraft,available=entries.filter(e=>!e.occasionId||e.occasionId===d.id);return back(d.id?'Occasion':'Occasions','cancel-occasion')+'<form class="wj-form" data-form="occasion"><div class="wj-page-head"><div><div class="wj-overline">Make room for a memory</div><h1>'+(d.id?'Edit occasion':'A moment, kept together.')+'</h1></div></div>'+occasionFields('occasion')+'<label><span class="wj-label">Occasion notes · optional</span><textarea class="wj-input" data-occasion="notes" placeholder="The people, the food, the things you want to keep…">'+esc(d.notes)+'</textarea></label><section style="margin-top:25px"><div class="wj-section-head"><h2>Wines for this occasion</h2>'+button(icon('plus')+'Add a wine','draft-add-wine')+'</div><p class="wj-small">Find a wine by barcode, photo, search, or add it manually. Return here to add another.</p>'+d.newEntries.map(e=>{const w=e.wineData||wine(e.wineId);return '<div class="wj-staged-entry"><div><h3>'+esc(w.name)+'</h3><p class="wj-small">'+esc(w.year)+' · '+date(e.date)+(e.place?' · '+esc(e.place):'')+'</p></div><div class="wj-actions">'+textButton('Edit','edit-staged','data-id="'+e._key+'"')+textButton('Remove','remove-staged','data-id="'+e._key+'"')+'</div></div>';}).join('')+'</section><details><summary>Link entries you already saved'+(d.entryIds.length?' · '+d.entryIds.length+' selected':'')+'</summary><p class="wj-small" style="margin-bottom:12px">Their original dates, places, notes, and memories stay with them.</p>'+available.map(e=>{const w=wine(e.wineId);return '<label class="wj-check-row"><input type="checkbox" data-existing="'+e.id+'"'+(d.entryIds.includes(e.id)?' checked':'')+'><span>'+esc(w.name)+' · '+esc(w.year)+'<br><span class="wj-small">'+date(e.date)+(e.place?' · '+esc(e.place):'')+'</span></span></label>';}).join('')+'</details><div id="wj-context-warning"></div><div class="wj-form-foot"><span class="wj-small">'+(d.newEntries.length?'New entries will be saved with this occasion.':'You can add wines later, too.')+'</span><button class="wj-button wj-primary" type="submit">Save occasion</button></div></form>';}
  function ratingPage(){
    const w=wine(selectedWine),history=ratings[w.id]||[];
    return back('Wine record','rating-back')+`<form class="wj-form" data-form="rating"><div class="wj-page-head"><div><h1>My rating</h1><p class="wj-subtitle">${esc(w.brand)} · ${esc(w.name)} · ${esc(w.year)}</p></div></div>
    <div class="wj-panel"><label><span class="wj-label">Current personal rating</span><select class="wj-input" name="rating" required><option value="" disabled${score(w.id)==null?' selected':''}>Choose a rating</option>${Array.from({length:9},(_,i)=>1+i*.5).map(v=>`<option value="${v}"${score(w.id)===v?' selected':''}>${v.toFixed(1)} / 5</option>`).join('')}</select></label>
    <p class="wj-rating-help">Your latest opinion of this wine. Previous ratings stay in your history.</p><button type="submit" class="wj-button wj-primary">Update rating</button><p class="wj-small wj-context">Updating a rating does not add a drinking entry.</p></div>
    <div class="wj-section-head wj-history-heading"><h2>Rating history</h2><span class="wj-small">${history.length} ${history.length===1?'rating':'ratings'}</span></div>
    ${history.length?`<ol class="wj-rating-history">${history.slice().reverse().map((r,i)=>`<li><span class="wj-score">${icon('star')}${r.value.toFixed(1)}${i===0?' <span class="wj-chip">Current</span>':''}</span><span class="wj-small">${date(r.date)}${r.time?' · '+esc(r.time):''}</span></li>`).join('')}</ol>`:'<p class="wj-subtitle">Your first rating will appear here.</p>'}</form>`;
  }

  function authPage(){
    const summary=pending==='entry'&&draft?selectedWineBlock(draft.wineId)+`<p class="wj-small wj-context">${date(draft.date)} · Your entry is ready to save.</p>`:'';
    return back(pending?'Back to your draft':'Keep browsing','auth-back')+`<form class="wj-form" data-form="auth"><div class="wj-page-head"><div><h1>Keep this one.</h1><p class="wj-subtitle">Sign in to save your wines and memories.</p></div></div>${summary}<label><span class="wj-label">Email</span><input class="wj-input" type="email" name="email" required autocomplete="email" placeholder="you@example.com"></label><button type="submit" class="wj-button wj-primary wj-field-space">Continue</button><p class="wj-small wj-context">Preview sign-in only. No email is sent.</p></form>`;
  }

  function manualPage(){const d=manualDraft;return back('Find a wine','manual-back')+'<form class="wj-form" data-form="manual"><div class="wj-page-head"><div><div class="wj-overline">Your own record</div><h1>Add a wine.</h1><p class="wj-subtitle">Start with what you know.</p></div></div><div class="wj-cover-picker">'+(d.coverData?'<img class="wj-cover-preview" src="'+esc(d.coverData)+'" alt="Bottle photo preview">':'<div class="wj-cover-preview wj-cover-empty">'+icon('wine')+'</div>')+'<div><label class="wj-upload">Bottle photo · optional<input type="file" accept="image/jpeg,image/png,image/webp" data-cover></label><p class="wj-small">Your wine’s cover in My wines. JPEG, PNG, or WebP.</p>'+(d.coverData?textButton('Remove photo','cover-remove'):'')+'<p id="wj-cover-error" class="wj-error" role="alert">'+esc(d.error||'')+'</p></div></div><label><span class="wj-label">Wine name</span><input class="wj-input" required data-manual="name" value="'+esc(d.name)+'" placeholder="Name or wording from the label"></label><div class="wj-fields"><label><span class="wj-label">Producer · optional</span><input class="wj-input" data-manual="producer" value="'+esc(d.producer)+'"></label><label><span class="wj-label">Vintage · optional</span><input class="wj-input" data-manual="vintage" value="'+esc(d.vintage)+'" placeholder="Unknown"></label></div><p class="wj-small" style="margin-bottom:15px">A personal wine record. This cover photo stays with your personal wine record.</p><button class="wj-button wj-primary" type="submit">Continue to entry</button></form>';}
  function accountPage(){return '<div class="wj-form">'+back('My wines','library')+'<div class="wj-page-head"><div><div class="wj-overline">Your space</div><h1>Your account</h1><p class="wj-subtitle">Your wine journal is private.</p></div></div>'+button('Sign out','signout')+'</div>';}
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

  function refreshIcons(){if(globalThis.lucide)globalThis.lucide.createIcons({attrs:{width:16,height:16}});}
  function go(where){screen=where;notice='';render();}
  function saveEntry(){if(!draft||!draft.date)return;if(captureOccasion==='@draft'){const staged=copy(draft);staged._key=staged._key||'draft'+(++uid);const ix=occasionDraft.newEntries.findIndex(e=>e._key===staged._key);if(ix>=0)occasionDraft.newEntries[ix]=staged;else occasionDraft.newEntries.push(staged);draft=null;manualWine=null;manualDraft=null;captureOccasion='';screen='occasion-form';notice='Wine added to this occasion draft. Add another when you’re ready.';render();return;}let created=null;if(inlineOccasion){created=makeOccasion(inlineOccasion);occasions.push(created);draft.occasionId=created.id;}const saved=commitEntry(draft),parent=captureOccasion;selectedWine=saved.wineId;draft=null;inlineOccasion=null;manualWine=null;manualDraft=null;placePicker=null;captureOccasion='';pending=null;if(created||parent){selectedOccasion=created?created.id:parent;screen='occasion';}else screen='wine';notice=created?'Entry and occasion saved. You can add another wine here.':'Entry saved. Add more detail whenever you like.';render();}
  function saveOccasion(){const d=occasionDraft;if(!d||!d.date)return;const saved=makeOccasion(d);if(d.id)occasions=occasions.map(o=>o.id===d.id?saved:o);else occasions.push(saved);entries=entries.map(e=>d.entryIds.includes(e.id)?{...e,occasionId:saved.id}:e.occasionId===saved.id?{...e,occasionId:''}:e);d.newEntries.forEach(e=>commitEntry({...e,occasionId:saved.id}));selectedOccasion=saved.id;occasionDraft=null;draft=null;pending=null;captureOccasion='';placePicker=null;screen='occasion';notice='Occasion and its new wine entries saved. Existing drinking details were kept.';render();}

  let browseTab='catalog',browseQuery='',selectedGuide='tasting',manualDraft=null,manualWine=null;
  let inlineOccasion=null,placePicker=null,queuedNavigation=null,wineReturn='library';
  const copy=v=>JSON.parse(JSON.stringify(v));
  const samplePlaces=[{id:'sample:bar-sol-napa',name:'Bar Sol',address:'Downtown Napa · sample place'},{id:'sample:bar-sol-sonoma',name:'Bar Sol',address:'Sonoma town centre · sample place'},{id:'sample:olive-table',name:'The Olive Table',address:'San Francisco · sample place'}];
  const guideTopics=[
    {id:'tasting',name:'Find your own tasting words',category:'Notes & tasting',intro:'A few familiar words are enough.',icon:'sprout'},
    {id:'styles',name:'Get to know a wine',category:'Grapes & styles',intro:'Look at grape, style, place, and release together.',icon:'wine'},
    {id:'pairing',name:'Explore food & wine',category:'Pairings',intro:'Notice what a bite of food changes.',icon:'utensils'},
    {id:'regions',name:'Read the place on the label',category:'Regions',intro:'Explore the origin of wines in your journal.',icon:'map-pin'}
  ];
  function captureParent(){return captureOccasion==='@draft'?occasionDraft:occasion(captureOccasion);}
  function findStart(context=''){captureOccasion=context;method='search';catalogQuery='';photoResults=false;scanFailure=false;manualWine=null;go('find');}
  function locationOwner(ctx){return ctx==='entry'?draft:ctx==='inline'?inlineOccasion:occasionDraft;}
  function locationField(ctx){const d=locationOwner(ctx);return '<div class="wj-location"><label><span class="wj-label">Location · optional</span><input class="wj-input" data-location="'+ctx+'" value="'+esc(d.place||'')+'" placeholder="Home, Alex’s house, a restaurant…"></label><div class="wj-row"><span class="wj-small">'+(d.placeRef?'Selected place · '+esc(d.placeRef.address):'Use any personal label.')+'</span>'+textButton(icon('map-pin')+'Find a place','place-open','data-ctx="'+ctx+'"')+'</div>'+((placePicker&&placePicker.ctx===ctx)?'<div class="wj-place-picker"><div class="wj-row"><h3>Find a place</h3>'+textButton('Close','place-close')+'</div><label><span class="wj-label">Place name or town</span><input class="wj-input" data-place-query value="'+esc(placePicker.query)+'" placeholder="Try Bar Sol"></label><p class="wj-small" style="margin:10px 0">Sample suggestions · Google Places connection planned</p><div id="wj-place-results">'+placeResults()+'</div></div>':'')+'</div>';}
  function placeResults(){const q=placePicker.query.toLowerCase().trim();const found=samplePlaces.filter(p=>(p.name+' '+p.address).toLowerCase().includes(q));return found.length?found.map(p=>'<button type="button" class="wj-place-result" data-a="place-select" data-id="'+p.id+'"><span>'+esc(p.name)+'</span><span class="wj-small">'+esc(p.address)+'</span></button>').join(''):'<p class="wj-small">No sample match. Close search and type your own location label.</p>';}
  function occasionFields(ctx){const d=ctx==='inline'?inlineOccasion:occasionDraft;const attr=ctx==='inline'?'data-inline':'data-occasion';return '<label><span class="wj-label">Occasion title · optional</span><input class="wj-input" '+attr+'="title" value="'+esc(d.title)+'" placeholder="Dinner with Alex & Sam"></label><div class="wj-fields"><label><span class="wj-label">Occasion date</span><input class="wj-input" type="date" required '+attr+'="date" value="'+esc(d.date)+'"></label><label><span class="wj-label">Start time · optional</span><input class="wj-input" type="time" '+attr+'="time" value="'+esc(d.time)+'"></label><div class="wj-field-full">'+locationField(ctx)+'</div></div>';}
  function makeOccasion(d){return {id:d.id||'o'+(++uid),title:d.title.trim(),date:d.date,time:d.time,place:d.place,placeRef:copy(d.placeRef||null),notes:d.notes||'',media:copy(d.media||[])};}
  function commitEntry(d){const saved=copy(d);if(saved.wineData&&!wines.some(w=>w.id===saved.wineId)){wines.push({...saved.wineData,ownerOnly:true});ratings[saved.wineId]=[];}delete saved.wineData;delete saved._key;if(saved.id)entries=entries.map(e=>e.id===saved.id?saved:e);else{saved.id='e'+(++uid);entries.push(saved);}return saved;}
  function cancelCapture(){
    const parent=captureOccasion,fromEntry=Boolean(draft);
    draft=null;inlineOccasion=null;manualWine=null;manualDraft=null;placePicker=null;pending=null;captureOccasion='';mediaError='';
    if(parent==='@draft')go('occasion-form');else if(parent){selectedOccasion=parent;go('occasion');}
    else if(fromEntry&&wine(selectedWine))go('wine');else go('library');
  }

  function browseCards(){let items=wines.filter(w=>!w.ownerOnly&&(w.brand+' '+w.name+' '+w.grape+' '+w.region+' '+w.year).toLowerCase().includes(browseQuery.toLowerCase()));return items.length?'<div class="wj-grid">'+items.map(w=>'<button type="button" class="wj-wine-card" data-a="browse-wine" data-id="'+w.id+'">'+art(w)+'<span class="wj-card-content"><span class="wj-producer">'+esc(w.brand)+'</span><span class="wj-wine-name">'+esc(w.name)+'</span><span>'+esc(w.year)+'</span><span class="wj-small">'+esc(w.grape)+' · '+esc(w.region)+'</span><span class="wj-chip">View wine</span></span></button>').join('')+'</div>':empty('No matching wine','Try another name or region.',textButton('Clear search','browse-clear'));}
  function browsePage(){let content='';if(browseTab==='catalog'){content='<label class="wj-search"><span class="wj-label">Search wines, grapes, or regions</span><input class="wj-input" data-live="browse" value="'+esc(browseQuery)+'" placeholder="Try Cabernet Sauvignon or Napa"></label><div id="wj-browse-results" style="margin-top:22px">'+browseCards()+'</div>';}else if(browseTab==='you'){const liked=signedIn?wines.filter(w=>!w.ownerOnly&&score(w.id)>=4):[];content='<div class="wj-guide"><span class="wj-overline">Future discovery concept</span><h2>A starting point for your taste.</h2><p>'+(liked.length?'Your higher-rated sample wines give future suggestions a starting point. There is still plenty to discover.':'Rate wines you’ve tried to give future suggestions a starting point.')+'</p><p class="wj-small">Suggestions will explain why a wine appears and offer “Not for me”. No recommendation service is connected.</p></div>'+(liked.length?'<div class="wj-two-col"><section><h3>Because you enjoyed…</h3>'+selectedWineBlock(liked[0].id)+'<p class="wj-subtitle">Try a related grape, another region, or a new style. Exact matches will depend on the available wine data.</p>'+button('Explore related wines','browse-related','data-query="'+esc(liked[0].grape)+'"')+'</section><aside class="wj-panel"><div class="wj-overline">Learn as you explore</div><h3>What shaped that impression?</h3><p class="wj-subtitle">A few tasting words can help you understand your preferences.</p>'+textButton('Open tasting guide','open-guide','data-id="tasting"')+'</aside></div>':button('Explore the catalog','browse-tab','data-id="catalog"'));}else{content='<div class="wj-guide"><span class="wj-overline">Future community concept</span><h2>What people are enjoying.</h2><p>Trending wines and public reviews will live here.</p><p class="wj-small">This journal has no public activity yet.</p></div><div class="wj-panel"><div class="wj-overline">Illustrative layout · invented sample data</div><h3>Example community wine</h3><p class="wj-subtitle">2023 · Red · Example region</p><div class="wj-actions" style="margin-top:15px"><span class="wj-score">'+icon('star')+'4.3 / 5</span><span class="wj-small">128 public ratings · sample</span><span class="wj-chip">Trending this week · sample</span></div><p class="wj-small" style="margin-top:12px">Community rating and your personal rating will be labeled separately.</p></div>';}return '<div class="wj-page-head"><div><div class="wj-overline">Find your next discovery</div><h1>Browse wines</h1><p class="wj-subtitle">Explore bottles before deciding what to try.</p></div>'+textButton(icon('book-open')+'Wine guides','guides')+'</div><div class="wj-discover-tabs" aria-label="Wine discovery views">'+[['catalog','All wines'],['you','For you'],['trending','Trending']].map(([id,label])=>button(label,'browse-tab','data-id="'+id+'" aria-pressed="'+(browseTab===id)+'"')).join('')+'</div>'+content;}
  function guidesPage(){return '<div class="wj-page-head"><div><div class="wj-overline">A little knowledge, a richer glass</div><h1>Wine guides</h1><p class="wj-subtitle">Start with a question. Find words for what you enjoy.</p></div></div><div class="wj-guide-grid">'+guideTopics.map(g=>'<button type="button" class="wj-guide-card" data-a="open-guide" data-id="'+g.id+'"><span class="wj-overline">'+icon(g.icon)+esc(g.category)+'</span><h2>'+esc(g.name)+'</h2><p>'+esc(g.intro)+'</p><span class="wj-text-button">Explore guide '+icon('arrow-right')+'</span></button>').join('')+'</div>';}
  function guidePage(){const g=guideTopics.find(x=>x.id===selectedGuide);let text='';if(g.id==='tasting')text='<h2>Start with something familiar.</h2><p>Think of a fruit, flower, spice, or other smell you recognise. Write your own words; you do not need a perfect answer.</p><h3>Then notice the feel.</h3><p><strong>Body:</strong> the weight of the wine in your mouth. <strong>Acidity:</strong> the mouth-watering sensation. <strong>Tannin:</strong> the drying or gripping feeling.</p><p>Keep observations alongside the entry from that day. Your current rating belongs to the wine and can change over time.</p><a target="_blank" rel="noopener noreferrer" href="https://www.wsetglobal.com/knowledge-centre/blog/2026/how-to-train-your-palate">Further reading: WSET on training your palate</a>';else if(g.id==='pairing')text='<h2>Notice the change.</h2><p>A bite of food can change how a wine tastes. Sweetness, salt, acidity, fat, and chilli can all affect the impression.</p><p>Sweet food may make a wine seem drier or more bitter. Salty food can soften the impression of tannin. Treat pairings as experiments in what you enjoy.</p><h3>A useful journal prompt</h3><p>“With this food, the wine felt…” Add the dish and your impression to the drinking entry so you can find it again.</p><a target="_blank" rel="noopener noreferrer" href="https://www.wsetglobal.com/knowledge-centre/blog/2023/july/13/four-rules-to-masterful-food-and-wine-pairing">Further reading: WSET food and wine pairing</a>';else if(g.id==='styles')text='<h2>Read the bottle in layers.</h2><p>Start with the producer and wine name, then look for the grape or blend, origin, vintage, and any named edition.</p><p>In the sample catalog, Calculated Risk’s Barrel Selection and Sonoma County Reserve are separate offerings. The 2023 and 2024 Barrel Selection also keep separate records.</p><h3>Explore an example</h3><p>Open a wine’s details without adding it to your journal. Log it only when you want to record trying it.</p>'+button('Browse Cabernet Sauvignon','browse-related','data-query="Cabernet"');else text='<h2>A place worth exploring.</h2><p>Use the origin on a bottle as a starting point. Compare wines from the same place, or follow a grape into another region.</p><p>The sample catalog includes Napa Valley, Sonoma County, Howell Mountain, and Champagne. More detailed region articles and maps are planned.</p><div class="wj-actions">'+button('Explore Napa Valley','browse-related','data-query="Napa"')+button('Explore Champagne','browse-related','data-query="Champagne"')+'</div>';return back('Wine guides','guides')+'<article class="wj-article"><div class="wj-overline">'+esc(g.category)+'</div><h1>'+esc(g.name)+'</h1>'+text+'</article>';}

  function submitPreview(form){if(!mediaBusy&&form&&form.reportValidity())form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}

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

  root.addEventListener('click',event=>{const submit=event.target.closest('button[type="submit"]');if(submit){event.preventDefault();submitPreview(submit.form);}},true);
  root.addEventListener('keydown',event=>{if(event.key==='Enter'&&event.target.tagName==='INPUT'&&event.target.form&&event.target.type!=='file'){event.preventDefault();submitPreview(event.target.form);}});
  const navigationActions=new Set(['library','browse','guides','occasions','find','account','auth','signout','new-occasion']);
  function clearCapture(){mediaError='';draft=null;occasionDraft=null;inlineOccasion=null;manualDraft=null;manualWine=null;captureOccasion='';placePicker=null;pending=null;}
  function navigateAction(a){clearCapture();if(a==='find')findStart();else if(a==='new-occasion')newOccasion();else if(a==='signout'){signedIn=false;go('library');}else go(a);}
  root.addEventListener('click',function(event){
    const b=event.target.closest('button[data-a]');if(!b)return;const a=b.dataset.a,id=b.dataset.id;notice='';
    if(navigationActions.has(a)){if(draft||occasionDraft||manualDraft){queuedNavigation=a;render();return;}navigateAction(a);return;}
    if(a==='keep-editing'){queuedNavigation=null;render();}
    else if(a==='discard-navigation'){const dest=queuedNavigation;queuedNavigation=null;navigateAction(dest);}
    else if(a==='wine'){wineReturn=screen==='find'?'find':screen==='occasion'?'occasion':'library';selectedWine=id;go('wine');}
    else if(a==='return-wine')go(wineReturn);
    else if(a==='browse-wine'){captureOccasion='';wineReturn='browse';selectedWine=id;go('wine');}
    else if(a==='log')startEntry(id,captureOccasion);
    else if(a==='cancel-capture')cancelCapture();
    else if(a==='context-find')go('find');
    else if(a==='edit-entry'){mediaError='';draft=copy(entries.find(e=>e.id===id));selectedWine=draft.wineId;captureOccasion=screen==='occasion'?selectedOccasion:'';inlineOccasion=null;guideOpen=false;entryDetailsOpen=true;go('entry');}
    else if(a==='guide'){guideOpen=!guideOpen;render();}
    else if(a==='descriptor'){const v=b.dataset.value;draft.descriptors=draft.descriptors.includes(v)?draft.descriptors.filter(x=>x!==v):draft.descriptors.concat(v);render();}
    else if(a==='method'){method=id;photoResults=false;scanFailure=false;render();}
    else if(a==='sample-scan'){selectedWine='cr23';wineReturn='find';go('wine');}
    else if(a==='sample-photo'){photoResults=true;catalogQuery='Calculated Risk';render();}
    else if(a==='scan-failure'){scanFailure=true;render();}
    else if(a==='manual'){manualDraft=manualDraft||{name:'',producer:'',vintage:'',coverData:'',error:''};go('manual');}
    else if(a==='manual-back'){manualDraft=null;manualWine=null;go('find');}
    else if(a==='cover-remove'){manualDraft.coverData='';manualDraft.error='';render();}
    else if(a==='other-vintage'){method='search';catalogQuery='Barrel Selection';go('find');}
    else if(a==='clear-filters'){query='';filter='All';render();}
    else if(a==='occasion'){selectedOccasion=id;go('occasion');}
    else if(a==='edit-occasion')newOccasion(true);
    else if(a==='occasion-add-wine')findStart(selectedOccasion);
    else if(a==='draft-add-wine'){placePicker=null;findStart('@draft');}
    else if(a==='cancel-occasion'){const id=occasionDraft.id;occasionDraft=null;placePicker=null;if(id){selectedOccasion=id;go('occasion');}else go('occasions');}
    else if(a==='edit-staged'){draft=copy(occasionDraft.newEntries.find(e=>e._key===id));selectedWine=draft.wineId;captureOccasion='@draft';entryDetailsOpen=true;go('entry');}
    else if(a==='remove-staged'){occasionDraft.newEntries=occasionDraft.newEntries.filter(e=>e._key!==id);render();}
    else if(a==='inline-new'){inlineOccasion={title:'',date:draft.date,time:'',place:draft.place,placeRef:copy(draft.placeRef||null),notes:'',media:[]};placePicker=null;render();}
    else if(a==='inline-cancel'){inlineOccasion=null;placePicker=null;render();}
    else if(a==='place-open'){placePicker={ctx:b.dataset.ctx,query:''};render();}
    else if(a==='place-close'){placePicker=null;render();}
    else if(a==='place-select'){const p=samplePlaces.find(p=>p.id===id),d=locationOwner(placePicker.ctx);d.place=p.name;d.placeRef={id:p.id,source:'sample',address:p.address};placePicker=null;render();}
    else if(a==='rating')go('rating');
    else if(a==='browse-tab'){browseTab=id;go('browse');}
    else if(a==='browse-clear'){browseQuery='';render();}
    else if(a==='browse-related'){browseQuery=b.dataset.query;browseTab='catalog';go('browse');}
    else if(a==='open-guide'){selectedGuide=id;go('guide-article');}
  });
  root.addEventListener('input',function(event){const el=event.target;
    if(el.dataset.draft&&draft)draft[el.dataset.draft]=el.value;
    if(el.dataset.occasion&&occasionDraft){occasionDraft[el.dataset.occasion]=el.value;updateContextWarning();}
    if(el.dataset.inline&&inlineOccasion)inlineOccasion[el.dataset.inline]=el.value;
    if(el.dataset.manual&&manualDraft)manualDraft[el.dataset.manual]=el.value;
    if(el.dataset.location){const d=locationOwner(el.dataset.location);d.place=el.value;d.placeRef=null;const hint=el.closest('.wj-location').querySelector('.wj-row .wj-small');if(hint)hint.textContent='Use any personal label.';updateContextWarning();}
    if(el.hasAttribute('data-place-query')){placePicker.query=el.value;root.querySelector('#wj-place-results').innerHTML=placeResults();}
    if(el.dataset.live==='library'){query=el.value;root.querySelector('#wj-library-results').innerHTML=libraryCards();refreshIcons();}
    if(el.dataset.live==='catalog'){catalogQuery=el.value;root.querySelector('#wj-catalog-results').innerHTML=catalogResults();refreshIcons();}
    if(el.dataset.live==='browse'){browseQuery=el.value;root.querySelector('#wj-browse-results').innerHTML=browseCards();refreshIcons();}
  });
  root.addEventListener('change',function(event){const el=event.target;
    if(el.dataset.live==='filter'||el.dataset.live==='sort'){if(el.dataset.live==='filter')filter=el.value;else sort=el.value;root.querySelector('#wj-library-results').innerHTML=libraryCards();refreshIcons();}
    if(el.dataset.draft&&draft){draft[el.dataset.draft]=el.value;if(el.dataset.draft==='occasionId')render();}
    if(el.dataset.occasion&&occasionDraft){occasionDraft[el.dataset.occasion]=el.value;updateContextWarning();}
    if(el.dataset.inline&&inlineOccasion)inlineOccasion[el.dataset.inline]=el.value;
    if(el.dataset.existing){const id=el.dataset.existing;occasionDraft.entryIds=el.checked?Array.from(new Set(occasionDraft.entryIds.concat(id))):occasionDraft.entryIds.filter(v=>v!==id);updateContextWarning();}
    if(el.hasAttribute('data-cover')){const f=el.files&&el.files[0],target=manualDraft;if(!f||!target)return;if(!['image/jpeg','image/png','image/webp'].includes(f.type)||f.size>8*1024*1024){target.error='Choose a JPEG, PNG, or WebP under 8 MB for this preview.';render();return;}const reader=new FileReader();reader.onload=()=>{if(manualDraft!==target)return;target.coverData=String(reader.result);target.error='';if(screen==='manual')render();};reader.onerror=()=>{if(manualDraft!==target)return;target.error='Could not read this photo. Try another file.';if(screen==='manual')render();};reader.readAsDataURL(f);}
    if(el.dataset.files)loadMemories(el);
  });
  root.addEventListener('submit',function(event){const form=event.target;event.preventDefault();
    if(form.dataset.form==='entry'){if(captureOccasion==='@draft')saveEntry();else if(!signedIn){pending='entry';go('auth');}else saveEntry();}
    else if(form.dataset.form==='occasion'){if(!signedIn){pending='occasion';go('auth');}else saveOccasion();}
    else if(form.dataset.form==='auth'){signedIn=true;if(pending==='entry')saveEntry();else if(pending==='occasion')saveOccasion();else go('library');}
    else if(form.dataset.form==='rating'){const v=Number(new FormData(form).get('rating'));if(score(selectedWine)!==v){if(!ratings[selectedWine])ratings[selectedWine]=[];ratings[selectedWine].push({value:v,date:TODAY,time:new Date().toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'})});}screen='wine';notice='Your current rating is updated. Past ratings are kept.';render();}
    else if(form.dataset.form==='manual'){const d=manualDraft,name=d.name.trim();if(!name){d.error='Add the wine name or wording from its label.';render();return;}const id='w'+(++uid);manualWine={id,brand:d.producer.trim()||'Personal wine record',name,grape:'Grape not added',region:'Origin not added',year:d.vintage.trim()||'Vintage unknown',type:'Unknown',mark:'WJ',art:'',family:id,url:'',coverData:d.coverData,ownerOnly:true};startEntry(id,captureOccasion);}
  });
  root.addEventListener('toggle',function(event){if(event.target.dataset.optional==='entry')entryDetailsOpen=event.target.open;},true);
  function updateContextWarning(){const target=root.querySelector('#wj-context-warning');if(!target||!occasionDraft)return;const different=entries.some(e=>occasionDraft.entryIds.includes(e.id)&&(e.date!==occasionDraft.date||(e.place&&occasionDraft.place&&e.place!==occasionDraft.place)));target.innerHTML=different?'<p class="wj-warning">Some selected entries have a different drinking date or location. Their original details will be kept.</p>':'';}
  function applyDesign(){root.style.setProperty('--wj-paper',design.paper==='Cream'?'#f7f3eb':'#ffffff');root.style.setProperty('--wj-card',design.paper==='Cream'?'#fffdf8':'#ffffff');root.style.setProperty('--wj-burgundy',design.burgundy);root.style.setProperty('--wj-olive',design.olive);root.style.setProperty('--wj-brown',design.brown);root.classList.toggle('wj-phone',design.frame==='Phone');root.classList.toggle('wj-list',design.layout==='List');}
  applyDesign();render();
  if(globalThis.Tweak){const tweak=new Tweak({container:root,onChange:applyDesign});tweak.addSelect(design,'paper',{label:'Light surface',options:['Cream','White']});tweak.addColorPicker(design,'burgundy',{label:'Burgundy',reference:'--wj-burgundy'});tweak.addColorPicker(design,'olive',{label:'Olive',reference:'--wj-olive'});tweak.addColorPicker(design,'brown',{label:'Branch brown',reference:'--wj-brown'});tweak.addSelect(design,'frame',{label:'Screen size',options:['Web','Phone']});tweak.addSelect(design,'layout',{label:'Wine library',options:['Cards','List']});}
})();
