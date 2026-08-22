from __future__ import annotations
import hashlib, hmac, html, json, os, time
from pathlib import Path
from urllib.parse import parse_qsl
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from db import Session, Experience, QuizAttempt, bump

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / 'static'
app = FastAPI(title='GenZ Expression Mini App', docs_url=None, redoc_url=None)

class QuizSubmit(BaseModel):
    init_data: str = ''
    answers: list[str] = []


def verify_init_data(init_data: str):
    """Validate Telegram WebApp initData. Returns user dict or None."""
    if not init_data:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received = pairs.pop('hash', None)
        auth_date = int(pairs.get('auth_date', '0'))
        if not received or not auth_date or abs(time.time() - auth_date) > 86400:
            return None
        bot_token = os.getenv('BOT_TOKEN', '')
        if not bot_token:
            return None
        check = '\n'.join(f'{k}={v}' for k, v in sorted(pairs.items()))
        secret = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, received):
            return None
        user = json.loads(pairs.get('user', '{}'))
        return user if user.get('id') else None
    except Exception:
        return None


def media_ids_for(exp):
    if exp is None: return []
    raw=exp.media_file_id
    if not raw: return []
    try:
        data=json.loads(raw)
        if isinstance(data,list): return [str(x) for x in data if str(x).strip()]
    except Exception: pass
    return [str(raw)]

def questions_for(exp):
    try:
        q = json.loads(exp.questions or '[]')
    except Exception:
        q = []
    if not isinstance(q, list):
        return []
    out=[]
    for item in q:
        if isinstance(item, dict):
            out.append({'question': str(item.get('question','')), 'answer': str(item.get('answer',''))})
        else:
            text=str(item)
            if '::' in text:
                question, answer = text.split('::',1)
                out.append({'question':question.strip(),'answer':answer.strip()})
            else:
                out.append({'question':text,'answer':''})
    return [x for x in out if x['question']][:20]


def public_base():
    value=os.getenv('RAILWAY_PUBLIC_DOMAIN','').strip()
    if value and not value.startswith(('http://','https://')): value='https://'+value
    return value.rstrip('/')


@app.get('/', response_class=HTMLResponse)
async def root():
    return HTMLResponse('<meta name="viewport" content="width=device-width,initial-scale=1"><body style="margin:0;background:#0A0A0A;color:#F5F5F5;font-family:system-ui;display:grid;place-items:center;min-height:100vh"><div style="text-align:center"><b style="color:#FF4F81">✦ GENZ EXPRESSION</b><h1>Telegram Mini App</h1><p style="color:#8A8A8A">Open an Expression from Telegram.</p></div></body>')

@app.get('/health')
async def health():
    return {'status':'ok','service':'genz-expression-miniapp','version':'2.0'}

@app.get('/miniapp', response_class=HTMLResponse)
async def miniapp():
    return FileResponse(STATIC/'index.html', media_type='text/html')

# Compatibility routes: older bot buttons / previously generated links may use
# /e/<code> or /w/<code>. Always send them to the canonical Mini App route.
@app.get('/e/{code}')
async def legacy_e(code: str):
    return RedirectResponse(url=f'/miniapp?code={code}', status_code=307)

@app.get('/w/{code}')
async def legacy_w(code: str):
    return RedirectResponse(url=f'/miniapp?code={code}', status_code=307)

@app.get('/miniapp/{code}')
async def miniapp_code(code: str):
    return RedirectResponse(url=f'/miniapp?code={code}', status_code=307)

@app.get('/static/{name}')
async def static_file(name: str):
    path=(STATIC/name).resolve()
    if STATIC not in path.parents or not path.is_file(): raise HTTPException(404)
    return FileResponse(path)


@app.get('/media/{code}')
async def media(code: str, idx: int = 0):
    exp=None
    async with Session() as s:
        exp=await s.scalar(select(Experience).where(Experience.code==code, Experience.published.is_(True)))
    ids=media_ids_for(exp)
    if not ids:
        raise HTTPException(404, 'Media not found')
    token=os.getenv('BOT_TOKEN','')
    if not token:
        raise HTTPException(503, 'Media unavailable')
    import httpx
    async with httpx.AsyncClient(timeout=20) as client:
        idx=max(0,min(idx,len(ids)-1))
        info=await client.get(f'https://api.telegram.org/bot{token}/getFile',params={'file_id':ids[idx]})
        if info.status_code!=200:
            raise HTTPException(404,'Media not found')
        fp=(info.json().get('result') or {}).get('file_path')
        if not fp:
            raise HTTPException(404,'Media not found')
        r=await client.get(f'https://api.telegram.org/file/bot{token}/{fp}')
        if r.status_code!=200:
            raise HTTPException(404,'Media not found')
        return Response(content=r.content,media_type=r.headers.get('content-type','application/octet-stream'))

@app.get('/audio/{code}')
async def audio(code: str):
    async with Session() as s:
        exp=await s.scalar(select(Experience).where(Experience.code==code, Experience.published.is_(True)))
    file_id=getattr(exp,'audio_file_id',None) if exp else None
    if not file_id: raise HTTPException(404,'Audio not found')
    token=os.getenv('BOT_TOKEN','')
    if not token: raise HTTPException(503,'Audio unavailable')
    import httpx
    async with httpx.AsyncClient(timeout=30) as client:
        info=await client.get(f'https://api.telegram.org/bot{token}/getFile',params={'file_id':file_id})
        if info.status_code!=200: raise HTTPException(404,'Audio not found')
        fp=(info.json().get('result') or {}).get('file_path')
        if not fp: raise HTTPException(404,'Audio not found')
        r=await client.get(f'https://api.telegram.org/file/bot{token}/{fp}')
        if r.status_code!=200: raise HTTPException(404,'Audio not found')
        return Response(content=r.content,media_type=r.headers.get('content-type','audio/ogg'))

@app.get('/api/experience/{code}')
async def experience(code: str):
    async with Session() as s:
        exp=await s.scalar(select(Experience).where(Experience.code==code, Experience.published.is_(True)))
        if not exp: raise HTTPException(404, 'Expression not found')
        exp.views += 1
        await s.commit()
        media=media_ids_for(exp)
        return {
            'code':exp.code,'kind':exp.kind,'title':exp.title,'intro':exp.intro,'body':exp.body,
            'media': media_ids_for(exp), 'audio': bool(getattr(exp,'audio_file_id',None)), 'questions': [q['question'] for q in questions_for(exp)],
            'quiz': [{'question': q['question']} for q in questions_for(exp)] if exp.kind in {'quiz','bestiequiz','compat','wyr','tod','thisthat'} else [],
            'plays':exp.plays,'views':exp.views
        }

@app.get('/api/quiz/{code}/leaderboard')
async def leaderboard(code: str):
    async with Session() as s:
        exp=await s.scalar(select(Experience).where(Experience.code==code, Experience.published.is_(True)))
        if not exp: raise HTTPException(404, 'Expression not found')
        rows=(await s.scalars(select(QuizAttempt).where(QuizAttempt.expression_code==code).order_by(QuizAttempt.score.desc(), QuizAttempt.duration_ms.asc(), QuizAttempt.created_at.asc()).limit(50))).all()
        return {'items':[{'name':r.display_name or 'Anonymous','score':r.score,'total':r.total,'duration_ms':r.duration_ms} for r in rows]}

@app.post('/api/quiz/{code}/submit')
async def submit_quiz(code: str, payload: QuizSubmit):
    tg_user=verify_init_data(payload.init_data)
    if not tg_user:
        raise HTTPException(401, 'Open this quiz inside Telegram.')
    async with Session() as s:
        exp=await s.scalar(select(Experience).where(Experience.code==code, Experience.published.is_(True)))
        if not exp: raise HTTPException(404, 'Expression not found')
        questions=questions_for(exp)
        if not questions: raise HTTPException(400, 'This Expression has no quiz questions.')
        answers=payload.answers[:len(questions)]
        score=sum(1 for q,a in zip(questions,answers) if q['answer'] and a.strip().casefold()==q['answer'].strip().casefold())
        display=(tg_user.get('first_name') or tg_user.get('username') or 'Anonymous')[:80]
        attempt=QuizAttempt(expression_code=code,telegram_id=int(tg_user['id']),display_name=display,score=score,total=len(questions),duration_ms=0)
        s.add(attempt); exp.plays += 1; await s.commit()
        rank=(await s.scalar(select(func.count()).where(QuizAttempt.expression_code==code, QuizAttempt.score>score))) or 0
        return {'score':score,'total':len(questions),'rank':rank+1}
