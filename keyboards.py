from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

def K(rows): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t,callback_data=d) for t,d in row] for row in rows])
def join(channel):
    rows=[]
    if channel: rows.append([InlineKeyboardButton(text='📢 JOIN CHANNEL',url=f'https://t.me/{channel.lstrip("@")}')])
    rows.append([InlineKeyboardButton(text='✅ SAYA SUDAH JOIN',callback_data='join_check')]); return InlineKeyboardMarkup(inline_keyboard=rows)
def main(owner=False):
    r=[[('✨ Buat Experience','create')],[('📂 Experience Saya','mine'),('💾 Draft','draft')],[('🎮 Jelajahi','explore')],[('💎 Premium','premium'),('💡 Saran/Kritik','feedback')],[('🐛 Laporkan Bug','bug'),('🚨 Report Konten','report')],[('ℹ️ Bantuan','help')]]
    if owner:r.append([('👑 Owner Panel','owner')])
    return K(r)
def cats(): return K([[('❤️ Cinta & Couple','cat_love'),('🫂 Friendship','cat_friend')],[('🎉 Event & Momen','cat_event'),('🎮 Mini Games','cat_game')],[('📸 Memories','cat_memory'),('🔥 Challenge','cat_challenge')],[('↩️ Menu','menu')]])
def types(c):
    m={'love':['confess','loveletter','anniversary','appreciation'],'friend':['friendship','bestiequiz','farewell','compat'],'event':['birthday','graduation','invitation','countdown'],'game':['quiz','wyr','tod','thisthat'],'memory':['memory','photostory','timeline'],'challenge':['challenge','30day','randomchallenge']}
    names={'confess':'💌 Confess','loveletter':'💖 Love Letter','anniversary':'💍 Anniversary','appreciation':'🥹 Appreciation','friendship':'🫂 Friendship','bestiequiz':'😂 Bestie Quiz','farewell':'🥲 Farewell','compat':'🧠 Compatibility','birthday':'🎂 Birthday','graduation':'🎓 Graduation','invitation':'🎊 Invitation','countdown':'🗓️ Countdown','quiz':'❓ Quiz','wyr':'🤔 Would You Rather','tod':'🎯 Truth or Dare','thisthat':'💭 This or That','memory':'📖 Memory Card','photostory':'📸 Photo Story','timeline':'🕰️ Timeline','challenge':'🔥 Challenge','30day':'💯 30-Day Challenge','randomchallenge':'🎲 Random Challenge'}
    return K([[ (names[x],f'type_{x}') ] for x in m[c]]+[[('↩️ Kembali','create')]])
def owner_kb(): return K([[('📊 Dashboard','a_stats'),('👥 Users','a_users')],[('💎 Premium','a_premium'),('📣 Broadcast','a_broadcast')],[('💡 Feedback','a_feedback'),('🐛 Bug Center','a_bug')],[('🚨 Reports','a_report'),('⚙️ Features','a_features')],[('🩺 Health','a_health'),('📜 Logs','a_logs')],[('↩️ Menu','menu')]])


def experience_share(code, base, bot_username):
    rows=[]
    if base:
        rows.append([InlineKeyboardButton(text='✨ Buka Experience', web_app=WebAppInfo(url=f'{base.rstrip("/")}/miniapp?code={code}'))])
    if bot_username:
        rows.append([InlineKeyboardButton(text='🔗 Link Share', url=f'https://t.me/{bot_username}?startapp=exp_{code}')])
    rows.append([InlineKeyboardButton(text='↩️ Menu', callback_data='menu')])
    return InlineKeyboardMarkup(inline_keyboard=rows)
