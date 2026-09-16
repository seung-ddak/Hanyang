"""Private GitHub progress sync; credentials stay in Git Credential Manager."""
from copy import deepcopy
import base64, json, os, re, subprocess, time, uuid, urllib.request, urllib.error
from study_widget_core import atomic_json, parse_date

def empty():return {'version':3,'fields':{},'notes':{}}
def validate(doc):
    if not isinstance(doc,dict) or doc.get('version')!=3 or not isinstance(doc.get('fields'),dict) or not isinstance(doc.get('notes'),dict):raise ValueError('지원하지 않는 기록 형식')
    for key,item in doc['fields'].items():
        if not isinstance(item,dict) or not re.fullmatch(r'\d{13}-.+',item.get('stamp','')):raise ValueError('기록 형식 오류')
        value=item.get('value')
        if key.startswith('done:'):
            _,day,task=key.split(':');parse_date(day)
            if task not in ('recall','read','exercise','oral','note'):raise ValueError('체크 항목 오류')
            if type(value) is not bool:raise ValueError('체크 형식 오류')
        elif key.startswith('unlock:'):
            parse_date(key[7:])
            if type(value) is not bool:raise ValueError('해금 형식 오류')
        elif key in ('start_date','interview_date'):
            if value or key=='start_date':parse_date(value)
        else:raise ValueError('알 수 없는 기록 항목')
    for day,notes in doc['notes'].items():
        parse_date(day)
        if not isinstance(notes,dict):raise ValueError('메모 형식 오류')
        for stamp,note in notes.items():
            if not re.fullmatch(r'\d{13}-.+',stamp) or not isinstance(note,str):raise ValueError('메모 형식 오류')
    return doc
def merge(a,b):
    validate(a);validate(b);out=deepcopy(a)
    for key,item in b['fields'].items():
        if key not in out['fields'] or item['stamp']>out['fields'][key]['stamp']:out['fields'][key]=deepcopy(item)
    for day,notes in b['notes'].items():out['notes'].setdefault(day,{}).update(notes)
    return out
def latest(notes):return notes[max(notes)] if notes else ''

class SharedProgress:
    def __init__(self,model):
        self.model=model;self.path=model.root/'shared_progress.json';self.device=uuid.uuid4().hex;self.clock=0
        self.doc=validate(json.loads(self.path.read_text(encoding='utf-8'))) if self.path.exists() else empty()
        self.initial=not self.path.exists() and not model.state['days']
        self.capture();self.initial=False
    def stamp(self):
        stamps=[int(v['stamp'][:13])+1 for v in self.doc['fields'].values()]
        stamps.extend(int(s[:13])+1 for notes in self.doc['notes'].values() for s in notes)
        self.clock=max([int(time.time()*1000),self.clock+1]+stamps)
        return f'{self.clock:013}-{self.device}'
    def capture(self):
        def put(key,value):
            if key not in self.doc['fields'] or self.doc['fields'][key]['value']!=value:self.doc['fields'][key]={'value':value,'stamp':'0000000000000-default' if self.initial else self.stamp()}
        for key in ('start_date','interview_date'):put(key,self.model.settings[key])
        for day,record in self.model.state['days'].items():
            plan=self.model.plan(parse_date(day));done=self.model.done(plan)
            for task in plan.tasks:put(f'done:{day}:{task.id}',task.id in done)
            note=self.model.note(parse_date(day));notes=self.doc['notes'].setdefault(day,{})
            if note!=latest(notes):notes[self.stamp()]=note
        for day in self.model.state.get('unlocked_days',[]):put('unlock:'+day,True)
        atomic_json(self.path,self.doc)
        return deepcopy(self.doc)
    def apply(self,incoming):
        self.capture();combined=merge(self.doc,incoming)
        settings={key:combined['fields'][key]['value'] for key in ('start_date','interview_date') if key in combined['fields']}
        if any(self.model.settings.get(k)!=v for k,v in settings.items()):self.model.update_settings(settings)
        state=deepcopy(self.model.state);grants=set();days=set(combined['notes'])
        for key,item in combined['fields'].items():
            if key.startswith('done:'):days.add(key.split(':')[1])
            if key.startswith('unlock:') and item['value']:grants.add(key[7:])
        for day in days:
            plan=self.model.plan(parse_date(day));record=state['days'].setdefault(day,{})
            record['signature']=plan.signature
            record['done']=[task.id for task in plan.tasks if combined['fields'].get(f'done:{day}:{task.id}',{}).get('value',False)]
            if day in combined['notes']:record['note']=latest(combined['notes'][day])
        state['unlocked_days']=sorted(grants)
        changed=state!=self.model.state
        if changed:atomic_json(self.model.state_path,state,backup=True);self.model.state=state
        self.doc=combined;atomic_json(self.path,combined)
        return deepcopy(combined)

class GitHub:
    def __init__(self):self.token=None
    def credential(self):
        if self.token:return self.token
        token=os.environ.get('HANYANG_GITHUB_TOKEN')
        if not token:
            environment={**os.environ,'GCM_INTERACTIVE':'never','GIT_TERMINAL_PROMPT':'0'}
            result=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,timeout=15,env=environment,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if result.returncode:raise ValueError('GitHub 로그인이 필요합니다. Git Credential Manager 또는 HANYANG_GITHUB_TOKEN을 설정하세요.')
            token=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line).get('password')
        if not token:raise ValueError('GitHub 인증 정보를 찾지 못했습니다.')
        self.token=token;return token
    def request(self,path='',method='GET',body=None):
        if path not in ('','/contents/progress/state.json','/contents/progress/state.json?ref=study-progress'):raise ValueError('허용되지 않은 동기화 경로')
        if method not in ('GET','PUT'):raise ValueError('허용되지 않은 요청')
        if method=='PUT':
            if not self.request()['private']:raise ValueError('공개 저장소에는 기록을 저장하지 않습니다.')
            body={**body,'branch':'study-progress'}
        req=urllib.request.Request('https://api.github.com/repos/seung-ddak/Hanyang'+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers={'Authorization':'Bearer '+self.credential(),'Accept':'application/vnd.github+json','User-Agent':'Hanyang-Study','X-GitHub-Api-Version':'2022-11-28'})
        with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
    def sync(self,local):
        if not self.request()['private']:raise ValueError('공개 저장소에는 기록을 저장하지 않습니다.')
        for attempt in range(3):
            sha=None
            try:
                file=self.request('/contents/progress/state.json?ref=study-progress');sha=file['sha'];remote=json.loads(base64.b64decode(file['content']))
            except urllib.error.HTTPError as e:
                if e.code!=404:raise
                remote=empty()
            combined=merge(local,remote)
            if combined==remote:return combined
            body={'message':'Sync study progress','content':base64.b64encode(json.dumps(combined,ensure_ascii=False,indent=2).encode()).decode()}
            if sha:body['sha']=sha
            try:self.request('/contents/progress/state.json','PUT',body);return combined
            except urllib.error.HTTPError as e:
                if e.code not in (409,422) or attempt==2:raise
