const express = require('express');
const cookieParser = require('cookie-parser');
const {MongoClient} = require('mongodb');
const {randomBytes, timingSafeEqual} = require('node:crypto');
const fs = require('node:fs');
const {formatNumber} = require('./format');

const app = express();
const client = new MongoClient('mongodb://' + (process.env.MONGO_HOST || 'mongo') + ':27017', {
  auth: {username: process.env.MONGO_USER || 'admin', password: fs.readFileSync('/run/secrets/mongo_reader_password', 'utf8').trim()},
  authSource: 'analytics', serverSelectionTimeoutMS: 3000
});
const AUTH = process.env.AUTH_URL || 'http://auth:8000';
const secure = process.env.COOKIE_SECURE === 'true';
const cookieSettings = {httpOnly: true, secure, sameSite: 'strict', maxAge: 7200000};
const style = `
<style>
    body {
        font-family: Arial, sans-serif;
        background-color: #f1f5f9;
        color: #1e293b;
        max-width: 850px;
        margin: 50px auto;
        padding: 20px;
        line-height: 1.6;
    }

    h1 {
        color: #1d4ed8;
        font-size: 32px;
    }

    h2 {
        color: #334155;
    }

    .box {
        background-color: white;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        margin: 20px 0;
    }

    input {
        padding: 12px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        margin: 10px 0;
        font-size: 16px;
    }

    button {
        background-color: #2563eb;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 16px;
    }

    button:hover {
        background-color: #1d4ed8;
    }

    a {
        color: #2563eb;
        text-decoration: none;
        margin-right: 12px;
    }

    a:hover {
        text-decoration: underline;
    }

    li {
        background-color: white;
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 6px;
    }

    .err {
        color: #dc2626;
    }
</style>
`;
const page = body => `<!doctype html><html><head><meta charset="utf-8"><title>Analytics Results</title>${style}</head><body>${body}</body></html>`;
const escapeHtml = s => String(s).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

app.use(express.urlencoded({extended:false, limit:'5kb'}));
app.use(cookieParser());
app.disable('x-powered-by');

async function username(req) {
  const token = req.cookies.results_token;
  if (!token) return null;
  try {
    const response = await fetch(AUTH+'/verify', {headers:{Authorization:'Bearer '+token}, signal:AbortSignal.timeout(3000)});
    if (!response.ok) return null;
    return (await response.json()).username;
  } catch { return null; }
}
function csrfOK(req) {
  const a=Buffer.from(req.cookies.results_csrf || '');
  const b=Buffer.from(req.body.csrf || '');
  return a.length > 0 && a.length === b.length && timingSafeEqual(a,b);
}
app.get('/health', async (_req,res) => {
  try { await client.db('admin').command({ping:1}); res.json({ok:true}); }
  catch { res.status(503).json({ok:false}); }
});
app.get('/login', (_req,res) => res.send(page(`<h1>Show Results: Log in</h1><form method="post"><label>Username <input name="username" required></label><br><label>Password <input name="password" type="password" required></label><br><button>Log in</button></form>`)));
app.post('/login', async (req,res) => {
  try {
    const response = await fetch(AUTH+'/login', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({username:req.body.username || '',password:req.body.password || ''}),signal:AbortSignal.timeout(5000)});
    if (!response.ok) return res.status(401).send(page('<p>Invalid login.</p><a href="/login">Try again</a>'));
    const {token} = await response.json();
    res.cookie('results_token',token,cookieSettings);
    res.cookie('results_csrf',randomBytes(24).toString('hex'),cookieSettings);
    res.redirect('/');
  } catch { res.status(503).send(page('Authentication unavailable.')); }
});
app.get('/', async (req,res) => {
  const user=await username(req);
  if (!user) return res.redirect('/login');
  try {
    const data=await client.db('analytics').collection('snapshots').findOne({name:'temperatures'});
    if (!data) return res.send(page(`<h1>Analytics results</h1><p>No results yet. Add readings at <a href="http://localhost:5000">Enter Data</a>.</p>`));
    res.send(page(`<h1>Temperature statistics</h1><p>Logged in as ${escapeHtml(user)}</p>
      <div class="box"><p><strong>Count:</strong> ${data.count}</p>
      <p><strong>Minimum:</strong> ${formatNumber(data.minimum)} °C</p>
      <p><strong>Maximum:</strong> ${formatNumber(data.maximum)} °C</p>
      <p><strong>Average:</strong> ${formatNumber(data.average)} °C</p>
      <p><small>Updated: ${escapeHtml(data.updated_at || '')}</small></p></div>
      <p><a href="http://localhost:5000">Enter Data</a></p>
      <form method="post" action="/logout"><input type="hidden" name="csrf" value="${escapeHtml(req.cookies.results_csrf || '')}"><button>Log out</button></form>`));
  } catch { res.status(503).send(page('<h1>MongoDB unavailable</h1><p>Try again after recovery.</p>')); }
});
app.post('/logout',(req,res) => {
  if(!csrfOK(req)) return res.status(403).send('Invalid CSRF token');
  res.clearCookie('results_token');res.clearCookie('results_csrf');res.redirect('/login');
});
app.listen(3000,'0.0.0.0',()=>console.log('show-results listening on 3000'));
