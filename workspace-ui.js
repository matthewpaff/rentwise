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
