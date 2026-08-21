import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from config import settings
from db import init_db, close_db
from handlers import router

async def main():
    logging.basicConfig(level=getattr(logging,settings.log_level.upper(),logging.INFO),format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    await init_db()
    bot=Bot(settings.bot_token,default=DefaultBotProperties(parse_mode=ParseMode.HTML)); dp=Dispatcher(); dp.include_router(router)
    await bot.set_my_commands([BotCommand(command='start',description='Mulai bot'),BotCommand(command='menu',description='Menu utama'),BotCommand(command='help',description='Bantuan'),BotCommand(command='cancel',description='Batalkan')])
    try: await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())
    finally: await bot.session.close(); await close_db()
if __name__=='__main__': asyncio.run(main())
