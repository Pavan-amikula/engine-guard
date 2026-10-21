'use strict';
const $=id=>document.getElementById(id);
const scenarios={
  pressure_bias:{title:'Pressure deviation',label:'MANIFOLD SENSOR +15%',file:'ftp75city2_f_pim_115.csv',note:'A +15% bias is introduced into the manifold pressure sensor during the recorded engine run.'},
  nominal:{title:'Nominal operation',label:'FAULT-FREE REFERENCE',file:'ftp75city2_NF.csv',note:'An untouched FTP75 city recording. Compare the physical sensor with an independently estimated pressure.'},
  airflow_bias:{title:'Airflow deviation',label:'AIR-MASS SENSOR +15%',file:'ftp75city2_f_waf_115.csv',note:'A +15% airflow-sensor bias affects an estimator input. Watch how the pressure residual responds.'},
  intercooler_bias:{title:'Intercooler deviation',label:'INTERCOOLER SENSOR +15%',file:'ftp75city2_f_pic_115.csv',note:'A +15% intercooler-pressure bias affects an estimator input and the recorded engine response.'}
};
let frames=[],filtered=[],index=0,playing=false,last=0,elapsed=0,speed=1,windowSize=60;
let scenario='pressure_bias',metrics=null,fault=null,firstAlarm=null,requestId=0,hoverX=null;
const visible={measured:true,virtual:true};
const colors={ink:'#292a26',muted:'#8a907e',rule:'#e4e6dc',orange:'#cb492a',blue:'#4169b5',alarm:'#f3d5c9'};
function formatTime(t){return `${String(Math.floor(t/60)).padStart(2,'0')}:${(t%60).toFixed(2).padStart(5,'0')}`;}
function setPlaying(value){playing=Boolean(value&&frames.length);if(playing&&index===frames.length-1)seekTo(0);last=performance.now();$('play-label').textContent=playing?'Pause recording':'Play recording';$('play-icon').textContent=playing?'Ⅱ':'▶';$('play').classList.toggle('playing',playing);}
function seekTo(i){if(!frames.length)return;index=Math.max(0,Math.min(frames.length-1,Math.round(i)));elapsed=frames[index][0];render();}
function atTime(t){let lo=0,hi=frames.length-1;while(lo<hi){let mid=(lo+hi)>>1;if(frames[mid][0]<t)lo=mid+1;else hi=mid;}return lo;}
async function load(){
  const id=++requestId;setPlaying(false);frames=[];filtered=[];fault=null;firstAlarm=null;$('play').disabled=true;
  $('status').textContent='Loading recording';$('status-detail').textContent='Preparing compiled C outputs';$('monitor-box').classList.remove('alarm');
  $('monitor-symbol').textContent='○';$('source').textContent='Loading selected recording…';$('recording-length').textContent='— S';$('timeline-duration').textContent='—';$('time').textContent='00:00.00';$('total-time').textContent='/ —';$('jump-fault').disabled=true;
  ['measured','virtual','delta'].forEach(k=>$(k).textContent='—');$('events').innerHTML='<p class="muted">Reading events…</p>';
  const meta=scenarios[scenario];$('experiment-title').textContent=meta.title;$('experiment-label').textContent=meta.label;$('scenario-note').textContent=meta.note;
  document.querySelectorAll('[data-scenario]').forEach(b=>{let active=b.dataset.scenario===scenario;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  drawEmpty();
  try{
    const response=await fetch('/api/replay?scenario='+scenario);if(!response.ok)throw Error('Recording unavailable. Check the local replay server.');
    const data=await response.json();if(id!==requestId)return;if(!data.frames.length)throw Error('This recording has no samples.');
    frames=data.frames;let z=0;filtered=frames.map(f=>{z=f[3]?0:.95*z+.05*(f[1]-f[2]);return z;});
    index=0;elapsed=0;$('seek').max=frames.length-1;$('source').textContent=data.source;
    $('recording-length').textContent=Math.round(frames.at(-1)[0])+' S';$('timeline-duration').textContent=`${frames.length.toLocaleString()} SAMPLES`;
    $('total-time').textContent='/ '+formatTime(frames.at(-1)[0]);$('play').disabled=false;updateEvents();seekTo(atTime(145));
  }catch(error){if(id!==requestId)return;$('status').textContent='Recording unavailable';$('status-detail').textContent=error.message;$('source').textContent='Local server connection required';$('events').innerHTML='<p class="muted">Start the local replay server and reload this page.</p>';drawEmpty();}
}
function updateEvents(){
  if(!frames.length)return;fault=metrics?.fault_runs.find(r=>r.file===scenarios[scenario].file)||null;
  firstAlarm=frames.findIndex(f=>f[4]&&(!fault||f[0]>=fault.fault_onset_s));
  const entries=[{t:0,title:'Recording begins',detail:'State reset · 20 Hz samples',kind:''}];
  if(fault)entries.push({t:fault.fault_onset_s,title:'Sensor bias introduced',detail:'Documented benchmark onset',kind:'fault'});
  if(firstAlarm>=0)entries.push({t:frames[firstAlarm][0],title:'First disagreement alarm',detail:fault?`${(frames[firstAlarm][0]-fault.fault_onset_s).toFixed(2)} s after fault onset`:'Persistent filtered residual',kind:'alarm'});
  else entries.push({t:null,title:'No alarm in recording',detail:'For this selected experiment',kind:''});
  $('events').replaceChildren(...entries.map(e=>{const row=document.createElement('div');row.className='event '+e.kind;const dot=document.createElement('i');dot.className='event-bullet';row.append(dot);const b=document.createElement(e.t===null?'div':'button');if(e.t!==null){b.setAttribute('aria-label',`Jump to ${e.title.toLowerCase()}`);b.onclick=()=>{setPlaying(false);seekTo(atTime(e.t));};}const time=document.createElement('time');time.textContent=e.t===null?'—':formatTime(e.t);const title=document.createElement('strong');title.textContent=e.title;const detail=document.createElement('small');detail.textContent=e.detail;b.append(time,title,detail);row.append(b);return row;}));
  $('jump-fault').disabled=!fault;$('interpretation').textContent=scenario==='nominal'?'This nominal recording measures generalization to a different driving cycle. A quiet monitor here does not establish a zero false-alarm rate.':'A residual alarm marks persistent disagreement. It does not identify the failed component. Low-load sensor biases may stay below the threshold.';
}
function context(canvas,height){const width=canvas.clientWidth;if(!width)return null;let dpr=Math.min(devicePixelRatio||1,2);if(canvas.width!==Math.round(width*dpr)||canvas.height!==Math.round(height*dpr)){canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);}let ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);return {ctx,width,height};}
function bounds(){const duration=frames.at(-1)[0],t=frames[index][0];let span=windowSize==='all'?duration:Math.min(windowSize,duration);let end=windowSize==='all'?duration:Math.min(duration,Math.max(span,t+span*.12));return {start:Math.max(0,end-span),end};}
function chartBase(canvas,height,minimum,maximum,ticks,timeLabels){
  const setup=context(canvas,height);if(!setup)return null;const {ctx,width}=setup,{start,end}=bounds();
  const left=43,right=width-18,top=15,bottom=height-(timeLabels?25:16);
  const x=t=>left+(t-start)/Math.max(end-start,.01)*(right-left),y=v=>bottom-(v-minimum)/(maximum-minimum)*(bottom-top);
  ctx.font='9px "IBM Plex Mono", monospace';ctx.fillStyle=colors.muted;ctx.lineWidth=.7;
  ticks.forEach(v=>{let yy=y(v);ctx.strokeStyle=colors.rule;ctx.beginPath();ctx.moveTo(left,yy);ctx.lineTo(right,yy);ctx.stroke();ctx.textAlign='right';ctx.fillText(v.toFixed(0),left-10,yy+3);});
  for(let i=0;i<=5;i++){let t=start+(end-start)*i/5,xx=x(t);ctx.strokeStyle=colors.rule;ctx.beginPath();ctx.moveTo(xx,top);ctx.lineTo(xx,bottom);ctx.stroke();if(timeLabels){ctx.fillStyle=colors.muted;ctx.textAlign=i===0?'left':i===5?'right':'center';ctx.fillText(t.toFixed(0),xx,height-7);}}
  const from=atTime(start),to=atTime(end);ctx.save();ctx.beginPath();ctx.rect(left,top,right-left,bottom-top);ctx.clip();
  let alarmStart=null;const playedTo=Math.min(to,index);for(let j=from;j<=playedTo;j++){if(frames[j][4]&&alarmStart===null)alarmStart=frames[j][0];if((!frames[j][4]||j===playedTo)&&alarmStart!==null){ctx.fillStyle=colors.alarm+'77';ctx.fillRect(x(alarmStart),top,Math.max(1,x(frames[j][0])-x(alarmStart)),bottom-top);alarmStart=null;}}
  if(fault&&fault.fault_onset_s>=start&&fault.fault_onset_s<=end){let xx=x(fault.fault_onset_s);ctx.strokeStyle=colors.orange;ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(xx,top);ctx.lineTo(xx,bottom);ctx.stroke();ctx.setLineDash([]);}
  ctx.restore();return {ctx,width,left,right,top,bottom,start,end,x,y,from,to};
}
function drawSeries(p,value,color,lineWidth=1.3){const {ctx}=p;ctx.save();ctx.beginPath();ctx.rect(p.left,p.top,p.right-p.left,p.bottom-p.top);ctx.clip();ctx.beginPath();let until=Math.min(p.to,index),step=Math.max(1,Math.floor((until-p.from)/Math.max(1,p.width*2)));for(let j=p.from;j<=until;j+=step){let xx=p.x(frames[j][0]),yy=p.y(value(j));if(j===p.from)ctx.moveTo(xx,yy);else ctx.lineTo(xx,yy);}ctx.lineWidth=lineWidth;ctx.strokeStyle=color;ctx.stroke();ctx.restore();}
function drawCharts(){
  if(!frames.length)return;const p=chartBase($('trace'),$('trace').clientHeight,0,180,[0,30,60,90,120,150,180],false);if(!p)return;
  if(visible.measured)drawSeries(p,j=>frames[j][1],colors.orange);if(visible.virtual)drawSeries(p,j=>frames[j][2],colors.blue);
  let xx=p.x(frames[index][0]);p.ctx.strokeStyle='#9fa58e';p.ctx.setLineDash([2,3]);p.ctx.beginPath();p.ctx.moveTo(xx,p.top);p.ctx.lineTo(xx,p.bottom);p.ctx.stroke();p.ctx.setLineDash([]);
  [1,2].forEach(k=>{if(!visible[k===1?'measured':'virtual'])return;p.ctx.fillStyle=k===1?colors.orange:colors.blue;p.ctx.beginPath();p.ctx.arc(xx,p.y(frames[index][k]),3,0,Math.PI*2);p.ctx.fill();});
  if(hoverX!==null){let h=Math.max(p.left,Math.min(p.right,hoverX));p.ctx.strokeStyle='#737b65';p.ctx.beginPath();p.ctx.moveTo(h,p.top);p.ctx.lineTo(h,p.bottom);p.ctx.stroke();}
  const threshold=(metrics?.deployment.alarm_threshold_pa||6385.83)/1000;
  const q=chartBase($('residual'),110,-18,18,[-15,0,15],true);if(q){q.ctx.setLineDash([4,4]);q.ctx.strokeStyle='#bd9c89';q.ctx.lineWidth=.8;[-threshold,threshold].forEach(v=>{q.ctx.beginPath();q.ctx.moveTo(q.left,q.y(v));q.ctx.lineTo(q.right,q.y(v));q.ctx.stroke();});q.ctx.setLineDash([]);drawSeries(q,j=>filtered[j],'#768366',1.2);}drawOverview();
}
function drawOverview(){
  const p=context($('overview'),42);if(!p||!frames.length)return;const {ctx,width}=p,duration=frames.at(-1)[0];
  ctx.strokeStyle='#b5bdab';ctx.lineWidth=.8;ctx.beginPath();let step=Math.max(1,Math.floor(frames.length/width));for(let j=0;j<frames.length;j+=step){let x=1+frames[j][0]/duration*(width-2),y=39-frames[j][1]/180*34;j?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();
  const b=bounds();ctx.fillStyle='#aeb79c20';ctx.fillRect(b.start/duration*width,0,(b.end-b.start)/duration*width,42);
  ctx.fillStyle=colors.orange;for(let j=0;j<frames.length;j+=step)if(frames[j][4])ctx.fillRect(frames[j][0]/duration*width,39,Math.max(1,step/frames.length*width),2);
  if(fault){ctx.fillStyle='#cb492a50';ctx.fillRect(fault.fault_onset_s/duration*width,0,1,42);}
  let cursor=frames[index][0]/duration*width;ctx.strokeStyle=colors.ink;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(cursor,0);ctx.lineTo(cursor,42);ctx.stroke();ctx.fillStyle=colors.ink;ctx.beginPath();ctx.moveTo(cursor-3,0);ctx.lineTo(cursor+3,0);ctx.lineTo(cursor,4);ctx.closePath();ctx.fill();
}
function render(){
  if(!frames.length)return;const f=frames[index];$('measured').textContent=f[1].toFixed(1);$('virtual').textContent=f[2].toFixed(1);let delta=f[1]-f[2];$('delta').textContent=(delta>0?'+':'')+delta.toFixed(1);$('time').textContent=formatTime(f[0]);$('seek').value=index;
  $('status').textContent=f[3]===2?'Invalid input':f[3]===1?'Baseline fallback':f[4]?'Disagreement detected':'Signals consistent';$('monitor-symbol').textContent=f[4]||f[3]?'!':'◎';$('monitor-box').classList.toggle('alarm',Boolean(f[4]||f[3]));$('status-detail').textContent=f[3]?'Residual monitor disabled':f[4]?'Filtered residual exceeds threshold':'Residual monitor enabled';if(!$('telemetry-view').hidden)drawCharts();
}
function drawEmpty(){['trace','residual','overview'].forEach(id=>{const el=$(id);context(el,el.clientHeight);});}
function populateEvidence(){
  if(!metrics)return;const variants=[['Speed-density baseline','speed_density'],['Ridge regression','ridge'],['Residual MLP · float32','float_mlp'],['Guarded C · int16 storage','deployed_guarded_c']],max=metrics.test.speed_density.rmse_kpa;
  $('benchmark-bars').replaceChildren(...variants.map(([label,key])=>{let row=document.createElement('div');row.className='benchmark-row';let heading=document.createElement('div');let name=document.createElement('span');name.textContent=label;let value=document.createElement('span');value.className='mono';value.textContent=metrics.test[key].rmse_kpa.toFixed(3);heading.append(name,value);let track=document.createElement('div');track.className='bar-track';let fill=document.createElement('div');fill.className='bar-fill';fill.style.width=metrics.test[key].rmse_kpa/max*100+'%';track.append(fill);row.append(heading,track);return row;}));
  $('evidence-score').textContent=`${((1-metrics.test.deployed_guarded_c.rmse_kpa/max)*100).toFixed(1)}% lower RMSE than the speed-density baseline on the independent nominal FTP75 recording.`;
  $('parameter-value').replaceChildren(document.createTextNode(metrics.deployment.parameter_bytes_int16.toLocaleString()),Object.assign(document.createElement('small'),{textContent:' bytes'}));$('storage-reduction').textContent=((1-metrics.deployment.parameter_bytes_int16/metrics.deployment.parameter_bytes_float32)*100).toFixed(1)+'%';$('parity').textContent=metrics.deployment.c_python_max_abs_diff_pa_in_domain.toFixed(3)+' Pa max';$('sample-count').textContent=metrics.rows.test.toLocaleString();$('threshold-label').textContent=`±${(metrics.deployment.alarm_threshold_pa/1000).toFixed(2)} kPa threshold`;
}
document.querySelectorAll('[data-scenario]').forEach(b=>b.onclick=()=>{scenario=b.dataset.scenario;hoverX=null;load();});
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{let telemetry=b.dataset.view==='telemetry';$('telemetry-view').hidden=!telemetry;$('evidence-view').hidden=telemetry;document.querySelectorAll('[data-view]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});if(!telemetry)setPlaying(false);else render();});
document.querySelectorAll('[data-window]').forEach(b=>b.onclick=()=>{windowSize=b.dataset.window==='all'?'all':Number(b.dataset.window);document.querySelectorAll('[data-window]').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b));});drawCharts();});
document.querySelectorAll('[data-speed]').forEach(b=>b.onclick=()=>{speed=Number(b.dataset.speed);document.querySelectorAll('[data-speed]').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b));});});
['measured','virtual'].forEach(key=>$('toggle-'+key).onclick=()=>{visible[key]=!visible[key];$('toggle-'+key).setAttribute('aria-pressed',String(visible[key]));drawCharts();});
$('play').onclick=()=>setPlaying(!playing);$('reset').onclick=()=>{setPlaying(false);seekTo(0);};$('seek').oninput=()=>seekTo(Number($('seek').value));$('jump-fault').onclick=()=>{if(!fault)return;setPlaying(false);seekTo(atTime(Math.max(0,fault.fault_onset_s-5)));};
$('trace').onpointermove=e=>{if(!frames.length)return;const rect=e.currentTarget.getBoundingClientRect();hoverX=e.clientX-rect.left;const b=bounds(),ratio=Math.max(0,Math.min(1,(hoverX-43)/(rect.width-61))),i=atTime(b.start+ratio*(b.end-b.start)),f=frames[i];$('cursor-readout').textContent=`${f[0].toFixed(2)} s / ${f[1].toFixed(1)} : ${f[2].toFixed(1)} kPa`;drawCharts();};
$('trace').onpointerleave=()=>{hoverX=null;$('cursor-readout').textContent='Click a trace to inspect';drawCharts();};$('trace').onclick=e=>{if(!frames.length)return;const rect=e.currentTarget.getBoundingClientRect(),b=bounds(),ratio=Math.max(0,Math.min(1,(e.clientX-rect.left-43)/(rect.width-61)));setPlaying(false);seekTo(atTime(b.start+ratio*(b.end-b.start)));};
document.addEventListener('keydown',e=>{if(['INPUT','SELECT','BUTTON','A'].includes(document.activeElement.tagName)||$('telemetry-view').hidden)return;if(e.code==='Space'){e.preventDefault();setPlaying(!playing);}else if(e.code==='ArrowRight'){e.preventDefault();seekTo(index+100);}else if(e.code==='ArrowLeft'){e.preventDefault();seekTo(index-100);}else if(e.key.toLowerCase()==='r'){setPlaying(false);seekTo(0);}});
new ResizeObserver(()=>render()).observe($('trace'));let lastDraw=0;
function tick(now){if(playing&&frames.length){elapsed+=Math.min((now-last)/1000,.25)*speed;while(index<frames.length-1&&frames[index+1][0]<=elapsed)index++;if(index===frames.length-1)setPlaying(false);if(now-lastDraw>40){render();lastDraw=now;}}last=now;requestAnimationFrame(tick);}
fetch('/api/metrics').then(r=>{if(!r.ok)throw Error('Metrics unavailable');return r.json();}).then(m=>{metrics=m;populateEvidence();updateEvents();render();}).catch(()=>{$('evidence-score').textContent='Evaluation metrics unavailable. Check the local server.';});load();requestAnimationFrame(tick);
