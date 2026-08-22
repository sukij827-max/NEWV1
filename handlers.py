import os, json, asyncio, re
from datetime import datetime, timedelta, timezone
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from config import settings
from db import *
from keyboards import *
from catalog import CATEGORIES, HELP

router=Router(); STATE={}
LEGACY_EXPIRATION_DEFAULTS={'confess':14,'loveletter':30,'anniversary':60,'appreciation':30,'friendship':60,'bestiequiz':30,'farewell':14,'compat':30,'birthday':30,'graduation':30,'invitation':14,'countdown':30,'quiz':30,'wyr':14,'tod':14,'thisthat':14,'memory':90,'photostory':90,'timeline':90,'challenge':30,'30day':45,'randomchallenge':14}
QUIZ_KINDS={'quiz','bestiequiz','compat','wyr','tod','thisthat','play:quizshow','play:whoknows'}

def owner(uid): return uid==settings.owner_id
async def joined(bot,uid):
    if owner(uid): return True
    try: return (await bot.get_chat_member(f'@{settings.channel_username}',uid)).status in {'member','administrator','creator'}
    except Exception: return False
async def gate(x,bot):
    await user(x.from_user); uid=x.from_user.id; u=await get_user(uid)
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

def default_expiration_days(kind):
    if kind in LEGACY_EXPIRATION_DEFAULTS: return LEGACY_EXPIRATION_DEFAULTS[kind]
    cat=kind.split(':',1)[0]
    return CATEGORIES.get(cat,{}).get('expiration',30)

def reset(uid): STATE.pop(uid,None)

def state_payload(st): return json.dumps(st.get('data',{}),ensure_ascii=False)

@router.message(CommandStart())
async def start(m:Message,bot:Bot):
    await expire_premium()
    if m.text and ' ' in m.text and m.text.split(' ',1)[1].startswith('exp_'):
        if not await gate(m,bot): return
        e=await get_exp(m.text.split(' ',1)[1][4:])
        if not e: await m.answer('❌ Experience tidak ditemukan.'); return
        await bump(e.code,'plays'); await bump(e.code,'views')
        await m.answer(f'✨ <b>{e.title}</b>\n\n{e.intro}\n\n{e.body}')
        if e.media_file_id:
            try:
                ids=json.loads(e.media_file_id) if str(e.media_file_id).startswith('[') else [e.media_file_id]
                for fid in ids[:10]: await m.answer_photo(fid)
            except Exception: pass
        qs=json.loads(e.questions or '[]')
        if qs: await m.answer('❓ <b>Pertanyaan</b>\n\n'+'\n'.join(f'{i+1}. {q.get("question",q) if isinstance(q,dict) else q}' for i,q in enumerate(qs)))
        return
    if await gate(m,bot): await m.answer('✨ <b>GENZ EXPRESSION</b>\n\nBuat Experience interaktif yang terasa hidup — story, letter, event, memories, atau game langsung dari Telegram.',reply_markup=main(owner(m.from_user.id)))

@router.message(Command('menu'))
async def menu(m,bot):
    if await gate(m,bot): await m.answer('🏠 <b>Menu Utama</b>',reply_markup=main(owner(m.from_user.id)))

@router.message(Command('help'))
async def help_(m,bot):
    if await gate(m,bot): await m.answer('ℹ️ <b>Bantuan GenZ Expression</b>\n\nPilih fitur dari menu Bantuan untuk melihat penjelasan singkat dan cara pakainya.',reply_markup=help_menu())

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
    if await gate(c,bot): await c.message.edit_text('✨ <b>Pilih tujuan Experience</b>\n\nKategori di sini berdasarkan fungsi, jadi setiap jenis punya pengalaman yang berbeda.',reply_markup=cats())

@router.callback_query(F.data.startswith('cat_'))
async def cat(c,bot):
    if not await gate(c,bot): return
    category=c.data[4:]
    if category not in CATEGORIES: await c.answer('Kategori tidak ditemukan.',show_alert=True); return
    desc=CATEGORIES[category]['desc']
    await c.message.edit_text(f"{CATEGORIES[category]['title']}\n\n{desc}\n\n🎨 <b>Pilih style</b>",reply_markup=styles(category))

@router.callback_query(F.data.startswith('style_'))
async def style(c,bot):
    if not await gate(c,bot): return
    _,category,style_key=c.data.split('_',2)
    label,desc=CATEGORIES[category]['styles'][style_key]
    await c.message.edit_text(f'{label}\n\n{desc}\n\n✨ <b>Pilih cara membuat:</b>\n\nQuick Create = cepat dan otomatis.\nCustom Create = lebih lengkap dan bisa diatur sendiri.',reply_markup=methods(category,style_key))

async def begin_builder(c,category,style_key,method):
    kind=f'{category}:{style_key}'
    STATE[c.from_user.id]={'kind':kind,'category':category,'style':style_key,'method':method,'step':'title','data':{'schema_version':1,'category':category,'style':style_key,'method':method}}
    await save_draft(c.from_user.id,kind,'title',state_payload(STATE[c.from_user.id]))
    await c.message.edit_text(f'✨ <b>{CATEGORIES[category]["title"]} · {CATEGORIES[category]["styles"][style_key][0]}</b>\n\n<b>{"Quick Create" if method=="quick" else "Custom Create"}</b>\n\n✏️ <b>Judul</b>\nNama yang akan tampil di awal Experience.\n\nKetik judul. /cancel untuk batal.')

@router.callback_query(F.data.startswith('method_'))
async def method(c,bot):
    if not await gate(c,bot): return
    _,method,category,style_key=c.data.split('_',3)
    await begin_builder(c,category,style_key,method)

async def ask(m,uid):
    st=STATE[uid]; cat=st.get('category'); method=st.get('method'); step=st['step']; days=default_expiration_days(st['kind'])
    if step=='title': text='✏️ <b>Judul</b>\nNama utama Experience yang muncul di opening.'
    elif step=='intro': text='📝 <b>Opening</b>\nKalimat pembuka yang muncul sebelum isi utama.'
    elif step=='quick_body': text='💬 <b>Isi utama</b>\nTulis pesan utama. Untuk Quick Create, template akan mengatur layout dan animasi otomatis.'
    elif step=='chapters': text='🎬 <b>Chapter</b>\nKirim satu chapter per pesan. Baris pertama = judul chapter, baris berikutnya = isi.\n\nContoh:\n<code>The Beginning\nHari itu semuanya dimulai...</code>\n\nKirim chapter berikutnya. Ketik /selesai kalau semua chapter sudah selesai.'
    elif step=='letter_body': text='💌 <b>Isi Surat</b>\nTulis pesan yang ingin dibaca penerima. Template akan membuat reveal surat secara otomatis.'
    elif step=='recipient': text='👤 <b>Untuk siapa?</b>\nNama panggilan atau sebutan penerima. Boleh tulis Anonymous.'
    elif step=='event_date': text='📅 <b>Tanggal & Waktu</b>\nUntuk countdown, gunakan format yang mudah dibaca seperti <code>2026-08-23 19:00</code>.\n\nKalau countdown tidak diperlukan, tulis tanggal biasa.'
    elif step=='event_details': text='🎉 <b>Detail Acara</b>\nTulis agenda, dress code, atau informasi penting lain.'
    elif step=='event_location': text='📍 <b>Lokasi</b>\nTulis tempat acara atau alamat. Bisa dikosongkan dengan /skip.'
    elif step=='rsvp': text='✅ <b>RSVP</b>\nTulis instruksi konfirmasi hadir. Contoh: “Konfirmasi hadir lewat @username”. Ketik /skip jika tidak diperlukan.'
    elif step=='memory_caption': text='📓 <b>Deskripsi</b>\nTulis kalimat pendek untuk memperkenalkan koleksi foto.'
    elif step=='questions': text='❓ <b>Pertanyaan</b>\nKirim soal + jawaban dalam satu pesan. Format 2 baris per soal, pisahkan antar soal dengan baris kosong. Bisa beberapa batch. Ketik /selesai jika semua soal selesai. Maksimal 20 soal. Format lama <code>pertanyaan::jawaban</code> tetap diterima.'
    elif step=='media': text='📸 <b>Media</b>\nKirim foto sebanyak yang kamu mau. Bisa juga kirim Audio/Voice/file audio di tahap ini. Ketik /selesai jika media sudah lengkap atau /skip jika tanpa media.'
    elif step=='expiration': text=f'⏳ <b>Expiration</b>\nDefault kategori ini: <b>{days} hari</b>.\n\nKetik <code>default</code>, 7, 14, 30, 60, 90, atau 0 untuk tanpa expiration.'
    elif step=='custom_options': text='🎨 <b>Detail Custom</b>\nTulis preferensi visual/animasi yang kamu inginkan. Contoh: “slow zoom, fade, dark, teks minimal”. Ketik /skip untuk otomatis.'
    else: text='✏️ <b>Isi data</b>\nKirim data untuk langkah ini.'
    await m.answer(text); await save_draft(uid,st['kind'],step,state_payload(st))

async def next_after_text(m,uid):
    st=STATE[uid]; cat=st['category']; method=st['method']; step=st['step']
    if step=='title': st['data']['title']=(m.text or '').strip()[:255]; st['step']='intro'
    elif step=='intro': st['data']['intro']=(m.text or '').strip(); st['step']='chapters' if cat=='story' else ('recipient' if cat=='letter' and method=='custom' else ('letter_body' if cat=='letter' else ('event_date' if cat=='event' else ('memory_caption' if cat=='memories' and method=='custom' else ('questions' if cat=='play' else 'quick_body')))))
    elif step=='quick_body': st['data']['body']=(m.text or '').strip(); st['step']='media'
    elif step=='chapters':
        lines=[x.strip() for x in (m.text or '').splitlines() if x.strip()]
        if len(lines)<2: await m.answer('❌ Chapter perlu minimal 2 baris: judul lalu isi.'); return
        st['data'].setdefault('chapters',[]).append({'title':lines[0][:120],'text':'\n'.join(lines[1:])[:3000]})
        await save_draft(uid,st['kind'],'chapters',state_payload(st)); await m.answer(f'🎬 Chapter diterima ({len(st["data"]["chapters"])}) . Kirim chapter lagi atau /selesai.'); return
    elif step=='recipient': st['data']['recipient']=(m.text or '').strip()[:255]; st['step']='letter_body'
    elif step=='letter_body': st['data']['body']=(m.text or '').strip(); st['step']='media'
    elif step=='event_date': st['data']['event_date']=(m.text or '').strip()[:120]; st['step']='event_location' if method=='custom' else 'event_details'
    elif step=='event_details': st['data']['event_details']=(m.text or '').strip(); st['step']='rsvp' if method=='custom' else 'media'
    elif step=='event_location':
        value=(m.text or '').strip(); st['data']['event_location']='' if value.lower()=='/skip' else value[:500]; st['step']='event_details'
    elif step=='rsvp':
        value=(m.text or '').strip(); st['data']['rsvp']='' if value.lower()=='/skip' else value; st['step']='media'
    elif step=='memory_caption': st['data']['body']=(m.text or '').strip(); st['step']='media'
    elif step=='questions':
        raw=m.text or ''
        if raw.lower() == '/selesai':
            if not st['data'].get('questions'): await m.answer('❌ Belum ada soal. Tambahkan minimal 1 soal dulu.'); return
            st['step']='media'; await ask(m,uid); return
        batch=parse_quiz_batch(raw)
        if not batch:
            await m.answer('❌ Format soal belum terbaca. Contoh:\n<code>siapa namaku?\nAnse\n\nwarna favoritku?\nHitam</code>\n\nAtau <code>pertanyaan::jawaban</code>.'); return
        current=st['data'].get('questions') or []; room=max(0,20-len(current)); added=batch[:room]; current.extend(added); st['data']['questions']=current[:20]
        await save_draft(uid,st['kind'],'questions',state_payload(st)); await m.answer(f'🧩 Soal diterima ({len(current)}/20). '+('Ketik /selesai untuk lanjut.' if len(current)>=20 else 'Kirim lagi atau /selesai.')); return
    elif step=='custom_options':
        value=(m.text or '').strip(); st['data']['custom_options']='' if value.lower()=='/skip' else value[:1500]; st['step']='expiration'
    else: return
    await save_draft(uid,st['kind'],st['step'],state_payload(st)); await ask(m,uid)

# Simplest format: every two non-empty lines are question/answer.
def parse_quiz_batch(text):
    out=[]
    if '::' in text:
        for part in re.split(r'\s*\|\s*|\n+',text):
            if '::' in part:
                q,a=part.split('::',1); q=q.strip(); a=a.strip()
                if q and a: out.append({'question':q,'answer':a})
        if out:return out
    lines=[x.strip() for x in text.splitlines() if x.strip()]; i=0
    while i<len(lines):
        if re.match(r'^pertanyaan\s*:',lines[i],re.I) and i+1<len(lines) and re.match(r'^jawaban\s*:',lines[i+1],re.I):
            q=re.sub(r'^pertanyaan\s*:\s*','',lines[i],flags=re.I); a=re.sub(r'^jawaban\s*:\s*','',lines[i+1],flags=re.I); i+=2
            if q.strip() and a.strip():out.append({'question':q.strip(),'answer':a.strip()})
        else:i+=1
    if out:return out
    if len(lines)%2:return []
    return [{'question':lines[i],'answer':lines[i+1]} for i in range(0,len(lines),2) if lines[i] and lines[i+1]][:20]

async def publish(m,uid):
    st=STATE.get(uid)
    if not st:return False
    d=st['data']; cat=st['category']; method=st['method']
    if not d.get('title') or not d.get('intro'):
        await m.answer('❌ Judul dan opening wajib diisi.'); return False
    if cat=='story' and not d.get('chapters'):
        d['body']=d.get('body') or d['intro'];
    elif cat=='letter': d['body']=d.get('body') or d.get('intro')
    elif cat=='event': d['body']=d.get('event_details') or d.get('intro')
    elif cat=='memories': d['body']=d.get('body') or d.get('intro')
    elif cat=='play': d['body']=d.get('body') or 'Interactive game — answer and submit once.'
    elif not d.get('body'): d['body']=d.get('intro')
    if cat=='play' and not d.get('questions'):
        await m.answer('❌ Tambahkan minimal 1 soal lalu /selesai.'); return False
    days=d.get('expiration_days',default_expiration_days(st['kind'])); expires_at=None if days==0 else datetime.now(timezone.utc)+timedelta(days=int(days))
    payload={'schema_version':1,'category':cat,'style':st['style'],'method':method,'intro':d.get('intro',''),'body':d.get('body',''),'chapters':d.get('chapters',[]),'recipient':d.get('recipient',''),'event_date':d.get('event_date',''),'event_location':d.get('event_location',''),'event_details':d.get('event_details',''),'rsvp':d.get('rsvp',''),'custom_options':d.get('custom_options','')}
    body='__GENZ_V4__'+json.dumps(payload,ensure_ascii=False)
    try:
        e=await create_exp(uid,st['kind'],d['title'],d['intro'],body,json.dumps(d.get('questions',[]),ensure_ascii=False),json.dumps(d.get('media',[]),ensure_ascii=False),d.get('audio'),expires_at)
    except Exception as exc:
        try: await log(uid,'ERROR','create_experience',str(exc)[:1000])
        except Exception: pass
        await m.answer('⚠️ Experience belum berhasil dibuat karena terjadi kesalahan pada database. Data kamu tetap tersimpan.'); return False
    await clear_draft(uid); reset(uid)
    me=await m.bot.get_me(); public_domain=os.getenv('RAILWAY_PUBLIC_DOMAIN','').strip()
    if public_domain and not public_domain.startswith(('http://','https://')): public_domain='https://'+public_domain
    exp_text='Tidak pernah' if not e.expires_at else (e.expires_at.replace(tzinfo=timezone.utc) if e.expires_at.tzinfo is None else e.expires_at).astimezone(timezone.utc).strftime('%d %b %Y %H:%M UTC')
    text=f'🎉 <b>Experience berhasil dibuat!</b>\n\n✨ {e.title}\n🆔 <code>{e.code}</code>\n⏳ Expired: <b>{exp_text}</b>\n\n✨ Setiap Experience punya desain dan alur sendiri sesuai kategori dan style.'
    kb=experience_share(e.code,public_domain,me.username,e.title) if public_domain else main(owner(uid))
    await m.answer(text,reply_markup=kb); return True

@router.callback_query(F.data.startswith('help_'))
async def help_detail(c,bot):
    if not await gate(c,bot): return
    key=c.data[5:]; item=HELP.get(key)
    if not item: await c.answer('Bantuan tidak ditemukan.',show_alert=True); return
    extra=''
    if key=='audio': extra='\n\nCara: pilih Tambah Audio saat builder → kirim Audio Telegram, VN, atau file audio → bot menyimpan audio dan lanjut.'
    elif key=='quiz': extra='\n\nCara: kirim beberapa batch soal → tambah lagi jika perlu → /selesai → media → expiration. Peserta hanya bisa submit sekali.'
    elif key=='message': extra='\n\nCara: penerima membuka Experience → isi pesan → Send to creator. Pesan diteruskan ke pembuat.'
    elif key=='expiration': extra='\n\nDefault berbeda per kategori. Kamu bisa memilih default, 7, 14, 30, 60, 90, atau 0.'
    await c.message.edit_text(f'{item[0]}\n\n{item[1]}{extra}',reply_markup=help_back())

@router.callback_query(F.data=='help')
async def help_cb(c,bot):
    if await gate(c,bot): await c.message.edit_text('ℹ️ <b>Bantuan GenZ Expression</b>\n\nPilih fitur untuk melihat apa fungsinya dan cara menggunakannya.',reply_markup=help_menu())

@router.message(F.audio | F.voice | F.document)
async def audio_upload(m:Message,bot:Bot):
    uid=m.from_user.id
    if not await gate(m,bot): return
    st=STATE.get(uid)
    if not st or st.get('step')!='media': await m.answer('⚠️ Saat ini bot tidak meminta audio.'); return
    obj=m.audio or m.voice or m.document
    if m.document:
        mime=(m.document.mime_type or '').lower(); name=(m.document.file_name or '').lower(); allowed_ext=('.mp3','.m4a','.mp4','.wav','.ogg','.oga','.opus','.flac','.aac','.webm')
        if not (mime.startswith('audio/') or name.endswith(allowed_ext)):
            await m.answer('❌ File ini bukan audio. Kirim MP3, M4A, WAV, OGG/OPUS, FLAC, AAC, atau Audio/Voice Telegram.'); return
    try:
        # Keep the Telegram file_id instead of a local path. This is portable across
        # Railway restarts/redeploys and lets the Mini App stream it through /audio/{code}.
        st['data']['audio']=obj.file_id
        await save_draft(uid,st['kind'],'media',state_payload(st))
        await m.answer('🎵 Audio diterima. Kirim foto lagi atau ketik /selesai untuk lanjut.')
    except Exception as e: await m.answer(f'❌ Audio gagal diproses. Coba kirim ulang.\n\n<code>{str(e)[:500]}</code>',parse_mode='HTML')

@router.message(F.text | F.photo)
async def collect(m:Message,bot:Bot):
    uid=m.from_user.id
    if not await gate(m,bot): return
    st=STATE.get(uid)
    if not st:
        return
    if st.get('mode') in {'feedback','bug','report'}:
        mode=st['mode']; f=await feedback(m.from_user,mode,m.text or ''); await log(uid,'INFO',mode,(m.text or '')[:500]); reset(uid); await m.answer('✅ Terima kasih. Sudah diterima.',reply_markup=main(owner(uid))); return
    if st.get('mode')=='broadcast':
        if not owner(uid):reset(uid);return
        users=await recent_users();ok=0
        for u in users:
            try:await bot.send_message(u.telegram_id,m.text or ' ');ok+=1
            except Exception:pass
            await asyncio.sleep(.03)
        reset(uid);await m.answer(f'📣 Selesai: {ok}/{len(users)}');return
    if st.get('mode')=='premium':
        if not owner(uid):reset(uid);return
        p=(m.text or '').split()
        if len(p)!=2:await m.answer('Format: TELEGRAM_ID HARI. HARI 0 = lifetime.');return
        try:
            target,days=int(p[0]),int(p[1]);until=None if days==0 else datetime.now(timezone.utc)+timedelta(days=days);await set_premium(target,until);reset(uid);await m.answer('💎 Premium berhasil diberikan.')
            try:await bot.send_message(target,'💎 <b>Premium kamu aktif!</b>')
            except Exception:pass
        except ValueError:await m.answer('❌ Format angka tidak valid.')
        return
    step=st['step']
    if step=='media':
        if m.text and m.text.lower()=='/skip': st['data']['media']=[]; st['step']='custom_options' if st.get('method')=='custom' else 'expiration'; await ask(m,uid); return
        if m.text and m.text.lower()=='/selesai':
            if st['category']=='play' and not st['data'].get('questions'): await m.answer('❌ Quiz belum punya soal. Tambahkan minimal 1 soal.'); return
            st['step']='custom_options' if st.get('method')=='custom' else 'expiration'; await save_draft(uid,st['kind'],'expiration',state_payload(st)); await ask(m,uid); return
        if m.photo:
            media=list(st['data'].get('media') or []); media.append(m.photo[-1].file_id); st['data']['media']=media[:50]; await save_draft(uid,st['kind'],'media',state_payload(st)); await m.answer(f'📸 Foto diterima ({len(media)}/50). Kirim lagi atau /selesai.'); return
        await m.answer('Kirim foto, audio/voice, /selesai, atau /skip.'); return
    if step=='custom_options':
        await next_after_text(m,uid); return
    if step=='expiration':
        raw=(m.text or '').strip().lower(); default=default_expiration_days(st['kind'])
        if raw=='default':days=default
        else:
            try:days=int(raw);assert days in {0,7,14,30,60,90}
            except Exception:await m.answer('❌ Pilih: default, 7, 14, 30, 60, 90, atau 0.');return
        st['data']['expiration_days']=days;await publish(m,uid);return
    if step=='chapters' and m.text and m.text.lower()=='/selesai':
        if not st['data'].get('chapters'):await m.answer('❌ Tambahkan minimal 1 chapter dulu.');return
        st['step']='media';await ask(m,uid);return
    if step=='questions' and m.text and m.text.lower()=='/selesai':
        if not st['data'].get('questions'):await m.answer('❌ Belum ada soal. Tambahkan minimal 1 soal dulu.');return
        st['step']='media';await ask(m,uid);return
    await next_after_text(m,uid)

@router.callback_query(F.data=='mine')
async def mine(c,bot):
    if not await gate(c,bot):return
    es=await user_exps(c.from_user.id);txt='📂 <b>Experience Saya</b>\n\n'+('\n'.join(f'• {e.title} — <code>{e.code}</code> — ▶️ {e.plays}' for e in es[:20]) if es else 'Belum ada.')
    await c.message.edit_text(txt,reply_markup=K([[('↩️ Menu','menu')]]))
@router.callback_query(F.data=='draft')
async def draft(c,bot):
    if not await gate(c,bot):return
    d=await get_draft(c.from_user.id);txt='💾 <b>Draft</b>\n\n'+(f'Jenis: {d.kind}\nStep: {d.step}' if d else 'Tidak ada draft.')
    await c.message.edit_text(txt,reply_markup=K([[('🗑️ Hapus','draft_clear')],[('↩️ Menu','menu')]]))
@router.callback_query(F.data=='draft_clear')
async def draft_clear(c,bot):
    if await gate(c,bot):await clear_draft(c.from_user.id);reset(c.from_user.id);await c.message.edit_text('🗑️ Draft dihapus.',reply_markup=main(owner(c.from_user.id)))
@router.callback_query(F.data=='explore')
async def explore(c,bot):
    if await gate(c,bot):await c.message.edit_text('🎮 <b>Jelajahi</b>\n\nExperience dimainkan melalui link yang dibagikan creator.',reply_markup=K([[('↩️ Menu','menu')]]))
@router.callback_query(F.data=='premium')
async def prem(c,bot):
    if not await gate(c,bot):return
    u=await get_user(c.from_user.id);status='🟢 Aktif' if u and u.is_premium else '⚪ Free';url=f'tg://user?id={settings.owner_id}'
    from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
    await c.message.edit_text(f'💎 <b>Premium</b>\n\nStatus: {status}\nUpgrade dilakukan manual oleh owner.',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='💬 HUBUNGI OWNER',url=url)],[InlineKeyboardButton(text='↩️ Menu',callback_data='menu')]]))

async def report_start(c,bot,mode,title):
    if await gate(c,bot):STATE[c.from_user.id]={'mode':mode};await c.message.edit_text(title+'\n\nKirim detail dalam satu pesan. /cancel untuk batal.')
for _d,_m,_t in [('feedback','feedback','💡 <b>Saran & Kritik</b>'),('bug','bug','🐛 <b>Laporkan Bug / Error</b>'),('report','report','🚨 <b>Report Konten</b>')]:
    async def _h(c,bot,mode=_m,title=_t):await report_start(c,bot,mode,title)
    router.callback_query(F.data==_d)(_h)
@router.callback_query(F.data=='owner')
async def owner_panel(c):
    if owner(c.from_user.id):await c.message.edit_text('👑 <b>Owner Panel</b>',reply_markup=owner_kb())
@router.callback_query(F.data=='a_stats')
async def a_stats(c):
    if not owner(c.from_user.id):return
    u,e,f=await stats();await c.message.edit_text(f'📊 <b>Dashboard</b>\n\n👥 Users: {u}\n✨ Experiences: {e}\n📥 Reports: {f}',reply_markup=owner_kb())
@router.callback_query(F.data=='a_users')
async def a_users(c):
    if not owner(c.from_user.id):return
    us=await recent_users();await c.message.edit_text('👥 <b>Users</b>\n\n'+'\n'.join(f'<code>{u.telegram_id}</code> @{u.username or "-"} {"💎" if u.is_premium else ""}' for u in us),reply_markup=owner_kb())
@router.callback_query(F.data=='a_premium')
async def a_premium(c):
    if owner(c.from_user.id):STATE[c.from_user.id]={'mode':'premium'};await c.message.edit_text('💎 Kirim <code>TELEGRAM_ID HARI</code>. Hari 0 = lifetime.')
@router.callback_query(F.data=='a_broadcast')
async def a_broadcast(c):
    if owner(c.from_user.id):STATE[c.from_user.id]={'mode':'broadcast'};await c.message.edit_text('📣 Kirim pesan broadcast. /cancel untuk batal.')
@router.callback_query(F.data.in_({'a_feedback','a_bug','a_report'}))
async def a_inbox(c):
    if not owner(c.from_user.id):return
    fs=await open_feedback();await c.message.edit_text('📥 <b>Inbox</b>\n\n'+('\n'.join(f'#{f.id} [{f.kind}] <code>{f.telegram_id}</code> @{f.username or "-"}\n{f.text[:200]}' for f in fs) if fs else 'Kosong.'),reply_markup=owner_kb())
@router.callback_query(F.data=='a_features')
async def a_features(c):
    if owner(c.from_user.id):await c.message.edit_text('⚙️ <b>Feature Toggle</b>\n\nGenZ Expression V4 Experience Builder aktif. SQL schema tetap kompatibel dengan V3.',reply_markup=owner_kb())
@router.callback_query(F.data=='a_health')
async def a_health(c):
    if not owner(c.from_user.id):return
    try:await stats();s='🟢 Database OK'
    except Exception as e:s='🔴 '+str(e)[:120]
    await c.message.edit_text(f'🩺 <b>Health Check</b>\n\n{s}\nBot: 🟢 RUNNING',reply_markup=owner_kb())
@router.callback_query(F.data=='a_logs')
async def a_logs(c):
    if owner(c.from_user.id):await c.message.edit_text('📜 Log event tersimpan di tabel logs dan runtime Railway.',reply_markup=owner_kb())
