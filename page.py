# The settings web page. One fixed page; its script loads /state and sends changes to /set, so
# tapping a button updates at once without reloading. The key travels in the address (?k=...).
# Written for a phone: big buttons, no zooming. Kept small because the board serves it from RAM.
PAGE = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Scoreboard</title><style>
*{box-sizing:border-box}body{font:17px system-ui,sans-serif;margin:0;background:#0d0d10;color:#eee}
main{max-width:520px;margin:auto;padding:14px 14px 80px}h1{font-size:24px;margin:6px 0 2px}
#info{color:#8a8a95;font-size:13px;margin:0 0 6px}
section{background:#17171c;border-radius:14px;padding:12px;margin:12px 0}
h2{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:#8a8a95;margin:0 0 8px}
.row{display:flex;flex-wrap:wrap;gap:8px}
button{flex:1 1 auto;min-width:72px;font:inherit;color:#eee;background:#2a2a32;border:0;border-radius:10px;
padding:13px 10px;touch-action:manipulation}button:active{filter:brightness(1.4)}
button.on{background:#1b9e6b;color:#fff;font-weight:600}
button.off{background:#8a2b2b;color:#fff;font-weight:600}
button.big{width:100%;padding:18px;font-size:19px}button.chip{flex:0 0 auto;margin-bottom:6px}
input{font:inherit;width:100%;padding:12px;margin-bottom:8px;border:0;border-radius:10px;background:#26262e;color:#eee}
.third{display:flex;gap:8px}.third input{flex:1;min-width:0}label{font-size:12px;color:#8a8a95}
#toast{position:fixed;left:0;right:0;bottom:18px;text-align:center;pointer-events:none;opacity:0;transition:opacity .2s}
#toast span{background:#333;padding:9px 16px;border-radius:20px;font-size:15px}#toast.show{opacity:1}
select{font:inherit;width:100%;padding:12px;margin:4px 0 10px;border:0;border-radius:10px;background:#26262e;color:#eee}
a{color:#7aa7ff}</style></head><body><main>
<h1>Scoreboard</h1><p id=info>loading...</p><div id=app></div>
<p><a id=log>Show the log</a></p></main><div id=toast><span id=tt></span></div>
<script>
var K=new URLSearchParams(location.search).get('k')||'',S={},T,TL={};
function call(p){return fetch('/'+p+(p.indexOf('?')<0?'?':'&')+'k='+encodeURIComponent(K))}
function toast(t){var e=document.getElementById('toast');document.getElementById('tt').textContent=t;e.className='show';
clearTimeout(T);T=setTimeout(function(){e.className=''},1400)}
function send(q,label){call('set?'+q).then(function(r){toast(r.ok?(label||'Saved'):'Not saved: '+r.status)},
function(){toast('Board not answering, try again')})}
function pick(key,val,label){S[key]=val;draw();send(key+'='+val,label)}
function btn(text,on,fn,cls){var b=document.createElement('button');b.textContent=text;
b.className=(on?'on ':'')+(cls||'');b.onclick=fn;return b}
function sec(title,items){var s=document.createElement('section'),h=document.createElement('h2'),r=document.createElement('div');
h.textContent=title;r.className='row';items.forEach(function(i){r.appendChild(i)});s.appendChild(h);s.appendChild(r);return s}
function opts(title,key,list){return sec(title,list.map(function(o){return btn(o[0],S[key]==o[1],function(){pick(key,o[1])})}))}
function field(id,label,val){var d=document.createElement('div');d.style.flex='1';
d.innerHTML='<label>'+label+'</label><input id='+id+' value="'+val+'" inputmode=decimal>';return d}
function teamsec(){var t=document.createElement('section');t.innerHTML='<h2>Teams you follow (up to 4 per sport)</h2>';
[['baseball','Baseball (MLB)'],['football','Football (NFL)'],['hockey','Hockey (NHL)'],['basketball','Basketball (NBA)'],['soccer','Soccer (MLS)']].forEach(function(x){
var k='team_'+x[0],cur=(S[k]||'').split(',').filter(Boolean),L=TL[x[0]]||[],d=document.createElement('div'),row=document.createElement('div');
d.innerHTML='<label>'+x[1]+'</label>';row.className='row';
cur.forEach(function(ab){var n=ab;L.forEach(function(o){if(o[0]==ab)n=o[1]});
row.appendChild(btn(n+(cur.length>1?' \\u00d7':''),1,function(){if(cur.length<2){toast('Follow at least one team');return}
pick(k,cur.filter(function(z){return z!=ab}).join(','),'Stopped following '+n)},'chip'))});d.appendChild(row);
if(cur.length<4&&L.length){var s=document.createElement('select'),o0=document.createElement('option');o0.value='';o0.textContent='Add a team...';s.appendChild(o0);
L.forEach(function(o){if(cur.indexOf(o[0])<0){var q=document.createElement('option');q.value=o[0];q.textContent=o[1];s.appendChild(q)}});
s.onchange=function(){if(s.value)pick(k,cur.concat([s.value]).join(','),'Following '+s.options[s.selectedIndex].textContent)};d.appendChild(s)}
t.appendChild(d)});return t}
function remsec(){var t=document.createElement('section');t.innerHTML='<h2>Reminders (shown between the slides)</h2>';
var R=window.RL||[],row=document.createElement('div');row.className='row';
R.forEach(function(r,i){var w=['once','daily','weekly'][r[3]];row.appendChild(btn(r[0]+' - '+r[1]+(r[2]?' '+r[2]:'')+' ('+w+') \u00d7',1,function(){
call('rem_del?i='+i).then(function(){toast('Deleted');rems()})},'chip'))});t.appendChild(row);
if(R.length<10){t.insertAdjacentHTML('beforeend','<input id=rt maxlength=30 placeholder="Take out the trash"><div class=third><input id=rd type=date><input id=rh type=time></div>'+
'<select id=rr><option value=0>Once</option><option value=1>Every day</option><option value=2>Every week</option></select>');
if(window.RD)document.getElementById('rd').value=window.RD;
t.appendChild(btn('Add reminder',0,function(){var x=document.getElementById('rt').value.trim(),d=document.getElementById('rd').value;
window.RD=d;if(!x||!d){toast('Needs a name and a date');return}
call('rem_add?text='+encodeURIComponent(x)+'&date='+d+'&time='+encodeURIComponent(document.getElementById('rh').value)+'&rep='+document.getElementById('rr').value)
.then(function(r){toast(r.ok?'Added':'Not valid');rems()})},'big'))}return t}
function rems(){call('reminders').then(function(r){return r.json()}).then(function(l){window.RL=l;draw()})}
function lists(){['baseball','football','hockey','basketball','soccer'].forEach(function(sp){if(!TL[sp]){TL[sp]=[];
call('teams?sport='+sp).then(function(r){return r.json()}).then(function(l){TL[sp]=l;draw()},function(){delete TL[sp]})}})}
function draw(){var a=document.getElementById('app'),on=S.display!=0;a.innerHTML='';
a.appendChild(sec('Display',[on?btn('Display is ON - tap to turn off',0,function(){pick('display',0,'Display off')},'big'):
btn('Display is OFF - tap to turn on',0,function(){pick('display',1,'Display on')},'big off')]));
a.appendChild(teamsec());
a.appendChild(opts('Brightness','bright',[['Auto',0],['10%',10],['25%',25],['50%',50],['75%',75],['100%',100]]));
a.appendChild(opts('Automatic brightness follows','sunbright',[['Sunrise and sunset',1],['Clock hours',0]]));
var qh=document.createElement('section');qh.innerHTML='<h2>Quiet hours (panel dark)</h2>';var qr=document.createElement('div');
qr.className='third';qr.appendChild(field('qs','From hour (0-23)',S.qs));qr.appendChild(field('qe','Until hour',S.qe));qh.appendChild(qr);
qh.appendChild(btn('Save quiet hours',0,function(){['qs','qe'].forEach(function(k){S[k]=document.getElementById(k).value});
send('qs='+S.qs+'&qe='+S.qe)},'big'));qh.appendChild(btn('No quiet hours',0,function(){S.qs=S.qe=0;send('qs=0&qe=0','Cleared');draw()},'big'));a.appendChild(qh);
a.appendChild(opts('Idle screen','mode',[['Normal',0],['Big clock',1],['Cameos nonstop',2]]));
var c=opts('Cameos','cameos',[['Often',0],['Normal',1],['Rare',2],['Off',3]]);
c.firstChild.nextSibling.appendChild(btn('Play one now',0,function(){send('cameo=1','Playing')}));a.appendChild(c);
a.appendChild(remsec());var m=document.createElement('section');m.innerHTML='<h2>Send a message</h2><input id=msg maxlength=60 placeholder="Dinner is ready">';
m.appendChild(btn('Scroll it across the bottom',0,function(){var v=document.getElementById('msg').value.trim();
if(v){send('msg='+encodeURIComponent(v),'Sent');document.getElementById('msg').value=''}},'big'));a.appendChild(m);
var l=document.createElement('section');l.innerHTML='<h2>Location (weather, sunrise)</h2>';var r=document.createElement('div');
r.className='third';r.appendChild(field('lat','Latitude',S.lat));r.appendChild(field('lon','Longitude',S.lon));
r.appendChild(field('tz','UTC hours',S.tz));l.appendChild(r);l.appendChild(btn('Save location',0,function(){
['lat','lon','tz'].forEach(function(k){S[k]=document.getElementById(k).value});
send('lat='+S.lat+'&lon='+S.lon+'&tz='+S.tz)},'big'));a.appendChild(l);
var bk=document.createElement('section');bk.innerHTML='<h2>Back up settings</h2><p><a id=exp>Open the settings file</a> (copy its text)</p><input id=imp placeholder="Paste settings here to restore">';
bk.appendChild(btn('Restore',0,function(){var v=document.getElementById('imp').value.trim();if(v){call('import?json='+encodeURIComponent(v)).then(function(r){
toast(r.ok?'Restored':'Not valid');load()})}},'big'));a.appendChild(bk);document.getElementById('exp').href='/export?k='+encodeURIComponent(K)}
function load(){call('state').then(function(r){return r.json()}).then(function(s){
var typing=document.activeElement&&/INPUT|SELECT/.test(document.activeElement.tagName);S=s;
document.getElementById('info').textContent=s.info;if(!typing)draw()},function(){
document.getElementById('info').textContent='Board not answering...'})}
document.getElementById('log').href='/log?k='+encodeURIComponent(K);lists();rems();load();setInterval(load,10000)
</script></body></html>"""
