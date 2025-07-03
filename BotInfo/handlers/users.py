import os
import sys
from aiogram import types, Router
from aiogram.filters import Command
from BotInfo.handlers.antispam import antispam
from BotInfo.handlers.auth import delete_prev, last_bot_msg_del
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from ..config import message_cooldown
from ..keyboards import student_kb, main, admin_kb, curator_kb
from ..db import query, execute
from ..utils import only_role

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


router_users = Router()


# States declaration
class ChangeUserData(StatesGroup):
    waiting_for_passwords = State()
    waiting_for_full_name = State()


# region Change Password

# Change password
@router_users.message(lambda msg: msg.text == "Изменить пароль")
@only_role('student', 'curator')
@antispam(message_cooldown)
async def change_password_start(msg: types.Message, state: FSMContext, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    row_role = await query(
        "SELECT role FROM users WHERE telegram_id = ?",
        (msg.from_user.id,),
        one=True
    )
    role = row_role['role'] if row_role else None
    kb = student_kb if role == 'student' else curator_kb

    sent = await msg.answer(
        "🛡️ Введите старый и новый пароли через пробел:\n"
        "<старый_пароль> <новый_пароль>",
        reply_markup=kb
    )
    last_bot_msg_del[msg.chat.id] = sent.message_id

    await state.set_state(ChangeUserData.waiting_for_passwords)


# changing password step
@router_users.message(ChangeUserData.waiting_for_passwords)
@only_role('student', 'curator')
async def process_passwords(msg: types.Message, state: FSMContext, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    row_role = await query(
        "SELECT role FROM users WHERE telegram_id = ?",
        (msg.from_user.id,),
        one=True
    )
    role = row_role['role'] if row_role else None
    kb = student_kb if role == 'student' else curator_kb

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        sent = await msg.answer(
            "❗ Формат неправильный. Нужно: <старый_пароль> <новый_пароль>", reply_markup=kb
        )
        last_bot_msg_del[msg.chat.id] = sent.message_id
        return

    old, new = parts

    # check database
    row = await query(
        'SELECT * FROM users WHERE telegram_id=? AND password=?',
        (msg.from_user.id, old),
        one=True
    )
    if not row:
        sent = await msg.answer('❌ Неверный старый пароль или вы не авторизованы', reply_markup=kb)
    else:
        # renew password
        await execute(
            'UPDATE users SET password=? WHERE telegram_id=?',
            (new, msg.from_user.id)
        )
        sent = await msg.answer('✅ Пароль успешно изменён', reply_markup=kb)
    last_bot_msg_del[msg.chat.id] = sent.message_id

    # get out of state
    await state.clear()

# endregion


# region Change Name

# chenge full name
@router_users.message(lambda msg: msg.text == "Изменить ФИО")
@only_role('student', 'curator')
@antispam(message_cooldown)
async def change_full_name_start(msg: types.Message, state: FSMContext, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    row_role = await query(
        "SELECT role FROM users WHERE telegram_id = ?",
        (msg.from_user.id,),
        one=True
    )
    role = row_role['role'] if row_role else None
    kb = student_kb if role == 'student' else curator_kb

    sent = await msg.answer(
        "✍️ Введите новое ФИО одним сообщением:\n"
        "<Фамилия Имя Отчество>",
        reply_markup=kb
    )
    last_bot_msg_del[msg.chat.id] = sent.message_id

    await state.set_state(ChangeUserData.waiting_for_full_name)
    return


# change full name step
@router_users.message(ChangeUserData.waiting_for_full_name)
async def process_full_name(msg: types.Message, state: FSMContext):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    row_role = await query(
        "SELECT role FROM users WHERE telegram_id = ?",
        (msg.from_user.id,),
        one=True
    )
    role = row_role['role'] if row_role else None
    kb = student_kb if role == 'student' else curator_kb

    parts = msg.text.split(maxsplit=3)
    if len(parts) > 3 or len(parts) < 2:
        sent = await msg.answer('Использование: <Фамилия Имя Отчество>', reply_markup=kb)
        last_bot_msg_del[msg.chat.id] = sent.message_id
        return

    full_name = msg.text
    await execute(
        'UPDATE users SET full_name = ? WHERE telegram_id = ?',
        (full_name, msg.from_user.id)
    )
    sent = await msg.answer(f"✅ Ваше полное имя обновлено: {full_name}", reply_markup=kb)
    last_bot_msg_del[msg.chat.id] = sent.message_id

    await state.clear()
    return

# endregion


# region Profile data

# show users data
@router_users.message(Command("my_data"))
@antispam(message_cooldown)
async def show_my_data(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    row = await query('SELECT full_name, role, username, password FROM users WHERE telegram_id=?', (msg.from_user.id,), one=True)
    if not row:
        sent = await msg.answer("Сначала авторизуйтесь.", reply_markup=main)
        last_bot_msg_del[msg.chat.id] = sent.message_id
        return

    role_to_kb = {
        'admin': admin_kb,
        'curator': curator_kb,
        'student': student_kb,
    }

    kb = role_to_kb.get(row['role'], main)

    sent = await msg.answer(
        f"ФИО: {row['full_name']}\n"
        f"Роль: {row['role']}\n"
        f"Логин: {row['username']}\n"
        f"Пароль: {row['password']}",
        reply_markup=kb
    )
    last_bot_msg_del[msg.chat.id] = sent.message_id
    return


# show users data (russificated)
@router_users.message(lambda msg: msg.text == "Мои данные")
@antispam(message_cooldown)
async def my_data_button(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    return await show_my_data(msg, **kwargs)

# endregion
