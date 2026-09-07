(() => {
  const data = window.COMPANION_DATA || [];
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const duplicateNames = new Set(data.filter((c, i) => data.findIndex(x => x.name === c.name) !== i).map(c => c.name));
  const state = {selected: data[0]?.id, level: 100};
  const coreNames = new Set(['ATK','DEF','HP','SPD']);
  const travelNames = new Set(['Travel Base Reward +','Travel Reward Bonus','Travel Extra Reward Chance']);
  const format = (name, value) => {
    if (name.includes('%') || ['Crit Rate','Crit RES','Accuracy','Block Rate','Crit DMG','Healing Boost','DMG Boost','DMG RES','Travel Reward Bonus','Travel Extra Reward Chance'].includes(name)) return `${Number(value).toLocaleString(undefined,{maximumFractionDigits:2})}%`;
    return Number(value).toLocaleString(undefined,{maximumFractionDigits:0});
  };
  const getSelected = () => data.find(c => c.id === state.selected) || data[0];
  const topSpecials = c => Object.entries(c.curve[c.maxLevel - 1] || {}).filter(([n]) => !coreNames.has(n) && !travelNames.has(n)).slice(0,3).map(([n,v]) => `${n} ${format(n,v)}`).join(' · ');

  function filtered() {
    const q = $('search').value.trim().toLowerCase();
    return data.filter(c => {
      const haystack = [c.name,c.nativeClass,c.catalog,c.gift,c.region,...c.recommended].join(' ').toLowerCase();
      return (!q || haystack.includes(q)) && (!$('recommendedFilter').value || c.recommended.includes($('recommendedFilter').value)) && (!$('nativeFilter').value || c.nativeClass === $('nativeFilter').value) && (!$('catalogFilter').value || c.catalog === $('catalogFilter').value) && (!$('rarityFilter').value || ($('rarityFilter').value === 'premium') === c.premium);
    });
  }

  function renderGrid() {
    const list = filtered();
    $('resultCount').textContent = `${list.length} of ${data.length}`;
    $('companionGrid').innerHTML = list.length ? list.map(c => `<button class="companion-card ${c.premium?'premium':''} ${c.id===state.selected?'active':''}" data-id="${c.id}">${c.art.icon?`<img src="${esc(c.art.icon)}" alt="">`:'<span class="card-fallback">✦</span>'}<span><strong>${esc(c.name)}</strong><small>${c.premium?'Premium':'Standard'} · ${esc(c.nativeClass)}</small><small class="mini-stats">${esc(topSpecials(c))}</small></span></button>`).join('') : '<p class="empty-results">No companions match these filters.</p>';
    document.querySelectorAll('.companion-card').forEach(button => button.addEventListener('click', () => { state.selected = Number(button.dataset.id); renderGrid(); renderDetail(); $('detailPanel').scrollIntoView({behavior:'smooth',block:'start'}); }));
  }

  function statRows(entries, empty='No bonus at this level') {
    return entries.length ? entries.map(([name,value]) => `<div class="stat-row"><span>${esc(name)}</span><b>${esc(format(name,value))}</b></div>`).join('') : `<div class="stat-row"><span>${esc(empty)}</span></div>`;
  }

  function renderDetail() {
    const c = getSelected(); if (!c) return;
    state.level = Math.max(1, Math.min(c.maxLevel, state.level));
    $('friendshipLevel').max = c.maxLevel; $('friendshipNumber').max = c.maxLevel;
    $('friendshipLevel').value = state.level; $('friendshipNumber').value = state.level; $('levelOutput').textContent = state.level;
    $('companionName').textContent = c.name;
    $('identityLine').textContent = `${c.catalog} companion · ${c.nativeClass} native combat class`;
    $('badges').innerHTML = `<span class="badge ${c.premium?'premium':''}">${c.premium?'Premium':'Standard'}</span><span class="badge">${c.catalog}</span>${duplicateNames.has(c.name)?`<span class="badge">Client entry ${c.id}</span>`:''}`;
    $('recommendedClasses').className = 'class-chips'; $('recommendedClasses').innerHTML = c.recommended.map(x => `<span class="class-chip">${esc(x)}</span>`).join('') || '<span class="class-chip">General</span>';
    $('quickFacts').innerHTML = `<div class="fact"><span>Favorite gifts</span><b>${esc(c.gift||'Not specified')}</b></div><div class="fact"><span>Region</span><b>${esc(c.region||'Client world entry')}</b></div><div class="fact"><span>Native class</span><b>${esc(c.nativeClass||'Not specified')}</b></div><div class="fact"><span>Friendship cap</span><b>Level ${c.maxLevel}</b></div>`;
    $('figure').src = c.art.figure || c.art.icon || ''; $('figure').alt = c.art.figure || c.art.icon ? `${c.name} artwork` : '';
    $('figure').hidden = !(c.art.figure || c.art.icon); $('portraitFallback').hidden = !($('figure').hidden);
    const stats = c.curve[state.level - 1] || {};
    const entries = Object.entries(stats);
    $('coreStats').innerHTML = statRows(entries.filter(([n]) => coreNames.has(n)));
    $('specialStats').innerHTML = statRows(entries.filter(([n]) => !coreNames.has(n) && !travelNames.has(n)));
    $('travelStats').innerHTML = statRows(entries.filter(([n]) => travelNames.has(n)));
    const nextExp = c.exp[state.level] || 0;
    $('levelNote').textContent = state.level < c.maxLevel ? `Next friendship level requires ${nextExp.toLocaleString()} cumulative friendship EXP.` : 'Maximum friendship level reached.';
    $('unlockLabel').textContent = c.unlock.label;
    $('unlockSources').innerHTML = c.unlock.sources.length ? c.unlock.sources.map(s => `<span class="source-chip">${esc(s)}</span>`).join('') : '<span class="source-chip">Client condition</span>';
    $('profiles').innerHTML = c.profiles.length ? c.profiles.map((p,i) => `<details ${i===0?'open':''}><summary>Profile ${esc(p.id)}${p.level?` · Friendship Lv${esc(p.level)}`:''}</summary><p>${esc(p.text)}</p></details>`).join('') : '<p class="notice">No localized profile chapters are present for this companion.</p>';
  }

  function setLevel(value) { state.level = Math.max(1, Math.min(getSelected().maxLevel, Number(value)||1)); renderDetail(); }
  ['search','recommendedFilter','nativeFilter','rarityFilter','catalogFilter'].forEach(id => $(id).addEventListener(id==='search'?'input':'change', renderGrid));
  $('friendshipLevel').addEventListener('input', e => setLevel(e.target.value)); $('friendshipNumber').addEventListener('input', e => setLevel(e.target.value));
  $('totalCount').textContent = data.length; $('premiumCount').textContent = data.filter(c=>c.premium).length;
  renderGrid(); renderDetail();
})();
