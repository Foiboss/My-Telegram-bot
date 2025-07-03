import os
import sys
from io import BytesIO
import pandas as pd
from aiogram import types, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from BotInfo.handlers.antispam import antispam
from BotInfo.handlers.auth import delete_prev, remember_bot_msg

from ..config import export_cooldown
from ..db import query
from ..utils import only_role
from ..keyboards import admin_kb

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

router_export = Router()

# region Export users


# Export users (Russificated)
@router_export.message(lambda msg: msg.text == "📥 Выгрузить пользователей")
@only_role('admin')
@antispam(export_cooldown)
async def export_users_button(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    # Send fake command to export
    fake_msg = msg.copy(update={'text': '/export_users'})
    return await export_excel(fake_msg, **kwargs)


# Export users command
@router_export.message(Command('export_users'))
@only_role('admin')
@antispam(export_cooldown)
async def export_excel(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    rows = await query(
        'SELECT id, telegram_id, username, full_name, role, password FROM users'
    )
    df = pd.DataFrame(rows, columns=[
        'id', 'telegram_id', 'username', 'full_name', 'role', 'password'
    ])

    bio = BytesIO()
    with pd.ExcelWriter(bio, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='users')
    bio.seek(0)

    filename = 'users_export.xlsx'
    sent = await msg.answer_document(
        BufferedInputFile(bio.read(), filename=filename),
        caption='Экспорт данных пользователей в формате Excel',
        reply_markup=admin_kb
    )
    remember_bot_msg(msg.chat.id, sent.message_id)
    return

# endregion


# region Export activities

# Export activities (Russificated)
@router_export.message(lambda msg: msg.text == "📥 Выгрузить активности")
@only_role('admin')
@antispam(export_cooldown)
async def export_activities_button(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    # Send fake command to export
    fake_msg = msg.copy(update={'text': '/export_activities'})
    return await export_activities(fake_msg, **kwargs)


# Export activities command
@router_export.message(Command('export_activities'))
@only_role('admin')
@antispam(export_cooldown)
async def export_activities(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass
    """
    Экспортирует таблицу activities в Excel и отправляет файл в Telegram
    """
    rows = await query(
        '''
        SELECT id,
               student_id,
               telegram_id,
               full_name,
               title,
               event_status,
               cert_url,
               curator_full_name,
               confirmed
          FROM activities
        '''
    )
    df = pd.DataFrame(rows, columns=[
        'id', 'student_id', 'telegram_id', 'full_name',
        'title', 'event_status', 'cert_url',
        'curator_full_name',
        'confirmed'
    ])

    bio = BytesIO()
    with pd.ExcelWriter(bio, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='activities')
    bio.seek(0)

    filename = 'activities_export.xlsx'
    sent = await msg.answer_document(
        BufferedInputFile(bio.read(), filename=filename),
        caption='Экспорт данных заявок в формате Excel',
        reply_markup=admin_kb
    )
    remember_bot_msg(msg.chat.id, sent.message_id)
    return

# endregion
