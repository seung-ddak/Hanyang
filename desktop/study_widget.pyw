"""Windows login study widget. Python + the bundled Tk only; no server/network."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
from datetime import date, timedelta
import hashlib
import os
import tkinter as tk
from tkinter import messagebox
import traceback
import webbrowser

from study_widget_core import ROOT, StudyModel
from study_dashboard import DashboardMixin

TITLE='한양대 면접 · 오늘의 공부'

def single_instance():
    if os.name!='nt':return None
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
    kernel.CreateMutexW.restype=wintypes.HANDLE
    name='Local\\HanyangStudyWidget_'+hashlib.sha256(str(ROOT).lower().encode()).hexdigest()[:16]
    handle=kernel.CreateMutexW(None,False,name)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error()==183:
        user=ctypes.WinDLL('user32',use_last_error=True)
        user.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR]
        user.FindWindowW.restype=wintypes.HWND
        user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
        user.SetForegroundWindow.argtypes=[wintypes.HWND]
        hwnd=user.FindWindowW(None,TITLE)
        if hwnd:user.ShowWindow(hwnd,9);user.SetForegroundWindow(hwnd)
        kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle(handle)
        return False
    return handle

class StudyWidgetBase:
    """Shared progress persistence, guide links and window lifecycle."""

    def wheel(self,event):
        if event.widget.winfo_class() not in ('Text','Entry','TEntry'):
            self.canvas.yview_scroll(int(-event.delta/120),'units')

    def toggle(self,task_id):
        if self.model.is_locked(self.selected):return
        plan=self.active_plan;done=self.model.done(plan)
        if self.checks[task_id].get():done.add(task_id)
        else:done.discard(task_id)
        note=self.notes.get('1.0','end-1c') if self.notes else None
        try:
            self.cancel_note();self.model.record(plan,done,note);self.status.configure(text='완료 상태를 저장했어요.')
        except (OSError,ValueError) as e:messagebox.showerror('저장 실패',str(e),parent=self.root)
        self.render()

    def cancel_note(self):
        if self.note_timer:self.root.after_cancel(self.note_timer);self.note_timer=None

    def queue_note(self,event=None):
        self.cancel_note();self.note_timer=self.root.after(600,self.flush_note)

    def flush_note(self):
        self.cancel_note()
        if self.notes and self.active_plan:
            text=self.notes.get('1.0','end-1c')
            if text!=self.model.note(self.selected):
                try:self.model.record(self.active_plan,self.model.done(self.active_plan),text)
                except (OSError,ValueError) as e:
                    messagebox.showerror('메모 저장 실패',str(e),parent=self.root);return False
        return True

    def navigate(self,n):self.show_date(self.selected+timedelta(days=n))

    def show_date(self,day):
        if not self.flush_note():return
        self.selected=day;self.render();self.canvas.yview_moveto(0)

    def open_guide(self,section):
        if self.model.is_locked(self.selected):
            messagebox.showinfo('단계 잠금','먼저 이전 단계를 완료하세요.',parent=self.root);return
        try:
            if not webbrowser.open(self.study_server.url(self.selected,section)):
                messagebox.showinfo('교재 경로',self.study_server.url(self.selected,section),parent=self.root)
        except (OSError,ValueError) as e:messagebox.showerror('교재 열기 실패',str(e),parent=self.root)

    def snooze(self):
        if not self.flush_note():return
        if self.snooze_timer:self.root.after_cancel(self.snooze_timer)
        mins=self.model.settings['snooze_minutes']
        self.status.configure(text=f'{mins}분 뒤 다시 열립니다. 절전 중이면 깨어난 뒤 표시됩니다.')
        self.root.withdraw();self.snooze_timer=self.root.after(mins*60000,self.wake)

    def mapped(self,event):
        if event.widget==self.root and self.snooze_timer:
            self.root.after_cancel(self.snooze_timer);self.snooze_timer=None

    def wake(self):
        self.snooze_timer=None;self.show_current()
        self.root.deiconify();self.root.lift()

    def check_day(self):
        today=date.today()
        if today!=self.last_today:
            old=self.last_today;self.last_today=today
            if self.model.settings.get('sequential_unlock'):self.show_current()
            elif self.selected==old:self.show_date(today)
            else:
                if self.flush_note():self.render()
        self.midnight_timer=self.root.after(30000,self.check_day)

    def close(self):
        if not self.flush_note():return
        if self.snooze_timer:self.root.after_cancel(self.snooze_timer)
        if self.midnight_timer:self.root.after_cancel(self.midnight_timer)
        if hasattr(self,"study_server"):self.study_server.close()
        self.root.destroy()

class StudyWidget(DashboardMixin, StudyWidgetBase):
    """Modern presentation with the existing local progress and lifecycle logic."""

def main():
    handle=single_instance()
    if handle is False:return
    root=None
    try:
        model=StudyModel();root=tk.Tk();widget=StudyWidget(root,model)
        from study_server import StudyServer
        widget.study_server=StudyServer(model)
        def refresh():
            if widget.study_server.drain():widget.render()
            widget.status.configure(text=widget.study_server.sync_status)
            root.after(150,refresh)
        root.after(150,refresh)
        root.mainloop()
    except Exception:
        error=traceback.format_exc()
        (ROOT/'study_widget_error.log').write_text(error,encoding='utf-8')
        if root is None:root=tk.Tk();root.withdraw()
        messagebox.showerror('공부 위젯 실행 오류','실행하지 못했습니다. study_widget_error.log를 확인하세요.\n\n'+error[-800:],parent=root)
        root.destroy()
    finally:
        if handle and os.name=='nt':
            kernel=ctypes.WinDLL('kernel32');kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle(handle)

if __name__=='__main__':main()
