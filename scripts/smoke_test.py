"""Lightweight running-stack check: auth denial, login, submission, stats page."""
from pathlib import Path
import sys
import requests

base=Path(__file__).resolve().parents[1]
passfile=base/'secrets'/'demo_password.txt'
if not passfile.exists(): sys.exit('Run python scripts/generate_secrets.py first')
pw=passfile.read_text(encoding='utf-8').strip()
enter='http://localhost:5000'
results='http://localhost:3000'
assert requests.get(enter+'/',allow_redirects=False,timeout=10).status_code==302
assert requests.get(results+'/',allow_redirects=False,timeout=10).status_code==302
s=requests.Session()
r=s.post(enter+'/login',data={'username':'student','password':pw},timeout=10)
assert r.ok and 'Temperature readings' in r.text,(r.status_code,r.text[:400])
from html.parser import HTMLParser
class CsrfParser(HTMLParser):
 def __init__(self): super().__init__();self.token=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='input' and a.get('name')=='csrf':self.token=a.get('value')
p=CsrfParser();p.feed(r.text)
assert p.token
r=s.post(enter+'/submit',data={'value':'30','csrf':p.token},timeout=25)
assert r.ok and 'Reading saved' in r.text,(r.status_code,r.text[:400])
t=requests.Session()
r=t.post(results+'/login',data={'username':'student','password':pw},timeout=10)
assert r.ok and 'Temperature statistics' in r.text,(r.status_code,r.text[:400])
assert 'Count:' in r.text
print('PASS: protected routes, user login, reading storage, analytics display')
