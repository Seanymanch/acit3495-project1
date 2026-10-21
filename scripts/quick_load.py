"""Optional simple concurrency test. Use JMeter for grading-grade repeatability."""
import argparse
import concurrent.futures
import html.parser
import time
import threading
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--users',type=int,default=10);p.add_argument('--requests',type=int,default=100)
args=p.parse_args()
pw=(Path(__file__).resolve().parents[1]/'secrets'/'demo_password.txt').read_text().strip()
class Parser(html.parser.HTMLParser):
 def __init__(self): super().__init__();self.csrf=''
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='input' and a.get('name')=='csrf':self.csrf=a.get('value','')
local=threading.local()
def one(i):
 t=time.perf_counter()
 try:
  if not hasattr(local, 'session'):
   local.session=requests.Session()
   r=local.session.post('http://localhost:5000/login',data={'username':'student','password':pw},timeout=10)
   r.raise_for_status()
   parse=Parser();parse.feed(r.text)
   if not parse.csrf:raise ValueError('Login/CSRF failed')
   local.csrf=parse.csrf
  r=local.session.post('http://localhost:5000/submit',data={'value':str(i % 50),'csrf':local.csrf},timeout=30)
  r.raise_for_status()
  if 'Reading saved and analytics refreshed.' not in r.text:
   raise ValueError('Analytics refresh failed')
  return r.status_code,time.perf_counter()-t
 except Exception: return 0,time.perf_counter()-t
start=time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=args.users) as pool:
 out=list(pool.map(one,range(args.requests)))
elapsed=time.perf_counter()-start
ok=sum(code==200 for code,lat in out)
print(f'Requests={args.requests}; Users={args.users}; Total time={elapsed:.2f}s; Throughput={args.requests/elapsed:.2f} requests/s; Errors={args.requests-ok}; Mean latency={sum(lat for _,lat in out)/len(out):.2f}s')
