from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from urllib.parse import quote
from catalog import CATEGORIES, HELP

def K(rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t,callback_data=d) for t,d in row] for row in rows])

def join(channel):
    rows=[]
    if channel: rows.append([InlineKeyboardButton(text='📢 JOIN CHANNEL',url=f'https://t.me/{channel.lstrip("@")}')])
    rows.append([InlineKeyboardButton(text='✅ SAYA SUDAH JOIN',callback_data='join_check')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def main(owner=False):
    r=[[('✨ Buat Experience','create')],[('📂 Experience Saya','mine'),('💾 Draft','draft')],[('🎮 Jelajahi','explore')],[('💎 Premium','premium'),('💡 Saran/Kritik','feedback')],[('🐛 Laporkan Bug','bug'),('🚨 Report Konten','report')],[('ℹ️ Bantuan','help')]]
    if owner:r.append([('👑 Owner Panel','owner')])
    return K(r)

def cats():
    rows=[]
    items=list(CATEGORIES.items())
    for i in range(0,len(items),2):
        rows.append([(items[i][1]['title'],f'cat_{items[i][0]}')] + ([(items[i+1][1]['title'],f'cat_{items[i+1][0]}')] if i+1<len(items) else []))
    rows.append([('↩️ Menu','menu')])
    return K(rows)

def styles(category):
    c=CATEGORIES[category]
    rows=[[(label,f'style_{category}_{key}')] for key,(label,desc) in c['styles'].items()]
    rows.append([('↩️ Kembali','create')])
    return K(rows)

def methods(category,style):
    return K([[('✨ Quick Create',f'method_quick_{category}_{style}')],[('🛠️ Custom Create',f'method_custom_{category}_{style}')],[('❓ Bantuan','help')],[('↩️ Kembali',f'cat_{category}')]])

def help_menu():
    rows=[[(HELP['quick'][0],'help_quick'),(HELP['custom'][0],'help_custom')],[(HELP['story'][0],'help_story'),(HELP['letter'][0],'help_letter')],[(HELP['event'][0],'help_event'),(HELP['memories'][0],'help_memories')],[(HELP['play'][0],'help_play'),(HELP['audio'][0],'help_audio')],[(HELP['media'][0],'help_media'),(HELP['expiration'][0],'help_expiration')],[(HELP['share'][0],'help_share'),(HELP['message'][0],'help_message')],[(HELP['quiz'][0],'help_quiz')],[('↩️ Menu','menu')]]
    return K(rows)

def help_back(): return K([[('↩️ Bantuan','help')]])

def owner_kb(): return K([[('📊 Dashboard','a_stats'),('👥 Users','a_users')],[('💎 Premium','a_premium'),('📣 Broadcast','a_broadcast')],[('💡 Feedback','a_feedback'),('🐛 Bug Center','a_bug')],[('🚨 Reports','a_report'),('⚙️ Features','a_features')],[('🩺 Health','a_health'),('📜 Logs','a_logs')],[('↩️ Menu','menu')]])

def experience_share(code, base, bot_username, title='Experience'):
    rows=[]
    web_link=f'{base.rstrip("/")}/miniapp/{quote(code, safe="")}' if base else ''
    if web_link:
        rows.append([InlineKeyboardButton(text='✨ Buka Mini App', web_app=WebAppInfo(url=web_link))])
        share_url='https://t.me/share/url?url='+quote(web_link,safe='')+'&text='+quote(f'✨ {title}',safe='')
        rows.append([InlineKeyboardButton(text='📤 Bagikan ke orang lain',url=share_url)])
        if bot_username:
            rows.append([InlineKeyboardButton(text='🔗 Link Telegram',url=f'https://t.me/{bot_username}?startapp=exp_{quote(code,safe="")}')])
            rows.append([InlineKeyboardButton(text='🌐 Buka versi Web',url=web_link)])
    elif bot_username:
        main_link=f'https://t.me/{bot_username}?startapp=exp_{quote(code,safe="")}'
        rows.append([InlineKeyboardButton(text='✨ Buka Mini App',url=main_link)])
        rows.append([InlineKeyboardButton(text='📤 Bagikan ke orang lain',url='https://t.me/share/url?url='+quote(main_link,safe='')+'&text='+quote(f'✨ {title}',safe=''))])
    rows.append([InlineKeyboardButton(text='↩️ Menu',callback_data='menu')])
    return InlineKeyboardMarkup(inline_keyboard=rows)
