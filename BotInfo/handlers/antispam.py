import asyncio
from datetime import datetime, timedelta

from aiogram import types, Router
from aiogram.types import Message

from BotInfo.config import clear_dict_cooldown

router_antispam = Router()

# Global dictionary: telegram_id -> datetime of the last msg
last_message_time: dict[int, datetime] = {}


async def check_antispam_dict():
    """
    Clears dict from logs that are older than clear_dict_cooldown and clears them, then waits for clear_dict_cooldown
    """
    while True:
        now = datetime.now()

        # Get user_id, that have tim of the last msg older than clear_dict_cooldown
        to_delete = [
            user_id
            for user_id, last_time in last_message_time.items()
            if now - last_time > clear_dict_cooldown
        ]

        # Delete them from dictionary
        for user_id in to_delete:
            del last_message_time[user_id]

        # Wait for clear_dict_cooldown
        await asyncio.sleep(clear_dict_cooldown.total_seconds())


def antispam(cooldown: timedelta):
    """
    Creates decorator antispam with given cooldown
    :param cooldown: cooldown of antispam decorator
    """
    def decorator(func):
        async def wrapper(message: types.Message, *args, **kwargs):
            user_id = message.from_user.id
            handler_key = f"{message.chat.id}:{func.__name__}"
            now = datetime.now()
            last = last_message_time.get((user_id, handler_key))

            if last and now - last < cooldown:
                rem = (cooldown - (now - last)).seconds
                return await message.reply(f"⏳ Подождите ещё {rem} сек.")

            # Обновляем время последнего вызова
            last_message_time[(user_id, handler_key)] = now

            # Периодически чистим старые записи
            to_del = [
                key for key, t in last_message_time.items()
                if now - t > clear_dict_cooldown
            ]
            for key in to_del:
                last_message_time.pop(key, None)

            return await func(message, *args, **kwargs)

        return wrapper

    return decorator


async def handle_all_messages(message: Message, **kwargs):
    """
    Adds person to cooldown dictionary on messaging
    :param message: message of the person
    :param kwargs: args that gives dispetcher (**kwargs needed so function has right amount of args)
    """
    user_id = message.from_user.id
    now = datetime.now()
    # Обновляем время последнего сообщения
    last_message_time[user_id] = now
