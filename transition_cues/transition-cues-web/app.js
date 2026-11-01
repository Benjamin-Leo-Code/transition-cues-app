'use strict';
const $ = s => document.querySelector(s);
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const app = $('#app');
let state, selected = {places:null, transport:null, items:[], people:[]}, category = 'places', locked = null, taps = [], pendingDelete = null;
let toastTimer, pendingJourney = null, pendingEdit = null, itemsReviewed = false, reorderBusy = false, settingsTabFocus = false;
function toast(message) { $('#toast').textContent = message; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true, 4500); }
async function api(path, data) {
  let response;
  try { response = await fetch('/api/' + path, data === undefined ? {cache:'no-store'} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}); }
  catch { throw new Error('Cannot reach ReadySteady. Check your Wi-Fi and try again.'); }
  let result;
  try { result = await response.json(); } catch { throw new Error('The server returned an unexpected response. Please try again.'); }
  if (!response.ok) throw new Error(result.error || 'Something went wrong. Please try again.');
  return result;
}
async function refresh() { state = await api('state'); state.items ??= []; state.people ??= []; }
const libraryIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 7"/></svg>';
const settingsIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><polygon points="20.00,12.00 21.81,13.95 21.24,15.83 18.65,16.44 17.66,17.66 17.56,20.31 15.83,21.24 13.56,19.85 12.00,20.00 10.05,21.81 8.17,21.24 7.56,18.65 6.34,17.66 3.69,17.56 2.76,15.83 4.15,13.56 4.00,12.00 2.19,10.05 2.76,8.17 5.35,7.56 6.34,6.34 6.44,3.69 8.17,2.76 10.44,4.15 12.00,4.00 13.95,2.19 15.83,2.76 16.44,5.35 17.66,6.34 20.31,6.44 21.24,8.17 19.85,10.44"/><circle cx="12" cy="12" r="3"/></svg>';
function frame(content, route) {
  document.body.classList.remove('lock-active');
  app.innerHTML = `<div class="shell"><header class="header ${route==='choose'?'':'subpage-header'}">${route==='choose'?'<a class="brand" href="#choose"><img src="/icon.svg" alt=""><span>ReadySteady<small>Transition Cues</small></span></a>':'<a class="back-plan secondary" href="#choose"><span aria-hidden="true">←</span> Back to plan</a>'}${route==='choose'?`<nav class="nav" aria-label="Main navigation">${[['manage','Picture library',libraryIcon],['settings','Settings',settingsIcon]].map(([r,t,icon])=>`<a class="icon-link" href="#${r}" aria-label="${t}" title="${t}" ${route===r?'aria-current="page"':''}>${icon}</a>`).join('')}</nav>`:''}${state.returnUrl ? `<a class="return-link" href="${esc(state.returnUrl)}">← Back to main screen</a>` : ''}</header>${content}</div>`;
}
function intro(title, description, extra='') { return `<div class="intro"><div><h1>${title}</h1>${description?`<p>${description}</p>`:''}</div>${extra}</div>`; }

function settingsHeader(section) {
  return intro('Settings')+`<div class="settings-segments" role="tablist" aria-label="Settings sections">${[['photos','Add photos',libraryIcon],['more','More settings',settingsIcon]].map(([key,label,icon])=>`<button type="button" role="tab" id="settingsTab-${key}" aria-selected="${key===section}" aria-controls="settingsPanel" tabindex="${key===section?'0':'-1'}" data-settings-section="${key}">${icon}<span>${label}</span></button>`).join('')}</div>`;
}
function wireSettingsSections(section) {
  const tabs=[...app.querySelectorAll('[data-settings-section]')];
  function selectTab(tab) {
    const target=tab.dataset.settingsSection==='photos'?'#settings':'#settings-more';
    if(tab.dataset.settingsSection===section){tab.focus();return;}
    settingsTabFocus=true;location.hash=target;
  }
  tabs.forEach((tab,index)=>{
    tab.onclick=()=>selectTab(tab);
    tab.onkeydown=e=>{
      const next={ArrowLeft:(index+1)%2,ArrowRight:(index+1)%2,Home:0,End:1}[e.key];
      if(next===undefined)return;
      e.preventDefault();selectTab(tabs[next]);
    };
  });
  if(settingsTabFocus){$('#settingsTab-'+section).focus({preventScroll:true});settingsTabFocus=false;}
}
const MAX_BRING_ITEMS = 4;
function empty(kind) {
  const content = {
    places:['⌂','A familiar place to start','a photo of a familiar place','a place'],
    transport:['↗','How will we get there?','a photo of your car, a bus, walking, or another way to travel','transport'],
    items:['＋','What shall we bring?','photos of things to take, like a drink, headphones or a favourite toy','an item'],
    people:['☺','Who is coming along?','a photo of someone who joins your journeys','a person']
  }[kind];
  return `<div class="empty"><div class="empty-symbol" aria-hidden="true">${content[0]}</div><h3>${content[1]}</h3><p>Add ${content[2]}.<br>Real, familiar pictures make each journey easier to recognise.</p><a class="secondary" href="#manage">Add ${content[3]} <span aria-hidden="true">＋</span></a></div>`;
}
function renderChoose() {
  for (const k of ['places','transport']) if (selected[k]) selected[k] = state[k].find(x=>x.id===selected[k].id) || null;
  selected.items = selected.items.map(item=>state.items.find(x=>x.id===item.id)).filter(Boolean).slice(0,MAX_BRING_ITEMS);
  selected.people = selected.people.map(person=>state.people.find(x=>x.id===person.id)).filter(Boolean);
  if(!selected.places){selected.transport=null;selected.items=[];selected.people=[];itemsReviewed=false;}
  if(!selected.transport){selected.items=[];selected.people=[];itemsReviewed=false;}
  const stepReady={places:true,transport:!!selected.places,items:!!(selected.places&&selected.transport),people:!!(selected.places&&selected.transport&&(itemsReviewed||selected.items.length||!state.items.length))};
  frame(intro('Where are we going?', 'Choose a place, how you’ll get there, and anything to bring along.', '<span class="pill">A moment of calm before you go</span>') +
    ['places','transport','items','people'].map((kind,i)=>{
      const multi = kind==='items' || kind==='people', ready=stepReady[kind];
      return `<section class="step ${ready?'':'step-inactive'}" aria-disabled="${!ready}" aria-labelledby="${kind}Heading"><div class="step-heading"><div class="step-title"><h2 id="${kind}Heading"><span class="step-number">${i+1}</span>${['Choose a place','Choose how to get there','Items to bring along','People'][i]}</h2>${multi?'<p class="step-optional">Optional</p>':''}</div>${multi?`<small id="${kind==='items'?'itemCount':'peopleCount'}" role="status">${kind==='items' ? `${selected.items.length} of ${MAX_BRING_ITEMS} selected` : `${selected.people.length} selected`}</small>`:''}</div>${multi?`<p class="step-help">${kind==='items'?'Choose up to 4 items.':'Choose the people coming along, or leave this empty.'} Tap a selected picture again to remove it.</p>`:''}${!ready?`<p class="step-prerequisite">${kind==='transport'?'Choose a place first.':kind==='items'?'Choose transport first.':'Choose items or skip that step first.'}</p>`:''}${kind==='items'&&ready&&!itemsReviewed&&!selected.items.length&&state.items.length?'<button id="skipItems" type="button" class="secondary skip-items">No items to bring →</button>':''}<div class="step-options" ${ready?'':'inert'}>${state[kind].length ? `<div class="grid">${state[kind].map(x=>{
        const active = multi ? selected[kind].some(item=>item.id===x.id) : selected[kind]?.id===x.id;
        const atLimit = kind==='items' && !active && selected.items.length>=MAX_BRING_ITEMS;
        return `<button class="picture ${kind==='people'?'person-picture':''} ${active?'selected':''}" data-kind="${kind}" data-id="${x.id}" aria-pressed="${active}" ${atLimit||!ready?'disabled':''}><img src="${esc(x.image)}" alt=""><span class="check" aria-hidden="true">✓</span><span class="name">${esc(x.name)}</span></button>`;
      }).join('')}</div>` : empty(kind)}</div></section>`;
    }).join('')+
    `<div class="journey-bar" ${selected.places?'':'hidden'}><div><strong>${selected.places && selected.transport ? `${esc(selected.places.name)} · ${esc(selected.transport.name)}${selected.items.length ? ` · ${selected.items.length} to bring` : ''}` : 'Choose a place and transport to continue'}</strong></div><button id="start" class="primary" ${selected.places&&selected.transport?'':'disabled'}>Show the plan <span aria-hidden="true">→</span></button></div>`, 'choose');
  app.querySelectorAll('[data-kind]').forEach(button => button.onclick = () => {
    const {kind,id} = button.dataset;
    const item = state[kind].find(x=>x.id===id);
    if(!stepReady[kind])return;
    if(kind==='items')itemsReviewed=true;
    if(kind==='items' || kind==='people') {
      if(selected[kind].some(x=>x.id===id)) selected[kind]=selected[kind].filter(x=>x.id!==id);
      else if(kind==='people' || selected.items.length<MAX_BRING_ITEMS) selected[kind].push(item);
      else return;
    } else selected[kind] = item;
    renderChoose();
    app.querySelector(`[data-kind="${kind}"][data-id="${id}"]`)?.focus({preventScroll:true});
  });
  if($('#skipItems'))$('#skipItems').onclick=()=>{itemsReviewed=true;renderChoose();$('#peopleHeading').scrollIntoView({block:'nearest'});};
  $('#start').onclick = () => {
    if(!selected.places||!selected.transport)return;
    pendingJourney = {places:selected.places, transport:selected.transport, items:selected.items.slice(0,MAX_BRING_ITEMS), people:[...selected.people]};
    let skip=false;
    try { skip=localStorage.getItem('tc-skip-plan-intro')==='true'; } catch {}
    if(skip)beginJourney();
    else { $('#skipPlanIntro').checked=false; $('#planDialog').showModal(); }
  };
}
function beginJourney() {
  if(!pendingJourney)return;
  try { localStorage.setItem('tc-locked-journey', JSON.stringify(pendingJourney)); }
  catch { toast('Allow browser storage so the locked display can survive a refresh.'); return; }
  if($('#planDialog').open && $('#skipPlanIntro').checked) {
    try { localStorage.setItem('tc-skip-plan-intro','true'); }
    catch { toast('Your plan can start, but this browser could not remember the splash screen setting.'); }
  }
  locked=pendingJourney; pendingJourney=null; taps=[];
  $('#planDialog').close(); renderLocked();
  document.documentElement.requestFullscreen?.().catch(()=>{});
  if ('wakeLock' in navigator) navigator.wakeLock.request('screen').catch(()=>{});
}
$('#planForm').onsubmit=e=>{e.preventDefault();beginJourney();};
$('#planBack').onclick=()=>$('#planDialog').close();
$('#planDialog').addEventListener('close',()=>{pendingJourney=null;});

function finishJourney() {
  try { localStorage.removeItem('tc-locked-journey'); }
  catch { toast('Allow browser storage to finish this saved plan.');return; }
  selected={places:locked.places,transport:locked.transport,items:locked.items||[],people:locked.people||[]};
  state ??= {places:[locked.places],transport:[locked.transport],items:locked.items||[],people:locked.people||[],returnUrl:''};
  locked=null;taps=[];itemsReviewed=true;
  if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});
  location.hash='choose';renderChoose();
}
function renderLocked() {
  document.body.classList.add('lock-active');
  const items = locked.items || [];
  const people = locked.people || [];
  app.innerHTML = `<main class="locked ${items.length?'has-items':''} ${people.length?'has-people':''}" id="lockedSurface" aria-label="Journey picture display"><div class="orientation-notice" role="status"><span aria-hidden="true">↻</span><h1>Turn your device</h1><p>Turn to landscape to see the plan.</p></div><div class="journey-content"><h1>We’re going…</h1><div class="cue-pair">${['places','transport'].map((kind,i)=>`<figure class="cue-card"><img src="${esc(locked[kind].image)}" alt="${esc(locked[kind].name)}" draggable="false"><figcaption><span class="cue-label">${i===0?'To:':'By:'}</span><span class="cue-name">${esc(locked[kind].name)}</span></figcaption></figure>`).join('')}</div>${people.length||items.length?`<div class="journey-companions">${people.length ? `<section class="journey-people" aria-labelledby="peopleHeading"><h2 id="peopleHeading">Coming with us…</h2><div class="people-row">${people.map(person=>`<figure class="person-card"><img src="${esc(person.image)}" alt="${esc(person.name)}" draggable="false"><figcaption>${esc(person.name)}</figcaption></figure>`).join('')}</div></section>` : ''}${items.length ? `<section class="bring-items" aria-labelledby="bringHeading"><h2 id="bringHeading">We’re bringing…</h2><div class="bring-grid">${items.map(item=>`<figure class="bring-card"><img src="${esc(item.image)}" alt="${esc(item.name)}" draggable="false"><figcaption>${esc(item.name)}</figcaption></figure>`).join('')}</div></section>` : ''}</div>`:''}</div></main>`;
  $('#lockedSurface').addEventListener('contextmenu', e=>e.preventDefault());
  $('#lockedSurface').onclick = () => {
    const now = Date.now(); taps = taps.filter(t=>now-t<3000); taps.push(now);
    if(taps.length>=5)finishJourney();
  };
}
const uploadCategories = [
  ['places','Place','<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/>'],
  ['transport','Transport','<rect x="5" y="3" width="14" height="15" rx="3"/><path d="M5 11h14M12 3v8M8 18l-3 4m11-4 3 4M8 21h8"/><circle cx="8.5" cy="14.5" r=".8"/><circle cx="15.5" cy="14.5" r=".8"/>'],
  ['items','Items','<circle cx="6.5" cy="5" r="3"/><circle cx="17.5" cy="5" r="3"/><ellipse cx="12" cy="18" rx="5" ry="4"/><circle cx="7" cy="20" r="2.5"/><circle cx="17" cy="20" r="2.5"/><circle cx="12" cy="10" r="6"/><ellipse cx="12" cy="12" rx="2" ry="1.5"/><path d="M9 9h.01M15 9h.01"/>'],
  ['people','People','<circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3Z"/>']
];
function renderManage() {
  frame(settingsHeader('photos')+`<section id="settingsPanel" role="tabpanel" aria-labelledby="settingsTab-photos">`+
    `<div class="management"><section class="panel" aria-label="Upload a picture"><form id="uploadForm"><div><label for="photo">Photo</label><input id="photo" type="file" accept="image/jpeg,image/png,image/webp" required><p class="help">JPEG, PNG or WebP. Photos fill a square automatically. Use Crop photo to zoom out, adjust framing and colour any gaps. People display as circles.</p><img id="photoPreview" class="preview-image" alt="Selected photo preview" hidden><button id="cropUpload" class="secondary" type="button" hidden>Crop photo</button></div><div><label for="name">Name</label><input id="name" maxlength="60" placeholder="e.g. Park" required></div><fieldset class="kind-picker"><legend>What is it?</legend><div class="kind-options">${categoryChoices('kind',category)}</div></fieldset><p id="uploadError" class="error" role="alert"></p><button class="primary" type="submit" id="uploadButton">Add to library <span aria-hidden="true">＋</span></button></form></section><section aria-label="Existing pictures"><div class="tabs" aria-label="Picture categories">${[['places','Places'],['transport','Transport'],['items','Items'],['people','People']].map(([k,t])=>`<button data-tab="${k}" aria-pressed="${category===k}">${t} · ${state[k].length}</button>`).join('')}</div><div id="library"></div></section></div></section>`, 'settings');
  wireSettingsSections('photos');
  const uploadKind=()=>$('#uploadForm input[name="kind"]:checked').value;
  app.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{category=b.dataset.tab;renderManage();});
  renderLibrary();
  let previewUrl, croppedImage = null, preparing = Promise.resolve(), revision = 0;
  const uploadForm=$('#uploadForm');
  let wasPerson = uploadKind()==='people';
  const defaultCrop=()=>{
    const current=++revision, file=$('#photo').files[0];
    croppedImage=null;
    $('#photoPreview').hidden=true; $('#cropUpload').hidden=true;
    $('#uploadButton').disabled=!!file;
    $('#uploadError').textContent='';
    preparing=(async()=>{
      if(!file)return;
      try {
        const image=await preparePhoto(file,1);
        if(current!==revision || !document.contains(uploadForm))return;
        croppedImage=image; $('#photoPreview').src='data:image/jpeg;base64,'+image;
        $('#photoPreview').hidden=false; $('#cropUpload').hidden=false;
      } catch(error) { if(current===revision && document.contains(uploadForm))$('#uploadError').textContent=error.message; }
      finally { if(current===revision && document.contains(uploadForm))$('#uploadButton').disabled=false; }
    })();
  };
  const updateUploadKind=()=>{
    const circle=uploadKind()==='people';
    $('#photoPreview').classList.toggle('round',circle);
    if(circle!==wasPerson)defaultCrop();
    wasPerson=circle;
  };
  app.querySelectorAll('input[name="kind"]').forEach(input=>input.onchange=updateUploadKind);
  updateUploadKind();
  $('#photo').onchange=()=>{
    if(previewUrl) URL.revokeObjectURL(previewUrl);
    const file=$('#photo').files[0];
    previewUrl=file?URL.createObjectURL(file):null;
    defaultCrop();
  };
  $('#cropUpload').onclick=async()=>{
    try {
      const file=$('#photo').files[0]; validatePhoto(file);
      await openCrop(previewUrl, uploadKind()==='people', async image=>{
        croppedImage=image; $('#photoPreview').src='data:image/jpeg;base64,'+image;
      });
    } catch(error) { $('#uploadError').textContent=error.message; }
  };
  $('#uploadForm').onsubmit=async e=>{
    e.preventDefault(); const button=$('#uploadButton'); button.disabled=true;button.textContent='Adding picture…'; $('#uploadError').textContent='';
    try { await preparing; const kind=uploadKind(); const image=croppedImage || await preparePhoto($('#photo').files[0],1); await api('items',{kind,name:$('#name').value,image,original:await preparePhoto($('#photo').files[0])}); await refresh();category=kind;if(previewUrl) URL.revokeObjectURL(previewUrl);renderManage();toast('Picture added to your library.'); }
    catch(error) { $('#uploadError').textContent=error.message; }
    finally { if(document.contains(button)){button.disabled=false;button.textContent='Add to library ＋';} }
  };
}
function validatePhoto(file) {
  if(!file || !['image/jpeg','image/png','image/webp'].includes(file.type)) throw new Error('Choose a JPEG, PNG or WebP photo. HEIC photos need converting first.');
  if(file.size>25*1024*1024) throw new Error('Choose a photo smaller than 25 MB.');
}
function imageHasTransparency(img) {
  // Scan strips at source resolution so even small translucent areas are detected.
  const canvas=document.createElement('canvas');canvas.width=img.width;canvas.height=Math.min(64,img.height);
  const context=canvas.getContext('2d',{willReadFrequently:true});
  for(let y=0;y<img.height;y+=canvas.height) {
    const height=Math.min(canvas.height,img.height-y);
    context.clearRect(0,0,canvas.width,canvas.height);
    context.drawImage(img,0,y,img.width,height,0,0,img.width,height);
    const pixels=context.getImageData(0,0,img.width,height).data;
    for(let i=3;i<pixels.length;i+=4)if(pixels[i]<255)return true;
  }
  return false;
}
function exportPhoto(img,box,background='#ffffff',maxEdge=1600) {
  const scale=Math.min(1,maxEdge/Math.max(box.width,box.height));
  const canvas=document.createElement('canvas');
  canvas.width=Math.max(1,Math.round(box.width*scale));canvas.height=Math.max(1,Math.round(box.height*scale));
  const context=canvas.getContext('2d');
  if(background!==null){context.fillStyle=background;context.fillRect(0,0,canvas.width,canvas.height);}
  context.drawImage(img,box.x,box.y,box.width,box.height,0,0,canvas.width,canvas.height);
  return canvas.toDataURL(background===null?'image/png':'image/jpeg',.9).split(',')[1];
}
async function preparePhoto(file,aspect=null) {
  validatePhoto(file);
  const url=URL.createObjectURL(file);
  try {
    const img=new Image();img.src=url;await img.decode();
    const width=aspect?Math.min(img.width,img.height*aspect):img.width;
    const height=aspect?width/aspect:img.height;
    const transparent=!aspect && imageHasTransparency(img);
    const box={x:(img.width-width)/2,y:(img.height-height)/2,width,height};
    let maxEdge=1600, image=exportPhoto(img,box,transparent?null:'#ffffff',maxEdge);
    // Transparent PNG originals can be larger than JPEGs; stay within the upload limit.
    while(transparent && image.length>3*1024*1024){maxEdge*=.8;image=exportPhoto(img,box,null,maxEdge);}
    return image;
  } catch { throw new Error('This photo could not be opened. Try another JPEG, PNG or WebP photo.'); }
  finally { URL.revokeObjectURL(url); }
}
const libraryIcons={
  crop:'<path d="M6 3v12a3 3 0 0 0 3 3h12M3 6h12a3 3 0 0 1 3 3v12"/>',
  rename:'<path d="m15 4 5 5M4 20l5-1L21 7a2 2 0 0 0-5-5L4 14Z"/>',
  transfer:'<path d="M3 7h17m-4-4 4 4-4 4M21 17H4m4-4-4 4 4 4"/>',
  remove:'<path d="M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7"/>'
};
function libraryAction(action,item,label,title) {
  return `<button type="button" class="library-action ${action==='remove'?'remove-icon':''}" data-${action}="${item.id}" aria-label="${label} ${esc(item.name)}" title="${title}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${libraryIcons[action]}</svg></button>`;
}
function categoryChoices(name,current,disableCurrent=false) {
  return uploadCategories.map(([kind,label,icon])=>`<label class="kind-choice"><input type="radio" name="${name}" value="${kind}" ${kind===current?'checked':''} ${kind===current&&disableCurrent?'disabled':''}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icon}</svg><span>${label}${kind===current&&disableCurrent?' (current)':''}</span></label>`).join('');
}
function openItemEdit(action,kind,item) {
  pendingEdit={action,kind,id:item.id,sourceName:item.name};
  const rename=action==='rename';
  $('#editForm').dataset.busy='false';$('#editError').textContent='';
  $('#editTitle').textContent=rename?'Rename picture':'Change category';
  $('#editHelp').textContent=rename?`Give “${item.name}” a new name. Plans already on screen keep their current name.`:`Move “${item.name}” to another category. Its photo and original are kept. Plans already on screen stay the same.`;
  $('#renameFields').hidden=!rename;$('#transferFields').hidden=rename;
  $('#editName').value=item.name;$('#editName').required=rename;
  $('#editCategories').innerHTML=rename?'':categoryChoices('targetKind',kind,true);
  $('#editSave').textContent=rename?'Save name':'Move picture';
  updateEditSave();$('#editDialog').showModal();
  if(rename){$('#editName').focus();$('#editName').select();}
}
function updateEditSave() {
  if(!pendingEdit)return;
  const valid=pendingEdit.action==='rename'?$('#editName').value.trim().length>0:!!$('#editForm input[name="targetKind"]:checked:not(:disabled)');
  $('#editSave').disabled=!valid||$('#editForm').dataset.busy==='true';
}
$('#editForm').oninput=updateEditSave;
$('#editCancel').onclick=()=>{if($('#editForm').dataset.busy!=='true')$('#editDialog').close();};
$('#editDialog').addEventListener('cancel',e=>{if($('#editForm').dataset.busy==='true')e.preventDefault();});
$('#editDialog').addEventListener('close',()=>{pendingEdit=null;});
$('#editForm').onsubmit=async e=>{
  e.preventDefault();if(!pendingEdit||$('#editForm').dataset.busy==='true')return;
  const editing=pendingEdit, target=$('#editForm input[name="targetKind"]:checked:not(:disabled)')?.value;
  if(editing.action==='transfer'&&!target)return;
  $('#editForm').dataset.busy='true';updateEditSave();$('#editCancel').disabled=true;$('#editError').textContent='';
  try {
    const body=editing.action==='rename'?{kind:editing.kind,id:editing.id,sourceName:editing.sourceName,name:$('#editName').value.trim()}:{kind:editing.kind,id:editing.id,targetKind:target};
    await api(editing.action,body);await refresh();
    if(target)category=target;
    $('#editDialog').close();renderManage();
    app.querySelector(`[data-${editing.action}="${editing.id}"]`)?.focus({preventScroll:true});
    toast(editing.action==='rename'?'Name updated.':'Picture moved to its new category.');
  } catch(error){$('#editError').textContent=error.message;}
  finally{$('#editForm').dataset.busy='false';$('#editCancel').disabled=false;updateEditSave();}
};
function orderControl(item,direction,disabled) {
  return `<button type="button" class="library-action" data-order="${item.id}" data-direction="${direction}" aria-label="Move ${esc(item.name)} ${direction}" title="Move ${direction}" ${disabled||reorderBusy?'disabled':''}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${direction==='left'?'M19 12H5m6-6-6 6 6 6':'M5 12h14m-6-6 6 6-6 6'}"/></svg></button>`;
}
function renderLibrary() {
  const items=state[category];
  $('#library').innerHTML=items.length ? `<div class="library-grid">${items.map((x,index)=>`<article class="library-item ${category==='people'?'person-picture':''}"><img src="${esc(x.image)}" alt=""><strong>${esc(x.name)}</strong><div class="library-order">${orderControl(x,'left',index===0)}${orderControl(x,'right',index===items.length-1)}</div><div class="library-actions">${libraryAction('crop',x,'Crop','Crop photo')}${libraryAction('rename',x,'Rename','Rename')}${libraryAction('transfer',x,'Change category for','Change category')}${libraryAction('remove',x,'Remove','Remove photo')}</div></article>`).join('')}</div>` : `<div class="empty"><h3>No ${category==='people'?'people':category==='items'?'items to bring along':category==='places'?'places':'transport pictures'} yet</h3><p>Add your first picture using the form.</p></div>`;
  app.querySelectorAll('[data-order]').forEach(button=>button.onclick=async()=>{
    if(reorderBusy)return;
    const kind=category, id=button.dataset.order, direction=button.dataset.direction;
    const index=items.findIndex(item=>item.id===id), neighbour=items[index+(direction==='left'?-1:1)];
    if(!neighbour)return;
    reorderBusy=true;app.querySelectorAll('[data-order]').forEach(control=>control.disabled=true);
    try {await api('reorder',{kind,id,direction,neighbourId:neighbour.id});await refresh();}
    catch(error){toast(error.message);try{await refresh();}catch{}}
    finally{
      reorderBusy=false;
      if($('#library')){renderLibrary();const next=app.querySelector(`[data-order="${id}"][data-direction="${direction}"]:not(:disabled)`)||app.querySelector(`[data-order="${id}"]:not(:disabled)`);next?.focus({preventScroll:true});}
    }
  });
  app.querySelectorAll('[data-crop]').forEach(button=>button.onclick=async()=>{
    const kind=category, item=state[kind].find(x=>x.id===button.dataset.crop);
    button.disabled=true;
    try { await openCrop(item.originalImage || item.image, kind==='people', async image=>{
      await api('crop',{kind,id:item.id,sourceImage:item.image,image});
      await refresh();renderManage();toast('Cropped picture saved. Locked journeys keep their current picture.');
    }); } catch(error) { toast(error.message); }
    finally { button.disabled=false; }
  });
  for(const action of ['rename','transfer'])app.querySelectorAll(`[data-${action}]`).forEach(button=>button.onclick=()=>openItemEdit(action,category,items.find(item=>item.id===button.dataset[action])));
  app.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{const item=items.find(x=>x.id===b.dataset.remove);pendingDelete={kind:category,id:item.id};$('#deleteText').textContent=`Remove “${item.name}” from the library? An already locked journey will keep its picture until it is finished.`;$('#deleteDialog').showModal();});
}
$('#deleteCancel').onclick=()=>$('#deleteDialog').close();
$('#deleteForm').onsubmit=async e=>{e.preventDefault();const b=e.submitter;b.disabled=true;try{await api('delete',pendingDelete);$('#deleteDialog').close();await refresh();renderManage();toast('Picture removed.');}catch(error){toast(error.message);}finally{b.disabled=false;}};
function renderSettings() {
  frame(settingsHeader('more')+`<section id="settingsPanel" role="tabpanel" aria-labelledby="settingsTab-more"><div class="settings-grid"><section class="panel"><h2>Back to main screen</h2><p>Add the address of your main tablet screen. A return link will appear on the parent screens.</p><form id="returnForm"><div><label for="returnUrl">Main screen address</label><input id="returnUrl" type="url" placeholder="http://homeassistant.local:8123/…" value="${esc(state.returnUrl)}"></div><button class="primary">Save link</button><p id="returnError" class="error" role="alert"></p></form></section></div></section>`, 'settings');
  wireSettingsSections('more');
  $('#returnForm').onsubmit=async e=>{e.preventDefault();const b=e.submitter;b.disabled=true;try{await api('settings',{returnUrl:$('#returnUrl').value.trim()});await refresh();renderSettings();toast('Return link saved.');}catch(error){$('#returnError').textContent=error.message;}finally{b.disabled=false;}};
}

async function route() {
  if($('#planDialog').open)$('#planDialog').close();
  if(locked){renderLocked();return;}
  const view=location.hash.slice(1) || (location.pathname==='/manage'?'manage':location.pathname==='/settings'?'settings':'choose');
  if(view==='manage'||view==='settings')renderManage();else if(view==='settings-more')renderSettings();else renderChoose();
}
window.addEventListener('hashchange',()=>route());
// Refresh the library when a parent returns to this tab; never replace a locked cue.
document.addEventListener('visibilitychange',async()=>{if(document.visibilityState==='visible'&&!locked){try{await refresh();if(!$('#deleteDialog').open&&!$('#editDialog').open&&!$('#cropDialog').open&&!$('#planDialog').open && !['INPUT','SELECT'].includes(document.activeElement.tagName))await route();}catch(error){toast(error.message);}}});
async function start() {
  try {
    const saved=localStorage.getItem('tc-locked-journey');
    if(saved){
      const data=JSON.parse(saved);
      const validPicture = item => item && typeof item.name==='string' && /^\/images\/[a-f0-9]+\.(jpg|png|webp)$/.test(item.image);
      if(validPicture(data.places) && validPicture(data.transport)) {
        // Journeys saved before bring-along items were added still restore normally.
        data.items = Array.isArray(data.items) ? data.items.filter(validPicture).slice(0,MAX_BRING_ITEMS) : [];
        data.people = Array.isArray(data.people) ? data.people.filter(validPicture) : [];
        locked=data;
      }
    }
  }catch{};
  // The saved journey can still be shown if the server is temporarily unreachable.
  if(locked)renderLocked();
  try {await refresh();await route();}
  catch(error){if(locked){toast(error.message);return;}app.innerHTML=`<div class="loading"><h1>Let’s try that again</h1><p>${esc(error.message)}</p><button id="retry" class="primary">Try again</button></div>`;$('#retry').onclick=start;}
}
let cropState=null;
async function openCrop(source, circle, save) {
  const img=new Image(); img.src=source;
  try { await img.decode(); } catch { throw new Error('This photo could not be opened. Try a different photo or refresh the library.'); }
  cropState={img,circle,save,busy:false,transparent:imageHasTransparency(img)};
  $('#cropError').textContent='';
  $('#cropZoom').min=String(Math.min(.25,Math.min(img.width,img.height)/Math.max(img.width,img.height)/2));
  $('#cropBackground').value='#ffffff';
  $('#cropHelp').textContent=circle ? 'Centre the face inside the circle. Zoom out to fit more of the photo; any gaps can have a background colour. The saved photo is square and displays as a circle.' : 'The frame is always square. Drag to move, zoom in to fill it, or zoom out to fit more of the photo. Choose a background colour for gaps or transparency.';
  $('#cropCanvas').classList.toggle('round',circle);
  resetCrop(); $('#cropDialog').showModal();
}
function cropRect() {
  const {img}=cropState;
  const width=Math.min(img.width,img.height)/Number($('#cropZoom').value);
  return {x:(img.width-width)*Number($('#cropX').value)/100, y:(img.height-width)*Number($('#cropY').value)/100, width,height:width};
}
function cropHasGaps(box) {
  return box.width>cropState.img.width+.01 || box.height>cropState.img.height+.01;
}
function cropBackground(box) { return cropHasGaps(box)||cropState.transparent?$('#cropBackground').value:'#ffffff'; }
function drawCrop() {
  if(!cropState)return;
  const box=cropRect(), canvas=$('#cropCanvas');
  canvas.width=canvas.height=560;
  $('#cropBackgroundGroup').hidden=!(cropHasGaps(box)||cropState.transparent);
  const context=canvas.getContext('2d'); context.fillStyle=cropBackground(box);context.fillRect(0,0,560,560);
  context.drawImage(cropState.img,box.x,box.y,box.width,box.height,0,0,560,560);
}
function resetCrop() { $('#cropZoom').value='1';$('#cropX').value='50';$('#cropY').value='50';drawCrop(); }
for(const id of ['cropZoom','cropX','cropY']) $('#'+id).oninput=drawCrop;
$('#cropBackground').oninput=drawCrop;
$('#cropFit').onclick=()=>{const {img}=cropState;$('#cropZoom').value=String(Math.min(img.width,img.height)/Math.max(img.width,img.height));$('#cropX').value=$('#cropY').value='50';drawCrop();};
$('#cropReset').onclick=resetCrop;
$('#cropCancel').onclick=()=>$('#cropDialog').close();
$('#cropDialog').addEventListener('cancel',e=>{if(cropState?.busy)e.preventDefault();});
$('#cropDialog').addEventListener('close',()=>{cropState=null;});
let cropDrag=null;
$('#cropCanvas').onpointerdown=e=>{
  if(!cropState || cropState.busy)return;
  cropDrag={x:e.clientX,y:e.clientY};e.currentTarget.setPointerCapture(e.pointerId);
};
$('#cropCanvas').onpointermove=e=>{
  if(!cropDrag || !cropState)return;
  const box=cropRect(), bounds=e.currentTarget.getBoundingClientRect(), img=cropState.img;
  const move=(id,delta,available)=>{if(Math.abs(available)>.01)$('#'+id).value=String(Math.min(100,Math.max(0,Number($('#'+id).value)-delta/available*100)));};
  move('cropX',(e.clientX-cropDrag.x)*box.width/bounds.width,img.width-box.width);
  move('cropY',(e.clientY-cropDrag.y)*box.height/bounds.height,img.height-box.height);
  cropDrag={x:e.clientX,y:e.clientY};drawCrop();
};
$('#cropCanvas').onpointerup=$('#cropCanvas').onpointercancel=()=>{cropDrag=null;};
$('#cropForm').onsubmit=async e=>{
  e.preventDefault();if(!cropState || cropState.busy)return;
  const editing=cropState, box=cropRect(), image=exportPhoto(editing.img,box,cropBackground(box));
  editing.busy=true; $('#cropError').textContent='';
  const controls=[...$('#cropForm').querySelectorAll('button,input,select')];controls.forEach(control=>control.disabled=true);
  try {await editing.save(image);$('#cropDialog').close();}
  catch(error){$('#cropError').textContent=error.message;}
  finally{editing.busy=false;controls.forEach(control=>control.disabled=false);}
};

start();
