
from __future__ import annotations
import html
import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

try:
    from db import Experience
except Exception:
    Experience = None

app = FastAPI(title="GenZ Expression V2", docs_url=None, redoc_url=None)

def db_url() -> Optional[str]:
    # Keep the V1 variable contract. Railway users can provide DATABASE_URL
    # when the existing V1 config already expects it; no V1 variable is renamed.
    candidates = ["DATABASE_URL", "POSTGRES_URL", "DB_URL"]
    for key in candidates:
        value = os.getenv(key)
        if value:
            return value
    return None

def normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url

async def fetch_expression(code: str) -> Any:
    if not Experience:
        return None
    url = db_url()
    if not url:
        return None
    engine = create_async_engine(normalize_db_url(url), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as session:
            result = await session.execute(
                select(Experience).where(Experience.code == code)
            )
            return result.scalar_one_or_none()
    finally:
        await engine.dispose()

def get_value(obj: Any, *names: str, default: Any = None) -> Any:
    if obj is None:
        return default
    for name in names:
        try:
            value = getattr(obj, name)
            if value is not None:
                return value
        except Exception:
            pass
    return default

def media_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value=value.strip()
        return [value] if value else []
    if isinstance(value, (list, tuple)):
        return [str(x) for x in value if str(x).strip()]
    return []

def page(exp: Any) -> str:
    title=html.escape(str(get_value(exp,"title","name",default="For you.")))
    intro=html.escape(str(get_value(exp,"intro","intro_text",default="someone made something for you.")))
    body=html.escape(str(get_value(exp,"body","message","content",default="")))
    raw_media = media_list(get_value(exp,"media_file_id","media","photos","images",default=[]))
    imgs="".join(
        f'<img src="/media/{html.escape(str(get_value(exp, "code", default="")))}" alt="" loading="lazy">'
        for _ in raw_media
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0A0A0A">
<meta name="description" content="{html.escape(intro, quote=True)}">
<title>{title} · GenZ Expression</title>
<style>
:root{{--bg:#0A0A0A;--surface:#111111;--text:#F5F5F5;--muted:#8A8A8A;--pink:#FF4F81;--purple:#A855F7}}
*{{box-sizing:border-box}}html,body{{margin:0;min-height:100%;background:var(--bg);color:var(--text)}}
body{{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;overflow-x:hidden}}
main{{width:min(760px,100%);margin:auto;padding:20px}}
.screen{{min-height:92vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:24px}}
.eyebrow{{font-size:12px;letter-spacing:.22em;color:var(--pink);text-transform:uppercase}}
h1{{font-size:clamp(44px,12vw,88px);line-height:.94;letter-spacing:-.055em;margin:0;overflow-wrap:anywhere}}
p{{max-width:640px;color:var(--muted);line-height:1.75;white-space:pre-wrap}}
button{{border:0;border-radius:999px;padding:14px 28px;background:linear-gradient(100deg,var(--pink),var(--purple));color:#fff;font-weight:750;font-size:16px;min-height:48px;cursor:pointer;box-shadow:0 10px 35px #ff4f8125}}
button:focus-visible{{outline:3px solid #fff;outline-offset:4px}}
.hidden{{display:none!important}}
.message{{font-size:clamp(23px,5.5vw,42px);line-height:1.25;white-space:pre-wrap;overflow-wrap:anywhere}}
.gallery{{display:grid;grid-template-columns:1fr;gap:14px;padding-bottom:30px}}
.gallery img{{width:100%;height:auto;max-height:75vh;object-fit:cover;border-radius:20px;background:var(--surface);display:block}}
.final{{min-height:60vh}}
@media (min-width:620px){{.gallery{{grid-template-columns:repeat(2,1fr)}}}}
@media (prefers-reduced-motion:reduce){{*{{scroll-behavior:auto!important;transition:none!important;animation:none!important}}}}
</style>
</head>
<body>
<main>
<section id="intro" class="screen">
<div class="eyebrow">✦ for you</div>
<h1>{title}</h1>
<p>{intro}</p>
<button type="button" onclick="reveal()">Open</button>
</section>
<section id="experience" class="hidden">
<div class="screen">
<div class="eyebrow">a little something</div>
<div class="message">{body}</div>
</div>
<div class="gallery">{imgs}</div>
<div class="screen final">
<p>that's it.<br>hope you felt what I meant.</p>
<button type="button" onclick="location.reload()">Replay</button>
</div>
</section>
</main>
<script>
function reveal(){{
 document.getElementById("intro").classList.add("hidden");
 document.getElementById("experience").classList.remove("hidden");
 window.scrollTo({{top:0,behavior:"smooth"}});
}}
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse("""<main style="background:#0A0A0A;color:#F5F5F5;min-height:100vh;display:grid;place-items:center;font-family:system-ui">
<div style="text-align:center"><div style="color:#FF4F81">✦ GENZ EXPRESSION</div><h1>Experience Layer</h1></div></main>""")

@app.get("/health")
async def health():
    return JSONResponse({"status":"ok","service":"genz-expression-web","version":"v2"})


@app.get("/media/{code}")
async def media(code: str):
    """Proxy the Telegram-hosted media without exposing the bot token."""
    exp = await fetch_expression(code)
    if exp is None:
        raise HTTPException(status_code=404, detail="Expression not found")
    file_id = get_value(exp, "media_file_id", "media", default=None)
    if not file_id:
        raise HTTPException(status_code=404, detail="Media not found")
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="Media unavailable")
    import httpx
    async with httpx.AsyncClient(timeout=20) as client:
        info = await client.get(f"https://api.telegram.org/bot{token}/getFile", params={"file_id": str(file_id)})
        if info.status_code != 200:
            raise HTTPException(status_code=404, detail="Media not found")
        data = info.json().get("result") or {}
        file_path = data.get("file_path")
        if not file_path:
            raise HTTPException(status_code=404, detail="Media not found")
        media_resp = await client.get(f"https://api.telegram.org/file/bot{token}/{file_path}")
        if media_resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Media not found")
        return Response(content=media_resp.content, media_type=media_resp.headers.get("content-type","application/octet-stream"))

@app.get("/e/{code}", response_class=HTMLResponse)
async def expression(code: str):
    code=code.strip()
    if not code or len(code)>128:
        raise HTTPException(status_code=404, detail="Expression not found")
    exp=await fetch_expression(code)
    if exp is None:
        raise HTTPException(status_code=404, detail="Expression not found")
    return HTMLResponse(page(exp))
