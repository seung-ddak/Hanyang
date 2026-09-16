"""Calendar and persistence for the study reminder; no GUI or third-party packages."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import os
import shutil

ROOT = Path(__file__).resolve().parent
DEFAULT_SETTINGS = {'start_date':'2026-09-16', 'interview_date':'',
                    'always_on_top':False, 'snooze_minutes':60, 'sequential_unlock':True}
GUIDE = ROOT / '한양대_컴퓨터소프트웨어_비전공자_면접교재.html'
PDF = ROOT / '한양대_컴퓨터소프트웨어_비전공자_면접교재.pdf'

def parse_date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('날짜는 YYYY-MM-DD 형식으로 입력하세요.')
    return parsed

def validate_settings(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError('설정 형식이 올바르지 않습니다.')
    result = {**DEFAULT_SETTINGS, **data}
    start = parse_date(result['start_date'])
    if result['interview_date']:
        if parse_date(result['interview_date']) < start:
            raise ValueError('면접일은 공부 시작일 이후여야 합니다.')
    if type(result['always_on_top']) is not bool:
        raise ValueError('항상 위 설정은 true 또는 false여야 합니다.')
    if type(result['sequential_unlock']) is not bool:
        raise ValueError('단계 잠금 설정은 true 또는 false여야 합니다.')
    if type(result['snooze_minutes']) is not int or not 1 <= result['snooze_minutes'] <= 1440:
        raise ValueError('다시 알림은 1~1440분 사이로 설정하세요.')
    return result

def atomic_json(path: Path, data: dict, backup: bool = False):
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    try:
        with temp.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if backup and path.exists():
            shutil.copy2(path, path.with_suffix(path.suffix + '.bak'))
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()

@dataclass(frozen=True)
class Task:
    id: str
    label: str
    minutes: int
    section: str

@dataclass(frozen=True)
class DayPlan:
    day: date
    title: str
    subtitle: str
    sections: tuple[str, ...]
    tasks: tuple[Task, ...]
    week: int | None
    day_number: int | None

    @property
    def signature(self):
        value = json.dumps([self.title, [(t.id, t.label, t.section) for t in self.tasks]], ensure_ascii=False)
        return hashlib.sha256(value.encode()).hexdigest()[:16]

class StudyModel:
    def __init__(self, root: Path = ROOT, today: date | None = None):
        self.root = Path(root)
        self.today = today or date.today()
        self.warnings = []
        self.settings_path = self.root/'study_widget_settings.json'
        self.state_path = self.root/'study_widget_state.json'
        self.settings = self._settings()
        data = json.loads((self.root/'study_schedule.json').read_text(encoding='utf-8-sig'))
        self.weeks = data['weeks']
        if len(self.weeks) != 7 or any(len(w['days']) != 7 for w in self.weeks):
            raise ValueError('학습 계획은 7주 × 7일이어야 합니다.')
        for week in self.weeks:
            for day in week['days']:
                if not day['sections'] or not all(isinstance(day[k], str) and day[k] for k in ['title','scope','exercise','oral']):
                    raise ValueError('학습 계획에 빈 항목이 있습니다.')
        self.state = self._state()

    def _preserve_corrupt(self, path):
        suffix = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        saved = path.with_name(path.stem + '.corrupt-' + suffix + '.json')
        shutil.copy2(path, saved)
        self.warnings.append(f'읽지 못한 파일을 {saved.name}에 보존했습니다.')

    def _settings(self):
        if not self.settings_path.exists():
            return deepcopy(DEFAULT_SETTINGS)
        try:
            return validate_settings(json.loads(self.settings_path.read_text(encoding='utf-8-sig')))
        except (ValueError, KeyError, TypeError):
            self._preserve_corrupt(self.settings_path)
            self.warnings.append('기본 일정으로 열었습니다. 설정에서 날짜를 확인하세요.')
            return deepcopy(DEFAULT_SETTINGS)

    def _state(self):
        if self.state_path.exists():
            try:
                state = json.loads(self.state_path.read_text(encoding='utf-8-sig'))
                if state['version'] != 1 or not isinstance(state['days'], dict):
                    raise ValueError('기록 버전 오류')
                parse_date(state['first_seen'])
                for day, entry in state['days'].items():
                    parse_date(day)
                    if not isinstance(entry, dict) or not isinstance(entry.get('done'), list) or not isinstance(entry.get('signature'), str):
                        raise ValueError('날짜별 기록 오류')
                    if not all(isinstance(v,str) for v in entry['done']):
                        raise ValueError('완료 기록 오류')
                return state
            except (ValueError, KeyError, TypeError):
                self._preserve_corrupt(self.state_path)
        state = {'version':1, 'first_seen':self.today.isoformat(), 'days':{}}
        atomic_json(self.state_path, state)
        return state

    def update_settings(self, values):
        settings = validate_settings({**self.settings, **values})
        atomic_json(self.settings_path, settings)
        self.settings = settings

    def plan(self, day: date) -> DayPlan:
        start = parse_date(self.settings['start_date'])
        # Plan dates identify curriculum stages; the interview date is a reminder.
        # It must not replace a future stage when studying ahead of the calendar.
        offset = (day-start).days
        if offset < 0:
            return DayPlan(day,'학습 시작 전이에요',f'{start.isoformat()}부터 7주 계획이 시작됩니다.',('roadmap',),(),None,None)
        week_index, day_index = divmod(offset,7)
        if week_index < 7:
            entry = self.weeks[week_index]['days'][day_index]
            title, scope = entry['title'], entry['scope']
            sections = tuple(entry['sections'])
            subtitle = f'{week_index+1}주차 · {day_index+1}일 / {self.weeks[week_index]["title"]}'
            exercise, oral = entry['exercise'], entry['oral']
            week, day_number = week_index+1, day_index+1
        else:
            groups=[('linear','trees','hashing'),('sorting','graphs'),('process','memory','synchronization'),
                    ('network',),('oop','database'),('discrete','extensions'),('research-bridge','mock')]
            sections=groups[(offset-49)%len(groups)]
            title='면접 직전 · 오답과 구술 복습'
            subtitle='7주 과정 이후 복습 · 정확한 면접일은 설정에서 입력'
            scope='오늘 연결된 장에서 설명이 막혔던 질문 2개 복습'
            exercise='오답 예제 1개를 새로운 숫자·조건으로 다시 풀기'
            oral='30초 답변 5개와 연구 설명 1회, 새 심화는 늘리지 않기'
            week,day_number=None,None
        tasks=(Task('recall','학습 목표와 현재 아는 내용을 세 문장으로 적기' if offset==0 else '이전 단계 내용을 덮고 기억나는 핵심 3개 말하기',10,sections[0]),
               Task('read',scope,30,sections[0]),Task('exercise',exercise,25,sections[0]),
               Task('oral',oral,15,sections[-1]),Task('note','막힌 질문과 내일 다시 볼 질문 1개 기록',10,sections[0]))
        return DayPlan(day,title,subtitle,sections,tasks,week,day_number)

    def done(self, plan: DayPlan) -> set[str]:
        record=self.state['days'].get(plan.day.isoformat(),{})
        if record.get('signature')!=plan.signature:
            return set()
        valid={t.id for t in plan.tasks}
        return set(record.get('done',[])) & valid

    def note(self, day: date) -> str:
        value=self.state['days'].get(day.isoformat(),{}).get('note','')
        return value if isinstance(value,str) else ''

    def record(self, plan: DayPlan, done: set[str], note: str | None = None):
        if self.is_locked(plan.day):
            raise ValueError('이전 단계를 완료하고 해금 버튼을 눌러 주세요.')
        state=deepcopy(self.state)
        record=state['days'].setdefault(plan.day.isoformat(),{})
        record.update({'signature':plan.signature,'done':sorted(done & {t.id for t in plan.tasks})})
        if note is not None: record['note']=note
        atomic_json(self.state_path,state,backup=True)
        self.state=state

    def backlog(self, today: date, limit=7):
        first=max(parse_date(self.state['first_seen']),parse_date(self.settings['start_date']),today-timedelta(days=limit))
        result=[]
        for n in range(max(0,(today-first).days)):
            plan=self.plan(first+timedelta(days=n))
            remaining=len(plan.tasks)-len(self.done(plan))
            if remaining:result.append((plan,remaining))
        return result

    def remaining(self, plan: DayPlan) -> tuple[Task, ...]:
        completed = self.done(plan)
        return tuple(task for task in plan.tasks if task.id not in completed)

    def current_stage(self, today: date | None = None) -> date:
        start=parse_date(self.settings['start_date'])
        grants=self.state.get('unlocked_days', [])
        day=start
        while not self.remaining(self.plan(day)) and self.plan(day).tasks:
            following=day+timedelta(days=1)
            if following.isoformat() not in grants:break
            day=following
        return day

    def is_locked(self, day: date, today: date | None = None) -> bool:
        start=parse_date(self.settings['start_date'])
        return day < start or day > self.current_stage(today)

    def unlock_next(self, day: date) -> date:
        plan=self.plan(day)
        if self.is_locked(day) or not plan.tasks or self.remaining(plan):
            raise ValueError('이전 단계의 체크 목록을 모두 완료해야 해금할 수 있어요.')
        following=day+timedelta(days=1)
        if not self.plan(following).tasks:
            raise ValueError('다음 학습 단계가 없습니다. 면접일 설정을 확인하세요.')
        state=deepcopy(self.state)
        grants=set(state.get('unlocked_days', []));grants.add(following.isoformat())
        state['unlocked_days']=sorted(grants)
        atomic_json(self.state_path,state,backup=True);self.state=state
        return following

    def unlocked_sections(self, today: date | None = None) -> set[str]:
        start=parse_date(self.settings['start_date']);last=self.current_stage(today)
        result={'roadmap'}
        for offset in range((last-start).days+1):
            result.update(self.plan(start+timedelta(days=offset)).sections)
        return result

    def calendar_status(self, day: date, today: date | None = None) -> str:
        """Calendar colors reflect widget checkmarks, not measured study time."""
        today = today or date.today()
        first = max(parse_date(self.state['first_seen']), parse_date(self.settings['start_date']))
        plan = self.plan(day)
        if day < first or not plan.tasks:
            return 'inactive'
        completed = self.done(plan)
        if len(completed) == len(plan.tasks):
            return 'complete'
        if day > today:
            return 'partial' if completed else 'future'
        if day == today:
            return 'today'
        return 'partial' if completed else 'missed'

    def yesterday(self, today: date) -> DayPlan | None:
        previous = today - timedelta(days=1)
        first = max(parse_date(self.state['first_seen']), parse_date(self.settings['start_date']))
        if previous < first:
            return None
        plan = self.plan(previous)
        return plan if self.remaining(plan) else None

    def mark_task(self, day: date, task_id: str, completed: bool):
        plan = self.plan(day)
        if task_id not in {task.id for task in plan.tasks}:
            raise ValueError('해당 날짜에 없는 항목입니다.')
        done = self.done(plan)
        if completed:
            done.add(task_id)
        else:
            done.discard(task_id)
        self.record(plan, done)

    def guide_url(self, section: str):
        path=self.root/GUIDE.name
        if not path.is_file():raise FileNotFoundError(f'교재를 찾지 못했습니다: {path}')
        if self.settings.get('sequential_unlock',False):
            from urllib.parse import urlencode
            sections=self.unlocked_sections()
            if section not in sections and section!='practice':
                raise ValueError('아직 잠긴 교재입니다. 현재 단계를 먼저 완료하세요.')
            return path.as_uri()+'?'+urlencode({'unlocked':','.join(sorted(sections))})+'#'+section
        return path.as_uri()+'#'+section
