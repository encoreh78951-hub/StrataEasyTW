"""Small Tk widgets; all UI mutation remains on the main thread."""
import re
import tkinter as tk
from tkinter import font as tkfont
C = {'bg':'#080B16','surface':'#11172A','panel':'#18203A','border':'#293653',
     'text':'#EDF5FF','muted':'#A1B2D0','cyan':'#63F3F7','pink':'#F173D9',
     'purple':'#B1A0FF','green':'#8FF3C7','warning':'#FFD28C','red':'#FF8CA8','terminal':'#060B13'}

def label(parent, text='', color='text', size=10, bold=False, **kw):
    return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=C.get(color,color),
        font=('Microsoft JhengHei UI',size,'bold' if bold else 'normal'),**kw)

def button(parent, text, command, primary=False, **kw):
    return tk.Button(parent,text=text,command=command,relief='flat',bd=0,
        bg=C['cyan'] if primary else C['panel'],fg=C['bg'] if primary else C['text'],
        activebackground=C['green'] if primary else C['border'],activeforeground=C['bg'] if primary else C['text'],
        font=('Microsoft JhengHei UI',10,'bold'),padx=13,pady=8,cursor='hand2',
        disabledforeground='#71809D',**kw)

class ScrollPanel(tk.Frame):
    def __init__(self,parent):
        super().__init__(parent,bg=C['surface'])
        self.canvas=tk.Canvas(self,bg=C['surface'],highlightthickness=0)
        scroll=tk.Scrollbar(self,command=self.canvas.yview)
        scroll.pack(side='right',fill='y'); self.canvas.pack(fill='both',expand=True)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.body=tk.Frame(self.canvas,bg=C['surface'],padx=18,pady=16)
        self.window=self.canvas.create_window((0,0),window=self.body,anchor='nw')
        self.wraps=[]
        self.body.bind('<Configure>',lambda _:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',self._resize)
        self.winfo_toplevel().bind('<MouseWheel>',self._wheel,add='+')
        self.winfo_toplevel().bind('<Button-4>',self._wheel,add='+')
        self.winfo_toplevel().bind('<Button-5>',self._wheel,add='+')
    def _resize(self,e):
        self.canvas.itemconfigure(self.window,width=e.width)
        for widget, subtract in self.wraps: widget.configure(wraplength=max(160,e.width-subtract))
    def _wheel(self,e):
        w=e.widget
        while w is not None:
            if w is self:
                delta=-1 if getattr(e,'num',None)==4 else 1 if getattr(e,'num',None)==5 else (-1 if e.delta>0 else 1)
                self.canvas.yview_scroll(delta*3,'units'); return 'break'
            w=getattr(w,'master',None)
    def text(self,text='',color='text',size=10,bold=False,gap=8):
        w=label(self.body,text,color,size,bold,wraplength=380,justify='left',anchor='w')
        w.pack(fill='x',pady=(0,gap)); self.wraps.append((w,42)); return w

ANSI={'black':'#101522','red':'#FA8BA1','green':'#8AE2AC','brown':'#F5D28D',
      'blue':'#8CB5FF','magenta':'#D39DFA','cyan':'#70E8E6','white':'#EDF5FF',
      'brightblack':'#94A5BF','brightred':'#FF9CB5','brightgreen':'#A5F6C2',
      'brightbrown':'#FFE3AA','brightblue':'#B0CFFF','brightmagenta':'#ECC2FF',
      'brightcyan':'#ACFFFF','brightwhite':'#FFFFFF'}
class TerminalView(tk.Frame):
    def __init__(self,parent,key_handler,resize_handler):
        super().__init__(parent,bg=C['terminal'])
        self.text=tk.Text(self,bg=C['terminal'],fg=C['text'],font=('Consolas',10),
            relief='flat',bd=0,padx=14,pady=12,wrap='none',state='disabled',
            insertbackground=C['cyan'],selectbackground='#355070',height=10)
        ys=tk.Scrollbar(self,command=self.text.yview)
        xs=tk.Scrollbar(self,orient='horizontal',command=self.text.xview)
        ys.pack(side='right',fill='y'); xs.pack(side='bottom',fill='x')
        self.text.pack(fill='both',expand=True)
        self.text.configure(yscrollcommand=ys.set,xscrollcommand=xs.set)
        self.text.bind('<Key>',key_handler)
        self.text.bind('<Button-1>',lambda _:self.text.focus_set(),add='+')
        self.text.bind('<Configure>',lambda e:resize_handler())
        self.tags={}
    def dimensions(self):
        font=tkfont.Font(font=self.text.cget('font'))
        return (max(8,(self.text.winfo_height()-24)//font.metrics('linespace')),
                max(40,(self.text.winfo_width()-28)//max(1,font.measure('M'))))
    def _tag(self,style):
        if style not in self.tags:
            if len(self.tags)>256: return ''
            fg,bg,bold,reverse=style
            def color(value,fallback):
                if value=='default':return fallback
                return ANSI.get(value,'#'+value if re.fullmatch('[a-fA-F0-9]{6}',value) else fallback)
            foreground,background=color(fg,C['text']),color(bg,C['terminal'])
            if reverse: foreground,background=background,foreground
            name='style'+str(len(self.tags))
            self.text.tag_configure(name,foreground=foreground,background=background,
                font=('Consolas',10,'bold' if bold else 'normal'))
            self.tags[style]=name
        return self.tags[style]
    def render(self,screen):
        y=self.text.yview(); follow=y[1]>.98
        selection=self.text.tag_ranges('sel')
        self.text.configure(state='normal');self.text.delete('1.0','end')
        for i,runs in enumerate(screen.snapshot()):
            if i:self.text.insert('end','\n')
            for text,style in runs:self.text.insert('end',text,self._tag(style))
        self.text.configure(state='disabled')
        if selection:self.text.tag_add('sel',*selection)
        if follow:self.text.see('end')
        else:self.text.yview_moveto(y[0])
