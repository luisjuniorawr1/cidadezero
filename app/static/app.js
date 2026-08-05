const els = {
  clock: document.querySelector('#clock'),
  count: document.querySelector('#character-count'),
  eventCount: document.querySelector('#event-count'),
  connection: document.querySelector('#connection'),
  updated: document.querySelector('#updated-at'),
  characters: document.querySelector('#characters'),
  events: document.querySelector('#events'),
};

const labels = {
  energy: 'Energia', hunger: 'Fome', social: 'Social', curiosity: 'Curiosidade'
};

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function characterCard(character) {
  const needs = Object.entries(character.needs).map(([key, value]) => `
    <div class="need"><span>${labels[key] ?? key}</span><div class="bar"><i style="width:${Math.round(value)}%"></i></div><b>${Math.round(value)}</b></div>
  `).join('');
  return `
    <article class="character-card">
      <header><h3>${escapeHtml(character.public_name)}</h3><span class="status-chip">${escapeHtml(character.mood)}</span></header>
      <p class="role">${escapeHtml(character.archetype || character.city_role || 'Morador experimental')}</p>
      <p class="current-action">${escapeHtml(character.action)}</p>
      <div class="meta-row"><span>${escapeHtml(character.location)}</span><span>${escapeHtml(character.central_value || '')}</span></div>
      <div class="needs">${needs}</div>
    </article>`;
}

function eventRow(event) {
  const hour = String(Math.floor(event.city_minute / 60)).padStart(2, '0');
  const minute = String(event.city_minute % 60).padStart(2, '0');
  return `<article class="event"><time>Dia ${event.city_day}<br>${hour}:${minute}</time><p>${escapeHtml(event.summary)}</p></article>`;
}

function render(state) {
  els.clock.textContent = `Dia ${state.city.day} — ${state.city.time}`;
  els.count.textContent = state.characters.length;
  els.eventCount.textContent = state.events.length;
  els.characters.innerHTML = state.characters.map(characterCard).join('');
  els.events.innerHTML = state.events.map(eventRow).join('');
  els.updated.textContent = `Atualizado às ${new Date().toLocaleTimeString('pt-BR')}`;
}

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${location.host}/ws`);
  socket.addEventListener('open', () => { els.connection.textContent = 'online'; });
  socket.addEventListener('message', event => render(JSON.parse(event.data)));
  socket.addEventListener('close', () => {
    els.connection.textContent = 'reconectando';
    setTimeout(connect, 1500);
  });
  socket.addEventListener('error', () => socket.close());
}

connect();
