import asyncio
import logging
from aiogram import Bot, Dispatcher, Router
from BotInfo.handlers.antispam import router_antispam, check_antispam_dict
from BotInfo.config import TOKEN, should_be_antispam_protected
from BotInfo.handlers.activities import router_activities
from BotInfo.handlers.admin import router_admin
from BotInfo.handlers.auth import router_auth
from BotInfo.handlers.export import router_export
from BotInfo.handlers.users import router_users
from BotInfo.db import init_db

tg_bot = Bot(TOKEN)
dp = Dispatcher()
router = Router()

logging.basicConfig(level=logging.INFO)


async def on_startup():
    if should_be_antispam_protected:
        dp.include_router(router_antispam)
        asyncio.create_task(check_antispam_dict())
    dp.include_router(router_activities)
    dp.include_router(router_admin)
    dp.include_router(router_auth)
    dp.include_router(router_export)
    dp.include_router(router_users)


async def main():
    await init_db()
    await on_startup()
    await dp.start_polling(tg_bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
