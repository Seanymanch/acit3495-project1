"""Generate a Word technical report from actual evidence. Never fabricate test results."""
import csv
import datetime
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_BREAK
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence'
OUT=ROOT/'docs/Technical_Report.docx'

def results():
    rows={}
    p=E/'performance-summary.csv'
    if p.exists():
        with p.open(encoding='utf-8',newline='') as f:
            for row in csv.DictReader(f):rows[row.get('scenario')]=row
    return rows

def val(obj,key,suffix='',dec=2):
    if not obj or obj.get(key) in ('',None):return 'NOT YET MEASURED'
    try:return f'{float(obj[key]):.{dec}f}{suffix}'
    except ValueError:return 'NOT YET MEASURED'

def analyze_scaling():
    p=E/'hpa-timeseries.csv'
    if not p.exists():return None
    rows=[]
    with p.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                rows.append((row['phase'],row['timestamp_utc'],int(row['replicas_current'])))
            except (ValueError,KeyError):pass
    if not rows:return None
    phases={p:[(date,n) for ph,date,n in rows if ph==p] for p in ('low','increasing','decreasing')}
    return phases

def paragraph(doc,text='',style=None):
    p=doc.add_paragraph(style=style)
    p.add_run(text)
    return p

def heading(doc,text,level=1):doc.add_heading(text,level=level)

def add_table(doc,headings,data):
    t=doc.add_table(rows=1,cols=len(headings));t.style='Light Shading Accent 1';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for i,h in enumerate(headings):t.rows[0].cells[i].text=h
    for row in data:
        cells=t.add_row().cells
        for i,value in enumerate(row):cells[i].text=str(value)
    doc.add_paragraph('')
    return t

def main():
    m=results();scaled=analyze_scaling()
    d=Document()
    sec=d.sections[0];sec.top_margin=Inches(.75);sec.bottom_margin=Inches(.7);sec.left_margin=Inches(.85);sec.right_margin=Inches(.85)
    styles=d.styles;styles['Normal'].font.name='Aptos';styles['Normal'].font.size=Pt(9.5)
    styles['Heading 1'].font.size=Pt(16);styles['Heading 1'].font.color.rgb=RGBColor(25,49,91)
    styles['Heading 2'].font.size=Pt(12);styles['Heading 2'].font.color.rgb=RGBColor(25,49,91)
    header=sec.header.paragraphs[0];header.text='ACIT 3495  /  PROJECT 2  /  TECHNICAL REPORT';header.style='Caption'
    title=d.add_heading('Cloud Deployment and Horizontal Scalability of Microservices',0);title.alignment=WD_ALIGN_PARAGRAPH.CENTER
    sub=paragraph(d,'ACIT 3495  |  Project 2  |  AWS EKS');sub.alignment=WD_ALIGN_PARAGRAPH.CENTER
    paragraph(d,'Team: ______________________________   Date of live experiment: __________________')
    paragraph(d,'Evidence status: '+('REAL MEASUREMENT FILES LOADED' if m and scaled else 'LIVE LOAD TEST AND SCREENSHOTS STILL REQUIRED'))
    heading(d,'1. Objective')
    paragraph(d,'Deploy the actual six-container temperature analytics application from Project 1 to a public-cloud Kubernetes cluster, configure Horizontal Pod Autoscaler (HPA) for a backend microservice, and evaluate actual scale-out/scale-in behavior during low, rising and falling traffic. The report must be supported by measured CPU, replica counts, response time, throughput and errors.')
    heading(d,'2. Cloud architecture')
    img=ROOT/'docs/architecture.png'
    if img.exists():d.add_picture(str(img),width=Inches(6.6))
    paragraph(d,'Environment: AWS EKS in us-west-2. Four application Deployments: enter-data (Flask/Gunicorn), auth (FastAPI), analytics (FastAPI) and show-results (Express/Node). Two persistent data services: MySQL 8.4 and MongoDB 7, each a one-replica StatefulSet backed by an encrypted EBS gp3 PVC. Internal communication uses ClusterIP / headless Services; users access both web frontends using authenticated kubectl port-forward, or short-lived optional demo LoadBalancers.')
    heading(d,'3. Application configuration and reliability')
    add_table(d,['Requirement','Implementation'],[
        ('Workloads','4 Deployments / Services; 2 StatefulSets / Services'),
        ('Configuration','Environment variables, initialization ConfigMaps, generated Kubernetes Secrets'),
        ('Network','Auth, analytics and databases not exposed outside the namespace'),
        ('Resources','CPU/memory requests and limits on all 6 workload containers'),
        ('Health','Startup probes plus process liveness and dependency readiness probes'),
        ('Persistence','EBS gp3 PVCs for MySQL and MongoDB (8 GiB each)'),
        ('Functional test','Login -> MySQL insertion -> Analytics -> MongoDB -> results page')])
    paragraph(d,'Cloud verification: kubectl get nodes; kubectl -n acit3495 get pods,deploy,statefulset,svc,pvc; python scripts/smoke_test_cloud.py. Attach real screenshot(s) showing ready pods, Bound claims and the working web pages.')
    heading(d,'4. Horizontal Pod Autoscaler')
    paragraph(d,'Target: actual auth backend (FastAPI). Replica range: minimum 1, maximum 5. CPU request per pod: 100 millicores. HPA metric: average CPU utilization 60% of requested CPU. Scale-out behavior allows up to two additional pods (or 100% growth) per 60 seconds; scale-in has a 120-second stabilization window and at most one pod removed per minute. The Metrics Server supplies resource metrics. Real login requests perform PBKDF2 password checks and supply genuine CPU load.')
    paragraph(d,'Proof commands: kubectl -n acit3495 describe hpa auth-hpa; kubectl -n acit3495 get hpa auth-hpa -w; kubectl top pods -n acit3495 -l app=auth. An HPA YAML file by itself is not proof of scaling.')
    heading(d,'5. Three k6 test scenarios')
    add_table(d,['Scenario','k6 load','Duration','Purpose'],[
        ('Low','1 virtual user','3 min','Baseline latency, CPU and replicas'),
        ('Increasing','1 to 12 to 36 virtual users','7 min','Raise real login/auth and data workload, observe scale-out'),
        ('Decreasing','1 virtual user','7 min','Reduce demand, allow stabilization, observe scale-in')])
    paragraph(d,'Each k6 iteration authenticates with the real demo user, posts a valid reading with a CSRF token, waits for analytics recalculation and verifies success. Kubernetes telemetry is sampled every 10 seconds. Three k6 JSON summaries, console logs and the timestamped HPA CSV form the raw evidence. Full test sequence: python scripts/run_experiments.py, then python scripts/summarize_results.py.')
    heading(d,'6. Measured results')
    add_table(d,['Scenario','Txn/s','HTTP avg (ms)','HTTP p95 (ms)','Txn failures','HTTP req/s'],[[
        s,val(m.get(s),'transactions_per_second'),val(m.get(s),'response_time_avg_ms'),
        val(m.get(s),'response_time_p95_ms'),val(m.get(s),'transaction_error_percent','%'),
        val(m.get(s),'requests_per_second')] for s in ('low','increasing','decreasing')])
    paragraph(d,'Txn/s is end-to-end temperature submissions per second. HTTP metrics represent requests, not the full transaction. HTTP p95 is the 95th-percentile request duration. Do not compare these as if they were the same unit.')
    if scaled:
        lines=[]
        for ph,rows in scaled.items():
            if rows:
                vals=[n for _,n in rows];lines.append((ph,str(min(vals)),str(max(vals)),str(vals[-1]),rows[0][0],rows[-1][0]))
            else:lines.append((ph,'No samples','No samples','No samples','-','-'))
        add_table(d,['Phase','Min pods','Max pods','Final pods','First sampled UTC','Last sampled UTC'],lines)
    else:
        paragraph(d,'HPA replica/CPU evidence: NOT YET MEASURED. The real k6 run must produce evidence/hpa-timeseries.csv and charts.')
    for filename,title_ in [('hpa-replicas.png','Replica count over time'),('hpa-cpu.png','HPA average CPU utilization over time'),
                             ('throughput.png','Transaction throughput by phase'),('response-time.png','HTTP p95 duration by phase'),('errors.png','Transaction errors by phase')]:
        path=E/filename
        if path.exists():
            p=d.add_paragraph(title_);p.style='Caption'
            d.add_picture(str(path),width=Inches(6.2))
    heading(d,'7. Analysis and discussion')
    if scaled:
        high=scaled.get('increasing',[]);down=scaled.get('decreasing',[])
        scaled_out=bool(high and max(n for _,n in high)>1)
        scaled_in=bool(high and down and down[-1][1]<max(n for _,n in high))
        paragraph(d,'Q4. Did the backend scale out and scale in?')
        paragraph(d,('Observed increasing-phase replicas exceeded one. ' if scaled_out else 'No confirmed replica increase during increasing load. ') + ('Later decreasing-phase replicas fell below the previous peak. ' if scaled_in else 'No confirmed scale-in relative to peak in the recorded decreasing phase. ')+'Refer to the precise timestamps in hpa-timeseries.csv and hpa-replicas.png. Include HPA events and actual observations in the final discussion.')
    else:
        paragraph(d,'Q4. Scale-out/in: PENDING LIVE EVIDENCE. Quote exact replica counts and UTC timestamps from the collected CSV. Do not claim scale-out merely because the configuration is present.')
    paragraph(d,'Q5. Did scaling improve the ability to handle more requests? Compare transaction throughput and failure percentages across the 3 measured phases, along with the active number of auth replicas. A higher VU count or replica count alone does not prove better capacity; describe actual results and any plateau.')
    paragraph(d,'Q6. How did latency, throughput and CPU change? Compare the measured HTTP average/p95 latency, transaction rate, and HPA CPU percentages. Discuss the observed relationship to replica count. Fill the numeric comparisons from the preceding tables and plots.')
    paragraph(d,'Q7. Limitations or bottlenecks: The application recalculates analytics synchronously and shares one MySQL and MongoDB replica, which can limit end-to-end performance even if auth scales. Other potential factors are Flask worker capacity, CPU throttling and the HPA observation/stabilization delay. Confirm which bottlenecks occurred in the raw logs before treating them as findings.')
    heading(d,'8. Limitations and future improvements')
    paragraph(d,'A three-node fixed EKS worker pool is not node autoscaling. MySQL/MongoDB are intentionally single-replica. EBS volumes are AZ-scoped. The optional public HTTP services have no TLS and must only use disposable coursework credentials; production needs managed TLS ingress, better network policy and a managed/HA data layer. Separate async queue-based analytics or write batching could prevent synchronous recalculation from limiting throughput. Add Prometheus/CloudWatch for richer monitoring if needed.')
    heading(d,'9. Evidence checklist and references')
    paragraph(d,'Attach screenshots: (1) AWS EKS nodes, (2) ready pods and Bound PVCs, (3) both working web apps, (4) HPA describe events showing scale-out, (5) high-load CPU values, (6) scale-in evidence, and (7) three k6 result summaries/charts. Raw files: evidence/hpa-timeseries.csv; low-, increasing-, decreasing-summary.json; performance-summary.csv; measured-results.md. These are required live deliverables.')
    paragraph(d,'Official documentation: Kubernetes HPA, https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/ ; Kubernetes Metrics Pipeline, https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/ ; AWS EKS EBS CSI add-on, https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html')
    footer=sec.footer.paragraphs[0];footer.text='ACIT 3495 Project 2   •   Results must be collected on the actual cluster';footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    OUT.parent.mkdir(exist_ok=True,parents=True);d.save(OUT)
    print('Created:',OUT)
    if not m or not scaled:print('NOTICE: report marks unmeasured results as pending until real cloud tests run.')
if __name__=='__main__':main()
