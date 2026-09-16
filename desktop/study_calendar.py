"""Monthly progress calendar, rendered locally from the widget's checkmarks."""
import calendar
from datetime import date
import tkinter as tk
from study_widget_view import Card, Button, rounded, SURFACE, SURFACE_2, TEXT, MUTED, MINT, BORDER, FONT

ROSE='#f4c9cd'
ROSE_INK='#75333b'

def shift_month(day, delta):
    index=(day.year-1)*12+day.month-1+delta
    index=max(0,min(9999*12-1,index))
    year,month=divmod(index,12)
    return date(year+1,month+1,1)

class CalendarDay(Button):
    def __init__(self,parent,day,status,completed,total,selected,today,command,locked=False):
        self.day,self.status,self.completed,self.total=day,status,completed,total
        self.selected,self.today=selected,today
        self.locked=locked
        super().__init__(parent,str(day.day),command,width=44,height=46)

    def paint(self):
        self.delete('all');w=max(1,self.winfo_width());h=max(1,self.winfo_height())
        if self.status in ('missed','partial'):fill=ROSE;fg=ROSE_INK
        elif self.status=='complete':fill='#234439';fg=MINT
        else:fill=SURFACE_2;fg=MUTED if self.status in ('inactive','future') else TEXT
        outline=MINT if self.day==self.today else BORDER
        if self.selected or self.hover or self.focus_get()==self:outline=TEXT
        rounded(self,2,2,w-2,h-2,8,fill=fill,outline=outline,width=2 if self.selected or self.day==self.today else 1)
        self.create_text(w/2,14,text=str(self.day.day),fill=fg,font=('Segoe UI',10,'bold'))
        caption={'missed':'미학습','partial':f'{self.completed}/{self.total}','complete':'완료','today':'오늘'}.get(self.status,'')
        if self.status=='today' and self.completed:caption=f'{self.completed}/{self.total}'
        if self.locked:caption='잠김'
        self.create_text(w/2,33,text=caption,fill=fg,font=(FONT,7))

class StudyCalendar(Card):
    def __init__(self,parent,model,month,selected,today,on_select,on_month):
        super().__init__(parent,pad=12)
        self.days={}
        header=tk.Frame(self.inner,bg=SURFACE);header.pack(fill='x',pady=(0,8))
        Button(header,'‹',lambda:on_month(-1),width=28,height=28).pack(side='left')
        Button(header,'›',lambda:on_month(1),width=28,height=28).pack(side='right')
        tk.Label(header,text=f'{month.year}년 {month.month}월 · 학습 달력',bg=SURFACE,fg=TEXT,font=(FONT,11,'bold')).pack(expand=True)
        grid=tk.Frame(self.inner,bg=SURFACE);grid.pack(fill='x')
        for column,title in enumerate('월화수목금토일'):
            grid.columnconfigure(column,weight=1,uniform='day')
            tk.Label(grid,text=title,bg=SURFACE,fg=MUTED,font=(FONT,8)).grid(row=0,column=column,pady=(0,4))
        for row,week in enumerate(calendar.Calendar(firstweekday=0).monthdayscalendar(month.year,month.month),1):
            for column,number in enumerate(week):
                if not number:continue
                day=date(month.year,month.month,number);plan=model.plan(day)
                cell=CalendarDay(grid,day,model.calendar_status(day,today),len(model.done(plan)),len(plan.tasks),
                                 day==selected,today,lambda d=day:on_select(d),model.is_locked(day,today))
                cell.grid(row=row,column=column,sticky='ew',padx=1,pady=1)
                self.days[day]=cell
        legend=tk.Frame(self.inner,bg=SURFACE);legend.pack(fill='x',pady=(9,0))
        for color,text in [(ROSE,'미학습·일부 미완료'),(MINT,'완료')]:
            tk.Label(legend,text='●',bg=SURFACE,fg=color,font=(FONT,9)).pack(side='left')
            tk.Label(legend,text=text,bg=SURFACE,fg=MUTED,font=(FONT,8)).pack(side='left',padx=(0,10))
        tk.Label(self.inner,text='지난 날짜의 완료 체크 기준 · 날짜를 눌러 확인',bg=SURFACE,fg=MUTED,font=(FONT,8),anchor='w').pack(fill='x',pady=(4,0))
