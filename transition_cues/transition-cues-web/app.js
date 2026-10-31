'use strict';
const $ = s => document.querySelector(s);
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const app = $('#app');
let state, selected = {places:null, transport:null, items:[], people:[]}, category = 'places', locked = null, taps = [], pinAction = null, pendingDelete = null;
let toastTimer, pendingJourney = null;
function toast(message) { $('#toast').textContent = message; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true, 4500); }
async function api(path, data) {
  let response;
  try { response = await fetch('/api/' + path, data === undefined ? {cache:'no-store'} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}); }
  catch { throw new Error('Cannot reach Transition Cues. Check your Wi-Fi and try again.'); }
  let result;
  try { result = await response.json(); } catch { throw new Error('The server returned an unexpected response. Please try again.'); }
  if (!response.ok) throw new Error(result.error || 'Something went wrong. Please try again.');
  return result;
}
async function refresh() { state = await api('state'); state.items ??= []; state.people ??= []; }
function frame(content, route) {
  document.body.classList.remove('lock-active');
  app.innerHTML = `<div class="shell"><header class="header"><a class="brand" href="#choose"><img src="/icon.svg" alt=""><span>Transition Cues<small>ONE JOURNEY AT A TIME</small></span></a><nav class="nav" aria-label="Main navigation">${[['choose','Plan a journey'],['manage','Picture library'],['settings','Settings']].map(([r,t])=>`<a href="#${r}" ${route===r?'aria-current="page"':''}>${t}</a>`).join('')}${state.returnUrl ? `<a class="return-link" href="${esc(state.returnUrl)}">← Back to main screen</a>` : ''}</nav></header>${content}</div>`;
}
function intro(kicker, title, description, extra='') { return `<div class="intro"><div><span class="eyebrow">${kicker}</span><h1>${title}</h1><p>${description}</p></div>${extra}</div>`; }
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
  frame(intro('LET’S GET READY', 'Where are we going?', 'Choose a place, how you’ll get there, and anything to bring along.', '<span class="pill">A moment of calm before you go</span>') +
    ['places','transport','items','people'].map((kind,i)=>{
      const multi = kind==='items' || kind==='people';
      return `<section class="step" aria-labelledby="${kind}Heading"><div class="step-heading"><h2 id="${kind}Heading"><span class="step-number">${i+1}</span>${['Choose a place','Choose how to get there','Items to bring along','People'][i]}</h2><small ${multi?`id="${kind==='items'?'itemCount':'peopleCount'}" role="status"`:''}>${multi ? (kind==='items' ? `${selected.items.length} of ${MAX_BRING_ITEMS} selected · optional` : `${selected.people.length} selected · optional`) : `${state[kind].length} ${kind==='places'?'places':'ways to travel'}`}</small></div>${multi?`<p class="step-help">${kind==='items'?'Choose up to 4 items.':'Choose the people coming along, or leave this empty.'} Tap a selected picture again to remove it.</p>`:''}${state[kind].length ? `<div class="grid">${state[kind].map(x=>{
        const active = multi ? selected[kind].some(item=>item.id===x.id) : selected[kind]?.id===x.id;
        const atLimit = kind==='items' && !active && selected.items.length>=MAX_BRING_ITEMS;
        return `<button class="picture ${kind==='people'?'person-picture':''} ${active?'selected':''}" data-kind="${kind}" data-id="${x.id}" aria-pressed="${active}" ${atLimit?'disabled':''}><img src="${esc(x.image)}" alt=""><span class="check" aria-hidden="true">✓</span><span class="name">${esc(x.name)}</span></button>`;
      }).join('')}</div>` : empty(kind)}</section>`;
    }).join('')+
    `<div class="journey-bar"><div><strong>${selected.places && selected.transport ? `${esc(selected.places.name)} · ${esc(selected.transport.name)}${selected.items.length ? ` · ${selected.items.length} to bring` : ''}` : 'Choose a place and transport to continue'}</strong></div><button id="start" class="primary" ${selected.places&&selected.transport?'':'disabled'}>Show the plan <span aria-hidden="true">→</span></button></div>`, 'choose');
  app.querySelectorAll('[data-kind]').forEach(button => button.onclick = () => {
    const {kind,id} = button.dataset;
    const item = state[kind].find(x=>x.id===id);
    if(kind==='items' || kind==='people') {
      if(selected[kind].some(x=>x.id===id)) selected[kind]=selected[kind].filter(x=>x.id!==id);
      else if(kind==='people' || selected.items.length<MAX_BRING_ITEMS) selected[kind].push(item);
      else return;
    } else selected[kind] = item;
    renderChoose();
    app.querySelector(`[data-kind="${kind}"][data-id="${id}"]`)?.focus({preventScroll:true});
  });
  $('#start').onclick = () => {
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

function renderLocked() {
  document.body.classList.add('lock-active');
  const items = locked.items || [];
  const people = locked.people || [];
  app.innerHTML = `<main class="locked ${items.length?'has-items':''} ${people.length?'has-people':''}" id="lockedSurface" aria-label="Journey picture display"><h1>We’re going…</h1><div class="cue-pair">${['places','transport'].map((kind,i)=>`<figure class="cue-card"><p class="cue-label">${i===0?'To':'By'}</p><img src="${esc(locked[kind].image)}" alt="${esc(locked[kind].name)}" draggable="false"><figcaption>${esc(locked[kind].name)}</figcaption></figure>`).join('')}</div>${people.length ? `<section class="journey-people" aria-labelledby="peopleHeading"><h2 id="peopleHeading">Coming with us…</h2><div class="people-row">${people.map(person=>`<figure class="person-card"><img src="${esc(person.image)}" alt="${esc(person.name)}" draggable="false"><figcaption>${esc(person.name)}</figcaption></figure>`).join('')}</div></section>` : ''}${items.length ? `<section class="bring-items" aria-labelledby="bringHeading"><h2 id="bringHeading">We’re bringing…</h2><div class="bring-grid">${items.map(item=>`<figure class="bring-card"><img src="${esc(item.image)}" alt="${esc(item.name)}" draggable="false"><figcaption>${esc(item.name)}</figcaption></figure>`).join('')}</div></section>` : ''}</main>`;
  $('#lockedSurface').addEventListener('contextmenu', e=>e.preventDefault());
  $('#lockedSurface').onclick = () => {
    const now = Date.now(); taps = taps.filter(t=>now-t<4000); taps.push(now);
    if(taps.length>=5) { taps=[]; showPin('unlock'); }
  };
}
// PINs stay in memory; the browser sees buttons and masked dots, not password fields.
const pinValues = new WeakMap();
let dialogPad = null;
function pinValue(id) { return pinValues.get($('#'+id)) || ''; }
function pinField(id, label) {
  return `<div><label for="${id}">${label}</label><button id="${id}" type="button" class="pin-entry" data-pin-label="${label}" aria-label="${label}, no digits entered"><span aria-hidden="true">○ ○ ○ ○</span></button></div>`;
}
function wirePinPad(form, ids, holder, submit, submitLabel) {
  const fields = ids.map(id=>$('#'+id));
  let active=fields[0];
  holder.innerHTML=`<p class="pin-pad-label" role="status"></p><div class="pin-keypad" role="group" aria-label="PIN number pad">${['1','2','3','4','5','6','7','8','9','clear','0','back'].map(key=>`<button type="button" data-pin-key="${key}" aria-label="${key==='clear'?'Clear PIN':key==='back'?'Delete last digit':key}">${key==='clear'?'Clear':key==='back'?'⌫':key}</button>`).join('')}</div>${ids.length>1 && form.id!=='pinForm'?'<button class="pin-next secondary" type="button">Next PIN field →</button>':''}`;
  function paint() {
    const busy=form.dataset.pinBusy==='true';
    holder.querySelectorAll('button').forEach(button=>button.disabled=busy);
    if(form.id==='pinForm')$('#pinCancel').disabled=busy;
    for(const field of fields) {
      field.disabled=busy;
      const value=pinValues.get(field)||'';
      field.innerHTML=`<span aria-hidden="true">${value?'●'.repeat(value.length):'○ ○ ○ ○'}</span>`;
      field.setAttribute('aria-label',`${field.dataset.pinLabel}, ${value.length} digits entered`);
      field.setAttribute('aria-pressed',String(field===active));
      field.classList.toggle('active',field===active);
    }
    holder.querySelector('.pin-pad-label').textContent=`${active.dataset.pinLabel} · ${(pinValues.get(active)||'').length} digits entered`;
    const allValid=fields.every(field=>(pinValues.get(field)||'').length>=4);
    submit.textContent=submitLabel(active.id);
    submit.disabled=form.dataset.pinBusy==='true' || (form.id==='pinForm' && pinAction==='setup' && active===fields[0] ? (pinValues.get(active)||'').length<4 : !allValid);
    const next=holder.querySelector('.pin-next');
    if(next) next.hidden=active===fields[fields.length-1];
  }
  function activate(field,focus=true) { active=field;paint();if(focus)field.focus({preventScroll:true}); }
  function key(value) {
    if(form.dataset.pinBusy==='true')return;
    let pin=pinValues.get(active)||'';
    if(value==='clear')pin='';
    else if(value==='back')pin=pin.slice(0,-1);
    else if(/^[0-9]$/.test(value) && pin.length<8)pin+=value;
    pinValues.set(active,pin);paint();
  }
  for(const field of fields){pinValues.set(field,'');field.onclick=()=>activate(field);field.onfocus=()=>activate(field,false);}
  holder.onclick=e=>{const button=e.target.closest('[data-pin-key]');if(button)key(button.dataset.pinKey);};
  form.onkeydown=e=>{
    if(e.ctrlKey||e.metaKey||e.altKey||e.defaultPrevented)return;
    if(/^[0-9]$/.test(e.key)){e.preventDefault();key(e.key);}
    else if(e.key==='Backspace'||e.key==='Delete'){e.preventDefault();key(e.key==='Delete'?'clear':'back');}
    else if(e.key==='Enter' && fields.includes(e.target)){e.preventDefault();if(!submit.disabled)form.requestSubmit(submit);}
  };
  const next=holder.querySelector('.pin-next');
  if(next)next.onclick=()=>activate(fields[Math.min(fields.length-1,fields.indexOf(active)+1)]);
  paint();
  return {get activeId(){return active.id;},activate:id=>activate($('#'+id)),clear:()=>{fields.forEach(field=>pinValues.set(field,''));paint();},paint};
}
function validPin(id) {
  const value=pinValue(id);
  if(!/^[0-9]{4,8}$/.test(value))throw new Error('Enter a PIN of 4 to 8 digits using the number pad.');
  return value;
}
function showPin(action) {
  if ($('#pinDialog').open) return;
  pinAction = action;
  const setup = action === 'setup';
  $('#pinForm').dataset.pinBusy='false'; $('#pinError').textContent='';
  $('#pinTitle').textContent = setup ? 'A PIN for the grown-ups' : 'Enter your parent PIN';
  $('#pinHelp').textContent = setup ? 'Choose 4 to 8 digits using the number pad, then confirm your PIN.' : 'Use the number pad to unlock. Your pictures will stay on screen until you do.';
  $('#confirmGroup').hidden = !setup;
  $('#pinCancel').hidden = setup;
  dialogPad=wirePinPad($('#pinForm'),setup?['pinInput','pinConfirm']:['pinInput'],$('#pinPad'),$('#pinSubmit'),id=>setup?(id==='pinInput'?'Next →':'Save PIN & get started'):'Unlock');
  $('#pinDialog').showModal(); $('#pinInput').focus();
}
$('#pinCancel').onclick = () => { if($('#pinForm').dataset.pinBusy==='true')return; $('#pinDialog').close(); if (!locked) location.hash='choose'; };
$('#pinDialog').addEventListener('cancel', e => { if(pinAction==='setup' || $('#pinForm').dataset.pinBusy==='true') e.preventDefault(); else if(!locked) location.hash='choose'; });
$('#pinDialog').addEventListener('close',()=>dialogPad?.clear());
$('#pinForm').onsubmit = async e => {
  e.preventDefault(); const form=$('#pinForm');
  if(form.dataset.pinBusy==='true')return;
  $('#pinError').textContent='';
  try {
    const pin=validPin('pinInput');
    if(pinAction==='setup' && dialogPad.activeId==='pinInput') { dialogPad.activate('pinConfirm');return; }
    if(pinAction==='setup' && pin!==validPin('pinConfirm')) throw new Error('The PINs do not match. Please try again.');
    form.dataset.pinBusy='true';dialogPad.paint();
    await api(pinAction==='setup'?'setup':'unlock',{pin});
    if(locked) { localStorage.removeItem('tc-locked-journey'); locked=null; if(document.fullscreenElement) document.exitFullscreen().catch(()=>{}); }
    $('#pinDialog').close(); await refresh(); await route();
  } catch(error) { $('#pinError').textContent=error.message; form.dataset.pinBusy='false'; dialogPad.clear();dialogPad.activate('pinInput'); }
  finally { form.dataset.pinBusy='false';dialogPad.paint(); }
};
function renderManage() {
  frame(intro('YOUR FAMILY’S PICTURE LIBRARY','Little pictures. Familiar faces.','Add your own photos, so every journey starts with something familiar.')+
    `<div class="management"><section class="panel"><h2>Add a picture</h2><p>A clear photo and a short, familiar name work best.</p><form id="uploadForm"><div><label for="kind">What is it?</label><select id="kind"><option value="places">A place</option><option value="transport">A way to travel</option><option value="items">An item to bring along</option><option value="people">A person</option></select></div><div><label for="name">Name</label><input id="name" maxlength="60" placeholder="e.g. Park" required></div><div><label for="photo">Photo</label><input id="photo" type="file" accept="image/jpeg,image/png,image/webp" required><p class="help">JPEG, PNG or WebP. Photos are cropped to 4:3 automatically. Use Crop photo to change the shape or framing. People use a square crop shown as a circle.</p><img id="photoPreview" class="preview-image" alt="Selected photo preview" hidden><button id="cropUpload" class="secondary" type="button" hidden>Crop photo</button></div><p id="uploadError" class="error" role="alert"></p><button class="primary" type="submit" id="uploadButton">Add to library <span aria-hidden="true">＋</span></button></form></section><section aria-label="Existing pictures"><div class="tabs" aria-label="Picture categories">${[['places','Places'],['transport','Transport'],['items','Items'],['people','People']].map(([k,t])=>`<button data-tab="${k}" aria-pressed="${category===k}">${t} · ${state[k].length}</button>`).join('')}</div><div id="library"></div></section></div>`, 'manage');
  $('#kind').value=category;
  app.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{category=b.dataset.tab;renderManage();});
  renderLibrary();
  let previewUrl, croppedImage = null, preparing = Promise.resolve(), revision = 0;
  const uploadForm=$('#uploadForm');
  let wasPerson = $('#kind').value==='people';
  const defaultCrop=()=>{
    const current=++revision, file=$('#photo').files[0], circle=$('#kind').value==='people';
    croppedImage=null;
    $('#photoPreview').hidden=true; $('#cropUpload').hidden=true;
    $('#uploadButton').disabled=!!file;
    $('#uploadError').textContent='';
    preparing=(async()=>{
      if(!file)return;
      try {
        const image=await preparePhoto(file,circle?1:4/3);
        if(current!==revision || !document.contains(uploadForm))return;
        croppedImage=image; $('#photoPreview').src='data:image/jpeg;base64,'+image;
        $('#photoPreview').hidden=false; $('#cropUpload').hidden=false;
      } catch(error) { if(current===revision && document.contains(uploadForm))$('#uploadError').textContent=error.message; }
      finally { if(current===revision && document.contains(uploadForm))$('#uploadButton').disabled=false; }
    })();
  };
  $('#kind').onchange=()=>{
    const circle=$('#kind').value==='people';
    $('#photoPreview').classList.toggle('round',circle);
    if(circle!==wasPerson)defaultCrop();
    wasPerson=circle;
  };
  $('#kind').onchange();
  $('#photo').onchange=()=>{
    if(previewUrl) URL.revokeObjectURL(previewUrl);
    const file=$('#photo').files[0];
    previewUrl=file?URL.createObjectURL(file):null;
    defaultCrop();
  };
  $('#cropUpload').onclick=async()=>{
    try {
      const file=$('#photo').files[0]; validatePhoto(file);
      await openCrop(previewUrl, $('#kind').value==='people', async image=>{
        croppedImage=image; $('#photoPreview').src='data:image/jpeg;base64,'+image;
      });
    } catch(error) { $('#uploadError').textContent=error.message; }
  };
  $('#uploadForm').onsubmit=async e=>{
    e.preventDefault(); const button=$('#uploadButton'); button.disabled=true;button.textContent='Adding picture…'; $('#uploadError').textContent='';
    try { await preparing; const kind=$('#kind').value; const image=croppedImage || await preparePhoto($('#photo').files[0],kind==='people'?1:4/3); await api('items',{kind,name:$('#name').value,image,original:await preparePhoto($('#photo').files[0])}); await refresh();category=kind;if(previewUrl) URL.revokeObjectURL(previewUrl);renderManage();toast('Picture added to your library.'); }
    catch(error) { $('#uploadError').textContent=error.message; }
    finally { if(document.contains(button)){button.disabled=false;button.textContent='Add to library ＋';} }
  };
}
function validatePhoto(file) {
  if(!file || !['image/jpeg','image/png','image/webp'].includes(file.type)) throw new Error('Choose a JPEG, PNG or WebP photo. HEIC photos need converting first.');
  if(file.size>25*1024*1024) throw new Error('Choose a photo smaller than 25 MB.');
}
function exportPhoto(img,box) {
  const scale=Math.min(1,1600/Math.max(box.width,box.height));
  const canvas=document.createElement('canvas');
  canvas.width=Math.max(1,Math.round(box.width*scale));canvas.height=Math.max(1,Math.round(box.height*scale));
  const context=canvas.getContext('2d');context.fillStyle='#ffffff';context.fillRect(0,0,canvas.width,canvas.height);
  context.drawImage(img,box.x,box.y,box.width,box.height,0,0,canvas.width,canvas.height);
  return canvas.toDataURL('image/jpeg',.9).split(',')[1];
}
async function preparePhoto(file,aspect=null) {
  validatePhoto(file);
  const url=URL.createObjectURL(file);
  try {
    const img=new Image();img.src=url;await img.decode();
    const width=aspect?Math.min(img.width,img.height*aspect):img.width;
    const height=aspect?width/aspect:img.height;
    return exportPhoto(img,{x:(img.width-width)/2,y:(img.height-height)/2,width,height});
  } catch { throw new Error('This photo could not be opened. Try another JPEG, PNG or WebP photo.'); }
  finally { URL.revokeObjectURL(url); }
}
function renderLibrary() {
  const items=state[category];
  $('#library').innerHTML=items.length ? `<div class="library-grid">${items.map(x=>`<article class="library-item ${category==='people'?'person-picture':''}"><img src="${esc(x.image)}" alt=""><strong>${esc(x.name)}</strong><button class="edit-crop" data-crop="${x.id}" aria-label="Crop ${esc(x.name)}">Crop photo</button><button class="remove" data-remove="${x.id}" aria-label="Remove ${esc(x.name)}">Remove picture</button></article>`).join('')}</div>` : `<div class="empty"><h3>No ${category==='people'?'people':category==='items'?'items to bring along':category==='places'?'places':'transport pictures'} yet</h3><p>Add your first picture using the form.</p></div>`;
  app.querySelectorAll('[data-crop]').forEach(button=>button.onclick=async()=>{
    const kind=category, item=state[kind].find(x=>x.id===button.dataset.crop);
    button.disabled=true;
    try { await openCrop(item.originalImage || item.image, kind==='people', async image=>{
      await api('crop',{kind,id:item.id,sourceImage:item.image,image});
      await refresh();renderManage();toast('Cropped picture saved. Locked journeys keep their current picture.');
    }); } catch(error) { toast(error.message); }
    finally { button.disabled=false; }
  });
  app.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{const item=items.find(x=>x.id===b.dataset.remove);pendingDelete={kind:category,id:item.id};$('#deleteText').textContent=`Remove “${item.name}” from the library? An already locked journey will keep its picture until it is finished.`;$('#deleteDialog').showModal();});
}
$('#deleteCancel').onclick=()=>$('#deleteDialog').close();
$('#deleteForm').onsubmit=async e=>{e.preventDefault();const b=e.submitter;b.disabled=true;try{await api('delete',pendingDelete);$('#deleteDialog').close();await refresh();renderManage();toast('Picture removed.');}catch(error){toast(error.message);}finally{b.disabled=false;}};
function renderSettings() {
  frame(intro('MAKE YOURSELF AT HOME','A few things for the grown-ups.','Keep your parent PIN and your return link up to date.')+`<div class="settings-grid"><section class="panel"><h2>Parent PIN</h2><p>Use the same PIN on the tablet and your phone.</p><form id="changePinForm">${pinField('oldPin','Current PIN')}${pinField('newPin','New PIN · 4 to 8 digits')}${pinField('newPinConfirm','Confirm new PIN')}<div id="settingsPinPad"></div><button class="primary" id="changePinSubmit">Change PIN</button><p class="error" id="changeError" role="alert"></p></form></section><section class="panel"><h2>Back to main screen</h2><p>Add the address of your main tablet screen. A return link will appear on the parent screens.</p><form id="returnForm"><div><label for="returnUrl">Main screen address</label><input id="returnUrl" type="url" placeholder="http://homeassistant.local:8123/…" value="${esc(state.returnUrl)}"></div><button class="primary">Save link</button><p id="returnError" class="error" role="alert"></p></form></section><section class="panel wide"><h2>On the tablet</h2><p>Choose a place, transport and up to four optional items to bring along, plus any people joining you, then tap “Show the plan”. To finish, tap the picture screen five times within four seconds and enter your PIN. Cancelling the PIN prompt keeps the journey locked.</p><p>Use the tablet’s kiosk mode or guided access to prevent leaving the browser. Keep Transition Cues open in its own browser tab rather than embedding it inside another page.</p><p class="help">To manage pictures from your phone, open this app’s address and choose Picture library. Both devices must reach the same server. Your pictures stay on your home server.</p></section></div>`, 'settings');
  $('#returnForm').onsubmit=async e=>{e.preventDefault();const b=e.submitter;b.disabled=true;try{await api('settings',{returnUrl:$('#returnUrl').value.trim()});await refresh();renderSettings();toast('Return link saved.');}catch(error){$('#returnError').textContent=error.message;}finally{b.disabled=false;}};
  const changeForm=$('#changePinForm');
  const settingsPad=wirePinPad(changeForm,['oldPin','newPin','newPinConfirm'],$('#settingsPinPad'),$('#changePinSubmit'),()=> 'Change PIN');
  changeForm.onsubmit=async e=>{
    e.preventDefault();if(changeForm.dataset.pinBusy==='true')return;
    $('#changeError').textContent='';
    try {
      const currentPin=validPin('oldPin'), pin=validPin('newPin');
      if(pin!==validPin('newPinConfirm'))throw new Error('The new PINs do not match.');
      changeForm.dataset.pinBusy='true';settingsPad.paint();
      await api('pin',{currentPin,pin});await refresh();renderSettings();toast('PIN changed. Other devices will need the new PIN.');
    }catch(error){$('#changeError').textContent=error.message;changeForm.dataset.pinBusy='false';settingsPad.clear();settingsPad.activate('oldPin');}
    finally{changeForm.dataset.pinBusy='false';settingsPad.paint();}
  };

}
async function route() {
  if($('#planDialog').open)$('#planDialog').close();
  if(locked){renderLocked();return;}
  const view=location.hash.slice(1) || (location.pathname==='/manage'?'manage':location.pathname==='/settings'?'settings':'choose');
  if(state.setupRequired){renderChoose();showPin('setup');return;}
  if(['manage','settings'].includes(view) && !state.authenticated){renderChoose();showPin('manage');return;}
  if(view==='manage')renderManage();else if(view==='settings')renderSettings();else renderChoose();
}
window.addEventListener('hashchange',()=>route());
// Refresh the library when a parent returns to this tab; never replace a locked cue.
document.addEventListener('visibilitychange',async()=>{if(document.visibilityState==='visible'&&!locked){try{await refresh();if(!$('#pinDialog').open&&!$('#deleteDialog').open&&!$('#cropDialog').open&&!$('#planDialog').open && !['INPUT','SELECT'].includes(document.activeElement.tagName))await route();}catch(error){toast(error.message);}}});
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
  cropState={img,circle,save,busy:false};
  $('#cropError').textContent='';
  $('#cropAspect').value=circle?'1':'1.3333333333'; $('#cropAspect').disabled=circle;
  $('#cropHelp').textContent=circle ? 'Centre the face inside the circle. Drag to move, or use the sliders. The saved photo is square and displays as a circle.' : 'Drag the picture or use the sliders to frame it. Existing pictures are cropped from their saved original.';
  $('#cropCanvas').classList.toggle('round',circle);
  resetCrop(); $('#cropDialog').showModal();
}
function cropRect() {
  const {img}=cropState;
  const aspect=$('#cropAspect').value==='original' ? img.width/img.height : Number($('#cropAspect').value);
  const width=Math.min(img.width,img.height*aspect)/Number($('#cropZoom').value), height=width/aspect;
  return {x:(img.width-width)*Number($('#cropX').value)/100, y:(img.height-height)*Number($('#cropY').value)/100, width,height,aspect};
}
function drawCrop() {
  if(!cropState)return;
  const box=cropRect(), canvas=$('#cropCanvas');
  canvas.width=Math.max(1,Math.round(560*Math.min(1,box.aspect)));
  canvas.height=Math.max(1,Math.round(560/Math.max(1,box.aspect)));
  const context=canvas.getContext('2d'); context.fillStyle='#ffffff';context.fillRect(0,0,canvas.width,canvas.height);
  context.drawImage(cropState.img,box.x,box.y,box.width,box.height,0,0,canvas.width,canvas.height);
}
function resetCrop() { $('#cropZoom').value='1';$('#cropX').value='50';$('#cropY').value='50';drawCrop(); }
for(const id of ['cropZoom','cropX','cropY']) $('#'+id).oninput=drawCrop;
$('#cropAspect').onchange=resetCrop;
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
  const move=(id,delta,available)=>{if(available>0)$('#'+id).value=String(Math.min(100,Math.max(0,Number($('#'+id).value)-delta/available*100)));};
  move('cropX',(e.clientX-cropDrag.x)*box.width/bounds.width,img.width-box.width);
  move('cropY',(e.clientY-cropDrag.y)*box.height/bounds.height,img.height-box.height);
  cropDrag={x:e.clientX,y:e.clientY};drawCrop();
};
$('#cropCanvas').onpointerup=$('#cropCanvas').onpointercancel=()=>{cropDrag=null;};
$('#cropForm').onsubmit=async e=>{
  e.preventDefault();if(!cropState || cropState.busy)return;
  const editing=cropState, image=exportPhoto(editing.img,cropRect());
  editing.busy=true; $('#cropError').textContent='';
  const controls=[...$('#cropForm').querySelectorAll('button,input,select')];controls.forEach(control=>control.disabled=true);
  try {await editing.save(image);$('#cropDialog').close();}
  catch(error){$('#cropError').textContent=error.message;}
  finally{editing.busy=false;controls.forEach(control=>control.disabled=false);$('#cropAspect').disabled=editing.circle;}
};

start();
