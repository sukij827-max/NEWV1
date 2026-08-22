import json,asyncio,os
from datetime import datetime,timedelta,timezone
from aiogram import Router,F,Bot
from aiogram.filters import Command,CommandStart
from aiogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from config import settings
from db import *
from keyboards import *
router=Router();STATE={}
TYPES={'for_someone':'For Someone','best_friend':'Best Friend','birthday':'Birthday','confession':'Confession','appreciation':'Appreciation','memories':'Memories','event':'Event','anonymous':'Anonymous','interactive_game':'Interactive / Game'}
MOODS={'soft':'🤍 Soft','deep':'🖤 Deep','flirty':'😈 Flirty','shy':'🫣 Shy','emotional':'🥹 Emotional','chaotic':'😭 Chaotic','nostalgic':'🌙 Nostalgic','minimal':'✨ Minimal'}
def owner(uid):return uid==settings.owner_id
def public_url(code):
    d=os.getenv('RAILWAY_PUBLIC_DOMAIN','').strip();base=(d if d.startswith(('http://','https://')) else ('https://'+d if d else '')).rstrip('/');return f'{base}/app?code={code}' if base else ''
def miniapp_share_url(bot_username,code):
    return f'https://t.me/{bot_username}?startapp=exp_{code}'
async def joined(bot,uid):
    if owner(uid):return True
    try:return (await bot.get_chat_member(f'@{settings.channel_username}',uid)).status in {'member','administrator','creator'}
    except Exception:return False
async def gate(x,bot):
    await user(x.from_user);uid=x.from_user.id;u=await get_user(uid)
    if u and u.is_banned:
        if isinstance(x,CallbackQuery):await x.answer('🚫 Akun dibatasi owner.',show_alert=True)
        else:await x.answer('🚫 Akun dibatasi owner.')
        return False
    if not await joined(bot,uid):
        text='🔒 <b>Gabung channel dulu</b>\n\nKamu harus bergabung ke channel owner sebelum memakai bot.'
        if isinstance(x,CallbackQuery):await x.message.edit_text(text,reply_markup=join(settings.channel_username));await x.answer()
        else:await x.answer(text,reply_markup=join(settings.channel_username))
        return False
    return True
def reset(uid):STATE.pop(uid,None)
async def persist(uid):
    st=STATE.get(uid)
    if st:await save_draft(uid,st['kind'],st.get('step',''),json.dumps(st.get('data',{}),ensure_ascii=False))
def preview_text(st):
    d=st['data'];return f'👁️ <b>Preview</b>\n\nType: {TYPES.get(st["kind"],st["kind"])}\nMood: {MOODS.get(d.get("mood","minimal"))}\nPrivacy: {"Anonymous" if d.get("anonymous") else "Creator private"}\n\n<b>{d.get("title","")}</b>\n\n{d.get("intro","")}\n\n{d.get("body","")}'
@router.message(CommandStart())
async def start(m:Message,bot:Bot):
    await expire_premium();arg=m.text.split(' ',1)[1] if m.text and ' ' in m.text else ''
    if arg.startswith('exp_'):
        e=await get_exp(arg[4:])
        if not e:return await m.answer('❌ Expression tidak ditemukan.')
        u=public_url(e.code)
        await bump(e.code,'plays')
        if u:await m.answer(f'✨ <b>{e.title}</b>\n\n<a href="{u}">🌐 Buka Experience</a>')
        else:await m.answer(f'✨ <b>{e.title}</b>\n\n{e.intro}\n\n{e.body}')
        return
    if await gate(m,bot):await m.answer('✨ <b>GENZ EXPRESSION</b>\n\nCREATE → CUSTOMIZE → GENERATE → SHARE → EXPERIENCE',reply_markup=main(owner(m.from_user.id)))
@router.message(Command('menu'))
async def menu(m,bot):
    if await gate(m,bot):await m.answer('🏠 <b>Main Menu</b>',reply_markup=main(owner(m.from_user.id)))
@router.message(Command('help'))
async def help_(m,bot):
    if await gate(m,bot):await m.answer('ℹ️ <b>Help</b>\n\nCreate → Customize → Preview → Publish → Share. Draft tersimpan otomatis. /cancel membatalkan.')
@router.message(Command('cancel'))
async def cancel(m,bot):
    if await gate(m,bot):reset(m.from_user.id);await clear_draft(m.from_user.id);await m.answer('✅ Dibatalkan.',reply_markup=main(owner(m.from_user.id)))
@router.callback_query(F.data=='join_check')
async def join_check(c,bot):
    if await joined(bot,c.from_user.id):await c.message.edit_text('✅ <b>Sudah terverifikasi.</b>',reply_markup=main(owner(c.from_user.id)));await c.answer()
    else:await c.answer('❌ Belum terdeteksi bergabung.',show_alert=True)
@router.callback_query(F.data=='menu')
async def menu_cb(c,bot):
    if await gate(c,bot):await c.message.edit_text('🏠 <b>Main Menu</b>',reply_markup=main(owner(c.from_user.id)))
@router.callback_query(F.data=='create')
async def create(c,bot):
    if await gate(c,bot):await c.message.edit_text('✨ <b>Create Expression</b>\n\nPilih tipe.',reply_markup=cats())
@router.callback_query(F.data.startswith('cat_'))
async def cat(c,bot):
    if await gate(c,bot):await c.message.edit_text('✨ <b>Choose Type</b>',reply_markup=types(c.data[4:]))
@router.callback_query(F.data.startswith('type_'))
async def typ(c,bot):
    if not await gate(c,bot):return
    kind=c.data[5:];STATE[c.from_user.id]={'kind':kind,'step':'mood','data':{'anonymous':kind=='anonymous'}};await persist(c.from_user.id);await c.message.edit_text(f'✨ <b>{TYPES[kind]}</b>\n\nPilih mood/style.',reply_markup=moods())
@router.callback_query(F.data.startswith('mood_'))
async def mood(c,bot):
    if not await gate(c,bot):return
    st=STATE.get(c.from_user.id)
    if not st:return await c.answer('Session expired.',show_alert=True)
    if st.get('mode')=='edit_mood':
        p=await get_v2(st['code']);p['mood']=c.data[5:];await save_v2(st['code'],p);code=st['code'];reset(c.from_user.id);return await c.message.edit_text('✅ Mood diperbarui.',reply_markup=manage_exp(code))
    st['data']['mood']=c.data[5:];st['step']='title';await persist(c.from_user.id);await c.message.edit_text('✏️ <b>Judul</b>\n\nTulis judul singkat.')
@router.message(F.photo)
async def photo(m,bot):
    uid=m.from_user.id;st=STATE.get(uid)
    if not st or st.get('step')!='media' or st.get('data',{}).get('await_media')!='photo':return
    st['data']['media_items']=st['data'].get('media_items',[])+[m.photo[-1].file_id];st['data']['media']=m.photo[-1].file_id;st['step']='preview';await persist(uid);await m.answer('📸 Foto tersimpan.',reply_markup=preview_menu())
@router.message(F.audio)
async def audio(m,bot):
    uid=m.from_user.id;st=STATE.get(uid)
    if not st or st.get('step')!='media' or st.get('data',{}).get('await_media')!='audio':return
    st['data']['audio_file_id']=m.audio.file_id;st['step']='preview';await persist(uid);await m.answer('🎵 Audio tersimpan.',reply_markup=preview_menu())
@router.message(F.voice)
async def voice(m,bot):
    uid=m.from_user.id;st=STATE.get(uid)
    if not st or st.get('step')!='media' or st.get('data',{}).get('await_media')!='audio':return
    st['data']['audio_file_id']=m.voice.file_id;st['step']='preview';await persist(uid);await m.answer('🎵 Audio tersimpan.',reply_markup=preview_menu())
@router.callback_query(F.data=='media_photo')
async def media_photo(c,bot):
    if await gate(c,bot):STATE[c.from_user.id]['data']['await_media']='photo';await c.answer('Kirim foto sekarang.',show_alert=True)
@router.callback_query(F.data=='media_audio')
async def media_audio(c,bot):
    if await gate(c,bot):STATE[c.from_user.id]['data']['await_media']='audio';await c.answer('Kirim audio/voice sekarang.',show_alert=True)
@router.callback_query(F.data=='media_skip')
async def media_skip(c,bot):
    if await gate(c,bot):st=STATE.get(c.from_user.id);st['step']='preview';await persist(c.from_user.id);await c.message.edit_text(preview_text(st),reply_markup=preview_menu())
@router.message()
async def text(m:Message,bot:Bot):
    uid=m.from_user.id
    if not await gate(m,bot):return
    st=STATE.get(uid)
    if not st:return
    mode=st.get('mode')
    if mode in {'feedback','bug','report'}:
        if not m.text:return await m.answer('Kirim detail dalam teks.')
        f=await feedback(m.from_user,mode,m.text);await log(uid,'INFO',mode,m.text[:500]);reset(uid);await m.answer(f'✅ Diterima. ID laporan <code>#{f.id}</code>.');return
    if mode in {'edit_title','edit_intro','edit_body'}:
        v=(m.text or '').strip()
        if not v:return await m.answer('❌ Tidak boleh kosong.')
        field={'edit_title':'title','edit_intro':'intro','edit_body':'body'}[mode];v=v[:255] if field=='title' else v;code=st['code'];e=await update_exp(code,uid,**{field:v});reset(uid);await m.answer('✅ Disimpan.' if e else '❌ Tidak berwenang.',reply_markup=manage_exp(code));return
    if mode=='edit_anon':
        code=st['code'];p=await get_v2(code);p['anonymous']=(m.text or '').strip().lower() in {'yes','y','ya','1','true','anonymous'};p['owner_id']=None if p['anonymous'] else uid;await save_v2(code,p);reset(uid);await m.answer('✅ Privacy diperbarui.',reply_markup=manage_exp(code));return
    if mode=='premium' and owner(uid):
        p=(m.text or '').split()
        if len(p)!=2:return await m.answer('Format: TELEGRAM_ID HARI')
        try:ok=await set_premium(int(p[0]),None if int(p[1])==0 else datetime.now(timezone.utc)+timedelta(days=int(p[1])));reset(uid);await m.answer('💎 Premium berhasil diberikan.' if ok else '❌ User tidak ditemukan.')
        except ValueError:await m.answer('❌ Format salah.')
        return
    step=st.get('step')
    if step=='title':
        v=(m.text or '').strip()[:255]
        if not v:return await m.answer('❌ Judul wajib.')
        st['data']['title']=v;st['step']='intro';await persist(uid);await m.answer('📝 <b>Intro</b>\n\nTulis pembuka.')
    elif step=='intro':
        v=(m.text or '').strip()
        if not v:return await m.answer('❌ Intro wajib.')
        st['data']['intro']=v;st['step']='body';await persist(uid);await m.answer('💬 <b>Main Message</b>\n\nTulis pesan utama.')
    elif step=='body':
        v=(m.text or '').strip()
        if not v:return await m.answer('❌ Pesan wajib.')
        st['data']['body']=v;st['step']='questions' if st['kind']=='interactive_game' else 'media';await persist(uid);await m.answer('🎮 Kirim opsi dipisahkan dengan |' if st['kind']=='interactive_game' else '🖼️ Tambahkan media atau lewati.',reply_markup=None if st['kind']=='interactive_game' else media_menu())
    elif step=='questions':
        q=[x.strip() for x in (m.text or '').split('|') if x.strip()]
        if len(q)<2:return await m.answer('❌ Minimal 2 opsi.')
        st['data']['questions']=q[:20];st['step']='media';await persist(uid);await m.answer('🖼️ Tambahkan media atau lewati.',reply_markup=media_menu())
@router.callback_query(F.data=='preview')
async def preview(c,bot):
    if await gate(c,bot):
        st=STATE.get(c.from_user.id)
        if st:await c.message.edit_text(preview_text(st),reply_markup=preview_menu())
@router.callback_query(F.data=='publish')
async def publish(c,bot):
    if not await gate(c,bot):return
    uid=c.from_user.id;st=STATE.get(uid)
    if not st:return await c.answer('Draft tidak ditemukan.',show_alert=True)
    d=st['data'];missing=[x for x in ('title','intro','body') if not d.get(x)]
    if missing:return await c.answer('Lengkapi: '+', '.join(missing),show_alert=True)
    u=await get_user(uid);e=await create_exp(uid,st['kind'],d['title'],d['intro'],d['body'],json.dumps(d.get('questions',[])),d.get('media'))
    await save_v2(e.code,{'version':2,'kind':st['kind'],'mood':d.get('mood','minimal'),'anonymous':bool(d.get('anonymous')),'title':d['title'],'intro':d['intro'],'body':d['body'],'questions':d.get('questions',[]),'media_items':d.get('media_items',[]),'audio_file_id':d.get('audio_file_id'),'owner_id':None if d.get('anonymous') else uid,'creator_username':None if d.get('anonymous') else (u.username if u else None)})
    await clear_draft(uid);reset(uid);me=await c.bot.get_me();url=public_url(e.code);share=miniapp_share_url(me.username,e.code) if me.username else url
    if url:
        await c.message.edit_text(f'✨ <b>Your expression is ready.</b>\n\n🔗 <a href="{share}">Share this Expression</a>',reply_markup=manage_exp(e.code))
    else:
        await c.message.edit_text(f'✨ <b>Published.</b>\n\n🔗 <a href="{share}">Open / Share</a>',reply_markup=main(owner(uid)))
@router.callback_query(F.data=='cancel_wizard')
async def cancel_wizard(c,bot):
    if await gate(c,bot):reset(c.from_user.id);await clear_draft(c.from_user.id);await c.message.edit_text('✅ Dibatalkan.',reply_markup=main(owner(c.from_user.id)))
@router.callback_query(F.data=='mine')
async def mine(c,bot):
    if await gate(c,bot):
        es=await user_exps(c.from_user.id);await c.message.edit_text('📂 <b>My Expressions</b>\n\n'+('\n'.join(f'• {e.title} — <code>{e.code}</code> — 👁 {e.views} / ▶ {e.plays}' for e in es[:20]) if es else 'Belum ada.'),reply_markup=share_menu_kb(es))
@router.callback_query(F.data=='share_menu')
async def share_menu(c,bot):await mine(c,bot)
@router.callback_query(F.data.startswith('view_'))
async def view(c,bot):
    if not await gate(c,bot):return
    code=c.data[5:];e=await get_exp(code)
    if not e or e.owner_id!=c.from_user.id:return await c.answer('Tidak berwenang.',show_alert=True)
    await c.message.edit_text(f'🌐 <b>{e.title}</b>\n\nType: {e.kind}\nCode: <code>{code}</code>\nViews: {e.views}\nPlays: {e.plays}\n\n{public_url(code) or "Public domain belum tersedia"}',reply_markup=manage_exp(code))
@router.callback_query(F.data.startswith('open_'))
async def open_web(c,bot):
    if not await gate(c,bot):return
    code=c.data[5:];e=await get_exp(code)
    if not e or e.owner_id!=c.from_user.id:return await c.answer('Tidak berwenang.',show_alert=True)
    u=public_url(code)
    if u:await c.message.answer(f'🌐 <a href="{u}">Open Experience</a>')
    else:await c.answer('Public domain Railway belum tersedia.',show_alert=True)
@router.callback_query(F.data.startswith('edit_'))
async def edit(c,bot):
    if not await gate(c,bot):return
    code=c.data[5:];e=await get_exp(code)
    if not e or e.owner_id!=c.from_user.id:return await c.answer('Tidak berwenang.',show_alert=True)
    await c.message.edit_text(f'✏️ <b>Edit {e.title}</b>',reply_markup=edit_menu(code))
@router.callback_query(F.data.startswith('ed_title_'))
async def ed_title(c,bot):
    if await gate(c,bot):STATE[c.from_user.id]={'mode':'edit_title','code':c.data[9:]};await c.message.edit_text('Kirim judul baru.')
@router.callback_query(F.data.startswith('ed_intro_'))
async def ed_intro(c,bot):
    if await gate(c,bot):STATE[c.from_user.id]={'mode':'edit_intro','code':c.data[9:]};await c.message.edit_text('Kirim intro baru.')
@router.callback_query(F.data.startswith('ed_body_'))
async def ed_body(c,bot):
    if await gate(c,bot):STATE[c.from_user.id]={'mode':'edit_body','code':c.data[8:]};await c.message.edit_text('Kirim message baru.')
@router.callback_query(F.data.startswith('ed_mood_'))
async def ed_mood(c,bot):
    if await gate(c,bot):STATE[c.from_user.id]={'mode':'edit_mood','code':c.data[8:]};await c.message.edit_text('Pilih mood.',reply_markup=moods())
@router.callback_query(F.data.startswith('ed_anon_'))
async def ed_anon(c,bot):
    if await gate(c,bot):STATE[c.from_user.id]={'mode':'edit_anon','code':c.data[8:]};await c.message.edit_text('Ketik yes untuk anonymous atau no untuk menampilkan creator sebagai metadata private.')
@router.callback_query(F.data.startswith('delete_'))
async def delete(c,bot):
    if await gate(c,bot):
        ok=await delete_exp(c.data[7:],c.from_user.id);await c.message.edit_text('🗑️ Expression dihapus.' if ok else '❌ Tidak berwenang.',reply_markup=main(owner(c.from_user.id)))
@router.callback_query(F.data=='draft')
async def draft(c,bot):
    if await gate(c,bot):
        d=await get_draft(c.from_user.id);await c.message.edit_text(f'💾 <b>Draft</b>\n\n{d.kind+" / "+d.step if d else "Tidak ada draft."}',reply_markup=K([[('↩️ Menu','menu')]]))
@router.callback_query(F.data=='explore')
async def explore(c,bot):
    if await gate(c,bot):await c.message.edit_text('🎮 <b>Explore</b>\n\nBuka Expression melalui link creator.',reply_markup=K([[('↩️ Menu','menu')]]))
async def report_start(c,bot,mode,title):
    if await gate(c,bot):STATE[c.from_user.id]={'mode':mode};await c.message.edit_text(title+'\n\nKirim detail. /cancel untuk batal.')
for _d,_m,_t in [('feedback','feedback','💡 <b>Saran & Kritik</b>'),('bug','bug','🐛 <b>Laporkan Bug / Error</b>'),('report','report','🚨 <b>Report Konten</b>')]:
    async def _h(c,bot,mode=_m,title=_t):await report_start(c,bot,mode,title)
    router.callback_query(F.data==_d)(_h)
@router.callback_query(F.data=='feedback')
async def feedback_cb(c,bot):await report_start(c,bot,'feedback','💡 <b>Saran & Kritik</b>')
@router.callback_query(F.data=='bug')
async def bug_cb(c,bot):await report_start(c,bot,'bug','🐛 <b>Laporkan Bug</b>')
@router.callback_query(F.data=='report')
async def report_cb(c,bot):await report_start(c,bot,'report','🚨 <b>Report Konten</b>')
@router.callback_query(F.data=='premium')
async def premium(c,bot):
    if await gate(c,bot):await c.message.edit_text('💎 <b>Premium</b>\n\nUpgrade dilakukan manual oleh owner.',reply_markup=K([[('↩️ Menu','menu')]]))
@router.callback_query(F.data=='help')
async def help_cb(c,bot):
    if await gate(c,bot):await c.message.edit_text('ℹ️ <b>Help</b>\n\nCreate → Customize → Preview → Publish → Share.\nMobile-first. Audio optional.',reply_markup=K([[('↩️ Menu','menu')]]))
@router.callback_query(F.data=='owner')
async def owner_panel(c):
    if owner(c.from_user.id):await c.message.edit_text('👑 <b>Owner Panel</b>',reply_markup=owner_kb())
@router.callback_query(F.data=='a_stats')
async def a_stats(c):
    if owner(c.from_user.id):
        u,e,f=await stats();await c.message.edit_text(f'📊 <b>Dashboard</b>\n\n👥 Users: {u}\n✨ Expressions: {e}\n📥 Reports: {f}',reply_markup=owner_kb())
@router.callback_query(F.data=='a_users')
async def a_users(c):
    if owner(c.from_user.id):
        us=await recent_users();await c.message.edit_text('👥 <b>Users</b>\n\n'+('\n'.join(f'<code>{u.telegram_id}</code> @{u.username or "-"}' for u in us) or 'Kosong'),reply_markup=owner_kb())
@router.callback_query(F.data=='a_premium')
async def a_premium(c):
    if owner(c.from_user.id):STATE[c.from_user.id]={'mode':'premium'};await c.message.edit_text('💎 Kirim TELEGRAM_ID HARI.')
@router.callback_query(F.data=='a_broadcast')
async def a_broadcast(c):
    if owner(c.from_user.id):STATE[c.from_user.id]={'mode':'broadcast'};await c.message.edit_text('📣 Kirim broadcast.')
@router.callback_query(F.data.in_({'a_feedback','a_bug','a_report'}))
async def a_inbox(c,bot):
    if owner(c.from_user.id):
        fs=await open_feedback();await c.message.edit_text('📥 <b>Inbox</b>\n\n'+('\n'.join(f'#{f.id} [{f.kind}] {f.text[:200]}' for f in fs) or 'Kosong'),reply_markup=owner_kb())
@router.callback_query(F.data=='a_features')
async def a_features(c):
    if owner(c.from_user.id):await c.message.edit_text('⚙️ <b>Feature System</b>\n\nV2 core aktif.',reply_markup=owner_kb())
@router.callback_query(F.data=='a_health')
async def a_health(c):
    if owner(c.from_user.id):
        try:await stats();s='🟢 Database OK'
        except Exception as e:s='🔴 '+str(e)[:120]
        await c.message.edit_text(f'🩺 <b>Health</b>\n\n{s}\nBot: 🟢 RUNNING',reply_markup=owner_kb())
@router.callback_query(F.data=='a_logs')
async def a_logs(c):
    if owner(c.from_user.id):await c.message.edit_text('📜 Logs tersimpan di database.',reply_markup=owner_kb())
