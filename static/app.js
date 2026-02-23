let siblingCount = 0;

function toggleExtra(){
  document.getElementById('extraBox')?.classList.toggle('hidden');
}

function toggleCardFields(cb,prefix){
  document.getElementById(prefix+'_card_extra')?.classList.toggle('hidden', !cb.checked);
}

function addSibling(){
  siblingCount++;
  if(siblingCount>5) return;
  const id='sibling'+siblingCount;
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
        <input name="${id}_name" placeholder="Ex: Popescu Mara">
      </label>
      <label>Sosete
        <input type="number" min="0" name="${id}_socks" value="0">
      </label>

      <label>
        <input type="checkbox" name="${id}_wants_card" onchange="toggleCardFields(this,'${id}')"> Doreste card fidelitate
      </label>

      <div></div>

      <div id="${id}_card_extra" class="hidden subgrid">
        <label>Data nasterii
          <input type="date" name="${id}_birth_date">
        </label>
        <label>Acord poze
          <select name="${id}_photo_consent"><option value="yes">Da</option><option value="no">Nu</option></select>
        </label>
      </div>
    </div>`;
  document.getElementById('siblings').appendChild(box);
}

function removeSibling(id){
  document.getElementById(id)?.remove();
}
