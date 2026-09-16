/* Shared field-level records; every note revision is retained. */
(function(root){
function empty(){return {version:3,fields:{},notes:{}}}
function validate(d){if(!d||d.version!==3||!d.fields||!d.notes)throw Error('지원하지 않는 기록 파일입니다.');for(const [k,v] of Object.entries(d.fields)){if(!v||typeof v.stamp!=='string'||!/^\d{13}-/.test(v.stamp))throw Error('기록 형식 오류');if(k.startsWith('done:')||k.startsWith('unlock:')){if(typeof v.value!=='boolean')throw Error('체크 형식 오류')}else if(k==='start_date'||k==='interview_date'){if(typeof v.value!=='string'||(v.value&&!/^\d{4}-\d{2}-\d{2}$/.test(v.value)))throw Error('날짜 형식 오류')}else throw Error('알 수 없는 기록 항목')}for(const [day,revisions] of Object.entries(d.notes)){if(!/^\d{4}-\d{2}-\d{2}$/.test(day)||!revisions||typeof revisions!=='object')throw Error('메모 형식 오류');for(const [stamp,note] of Object.entries(revisions))if(!/^\d{13}-/.test(stamp)||typeof note!=='string')throw Error('메모 형식 오류')}return d}
function merge(a,b){validate(a);validate(b);const out=empty();for(const d of [a,b]){for(const [k,v] of Object.entries(d.fields))if(!out.fields[k]||v.stamp>out.fields[k].stamp)out.fields[k]=v;for(const [k,v] of Object.entries(d.notes))out.notes[k]={...out.notes[k],...v}}return out}
function value(d,k,f){return d.fields[k]?.value??f}
function note(d,day){const n=d.notes[day]||{};return n[Object.keys(n).sort().at(-1)]||''}
root.Progress={empty,validate,merge,value,note};
})(globalThis);
