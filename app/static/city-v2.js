const detailedLooks = {
  chatgpt:{main:'#72e6b0',dark:'#1c7354',accent:'#d9fff0',skin:'#bf815f',hair:'#1d2429',hair2:'#2c343b',outfit:'jacket',hairStyle:'wave'},
  claude:{main:'#e89058',dark:'#783f27',accent:'#ffe2ca',skin:'#e1aa82',hair:'#733f29',hair2:'#a85d39',outfit:'cardigan',hairStyle:'soft'},
  deepseek:{main:'#64b8ff',dark:'#265c8a',accent:'#d9efff',skin:'#d49b73',hair:'#18384e',hair2:'#27658b',outfit:'utility',hairStyle:'short'},
  gemini:{main:'#ad8cff',dark:'#553b91',accent:'#efe8ff',skin:'#b46f52',hair:'#2b1f4f',hair2:'#6849a8',outfit:'coat',hairStyle:'long'},
  grok:{main:'#e9eef1',dark:'#4d5960',accent:'#fff',skin:'#d5a078',hair:'#171a1d',hair2:'#333a3f',outfit:'hoodie',hairStyle:'messy'},
  meta_ai:{main:'#58cef7',dark:'#1c637c',accent:'#d9f7ff',skin:'#8d5e43',hair:'#111b22',hair2:'#1c3440',outfit:'tech',hairStyle:'curl'},
  manus:{main:'#f1c85f',dark:'#765c1e',accent:'#fff2bc',skin:'#e0a77d',hair:'#4c2d22',hair2:'#8c5235',outfit:'vest',hairStyle:'bun'},
};

Object.assign(baseLayout, {
  praca:{x:50,y:50,kind:'plaza',icon:'CZ'}, cafe:{x:28,y:43,kind:'social',icon:'CAFÉ'},
  biblioteca:{x:70,y:36,kind:'study',icon:'BIB'}, laboratorio:{x:81,y:59,kind:'work',icon:'LAB'},
  prefeitura:{x:51,y:25,kind:'civic',icon:'PREF'}, mercado:{x:18,y:66,kind:'commerce',icon:'MKT'},
  parque:{x:48,y:76,kind:'park',icon:'PARQUE'}, oficina:{x:70,y:79,kind:'work',icon:'OFIC'},
  casa_chatgpt:{x:8,y:23,kind:'home',icon:'GPT'}, casa_claude:{x:23,y:16,kind:'home',icon:'CL'},
  casa_deepseek:{x:39,y:12,kind:'home',icon:'DS'}, casa_gemini:{x:61,y:12,kind:'home',icon:'GM'},
  casa_grok:{x:78,y:16,kind:'home',icon:'GR'}, casa_meta_ai:{x:92,y:26,kind:'home',icon:'META'},
  casa_manus:{x:91,y:77,kind:'home',icon:'MN'},
});

function detailedSceneryMarkup(){
  const trees=[[7,54,1.15],[14,36,.82],[34,27,.86],[64,25,.9],[88,43,1.08],[10,78,.92],[32,79,.72],[57,88,.8],[84,88,1.05],[95,58,.76]];
  const lamps=[[24,57],[39,47],[61,48],[76,67],[40,68]];
  const benches=[[35,55],[56,61],[43,82]];
  return `<div class="canal"><i></i><i></i><i></i></div><div class="plaza-floor"><span class="fountain"><i></i><b></b></span></div><div class="garden-bed garden-a"></div><div class="garden-bed garden-b"></div>${trees.map(([x,y,scale],i)=>`<span class="city-tree tree-${i%3+1}" style="--x:${x}%;--y:${y}%;--scale:${scale}"><i class="tree-crown"></i><i class="tree-crown tree-crown-b"></i><i class="tree-trunk"></i><i class="tree-planter"></i></span>`).join('')}${lamps.map(([x,y])=>`<span class="street-lamp" style="--x:${x}%;--y:${y}%"><i></i><b></b></span>`).join('')}${benches.map(([x,y])=>`<span class="city-bench" style="--x:${x}%;--y:${y}%"><i></i><b></b></span>`).join('')}<div class="city-sign"><b>CIDADE ZERO</b><span>Distrito experimental</span></div>`;
}

function detailedProps(kind){
  const plant='<span class="prop planter"><i></i></span>';
  return ({
    home:`${plant}<span class="prop mailbox"><i></i></span><span class="prop flowerbox"></span>`,
    social:`${plant}<span class="prop cafe-table"><i></i><b></b><em></em></span><span class="prop menu-board"></span>`,
    study:`${plant}<span class="prop book-cart"><i></i><b></b><em></em></span>`,
    work:`${plant}<span class="prop crate crate-a"></span><span class="prop crate crate-b"></span><span class="prop terminal"><i></i></span>`,
    civic:'<span class="prop flag"><i></i><b></b></span><span class="prop civic-step"></span>',
    commerce:`${plant}<span class="prop produce produce-a"></span><span class="prop produce produce-b"></span><span class="prop market-table"></span>`,
    park:'<span class="prop park-tree"><i></i><b></b></span><span class="prop park-bench"><i></i></span>',
    plaza:'<span class="prop kiosk"><i></i><b></b></span><span class="prop info-pillar"><i></i></span>',
  })[kind]||plant;
}

function detailedBuilding(locationId,name,kind,icon,index){
  const layout=layoutFor(locationId,index);
  return `<div class="place place-${escapeHtml(kind)}" data-location="${escapeHtml(locationId)}" style="--x:${layout.x}%;--y:${layout.y}%"><div class="place-shadow"></div><div class="iso-building"><span class="roof roof-left"></span><span class="roof roof-right"></span><span class="roof-trim"></span><span class="wall wall-front"><i class="door"><b></b></i><i class="window window-a"><b></b></i><i class="window window-b"><b></b></i><em class="building-sign">${escapeHtml(icon)}</em></span><span class="wall wall-side"><i class="window side-window"><b></b></i><i class="side-detail"></i></span><span class="chimney"><i></i></span><span class="awning"></span></div><div class="place-props">${detailedProps(kind)}</div><span class="place-label">${escapeHtml(name)}</span></div>`;
}

function buildCity(locations){
  const locationMap=new Map(locations.map(location=>[location.id,location]));
  const locationIds=[...new Set([...Object.keys(baseLayout),...locationMap.keys()])];
  els.cityMap.innerHTML=`<div class="road road-a"><i></i></div><div class="road road-b"><i></i></div><div class="road road-c"><i></i></div>${detailedSceneryMarkup()}${locationIds.map((locationId,index)=>{const location=locationMap.get(locationId);const layout=layoutFor(locationId,index);const name=location?.name||locationId.replace(/^casa_/,'Casa de ').replaceAll('_',' ');const kind=layout.kind||location?.kind||'public';return detailedBuilding(locationId,name,kind,layout.icon||'CZ',index)}).join('')}`;
  mapReady=true;
}

function miniAvatar(character){
  const look=detailedLooks[character.character_id]||detailedLooks.chatgpt;
  return `<span class="mini-avatar" style="--actor-main:${look.main};--actor-dark:${look.dark};--skin:${look.skin};--hair:${look.hair}"><i class="mini-hair"></i><i class="mini-head"></i><i class="mini-body"></i></span>`;
}

function characterCard(character){
  return `<button class="character-card ${selectedId===character.character_id?'is-selected':''}" type="button" data-character="${escapeHtml(character.character_id)}"><header><span class="card-identity">${miniAvatar(character)}<span><h3>${escapeHtml(character.public_name)}</h3><small>${escapeHtml(character.archetype||character.city_role||'Morador experimental')}</small></span></span><span class="status-chip">${escapeHtml(character.mood)}</span></header><p class="current-action">${escapeHtml(character.action)}</p><div class="meta-row"><span>${escapeHtml(readableLocation(character.location))}</span><span>${escapeHtml(character.central_value||'')}</span></div><div class="needs">${needBars(character.needs)}</div></button>`;
}

function actorMarkup(character){
  const look=detailedLooks[character.character_id]||detailedLooks.chatgpt;
  return `<span class="actor-action">${escapeHtml(character.action)}</span><span class="actor-shadow"></span><span class="avatar avatar-${escapeHtml(character.character_id)} hair-${escapeHtml(look.hairStyle)} outfit-${escapeHtml(look.outfit)}" style="--actor-main:${look.main};--actor-dark:${look.dark};--actor-accent:${look.accent};--skin:${look.skin};--hair:${look.hair};--hair-2:${look.hair2}"><i class="avatar-hair hair-back"></i><i class="avatar-neck"></i><i class="avatar-head"><b class="ear ear-a"></b><b class="ear ear-b"></b><em class="eye eye-a"></em><em class="eye eye-b"></em><em class="mouth"></em></i><i class="avatar-hair hair-front"></i><i class="avatar-body"><b class="outfit-detail"></b><em class="outfit-badge"></em></i><i class="avatar-arm arm-a"><b class="hand"></b></i><i class="avatar-arm arm-b"><b class="hand"></b></i><i class="avatar-leg leg-a"><b class="shoe"></b></i><i class="avatar-leg leg-b"><b class="shoe"></b></i></span><strong>${escapeHtml(character.public_name)}</strong><small>${escapeHtml(character.mood)}</small>`;
}

function renderSelection(){
  if(!latestState)return;
  const character=latestState.characters.find(item=>item.character_id===selectedId);
  if(!character){selectedId=null;els.observer.innerHTML='<h2>Escolha um morador</h2><p class="observer-empty">Clique em alguém no mapa para ver sua ação, localização, humor e necessidades.</p>';return}
  const recentEvent=latestState.events.find(event=>event.character_id===character.character_id);
  els.observer.innerHTML=`<div class="observer-title"><div><span class="observer-kicker">ACOMPANHANDO</span><h2>${escapeHtml(character.public_name)}</h2></div><span class="observer-mood">${escapeHtml(character.mood)}</span></div><div class="observer-portrait">${miniAvatar(character)}</div><p class="observer-role">${escapeHtml(character.archetype||character.city_role||'Morador experimental')}</p><div class="observer-action"><span>AGORA</span><strong>${escapeHtml(character.action)}</strong><small>${escapeHtml(readableLocation(character.location))}</small></div><div class="observer-needs">${needBars(character.needs,true)}</div><div class="observer-event"><span>ÚLTIMO REGISTRO</span><p>${escapeHtml(recentEvent?.summary||'Nenhum acontecimento recente registrado.')}</p></div>`;
}

mapReady=false;
if(latestState)render(latestState);
