import hmac
import html
import logging
import math
import os
import secrets
from pathlib import Path

import requests
from flask import Flask, request, redirect, make_response
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

logging.basicConfig(level=logging.INFO)
log=logging.getLogger('enter-data')
def secret(name): return Path('/run/secrets',name).read_text(encoding='utf-8').strip()
engine=create_engine(URL.create('mysql+pymysql',username=os.getenv('MYSQL_USER','temperature_app'),
    password=secret('mysql_password'),host=os.getenv('MYSQL_HOST','mysql'),
    database=os.getenv('MYSQL_DATABASE','temperatures')),
    pool_pre_ping=True,pool_size=int(os.getenv('DB_POOL_SIZE','5')),max_overflow=0)
app=Flask(__name__)
AUTH=os.getenv('AUTH_URL','http://auth:8000')
ANALYTICS=os.getenv('ANALYTICS_URL','http://analytics:8000')
SECURE=os.getenv('COOKIE_SECURE','false').lower()=='true'
STYLE='''<style>body{font:16px system-ui;max-width:700px;margin:45px auto;padding:0 16px;line-height:1.5}input,button{padding:9px;margin:5px 0}a{margin-right:12px}.box{padding:18px;border:1px solid #ccc;border-radius:9px}.err{color:#a33}</style>'''

def page(content): return '<!doctype html><html><head><meta charset="utf-8"><title>Enter Data</title>'+STYLE+'</head><body>'+content+'</body></html>'
def who():
    tok=request.cookies.get('enter_token')
    if not tok: return None
    try:
        r=requests.get(AUTH+'/verify',headers={'Authorization':'Bearer '+tok},timeout=3)
        return r.json().get('username') if r.ok else None
    except requests.RequestException:
        return None

def csrf_ok():
    a=request.cookies.get('enter_csrf','')
    b=request.form.get('csrf','')
    return bool(a and b and hmac.compare_digest(a,b))

@app.get('/health')
def health():
    try:
        with engine.connect() as c: c.execute(text('SELECT 1'))
        return {'ok':True}
    except Exception: return {'ok':False},503

@app.get('/login')
def login_page():
    return page('<h1>Enter Data: Log in</h1><form method="post" action="/login"><label>Username <input name="username" required></label><br><label>Password <input type="password" name="password" required></label><br><button>Log in</button></form>')

@app.post('/login')
def login():
    try:
        r=requests.post(AUTH+'/login',json={'username':request.form.get('username',''),
            'password':request.form.get('password','')},timeout=5)
    except requests.RequestException:
        return page('<p class="err">Authentication service unavailable.</p><a href="/login">Try again</a>'),503
    if not r.ok:
        return page('<p class="err">Invalid username or password.</p><a href="/login">Try again</a>'),401
    resp=make_response(redirect('/'))
    resp.set_cookie('enter_token',r.json()['token'],httponly=True,secure=SECURE,samesite='Strict',max_age=7200)
    resp.set_cookie('enter_csrf',secrets.token_urlsafe(24),httponly=True,secure=SECURE,samesite='Strict',max_age=7200)
    return resp

@app.get('/')
def home():
    username=who()
    if not username:return redirect('/login')
    csrf=html.escape(request.cookies.get('enter_csrf',''),quote=True)
    try:
        with engine.connect() as conn:
            rows=conn.execute(text('SELECT id,value,created_at FROM readings ORDER BY id DESC LIMIT 10')).fetchall()
    except Exception:
        return page('<h1>Database unavailable</h1><p>Try again after MySQL recovers.</p>'),503
    items=''.join(f'<li>#{r.id}: {r.value:g}°C ({html.escape(str(r.created_at))})</li>' for r in rows)
    message=html.escape(request.args.get('message',''))
    return page(f'''<h1>Temperature readings</h1><p>Logged in as {html.escape(username)}</p>
       <p><a href="http://localhost:3000">Show Results</a></p>
       <div class="box"><p>{message}</p><form method="post" action="/submit">
       <label>Temperature (°C): <input type="number" name="value" min="-100" max="100" step="any" required></label>
       <input type="hidden" name="csrf" value="{csrf}"><button>Save reading</button></form></div>
       <h2>Recent readings</h2><ul>{items or '<li>No readings yet</li>'}</ul>
       <form method="post" action="/logout"><input type="hidden" name="csrf" value="{csrf}"><button>Log out</button></form>''')

@app.post('/submit')
def submit():
    if not who():return redirect('/login')
    if not csrf_ok():return 'Invalid CSRF token',403
    try:
        value=float(request.form.get('value',''))
        if not math.isfinite(value) or not -100 <= value <= 100:raise ValueError
    except ValueError:
        return page('<p class="err">Enter a finite temperature between -100 and 100.</p><a href="/">Back</a>'),400
    try:
        with engine.begin() as conn:
            conn.execute(text('INSERT INTO readings (value) VALUES (:v)'),{'v':value})
    except Exception:
        return page('<p class="err">Database unavailable; reading not saved.</p><a href="/">Back</a>'),503
    log.info('Saved temperature reading')
    try:
        r=requests.post(ANALYTICS+'/recalculate',headers={'X-Internal-Token':secret('internal_token')},timeout=15)
        r.raise_for_status()
        msg='Reading saved and analytics refreshed.'
    except requests.RequestException:
        msg='Reading saved, but analytics is unavailable. Submit another reading after recovery to refresh.'
    return redirect('/?message='+requests.utils.quote(msg))

@app.post('/logout')
def logout():
    if not csrf_ok():return 'Invalid CSRF token',403
    resp=make_response(redirect('/login'))
    resp.delete_cookie('enter_token')
    resp.delete_cookie('enter_csrf')
    return resp
