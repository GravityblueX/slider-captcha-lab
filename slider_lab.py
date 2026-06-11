from __future__ import annotations

import csv, json, math, os, random, socket, ssl, statistics, subprocess, sys, time, urllib.request, webbrowser
from dataclasses import dataclass, asdict
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception:
    plt = None
    FigureCanvasTkAgg = None

ROOT = Path(__file__).resolve().parent

@dataclass
class Point:
    x: float
    y: float
    t: float

# ---------------- trajectory engine ----------------
def _bezier(p0, p1, p2, p3, u):
    return (1-u)**3*p0 + 3*(1-u)**2*u*p1 + 3*(1-u)*u**2*p2 + u**3*p3

def _ease(u, mode):
    if mode == 'fast': return 1 - (1-u)**2.2
    if mode == 'hesitant':
        base = .5 - .5*math.cos(math.pi*u)
        return max(0, min(1, base + .018*math.sin(8*math.pi*u)))
    return .5 - .5*math.cos(math.pi*u)

def generate_trajectory(start=(0,0), end=(320,0), duration_ms=900, steps=90, jitter=1.6, mode='normal', overshoot=True, micro_pause=True):
    sx, sy = map(float, start); ex0, ey0 = map(float, end)
    dx, dy = ex0-sx, ey0-sy
    duration_ms = int(duration_ms * {'fast':.82, 'careful':1.22, 'hesitant':1.38}.get(mode, 1.0) * random.uniform(.94,1.08))
    jitter *= {'fast':1.15, 'careful':.85, 'hesitant':1.35}.get(mode, 1.0)
    ex, ey = ex0, ey0
    if overshoot and abs(dx) > 120 and random.random() < .72:
        ex += random.uniform(3, min(18, abs(dx)*.045)) * (1 if dx >= 0 else -1)
        ey += random.uniform(-2.5, 2.5)
    c1 = (sx + dx*random.uniform(.22,.35), sy + dy*.25 + random.uniform(-24,24))
    c2 = (sx + dx*random.uniform(.62,.82), sy + dy*.75 + random.uniform(-24,24))
    steps = max(8, int(steps)); pts=[]; pause_at=set(); time_offset=0; lx,ly=sx,sy
    if micro_pause:
        for _ in range({'fast':0,'normal':1,'careful':2,'hesitant':3}.get(mode,1)):
            pause_at.add(random.randint(max(2, steps//5), max(3, steps-steps//6)))
    for i in range(steps):
        u=i/(steps-1); e=_ease(u, mode); tremor=math.sin(math.pi*u)
        x=_bezier(sx,c1[0],c2[0],ex,e)+random.gauss(0,jitter*tremor)
        y=_bezier(sy,c1[1],c2[1],ey,e)+random.gauss(0,jitter*tremor)
        if i>0 and random.random()<.18:
            x=lx+(x-lx)*random.uniform(.82,1.08); y=ly+(y-ly)*random.uniform(.82,1.12)
        if i in pause_at: time_offset += random.uniform(35,130)
        t=max(0, duration_ms*e + time_offset + random.uniform(-5,5))
        pts.append(Point(x,y,t)); lx,ly=x,y
    if overshoot and (abs(ex-ex0)>.5 or abs(ey-ey0)>.5):
        ox,oy,bt=pts[-1].x,pts[-1].y,pts[-1].t
        for j in range(1, random.randint(4,9)+1):
            u=j/8; e=.5-.5*math.cos(math.pi*u)
            pts.append(Point(ox+(ex0-ox)*e+random.gauss(0,jitter*.25), oy+(ey0-oy)*e+random.gauss(0,jitter*.25), bt+35*j+random.uniform(-4,4)))
    pts[0]=Point(sx,sy,0); pts[-1]=Point(ex0,ey0,max(pts[-1].t,duration_ms))
    fixed=[]; last=-1
    for p in pts:
        t=max(p.t,last+random.uniform(4,18)); fixed.append(Point(p.x,p.y,t)); last=t
    fixed[0]=Point(sx,sy,0); return fixed

# ---------------- analysis ----------------
def analyze(points):
    if len(points)<3: return {'verdict':'insufficient_data','score':0}
    speeds=[]; dts=[]; dists=[]
    for a,b in zip(points, points[1:]):
        dt=max((b.t-a.t)/1000,1e-6); dist=math.hypot(b.x-a.x,b.y-a.y)
        speeds.append(dist/dt); dts.append(dt*1000); dists.append(dist)
    acc=[b-a for a,b in zip(speeds,speeds[1:])]; jerk=[b-a for a,b in zip(acc,acc[1:])]
    xs=abs(points[-1].x-points[0].x); path=sum(dists); yr=max(p.y for p in points)-min(p.y for p in points); dur=points[-1].t-points[0].t
    speed_std=statistics.pstdev(speeds) if len(speeds)>1 else 0; int_std=statistics.pstdev(dts) if len(dts)>1 else 0
    score=100
    if dur<250 or dur>3500: score-=20
    if path/max(xs,1)<1.002: score-=20
    if yr<1.2: score-=15
    if int_std<1: score-=15
    if speed_std<20: score-=15
    if max(speeds)>5000: score-=15
    if sum(1 for x in dts if x>45)==0 and dur>700: score-=5
    if (statistics.pstdev(jerk) if len(jerk)>1 else 0)==0: score-=10
    score=max(0,min(100,score))
    return {'score':round(score,2),'verdict':'natural_like_for_local_lab' if score>=75 else 'mixed_or_needs_review' if score>=45 else 'mechanical_or_anomalous','points':len(points),'duration_ms':round(dur,3),'x_span':round(xs,3),'path_length':round(path,3),'path_ratio':round(path/max(xs,1),5),'y_range':round(yr,3),'avg_speed_px_s':round(statistics.mean(speeds),3),'max_speed_px_s':round(max(speeds),3),'speed_std':round(speed_std,3),'interval_std_ms':round(int_std,3)}

def write_points(path, pts):
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['x','y','t_ms']); [w.writerow([round(p.x,3),round(p.y,3),round(p.t,3)]) for p in pts]

def read_points(path):
    pts=[]
    with open(path,newline='',encoding='utf-8-sig') as f:
        for r in csv.DictReader(f): pts.append(Point(float(r['x']),float(r['y']),float(r.get('t_ms',r.get('t',0)))))
    if pts:
        x0,y0,t0=pts[0].x,pts[0].y,pts[0].t; pts=[Point(p.x-x0,p.y-y0,p.t-t0) for p in pts]
    return pts

# ---------------- network diagnostics ----------------
def tls_diag(host='example.com'):
    ctx=ssl.create_default_context(); out={'host':host,'port':443}
    try: ctx.set_alpn_protocols(['h2','http/1.1'])
    except Exception: pass
    try:
        with socket.create_connection((host,443),timeout=8) as raw:
            with ctx.wrap_socket(raw,server_hostname=host) as s:
                cert=s.getpeercert(); out.update({'tls_version':s.version(),'cipher':s.cipher(),'selected_alpn':s.selected_alpn_protocol(),'cert_subject':cert.get('subject'),'cert_issuer':cert.get('issuer'),'not_before':cert.get('notBefore'),'not_after':cert.get('notAfter')})
    except Exception as e: out['error']=str(e)
    return out

def ip_context():
    res={}
    for name,url in [('ipify','https://api.ipify.org?format=json'),('ipapi','https://ipapi.co/json/')]:
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'SliderTrajectoryLab'}),timeout=8) as r: res[name]=json.loads(r.read().decode('utf-8','replace'))
        except Exception as e: res[name]={'error':str(e)}
    return res

# ---------------- GUI ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('Slider Trajectory Lab - Unified'); self.geometry('1180x780')
        self.points=[]; self.rec=[]; self.recording=False; self.t0=0
        nb=ttk.Notebook(self); nb.pack(fill=tk.BOTH,expand=True)
        self.tab_main=ttk.Frame(nb,padding=10); self.tab_rec=ttk.Frame(nb,padding=10); self.tab_test=ttk.Frame(nb,padding=10); self.tab_env=ttk.Frame(nb,padding=10); self.tab_about=ttk.Frame(nb,padding=10)
        for tab,name in [(self.tab_main,'轨迹生成与分析'),(self.tab_rec,'人工轨迹记录'),(self.tab_test,'本地滑块模拟'),(self.tab_env,'环境诊断'),(self.tab_about,'说明')]: nb.add(tab,text=name)
        self.build_main(); self.build_rec(); self.build_test(); self.build_env(); self.build_about(); self.generate()
    def build_main(self):
        left=ttk.Frame(self.tab_main); left.pack(side=tk.LEFT,fill=tk.Y); right=ttk.Frame(self.tab_main); right.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)
        self.distance=tk.IntVar(value=320); self.duration=tk.IntVar(value=900); self.steps=tk.IntVar(value=90); self.jitter=tk.DoubleVar(value=1.6); self.mode=tk.StringVar(value='normal')
        for label,var,a,b in [('滑动距离 px',self.distance,80,900),('持续时间 ms',self.duration,200,2500),('轨迹点数量',self.steps,10,300)]:
            ttk.Label(left,text=label).pack(anchor='w'); ttk.Spinbox(left,from_=a,to=b,textvariable=var,width=18).pack(anchor='w',pady=(0,8))
        ttk.Label(left,text='抖动强度').pack(anchor='w'); ttk.Spinbox(left,from_=0,to=8,increment=.1,textvariable=self.jitter,width=18).pack(anchor='w',pady=(0,8))
        ttk.Label(left,text='行为模式').pack(anchor='w'); ttk.Combobox(left,textvariable=self.mode,values=['normal','careful','fast','hesitant'],state='readonly',width=16).pack(anchor='w',pady=(0,8))
        for txt,cmd in [('生成轨迹',self.generate),('导入CSV分析',self.import_csv),('导出CSV',self.export_csv),('导出PNG',self.export_png),('批量生成CSV',self.batch)]: ttk.Button(left,text=txt,command=cmd).pack(fill=tk.X,pady=4)
        self.output=tk.Text(left,width=38,height=28); self.output.pack(fill=tk.BOTH,expand=True,pady=8)
        if plt and FigureCanvasTkAgg:
            self.fig,self.axes=plt.subplots(3,1,figsize=(8,6.8),dpi=100); self.canvas=FigureCanvasTkAgg(self.fig,master=right); self.canvas.get_tk_widget().pack(fill=tk.BOTH,expand=True)
        else: ttk.Label(right,text='缺少 matplotlib：pip install matplotlib').pack()
    def build_rec(self):
        bar=ttk.Frame(self.tab_rec); bar.pack(fill=tk.X)
        for txt,cmd in [('开始记录',self.start_rec),('停止记录',self.stop_rec),('用于分析',self.use_rec),('保存CSV',self.save_rec),('清空',self.clear_rec)]: ttk.Button(bar,text=txt,command=cmd).pack(side=tk.LEFT,padx=4)
        self.rec_status=ttk.Label(bar,text='在画布中按住鼠标拖动以记录人工轨迹'); self.rec_status.pack(side=tk.LEFT,padx=12)
        self.rec_canvas=tk.Canvas(self.tab_rec,bg='#f8fafc'); self.rec_canvas.pack(fill=tk.BOTH,expand=True,pady=10)
        self.rec_canvas.bind('<ButtonPress-1>',self.rec_down); self.rec_canvas.bind('<ButtonRelease-1>',self.rec_up); self.rec_canvas.bind('<Motion>',self.rec_move)
    def build_test(self):
        top=ttk.Frame(self.tab_test); top.pack(fill=tk.X); ttk.Button(top,text='用当前轨迹运行本地滑块模拟',command=self.run_local_slider).pack(side=tk.LEFT,padx=4); ttk.Button(top,text='重新生成并运行',command=lambda:(self.generate(),self.run_local_slider())).pack(side=tk.LEFT,padx=4)
        self.test_canvas=tk.Canvas(self.tab_test,bg='#f6f7fb',height=420); self.test_canvas.pack(fill=tk.BOTH,expand=True,pady=10); self.draw_slider(0)
    def build_env(self):
        bar=ttk.Frame(self.tab_env); bar.pack(fill=tk.X); self.host=tk.StringVar(value='example.com')
        ttk.Label(bar,text='TLS/HTTP2测试Host').pack(side=tk.LEFT); ttk.Entry(bar,textvariable=self.host,width=28).pack(side=tk.LEFT,padx=6)
        ttk.Button(bar,text='运行网络诊断',command=self.run_net).pack(side=tk.LEFT,padx=4); ttk.Button(bar,text='打开浏览器事件/指纹诊断页',command=self.open_diag_page).pack(side=tk.LEFT,padx=4)
        self.env_out=tk.Text(self.tab_env); self.env_out.pack(fill=tk.BOTH,expand=True,pady=10)
    def build_about(self):
        t=tk.Text(self.tab_about,wrap=tk.WORD); t.pack(fill=tk.BOTH,expand=True); t.insert(tk.END,'本工具将轨迹生成、人工记录、本地滑块模拟、事件/指纹诊断、TLS/HTTP2/IP上下文诊断合并到一个桌面应用。\n\n目标：研究和验证本地/授权环境中的人类鼠标轨迹模拟、事件完整性和环境信号，不针对第三方真实网站绕过访问控制。\n'); t.config(state=tk.DISABLED)
    def generate(self):
        self.points=generate_trajectory((0,0),(self.distance.get(),0),self.duration.get(),self.steps.get(),self.jitter.get(),self.mode.get()); self.plot(); self.show_analysis()
    def show_analysis(self):
        self.output.delete('1.0',tk.END); self.output.insert(tk.END,'分析结果\n========================\n'); [self.output.insert(tk.END,f'{k}: {v}\n') for k,v in analyze(self.points).items()]
    def plot(self):
        if not (plt and FigureCanvasTkAgg) or not self.points: return
        for ax in self.axes: ax.clear()
        xs=[p.x for p in self.points]; ys=[p.y for p in self.points]; ts=[p.t for p in self.points]; speeds=[0]
        for a,b in zip(self.points,self.points[1:]): speeds.append(math.hypot(b.x-a.x,b.y-a.y)/max((b.t-a.t)/1000,1e-6))
        acc=[0]+[b-a for a,b in zip(speeds,speeds[1:])]
        self.axes[0].plot(xs,ys,marker='o',markersize=2); self.axes[0].set_title('Trajectory path'); self.axes[0].grid(alpha=.25)
        self.axes[1].plot(ts,speeds); self.axes[1].set_title('Speed curve'); self.axes[1].grid(alpha=.25)
        self.axes[2].plot(ts,acc); self.axes[2].set_title('Acceleration delta'); self.axes[2].grid(alpha=.25); self.fig.tight_layout(); self.canvas.draw()
    def import_csv(self):
        p=filedialog.askopenfilename(filetypes=[('CSV','*.csv')]);
        if p: self.points=read_points(p); self.plot(); self.show_analysis()
    def export_csv(self):
        p=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')]);
        if p: write_points(p,self.points); messagebox.showinfo('完成',p)
    def export_png(self):
        if not hasattr(self,'fig'): return
        p=filedialog.asksaveasfilename(defaultextension='.png',filetypes=[('PNG','*.png')]);
        if p: self.fig.savefig(p,dpi=160); messagebox.showinfo('完成',p)
    def batch(self):
        d=filedialog.askdirectory();
        if not d: return
        for i in range(30): write_points(str(Path(d)/f'trajectory_{i+1:03d}.csv'), generate_trajectory((0,0),(self.distance.get(),0),self.duration.get(),self.steps.get(),self.jitter.get(),self.mode.get()))
        messagebox.showinfo('完成','已批量生成30条轨迹')
    def start_rec(self): self.rec=[]; self.rec_canvas.delete('all'); self.t0=time.perf_counter(); self.recording=True; self.rec_status.config(text='记录中')
    def stop_rec(self): self.recording=False; self.rec_status.config(text=f'停止，点数：{len(self.rec)}')
    def clear_rec(self): self.rec=[]; self.rec_canvas.delete('all')
    def rec_down(self,e):
        if not self.recording: self.start_rec()
        self.add_rec(e.x,e.y)
    def rec_up(self,e): self.add_rec(e.x,e.y); self.stop_rec()
    def rec_move(self,e):
        if self.recording: self.add_rec(e.x,e.y)
    def add_rec(self,x,y):
        if self.rec: self.rec_canvas.create_line(self.rec[-1].x,self.rec[-1].y,x,y,fill='#2563eb',width=2)
        self.rec.append(Point(float(x),float(y),(time.perf_counter()-self.t0)*1000)); self.rec_status.config(text=f'记录中，点数：{len(self.rec)}')
    def use_rec(self):
        if not self.rec: return
        x0,y0,t0=self.rec[0].x,self.rec[0].y,self.rec[0].t; self.points=[Point(p.x-x0,p.y-y0,p.t-t0) for p in self.rec]; self.plot(); self.show_analysis()
    def save_rec(self):
        p=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')]);
        if p: write_points(p,self.rec)
    def draw_slider(self,pos):
        c=self.test_canvas; c.delete('all'); w=max(c.winfo_width(),900); y=200; x0=120; x1=w-120
        c.create_rectangle(x0,y-18,x1,y+18,fill='#e5e7eb',outline=''); c.create_rectangle(x0,y-18,x0+pos,y+18,fill='#93c5fd',outline=''); c.create_oval(x0+pos-22,y-22,x0+pos+22,y+22,fill='white',outline='#2563eb',width=2); c.create_text(w/2,90,text='本地滑块模拟：验证生成轨迹在本地控件上的拖动效果',font=('Segoe UI',14))
    def run_local_slider(self):
        if not self.points: self.generate()
        maxpos=max(p.x for p in self.points) or 1
        for p in self.points:
            self.draw_slider(int((p.x/maxpos)*(max(self.test_canvas.winfo_width(),900)-240))); self.update(); time.sleep(0.006)
    def open_diag_page(self):
        p=ROOT/'demo'/'event_diagnostics.html'; webbrowser.open(p.as_uri())
    def run_net(self):
        self.env_out.delete('1.0',tk.END); data={'tls_http2':tls_diag(self.host.get().strip() or 'example.com'),'public_ip_context':ip_context(),'note':'TLS/HTTP2/IP为诊断观测，不进行伪装或绕过。'}; self.env_out.insert(tk.END,json.dumps(data,ensure_ascii=False,indent=2,default=str))

if __name__=='__main__': App().mainloop()
