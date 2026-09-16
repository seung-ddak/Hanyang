"""Local-only study dashboard. No phone connection or network reminders."""
from datetime import date, timedelta
import ctypes
import os
import tkinter as tk
from tkinter import messagebox, ttk
from study_widget_core import parse_date
from study_calendar import StudyCalendar, shift_month
from study_widget_view import BG, SURFACE, SURFACE_2, BORDER, TEXT, MUTED, MINT, AMBER, FONT, Card, Button, Check, Ring

TITLE='한양대 면접 · 오늘의 공부'
CATEGORIES={'recall':'복습','read':'교재 읽기','exercise':'문제 풀기','oral':'면접 연습','note':'메모 작성','review':'핵심 복습','research':'연구 설명','ready':'준비물 확인'}

class DashboardMixin:
    def __init__(self, root, model):
        self.root,self.model=root,model
        self.selected=self.last_today=date.today()
        if model.settings.get('sequential_unlock',False):self.selected=model.current_stage()
        self.calendar_month=self.selected.replace(day=1)
        self.note_timer=self.snooze_timer=self.midnight_timer=None
        self.notes=self.active_plan=None
        self.expanded_yesterday=False
        self.calendar_open=False;self.memo_open=False;self.expanded_task=None
        root.title(TITLE);root.configure(bg=BG);root.minsize(360,480)
        root.option_add('*Font',(FONT,10))
        style=ttk.Style(root);style.theme_use('clam')
        style.configure('Study.Vertical.TScrollbar',background=SURFACE_2,troughcolor=BG,bordercolor=BG,
                        arrowcolor=MUTED,darkcolor=BG,lightcolor=BG,arrowsize=10)
        style.map('Study.Vertical.TScrollbar',background=[('active',BORDER)])
        root.attributes('-topmost',model.settings['always_on_top'])
        width=410;height=min(660,root.winfo_screenheight()-100)
        root.geometry(f'{width}x{height}+{max(0,root.winfo_screenwidth()-width-24)}+40')
        mast=tk.Frame(root,bg=BG,padx=16,pady=10);mast.pack(fill='x')
        Button(mast,'설정',self.settings,height=28).pack(side='right')
        self.label(mast,'한양대 · 오늘의 공부',fg=MINT,font=(FONT,11,'bold'))
        footer=tk.Frame(root,bg=BG,padx=16,pady=8);footer.pack(side='bottom',fill='x')
        self.snooze_button=Button(footer,'나중에 다시 알림',self.snooze)
        self.snooze_button.pack(side='left')
        Button(footer,'닫기',self.close).pack(side='right')
        self.status=tk.Label(root,text='체크·메모 자동 저장 · 완료 후 버튼으로 다음 단계 해금',bg=BG,fg=MUTED,font=(FONT,8),wraplength=370)
        self.status.pack(side='bottom',fill='x',padx=16)
        shell=tk.Frame(root,bg=BG);shell.pack(fill='both',expand=True,padx=(16,6))
        self.canvas=tk.Canvas(shell,bg=BG,highlightthickness=0,yscrollincrement=24)
        scrollbar=ttk.Scrollbar(shell,orient='vertical',command=self.canvas.yview,style='Study.Vertical.TScrollbar')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y',padx=(6,0));self.canvas.pack(side='left',fill='both',expand=True)
        self.content=tk.Frame(self.canvas,bg=BG)
        self.canvas_id=self.canvas.create_window(0,0,window=self.content,anchor='nw')
        self.content.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',lambda e:self.resize_content(e.width))
        root.bind('<MouseWheel>',self.wheel)
        root.protocol('WM_DELETE_WINDOW',self.close);root.bind('<Map>',self.mapped)
        self.render()
        self.midnight_timer=root.after(30000,self.check_day)
        root.after_idle(self.dark_titlebar)
        if model.warnings:root.after(400,lambda:messagebox.showwarning('기록 확인','\n'.join(model.warnings),parent=root))

    def dark_titlebar(self):
        if os.name!='nt':return
        try:
            user=ctypes.WinDLL('user32');user.GetParent.argtypes=[ctypes.c_void_p];user.GetParent.restype=ctypes.c_void_p
            hwnd=user.GetParent(self.root.winfo_id())
            dwm=ctypes.WinDLL('dwmapi');dwm.DwmSetWindowAttribute.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint]
            value=ctypes.c_int(1);dwm.DwmSetWindowAttribute(hwnd,20,ctypes.byref(value),ctypes.sizeof(value))
        except (OSError,AttributeError):pass

    def label(self,parent,text,**kwargs):
        options=dict(bg=parent.cget('bg'),fg=TEXT,justify='left',anchor='w',font=(FONT,10))
        options.update(kwargs)
        label=tk.Label(parent,text=text,**options);label.pack(fill='x',pady=2)
        label.bind('<Configure>',lambda e:label.configure(wraplength=max(40,e.width-4)))
        return label

    def resize_content(self,width):
        self.canvas.itemconfigure(self.canvas_id,width=max(1,width))

    def show_date(self,day):
        if not self.flush_note():return
        self.selected=day;self.calendar_month=day.replace(day=1);self.render()
        self.root.after_idle(lambda:self.canvas.yview_moveto(0))

    def change_calendar_month(self,delta):
        if not self.flush_note():return
        self.calendar_month=shift_month(self.calendar_month,delta);self.render()

    def toggle_panel(self,name):
        if not self.flush_note():return
        setattr(self,name,not getattr(self,name));self.render()

    def toggle_detail(self,task_id):
        if not self.flush_note():return
        self.expanded_task=None if self.expanded_task==task_id else task_id
        self.render()

    def start_task(self,task):
        if self.model.is_locked(self.selected):return
        self.open_guide(task.id)

    def unlock_next(self):
        if not self.flush_note():return
        try:self.show_date(self.model.unlock_next(self.selected))
        except (OSError,ValueError) as e:messagebox.showinfo('단계 해금',str(e),parent=self.root)

    def task_name(self,task):
        if task.id=='recall' and self.selected==parse_date(self.model.settings['start_date']):
            return '학습 준비'
        return CATEGORIES.get(task.id,'공부')

    def render(self):
        position=self.canvas.yview()[0]
        for child in self.content.winfo_children():child.destroy()
        self.notes=None;self.checks={};self.yesterday_checks={}
        plan=self.active_plan=self.model.plan(self.selected)
        today=date.today();done=self.model.done(plan);remaining=self.model.remaining(plan)
        locked=self.model.is_locked(self.selected)
        nav=tk.Frame(self.content,bg=BG);nav.pack(fill='x',pady=(0,6))
        Button(nav,'‹',lambda:self.navigate(-1),width=28,height=28).pack(side='left')
        Button(nav,'›',lambda:self.navigate(1),width=28,height=28).pack(side='right')
        Button(nav,'내 진도',self.show_current,width=60,height=28).pack(side='right',padx=5)
        tk.Label(nav,text=f'{self.selected.month}/{self.selected.day} ({"월화수목금토일"[self.selected.weekday()]})',bg=BG,fg=TEXT,font=(FONT,10)).pack(side='left',padx=8)
        hero=Card(self.content,pad=12);hero.pack(fill='x',pady=(0,8))
        stage=(self.selected-parse_date(self.model.settings['start_date'])).days+1
        subtitle=f'{stage}단계' if stage>0 else '학습 시작 전'
        if locked:subtitle+=' · 잠김'
        elif self.selected<today and remaining:subtitle+=' · 밀린 공부부터'
        elif plan.tasks and not remaining:subtitle+=' · 완료'
        else:subtitle+=' · 지금 할 공부'
        self.label(hero.inner,subtitle,fg=AMBER if locked or (self.selected<today and remaining) else MINT,font=(FONT,8,'bold'))
        self.label(hero.inner,plan.title,font=(FONT,14,'bold'))
        self.label(hero.inner,f'{len(done)}/{len(plan.tasks)} 완료 · 남은 분량 {sum(t.minutes for t in remaining)}분',fg=MUTED,font=(FONT,8))
        progress=tk.Canvas(hero.inner,height=5,bg=SURFACE,highlightthickness=0)
        progress.pack(fill='x',pady=(5,0))
        def draw_progress(event):
            progress.delete('all');progress.create_rectangle(0,0,event.width,5,fill=BORDER,outline='')
            if plan.tasks:progress.create_rectangle(0,0,event.width*len(done)/len(plan.tasks),5,fill=MINT,outline='')
        progress.bind('<Configure>',draw_progress)
        if locked:
            gate=Card(self.content,pad=14);gate.pack(fill='x',pady=(0,10))
            first=self.model.current_stage(today)
            self.label(gate.inner,'이전 단계를 먼저 마쳐 주세요.',font=(FONT,11,'bold'),fg=AMBER)
            self.label(gate.inner,f'{first:%m/%d} 단계의 체크 목록을 모두 완료한 뒤 해금 버튼을 눌러 주세요. 날짜와 관계없이 이어갈 수 있어요.',fg=MUTED,font=(FONT,9))
            Button(gate.inner,'진행 중인 단계로 →',self.show_current,kind='primary').pack(fill='x',pady=(8,0))
        else:
            if remaining:
                task=remaining[0]
                Button(self.content,f'{self.task_name(task)} →',
                       lambda t=task:self.start_task(t),kind='primary',height=36).pack(fill='x',pady=(0,8))
            elif plan.tasks:Button(self.content,'다음 단계 해금 →',self.unlock_next,kind='primary').pack(fill='x',pady=(0,8))
            else:self.label(self.content,plan.subtitle,fg=MUTED,font=(FONT,9))
            previous=self.model.yesterday(today)
            if self.selected==today and previous:self.render_yesterday(previous)
            self.task_rows={}
            for task in plan.tasks:
                card=Card(self.content,pad=7);card.pack(fill='x',pady=2)
                self.task_rows[task.id]=card
                top=tk.Frame(card.inner,bg=SURFACE);top.pack(fill='x')
                var=tk.BooleanVar(value=task.id in done);self.checks[task.id]=var
                Check(top,var,lambda t=task:self.toggle(t.id),disabled=locked).pack(side='left')
                Button(top,self.task_name(task),lambda t=task:self.start_task(t),height=30,width=98).pack(side='left',padx=(4,0))
                tk.Label(top,text=f'{task.minutes}분',bg=SURFACE,fg=MUTED,font=(FONT,8)).pack(side='right',padx=6)
                is_next=bool(remaining and task.id==remaining[0].id)
                if is_next:tk.Label(top,text='지금',bg=SURFACE,fg=MINT,font=(FONT,8,'bold')).pack(side='right')
                if is_next or self.expanded_task==task.id:
                    self.label(card.inner,task.label,fg=MUTED if task.id in done else TEXT,font=(FONT,9))
        tools=tk.Frame(self.content,bg=BG);tools.pack(fill='x',pady=(10,6))
        Button(tools,'\uc9c0\uae08 \ub3d9\uae30\ud654',self.sync_now,height=30).pack(side='left',padx=4)
        self.calendar_button=Button(tools,'달력 접기' if self.calendar_open else '달력 ▾',lambda:self.toggle_panel('calendar_open'),height=30)
        self.calendar_button.pack(side='left')
        if not locked and plan.tasks:
            Button(tools,'메모 작성',lambda:self.open_guide('note'),height=30).pack(side='left',padx=5)
            Button(tools,'교재 목차',self.open_today,height=30).pack(side='right')
        self.calendar=StudyCalendar(self.content,self.model,self.calendar_month,self.selected,today,self.show_date,self.change_calendar_month)
        if self.calendar_open:self.calendar.pack(fill='x',pady=(0,8))
        extra=tk.Frame(self.content,bg=BG)
        if self.calendar_open:
            extra.pack(fill='x',pady=(0,6))
            backlog=self.model.backlog(today)
            if backlog:Button(extra,f'미완료 {len(backlog)}일 · 최근 7일',self.show_backlog,height=28).pack(side='left')
            exam=self.model.settings['interview_date']
            if exam:self.label(self.content,f'면접 {exam} · D{(today-parse_date(exam)).days:+d}',fg=MUTED,font=(FONT,8))
        self.snooze_button.set_text(f'{self.model.settings["snooze_minutes"]}분 뒤 알림')
        self.root.after_idle(lambda:self.canvas.yview_moveto(position))

    def render_yesterday(self,plan):
        remaining=self.model.remaining(plan)
        card=Card(self.content,fill='#29241f',border='#655039',pad=14);card.pack(fill='x',pady=(0,14))
        self.label(card.inner,f'어제 못 끝낸 공부  ·  {len(remaining)}개',fg=AMBER,font=(FONT,11,'bold'))
        self.label(card.inner,f'{plan.day:%m/%d}  {plan.title}',fg='#c3b6a5',font=(FONT,9))
        for task in remaining if self.expanded_yesterday else remaining[:2]:
            row=tk.Frame(card.inner,bg=card.fill);row.pack(fill='x',pady=5)
            var=tk.BooleanVar(value=False);self.yesterday_checks[task.id]=var
            Check(row,var,lambda t=task,v=var:self.toggle_previous(plan.day,t.id,v.get())).pack(side='left',anchor='n',padx=(0,8))
            self.label(row,f'{task.label}  ·  {task.minutes}분',font=(FONT,9),fg='#f0e4d6')
        actions=tk.Frame(card.inner,bg=card.fill);actions.pack(fill='x',pady=(8,0))
        if len(remaining)>2:Button(actions,'접기' if self.expanded_yesterday else f'미완료 {len(remaining)}개 모두 보기',self.expand_previous,height=30).pack(side='left')
        Button(actions,'어제 공부 열기 ↗',lambda:self.show_date(plan.day),height=30).pack(side='right')
        self.label(card.inner,'체크하면 어제 날짜에 완료로 기록돼요.',fg='#c3b6a5',font=(FONT,8))

    def expand_previous(self):
        if not self.flush_note():return
        self.expanded_yesterday=not self.expanded_yesterday;self.render()

    def toggle_previous(self,day,task_id,completed):
        if not self.flush_note():return
        try:self.model.mark_task(day,task_id,completed)
        except (OSError,ValueError) as e:messagebox.showerror('저장 실패',str(e),parent=self.root)
        self.render()

    def show_current(self):
        self.show_date(self.model.current_stage() if self.model.settings.get('sequential_unlock') else date.today())

    def popup(self,title):
        popup=tk.Toplevel(self.root);popup.title(title);popup.configure(bg=BG);popup.transient(self.root)
        popup.geometry(f'440x430+{max(0,self.root.winfo_x()-50)}+{self.root.winfo_y()+60}')
        frame=tk.Frame(popup,bg=BG,padx=22,pady=18);frame.pack(fill='both',expand=True)
        return popup,frame

    def show_backlog(self):
        popup,frame=self.popup('최근 7일 미완료')
        self.label(frame,'미뤄 둔 공부 이어하기',font=(FONT,16,'bold'))
        self.label(frame,'위젯을 처음 사용한 날 이후, 최근 7일만 표시해요.',fg=MUTED,font=(FONT,9))
        def choose(day):popup.destroy();self.show_date(day)
        for plan,count in self.model.backlog(date.today()):
            Button(frame,f'{plan.day:%m/%d}  ·  {count}개 남음  ·  {plan.title}',lambda d=plan.day:choose(d)).pack(fill='x',pady=4)

    def open_today(self):
        self.open_guide('read')

    def settings(self):
        popup,frame=self.popup('공부 위젯 설정');popup.geometry('440x560');popup.resizable(False,False)
        self.label(frame,'나의 공부 설정',font=(FONT,18,'bold'))
        self.label(frame,'일정과 PC 팝업을 내 생활에 맞춰요.',fg=MUTED,font=(FONT,9))
        entries={}
        for key,title in [('start_date','학습 시작일 · YYYY-MM-DD'),('interview_date','정확한 면접일 · 모르면 빈칸'),('snooze_minutes','다시 알림 간격 · 분')]:
            self.label(frame,title,fg=MUTED,font=(FONT,9),pady=6)
            entry=tk.Entry(frame,bg=SURFACE_2,fg=TEXT,insertbackground=MINT,relief='flat',font=(FONT,11))
            entry.insert(0,str(self.model.settings[key]));entry.pack(fill='x',ipady=8);entries[key]=entry
        row=tk.Frame(frame,bg=BG);row.pack(fill='x',pady=12)
        top=tk.BooleanVar(value=self.model.settings['always_on_top'])
        Check(row,top,lambda:None).pack(side='left');self.label(row,'다른 창보다 항상 위에 표시')
        self.label(frame,'시작일을 바꾸면 날짜별 공부 범위가 이동해요.\n범위가 달라진 날의 완료 체크는 다시 확인해요.',fg=MUTED,font=(FONT,9))
        self.label(frame,'순차 학습: 이전 단계 완료 후 다음 단계가 열려요.\n휴대폰·이메일 알림은 사용하지 않아요.',fg=MUTED,font=(FONT,9))
        def save():
            if not self.flush_note():return
            try:
                self.model.update_settings({'start_date':entries['start_date'].get().strip(),'interview_date':entries['interview_date'].get().strip(),
                    'snooze_minutes':int(entries['snooze_minutes'].get().strip()),'always_on_top':top.get()})
            except (ValueError,TypeError,OSError) as e:messagebox.showerror('설정 확인',str(e),parent=popup);return
            self.root.attributes('-topmost',top.get());popup.destroy();self.render();self.status.configure(text='설정을 저장했어요.')
        Button(frame,'설정 저장',save,kind='primary',height=42).pack(fill='x',pady=16)
