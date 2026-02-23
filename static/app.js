let siblingCount = 0;
function toggleExtra(){document.getElementById('extraBox')?.classList.toggle('hidden')}
function toggleCardFields(cb,prefix){document.getElementById(prefix+'_card_extra')?.classList.toggle('hidden', !cb.checked)}
async function findLoyalty(name,prefix){
  if(!name) return;
  const r = await fetch('/api/loyalty/find',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
  const data = await r.json();
  if(data.found){
    document.querySelector(`input[name="${prefix}_name"]`).value = data.name;
    document.querySelector(`input[name="${prefix}_loyalty_id"]`).value = data.id;
  }
}
function addSibling(){
  siblingCount++; if(siblingCount>5) return;
  const id='sibling'+siblingCount;
  const box=document.createElement('div'); box.className='card'; box.id=id+'_box';
  box.innerHTML=`<div style="display:flex;justify-content:space-between"><h4>Frate ${siblingCount}</h4><button type="button" onclick="removeSibling('${id}_box')">X</button></div>
  <div class="grid">
    <label>Nume <input name="${id}_name"></label>
    <label><input type="checkbox" name="${id}_has_card"> Are card fidelitate</label>
    <label>Nume cautare card <input onblur="findLoyalty(this.value,'${id}')"></label>
    <input type="hidden" name="${id}_loyalty_id">
    <label>Sosete <input type="number" min="0" name="${id}_socks" value="0"></label>
  </div>`;
  document.getElementById('siblings').appendChild(box);
}
function removeSibling(id){document.getElementById(id)?.remove();}
