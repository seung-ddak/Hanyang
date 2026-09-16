"""Small custom-painted widgets for a modern, dependency-free Tk dashboard."""
import tkinter as tk
import tkinter.font as tkfont

BG='#0d121c'
SURFACE='#171e2b'
SURFACE_2='#202a3b'
BORDER='#2c3749'
TEXT='#edf2fb'
MUTED='#9aa9bf'
MINT='#9aefce'
AMBER='#f6c98c'
FONT='맑은 고딕'

def rounded(canvas,x1,y1,x2,y2,r=16,**kwargs):
    r=min(r,(x2-x1)/2,(y2-y1)/2)
    return canvas.create_polygon(x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,
                                 x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,
                                 x1,y2,x1,y2-r,x1,y1+r,x1,y1,smooth=True,**kwargs)

class Card(tk.Canvas):
    def __init__(self,parent,fill=SURFACE,pad=16,border=BORDER,**kwargs):
        super().__init__(parent,bg=parent.cget('bg'),bd=0,highlightthickness=0,**kwargs)
        self.fill,self.pad,self.border=fill,pad,border
        self.inner=tk.Frame(self,bg=fill)
        self.window=self.create_window(pad,pad,window=self.inner,anchor='nw')
        self.bind('<Configure>',self.layout)
        self.inner.bind('<Configure>',self.fit)
    def fit(self,event=None):
        height=self.inner.winfo_reqheight()+self.pad*2
        if int(self.cget('height'))!=height:self.configure(height=height)
        self.layout()
    def layout(self,event=None):
        w=max(40,self.winfo_width());h=max(20,self.winfo_height())
        self.itemconfigure(self.window,width=max(1,w-self.pad*2))
        self.delete('shape')
        rounded(self,1,1,w-1,h-1,18,fill=self.fill,outline=self.border,tags='shape')
        self.tag_lower('shape')

class Button(tk.Canvas):
    def __init__(self,parent,text,command,kind='quiet',width=None,height=36,**kwargs):
        self.text,self.command,self.kind=text,command,kind
        self.font=tkfont.Font(family=FONT,size=9,weight='bold' if kind=='primary' else 'normal')
        self.hover=False
        super().__init__(parent,width=width or self.font.measure(text)+28,height=height,
                         bg=parent.cget('bg'),highlightthickness=0,bd=0,takefocus=1,cursor='hand2',**kwargs)
        self.bind('<Configure>',lambda e:self.paint())
        self.bind('<Enter>',lambda e:self.set_hover(True));self.bind('<Leave>',lambda e:self.set_hover(False))
        self.bind('<Button-1>',lambda e:self.invoke())
        self.bind('<space>',lambda e:self.invoke());self.bind('<Return>',lambda e:self.invoke())
        self.bind('<FocusIn>',lambda e:self.paint());self.bind('<FocusOut>',lambda e:self.paint())
    def invoke(self):
        if self.command:self.command()
    def set_hover(self,value):self.hover=value;self.paint()
    def set_text(self,text):self.text=text;self.paint()
    def paint(self):
        self.delete('all');w=max(1,self.winfo_width());h=max(1,self.winfo_height())
        if self.kind=='primary':fill='#b5ffdf' if self.hover else MINT;fg=BG
        else:fill='#2d3a4f' if self.hover else SURFACE_2;fg=TEXT
        border=MINT if self.focus_get()==self else fill
        rounded(self,1,1,w-1,h-1,10,fill=fill,outline=border)
        self.create_text(w/2,h/2,text=self.text,fill=fg,font=self.font)

class Check(tk.Canvas):
    def __init__(self,parent,variable,command,disabled=False):
        self.var,self.command,self.disabled=variable,command,disabled
        super().__init__(parent,width=30,height=32,bg=parent.cget('bg'),bd=0,highlightthickness=0,
                         takefocus=0 if disabled else 1,cursor='arrow' if disabled else 'hand2')
        self.bind('<Configure>',lambda e:self.paint())
        self.bind('<Button-1>',lambda e:self.invoke());self.bind('<space>',lambda e:self.invoke())
        self.bind('<Return>',lambda e:self.invoke())
        self.bind('<FocusIn>',lambda e:self.paint());self.bind('<FocusOut>',lambda e:self.paint())
    def invoke(self):
        if not self.disabled:self.var.set(not self.var.get());self.command()
    def paint(self):
        self.delete('all')
        selected=self.var.get()
        rounded(self,3,6,25,28,6,fill=MINT if selected else SURFACE,
                outline=MINT if selected or self.focus_get()==self else BORDER,width=2)
        if selected:self.create_line(8,17,12,21,20,12,fill=BG,width=2.3,capstyle='round',joinstyle='round')

class Ring(tk.Canvas):
    def __init__(self,parent,done,total):
        super().__init__(parent,width=106,height=106,bg=parent.cget('bg'),highlightthickness=0,bd=0)
        self.create_oval(9,9,97,97,outline=BORDER,width=7)
        fraction=done/total if total else 0
        if fraction>=1:self.create_oval(9,9,97,97,outline=MINT,width=7)
        elif fraction>0:self.create_arc(9,9,97,97,start=90,extent=-360*fraction,style='arc',outline=MINT,width=7)
        self.create_text(53,44,text=f'{round(fraction*100)}',font=('Segoe UI',24,'bold'),fill=TEXT)
        self.create_text(53,71,text='PERCENT',font=('Segoe UI',7,'bold'),fill=MUTED)
