'use strict';
const $ = id => document.getElementById(id);
const nf = new Intl.NumberFormat('en-US');
const date = new Intl.DateTimeFormat('en-GB', {timeZone:'Europe/Berlin',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
const clock = new Intl.DateTimeFormat('en-GB', {timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
let data = null, range = 'session', busy = false, failed = false;
try {const saved=JSON.parse(localStorage.getItem('slm-dashboard-view')||'{}');range=saved.range==='all'?'all':'session';$('continuous').checked=!!saved.continuous;} catch {}
function saveView(){try{localStorage.setItem('slm-dashboard-view',JSON.stringify({range,continuous:$('continuous').checked}));}catch{}}
const valid = n => typeof n === 'number' && Number.isFinite(n);
const compact = n => !valid(n) ? '—' : n >= 1e6 ? `${(n/1e6).toFixed(2)}M` : n >= 1e3 ? `${(n/1e3).toFixed(1)}k` : n.toFixed(0);
const stamp = t => valid(t) ? `${date.format(new Date(t*1000))} CEST` : '—';
const text = (id, value) => {$(id).textContent = value;};
function remaining(t) {if(!valid(t))return '—'; const s=Math.max(0,Math.floor(t-Date.now()/1000)); return s ? `${Math.floor(s/3600)}h ${String(Math.floor(s%3600/60)).padStart(2,'0')}m` : 'Budget window ended';}
function liveStatus() {
  if (!data) return;
  const age = valid(data.heartbeat_age) ? data.heartbeat_age + Math.max(0,Date.now()/1000-data.generated_at) : null;
  const stale = data.status === 'running' && (!data.supervisor_alive || age === null || age > 90);
  const label = failed ? 'Connection lost' : stale ? 'Status needs checking' : data.status === 'running' ? (data.phase === 'evaluation' ? 'Evaluating' : data.phase === 'report' ? 'Writing report' : 'Training') : data.status === 'completed' ? 'Completed' : data.status === 'paused' ? 'Paused' : data.status;
  text('status', label);
  $('status').className = 'status'+(failed || stale || data.status==='paused' ? ' warning' : data.live ? ' live' : '');
  text('heartbeat', data.status==='running' && valid(age) ? `Controller heartbeat ${Math.floor(age)}s ago` : data.recoverable ? 'Showing saved checkpoint progress' : '');
  text('remaining', data.status==='completed' ? 'Finished' : remaining(data.deadline));
}
function paint() {
  text('tokens',compact(data.tokens)); $('tokens').title=valid(data.tokens)?nf.format(data.tokens):'';
  text('steps',valid(data.steps)?nf.format(data.steps):'—');
  text('loss',valid(data.best_dev_loss)?data.best_dev_loss.toFixed(4):'—');
  text('speed',valid(data.speed)?nf.format(Math.round(data.speed)):'—');
  text('speed-note',valid(data.speed)?'Training tokens / second':'No fresh training speed sample');
  text('tokens-note',data.recoverable?'Saved, recoverable training targets':'Cumulative prediction targets');
  text('until',stamp(data.training_until)); text('deadline',stamp(data.deadline));
  text('checkpoint',valid(data.checkpoint_step)?`Update ${nf.format(data.checkpoint_step)}`:'Not saved yet');
  text('checked',`Checked ${stamp(data.generated_at)}`);
  text('run',data.run);
  const checks=data.evaluations.map(e=>`${e.name==='final-dev'?'Final dev':'Confirmation'}: ${e.completed?'complete ('+nf.format(e.evaluated)+' tasks)':e.evaluated?'partial ('+nf.format(e.evaluated)+' tasks)':'pending'}`);
  text('evaluations',checks.join(' · ')+`. Report: ${data.report_ready?'available':'pending'}.`);
  if(data.error){$('error').hidden=false;$('error').textContent=data.error;} else if(!failed){$('error').hidden=true;}
  liveStatus(); drawAll();
}
function svgNode(tag, attrs={}, value) {
  const el=document.createElementNS('http://www.w3.org/2000/svg',tag);
  Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));
  if(value!==undefined)el.textContent=value;
  return el;
}
function chart(id, segments, key, color, axis, logarithmic=false) {
  const container=$(id); container.replaceChildren();
  segments=segments.map(s=>s.filter(p=>valid(p[key]) && (!logarithmic||p[key]>0))).filter(s=>s.length);
  const points=segments.flat();
  if(!points.length){const empty=document.createElement('div');empty.className='empty';empty.textContent='No samples in this time range yet.';container.append(empty);return;}
  const width=Math.max(320,container.clientWidth), height=235;
  const left=55,right=16,top=14,bottom=38,pw=width-left-right,ph=height-top-bottom;
  let y0=Math.min(...points.map(p=>p[key])),y1=Math.max(...points.map(p=>p[key]));
  const transform=logarithmic?Math.log10:n=>n, inverse=logarithmic?n=>10**n:n=>n;
  y0=transform(y0);y1=transform(y1);
  const pad=(y1-y0)*.1 || Math.max(Math.abs(y1)*.03,.03);y0-=pad;y1+=pad;
  if(!logarithmic)y0=Math.max(0,y0);
  const {start,end}=axis, x=t=>left+(axis.map(t)-start)/Math.max(1,end-start)*pw, y=v=>top+(y1-transform(v))/(y1-y0)*ph;
  const svg=svgNode('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':`${container.previousElementSibling.querySelector('h3').textContent}, ${points.length} plotted samples`});
  for(let i=0;i<5;i++){
    const v=inverse(y0+(y1-y0)*i/4),py=y(v);
    svg.append(svgNode('line',{x1:left,x2:width-right,y1:py,y2:py,stroke:'#e4e8df','stroke-dasharray':i===0?'0':'3 4'}));
    const label=key==='loss'?v.toFixed(v<2?3:2):v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(1)+'k':Math.round(v).toString();
    svg.append(svgNode('text',{x:left-9,y:py+3,'text-anchor':'end'},label));
  }
  const count=width<420?3:4;
  for(let i=0;i<count;i++){
    const t=start+(end-start)*i/(count-1), label=axis.tick(t);
    svg.append(svgNode('text',{x:left+pw*i/(count-1),y:height-12,'text-anchor':i===0?'start':i===count-1?'end':'middle'},label));
  }
  for(const segment of segments){
    const d=segment.map((p,i)=>`${i?'L':'M'}${x(p.time).toFixed(2)},${y(p[key]).toFixed(2)}`).join(' ');
    if(key!=='loss' && segment.length>1){svg.append(svgNode('path',{d:`${d} L${x(segment.at(-1).time)},${top+ph} L${x(segment[0].time)},${top+ph} Z`,fill:color,'fill-opacity':'.045'}));}
    svg.append(svgNode('path',{d,fill:'none',stroke:color,'stroke-width':'1.8','stroke-linecap':'round','stroke-linejoin':'round'}));
    if(key==='loss' || segment.length===1)for(const p of segment)svg.append(svgNode('circle',{cx:x(p.time),cy:y(p[key]),r:3,fill:color,stroke:'#fcfcf8','stroke-width':1}));
  }
  const cross=svgNode('line',{x1:0,x2:0,y1:top,y2:top+ph,stroke:color,'stroke-dasharray':'3 3',visibility:'hidden'});
  const dot=svgNode('circle',{cx:0,cy:0,r:4,fill:color,stroke:'#fcfcf8','stroke-width':2,visibility:'hidden'});
  svg.append(cross,dot);container.append(svg);
  const tip=document.createElement('div');tip.className='tooltip';tip.hidden=true;container.append(tip);
  svg.addEventListener('pointermove',event=>{
    const rect=svg.getBoundingClientRect(), px=(event.clientX-rect.left)/rect.width*width;
    let point=points[0];for(const p of points)if(Math.abs(x(p.time)-px)<Math.abs(x(point.time)-px))point=p;
    cross.setAttribute('x1',x(point.time));cross.setAttribute('x2',x(point.time));cross.setAttribute('visibility','visible');
    dot.setAttribute('cx',x(point.time));dot.setAttribute('cy',y(point[key]));dot.setAttribute('visibility','visible');
    const value=key==='loss'?point[key].toFixed(4):nf.format(Math.round(point[key]));
    tip.textContent=`${stamp(point.time)} · ${value}${key==='speed'?' tok/s':key==='tokens'?' tokens':key==='step'?' updates':' loss'}`;tip.hidden=false;
  });
  svg.addEventListener('pointerleave',()=>{tip.hidden=true;cross.setAttribute('visibility','hidden');dot.setAttribute('visibility','hidden');});
}
function drawAll(){
  if(!data)return;
  const h=data.history, since=range==='session'?(h.sessions.at(-1)?.time ?? 0):0;
  const segments=h.segments.map(s=>s.filter(p=>p.time>=since)).filter(s=>s.length);
  const dev=h.development.filter(p=>p.time>=since);
  const devGroups=[];for(const p of dev){if(!devGroups.length || devGroups.at(-1)[0].session!==p.session)devGroups.push([]);devGroups.at(-1).push(p);}
  const points=segments.flat(), times=[...points,...dev].map(p=>p.time);
  const start=range==='session'&&since?since:times.length?Math.min(...times):data.generated_at,end=Math.max(start+1,...times);
  const continuous=$('continuous').checked;
  const duration=t=>`${Math.floor(t/3600)}h ${String(Math.floor(t%3600/60)).padStart(2,'0')}m`;
  const compress=t=>trainingElapsed(h.sessions,t);
  const base=compress(start);
  const axis=continuous?{start:0,end:Math.max(1,compress(end)-base),map:t=>compress(t)-base,tick:duration}:{start,end,map:t=>t,tick:t=>range==='all'?date.format(new Date(t*1000)):clock.format(new Date(t*1000))};
  text('range-caption',`${range==='session'?'Latest session':'All recorded sessions'} · ${continuous?'Continuous view · logged session time, pause gaps removed':stamp(start)+' → '+clock.format(new Date(end*1000))+' · wall-clock time'}`);
  chart('token-chart',segments,'tokens','#237454',axis);
  chart('step-chart',segments,'step','#237454',axis);
  chart('loss-chart',devGroups,'loss','#a76c23',axis,true);
  chart('speed-chart',segments,'speed','#48768a',axis);
}
async function refresh(){
  if(busy)return;busy=true;$('refresh').disabled=true;$('refresh').textContent='Reading…';
  try{const response=await fetch('/api/status',{cache:'no-store'});if(!response.ok)throw new Error('Snapshot unavailable');data=await response.json();failed=false;paint();}
  catch(error){failed=true;$('error').hidden=false;$('error').textContent='Could not refresh. The values below may be outdated. Check that the local dashboard server is running, then try again.';if(data)liveStatus();else text('status','Dashboard unavailable');}
  finally{busy=false;$('refresh').disabled=false;$('refresh').textContent='↻ Refresh';}
}
$('refresh').addEventListener('click',refresh);
document.querySelectorAll('[data-range]').forEach(button=>button.addEventListener('click',()=>{range=button.dataset.range;document.querySelectorAll('[data-range]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));saveView();drawAll();}));
document.querySelectorAll('[data-range]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.range===range)));
$('continuous').addEventListener('change',()=>{saveView();drawAll();});
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(drawAll,120);});
setInterval(()=>{if($('auto').checked)refresh();},30000);
setInterval(liveStatus,1000);
refresh();
