(() => {
  'use strict';

  const stage = document.querySelector('#city-stage');
  const zoomIn = document.querySelector('#map-zoom-in');
  const zoomOut = document.querySelector('#map-zoom-out');
  if (!stage) return;

  stage.classList.add('ai-art-mode');
  if (zoomIn) zoomIn.hidden = true;
  if (zoomOut) zoomOut.hidden = true;

  const layer = document.createElement('div');
  layer.className = 'ai-residents-layer';
  layer.setAttribute('aria-label', 'Moradores no mapa da Cidade Zero');
  stage.appendChild(layer);

  const credit = document.createElement('span');
  credit.className = 'ai-art-credit';
  credit.textContent = 'cenário gerado por IA';
  stage.appendChild(credit);

  const anchors = {
    casa_claude: [15, 18],
    casa_gemini: [34, 19],
    casa_grok: [55, 16],
    casa_deepseek: [82, 18],
    casa_chatgpt: [13, 50],
    casa_meta_ai: [91, 47],
    casa_manus: [13, 85],
    cafe: [36, 52],
    praca: [52, 54],
    biblioteca: [72, 51],
    laboratorio: [84, 35],
    oficina: [71, 66],
    mercado: [29, 82],
    centro_comunitario: [89, 77],
    prefeitura: [49, 28],
    parque: [42, 72],
    clinica: [49, 92],
    lavanderia: [63, 92]
  };

  const colors = {
    chatgpt: '#73e3ad',
    claude: '#df8956',
    deepseek: '#58aefe',
    gemini: '#a987f2',
    grok: '#e6ecee',
    meta_ai: '#55c6ed',
    manus: '#e8bf58'
  };

  function initials(name) {
    return String(name || '?')
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(part => part[0])
      .join('')
      .toUpperCase();
  }

  function stateSnapshot() {
    try {
      return typeof latestState !== 'undefined' ? latestState : null;
    } catch (_) {
      return null;
    }
  }

  function selectedCharacterId() {
    try {
      return typeof selectedId !== 'undefined' ? selectedId : null;
    } catch (_) {
      return null;
    }
  }

  function select(id) {
    try {
      if (typeof selectCharacter === 'function') {
        selectCharacter(id);
      }
    } catch (_) {
      // O painel continua funcionando mesmo se a seleção ainda não estiver pronta.
    }
  }

  function renderPins() {
    const snapshot = stateSnapshot();
    if (!snapshot || !Array.isArray(snapshot.characters)) return;

    const selected = selectedCharacterId();
    const grouped = new Map();
    snapshot.characters.forEach(character => {
      const key = character.location || 'praca';
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(character);
    });

    const fragment = document.createDocumentFragment();
    grouped.forEach((characters, locationId) => {
      const [baseX, baseY] = anchors[locationId] || anchors.praca;
      characters.forEach((character, index) => {
        const spread = characters.length > 1 ? 4.2 : 0;
        const offsetX = (index - (characters.length - 1) / 2) * spread;
        const offsetY = index % 2 ? 2.4 : 0;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'ai-resident-pin';
        if (selected === character.character_id) button.classList.add('is-selected');
        button.style.left = `${baseX + offsetX}%`;
        button.style.top = `${baseY + offsetY}%`;
        button.style.setProperty('--pin', colors[character.character_id] || '#75e6ac');
        button.setAttribute('aria-label', `${character.public_name}: ${character.action || 'sem atividade registrada'}`);
        button.addEventListener('click', () => select(character.character_id));

        const core = document.createElement('span');
        core.className = 'ai-pin-core';
        core.textContent = initials(character.public_name);

        const label = document.createElement('span');
        label.className = 'ai-resident-label';
        label.textContent = character.public_name || character.character_id;

        const action = document.createElement('small');
        action.textContent = character.action || 'sem atividade registrada';
        label.appendChild(action);

        button.append(core, label);
        fragment.appendChild(button);
      });
    });

    layer.replaceChildren(fragment);
  }

  renderPins();
  window.setInterval(renderPins, 1200);
  window.addEventListener('resize', renderPins);
})();
