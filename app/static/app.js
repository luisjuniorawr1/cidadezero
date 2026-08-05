const els = {
  clock: document.querySelector('#clock'),
  stageTime: document.querySelector('#stage-time'),
  count: document.querySelector('#character-count'),
  eventCount: document.querySelector('#event-count'),
  engineStatus: document.querySelector('#engine-status'),
  connection: document.querySelector('#connection'),
  updated: document.querySelector('#updated-at'),
  characters: document.querySelector('#characters'),
  events: document.querySelector('#events'),
  cityStage: document.querySelector('#city-stage'),
  cityMap: document.querySelector('#city-map'),
  actorsLayer: document.querySelector('#actors-layer'),
  observer: document.querySelector('#observer-content'),
  worldStatus: document.querySelector('#world-status'),
  clearFollow: document.querySelector('#clear-follow'),
};

const labels = {
  energy: 'Energia',
  hunger: 'Fome',
  social: 'Social',
  curiosity: 'Curiosidade',
};

const palettes = {
  chatgpt: ['#83f3bd', '#235d49'],
  claude: ['#f3a36b', '#743e27'],
  deepseek: ['#71bcff', '#234f75'],
  gemini: ['#b69cff', '#503c7f'],
  grok: ['#f2f4f5', '#4d555b'],
  meta_ai: ['#6fd4ff', '#235a74'],
  manus: ['#ffd36d', '#705522'],
};

const baseLayout = {
  praca: { x: 50, y: 48, kind: 'plaza', icon: '◆' },
  cafe: { x: 28, y: 39, kind: 'social', icon: '☕' },
  biblioteca: { x: 71, y: 31, kind: 'study', icon: '▤' },
  laboratorio: { x: 80, y: 57, kind: 'work', icon: '⌬' },
  prefeitura: { x: 49, y: 22, kind: 'civic', icon: '▥' },
  mercado: { x: 20, y: 63, kind: 'commerce', icon: '▣' },
  parque: { x: 48, y: 73, kind: 'park', icon: '♣' },
  oficina: { x: 70, y: 77, kind: 'work', icon: '⚙' },
  casa_chatgpt: { x: 9, y: 22, kind: 'home', icon: '⌂' },
  casa_claude: { x: 25, y: 15, kind: 'home', icon: '⌂' },
  casa_deepseek: { x: 41, y: 11, kind: 'home', icon: '⌂' },
  casa_gemini: { x: 58, y: 11, kind: 'home', icon: '⌂' },
  casa_grok: { x: 75, y: 15, kind: 'home', icon: '⌂' },
  casa_meta_ai: { x: 91, y: 24, kind: 'home', icon: '⌂' },
  casa_manus: { x: 91, y: 73, kind: 'home', icon: '⌂' },
};

const fallbackSpots = [
  { x: 11, y: 82 }, { x: 27, y: 86 }, { x: 43, y: 88 },
  { x: 59, y: 88 }, { x: 76, y: 85 }, { x: 90, y: 84 },
];

const actorNodes = new Map();
let latestState = null;
let selectedId = null;
let overviewMode = false;
let mapReady = false;

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[character]));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function layoutFor(locationId, fallbackIndex = 0) {
  return baseLayout[locationId] || fallbackSpots[fallbackIndex % fallbackSpots.length] || { x: 50, y: 50 };
}

function periodForMinute(minute) {
  const hour = Math.floor(minute / 60);
  if (hour >= 5 && hour < 8) return 'dawn';
  if (hour >= 8 && hour < 18) return 'day';
  if (hour >= 18 && hour < 21) return 'dusk';
  return 'night';
}

function buildCity(locations) {
  const locationMap = new Map(locations.map(location => [location.id, location]));
  const locationIds = [...new Set([...Object.keys(baseLayout), ...locationMap.keys()])];

  els.cityMap.innerHTML = `
    <div class="road road-a"></div>
    <div class="road road-b"></div>
    <div class="road road-c"></div>
    <div class="water-line"></div>
    <div class="city-sign"><b>CIDADE ZERO</b><span>Distrito experimental</span></div>
    ${locationIds.map((locationId, index) => {
      const location = locationMap.get(locationId);
      const layout = layoutFor(locationId, index);
      const name = location?.name || locationId.replace(/^casa_/, 'Casa de ').replaceAll('_', ' ');
      const kind = layout.kind || location?.kind || 'public';
      const icon = layout.icon || '◆';
      return `
        <div class="place place-${escapeHtml(kind)}" data-location="${escapeHtml(locationId)}"
             style="--x:${layout.x}%;--y:${layout.y}%">
          <div class="place-shadow"></div>
          <div class="building">
            <div class="building-roof"></div>
            <div class="building-face"><span>${escapeHtml(icon)}</span></div>
          </div>
          <span class="place-label">${escapeHtml(name)}</span>
        </div>`;
    }).join('')}
  `;
  mapReady = true;
}

function needBars(needs = {}, compact = false) {
  return Object.entries(needs).map(([key, rawValue]) => {
    const value = clamp(Number(rawValue) || 0, 0, 100);
    return `
      <div class="need ${compact ? 'need-compact' : ''}">
        <span>${escapeHtml(labels[key] ?? key)}</span>
        <div class="bar"><i style="width:${Math.round(value)}%"></i></div>
        <b>${Math.round(value)}</b>
      </div>`;
  }).join('');
}

function characterCard(character) {
  return `
    <button class="character-card ${selectedId === character.character_id ? 'is-selected' : ''}"
            type="button" data-character="${escapeHtml(character.character_id)}">
      <header>
        <h3>${escapeHtml(character.public_name)}</h3>
        <span class="status-chip">${escapeHtml(character.mood)}</span>
      </header>
      <p class="role">${escapeHtml(character.archetype || character.city_role || 'Morador experimental')}</p>
      <p class="current-action">${escapeHtml(character.action)}</p>
      <div class="meta-row">
        <span>${escapeHtml(readableLocation(character.location))}</span>
        <span>${escapeHtml(character.central_value || '')}</span>
      </div>
      <div class="needs">${needBars(character.needs)}</div>
    </button>`;
}

function eventRow(event) {
  const hour = String(Math.floor(event.city_minute / 60)).padStart(2, '0');
  const minute = String(event.city_minute % 60).padStart(2, '0');
  return `<article class="event"><time>Dia ${event.city_day}<br>${hour}:${minute}</time><p>${escapeHtml(event.summary)}</p></article>`;
}

function readableLocation(locationId) {
  const location = latestState?.locations?.find(item => item.id === locationId);
  return location?.name || String(locationId || 'local desconhecido').replace(/^casa_/, 'Casa de ').replaceAll('_', ' ');
}

function actorMarkup(character) {
  const colors = palettes[character.character_id] || ['#84f2bd', '#285743'];
  const initials = character.public_name.split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase();
  return `
    <span class="actor-action">${escapeHtml(character.action)}</span>
    <span class="actor-shadow"></span>
    <span class="pixel-person" style="--actor-main:${colors[0]};--actor-dark:${colors[1]}">
      <i class="pixel-head"><em>${escapeHtml(initials)}</em></i>
      <i class="pixel-body"></i>
      <i class="pixel-leg pixel-leg-a"></i>
      <i class="pixel-leg pixel-leg-b"></i>
    </span>
    <strong>${escapeHtml(character.public_name)}</strong>
    <small>${escapeHtml(character.mood)}</small>
  `;
}

function renderActors(characters) {
  const grouped = new Map();
  characters.forEach(character => {
    if (!grouped.has(character.location)) grouped.set(character.location, []);
    grouped.get(character.location).push(character);
  });

  const activeIds = new Set(characters.map(character => character.character_id));
  const offsets = [
    [0, 0], [-3.6, 2.2], [3.6, 2.2], [-6.2, 4.6], [6.2, 4.6], [0, 5.4], [0, -3],
  ];

  characters.forEach((character, index) => {
    const group = grouped.get(character.location) || [character];
    const groupIndex = group.findIndex(item => item.character_id === character.character_id);
    const [offsetX, offsetY] = offsets[groupIndex] || [groupIndex * 2, groupIndex * 2];
    const location = layoutFor(character.location, index);
    const x = clamp(location.x + offsetX, 4, 96);
    const y = clamp(location.y + offsetY, 8, 92);

    let node = actorNodes.get(character.character_id);
    if (!node) {
      node = document.createElement('button');
      node.type = 'button';
      node.className = 'actor';
      node.dataset.character = character.character_id;
      node.addEventListener('click', () => selectCharacter(character.character_id));
      els.actorsLayer.appendChild(node);
      actorNodes.set(character.character_id, node);
    }

    const previousLocation = node.dataset.location;
    const previousX = Number(node.dataset.x || x);
    node.innerHTML = actorMarkup(character);
    node.dataset.location = character.location;
    node.dataset.x = String(x);
    node.dataset.mood = character.mood;
    node.style.left = `${x}%`;
    node.style.top = `${y}%`;
    node.style.zIndex = String(Math.round(y * 10));
    node.classList.toggle('is-selected', selectedId === character.character_id);
    node.classList.toggle('facing-left', x < previousX);

    if (previousLocation && previousLocation !== character.location) {
      node.classList.add('is-walking');
      window.setTimeout(() => node.classList.remove('is-walking'), 1400);
    }
  });

  for (const [characterId, node] of actorNodes.entries()) {
    if (!activeIds.has(characterId)) {
      node.remove();
      actorNodes.delete(characterId);
    }
  }
}

function selectCharacter(characterId) {
  overviewMode = false;
  selectedId = characterId;
  renderSelection();
  document.querySelectorAll('[data-character]').forEach(node => {
    node.classList.toggle('is-selected', node.dataset.character === characterId);
  });
}

function renderSelection() {
  if (!latestState) return;
  const character = latestState.characters.find(item => item.character_id === selectedId);
  if (!character) {
    selectedId = null;
    els.observer.innerHTML = `
      <h2>Escolha um morador</h2>
      <p class="observer-empty">Clique em alguém no mapa para ver sua ação, localização, humor e necessidades.</p>`;
    return;
  }

  const recentEvent = latestState.events.find(event => event.character_id === character.character_id);
  els.observer.innerHTML = `
    <div class="observer-title">
      <div>
        <span class="observer-kicker">ACOMPANHANDO</span>
        <h2>${escapeHtml(character.public_name)}</h2>
      </div>
      <span class="observer-mood">${escapeHtml(character.mood)}</span>
    </div>
    <p class="observer-role">${escapeHtml(character.archetype || character.city_role || 'Morador experimental')}</p>
    <div class="observer-action">
      <span>AGORA</span>
      <strong>${escapeHtml(character.action)}</strong>
      <small>${escapeHtml(readableLocation(character.location))}</small>
    </div>
    <div class="observer-needs">${needBars(character.needs, true)}</div>
    <div class="observer-event">
      <span>ÚLTIMO REGISTRO</span>
      <p>${escapeHtml(recentEvent?.summary || 'Nenhum acontecimento recente registrado.')}</p>
    </div>`;
}

function render(state) {
  latestState = state;
  if (!mapReady) buildCity(state.locations || []);
  if (!selectedId && !overviewMode && state.characters.length) selectedId = state.characters[0].character_id;

  const period = periodForMinute(state.city.minute);
  els.cityStage.dataset.period = period;
  els.clock.textContent = `Dia ${state.city.day} — ${state.city.time}`;
  els.stageTime.textContent = `Dia ${state.city.day} · ${state.city.time}`;
  els.count.textContent = state.characters.length;
  els.eventCount.textContent = state.events.length;
  els.engineStatus.textContent = state.city.running ? 'ativo' : 'pausado';
  els.worldStatus.textContent = `${state.characters.length} moradores · ${readablePeriod(period)}`;
  els.characters.innerHTML = state.characters.map(characterCard).join('');
  els.events.innerHTML = state.events.map(eventRow).join('');
  els.updated.textContent = `Atualizado às ${new Date().toLocaleTimeString('pt-BR')}`;

  renderActors(state.characters);
  renderSelection();

  document.querySelectorAll('.character-card').forEach(card => {
    card.addEventListener('click', () => selectCharacter(card.dataset.character));
  });
}

function readablePeriod(period) {
  return ({ dawn: 'amanhecer', day: 'dia', dusk: 'entardecer', night: 'noite' })[period] || period;
}

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${location.host}/ws`);

  socket.addEventListener('open', () => {
    els.connection.textContent = 'online';
    els.connection.closest('span')?.classList.add('is-online');
  });

  socket.addEventListener('message', event => {
    try {
      render(JSON.parse(event.data));
    } catch (error) {
      console.error('Estado inválido recebido da Cidade Zero', error);
    }
  });

  socket.addEventListener('close', () => {
    els.connection.textContent = 'reconectando';
    els.connection.closest('span')?.classList.remove('is-online');
    window.setTimeout(connect, 1500);
  });

  socket.addEventListener('error', () => socket.close());
}

els.clearFollow.addEventListener('click', () => {
  overviewMode = true;
  selectedId = null;
  document.querySelectorAll('[data-character]').forEach(node => node.classList.remove('is-selected'));
  renderSelection();
});

connect();
