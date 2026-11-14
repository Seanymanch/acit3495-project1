"""Real end-to-end cloud check. Does not claim success unless authenticated data flows work."""
import argparse
import html.parser
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--enter',default='http://localhost:5000')
p.add_argument('--results',default='http://localhost:3000')
p.add_argument('--password-file',default=str(ROOT/'secrets/demo_password.txt'))
a=p.parse_args()
password=Path(a.password_file).read_text(encoding='utf-8').strip()
class CsrfParser(html.parser.HTMLParser):
    def __init__(self): super().__init__(); self.value=None
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='input' and d.get('name')=='csrf':self.value=d.get('value')
assert requests.get(a.enter+'/login',timeout=15).status_code==200
assert requests.get(a.results+'/login',timeout=15).status_code==200
s=requests.Session()
r=s.post(a.enter+'/login',data={'username':'student','password':password},timeout=30)
assert r.ok and 'Temperature readings' in r.text,('Enter login failed',r.status_code)
parser=CsrfParser();parser.feed(r.text)
assert parser.value, 'CSRF missing from authenticated form'
r=s.post(a.enter+'/submit',data={'csrf':parser.value,'value':'23.5'},timeout=45)
assert r.ok and 'Reading saved and analytics refreshed.' in r.text,('Submit/analytics failed',r.status_code,r.text[:100])
t=requests.Session()
r=t.post(a.results+'/login',data={'username':'student','password':password},timeout=30)
assert r.ok and 'Count:' in r.text,('Results login/data failed',r.status_code,r.text[:100])
print('PASS: both public-facing apps, auth, MySQL, analytics, and MongoDB communicate correctly.')
