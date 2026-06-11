const zone = document.getElementById('zone');
const eventsEl = document.getElementById('events');
const scoreEl = document.getElementById('score');
const fpEl = document.getElementById('fp');
const logs = [];
const eventNames = [
  'pointerover','pointerenter','pointerdown','pointermove','pointerup','pointercancel','pointerout','pointerleave',
  'mouseover','mouseenter','mousedown','mousemove','mouseup','mouseout','mouseleave','click',
  'touchstart','touchmove','touchend','touchcancel'
];
function pick(e){
  return {
    type:e.type, t:Math.round(performance.now()*1000)/1000,
    x:e.clientX??null, y:e.clientY??null,
    pointerType:e.pointerType??null, isPrimary:e.isPrimary??null,
    buttons:e.buttons??null, button:e.button??null,
    pressure:e.pressure??null, width:e.width??null, height:e.height??null,
    isTrusted:e.isTrusted,
    touches:e.touches?e.touches.length:null
  };
}
function update(){
  eventsEl.textContent = JSON.stringify(logs.slice(-80), null, 2);
  scoreEl.textContent = JSON.stringify(scoreEvents(logs), null, 2);
}
function scoreEvents(items){
  const types = new Set(items.map(x=>x.type));
  const pointer = items.filter(x=>x.type.startsWith('pointer'));
  const mouse = items.filter(x=>x.type.startsWith('mouse') || x.type === 'click');
  const touch = items.filter(x=>x.type.startsWith('touch'));
  const moves = items.filter(x=>x.type.includes('move'));
  const downs = items.filter(x=>x.type.includes('down') || x.type === 'touchstart');
  const ups = items.filter(x=>x.type.includes('up') || x.type === 'touchend');
  const untrusted = items.filter(x=>x.isTrusted === false).length;
  let score = 100;
  if (items.length < 8) score -= 25;
  if (moves.length < 3) score -= 20;
  if (downs.length < 1 || ups.length < 1) score -= 20;
  if (pointer.length === 0 && mouse.length === 0 && touch.length === 0) score -= 20;
  if (untrusted > 0) score -= 30;
  if (types.has('pointerdown') && !types.has('mousedown') && touch.length === 0) score -= 8;
  if (types.has('mousedown') && !types.has('pointerdown')) score -= 8;
  const dts = [];
  for (let i=1;i<items.length;i++) dts.push(items[i].t-items[i-1].t);
  const avgDt = dts.length ? dts.reduce((a,b)=>a+b,0)/dts.length : 0;
  return {
    score: Math.max(0, Math.min(100, score)),
    verdict: score >= 75 ? 'event_chain_looks_complete_for_local_test' : score >= 45 ? 'partial_or_needs_review' : 'incomplete_or_synthetic_signals',
    total: items.length,
    pointerEvents: pointer.length,
    mouseEvents: mouse.length,
    touchEvents: touch.length,
    moveEvents: moves.length,
    downEvents: downs.length,
    upEvents: ups.length,
    untrustedEvents: untrusted,
    avgIntervalMs: Math.round(avgDt*1000)/1000,
    eventTypes: Array.from(types)
  };
}
for(const name of eventNames){
  zone.addEventListener(name, e=>{logs.push(pick(e)); update();}, {passive:true});
}
document.getElementById('clear').onclick=()=>{logs.length=0;update();};
document.getElementById('export').onclick=()=>{
  const blob=new Blob([JSON.stringify({events:logs, score:scoreEvents(logs), fingerprint:fingerprint()},null,2)],{type:'application/json'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='event-diagnostics.json'; a.click(); URL.revokeObjectURL(a.href);
};
function canvasHash(){
  try{const c=document.createElement('canvas');c.width=220;c.height=60;const ctx=c.getContext('2d');ctx.textBaseline='top';ctx.font='16px Arial';ctx.fillStyle='#f60';ctx.fillRect(0,0,220,60);ctx.fillStyle='#069';ctx.fillText('SliderTrajectoryLab 本地诊断',8,8);return c.toDataURL().slice(0,80)+'...';}catch(e){return String(e)}
}
function webglInfo(){
  try{const c=document.createElement('canvas');const gl=c.getContext('webgl')||c.getContext('experimental-webgl');if(!gl)return null;const dbg=gl.getExtension('WEBGL_debug_renderer_info');return dbg?{vendor:gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL),renderer:gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)}:{vendor:gl.getParameter(gl.VENDOR),renderer:gl.getParameter(gl.RENDERER)}}catch(e){return {error:String(e)}}
}
function fingerprint(){
  return {
    userAgent:navigator.userAgent,
    webdriver:navigator.webdriver,
    languages:navigator.languages,
    platform:navigator.platform,
    hardwareConcurrency:navigator.hardwareConcurrency,
    deviceMemory:navigator.deviceMemory,
    maxTouchPoints:navigator.maxTouchPoints,
    cookieEnabled:navigator.cookieEnabled,
    doNotTrack:navigator.doNotTrack,
    timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,
    screen:{w:screen.width,h:screen.height,aw:screen.availWidth,ah:screen.availHeight,colorDepth:screen.colorDepth,pixelDepth:screen.pixelDepth,devicePixelRatio:window.devicePixelRatio},
    plugins:Array.from(navigator.plugins||[]).map(p=>p.name).slice(0,20),
    mimeTypes:Array.from(navigator.mimeTypes||[]).map(m=>m.type).slice(0,20),
    permissionsApi:!!navigator.permissions,
    webgl:webglInfo(),
    canvasSample:canvasHash()
  };
}
fpEl.textContent = JSON.stringify(fingerprint(), null, 2);
update();
