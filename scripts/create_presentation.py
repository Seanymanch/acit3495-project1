"""Generate editable project presentation. Populate numeric fields only from actual measurements."""
import csv
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence';O=ROOT/'docs/Project2_Presentation.pptx'
NAVY=RGBColor(21,43,77);INK=RGBColor(42,54,71);GREY=RGBColor(100,116,139)
BLUE=RGBColor(40,106,191);LIGHT=RGBColor(235,243,255);WHITE=RGBColor(255,255,255)

def shape(slide,x,y,w,h,fill=LIGHT):
    obj=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    obj.fill.solid();obj.fill.fore_color.rgb=fill;obj.line.fill.background();return obj

def text(slide,s,x,y,w,h,size=18,bold=False,color=INK,align=None):
    tx=slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf=tx.text_frame;tf.word_wrap=True
    tf.margin_left=Inches(.08);tf.margin_right=Inches(.08);tf.margin_top=Inches(.02)
    tf.clear()
    for i,line in enumerate(str(s).split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.text=line;p.font.name='Aptos';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=color
        if align:p.alignment=align
    return tx

def base(prs,title,n):
    slide=prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid();slide.background.fill.fore_color.rgb=WHITE
    shape(slide,.45,.38,.13,.55,BLUE)
    text(slide,title,.82,.35,11.3,.62,30,True,NAVY)
    text(slide,f'ACIT 3495  •  PROJECT 2',.6,7.05,6,.22,9,False,GREY)
    text(slide,f'{n} / 8',11.9,7.05,.8,.22,9,False,GREY)
    return slide

def section(slide,title,body,x,y,w,h):
    shape(slide,x,y,w,h)
    text(slide,title,x+.16,y+.1,w-.32,.4,20,True,NAVY)
    text(slide,body,x+.15,y+.58,w-.3,h-.7,15,False,INK)

def getdata():
    p=E/'performance-summary.csv'
    if not p.exists():return {}
    with p.open(encoding='utf-8') as f:return {r['scenario']:r for r in csv.DictReader(f)}

def num(x,key,unit=''):
    if x is None or not x.get(key):return 'PENDING'
    try:return f'{float(x[key]):.2f}{unit}'
    except (ValueError,TypeError):return 'PENDING'

def main():
    data=getdata();prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    s=base(prs,'Cloud Deployment + Horizontal Scalability',1)
    text(s,'AWS EKS  |  Kubernetes  |  HPA  |  k6',.8,1.15,11,.6,22,False,BLUE)
    section(s,'Project objective','Move the six-container Project 1 temperature application to public-cloud Kubernetes and measure real automatic scaling.',.8,2.1,11.75,1.55)
    section(s,'Live demonstration','Real working app, HPA scaling events, CPU/replica logs and three measured traffic levels.',.8,4,11.75,1.55)
    s=base(prs,'Cloud architecture',2)
    img=ROOT/'docs/architecture.png'
    if img.exists():s.shapes.add_picture(str(img),Inches(2.1),Inches(1.14),width=Inches(9.1))
    s=base(prs,'Kubernetes infrastructure',3)
    section(s,'Microservices','Four app Deployments + Services: Enter Data, Auth, Analytics and Show Results.',.75,1.45,5.75,1.85)
    section(s,'Persistent data','MySQL 8.4 + MongoDB 7 StatefulSets; encrypted EBS gp3 claims, one database pod each.',6.8,1.45,5.75,1.85)
    section(s,'Reliability','Startup, readiness and liveness probes; memory/CPU requests and limits; private backend Services.',.75,3.65,5.75,1.85)
    section(s,'Public-cloud setup','AWS EKS in us-west-2, worker nodes and AWS resource Metrics Server.',6.8,3.65,5.75,1.85)
    s=base(prs,'Horizontal Pod Autoscaler',4)
    section(s,'Selected backend','Auth FastAPI service; real PBKDF2 password verification is CPU-intensive.',.7,1.45,5.7,2.05)
    section(s,'HPA policy','Min 1 pod  |  Max 5 pods\nCPU utilization target: 60%\nCPU request: 100m per pod\nScale-in stabilization: 120 s',6.7,1.45,5.85,2.05)
    section(s,'Evidence to present','Actual `kubectl describe hpa`, auth pod counts, CPU metrics and timestamped replica plot; configuration alone is not proof.',.7,3.9,11.85,1.65)
    s=base(prs,'Load test: three required scenarios',5)
    section(s,'01  Low demand','1 k6 virtual user\n3 minutes\nBaseline response times, CPU and replica count',.45,1.55,4.0,3.15)
    section(s,'02  Increasing demand','Ramp 1 → 12 → 36 virtual users\n7 minutes\nObserve CPU rise and automatic scale-out',4.68,1.55,4.0,3.15)
    section(s,'03  Decreasing demand','Reduce back to 1 virtual user\n7 minutes\nObserve HPA stabilization and scale-in',8.9,1.55,4.0,3.15)
    text(s,'Each iteration: real login → submit reading → MySQL → analytics → MongoDB',1,5.2,11.3,.7,18,True,BLUE)
    s=base(prs,'Observed HPA scaling and CPU',6)
    rimg=E/'hpa-replicas.png';cimg=E/'hpa-cpu.png'
    if rimg.exists():s.shapes.add_picture(str(rimg),Inches(.55),Inches(1.45),width=Inches(6.05))
    else:section(s,'Replica count plot','PENDING: run experiments and regenerate this deck.\nEvidence: evidence/hpa-timeseries.csv',.65,1.65,5.83,3.55)
    if cimg.exists():s.shapes.add_picture(str(cimg),Inches(6.75),Inches(1.45),width=Inches(6.0))
    else:section(s,'CPU percentage plot','PENDING: actual Metrics Server output and HPA utilization must be recorded.',6.82,1.65,5.84,3.55)
    text(s,'Scaling is demonstrated by observed replica changes under load, not by the HPA YAML alone.',.72,6.1,12,.55,16,True,BLUE)
    s=base(prs,'Performance evaluation',7)
    xx=[.45,2.8,5.1,7.7,10.4]; ww=[2.3,2.2,2.5,2.55,2.4]
    for x,w,head in zip(xx,ww,['Scenario','Transactions/s','Avg HTTP ms','p95 HTTP ms','Txn fail %']):
        shape(s,x,1.55,w,.65,BLUE);text(s,head,x+.05,1.7,w-.1,.35,15,True,WHITE,PP_ALIGN.CENTER)
    for i,name in enumerate(['low','increasing','decreasing']):
        vals=[name,num(data.get(name),'transactions_per_second'),num(data.get(name),'response_time_avg_ms'),num(data.get(name),'response_time_p95_ms'),num(data.get(name),'transaction_error_percent')]
        y=2.45+i*1.05
        for x,w,value in zip(xx,ww,vals):
            shape(s,x,y,w,.8,LIGHT);text(s,value,x+.06,y+.2,w-.13,.4,15,False,INK,PP_ALIGN.CENTER)
    text(s,'Measured CPU/replicas and latency charts: evidence/  •  Never invent results.',.7,6.3,11.8,.5,16,True,BLUE)
    s=base(prs,'Findings, limitations and demo',8)
    section(s,'Discussion questions','1. Did auth scale OUT and IN?\n2. Did capacity improve?\n3. What happened to latency, throughput and CPU?\n4. What bottlenecks did we observe?',.62,1.4,5.9,3.9)
    section(s,'Known architectural constraints','One MySQL and one MongoDB instance, synchronous per-request analytics refresh, and a fixed EKS worker count. These are potential bottlenecks, not claimed observed faults.',6.76,1.4,5.85,3.9)
    text(s,'Demo: app + kubectl pods/HPA + k6 logs + actual charts + measured report',.65,6.15,12,.6,17,True,BLUE)
    O.parent.mkdir(exist_ok=True,parents=True);prs.save(O)
    print('Created:',O)
    if not data:print('NOTICE: numeric slide fields are PENDING until a real experiment is run.')
if __name__=='__main__':main()
