(() => {
  'use strict';

  const canvas = document.querySelector('#city-canvas');
  if (!canvas || !canvas.getContext) return;

  const ctx = canvas.getContext('2d', { alpha: false });
  const WIDTH = 512;
  const HEIGHT = 320;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const actorState = new Map();
  const hitboxes = [];
  let locations = [];
  let characters = [];
  let lastFrame = performance.now();

  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  ctx.imageSmoothingEnabled = false;
  els.cityStage.classList.add('canvas-mode');

  const periodPalettes = {
    dawn: {
      sky: '#8c776f', ground: '#426650', ground2: '#4d755b', road: '#3d4746',
      roadEdge: '#263130', line: '#d8bd76', water: '#376f78', waterLight: '#69a5a4',
      label: '#fff0c6', shadow: '#1a2b25', window: '#f4d18a', haze: 'rgba(255,190,135,.10)',
    },
    day: {
      sky: '#6f9a8b', ground: '#4f7a5e', ground2: '#5c8868', road: '#3e4b49',
      roadEdge: '#293533', line: '#d5c27d', water: '#367c80', waterLight: '#7fc0bb',
      label: '#f6f0ce', shadow: '#21342c', window: '#8ed1ca', haze: 'rgba(255,255,230,.03)',
    },
    dusk: {
      sky: '#735d69', ground: '#3d604d', ground2: '#486a54', road: '#394341',
      roadEdge: '#232e2c', line: '#c9aa69', water: '#315f70', waterLight: '#6f929a',
      label: '#ffe3bd', shadow: '#182721', window: '#f2c977', haze: 'rgba(255,125,90,.11)',
    },
    night: {
      sky: '#182b35', ground: '#294638', ground2: '#31503f', road: '#273331',
      roadEdge: '#16211f', line: '#8e8559', water: '#244c5b', waterLight: '#547e83',
      label: '#d9eee3', shadow: '#0b1512', window: '#ffd36d', haze: 'rgba(30,53,75,.18)',
    },
  };

  const buildingColors = {
    home: ['#c8b895', '#8c7058', '#b85f4a'],
    social: ['#d4a573', '#8d6047', '#b85b45'],
    study: ['#b6b79e', '#747d73', '#6f5aa1'],
    work: ['#aab5b1', '#687977', '#4b7585'],
    civic: ['#d4c7a8', '#8b846f', '#567a68'],
    commerce: ['#d4b17b', '#8a6543', '#be7743'],
    park: ['#789568', '#4d6e4d', '#3e7d53'],
    health: ['#cad1c4', '#78877e', '#5c8b83'],
    service: ['#bcb6a3', '#777164', '#80604e'],
    public: ['#c4bca3', '#77766a', '#61776c'],
  };

  const scenery = [
    [25, 170], [63, 122], [107, 245], [154, 95], [205, 266], [272, 91],
    [337, 253], [389, 112], [438, 246], [482, 156], [464, 73], [309, 283],
  ];

  function palette() {
    const period = els.cityStage.dataset.period || 'day';
    return periodPalettes[period] || periodPalettes.day;
  }

  function worldPoint(locationId, fallbackIndex = 0) {
    const source = layoutFor(locationId, fallbackIndex);
    return {
      x: Math.round(18 + (source.x / 100) * 476),
      y: Math.round(38 + (source.y / 100) * 244),
    };
  }

  function hash(value) {
    let result = 0;
    for (const char of String(value)) result = ((result << 5) - result + char.charCodeAt(0)) | 0;
    return Math.abs(result);
  }

  function actorOffset(characterId, groupIndex) {
    const seed = hash(characterId);
    const offsets = [[0, 0], [-9, 7], [9, 7], [-15, 13], [15, 13], [0, 17], [0, -9]];
    const chosen = offsets[groupIndex] || [((seed % 5) - 2) * 6, (Math.floor(seed / 7) % 4) * 5];
    return { x: chosen[0], y: chosen[1] };
  }

  function rect(x, y, w, h, fill) {
    ctx.fillStyle = fill;
    ctx.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
  }

  function line(points, color, width) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineCap = 'square';
    ctx.lineJoin = 'miter';
    ctx.beginPath();
    ctx.moveTo(Math.round(points[0][0]), Math.round(points[0][1]));
    points.slice(1).forEach(([x, y]) => ctx.lineTo(Math.round(x), Math.round(y)));
    ctx.stroke();
  }

  function text(value, x, y, color, align = 'center', size = 7) {
    ctx.font = `700 ${size}px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`;
    ctx.textAlign = align;
    ctx.textBaseline = 'top';
    ctx.fillStyle = color;
    ctx.fillText(String(value), Math.round(x), Math.round(y));
  }

  function drawGround(p) {
    rect(0, 0, WIDTH, HEIGHT, p.sky);
    rect(0, 30, WIDTH, HEIGHT - 30, p.ground);
    for (let y = 32; y < HEIGHT; y += 12) {
      for (let x = (y / 12) % 2 ? 0 : 6; x < WIDTH; x += 12) {
        if ((x + y) % 36 === 0) rect(x, y, 2, 2, p.ground2);
      }
    }
    rect(0, 29, WIDTH, 3, p.ground2);
    rect(0, 31, WIDTH, 1, 'rgba(255,255,255,.12)');
  }

  function drawRoads(p) {
    const center = worldPoint('praca');
    const routes = [
      ['prefeitura', 'cafe'], ['biblioteca', 'laboratorio'], ['mercado', 'oficina'],
      ['parque', 'praca'], ['casa_chatgpt', 'casa_meta_ai'], ['casa_claude', 'casa_grok'],
      ['casa_deepseek', 'casa_gemini'], ['casa_manus', 'praca'],
    ];
    routes.forEach(([a, b], index) => {
      const start = worldPoint(a, index);
      const end = worldPoint(b, index + 1);
      const midX = index % 2 ? center.x : Math.round((start.x + end.x) / 2);
      const path = [[start.x, start.y], [midX, start.y], [midX, end.y], [end.x, end.y]];
      line(path, p.roadEdge, 16);
      line(path, p.road, 12);
      if (index < 4) {
        ctx.setLineDash([7, 7]);
        line(path, p.line, 1);
        ctx.setLineDash([]);
      }
    });
  }

  function drawCanal(p) {
    const points = [[365, 286], [512, 245]];
    line(points, '#1d3f46', 29);
    line(points, p.water, 23);
    line(points, p.waterLight, 2);
    for (let index = 0; index < 6; index += 1) {
      const x = 382 + index * 23;
      rect(x, 278 - index * 6, 10, 1, 'rgba(220,255,245,.35)');
    }
  }

  function drawPlaza(p) {
    const center = worldPoint('praca');
    ctx.fillStyle = '#bdb18f';
    ctx.beginPath();
    ctx.moveTo(center.x, center.y - 27);
    ctx.lineTo(center.x + 44, center.y);
    ctx.lineTo(center.x, center.y + 27);
    ctx.lineTo(center.x - 44, center.y);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = '#756f5d';
    ctx.lineWidth = 2;
    ctx.stroke();
    rect(center.x - 10, center.y - 7, 20, 11, '#3f8790');
    rect(center.x - 7, center.y - 10, 14, 3, '#9cb3a5');
    rect(center.x - 2, center.y - 19, 4, 12, '#8dc9ca');
    rect(center.x - 4, center.y + 4, 8, 3, '#67665a');
  }

  function drawTree(x, y, p, scale = 1) {
    const trunkW = Math.max(2, Math.round(3 * scale));
    rect(x - trunkW / 2, y - 9 * scale, trunkW, 10 * scale, '#65472f');
    rect(x - 7 * scale, y - 20 * scale, 14 * scale, 11 * scale, '#244b34');
    rect(x - 10 * scale, y - 15 * scale, 20 * scale, 9 * scale, '#326743');
    rect(x - 5 * scale, y - 23 * scale, 10 * scale, 5 * scale, '#4f8357');
    rect(x - 8 * scale, y + 1, 16 * scale, 2, p.shadow);
  }

  function drawScenery(p) {
    scenery.forEach(([x, y], index) => drawTree(x, y, p, 0.75 + (index % 3) * 0.12));
    [[172, 174], [228, 194], [319, 171]].forEach(([x, y]) => {
      rect(x - 9, y - 3, 18, 3, '#795438');
      rect(x - 7, y, 2, 4, '#2b3532');
      rect(x + 5, y, 2, 4, '#2b3532');
    });
  }

  function drawBuilding(location, index, p) {
    if (location.id === 'praca' || location.id === 'parque') return;
    const layout = layoutFor(location.id, index);
    const point = worldPoint(location.id, index);
    const kind = layout.kind || location.kind || 'public';
    const colors = buildingColors[kind] || buildingColors.public;
    const width = kind === 'civic' ? 38 : 30;
    const height = kind === 'work' ? 25 : 21;
    const x = point.x - Math.round(width / 2);
    const y = point.y - height;
    rect(x - 4, point.y + 3, width + 8, 4, p.shadow);
    rect(x, y, width, height, colors[0]);
    rect(x + width - 7, y + 4, 7, height - 4, colors[1]);
    ctx.fillStyle = colors[2];
    ctx.beginPath();
    ctx.moveTo(x - 3, y + 3);
    ctx.lineTo(x + width / 2, y - 9);
    ctx.lineTo(x + width + 3, y + 3);
    ctx.closePath();
    ctx.fill();
    rect(x - 2, y + 3, width + 4, 2, '#47352d');
    rect(x + 4, point.y - 10, 6, 10, '#62462f');
    rect(x + width - 11, y + 9, 6, 6, p.window);
    if (width > 32) rect(x + width - 20, y + 9, 6, 6, p.window);
    rect(x + width - 9, y + 11, 1, 6, 'rgba(30,50,47,.5)');
    const shortName = String(location.name || location.id).replace('Casa de ', '').slice(0, 11).toUpperCase();
    const labelWidth = Math.max(24, shortName.length * 5 + 6);
    rect(point.x - labelWidth / 2, point.y + 7, labelWidth, 10, 'rgba(10,20,18,.82)');
    text(shortName, point.x, point.y + 9, p.label, 'center', 5);
  }

  function lookFor(character) {
    if (typeof detailedLooks !== 'undefined' && detailedLooks[character.character_id]) {
      return detailedLooks[character.character_id];
    }
    const colors = palettes[character.character_id] || palettes.chatgpt;
    return { main: colors[0], dark: colors[1], accent: '#eafff5', skin: '#c58d69', hair: '#25312d' };
  }

  function moodMark(mood) {
    if (/feliz|disposto|acolhido/.test(mood)) return '+';
    if (/preocupado|sobrecarregado|exausto|faminto|indisposto/.test(mood)) return '!';
    if (/solitário|sufocado/.test(mood)) return '~';
    return '·';
  }

  function drawActor(character, state, p, now) {
    const look = lookFor(character);
    const moving = now < state.moveUntil;
    const progress = moving ? Math.min(1, (now - state.moveStart) / Math.max(1, state.moveUntil - state.moveStart)) : 1;
    const eased = reducedMotion.matches ? 1 : 1 - Math.pow(1 - progress, 3);
    const x = Math.round(state.fromX + (state.targetX - state.fromX) * eased);
    const y = Math.round(state.fromY + (state.targetY - state.fromY) * eased);
    state.x = x;
    state.y = y;
    const bob = moving && !reducedMotion.matches ? Math.round(Math.sin(now / 75) * 1.2) : 0;
    const selected = selectedId === character.character_id;
    const spriteY = y - 15 + bob;
    rect(x - 5, y + 1, 10, 2, p.shadow);
    if (selected) {
      rect(x - 8, spriteY - 4, 16, 2, '#fff3a4');
      rect(x - 2, spriteY - 7, 4, 3, '#fff3a4');
    }
    rect(x - 3, spriteY, 6, 5, look.skin);
    rect(x - 4, spriteY - 2, 8, 3, look.hair);
    rect(x - 4, spriteY + 5, 8, 7, look.main);
    rect(x - 5, spriteY + 6, 2, 5, look.dark);
    rect(x + 3, spriteY + 6, 2, 5, look.dark);
    rect(x - 4, spriteY + 12, 3, 4, look.dark);
    rect(x + 1, spriteY + 12, 3, 4, look.dark);
    rect(x - 2, spriteY + 2, 1, 1, '#1b211f');
    rect(x + 1, spriteY + 2, 1, 1, '#1b211f');
    const name = String(character.public_name).slice(0, 10);
    const labelWidth = Math.max(20, name.length * 5 + 8);
    rect(x - labelWidth / 2, spriteY - 15, labelWidth, 9, selected ? '#f4d978' : 'rgba(8,18,16,.82)');
    text(name, x, spriteY - 13, selected ? '#27302d' : p.label, 'center', 5);
    rect(x + labelWidth / 2 - 1, spriteY - 15, 7, 7, selected ? '#27302d' : '#263c34');
    text(moodMark(String(character.mood || '')), x + labelWidth / 2 + 2, spriteY - 14, p.label, 'center', 5);
    hitboxes.push({ id: character.character_id, x: x - 10, y: spriteY - 18, w: 20, h: 38 });
    if (selected) drawActionBubble(character, x, spriteY, p);
  }

  function drawActionBubble(character, x, y, p) {
    const raw = String(character.action || '').trim();
    if (!raw) return;
    const words = raw.split(/\s+/);
    const lines = [];
    let current = '';
    words.forEach(word => {
      const candidate = current ? `${current} ${word}` : word;
      if (candidate.length > 25 && current) {
        lines.push(current);
        current = word;
      } else current = candidate;
    });
    if (current) lines.push(current);
    const visible = lines.slice(0, 2);
    const width = Math.min(136, Math.max(62, ...visible.map(item => item.length * 5 + 10)));
    const bubbleX = clamp(x - width / 2, 3, WIDTH - width - 3);
    const bubbleY = Math.max(35, y - 43);
    rect(bubbleX, bubbleY, width, 19, 'rgba(244,239,207,.95)');
    rect(bubbleX, bubbleY + 19, width, 2, '#4f5d55');
    rect(x - 2, bubbleY + 21, 4, 3, '#f4efcf');
    visible.forEach((item, index) => text(item, bubbleX + 5, bubbleY + 4 + index * 7, '#26332e', 'left', 5));
  }

  function drawLighting(p) {
    rect(0, 0, WIDTH, HEIGHT, p.haze);
    if ((els.cityStage.dataset.period || 'day') === 'night') {
      scenery.slice(0, 7).forEach(([x, y], index) => {
        if (index % 2) return;
        rect(x - 1, y - 27, 2, 18, '#202827');
        rect(x - 4, y - 29, 8, 5, '#f3c96b');
      });
    }
  }

  function frame(now) {
    const p = palette();
    const delta = Math.min(80, now - lastFrame);
    lastFrame = now;
    void delta;
    hitboxes.length = 0;
    drawGround(p);
    drawRoads(p);
    drawCanal(p);
    drawPlaza(p);
    drawScenery(p);
    const locationList = locations.length ? locations : Object.keys(baseLayout).map(id => ({ id, name: readableLocation(id) }));
    [...locationList]
      .sort((a, b) => worldPoint(a.id).y - worldPoint(b.id).y)
      .forEach((location, index) => drawBuilding(location, index, p));
    [...characters]
      .sort((a, b) => (actorState.get(a.character_id)?.targetY || 0) - (actorState.get(b.character_id)?.targetY || 0))
      .forEach(character => {
        const state = actorState.get(character.character_id);
        if (state) drawActor(character, state, p, now);
      });
    drawLighting(p);
    requestAnimationFrame(frame);
  }

  function updateActors(nextCharacters) {
    characters = Array.isArray(nextCharacters) ? nextCharacters : [];
    const grouped = new Map();
    characters.forEach(character => {
      if (!grouped.has(character.location)) grouped.set(character.location, []);
      grouped.get(character.location).push(character);
    });
    const activeIds = new Set();
    const now = performance.now();
    characters.forEach((character, index) => {
      activeIds.add(character.character_id);
      const group = grouped.get(character.location) || [character];
      const groupIndex = group.findIndex(item => item.character_id === character.character_id);
      const point = worldPoint(character.location, index);
      const offset = actorOffset(character.character_id, groupIndex);
      const targetX = clamp(point.x + offset.x, 12, WIDTH - 12);
      const targetY = clamp(point.y + offset.y, 48, HEIGHT - 12);
      let state = actorState.get(character.character_id);
      if (!state) {
        state = {
          x: targetX, y: targetY, fromX: targetX, fromY: targetY,
          targetX, targetY, location: character.location, moveStart: now, moveUntil: now,
        };
        actorState.set(character.character_id, state);
      } else if (state.location !== character.location || state.targetX !== targetX || state.targetY !== targetY) {
        state.fromX = state.x;
        state.fromY = state.y;
        state.targetX = targetX;
        state.targetY = targetY;
        state.location = character.location;
        state.moveStart = now;
        state.moveUntil = now + (reducedMotion.matches ? 1 : 1500);
      }
    });
    [...actorState.keys()].forEach(id => {
      if (!activeIds.has(id)) actorState.delete(id);
    });
  }

  function canvasPoint(event) {
    const bounds = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - bounds.left) * (WIDTH / bounds.width),
      y: (event.clientY - bounds.top) * (HEIGHT / bounds.height),
    };
  }

  canvas.addEventListener('click', event => {
    const point = canvasPoint(event);
    const match = [...hitboxes].reverse().find(box => (
      point.x >= box.x && point.x <= box.x + box.w && point.y >= box.y && point.y <= box.y + box.h
    ));
    if (match) selectCharacter(match.id);
  });

  canvas.addEventListener('mousemove', event => {
    const point = canvasPoint(event);
    const overActor = hitboxes.some(box => (
      point.x >= box.x && point.x <= box.x + box.w && point.y >= box.y && point.y <= box.y + box.h
    ));
    canvas.classList.toggle('is-over-actor', overActor);
  });

  canvas.addEventListener('keydown', event => {
    if (!characters.length || !['ArrowLeft', 'ArrowRight', 'Enter', ' '].includes(event.key)) return;
    event.preventDefault();
    const current = Math.max(0, characters.findIndex(item => item.character_id === selectedId));
    if (event.key === 'ArrowLeft') selectCharacter(characters[(current - 1 + characters.length) % characters.length].character_id);
    else if (event.key === 'ArrowRight') selectCharacter(characters[(current + 1) % characters.length].character_id);
    else selectCharacter(characters[current].character_id);
  });

  buildCity = function buildCanvasCity(nextLocations) {
    locations = Array.isArray(nextLocations) ? nextLocations : [];
    els.cityStage.classList.add('canvas-mode');
    mapReady = true;
  };

  renderActors = function renderCanvasActors(nextCharacters) {
    updateActors(nextCharacters);
  };

  mapReady = false;
  requestAnimationFrame(frame);
  if (latestState) render(latestState);
})();
