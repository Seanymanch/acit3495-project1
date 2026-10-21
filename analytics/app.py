import hmac
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pymongo import MongoClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from calculations import summarize

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('analytics')
def secret(name): return Path('/run/secrets',name).read_text(encoding='utf-8').strip()

engine=create_engine(URL.create('mysql+pymysql',username=os.getenv('MYSQL_USER','temperature_app'),
    password=secret('mysql_password'),host=os.getenv('MYSQL_HOST','mysql'),
    database=os.getenv('MYSQL_DATABASE','temperatures')),
    pool_pre_ping=True,pool_size=int(os.getenv('DB_POOL_SIZE','5')),max_overflow=0)
mongo=MongoClient(host=os.getenv('MONGO_HOST','mongo'),port=27017,
    username=os.getenv('MONGO_USER','admin'),password=secret('mongo_app_password'),
    authSource='analytics',serverSelectionTimeoutMS=3000)
collection=mongo['analytics']['snapshots']
app=FastAPI()

@app.get('/health')
def health():
    try:
        with engine.connect() as c: c.execute(text('SELECT 1'))
        mongo.admin.command('ping')
        return {'ok':True}
    except Exception:
        raise HTTPException(503,'Dependency unavailable')

@app.post('/recalculate')
def recalculate(x_internal_token: str | None=Header(default=None)):
    if not x_internal_token or not hmac.compare_digest(x_internal_token,secret('internal_token')):
        raise HTTPException(403,'Forbidden')
    mode=os.getenv('ANALYTICS_MODE','sql')
    with engine.connect() as conn:
        if mode == 'python':
            rows=conn.execute(text('SELECT value FROM readings')).fetchall()
            result=summarize([row[0] for row in rows])
        elif mode == 'sql':
            row=conn.execute(text('SELECT COUNT(*) AS n, MIN(value) AS mn, MAX(value) AS mx, AVG(value) AS av FROM readings')).first()
            result={'count':row.n,'minimum':row.mn,'maximum':row.mx,
                    'average':float(row.av) if row.av is not None else None}
        else:
            raise HTTPException(500,'Unsupported analytics mode')
    result['name']='temperatures'
    result['updated_at']=datetime.now(timezone.utc)
    collection.replace_one({'name':'temperatures'},result,upsert=True)
    log.info('Calculated stats count=%s mode=%s',result['count'],mode)
    return {'ok':True,'count':result['count']}
