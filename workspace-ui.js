/* Persistent local workspace controls; all user text is rendered as text nodes. */
const workspacePanel=el('section',undefined,'panel workspace-panel');workspacePanel.id='workspace';
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
const collectionButtons=el('div',undefined,'button-row');collectionArea.append(collectionButtons);
const collectionList=el('div',undefined,'workspace-list');collectionArea.append(collectionList);
collectionButtons.append(action('Save as new collection',async()=>{const data=await api('/api/collections/create',{name:collectionName.value,provenance:provenance.value,listings:JSON.parse($('json').value)});activeCollection=data;await refreshCollections();message('Saved collection version 1. Original source dates were retained.');},true));
collectionButtons.append(action('Save revision',async()=>{if(!activeCollection)throw new Error('Load a collection first.');activeCollection=await api('/api/collections/revise',{id:activeCollection.id,expected_version:activeCollection.version,provenance:provenance.value,listings:JSON.parse($('json').value)});await refreshCollections();message('Saved immutable version '+activeCollection.version+'. Earlier versions remain available.');}));
async function loadCollection(id,version){
 const data=await api('/api/collections/load',{id,...(version?{version}:{})});activeCollection=data;imported=data.listings;$('json').value=JSON.stringify(imported,null,2);collectionName.value=data.name;provenance.value=data.provenance;selected.clear();await evaluate();message('Loaded '+data.name+' · version '+data.version+' · '+data.provenance);
}
async function refreshCollections(){
 const response=await fetch('/api/collections');const data=await response.json();if(!response.ok)throw new Error(data.error);collectionList.replaceChildren();
 if(!data.collections.length)collectionList.append(el('p','No collections yet. Save the editor contents to start a versioned research set.','muted'));
 data.collections.forEach(c=>{const row=el('div',undefined,'workspace-row');row.append(el('strong',c.name),el('small','Version '+c.version+(c.archived?' · archived':' · active')));const buttons=el('div',undefined,'button-row');buttons.append(action('Load latest',()=>loadCollection(c.id)),action('Versions',async()=>{const data=await api('/api/collections/versions',{id:c.id});const history=el('div',undefined,'workspace-list');data.versions.forEach(v=>{const line=el('div');line.append(el('small','v'+v.version+' · '+new Date(v.created*1000).toLocaleString()+' · '+v.provenance),action('Load v'+v.version,()=>loadCollection(c.id,v.version)));history.append(line);});row.append(history);}));row.append(buttons);collectionList.append(row);});
}
refreshCollections().catch(e=>message(e.message));
