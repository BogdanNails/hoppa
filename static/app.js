let siblingCount = 0;

function toggleExtra(){
  document.getElementById('extraBox')?.classList.toggle('hidden');
}

function toggleCardFields(cb,prefix){
  document.getElementById(prefix+'_card_extra')?.classList.toggle('hidden', !cb.checked);
}

function addSibling(prefill = null){
  siblingCount++;
  if(siblingCount>5) return;
  const id='sibling'+siblingCount;
  const data = prefill || {name:'', wants_card:false, birth_date:'', photo_consent:'yes'};
  const box=document.createElement('div');
  box.className='card';
  box.id=id+'_box';
  box.innerHTML=`
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h4>Frate ${siblingCount}</h4>
      <button type="button" class="btn tiny danger" onclick="removeSibling('${id}_box')">X</button>
    </div>
    <div class="grid two-col">
      <label>Nume frate (Nume Prenume)
        <input name="${id}_name" placeholder="Ex: Popescu Mara" value="${(data.name||'').replace(/"/g,'&quot;')}">
      </label>

      <label class="checkline">
        <input type="checkbox" name="${id}_wants_card" onchange="toggleCardFields(this,'${id}')" ${data.wants_card ? 'checked' : ''}> Doreste card de fidelitate
      </label>

      <div id="${id}_card_extra" class="${data.wants_card ? '' : 'hidden'} subgrid">
        <label>Data nasterii
          <input type="date" name="${id}_birth_date" value="${data.birth_date||''}">
        </label>
        <label>Acord poze
          <select name="${id}_photo_consent">
            <option value="yes" ${(data.photo_consent||'yes')==='yes' ? 'selected' : ''}>Da</option>
            <option value="no" ${(data.photo_consent||'yes')==='no' ? 'selected' : ''}>Nu</option>
          </select>
        </label>
      </div>
    </div>`;
  document.getElementById('siblings').appendChild(box);
}

function removeSibling(id){
  document.getElementById(id)?.remove();
}

window.addEventListener('DOMContentLoaded', () => {
  const initial = window.initialSiblings || [];
  initial.forEach(item => addSibling(item));
});
