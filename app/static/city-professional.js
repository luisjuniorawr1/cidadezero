(() => {
  const canvas = document.querySelector('#city-canvas');
  const tooltip = document.querySelector('#city-tooltip');
  const zoomInButton = document.querySelector('#map-zoom-in');
  const zoomOutButton = document.querySelector('#map-zoom-out');
  const resetButton = document.querySelector('#clear-follow');
  if (!canvas || !canvas.getContext || !tooltip) return;

  const ctx = canvas.getContext('2d', { alpha: false });
  const WIDTH = 960;
  const HEIGHT = 540;
  const CENTER = { x: WIDTH / 2, y: HEIGHT / 2 };
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  ctx.imageSmoothingEnabled = false;
  els.cityStage.classList.add('professional-map');

  const paletteByPeriod = {
    dawn: {
      sky:'#8b7a77', horizon:'#c49b83', ground:'#3f6652', groundAlt:'#4b735d',
      road:'#3b4845', roadEdge:'#26322f', marking:'#c9af72', water:'#356f78',
      waterLight:'#73a9a8', shadow:'#182620', lamp:'#ffe09a', haze:'rgba(244,174,137,.10)'
    },
    day: {
      sky:'#72a096', horizon:'#a8c5ad', ground:'#4d795f', groundAlt:'#5a876b',
      road:'#3d4c48', roadEdge:'#293632', marking:'#d4c17c', water:'#397f82',
      waterLight:'#88c7bd', shadow:'#20332b', lamp:'#c7d7c8', haze:'rgba(255,255,235,.03)'
    },
    dusk: {
      sky:'#705f71', horizon:'#bb7d72', ground:'#3c604d', groundAlt:'#486c56',
      road:'#394540', roadEdge:'#222e2a', marking:'#c6a66b', water:'#315f70',
      waterLight:'#75939b', shadow:'#17251f', lamp:'#ffd481', haze:'rgba(225,111,86,.11)'
    },
    night: {
      sky:'#182c37', horizon:'#294453', ground:'#294839', groundAlt:'#335440',
      road:'#263431', roadEdge:'#151f1c', marking:'#8d855b', water:'#244c5b',
      waterLight:'#567f84', shadow:'#09130f', lamp:'#ffd36d', haze:'rgba(19,38,53,.18)'
    }
  };

  const residentLooks = {
    chatgpt:{main:'#70e2ad',dark:'#245c49',skin:'#bd825f',hair:'#20282c',accent:'#d7fff0'},
    claude:{main:'#df8956',dark:'#784027',skin:'#d9a17b',hair:'#73432c',accent:'#ffe0c6'},
    deepseek:{main:'#5aaeff',dark:'#285b87',skin:'#ce956d',hair:'#19394e',accent:'#d9edff'},
    gemini:{main:'#a987f2',dark:'#553a8c',skin:'#af6d52',hair:'#2d214d',accent:'#efe7ff'},
    grok:{main:'#e7ecee',dark:'#4c575d',skin:'#d19b73',hair:'#161a1d',accent:'#ffffff'},
    meta_ai:{main:'#55c6ed',dark:'#1d6178',skin:'#8c5d42',hair:'#121c22',accent:'#d8f6ff'},
    manus:{main:'#e8bf58',dark:'#70571d',skin:'#d9a17a',hair:'#4a2d22',accent:'#fff0b5'}
  };

  const kindColors = {
    home:{wall:'#c8baa0',side:'#8f7d69',roof:'#a45b4c',trim:'#f0d7aa'},
    social:{wall:'#d0ad7e',side:'#8a654d',roof:'#b35643',trim:'#f7d998'},
    study:{wall:'#bbbca8',side:'#747d72',roof:'#6d5b9b',trim:'#d9d8c3'},
    work:{wall:'#aeb9b5',side:'#687a77',roof:'#4d7786',trim:'#d5e0dc'},
    civic:{wall:'#d1c6aa',side:'#8b846d',roof:'#567965',trim:'#efe3c1'},
    commerce:{wall:'#d2b17d',side:'#8c6746',roof:'#ba7443',trim:'#f0cf91'},
    park:{wall:'#80946d',side:'#4e6f4e',roof:'#3f7951',trim:'#b8c99f'},
    health:{wall:'#cad2c5',side:'#7b8a81',roof:'#5c8d84',trim:'#eef3eb'},
    service:{wall:'#bbb6a4',side:'#777264',roof:'#7b604e',trim:'#e2dac2'},
    public:{wall:'#c0b9a4',side:'#77766a',roof:'#61776c',trim:'#e0d9c5'}
  };

  const layout = {
    casa_chatgpt:{x:105,y:105,kind:'home'},
    casa_claude:{x:245,y:84,kind:'home'},
    casa_deepseek:{x:390,y:72,kind:'home'},
    casa_gemini:{x:565,y:72,kind:'home'},
    casa_grok:{x:720,y:84,kind:'home'},
    casa_meta_ai:{x:855,y:122,kind:'home'},
    casa_manus:{x:845,y:446,kind:'home'},
    prefeitura:{x:480,y:152,kind:'civic',size:1.2},
    praca:{x:480,y:282,kind:'public'},
    cafe:{x:205,y:245,kind:'social'},
    biblioteca:{x:742,y:235,kind:'study'},
    mercado:{x:135,y:385,kind:'commerce'},
    laboratorio:{x:800,y:335,kind:'work'},
    oficina:{x:695,y:445,kind:'work'},
    parque:{x:420,y:447,kind:'park'},
    clinica:{x:595,y:373,kind:'health'},
    lavanderia:{x:555,y:460,kind:'service'},
    centro_comunitario:{x:300,y:360,kind:'civic'}
  };

  const state = {
    locations:[],
    characters:[],
    actors:new Map(),
    hitboxes:[],
    hovered:null,
    selectedLocationId:null,
    camera:{scale:1,targetScale:1,x:CENTER.x,y:CENTER.y,targetX:CENTER.x,targetY:CENTER.y},
    lastFrame:performance.now()
  };

  function currentPalette(){
    return paletteByPeriod[els.cityStage.dataset.period] || paletteByPeriod.day;
  }

  function locationPoint(id,index=0){
    if (layout[id]) return layout[id];
    const column=index%5;
    const row=Math.floor(index/5);
    return {x:120+column*165,y:160+row*120,kind:'public'};
  }

  function cameraPoint(point){
    const camera=state.camera;
    return {
      x:(point.x-camera.x)*camera.scale+CENTER.x,
      y:(point.y-camera.y)*camera.scale+CENTER.y
    };
  }

  function rounded(value,step=2){return Math.round(value/step)*step}

  function rect(x,y,w,h,color){
    ctx.fillStyle=color;
    ctx.fillRect(rounded(x),rounded(y),Math.max(2,rounded(w)),Math.max(2,rounded(h)));
  }

  function polygon(points,color,stroke=null,width=2){
    ctx.beginPath();
    ctx.moveTo(rounded(points[0][0]),rounded(points[0][1]));
    points.slice(1).forEach(([x,y])=>ctx.lineTo(rounded(x),rounded(y)));
    ctx.closePath();
    ctx.fillStyle=color;
    ctx.fill();
    if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width;ctx.stroke()}
  }

  function strokePath(points,color,width=2,dash=[]){
    ctx.beginPath();
    ctx.moveTo(rounded(points[0][0]),rounded(points[0][1]));
    points.slice(1).forEach(([x,y])=>ctx.lineTo(rounded(x),rounded(y)));
    ctx.strokeStyle=color;
    ctx.lineWidth=width;
    ctx.lineJoin='miter';
    ctx.lineCap='square';
    ctx.setLineDash(dash);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  function drawSky(p){
    rect(0,0,WIDTH,HEIGHT,p.sky);
    for(let y=0;y<110;y+=6){
      const opacity=Math.max(0,0.16-y/900);
      rect(0,72+y,WIDTH,6,`rgba(255,210,170,${opacity})`);
    }
    rect(0,108,WIDTH,HEIGHT-108,p.ground);
    for(let y=112;y<HEIGHT;y+=16){
      for(let x=(y/16)%2?0:8;x<WIDTH;x+=16){
        if((x+y)%48===0) rect(x,y,3,3,p.groundAlt);
      }
    }
    rect(0,106,WIDTH,4,p.horizon);
  }

  function drawRoadSegment(a,b,p,major=false){
    const start=cameraPoint(a);const end=cameraPoint(b);
    const width=(major?28:20)*state.camera.scale;
    strokePath([[start.x,start.y],[end.x,end.y]],p.roadEdge,width+8);
    strokePath([[start.x,start.y],[end.x,end.y]],p.road,width);
    if(major) strokePath([[start.x,start.y],[end.x,end.y]],p.marking,2*state.camera.scale,[12*state.camera.scale,14*state.camera.scale]);
  }

  function drawRoads(p){
    const routes=[
      ['casa_chatgpt','casa_meta_ai',true],
      ['casa_claude','casa_grok',false],
      ['prefeitura','praca',true],
      ['cafe','biblioteca',true],
      ['mercado','laboratorio',true],
      ['centro_comunitario','clinica',false],
      ['parque','oficina',false],
      ['lavanderia','casa_manus',false],
      ['praca','parque',true]
    ];
    routes.forEach(([from,to,major])=>{
      const a=locationPoint(from);const b=locationPoint(to);
      const midX=(a.x+b.x)/2;
      drawRoadSegment(a,{x:midX,y:a.y},p,major);
      drawRoadSegment({x:midX,y:a.y},{x:midX,y:b.y},p,major);
      drawRoadSegment({x:midX,y:b.y},b,p,major);
    });
  }

  function drawWater(p){
    const points=[{x:670,y:520},{x:960,y:435}].map(cameraPoint);
    strokePath(points,'#17363d',52*state.camera.scale);
    strokePath(points,p.water,42*state.camera.scale);
    strokePath(points,p.waterLight,3*state.camera.scale);
    for(let i=0;i<7;i+=1){
      const x=720+i*42;const y=505-i*12;
      const point=cameraPoint({x,y});
      rect(point.x,point.y,20*state.camera.scale,2*state.camera.scale,'rgba(220,255,246,.35)');
    }
  }

  function drawPlaza(p){
    const center=cameraPoint(locationPoint('praca'));
    const s=state.camera.scale;
    polygon([[center.x,center.y-58*s],[center.x+92*s,center.y],[center.x,center.y+58*s],[center.x-92*s,center.y]],'#c3b997','#77715f',3*s);
    for(let offset=-52;offset<=52;offset+=20){
      strokePath([[center.x+offset*s,center.y-30*s],[center.x+offset*s,center.y+30*s]],'rgba(91,85,70,.22)',2*s);
    }
    polygon([[center.x,center.y-22*s],[center.x+32*s,center.y],[center.x,center.y+20*s],[center.x-32*s,center.y]],'#538f95','#445f5c',3*s);
    rect(center.x-7*s,center.y-42*s,14*s,30*s,'#a8d7d5');
    rect(center.x-11*s,center.y-48*s,22*s,8*s,'#d8f0e7');
  }

  function drawTree(worldX,worldY,scale,p){
    const point=cameraPoint({x:worldX,y:worldY});
    const s=scale*state.camera.scale;
    rect(point.x-4*s,point.y-20*s,8*s,22*s,'#6c4b31');
    polygon([[point.x,point.y-54*s],[point.x+23*s,point.y-28*s],[point.x+14*s,point.y-11*s],[point.x-14*s,point.y-11*s],[point.x-23*s,point.y-28*s]],'#2b593c','#1d382a',2*s);
    polygon([[point.x+7*s,point.y-47*s],[point.x+29*s,point.y-25*s],[point.x+17*s,point.y-9*s],[point.x-1*s,point.y-13*s]],'#3c744b',null);
    rect(point.x-17*s,point.y+2*s,34*s,5*s,p.shadow);
  }

  function drawStreetFurniture(p){
    const trees=[[72,205,1],[92,330,.9],[252,180,.8],[340,470,.95],[523,238,.75],[640,176,.85],[900,250,1],[890,365,.9],[755,495,.8],[250,455,.8]];
    trees.forEach(args=>drawTree(...args,p));
    [[365,300],[565,305],[390,400]].forEach(([x,y])=>{
      const point=cameraPoint({x,y});const s=state.camera.scale;
      rect(point.x-18*s,point.y-6*s,36*s,7*s,'#825738');
      rect(point.x-14*s,point.y+1*s,5*s,9*s,'#2d3934');
      rect(point.x+9*s,point.y+1*s,5*s,9*s,'#2d3934');
    });
    [[165,315],[520,190],[675,305],[460,410]].forEach(([x,y])=>{
      const point=cameraPoint({x,y});const s=state.camera.scale;
      rect(point.x-3*s,point.y-30*s,6*s,32*s,'#273431');
      rect(point.x-9*s,point.y-41*s,18*s,13*s,'#323c38');
      rect(point.x-6*s,point.y-38*s,12*s,8*s,p.lamp);
    });
  }

  function drawIcon(kind,x,y,s,color){
    ctx.fillStyle=color;
    if(kind==='social'){
      rect(x-8*s,y-5*s,13*s,9*s,color);rect(x+5*s,y-3*s,5*s,5*s,color);rect(x-5*s,y+4*s,8*s,3*s,color);
    }else if(kind==='study'){
      rect(x-10*s,y-7*s,9*s,15*s,color);rect(x+1*s,y-7*s,9*s,15*s,color);rect(x-1*s,y-8*s,2*s,17*s,color);
    }else if(kind==='work'){
      rect(x-9*s,y-8*s,18*s,16*s,color);rect(x-5*s,y-4*s,10*s,8*s,'#17221f');rect(x-2*s,y+8*s,4*s,5*s,color);
    }else if(kind==='health'){
      rect(x-3*s,y-10*s,6*s,20*s,color);rect(x-10*s,y-3*s,20*s,6*s,color);
    }else if(kind==='commerce'){
      rect(x-10*s,y-6*s,18*s,13*s,color);rect(x-7*s,y+7*s,4*s,4*s,color);rect(x+4*s,y+7*s,4*s,4*s,color);rect(x+8*s,y-10*s,3*s,7*s,color);
    }else if(kind==='civic'){
      rect(x-10*s,y-8*s,20*s,4*s,color);for(let i=-7;i<=7;i+=7)rect(x+i*s,y-4*s,4*s,12*s,color);rect(x-11*s,y+8*s,22*s,3*s,color);
    }else if(kind==='service'){
      rect(x-9*s,y-9*s,18*s,18*s,color);rect(x-5*s,y-5*s,10*s,10*s,'#17221f');
    }
  }

  function homeRoofColor(locationId){
    const id=locationId.replace('casa_','');
    return residentLooks[id]?.main || '#a45b4c';
  }

  function drawBuilding(location,index,p){
    if(location.id==='praca'||location.id==='parque') return;
    const source=locationPoint(location.id,index);
    const center=cameraPoint(source);
    const kind=source.kind||location.kind||'public';
    const colors={...(kindColors[kind]||kindColors.public)};
    if(kind==='home') colors.roof=homeRoofColor(location.id);
    const baseScale=(source.size||1)*state.camera.scale;
    const w=(kind==='civic'?104:82)*baseScale;
    const h=(kind==='civic'?70:58)*baseScale;
    const depth=30*baseScale;

    polygon([[center.x-w*.58,center.y+10*baseScale],[center.x,center.y+depth],[center.x+w*.62,center.y+7*baseScale],[center.x,center.y-depth*.55]],p.shadow,null);
    polygon([[center.x-w*.5,center.y-h*.15],[center.x,center.y+h*.12],[center.x,center.y+h],[center.x-w*.5,center.y+h*.68]],colors.wall,'#303a35',2*baseScale);
    polygon([[center.x,center.y+h*.12],[center.x+w*.5,center.y-h*.15],[center.x+w*.5,center.y+h*.68],[center.x,center.y+h]],colors.side,'#303a35',2*baseScale);
    polygon([[center.x-w*.58,center.y-h*.18],[center.x,center.y-h*.66],[center.x+w*.58,center.y-h*.18],[center.x,center.y+h*.12]],colors.roof,'#33332e',3*baseScale);
    polygon([[center.x-w*.46,center.y-h*.18],[center.x,center.y-h*.54],[center.x,center.y-h*.43],[center.x-w*.42,center.y-h*.1]],colors.trim,null);

    const windowColor=(els.cityStage.dataset.period==='night'||els.cityStage.dataset.period==='dusk')?p.lamp:'#84bbb4';
    rect(center.x-w*.36,center.y+h*.3,16*baseScale,17*baseScale,windowColor);
    rect(center.x+w*.16,center.y+h*.2,16*baseScale,17*baseScale,windowColor);
    rect(center.x-5*baseScale,center.y+h*.45,17*baseScale,31*baseScale,'#6e4b34');
    rect(center.x+6*baseScale,center.y+h*.62,3*baseScale,3*baseScale,'#e7c96d');

    if(kind!=='home') drawIcon(kind,center.x,center.y-h*.18,baseScale*.7,'#f4ead0');
    state.hitboxes.push({type:'location',id:location.id,name:location.name||readableLocation(location.id),kind,screenX:center.x,screenY:center.y,width:w,height:h*1.5});
  }

  function actorTarget(character,index,groupIndex){
    const point=locationPoint(character.location,index);
    const offsets=[[0,34],[-25,34],[25,34],[-42,48],[42,48],[0,55],[0,12]];
    const offset=offsets[groupIndex]||[((index%3)-1)*22,34+Math.floor(index/3)*15];
    return {x:point.x+offset[0],y:point.y+offset[1]};
  }

  function ensureActor(character,index,groupIndex){
    const target=actorTarget(character,index,groupIndex);
    let actor=state.actors.get(character.character_id);
    if(!actor){actor={x:target.x,y:target.y,targetX:target.x,targetY:target.y,facing:1,character};state.actors.set(character.character_id,actor)}
    actor.character=character;
    if(Math.abs(actor.targetX-target.x)>1) actor.facing=target.x<actor.targetX?-1:1;
    actor.targetX=target.x;actor.targetY=target.y;
    return actor;
  }

  function drawActor(actor,p,time){
    const screen=cameraPoint(actor);
    const look=residentLooks[actor.character.character_id]||residentLooks.chatgpt;
    const s=state.camera.scale;
    const moving=Math.abs(actor.x-actor.targetX)>1||Math.abs(actor.y-actor.targetY)>1;
    const bob=moving&&!reducedMotion.matches?Math.round(Math.sin(time/90)*2)*s:0;
    const selected=selectedId===actor.character.character_id;

    if(selected){
      ctx.strokeStyle='#f3d677';ctx.lineWidth=3*s;ctx.beginPath();ctx.ellipse(screen.x,screen.y+14*s,24*s,10*s,0,0,Math.PI*2);ctx.stroke();
    }
    rect(screen.x-15*s,screen.y+13*s,30*s,7*s,p.shadow);
    rect(screen.x-7*s,screen.y-19*s+bob,14*s,14*s,look.skin);
    rect(screen.x-9*s,screen.y-24*s+bob,18*s,8*s,look.hair);
    rect(screen.x-10*s,screen.y-6*s+bob,20*s,22*s,look.main);
    rect(screen.x-13*s,screen.y-3*s+bob,5*s,15*s,look.skin);
    rect(screen.x+8*s,screen.y-3*s+bob,5*s,15*s,look.skin);
    const step=moving&&!reducedMotion.matches?Math.round(Math.sin(time/85)*3)*s:0;
    rect(screen.x-8*s,screen.y+15*s+bob,6*s,15*s+step,look.dark);
    rect(screen.x+2*s,screen.y+15*s+bob,6*s,15*s-step,look.dark);
    rect(screen.x-5*s,screen.y-13*s+bob,3*s,3*s,'#17211e');
    rect(screen.x+3*s,screen.y-13*s+bob,3*s,3*s,'#17211e');

    state.hitboxes.push({type:'character',id:actor.character.character_id,name:actor.character.public_name,subtitle:actor.character.action,screenX:screen.x,screenY:screen.y,width:42*s,height:66*s});
  }

  function drawPark(p){
    const center=cameraPoint(locationPoint('parque'));const s=state.camera.scale;
    polygon([[center.x,center.y-50*s],[center.x+82*s,center.y-5*s],[center.x+45*s,center.y+55*s],[center.x-70*s,center.y+40*s]],'#477652','#294f38',3*s);
    drawTree(385,445,.8,p);drawTree(455,430,.9,p);
    state.hitboxes.push({type:'location',id:'parque',name:'Parque e beira d’água',kind:'park',screenX:center.x,screenY:center.y,width:150*s,height:110*s});
  }

  function updateMotion(delta){
    const speed=reducedMotion.matches?1:Math.min(1,delta/180);
    state.actors.forEach(actor=>{
      actor.x+=(actor.targetX-actor.x)*speed;
      actor.y+=(actor.targetY-actor.y)*speed;
    });
    const camera=state.camera;
    const cameraSpeed=reducedMotion.matches?1:Math.min(1,delta/240);
    camera.scale+=(camera.targetScale-camera.scale)*cameraSpeed;
    camera.x+=(camera.targetX-camera.x)*cameraSpeed;
    camera.y+=(camera.targetY-camera.y)*cameraSpeed;
  }

  function draw(time){
    const delta=Math.min(80,time-state.lastFrame||16);state.lastFrame=time;
    updateMotion(delta);
    state.hitboxes=[];
    const p=currentPalette();
    drawSky(p);drawRoads(p);drawWater(p);drawPlaza(p);drawStreetFurniture(p);drawPark(p);

    const locations=[...state.locations].sort((a,b)=>locationPoint(a.id).y-locationPoint(b.id).y);
    locations.forEach((location,index)=>drawBuilding(location,index,p));
    [...state.actors.values()].sort((a,b)=>a.y-b.y).forEach(actor=>drawActor(actor,p,time));

    ctx.fillStyle=p.haze;ctx.fillRect(0,0,WIDTH,HEIGHT);
    requestAnimationFrame(draw);
  }

  function buildCityProfessional(locations){
    state.locations=Array.isArray(locations)?locations:[];
    mapReady=true;
  }

  function renderActorsProfessional(characters){
    state.characters=Array.isArray(characters)?characters:[];
    const grouped=new Map();
    state.characters.forEach(character=>{
      if(!grouped.has(character.location)) grouped.set(character.location,[]);
      grouped.get(character.location).push(character);
    });
    const active=new Set();
    state.characters.forEach((character,index)=>{
      active.add(character.character_id);
      const group=grouped.get(character.location)||[character];
      ensureActor(character,index,group.findIndex(item=>item.character_id===character.character_id));
    });
    [...state.actors.keys()].forEach(id=>{if(!active.has(id))state.actors.delete(id)});
  }

  function labelsForNeeds(needs){
    const definitions=[
      ['energy','Energia',Number(needs.energy)||0],
      ['hunger','Fome',Number(needs.hunger)||0],
      ['stress','Estresse',Number(needs.stress)||0],
      ['social','Social',Number(needs.social)||0]
    ];
    return definitions.map(([key,label,value])=>{
      const display=Math.max(0,Math.min(100,Math.round(value)));
      const goodValue=key==='energy'?display:100-display;
      return `<article class="professional-need"><header><span>${label}</span><b>${display}</b></header><div class="meter"><i style="width:${goodValue}%"></i></div></article>`;
    }).join('');
  }

  function cityOverview(){
    const society=latestState?.society||{};
    return `<div class="city-overview-card"><span class="panel-label">VISÃO GERAL</span><h2>Cidade Zero</h2><p class="observer-role">Selecione um morador ou prédio no mapa. A arte mostra presença e deslocamento; ações e contexto ficam neste painel.</p></div><div class="observer-needs"><article class="professional-need"><header><span>Moradores</span><b>${state.characters.length}</b></header><div class="meter"><i style="width:100%"></i></div></article><article class="professional-need"><header><span>Estresse médio</span><b>${Math.round(Number(society.average_stress)||0)}</b></header><div class="meter"><i style="width:${Math.max(0,100-(Number(society.average_stress)||0))}%"></i></div></article><article class="professional-need"><header><span>Problemas ativos</span><b>${Number(society.active_problems)||0}</b></header><div class="meter"><i style="width:${Math.max(10,100-(Number(society.active_problems)||0)*12)}%"></i></div></article><article class="professional-need"><header><span>Pertencimento</span><b>${Math.round(Number(society.average_belonging)||0)}</b></header><div class="meter"><i style="width:${Math.max(0,Number(society.average_belonging)||0)}%"></i></div></article></div>`;
  }

  function locationObserver(location){
    const people=state.characters.filter(character=>character.location===location.id);
    const list=people.length?people.map(person=>`<button type="button" data-person="${escapeHtml(person.character_id)}">${escapeHtml(person.public_name)}</button>`).join(''):'<span class="observer-role">Nenhum morador está aqui agora.</span>';
    return `<div class="observer-title"><div><span class="observer-kicker">LOCAL</span><h2>${escapeHtml(location.name||readableLocation(location.id))}</h2></div><span class="observer-mood">${people.length} presente${people.length===1?'':'s'}</span></div><p class="observer-role">${escapeHtml((location.kind||'espaço público').replaceAll('_',' '))}</p><div class="location-overview"><span class="panel-label">QUEM ESTÁ AQUI</span><div class="location-people">${list}</div></div><div class="observer-event"><span>ATIVIDADE LOCAL</span><p>${people.length?people.map(person=>`${escapeHtml(person.public_name)}: ${escapeHtml(person.action)}`).join('<br>'):'O espaço está tranquilo neste momento.'}</p></div><div class="panel-actions"><button type="button" data-focus-location="${escapeHtml(location.id)}">Focar no mapa</button></div>`;
  }

  function characterObserver(character){
    const recentEvent=latestState?.events?.find(event=>event.character_id===character.character_id);
    const portrait=typeof miniAvatar==='function'?miniAvatar(character):'';
    return `<div class="observer-title"><div><span class="observer-kicker">ACOMPANHANDO</span><h2>${escapeHtml(character.public_name)}</h2></div><span class="observer-mood">${escapeHtml(character.mood)}</span></div><div class="observer-portrait">${portrait}</div><p class="observer-role">${escapeHtml(character.archetype||character.city_role||'Morador da Cidade Zero')}</p><div class="observer-action"><span>AGORA</span><strong>${escapeHtml(character.action)}</strong><small>${escapeHtml(readableLocation(character.location))}</small></div><div class="observer-needs">${labelsForNeeds(character.needs||{})}</div><div class="observer-event"><span>ÚLTIMO REGISTRO</span><p>${escapeHtml(recentEvent?.summary||'Nenhum acontecimento recente registrado.')}</p></div><div class="panel-actions"><button type="button" data-focus-character="${escapeHtml(character.character_id)}">Focar</button><button type="button" data-open-location="${escapeHtml(character.location)}">Ver local</button></div>`;
  }

  function bindObserverActions(){
    els.observer.querySelectorAll('[data-person]').forEach(button=>button.addEventListener('click',()=>selectCharacter(button.dataset.person)));
    els.observer.querySelectorAll('[data-focus-character]').forEach(button=>button.addEventListener('click',()=>focusCharacter(button.dataset.focusCharacter)));
    els.observer.querySelectorAll('[data-open-location]').forEach(button=>button.addEventListener('click',()=>selectLocation(button.dataset.openLocation)));
    els.observer.querySelectorAll('[data-focus-location]').forEach(button=>button.addEventListener('click',()=>focusLocation(button.dataset.focusLocation)));
  }

  function renderObserver(){
    if(!latestState)return;
    if(state.selectedLocationId){
      const location=state.locations.find(item=>item.id===state.selectedLocationId)||{id:state.selectedLocationId,name:readableLocation(state.selectedLocationId)};
      els.observer.innerHTML=locationObserver(location);bindObserverActions();return;
    }
    const character=latestState.characters.find(item=>item.character_id===selectedId);
    els.observer.innerHTML=character?characterObserver(character):cityOverview();
    bindObserverActions();
  }

  function focusPoint(point,scale=1.45){
    state.camera.targetX=point.x;state.camera.targetY=point.y;state.camera.targetScale=scale;
  }

  function focusCharacter(id){
    const actor=state.actors.get(id);if(actor)focusPoint(actor,1.55);
  }

  function focusLocation(id){focusPoint(locationPoint(id),1.42)}

  function resetCamera(){
    state.camera.targetX=CENTER.x;state.camera.targetY=CENTER.y;state.camera.targetScale=1;
  }

  function selectLocation(id){
    state.selectedLocationId=id;selectedId=null;overviewMode=true;renderObserver();focusLocation(id);
  }

  function mousePosition(event){
    const bounds=canvas.getBoundingClientRect();
    return {x:(event.clientX-bounds.left)*(WIDTH/bounds.width),y:(event.clientY-bounds.top)*(HEIGHT/bounds.height)};
  }

  function hitAt(point){
    return [...state.hitboxes].reverse().find(item=>Math.abs(point.x-item.screenX)<=item.width/2&&Math.abs(point.y-item.screenY)<=item.height/2)||null;
  }

  function showTooltip(hit){
    if(!hit){tooltip.hidden=true;canvas.classList.remove('is-interactive');return}
    canvas.classList.add('is-interactive');tooltip.hidden=false;
    tooltip.innerHTML=`<strong>${escapeHtml(hit.name)}</strong><span>${escapeHtml(hit.subtitle||((hit.type==='character')?'Morador da Cidade Zero':'Clique para observar este local'))}</span>`;
    tooltip.style.left=`${(hit.screenX/WIDTH)*100}%`;tooltip.style.top=`${(hit.screenY/HEIGHT)*100}%`;
  }

  canvas.addEventListener('pointermove',event=>{state.hovered=hitAt(mousePosition(event));showTooltip(state.hovered)});
  canvas.addEventListener('pointerleave',()=>{state.hovered=null;showTooltip(null)});
  canvas.addEventListener('click',event=>{
    const hit=hitAt(mousePosition(event));if(!hit)return;
    if(hit.type==='character'){state.selectedLocationId=null;selectCharacter(hit.id);focusCharacter(hit.id)}else selectLocation(hit.id);
  });
  canvas.addEventListener('keydown',event=>{
    if(!['ArrowLeft','ArrowRight','Enter',' '].includes(event.key)||!state.characters.length)return;
    event.preventDefault();
    const current=Math.max(0,state.characters.findIndex(item=>item.character_id===selectedId));
    if(event.key==='ArrowLeft'||event.key==='ArrowRight'){
      const direction=event.key==='ArrowLeft'?-1:1;
      const next=(current+direction+state.characters.length)%state.characters.length;
      state.selectedLocationId=null;selectCharacter(state.characters[next].character_id);focusCharacter(state.characters[next].character_id);
    }else if(selectedId)focusCharacter(selectedId);
  });
  canvas.addEventListener('wheel',event=>{
    event.preventDefault();
    state.camera.targetScale=Math.max(1,Math.min(1.8,state.camera.targetScale+(event.deltaY<0?.15:-.15)));
  },{passive:false});

  zoomInButton?.addEventListener('click',()=>{state.camera.targetScale=Math.min(1.8,state.camera.targetScale+.2)});
  zoomOutButton?.addEventListener('click',()=>{state.camera.targetScale=Math.max(1,state.camera.targetScale-.2)});
  resetButton?.addEventListener('click',()=>{state.selectedLocationId=null;resetCamera();setTimeout(renderObserver,0)});

  const originalSelectCharacter=selectCharacter;
  selectCharacter=function(characterId){
    state.selectedLocationId=null;
    originalSelectCharacter(characterId);
  };
  buildCity=buildCityProfessional;
  renderActors=renderActorsProfessional;
  renderSelection=renderObserver;

  mapReady=false;
  if(latestState)render(latestState);
  requestAnimationFrame(draw);
})();
