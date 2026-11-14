"""Run all three required k6 scenarios while sampling ACTUAL Kubernetes HPA and CPU metrics.
Keep an authenticated kubectl port-forward to enter-data service running in another terminal.
Run from project root: python scripts/run_experiments.py
"""
import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import threading
import time
ROOT=Path(__file__).resolve().parents[1]
FIELDNAMES=['timestamp_utc','phase','replicas_current','replicas_desired','ready_replicas',
            'hpa_cpu_util_percent','pod_cpu_total_mcores','sampling_error']

def kubectl_json(*args):
    p=subprocess.run(['kubectl','-n','acit3495',*args,'-o','json'],capture_output=True,text=True,timeout=20)
    if p.returncode: raise RuntimeError(p.stderr.strip()[:200])
    return json.loads(p.stdout)

def sample(phase):
    row={'timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
         'phase':phase,'replicas_current':'','replicas_desired':'','ready_replicas':'',
         'hpa_cpu_util_percent':'','pod_cpu_total_mcores':'','sampling_error':''}
    try:
        h=kubectl_json('get','hpa','auth-hpa')
        d=kubectl_json('get','deployment','auth')
        row['replicas_current']=h.get('status',{}).get('currentReplicas',0)
        row['replicas_desired']=h.get('status',{}).get('desiredReplicas',0)
        row['ready_replicas']=d.get('status',{}).get('readyReplicas',0)
        for item in h.get('status',{}).get('currentMetrics',[]):
            if item.get('resource',{}).get('name')=='cpu':
                row['hpa_cpu_util_percent']=item['resource']['current'].get('averageUtilization','')
        # Resource Metrics API: one container CPU usage per running auth pod.
        # Parsing quantities supports n/u/m/whole CPU, not just top's display format.
        try:
            raw=subprocess.run(['kubectl','get','--raw',
              '/apis/metrics.k8s.io/v1beta1/namespaces/acit3495/pods'],
              capture_output=True,text=True,timeout=20,check=True)
            data=json.loads(raw.stdout)
            pods={x['metadata']['name'] for x in kubectl_json('get','pods','-l','app=auth').get('items',[])}
            def millicores(q):
                q=str(q)
                for unit,mult in [('n',1e-6),('u',1e-3),('m',1)]:
                    if q.endswith(unit): return float(q[:-1])*mult
                return float(q)*1000
            total=0
            for pod in data.get('items',[]):
                if pod['metadata']['name'] in pods:
                    total+=sum(millicores(c['usage']['cpu']) for c in pod.get('containers',[]))
            row['pod_cpu_total_mcores']=round(total,2)
        except (subprocess.SubprocessError,ValueError,KeyError,TypeError):
            pass
    except (subprocess.SubprocessError,RuntimeError,KeyError,TypeError) as e:
        row['sampling_error']=str(e).replace('\n',' ')[:150]
    return row

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base-url',default='http://localhost:5000')
    ap.add_argument('--interval',type=float,default=10.0)
    ap.add_argument('--output-dir',default=str(ROOT/'evidence'))
    ap.add_argument('--scenarios',nargs='+',choices=['low','increasing','decreasing'],
                    default=['low','increasing','decreasing'])
    args=ap.parse_args()
    pwd=(ROOT/'secrets/demo_password.txt')
    if not pwd.exists():ap.error('Run python scripts/generate_secrets.py')
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    if (out/'hpa-timeseries.csv').exists():
        ap.error('evidence/hpa-timeseries.csv already exists; archive/delete old results to avoid mixing runs')
    environment=os.environ.copy()
    environment['DEMO_PASSWORD']=pwd.read_text(encoding='utf-8').strip()
    environment['BASE_URL']=args.base_url
    error=[]
    stop=threading.Event()
    phase=['starting']
    def monitor():
        with (out/'hpa-timeseries.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=FIELDNAMES);writer.writeheader()
            while not stop.is_set():
                writer.writerow(sample(phase[0]));f.flush()
                stop.wait(args.interval)
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    try:
        for name in args.scenarios:
            phase[0]=name
            print('\n===',name.upper(),'===',flush=True)
            environment['SCENARIO']=name
            cmd=['k6','run','--summary-export',str(out/f'{name}-summary.json'),
                 str(ROOT/'k6/temperature-workload.js')]
            with (out/f'{name}-k6-console.log').open('w',encoding='utf-8') as log:
                p=subprocess.run(cmd,env=environment,stdout=log,stderr=subprocess.STDOUT)
            print('k6 finished',name,'exit code',p.returncode,flush=True)
            if p.returncode: error.append(name)
            print('Console log:',out/f'{name}-k6-console.log')
        phase[0]='post-test'
    finally:
        stop.set();thread.join(timeout=30)
    print('Recorded HPA samples:',out/'hpa-timeseries.csv')
    print('Next: python scripts/summarize_results.py')
    if error: raise SystemExit('Some k6 runs reported non-zero status; inspect logs for: '+', '.join(error))
if __name__=='__main__':main()
