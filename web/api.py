from __future__ import annotations
import hashlib,hmac,html,json,os,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import parse_qsl
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import HTMLResponse,FileResponse,Response,RedirectResponse
from pydantic import BaseModel,Field
from sqlalchemy import select,func,and_
from db import Session,Experience,QuizAttempt,OwnerMessage
ROOT=Path(__file__).resolve().parent; STATIC=ROOT/'static'; app=FastAPI(title='GenZ Expression Mini App',docs_url=None,redoc_url=None)
QUIZ_KINDS={'quiz','bestiequiz','compat','wyr','tod','thisthat'}
class QuizSubmit(BaseModel): init_data:str=''; answers:list[str]=Field(default_factory=list); duration_ms:int=Field(default=0,ge=0,le=3600000)
class OwnerMessageIn(BaseModel): init_data:str=''; text:str=Field(min_length=1,max_length=2000)
def verify_init_data(init_data):
    if not init_data:return None
    try:
        p=dict(parse_qsl(init_data,keep_blank_values=True)); received=p.pop('hash',None); auth=int(p.get('auth_date','0')); token=os.getenv('BOT_TOKEN','')
        if not received or not auth or not token or abs(time.time()-auth)>86400:return None
        check='\n'.join(f'{k}={v}' for k,v in sorted(p.items())); secret=hmac.new(b'WebAppData',token.encode(),hashlib.sha256).digest(); expected=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,received):return None
        u=json.loads(p.get('user','{}')); return u if u.get('id') else None
    except Exception:return None
def media_ids_for(exp):
    if not exp or not exp.media_file_id:return []
    try:
        x=json.loads(exp.media_file_id)
        if isinstance(x,list):return [str(v) for v in x if str(v).strip()]
    except Exception:pass
    return [str(exp.media_file_id)]
def questions_for(exp):
    try:q=json.loads(exp.questions or '[]')
    except Exception:q=[]
    out=[]
    for item in q if isinstance(q,list) else []:
        if isinstance(item,dict): question=str(item.get('question','')).strip(); answer=str(item.get('answer','')).strip()
        else:
            question,sep,answer=str(item).partition('::'); question=question.strip(); answer=answer.strip() if sep else ''
        if question:out.append({'question':question,'answer':answer})
    return out[:20]
def expired(e):
    if not e or not e.expires_at:
        return False
    # Some database drivers may return DateTime columns without tzinfo even when the
    # SQLAlchemy column is declared timezone-aware. Normalize before comparing.
    exp=e.expires_at
    if exp.tzinfo is None:
        exp=exp.replace(tzinfo=timezone.utc)
    return exp<=datetime.now(timezone.utc)
def theme_for(k):
    m={'confess':('CONFESSION','romance','Reveal what was left unsaid.'),'loveletter':('LOVE LETTER','romance','A letter made to be opened slowly.'),'anniversary':('ANNIVERSARY','gold','A little timeline of us.'),'appreciation':('APPRECIATION','warm','Something worth saying out loud.'),'friendship':('BEST FRIEND','sunset','For the person who makes ordinary days better.'),'bestiequiz':('BESTIE QUIZ','playful','Let’s see how well you really know each other.'),'farewell':('FAREWELL','dusk','Some moments deserve a gentle goodbye.'),'compat':('COMPATIBILITY','violet','Two people. One little test.'),'birthday':('BIRTHDAY','party','Today deserves a little extra sparkle.'),'graduation':('GRADUATION','blue','A new chapter starts here.'),'invitation':('INVITATION','gold','You are officially invited.'),'countdown':('COUNTDOWN','neon','Every second brings it closer.'),'quiz':('QUIZ','neon','Answer once. Make it count.'),'wyr':('WOULD YOU RATHER','neon','Pick one. No overthinking.'),'tod':('TRUTH OR DARE','danger','Your turn.'),'thisthat':('THIS OR THAT','minimal','One choice says a lot.'),'memory':('MEMORY','film','A place to keep a moment.'),'photostory':('PHOTO STORY','film','Scroll through the story.'),'timeline':('TIMELINE','paper','Little moments, in order.'),'challenge':('CHALLENGE','fire','Ready? Start now.'),'30day':('30-DAY CHALLENGE','fire','One day at a time.'),'randomchallenge':('RANDOM CHALLENGE','glitch','You got this one.')};return m.get(k,('EXPERIENCE','party','Made just for you.'))
async def active_exp(code):
    async with Session() as s:return await s.scalar(select(Experience).where(Experience.code==code,Experience.published.is_(True)))
@app.get('/',response_class=HTMLResponse)
async def root():return HTMLResponse('<meta name="viewport" content="width=device-width,initial-scale=1"><body style="margin:0;background:#080808;color:#fff;font-family:system-ui;display:grid;place-items:center;min-height:100vh"><div style="text-align:center"><b style="color:#ff4f81">✦ GENZ EXPRESSION</b><h1>Telegram Mini App</h1><p style="color:#888">Open an Expression from Telegram.</p></div></body>')
@app.get('/health')
async def health():return {'status':'ok','service':'genz-expression-miniapp','version':'3.0'}
@app.get('/miniapp',response_class=HTMLResponse)
async def miniapp():return FileResponse(STATIC/'index.html',media_type='text/html')
@app.get('/e/{code}')
async def legacy_e(code):return RedirectResponse(f'/miniapp?code={code}',307)
@app.get('/w/{code}')
async def legacy_w(code):return RedirectResponse(f'/miniapp?code={code}',307)
@app.get('/miniapp/{code}',response_class=HTMLResponse)
async def miniapp_code(code):
    # Serve the app directly instead of redirecting. Telegram WebViews can
    # occasionally close/reopen the bot when a Mini App launch URL redirects.
    return FileResponse(STATIC/'index.html',media_type='text/html')
@app.get('/static/{name}')
async def static_file(name):
    p=(STATIC/name).resolve()
    if STATIC not in p.parents or not p.is_file():raise HTTPException(404)
    return FileResponse(p)
@app.get('/media/{code}')
async def media(code,idx:int=0):
    e=await active_exp(code)
    if not e or expired(e):raise HTTPException(410,'This Expression has expired.')
    ids=media_ids_for(e)
    if not ids:raise HTTPException(404,'Media not found')
    token=os.getenv('BOT_TOKEN','')
    if not token:raise HTTPException(503,'Media unavailable')
    import httpx; idx=max(0,min(idx,len(ids)-1))
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.get(f'https://api.telegram.org/bot{token}/getFile',params={'file_id':ids[idx]}); fp=(r.json().get('result') or {}).get('file_path') if r.status_code==200 else None
        if not fp:raise HTTPException(404,'Media not found')
        r=await c.get(f'https://api.telegram.org/file/bot{token}/{fp}')
        if r.status_code!=200:raise HTTPException(404,'Media not found')
        return Response(r.content,media_type=r.headers.get('content-type','application/octet-stream'),headers={'Cache-Control':'public,max-age=86400'})
@app.get('/audio/{code}')
async def audio(code,request:Request):
    e=await active_exp(code)
    if not e or expired(e):raise HTTPException(410,'This Expression has expired.')
    if not e.audio_file_id:raise HTTPException(404,'Audio not found')
    token=os.getenv('BOT_TOKEN','')
    if not token:raise HTTPException(503,'Audio unavailable')
    import httpx, mimetypes
    async with httpx.AsyncClient(timeout=30) as c:
        meta=await c.get(f'https://api.telegram.org/bot{token}/getFile',params={'file_id':e.audio_file_id})
        fp=(meta.json().get('result') or {}).get('file_path') if meta.status_code==200 else None
        if not fp:raise HTTPException(404,'Audio not found')
        r=await c.get(f'https://api.telegram.org/file/bot{token}/{fp}')
        if r.status_code!=200:raise HTTPException(404,'Audio not found')

    content=r.content
    total=len(content)
    mime=mimetypes.guess_type(fp)[0] or r.headers.get('content-type') or 'application/octet-stream'
    headers={'Accept-Ranges':'bytes','Cache-Control':'public,max-age=86400'}
    # Browser audio players may issue Range requests for seeking. Returning a 206
    # response here makes MP3/M4A/WAV/OGG playback much more reliable.
    rh=request.headers.get('range')
    if rh and rh.startswith('bytes='):
        spec=rh[6:].split(',',1)[0].strip()
        try:
            start_s,end_s=(spec.split('-',1)+[''])[:2]
            if start_s:
                start=int(start_s)
                end=int(end_s) if end_s else total-1
            else:
                length=int(end_s); start=max(0,total-length); end=total-1
            if start<0 or start>=total or end<start:
                raise ValueError
            end=min(end,total-1)
            chunk=content[start:end+1]
            headers.update({'Content-Range':f'bytes {start}-{end}/{total}','Content-Length':str(len(chunk))})
            return Response(chunk,status_code=206,media_type=mime,headers=headers)
        except ValueError:
            return Response(b'',status_code=416,media_type=mime,headers={'Content-Range':f'bytes */{total}'})
    headers['Content-Length']=str(total)
    return Response(content,media_type=mime,headers=headers)
@app.get('/api/experience/{code}')
async def experience(code):
    async with Session() as s:
        e=await s.scalar(select(Experience).where(Experience.code==code,Experience.published.is_(True)))
        if not e:raise HTTPException(404,'Expression not found')
        if expired(e):return {'expired':True,'code':e.code,'kind':e.kind,'title':e.title,'expires_at':e.expires_at.isoformat() if e.expires_at else None}
        e.views+=1;await s.commit(); theme=theme_for(e.kind); qs=questions_for(e)
        return {'expired':False,'code':e.code,'kind':e.kind,'title':e.title,'intro':e.intro,'body':e.body,'media':media_ids_for(e),'audio':bool(e.audio_file_id),'quiz': [{'question': q['question']} for q in qs] if e.kind in QUIZ_KINDS else [],'plays':e.plays,'views':e.views,'expires_at':e.expires_at.isoformat() if e.expires_at else None,'feedback_enabled':bool(e.feedback_enabled),'theme':{'name':theme[0],'accent':theme[1],'tagline':theme[2]}}
@app.get('/api/quiz/{code}/leaderboard')
async def leaderboard(code):
    e=await active_exp(code)
    if not e:raise HTTPException(404,'Expression not found')
    if expired(e):raise HTTPException(410,'This Expression has expired.')
    async with Session() as s:
        rows=(await s.scalars(select(QuizAttempt).where(QuizAttempt.expression_code==code).order_by(QuizAttempt.score.desc(),QuizAttempt.duration_ms.asc(),QuizAttempt.created_at.asc()).limit(50))).all()
        return {'items':[{'name':r.display_name or 'Anonymous','score':r.score,'total':r.total,'duration_ms':r.duration_ms} for r in rows]}
@app.post('/api/quiz/{code}/submit')
async def submit_quiz(code,payload:QuizSubmit):
    u=verify_init_data(payload.init_data)
    if not u:raise HTTPException(401,'Open this quiz inside Telegram.')
    async with Session() as s:
        e=await s.scalar(select(Experience).where(Experience.code==code,Experience.published.is_(True)))
        if not e:raise HTTPException(404,'Expression not found')
        if expired(e):raise HTTPException(410,'This Expression has expired.')
        qs=questions_for(e)
        if not qs:raise HTTPException(400,'This Expression has no quiz questions.')
        uid=int(u['id']); existing=await s.scalar(select(QuizAttempt).where(QuizAttempt.expression_code==code,QuizAttempt.telegram_id==uid))
        if existing:
            rank=(await s.scalar(select(func.count()).where(QuizAttempt.expression_code==code,QuizAttempt.score>existing.score))) or 0
            return {'already_submitted':True,'score':existing.score,'total':existing.total,'rank':rank+1}
        answers=payload.answers[:len(qs)]; score=sum(1 for q,a in zip(qs,answers) if q['answer'] and a.strip().casefold()==q['answer'].strip().casefold()); name=(u.get('first_name') or u.get('username') or 'Anonymous')[:80]
        s.add(QuizAttempt(expression_code=code,telegram_id=uid,display_name=name,score=score,total=len(qs),duration_ms=payload.duration_ms));e.plays+=1
        try:await s.commit()
        except Exception:
            await s.rollback(); existing=await s.scalar(select(QuizAttempt).where(QuizAttempt.expression_code==code,QuizAttempt.telegram_id==uid))
            if not existing:raise
            return {'already_submitted':True,'score':existing.score,'total':existing.total,'rank':1}
        rank=(await s.scalar(select(func.count()).where(QuizAttempt.expression_code==code,QuizAttempt.score>score))) or 0
        return {'already_submitted':False,'score':score,'total':len(qs),'rank':rank+1}
@app.post('/api/experience/{code}/message')
async def owner_message(code,payload:OwnerMessageIn):
    u=verify_init_data(payload.init_data)
    if not u:raise HTTPException(401,'Open this Experience inside Telegram.')
    e=await active_exp(code)
    if not e:raise HTTPException(404,'Expression not found')
    if expired(e):raise HTTPException(410,'This Expression has expired.')
    if not e.feedback_enabled:raise HTTPException(403,'Messages are disabled for this Experience.')
    uid=int(u['id']); text=payload.text.strip(); now=datetime.now(timezone.utc); name=(u.get('first_name') or u.get('username') or 'Anonymous')[:255]
    async with Session() as s:
        recent=await s.scalar(select(OwnerMessage).where(and_(OwnerMessage.expression_code==code,OwnerMessage.sender_id==uid,OwnerMessage.created_at>=now-timedelta(seconds=30))).order_by(OwnerMessage.id.desc()))
    if recent:raise HTTPException(429,'Please wait before sending another message.')
    token=os.getenv('BOT_TOKEN',''); delivered=False
    if token:
        import httpx
        msg=f'💌 <b>Pesan baru dari Experience</b>\n\n🌐 <b>{html.escape(e.title)}</b>\n🆔 <code>{html.escape(code)}</code>\n👤 {html.escape(name)}\n🆔 <code>{uid}</code>\n\n💬 {html.escape(text)}'
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r=await c.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':e.owner_id,'text':msg,'parse_mode':'HTML'}); delivered=bool(r.status_code==200 and r.json().get('ok'))
        except Exception:delivered=False
    async with Session() as s:s.add(OwnerMessage(expression_code=code,owner_id=e.owner_id,sender_id=uid,sender_name=name,text=text,delivered=delivered));await s.commit()
    if not delivered:raise HTTPException(502,'Message saved but could not be delivered to the creator right now.')
    return {'ok':True}
