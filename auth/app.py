import hashlib
import hmac
import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('auth')

def secret(name):
    return Path('/run/secrets', name).read_text(encoding='utf-8').strip()

def make_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 310000)
    return f'{salt}${digest.hex()}'

def verify_hash(password, saved):
    try:
        salt, _ = saved.split('$', 1)
        return hmac.compare_digest(make_hash(password, salt), saved)
    except (ValueError, TypeError):
        return False

engine = create_engine(URL.create('mysql+pymysql', username=os.getenv('MYSQL_USER','temperature_app'),
    password=secret('mysql_password'),host=os.getenv('MYSQL_HOST','mysql'),
    database=os.getenv('MYSQL_DATABASE','temperatures')), pool_pre_ping=True)
jwt_secret = secret('jwt_secret')

@asynccontextmanager
async def lifespan(app):
    with engine.begin() as conn:
        conn.execute(text('''CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL)'''))
        username = os.getenv('APP_USERNAME','student')
        found = conn.execute(text('SELECT id FROM users WHERE username=:user'), {'user':username}).first()
        if not found:
            conn.execute(text('INSERT INTO users (username,password_hash) VALUES (:u,:p)'),
                 {'u':username,'p':make_hash(secret('demo_password'))})
            log.info('Initialized demo account')
    yield
    engine.dispose()

app=FastAPI(lifespan=lifespan)
class Login(BaseModel):
    username: str = Field(min_length=1,max_length=50)
    password: str = Field(min_length=1,max_length=200)

@app.get('/health')
def health():
    try:
        with engine.connect() as c: c.execute(text('SELECT 1'))
        return {'ok':True}
    except Exception:
        raise HTTPException(503,'Database unavailable')

@app.post('/login')
def login(body: Login):
    with engine.connect() as conn:
        row=conn.execute(text('SELECT password_hash FROM users WHERE username=:u'), {'u':body.username}).first()
    if not row or not verify_hash(body.password,row[0]):
        log.warning('Login rejected')
        raise HTTPException(401,'Invalid credentials')
    now=datetime.now(timezone.utc)
    token=jwt.encode({'sub':body.username,'iat':now,'exp':now+timedelta(hours=2)}, jwt_secret,algorithm='HS256')
    return {'token':token}

@app.get('/verify')
def verify(authorization: str | None=Header(default=None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401,'Missing token')
    try:
        body=jwt.decode(authorization[7:],jwt_secret,algorithms=['HS256'],options={'require':['exp','sub']})
        return {'username':body['sub']}
    except jwt.InvalidTokenError:
        raise HTTPException(401,'Invalid or expired token')
