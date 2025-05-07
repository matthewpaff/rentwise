/* Persistent local workspace controls; all user text is rendered as text nodes. */
const workspacePanel=el('section',undefined,'panel workspace-panel');workspacePanel.id='workspace';
const sortSelect=el('select');sortSelect.id='sort';
for(const [value,label] of [['total','Known lease expense'],['monthly','Recurring monthly cost'],['effective','Effective monthly expense'],['completeness','Price completeness']]){const opt=el('option',label);opt.value=value;sortSelect.append(opt);}
document.querySelector('.toolbar').append(field('Rank homes by',sortSelect));sortSelect.onchange=evaluate;
const monthsInput=el('input');monthsInput.id='months';monthsInput.type='number';monthsInput.min='1';monthsInput.max='60';monthsInput.step='1';monthsInput.value=$('months').value;$('months').replaceWith(monthsInput);monthsInput.onchange=evaluate;
workspacePanel.append(el('div','LOCAL WORKSPACE','eyebrow'),el('h2','Keep your research together.'),el('p','Collections and saved searches stay in this browser’s local server database. No account or cloud sync.','muted'));
const workspaceStatus=el('p','','workspace-status');workspaceStatus.setAttribute('role','status');workspaceStatus.setAttribute('aria-live','polite');
workspacePanel.append(workspaceStatus);document.querySelector('.bottom-grid').before(workspacePanel);
const workspaceGrid=el('div',undefined,'workspace-grid');workspacePanel.append(workspaceGrid);
function field(title,node){const label=el('label',title);label.append(node);return label;}
function input(placeholder){const node=el('input');node.placeholder=placeholder;return node;}
function action(text,fn,primary=false){const b=el('button',text,primary?'primary':'');b.type='button';b.onclick=async()=>{b.disabled=true;workspaceStatus.textContent='Working…';try{await fn();}catch(e){workspaceStatus.textContent=e.message;}finally{b.disabled=false;}};return b;}
function message(value){workspaceStatus.textContent=value;}
const collectionArea=el('div');const searchArea=el('div');workspaceGrid.append(collectionArea,searchArea);
collectionArea.append(el('h3','Listing collections'));searchArea.append(el('h3','Saved searches'));
const collectionName=input('e.g. November shortlist');const provenance=input('Where did these inputs come from?');
collectionArea.append(field('Collection name',collectionName),field('Import / revision provenance',provenance));
let activeCollection=null;
collectionArea.append(action('Explore deposit & credit sample',async()=>{const response=await fetch('/api/fee-lab');const data=await response.json();if(!response.ok)throw new Error(data.error);imported=data.listings;activeCollection=null;$('json').value=JSON.stringify(imported,null,2);selected.clear();await applyPreferences({budget:'2500',months:12});message('Loaded a synthetic fee-lab scenario. It is not bookable. Inspect the card breakdown or save a collection.');}));
const collectionButtons=el('div',undefined,'button-row');collectionArea.append(collectionButtons);
const collectionList=el('div',undefined,'workspace-list');collectionArea.append(collectionList);
collectionButtons.append(action('Save as new collection',async()=>{const data=await api('/api/collections/create',{name:collectionName.value,provenance:provenance.value,listings:JSON.parse($('json').value)});activeCollection=data;await refreshCollections();message('Saved collection version 1. Original source dates were retained.');},true));
collectionButtons.append(action('Save revision',async()=>{if(!activeCollection)throw new Error('Load a collection first.');activeCollection=await api('/api/collections/revise',{id:activeCollection.id,expected_version:activeCollection.version,provenance:provenance.value,listings:JSON.parse($('json').value)});await refreshCollections();message('Saved immutable version '+activeCollection.version+'. Earlier versions remain available.');}));
const diffOutput=el('pre','Load a collection to compare revisions.');collectionArea.append(diffOutput);
collectionButtons.append(action('Compare latest revisions',async()=>{if(!activeCollection||activeCollection.version<2)throw new Error('Load a collection at version 2 or later.');const data=await api('/api/collections/diff',{id:activeCollection.id,before:activeCollection.version-1,after:activeCollection.version});diffOutput.textContent=JSON.stringify(data,null,2);message('Compared field changes between the loaded version and its predecessor.');}));
async function loadCollection(id,version){
 const data=await api('/api/collections/load',{id,...(version?{version}:{})});activeCollection=data;imported=data.listings;$('json').value=JSON.stringify(imported,null,2);collectionName.value=data.name;provenance.value=data.provenance;selected.clear();await evaluate();message('Loaded '+data.name+' · version '+data.version+' · '+data.provenance);
}
async function refreshCollections(){
 const response=await fetch('/api/collections');const data=await response.json();if(!response.ok)throw new Error(data.error);collectionList.replaceChildren();
 if(!data.collections.length)collectionList.append(el('p','No collections yet. Save the editor contents to start a versioned research set.','muted'));
 data.collections.forEach(c=>{const row=el('div',undefined,'workspace-row');row.append(el('strong',c.name),el('small','Version '+c.version+(c.archived?' · archived':' · active')));const buttons=el('div',undefined,'button-row');buttons.append(action('Load latest',()=>loadCollection(c.id)),action('Versions',async()=>{const data=await api('/api/collections/versions',{id:c.id});const history=el('div',undefined,'workspace-list');data.versions.forEach(v=>{const line=el('div');line.append(el('small','v'+v.version+' · '+new Date(v.created*1000).toLocaleString()+' · '+v.provenance),action('Load v'+v.version,()=>loadCollection(c.id,v.version)));history.append(line);});row.append(history);}),action(c.archived?'Restore':'Archive',async()=>{await api('/api/collections/archive',{id:c.id,archived:!c.archived});await refreshCollections();message(c.archived?'Collection restored.':'Collection archived; its version history is retained.');}));row.append(buttons);collectionList.append(row);});
}
refreshCollections().catch(e=>message(e.message));
const searchName=input('e.g. Shared home under $1,200');searchArea.append(field('Search name',searchName));
searchArea.append(action('Save current filters',async()=>{await api('/api/searches/save',{name:searchName.value,preferences:prefs()});await refreshSearches();message('Saved current filters. Listing data is stored separately in collections.');},true));
const searchList=el('div',undefined,'workspace-list');searchArea.append(searchList);
function applyPreferences(value){
 const defaults={budget:'2500',kind:'all',months:12,optional:false,known_only:false,sort:'total'};const p={...defaults,...value};$('sort').value=p.sort;
 $('budget').value=p.budget;$('kind').value=p.kind;$('months').value=p.months;$('optional').checked=p.optional;$('known').checked=p.known_only;
 return evaluate();
}
async function refreshSearches(){
 const response=await fetch('/api/searches');const data=await response.json();if(!response.ok)throw new Error(data.error);searchList.replaceChildren();
 if(!data.searches.length)searchList.append(el('p','Save useful filters and return to them later.','muted'));
 data.searches.forEach(s=>{const row=el('div',undefined,'workspace-row');row.append(el('strong',s.name),el('small',JSON.stringify(s.preferences)));const buttons=el('div',undefined,'button-row');buttons.append(action('Apply filters',async()=>{await applyPreferences(s.preferences);message('Applied saved search: '+s.name);}),action('Delete',async()=>{await api('/api/searches/delete',{id:s.id});await refreshSearches();message('Saved search deleted.');}));row.append(buttons);searchList.append(row);});
}
refreshSearches().catch(e=>message(e.message));
const exportButtons=el('div',undefined,'button-row');$('comparison').append(exportButtons);
function download(content,type,name){const url=URL.createObjectURL(new Blob([content],{type}));const link=el('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
for(const format of ['json','csv'])exportButtons.append(action('Download comparison '+format.toUpperCase(),async()=>{
 const ids=results.filter(x=>selected.has(x.id)).map(x=>x.id);if(!ids.length)throw new Error('Select at least one visible home to export.');
 const payload={preferences:prefs(),ids,format};if(imported)payload.listings=imported;
 const data=await api('/api/export',payload);download(data.content,format==='csv'?'text/csv;charset=utf-8':'application/json','rentwise-comparison.'+format);message('Downloaded source-cited '+format.toUpperCase()+' comparison. Unknown fees remain explicit.');
}));
const historyPanel=el('section',undefined,'panel');historyPanel.id='booking-history';historyPanel.append(el('div','SIMULATION ACTIVITY','eyebrow'),el('h2','Your sandbox requests.'),el('p','History survives a page refresh. These records never reserve a property or contact a host.','muted'));
const historyList=el('div',undefined,'workspace-list');historyPanel.append(action('Refresh booking history',refreshBookings),historyList);document.querySelector('.bottom-grid').after(historyPanel);
async function refreshBookings(){
 const response=await fetch('/api/bookings');const data=await response.json();if(!response.ok)throw new Error(data.error);historyList.replaceChildren();
 if(!data.bookings.length)historyList.append(el('p','No sandbox activity yet.','muted'));
 data.bookings.forEach(renderBooking);
}
function renderBooking(b){
 const row=el('div',undefined,'workspace-row');row.append(el('strong',b.listing+' · '+b.status),el('small',new Date(b.created*1000).toLocaleString()+' · '+b.key));
 const buttons=el('div',undefined,'button-row');
 buttons.append(action('Inspect status',async()=>{const status=await api('/api/bookings/status',{key:b.key});$('booking-result').textContent=JSON.stringify(status,null,2);message('Loaded current status without changing it.');}));
 if(b.status==='pending')buttons.append(action('Reconcile',async()=>{await api('/api/reconcile',{key:b.key});await refreshBookings();message('Reconciled simulated acknowledgement.');}));
 buttons.append(action('Audit trail',async()=>{const data=await api('/api/bookings/events',{key:b.key});const events=el('ol',undefined,'muted');data.events.forEach(event=>events.append(el('li',new Date(event.occurred*1000).toLocaleString()+': '+(event.previous_status||'new')+' → '+event.status+' · '+event.reason)));row.append(events);}));
 if(b.status!=='cancelled'){
  const consent=el('input');consent.type='checkbox';const label=field(' I explicitly consent to cancel this sandbox request.',consent);label.className='check consent';row.append(label);
  buttons.append(action('Cancel simulation',async()=>{if(!consent.checked)throw new Error('Check the cancellation consent box for this request.');await api('/api/bookings/cancel',{key:b.key,consent:true});await refreshBookings();message('Sandbox request cancelled. It cannot be reactivated by a retry.');}));
 }
 row.append(buttons);historyList.append(row);
}
refreshBookings().catch(e=>message(e.message));
const snapshotArea=el('div',undefined,'panel');snapshotArea.append(el('div','DECISION RECORDS','eyebrow'),el('h2','Save this comparison as a snapshot.'),el('p','Snapshots preserve the evaluated costs, filters and source text at save time. They are research records, never booking instructions.','muted'));
const snapshotName=input('e.g. First shortlist · November');snapshotArea.append(field('Snapshot name',snapshotName));
const snapshotList=el('div',undefined,'workspace-list');snapshotArea.append(action('Save selected comparison',async()=>{
 const listings=(imported||samples).filter(x=>selected.has(x.id)&&results.some(r=>r.id===x.id));if(!listings.length)throw new Error('Select at least one visible home first.');
 await api('/api/snapshots/save',{name:snapshotName.value,listings,preferences:prefs()});await refreshSnapshots();message('Saved immutable comparison snapshot.');
},true),snapshotList);$('comparison').after(snapshotArea);
async function refreshSnapshots(){
 const response=await fetch('/api/snapshots');const data=await response.json();if(!response.ok)throw new Error(data.error);snapshotList.replaceChildren();
 if(!data.snapshots.length)snapshotList.append(el('p','No saved decision records yet.','muted'));
 data.snapshots.forEach(s=>{const row=el('div',undefined,'workspace-row');row.append(el('strong',s.name),el('small',new Date(s.created*1000).toLocaleString()));const buttons=el('div',undefined,'button-row');
 buttons.append(action('Inspect snapshot',async()=>{const snapshot=await api('/api/snapshots/load',{id:s.id});const detail=el('pre',JSON.stringify(snapshot,null,2));row.append(detail);message('Viewing an immutable saved calculation; current filters were not changed.');}),action('Download JSON',async()=>{const snapshot=await api('/api/snapshots/load',{id:s.id});download(JSON.stringify(snapshot,null,2),'application/json','rentwise-snapshot-'+s.id+'.json');message('Downloaded saved research record.');}));row.append(buttons);snapshotList.append(row);});
}
refreshSnapshots().catch(e=>message(e.message));
