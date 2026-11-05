const $ = id => document.getElementById(id);
const usd = value => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(value);
let samples=[], imported=null, results=[], selected=new Set(), bookingKey=null, suggestion=null;
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
async function api(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw new Error(data.error || 'Request failed');return data;}
function prefs(){return {budget:$('budget').value,kind:$('kind').value,months:Number($('months').value),optional:$('optional').checked,known_only:$('known').checked,sort:$('sort')?.value||'total'};}
let evaluationSequence=0;
async function evaluate(){
 const sequence=++evaluationSequence;$('cards').setAttribute('aria-busy','true');$('notice').textContent='Evaluating known costs…';
 try{const payload=prefs();if(imported)payload.listings=imported;const response=await api('/api/evaluate',payload);if(sequence!==evaluationSequence)return;results=response.results;
 selected=new Set([...selected].filter(id=>results.some(x=>x.id===id)));$('notice').textContent=response.excluded.length+' homes excluded by your filters. Unknown charges are never treated as a final price.';render();
 }catch(e){if(sequence===evaluationSequence)$('notice').textContent=e.message;}
 finally{if(sequence===evaluationSequence)$('cards').setAttribute('aria-busy','false');}
}
function render(){
 queueMicrotask(renderFinancialDetails);
 $('count').replaceChildren(el('span',String(results.length)+' possibilities'));$('lowest').textContent=results.length?usd(Math.min(...results.map(x=>Number(x.cost.monthly))))+' /mo':'—';
 $('complete').textContent=results.filter(x=>x.cost.complete).length+' fully specified';$('cards').replaceChildren();
 if(!results.length)$('cards').append(el('p','No homes match. Try a larger budget or include unknown fees.','empty'));
 results.forEach((x,i)=>{const card=el('article',undefined,'card');const art=el('div',undefined,'art tone-'+i);art.append(el('span',x.kind==='room'?'PRIVATE ROOM':'ENTIRE PLACE','tag'),el('span','ILLUSTRATIVE ARCHITECTURE','sample'));const b=el('div',undefined,'card-body');b.append(el('div',x.area+' · San Diego','location'),el('h3',x.name));const p=el('div',undefined,'price-row');const price=el('div',usd(x.cost.monthly),'price');price.append(el('small',' / month'));p.append(price,el('span',x.cost.complete?'Fees specified':'Unknown fees','cost-note'+(x.cost.complete?' complete':'')));b.append(p);const breakdown=el('div',undefined,'breakdown');[['Base rent',x.base],['Required /mo',x.required],['Upfront',x.upfront]].forEach(([k,v])=>{const d=el('div',k);d.append(el('strong',usd(v)));breakdown.append(d);});b.append(breakdown);const note=el('p',usd(x.cost.total)+' known total over '+x.cost.months+' months'+(x.cost.complete?'':' + unspecified charges'),'muted');b.append(note);const bottom=el('div',undefined,'card-bottom');const btn=el('button',selected.has(x.id)?'✓ Added to comparison':'+ Compare home');btn.onclick=()=>{if(selected.has(x.id))selected.delete(x.id);else if(selected.size<3)selected.add(x.id);else{$('notice').textContent='Choose up to three homes to compare.';return;}render();};bottom.append(el('span',x.source.split(' · ')[0],'source'),btn);b.append(bottom);card.append(art,b);$('cards').append(card);});renderCompare();
}
function renderFinancialDetails(){
 document.querySelectorAll('#cards .card-body').forEach((body,index)=>{
  const item=results[index];if(!item)return;
  const details=el('details');details.append(el('summary','Cost breakdown & decision notes'));
  if(item.cost.explanation)details.append(el('p',item.cost.explanation,'muted'));
  if(item.cost.components){
   item.cost.components.forEach(fee=>{const row=el('div',undefined,'fee-line');row.append(el('span',fee.label+(fee.refundable?' · refundable':'')+(fee.required?'':' · optional')),el('strong',fee.amount===null?'Unspecified':usd(fee.amount)+(fee.cadence==='monthly'?'/mo':' once')));details.append(row);});
   const totals=el('p','Known cash outlay: '+usd(item.cost.cash_outlay)+' · Refundable deposit: '+usd(item.cost.refundable_deposits)+' · Effective monthly expense: '+usd(item.cost.effective_monthly),'muted');details.append(totals);
   details.append(el('p','Move-in cash before credits: '+usd(item.cost.move_in_cash)+'. Credits do not assume immediate cash reimbursement.','muted'));
  }
  if(item.warnings?.length){const warnings=el('ul',undefined,'warning-list');item.warnings.forEach(value=>warnings.append(el('li',value)));details.append(warnings);}
  if(item.ranking)details.append(el('p','Rank '+item.ranking.position+': '+item.ranking.basis+'. Known monthly budget headroom: '+usd(item.ranking.known_budget_headroom),'muted'));
  details.append(el('blockquote',item.excerpt,'muted'),el('p',item.source+' · '+item.observed_at,'source'));body.append(details);
 });
}
function renderCompare(){const matches=results.filter(x=>selected.has(x.id));$('compare').replaceChildren();$('selection').textContent=matches.length+' of 3 homes selected';if(!matches.length){$('compare').append(el('p','Select homes above to inspect their full source excerpts.','muted'));return;}matches.forEach(x=>{const d=el('div',undefined,'compare-item');d.append(el('small',x.kind==='room'?'PRIVATE ROOM · SHARED HOME':'ENTIRE PLACE'),el('h3',x.name),el('p',usd(x.cost.total)+' / '+x.cost.months+' months'),el('p','Optional extras: '+usd(x.optional)+'/mo ('+(x.cost.optional_included?'included':'excluded')+')'),el('p','Unknown: '+(x.unknown.join(', ')||'none stated')),el('blockquote',x.excerpt),el('p',x.source+' · observed '+x.observed_at,'source'));$('compare').append(d);});}
['budget','kind','months','optional','known'].forEach(id=>$(id).addEventListener('change',evaluate));
$('import').onclick=()=>{try{imported=JSON.parse($('json').value);selected.clear();evaluate();}catch(e){$('notice').textContent='Invalid JSON: '+e.message;}};
$('reset').onclick=()=>{imported=null;$('json').value=JSON.stringify(samples,null,2);selected.clear();evaluate();};
$('book').onclick=async()=>{try{if(!bookingKey)bookingKey=crypto.randomUUID();const data=await api('/api/book',{listing:$('booking-home').value,key:bookingKey,consent:$('consent').checked});$('booking-result').textContent=JSON.stringify(data,null,2);$('reconcile').disabled=false;$('book').textContent='Retry same request';}catch(e){$('booking-result').textContent=e.message;}};
$('booking-home').onchange=()=>{bookingKey=null;$('book').textContent='Create sandbox request ↗';$('reconcile').disabled=true;$('booking-result').textContent='Ready for a new sandbox request.';};
$('reconcile').onclick=async()=>{try{$('booking-result').textContent=JSON.stringify(await api('/api/reconcile',{key:bookingKey}),null,2);}catch(e){$('booking-result').textContent=e.message;}};
$('model').onclick=async()=>{try{suggestion=await api('/api/preferences',{text:$('model-prompt').value});$('model-result').textContent=JSON.stringify(suggestion,null,2);$('apply-model').disabled=false;}catch(e){$('model-result').textContent=e.message;}};
$('apply-model').onclick=()=>{if(!suggestion)return;for(const id of ['budget','kind','months'])if(suggestion[id]!==undefined)$(id).value=suggestion[id];for(const [key,id] of [['optional','optional'],['known_only','known']])if(suggestion[key]!==undefined)$(id).checked=suggestion[key];evaluate();};
fetch('/api/listings').then(r=>r.json()).then(d=>{samples=d.listings;$('json').value=JSON.stringify(samples,null,2);samples.forEach(x=>{const opt=el('option',x.name);opt.value=x.id;$('booking-home').append(opt);});evaluate();}).catch(e=>{$('notice').textContent=e.message;});
