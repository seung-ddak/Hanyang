const STORAGE_KEY = 'hanyang-study-pwa-v2';
const SETTINGS_KEY = 'hanyang-study-pwa-settings-v2';
const TASKS = [
  ['recall','복습 / 학습 준비',10],
  ['read','교재 읽기',30],
  ['exercise','문제 풀기',25],
  ['oral','면접 구술 연습',15],
  ['note','메모 작성',10],
];
let schedule, state, settings, selectedDate, calendarCursor;
const $ = (id)=>document.getElementById(id);
const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const parseISO = s => { const [y,m,d]=s.split('-').map(Number); return new Date(y,m-1,d); };
const dateOnly = d => new Date(d.getFullYear(),d.getMonth(),d.getDate());
const addDays = (d,n)=>{const x=new Date(d);x.setDate(x.getDate()+n);return x};
const diffDays=(a,b)=>Math.round((dateOnly(a)-dateOnly(b))/86400000);
const today=()=>dateOnly(new Date());
function loadJSON(key,fallback){try{return JSON.parse(localStorage.getItem(key))||fallback}catch{return fallback}}
function save(){localStorage.setItem(STORAGE_KEY,JSON.stringify(state));localStorage.setItem(SETTINGS_KEY,JSON.stringify(settings));}
function defaultState(){return {version:2,firstSeen:iso(today()),days:{}}}
function dayEntry(d){return state.days[iso(d)]||{done:[],note:''}}
function setEntry(d, patch){const key=iso(d);state.days[key]={...dayEntry(d),...patch};save()}
function scheduleEntry(index){const wi=Math.floor(index/7),di=index%7;return schedule.weeks[wi]?.days[di]||null}
function planFor(day){
  const start=parseISO(settings.start_date); const exam=settings.interview_date?parseISO(settings.interview_date):null;
  if(exam && day>exam) return {day,title:'설정한 면접일이 지났어요',subtitle:'필요하면 설정에서 다음 일정을 바꿔 주세요.',sections:['mock'],tasks:[],index:null};
  if(exam && iso(day)===iso(exam)) return {day,title:'면접 당일 · 가볍게 점검',subtitle:'새로운 심화 학습보다 준비한 내용을 확인하세요.',sections:['mock','research-bridge'],tasks:[{id:'review',label:'틀렸던 정의와 핵심 답변만 가볍게 확인',minutes:10,section:'mock'},{id:'research',label:'연구 기여·평가·한계를 한 번 설명',minutes:5,section:'research-bridge'},{id:'ready',label:'면접 시간·장소·준비물 확인',minutes:5,section:'roadmap'}],index:null};
  const off=diffDays(day,start);
  if(off<0) return {day,title:'학습 시작 전이에요',subtitle:`${settings.start_date}부터 7주 계획이 시작됩니다.`,sections:['roadmap'],tasks:[],index:null};
  if(off<49){const e=scheduleEntry(off);const wi=Math.floor(off/7),di=off%7;const defs=[['recall',off===0?'학습 목표와 현재 아는 내용을 세 문장으로 적기':'이전 단계 내용을 덮고 기억나는 핵심 3개 말하기',10,e.sections[0]],['read',e.scope,30,e.sections[0]],['exercise',e.exercise,25,e.sections[0]],['oral',e.oral,15,e.sections.at(-1)],['note','막힌 질문과 내일 다시 볼 질문 1개 기록',10,e.sections[0]]];return {day,title:e.title,subtitle:`${wi+1}주차 · ${di+1}일 / ${schedule.weeks[wi].title}`,sections:e.sections,tasks:defs.map(([id,label,minutes,section])=>({id,label,minutes,section})),index:off};}
  const groups=[['linear','trees','hashing'],['sorting','graphs'],['process','memory','synchronization'],['network'],['oop','database'],['discrete','extensions'],['research-bridge','mock']]; const sections=groups[(off-49)%groups.length];
  return {day,title:'면접 직전 · 오답과 구술 복습',subtitle:'7주 과정 이후 복습',sections,tasks:[{id:'recall',label:'이전 단계 내용을 덮고 기억나는 핵심 3개 말하기',minutes:10,section:sections[0]},{id:'read',label:'오늘 연결된 장에서 설명이 막혔던 질문 2개 복습',minutes:30,section:sections[0]},{id:'exercise',label:'오답 예제 1개를 새로운 숫자·조건으로 다시 풀기',minutes:25,section:sections[0]},{id:'oral',label:'30초 답변 5개와 연구 설명 1회, 새 심화는 늘리지 않기',minutes:15,section:sections.at(-1)},{id:'note',label:'막힌 질문과 내일 다시 볼 질문 1개 기록',minutes:10,section:sections[0]}],index:off};
}
function remaining(plan){const done=new Set(dayEntry(plan.day).done||[]);return plan.tasks.filter(t=>!done.has(t.id))}
function currentStage(){const start=parseISO(settings.start_date),now=today();const last=Math.max(0,diffDays(now,start));for(let n=0;n<=last;n++){const p=planFor(addDays(start,n));if(remaining(p).length)return p.day}return now<start?start:now}
function isLocked(day){if(!settings.sequential_unlock)return false;return day>today() || day>currentStage()}
function unlockedSections(){const start=parseISO(settings.start_date), last=[today(),currentStage()].sort((a,b)=>a-b)[0];const out=new Set(['roadmap']);for(let n=0;n<=Math.max(0,diffDays(last,start));n++){planFor(addDays(start,n)).sections.forEach(s=>out.add(s))}return [...out]}
function statusFor(day){const start=parseISO(settings.start_date), first=parseISO(state.firstSeen||settings.start_date),p=planFor(day);if(day<start||day<first||!p.tasks.length)return'inactive';if(isLocked(day))return'locked';if(day>today())return'future';const done=dayEntry(day).done?.length||0;if(done===p.tasks.length)return'complete';if(iso(day)===iso(today()))return'today';return done?'partial':'missed'}
function openGuide(section){if(isLocked(selectedDate)){showModal('잠긴 단계','<p>이전 단계를 모두 완료한 뒤 열 수 있습니다. 미래 날짜는 해당 날짜가 되어야 열립니다.</p>');return}const unlocked=encodeURIComponent(unlockedSections().join(','));window.open(`lessons.html?unlocked=${unlocked}#${encodeURIComponent(section)}`,'_blank')}
function render(){const plan=planFor(selectedDate);const entry=dayEntry(selectedDate);const done=new Set(entry.done||[]);const pct=plan.tasks.length?Math.round(done.size/plan.tasks.length*100):0;const stage=currentStage();
  $('stageLabel').textContent = isLocked(selectedDate)?`🔒 잠김 · ${iso(selectedDate)}`:`${iso(selectedDate)} · 현재 진도 ${iso(stage)}`;
  $('title').textContent=plan.title;$('subtitle').textContent=plan.subtitle;$('progressText').textContent=`${pct}%`;$('progressBar').style.width=`${pct}%`;$('progressRing').style.setProperty('--p',`${pct*3.6}deg`);$('remainingBadge').textContent=`${remaining(plan).length}/${plan.tasks.length} 남음`;
  $('tasks').innerHTML='';plan.tasks.forEach((t,i)=>{const locked=isLocked(selectedDate),checked=done.has(t.id);const row=document.createElement('div');row.className=`task ${checked?'done':''} ${locked?'locked':''}`;row.innerHTML=`<input type="checkbox" ${checked?'checked':''} ${locked?'disabled':''} aria-label="${t.label}"><div><div class="task-title">${t.label}</div><div class="task-meta">${TASKS.find(x=>x[0]===t.id)?.[1]||'학습'} · 교재: ${t.section}</div></div><span class="minutes">${t.minutes}분</span>`;row.querySelector('input').addEventListener('change',e=>toggleTask(plan,t.id,e.target.checked));row.querySelector('.task-title').addEventListener('click',()=>openGuide(t.section));$('tasks').appendChild(row)});
  $('note').value=entry.note||'';$('note').disabled=isLocked(selectedDate);$('openCurrentLesson').disabled=isLocked(selectedDate)||!plan.sections.length;
  renderYesterday();renderCalendar();
}
function toggleTask(plan,id,on){if(isLocked(plan.day))return;const done=new Set(dayEntry(plan.day).done||[]);on?done.add(id):done.delete(id);setEntry(plan.day,{done:[...done]});if(done.size===plan.tasks.length && iso(plan.day)===iso(currentStage())){const next=addDays(plan.day,1);if(next<=today())selectedDate=currentStage()}render()}
function renderYesterday(){const y=addDays(today(),-1),p=planFor(y),rem=remaining(p);if(!p.tasks.length||!rem.length){$('yesterdayCard').classList.add('hidden');return}$('yesterdayCard').classList.remove('hidden');$('yesterdayCount').textContent=`${rem.length}개`;$('yesterdayTasks').innerHTML='';rem.forEach(t=>{const x=document.createElement('label');x.className='compact-item';x.innerHTML=`<input type="checkbox"> <span>${t.label}</span>`;x.querySelector('input').addEventListener('change',e=>toggleTask(p,t.id,e.target.checked));$('yesterdayTasks').appendChild(x)})}
function renderCalendar(){const y=calendarCursor.getFullYear(),m=calendarCursor.getMonth();$('monthLabel').textContent=`${y}년 ${m+1}월`;const first=new Date(y,m,1);const mondayIndex=(first.getDay()+6)%7;const gridStart=addDays(first,-mondayIndex);$('calendar').innerHTML='';for(let i=0;i<42;i++){const d=addDays(gridStart,i);const p=planFor(d),st=statusFor(d);const el=document.createElement('button');el.className=`day ${st} ${d.getMonth()!==m?'out':''} ${iso(d)===iso(today())?'today':''}`;const n=dayEntry(d).done?.length||0;el.innerHTML=`<span class="num">${d.getDate()}</span><span class="mini">${p.tasks.length?n+'/'+p.tasks.length:''}</span>`;el.title=p.title;el.addEventListener('click',()=>{selectedDate=d;render();window.scrollTo({top:0,behavior:'smooth'})});$('calendar').appendChild(el)}}
function showModal(title,html){$('modalTitle').textContent=title;$('modalBody').innerHTML=html;$('modal').showModal()}
async function snooze(){
  if(!('Notification'in window)){showModal('알림 제한','<p>이 브라우저에서는 웹 알림을 지원하지 않습니다.</p>');return}
  const permission=await Notification.requestPermission();if(permission!=='granted'){showModal('알림 권한 필요','<p>알림 권한이 허용되지 않았습니다.</p>');return}
  const mins=60;showModal('다시 알림 설정',`<p>${mins}분 뒤 알림을 예약했습니다. 단, iOS가 웹앱을 완전히 종료하면 이 단순 로컬 타이머는 중단될 수 있습니다.</p>`);setTimeout(async()=>{try{const reg=await navigator.serviceWorker.ready;reg.showNotification('한양대 면접 공부',{body:'다시 공부할 시간입니다. 현재 미완료 단계를 이어서 진행하세요.',icon:'assets/icon-192.png'})}catch{}},mins*60*1000)
}
async function init(){schedule=await fetch('study_schedule.json').then(r=>r.json());state=loadJSON(STORAGE_KEY,defaultState());settings=loadJSON(SETTINGS_KEY,{start_date:'2026-09-16',interview_date:'',sequential_unlock:true});selectedDate=currentStage();calendarCursor=new Date(selectedDate.getFullYear(),selectedDate.getMonth(),1);$('startDate').value=settings.start_date;$('interviewDate').value=settings.interview_date;$('sequentialUnlock').checked=settings.sequential_unlock;render();
  if('serviceWorker'in navigator)navigator.serviceWorker.register('./sw.js').catch(()=>{});
}
$('openCurrentLesson').addEventListener('click',()=>{const p=planFor(selectedDate);openGuide(remaining(p)[0]?.section||p.sections[0]||'roadmap')});
$('openUnlocked').addEventListener('click',()=>{window.open(`lessons.html?unlocked=${encodeURIComponent(unlockedSections().join(','))}#roadmap`,'_blank')});
$('snooze').addEventListener('click',snooze);$('prevMonth').addEventListener('click',()=>{calendarCursor=new Date(calendarCursor.getFullYear(),calendarCursor.getMonth()-1,1);renderCalendar()});$('nextMonth').addEventListener('click',()=>{calendarCursor=new Date(calendarCursor.getFullYear(),calendarCursor.getMonth()+1,1);renderCalendar()});
$('note').addEventListener('input',e=>setEntry(selectedDate,{note:e.target.value}));$('startDate').addEventListener('change',e=>{settings.start_date=e.target.value;save();selectedDate=currentStage();calendarCursor=new Date(selectedDate.getFullYear(),selectedDate.getMonth(),1);render()});$('interviewDate').addEventListener('change',e=>{settings.interview_date=e.target.value;save();render()});$('sequentialUnlock').addEventListener('change',e=>{settings.sequential_unlock=e.target.checked;save();render()});
$('resetProgress').addEventListener('click',()=>showModal('학습 기록 초기화','<p>완료 체크와 메모를 모두 지웁니다. 이 작업은 되돌릴 수 없습니다.</p><button id="confirmReset" class="danger">정말 초기화</button>'));
document.addEventListener('click',e=>{if(e.target?.id==='confirmReset'){state=defaultState();save();$('modal').close();selectedDate=currentStage();render()}});$('closeModal').addEventListener('click',()=>$('modal').close());
$('installHelp').addEventListener('click',()=>showModal('iPhone에 앱처럼 설치',`<ol><li>이 페이지를 <strong>Safari</strong>로 엽니다.</li><li>하단의 <strong>공유</strong> 버튼을 누릅니다.</li><li><strong>홈 화면에 추가</strong>를 선택합니다.</li><li>추가된 '면접공부' 아이콘으로 실행합니다.</li></ol><p>오프라인 사용을 위해 첫 접속 때 인터넷 연결이 한 번 필요합니다.</p>`));
init();
