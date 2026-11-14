"""Produce evidence/charts plus actual metrics report from k6 JSON and Kubernetes CSV."""
import csv
import json
import statistics
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence'
SCENARIOS=['low','increasing','decreasing']

def metric(obj,name,key='avg'):
    try:return obj['metrics'][name]['values'][key]
    except (KeyError,TypeError):return None

def fmt(v,digits=2):return 'not measured' if v is None else f'{v:.{digits}f}'

def main():
    E.mkdir(exist_ok=True)
    data=[]
    for name in SCENARIOS:
        p=E/f'{name}-summary.json'
        if not p.exists():
            print('Missing',p,'; run experiments first. No results were invented.')
            continue
        obj=json.loads(p.read_text(encoding='utf-8'))
        row={'scenario':name,'requests_per_second':metric(obj,'http_reqs','rate'),
             'response_time_avg_ms':metric(obj,'http_req_duration','avg'),
             'response_time_p95_ms':metric(obj,'http_req_duration','p(95)'),
             'http_error_percent':(metric(obj,'http_req_failed','rate') or 0)*100 if metric(obj,'http_req_failed','rate') is not None else None,
             'transaction_error_percent':(metric(obj,'transaction_failure_rate','rate') or 0)*100 if metric(obj,'transaction_failure_rate','rate') is not None else None,
             'transactions_per_second':metric(obj,'iterations','rate')}
        data.append(row)
    if data:
        with (E/'performance-summary.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=data[0].keys());w.writeheader();w.writerows(data)
        for name,col,ylabel in [('throughput','transactions_per_second','Completed transactions per second'),
                                  ('response-time','response_time_p95_ms','HTTP p95 response time (ms)'),
                                  ('errors','transaction_error_percent','Transaction failure (%)')]:
            fig,ax=plt.subplots(figsize=(8,4))
            ax.bar([r['scenario'] for r in data],[r[col] or 0 for r in data])
            ax.set_ylabel(ylabel);ax.set_xlabel('Load scenario');ax.set_title(ylabel)
            fig.tight_layout();fig.savefig(E/(name+'.png'),dpi=160);plt.close(fig)
    metrics_csv=E/'hpa-timeseries.csv'
    samples=[]
    if metrics_csv.exists():
        with metrics_csv.open(encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if r['replicas_current']:
                    try:
                        samples.append({'timestamp':datetime.fromisoformat(r['timestamp_utc']),
                          'phase':r['phase'],'replicas':float(r['replicas_current']),
                          'cpu':float(r['hpa_cpu_util_percent']) if r['hpa_cpu_util_percent'] else None,
                          'cpu_m':float(r['pod_cpu_total_mcores']) if r['pod_cpu_total_mcores'] else None})
                    except ValueError:pass
    if samples:
        fig,ax=plt.subplots(figsize=(10,4.5))
        ax.step([x['timestamp'] for x in samples],[x['replicas'] for x in samples],where='post')
        ax.set_ylim(bottom=0);ax.set_ylabel('Auth replicas');ax.set_xlabel('UTC time');ax.set_title('Observed auth replica count through load phases')
        ax.tick_params(axis='x',rotation=25)
        fig.tight_layout();fig.savefig(E/'hpa-replicas.png',dpi=160);plt.close(fig)
        cpus=[x for x in samples if x['cpu'] is not None]
        if cpus:
            fig,ax=plt.subplots(figsize=(10,4.5))
            ax.plot([x['timestamp'] for x in cpus],[x['cpu'] for x in cpus])
            ax.axhline(60,linestyle='--',label='HPA target: 60%');ax.legend()
            ax.set_ylabel('Average auth CPU / CPU request (%)');ax.set_xlabel('UTC time')
            ax.set_title('Observed CPU utilization used by HPA');ax.tick_params(axis='x',rotation=25)
            fig.tight_layout();fig.savefig(E/'hpa-cpu.png',dpi=160);plt.close(fig)
    lines=['# Measured results (generated from actual evidence)','',
          'Generated only from on-disk k6 summaries and Kubernetes telemetry. No values are simulated.','',
          '| Scenario | Transaction rate/s | HTTP request rate/s | HTTP avg latency ms | HTTP p95 latency ms | Transaction failures % |',
          '|---|---:|---:|---:|---:|---:|']
    for row in data:
        lines.append('| '+row['scenario']+' | '+' | '.join(fmt(row[k]) for k in ['transactions_per_second','requests_per_second','response_time_avg_ms','response_time_p95_ms','transaction_error_percent'])+' |')
    lines +=['','## HPA observations','']
    for phase in SCENARIOS:
        phase_samples=[x for x in samples if x['phase']==phase]
        if not phase_samples:
            lines.append(f'- {phase}: No Kubernetes samples found.')
        else:
            reps=[x['replicas'] for x in phase_samples]
            cpu=[x['cpu'] for x in phase_samples if x['cpu'] is not None]
            lines.append(f'- {phase}: replicas min={min(reps):.0f}, max={max(reps):.0f}, final={reps[-1]:.0f}; '
                         + ('HPA CPU utilization mean='+fmt(statistics.mean(cpu))+'%.' if cpu else 'HPA CPU utilization unavailable.'))
    if samples:
        overall=[x['replicas'] for x in samples]
        lines+=['',f'Observed replica range across complete experiment: {min(overall):.0f} to {max(overall):.0f}.',
                'Scale-out and scale-in must be confirmed in the chronological hpa-replicas.png plot and logs.']
    else:lines+=['','No HPA samples exist. Do not claim scaling occurred.']
    lines+=['','## Evidence files','',
            '- hpa-timeseries.csv: raw HPA, deployment, and CPU sampling (if recorded).',
            '- *-summary.json: raw k6 summary for each scenario (if recorded).',
            '- *-k6-console.log: workload console output (if recorded).',
            '- hpa-replicas.png, hpa-cpu.png, throughput.png, response-time.png, errors.png: generated plots when supported.',
            '','## Discussion checklist','',
            '1. Did replicas increase above 1 during increasing traffic, then return toward 1 during decreasing traffic? Cite exact timestamps.',
            '2. Compare throughput, p95 response time and error rate across three stages. Do not assume improvement.',
            '3. Discuss database contention, login hashing CPU, EBS storage, network, HPA delays, resource limits, and node capacity as observed.',
            '4. Clarify that HTTP request latency includes auth + write + analytics operations; HTTP requests are not identical to end-to-end transactions.']
    (E/'measured-results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Wrote actual-measurement report:',E/'measured-results.md')
    print('Created charts only where evidence exists.')
if __name__=='__main__': main()
