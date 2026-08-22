import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, select, func, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from config import settings

def now(): return datetime.now(timezone.utc)
engine=create_async_engine(settings.database_url,pool_pre_ping=True,pool_recycle=1800)
Session=async_sessionmaker(engine,expire_on_commit=False)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'; id:Mapped[int]=mapped_column(Integer,primary_key=True); telegram_id:Mapped[int]=mapped_column(BigInteger,unique=True,index=True); username:Mapped[Optional[str]]=mapped_column(String(255)); first_name:Mapped[str]=mapped_column(String(255),default=''); is_premium:Mapped[bool]=mapped_column(Boolean,default=False); premium_until:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True)); is_banned:Mapped[bool]=mapped_column(Boolean,default=False); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); last_seen:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Experience(Base):
    __tablename__='experiences'; id:Mapped[int]=mapped_column(Integer,primary_key=True); code:Mapped[str]=mapped_column(String(32),unique=True,index=True); owner_id:Mapped[int]=mapped_column(BigInteger,index=True); kind:Mapped[str]=mapped_column(String(60)); title:Mapped[str]=mapped_column(String(255)); intro:Mapped[str]=mapped_column(Text,default=''); body:Mapped[str]=mapped_column(Text,default=''); questions:Mapped[str]=mapped_column(Text,default='[]'); media_file_id:Mapped[Optional[str]]=mapped_column(Text); published:Mapped[bool]=mapped_column(Boolean,default=True); views:Mapped[int]=mapped_column(Integer,default=0); plays:Mapped[int]=mapped_column(Integer,default=0); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Draft(Base):
    __tablename__='drafts'; id:Mapped[int]=mapped_column(Integer,primary_key=True); owner_id:Mapped[int]=mapped_column(BigInteger,unique=True,index=True); kind:Mapped[str]=mapped_column(String(60)); step:Mapped[str]=mapped_column(String(40)); data:Mapped[str]=mapped_column(Text,default='{}'); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Feedback(Base):
    __tablename__='feedback'; id:Mapped[int]=mapped_column(Integer,primary_key=True); telegram_id:Mapped[int]=mapped_column(BigInteger,index=True); username:Mapped[Optional[str]]=mapped_column(String(255)); first_name:Mapped[str]=mapped_column(String(255),default=''); kind:Mapped[str]=mapped_column(String(30)); text:Mapped[str]=mapped_column(Text); status:Mapped[str]=mapped_column(String(20),default='open'); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Log(Base):
    __tablename__='logs'; id:Mapped[int]=mapped_column(Integer,primary_key=True); telegram_id:Mapped[Optional[int]]=mapped_column(BigInteger); level:Mapped[str]=mapped_column(String(20)); event:Mapped[str]=mapped_column(String(100)); details:Mapped[str]=mapped_column(Text,default=''); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Setting(Base):
    __tablename__='settings'; key:Mapped[str]=mapped_column(String(100),primary_key=True); value:Mapped[str]=mapped_column(Text,default='')
class ExperienceV2(Base):
    __tablename__='experience_v2'; id:Mapped[int]=mapped_column(Integer,primary_key=True); expression_code:Mapped[str]=mapped_column(String(32),unique=True,index=True); payload:Mapped[str]=mapped_column(Text,default='{}'); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class LeaderboardEntry(Base):
    __tablename__='leaderboard_entries'; id:Mapped[int]=mapped_column(Integer,primary_key=True); expression_code:Mapped[str]=mapped_column(String(32),index=True); telegram_id:Mapped[Optional[int]]=mapped_column(BigInteger,index=True); name:Mapped[str]=mapped_column(String(80),default='Anonymous'); score:Mapped[int]=mapped_column(Integer,default=0); total:Mapped[int]=mapped_column(Integer,default=0); elapsed:Mapped[int]=mapped_column(Integer,default=0); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
async def init_db():
    async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
async def close_db(): await engine.dispose()
async def user(tg):
    async with Session() as s:
        u=await s.scalar(select(User).where(User.telegram_id==tg.id))
        if not u:u=User(telegram_id=tg.id,username=tg.username,first_name=tg.first_name or '');s.add(u)
        else:u.username=tg.username;u.first_name=tg.first_name or '';u.last_seen=now()
        await s.commit();return u
async def get_user(uid):
    async with Session() as s:return await s.scalar(select(User).where(User.telegram_id==uid))
async def expire_premium():
    async with Session() as s:await s.execute(update(User).where(User.is_premium.is_(True),User.premium_until.is_not(None),User.premium_until<now()).values(is_premium=False,premium_until=None));await s.commit()
async def set_premium(uid,until):
    async with Session() as s:
        u=await s.scalar(select(User).where(User.telegram_id==uid))
        if not u:return False
        u.is_premium=True;u.premium_until=until;await s.commit();return True
async def create_exp(uid,kind,title,intro,body,questions,media):
    import secrets
    async with Session() as s:
        code=secrets.token_hex(4)
        while await s.scalar(select(Experience.id).where(Experience.code==code)):code=secrets.token_hex(4)
        e=Experience(code=code,owner_id=uid,kind=kind,title=title,intro=intro,body=body,questions=questions,media_file_id=media);s.add(e);await s.commit();await s.refresh(e);return e
async def update_exp(code,uid,**values):
    async with Session() as s:
        e=await s.scalar(select(Experience).where(Experience.code==code,Experience.owner_id==uid))
        if not e:return None
        for k,v in values.items():
            if hasattr(e,k):setattr(e,k,v)
        await s.commit();await s.refresh(e);return e
async def delete_exp(code,uid):
    async with Session() as s:
        e=await s.scalar(select(Experience).where(Experience.code==code,Experience.owner_id==uid))
        if not e:return False
        await s.delete(e);await s.execute(delete(ExperienceV2).where(ExperienceV2.expression_code==code));await s.commit();return True
async def get_exp(code):
    async with Session() as s:return await s.scalar(select(Experience).where(Experience.code==code))
async def user_exps(uid):
    async with Session() as s:return list(await s.scalars(select(Experience).where(Experience.owner_id==uid).order_by(Experience.id.desc())))
async def bump(code,field):
    if field not in {'views','plays'}:return
    async with Session() as s:
        e=await s.scalar(select(Experience).where(Experience.code==code))
        if e:setattr(e,field,getattr(e,field)+1);await s.commit()
async def save_draft(uid,kind,step,data):
    async with Session() as s:
        d=await s.scalar(select(Draft).where(Draft.owner_id==uid))
        if not d:d=Draft(owner_id=uid,kind=kind,step=step,data=data);s.add(d)
        else:d.kind=kind;d.step=step;d.data=data;d.updated_at=now()
        await s.commit()
async def get_draft(uid):
    async with Session() as s:return await s.scalar(select(Draft).where(Draft.owner_id==uid))
async def clear_draft(uid):
    async with Session() as s:
        d=await s.scalar(select(Draft).where(Draft.owner_id==uid))
        if d:await s.delete(d);await s.commit()
async def feedback(tg,kind,text):
    async with Session() as s:
        f=Feedback(telegram_id=tg.id,username=tg.username,first_name=tg.first_name or '',kind=kind,text=text);s.add(f);await s.commit();await s.refresh(f);return f
async def log(uid,level,event,details=''):
    async with Session() as s:s.add(Log(telegram_id=uid,level=level,event=event,details=details));await s.commit()
async def stats():
    async with Session() as s:return tuple((await s.scalar(select(func.count()).select_from(q))) or 0 for q in [User,Experience,Feedback])
async def recent_users(limit=20):
    async with Session() as s:return list(await s.scalars(select(User).order_by(User.last_seen.desc()).limit(limit)))
async def open_feedback(limit=20):
    async with Session() as s:return list(await s.scalars(select(Feedback).where(Feedback.status=='open').order_by(Feedback.id.desc()).limit(limit)))
async def set_feature(key,value):
    async with Session() as s:
        x=await s.get(Setting,key)
        if not x:s.add(Setting(key=key,value=value))
        else:x.value=value
        await s.commit()
async def get_feature(key,default='1'):
    async with Session() as s:
        x=await s.get(Setting,key);return x.value if x else default
async def save_v2(code,payload):
    async with Session() as s:
        x=await s.scalar(select(ExperienceV2).where(ExperienceV2.expression_code==code));raw=json.dumps(payload,ensure_ascii=False)
        if not x:x=ExperienceV2(expression_code=code,payload=raw);s.add(x)
        else:x.payload=raw;x.updated_at=now()
        await s.commit()
async def get_v2(code):
    async with Session() as s:
        x=await s.scalar(select(ExperienceV2).where(ExperienceV2.expression_code==code))
        if not x:return {}
        try:return json.loads(x.payload or '{}')
        except Exception:return {}

async def submit_score(code,telegram_id,name,score,total,elapsed):
    async with Session() as s:
        e=LeaderboardEntry(expression_code=code,telegram_id=telegram_id,name=name,score=score,total=total,elapsed=elapsed);s.add(e);await s.commit();await s.refresh(e);return {'id':e.id,'name':e.name,'score':e.score,'total':e.total,'elapsed':e.elapsed}

async def leaderboard(code,limit=20):
    async with Session() as s:
        rows=list(await s.scalars(select(LeaderboardEntry).where(LeaderboardEntry.expression_code==code).order_by(LeaderboardEntry.score.desc(),LeaderboardEntry.elapsed.asc(),LeaderboardEntry.id.asc()).limit(limit)))
        return [{'name':x.name,'score':x.score,'total':x.total,'elapsed':x.elapsed} for x in rows]
