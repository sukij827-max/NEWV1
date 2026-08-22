import os
import json, asyncio
from datetime import datetime, timedelta, timezone
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from config import settings
from db import *
from keyboards import *
router=Router(); STATE={}

def owner(uid): return uid==settings.owner_id
async def joined(bot,uid):
    if owner(uid): return True
    try: return (await bot.get_chat_member(f"@{settings.channel_username}",uid)).status in {'member','administrator','creator'}
    except Exception: return False
async def gate(x,bot):
    await user(x.from_user); uid=x.from_user.id
    u=await get_user(uid)
    if u and u.is_banned:
        if isinstance(x,CallbackQuery): await x.answer('🚫 Akun dibatasi owner.',show_alert=True)
        else: await x.answer('🚫 Akun dibatasi owner.')
        return False
    if not await joined(bot,uid):
        text='🔒 <b>Gabung channel dulu</b>\n\nKamu harus bergabung ke channel owner sebelum memakai bot.'
        if isinstance(x,CallbackQuery): await x.message.edit_text(text,reply_markup=join(settings.channel_username)); await x.answer()
        else: await x.answer(text,reply_markup=join(settings.channel_username))
        return False
    return True


EXPIRATION_DEFAULTS={'confess':14,'loveletter':30,'anniversary':60,'appreciation':30,'friendship':60,'bestiequiz':30,'farewell':14,'compat':30,'birthday':30,'graduation':30,'invitation':14,'countdown':30,'quiz':30,'wyr':14,'tod':14,'thisthat':14,'memory':90,'photostory':90,'timeline':90,'challenge':30,'30day':45,'randomchallenge':14}
QUIZ_KINDS={'quiz','bestiequiz','compat','wyr','tod','thisthat'}
def default_expiration_days(kind): return EXPIRATION_DEFAULTS.get(kind,30)

def reset(uid): STATE.pop(uid,None)

@router.message(CommandStart())
async def start(m:Message,bot:Bot):
    await expire_premium()
    # Deep link: /start exp_CODE
    if m.text and ' ' in m.text and m.text.split(' ',1)[1].startswith('exp_'):
        if not await gate(m,bot): return
        e=await get_exp(m.text.split(' ',1)[1][4:])
        if not e: await m.answer('❌ Experience tidak ditemukan.'); return
        await bump(e.code,'plays'); await bump(e.code,'views')
        await m.answer(f'✨ <b>{e.title}</b>\n\n{e.intro}\n\n{e.body}')
        if e.media_file_id:
            try: await m.answer_photo(e.media_file_id)
            except Exception: pass
        qs=json.loads(e.questions or '[]')
        if qs: await m.answer('❓ <b>Pertanyaan</b>\n\n'+'\n'.join(f'{i+1}. {q}' for i,q in enumerate(qs)))
        return
    if await gate(m,bot): await m.answer('✨ <b>GENZ EXPERIENCE</b>\n\nBuat confession, anniversary, birthday, friendship, mini game, memories, challenge dan momen lainnya langsung di Telegram.',reply_markup=main(owner(m.from_user.id)))

@router.message(Command('menu'))
async def menu(m,bot):
    if await gate(m,bot): await m.answer('🏠 <b>Menu Utama</b>',reply_markup=main(owner(m.from_user.id)))
@router.message(Command('help'))
async def help_(m,bot):
    if await gate(m,bot): await m.answer('ℹ️ Pilih fitur dari menu. Draft tersimpan otomatis. /cancel untuk membatalkan proses.')
@router.message(Command('cancel'))
async def cancel(m,bot):
    if await gate(m,bot): reset(m.from_user.id); await clear_draft(m.from_user.id); await m.answer('✅ Dibatalkan.',reply_markup=main(owner(m.from_user.id)))

@router.callback_query(F.data=='join_check')
async def join_check(c,bot):
    if await joined(bot,c.from_user.id): await c.message.edit_text('✅ <b>Sudah terverifikasi.</b>',reply_markup=main(owner(c.from_user.id))); await c.answer()
    else: await c.answer('❌ Belum terdeteksi bergabung.',show_alert=True)
@router.callback_query(F.data=='menu')
async def menu_cb(c,bot):
    if await gate(c,bot): await c.message.edit_text('🏠 <b>Menu Utama</b>',reply_markup=main(owner(c.from_user.id)))
@router.callback_query(F.data=='create')
async def create(c,bot):
    if await gate(c,bot): await c.message.edit_text('✨ <b>Pilih kategori</b>',reply_markup=cats())
@router.callback_query(F.data.startswith('cat_'))
async def cat(c,bot):
    if await gate(c,bot): await c.message.edit_text('Pilih jenis experience:',reply_markup=types(c.data[4:]))
@router.callback_query(F.data.startswith('type_'))
async def typ(c,bot):
    if not await gate(c,bot): return
    kind=c.data[5:]; STATE[c.from_user.id]={'kind':kind,'step':'title','data':{}}; await save_draft(c.from_user.id,kind,'title','{}')
    await c.message.edit_text(f'✨ <b>{kind.replace("_"," ").title()}</b>\n\n✏️ <b>Judul</b>\nKetik judul. /cancel untuk batal.')

async def ask(m,uid):
    st=STATE[uid]; days=default_expiration_days(st['kind'])
    p={'intro':'📝 <b>Pembuka</b>\nTulis pembuka untuk experience.','body':'💬 <b>Isi utama</b>\nTulis pesan/isi yang akan dilihat penerima.','questions':'❓ <b>Pertanyaan</b>\nFormat: <code>pertanyaan::jawaban</code> dan pisahkan soal dengan <code>|</code>. Maksimal 20 soal.','media':'📸 <b>Media</b>\nKirim foto satu per satu. Untuk musik, kirim Audio Telegram, Voice Note, atau file audio sebagai Document (MP3/M4A/WAV/OGG/OPUS/FLAC/AAC). Ketik /selesai jika sudah.','expiration':f'⏳ <b>Expiration</b>\nDefault template ini: <b>{days} hari</b>.\n\nKetik: <code>default</code>, <code>7</code>, <code>14</code>, <code>30</code>, <code>60</code>, <code>90</code>, atau <code>0</code> untuk tanpa expiration.'}
    await m.answer(p[st['step']]); await save_draft(uid,st['kind'],st['step'],json.dumps(st['data'],ensure_ascii=False))
async def publish(m,uid):
    st=STATE[uid]; d=st['data']; missing=[x for x in ('title','intro','body') if not d.get(x)]
    if missing: await m.answer('❌ Field wajib kosong: '+', '.join(missing)); return
    days=d.get('expiration_days',default_expiration_days(st['kind']))
    expires_at=None if days==0 else datetime.now(timezone.utc)+timedelta(days=int(days))
    e=await create_exp(uid,st['kind'],d['title'],d['intro'],d['body'],json.dumps(d.get('questions',[]),ensure_ascii=False),json.dumps(d.get('media',[]),ensure_ascii=False),d.get('audio'),expires_at)
    await clear_draft(uid); reset(uid)
    me=await m.bot.get_me(); public_domain=os.getenv('RAILWAY_PUBLIC_DOMAIN','').strip()
    if public_domain and not public_domain.startswith(('http://','https://')): public_domain='https://'+public_domain
    if not e.expires_at:
        exp_text='Tidak pernah'
    else:
        exp_dt=e.expires_at
        if exp_dt.tzinfo is None:
            exp_dt=exp_dt.replace(tzinfo=timezone.utc)
        exp_text=exp_dt.astimezone(timezone.utc).strftime('%d %b %Y %H:%M UTC')
    if public_domain:
        await m.answer(f'🎉 <b>Experience berhasil dibuat!</b>\n\n✨ {e.title}\n🆔 <code>{e.code}</code>\n⏳ Expired: <b>{exp_text}</b>\n\nGunakan tombol di bawah untuk membuka Mini App atau membagikan Experience.',reply_markup=experience_share(e.code,public_domain,me.username,e.title))
    else:
        await m.answer(f'🎉 <b>Experience tersimpan!</b>\n\n✨ {e.title}\n🆔 <code>{e.code}</code>\n\n⚠️ Set <code>RAILWAY_PUBLIC_DOMAIN</code> agar Mini App dapat dibuka.',reply_markup=main(owner(uid)))

@router.message(F.audio | F.voice | F.document)
async def audio_upload(m:Message,bot:Bot):
    """Accept music from Telegram Audio, Voice Note, or an audio file sent as Document.

    This covers the common cases where a creator uploads a song from the phone,
    forwards an audio track from another Telegram chat/bot, or sends a voice note.
    Only actual audio documents are accepted.
    """
    uid=m.from_user.id
    if not await gate(m,bot): return
    st=STATE.get(uid)
    if not st or st.get('step')!='media':
        await m.answer('⚠️ Saat ini bot tidak meminta audio.')
        return

    obj=m.audio or m.voice or m.document
    if not obj:
        await m.answer('❌ Audio tidak terbaca. Kirim lagu sebagai Audio, Voice Note, atau file audio.')
        return

    if m.document:
        mime=(m.document.mime_type or '').lower()
        name=(m.document.file_name or '').lower()
        allowed_ext=('.mp3','.m4a','.mp4','.wav','.ogg','.oga','.opus','.flac','.aac','.webm')
        if not (mime.startswith('audio/') or name.endswith(allowed_ext)):
            await m.answer('❌ File ini bukan audio. Kirim MP3, M4A, WAV, OGG/OPUS, FLAC, AAC, atau gunakan Audio/Voice Telegram.')
            return

    # Telegram Bot API file downloads have a practical size limit; reject clearly
    # oversized media instead of saving a draft that can never be played.
    size=getattr(obj,'file_size',None)
    if size and size > 20*1024*1024:
        await m.answer('❌ Audio terlalu besar. Maksimal 20 MB untuk audio yang diproses bot ini.')
        return

    st['data']['audio']=obj.file_id
    st['data']['audio_source']='voice' if m.voice else ('document' if m.document else 'audio')
    await save_draft(uid,st['kind'],'media',json.dumps(st['data'],ensure_ascii=False))
    await m.answer('🎵 Audio diterima. Bisa kirim foto/audio lain atau /selesai untuk lanjut.\n\nSumber: '+('Voice Note 🎙️' if m.voice else 'File Telegram 📁' if m.document else 'Audio Telegram 🎵'))

@router.message()
async def text(m:Message,bot:Bot):
    uid=m.from_user.id
    if not await gate(m,bot): return
    st=STATE.get(uid)
    if not st: return
    mode=st.get('mode')
    if mode in {'feedback','bug','report'}:
        if not m.text: await m.answer('Kirim detail dalam teks.'); return
        f=await feedback(m.from_user,mode,m.text); await log(uid,'INFO',mode,m.text[:500]); reset(uid)
        await m.answer(f'✅ Diterima. ID laporan <code>#{f.id}</code>.')
        try: await bot.send_message(settings.owner_id,f'📥 <b>{mode.upper()} #{f.id}</b>\n👤 {m.from_user.full_name}\n🆔 <code>{uid}</code>\n@{m.from_user.username or "-"}\n\n{m.text[:3500]}')
        except Exception: pass
        return
    if mode=='broadcast':
        if not owner(uid): reset(uid); return
        users=await recent_users(100000); ok=0
        for u in users:
            try: await bot.send_message(u.telegram_id,m.text or ' '); ok+=1
            except Exception: pass
            await asyncio.sleep(.03)
        reset(uid); await m.answer(f'📣 Selesai: {ok}/{len(users)}'); return
    if mode=='premium':
        if not owner(uid): reset(uid); return
        p=(m.text or '').split()
        if len(p)!=2: await m.answer('Format: TELEGRAM_ID HARI. HARI 0 = lifetime.'); return
        try:
            target,days=int(p[0]),int(p[1]); until=None if days==0 else datetime.now(timezone.utc)+timedelta(days=days); await set_premium(target,until); reset(uid); await m.answer('💎 Premium berhasil diberikan.')
            try: await bot.send_message(target,'💎 <b>Premium kamu aktif!</b>')
            except Exception: pass
        except ValueError: await m.answer('❌ Format angka tidak valid.')
        return
    step=st['step']
    if step=='title': st['data']['title']=(m.text or '').strip()[:255]; st['step']='intro'; await ask(m,uid)
    elif step=='intro': st['data']['intro']=(m.text or '').strip(); st['step']='body'; await ask(m,uid)
    elif step=='body': st['data']['body']=(m.text or '').strip(); st['step']='questions' if st['kind'] in QUIZ_KINDS else 'media'; await ask(m,uid)
    elif step=='questions':
        raw=(m.text or '').strip(); qs=[x.strip() for x in raw.split('|') if x.strip()]
        if any('::' not in x for x in qs): await m.answer('❌ Setiap soal harus memakai format <code>pertanyaan::jawaban</code>.'); return
        st['data']['questions']=qs[:20]; st['step']='media'; await ask(m,uid)
    elif step=='media':
        if m.text and m.text.lower() in {'/skip','/selesai'}:
            if m.text.lower()=='/skip' and not st['data'].get('media'): st['data']['media']=None
            st['step']='expiration'; await ask(m,uid); return
        elif m.photo:
            media=list(st['data'].get('media') or []); media.append(m.photo[-1].file_id); st['data']['media']=media[:20]
            await save_draft(uid,st['kind'],'media',json.dumps(st['data'],ensure_ascii=False)); await m.answer(f'📸 Foto diterima ({len(media)}/20). Kirim lagi atau /selesai.'); return
        else: await m.answer('Kirim foto, /selesai, atau /skip.'); return
    elif step=='expiration':
        raw=(m.text or '').strip().lower(); default=default_expiration_days(st['kind'])
        if raw=='default': days=default
        else:
            try: days=int(raw); assert days in {0,7,14,30,60,90}
            except Exception: await m.answer('❌ Pilih: default, 7, 14, 30, 60, 90, atau 0.'); return
        st['data']['expiration_days']=days; await publish(m,uid); return

@router.callback_query(F.data=='mine')
async def mine(c,bot):
    if not await gate(c,bot): return
    es=await user_exps(c.from_user.id); txt='📂 <b>Experience Saya</b>\n\n'+('\n'.join(f'• {e.title} — <code>{e.code}</code> — ▶️ {e.plays}' for e in es[:20]) if es else 'Belum ada.')
    await c.message.edit_text(txt,reply_markup=K([[('↩️ Menu','menu')]]))
@router.callback_query(F.data=='draft')
async def draft(c,bot):
    if not await gate(c,bot): return
    d=await get_draft(c.from_user.id); txt='💾 <b>Draft</b>\n\n'+(f'Jenis: {d.kind}\nStep: {d.step}' if d else 'Tidak ada draft.')
    await c.message.edit_text(txt,reply_markup=K([[('🗑️ Hapus','draft_clear')],[('↩️ Menu','menu')]]))
@router.callback_query(F.data=='draft_clear')
async def draft_clear(c,bot):
    if await gate(c,bot): await clear_draft(c.from_user.id); reset(c.from_user.id); await c.message.edit_text('🗑️ Draft dihapus.',reply_markup=main(owner(c.from_user.id)))
@router.callback_query(F.data=='explore')
async def explore(c,bot):
    if await gate(c,bot): await c.message.edit_text('🎮 <b>Jelajahi</b>\n\nExperience dimainkan melalui link yang dibagikan creator.',reply_markup=K([[('↩️ Menu','menu')]]))
@router.callback_query(F.data=='premium')
async def prem(c,bot):
    if not await gate(c,bot): return
    u=await get_user(c.from_user.id); status='🟢 Aktif' if u and u.is_premium else '⚪ Free'; url=f'tg://user?id={settings.owner_id}'
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    await c.message.edit_text(f'💎 <b>Premium</b>\n\nStatus: {status}\nUpgrade dilakukan manual oleh owner.',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='💬 HUBUNGI OWNER',url=url)],[InlineKeyboardButton(text='↩️ Menu',callback_data='menu')]]))
async def report_start(c,bot,mode,title):
    if await gate(c,bot): STATE[c.from_user.id]={'mode':mode}; await c.message.edit_text(title+'\n\nKirim detail dalam satu pesan. /cancel untuk batal.')
for _d,_m,_t in [('feedback','feedback','💡 <b>Saran & Kritik</b>'),('bug','bug','🐛 <b>Laporkan Bug / Error</b>'),('report','report','🚨 <b>Report Konten</b>')]:
    async def _h(c,bot,mode=_m,title=_t): await report_start(c,bot,mode,title)
    router.callback_query(F.data==_d)(_h)
@router.callback_query(F.data=='help')
async def help_cb(c,bot):
    if await gate(c,bot): await c.message.edit_text('ℹ️ <b>Bantuan</b>\n\nPilih fitur dari menu. Draft tersimpan otomatis. /cancel membatalkan.',reply_markup=K([[('↩️ Menu','menu')]]))

@router.callback_query(F.data=='owner')
async def owner_panel(c):
    if owner(c.from_user.id): await c.message.edit_text('👑 <b>Owner Panel</b>',reply_markup=owner_kb())
@router.callback_query(F.data=='a_stats')
async def a_stats(c):
    if not owner(c.from_user.id): return
    u,e,f=await stats(); await c.message.edit_text(f'📊 <b>Dashboard</b>\n\n👥 Users: {u}\n✨ Experiences: {e}\n📥 Reports: {f}',reply_markup=owner_kb())
@router.callback_query(F.data=='a_users')
async def a_users(c):
    if not owner(c.from_user.id): return
    us=await recent_users(); await c.message.edit_text('👥 <b>Users</b>\n\n'+'\n'.join(f'<code>{u.telegram_id}</code> @{u.username or "-"} {"💎" if u.is_premium else ""}' for u in us),reply_markup=owner_kb())
@router.callback_query(F.data=='a_premium')
async def a_premium(c):
    if owner(c.from_user.id): STATE[c.from_user.id]={'mode':'premium'}; await c.message.edit_text('💎 Kirim <code>TELEGRAM_ID HARI</code>. Hari 0 = lifetime.')
@router.callback_query(F.data=='a_broadcast')
async def a_broadcast(c):
    if owner(c.from_user.id): STATE[c.from_user.id]={'mode':'broadcast'}; await c.message.edit_text('📣 Kirim pesan broadcast. /cancel untuk batal.')
@router.callback_query(F.data.in_({'a_feedback','a_bug','a_report'}))
async def a_inbox(c):
    if not owner(c.from_user.id): return
    fs=await open_feedback(); await c.message.edit_text('📥 <b>Inbox</b>\n\n'+('\n'.join(f'#{f.id} [{f.kind}] <code>{f.telegram_id}</code> @{f.username or "-"}\n{f.text[:200]}' for f in fs) if fs else 'Kosong.'),reply_markup=owner_kb())
@router.callback_query(F.data=='a_features')
async def a_features(c):
    if owner(c.from_user.id): await c.message.edit_text('⚙️ <b>Feature Toggle</b>\n\nV1 fitur inti aktif. Toggle lanjutan dapat ditambahkan tanpa mengubah data user.',reply_markup=owner_kb())
@router.callback_query(F.data=='a_health')
async def a_health(c):
    if not owner(c.from_user.id): return
    try: await stats(); s='🟢 Database OK'
    except Exception as e: s='🔴 '+str(e)[:120]
    await c.message.edit_text(f'🩺 <b>Health Check</b>\n\n{s}\nBot: 🟢 RUNNING',reply_markup=owner_kb())
@router.callback_query(F.data=='a_logs')
async def a_logs(c):
    if owner(c.from_user.id): await c.message.edit_text('📜 Log event tersimpan di tabel logs dan runtime Railway.',reply_markup=owner_kb())
