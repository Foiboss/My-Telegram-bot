import os
import sys
import tempfile
from aiogram import types, Router
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.types import ReplyKeyboardRemove
from BotInfo.handlers.antispam import antispam
from BotInfo.handlers.auth import delete_prev, last_bot_msg_del

from ..config import message_cooldown
from ..db import execute, query
from ..keyboards import admin_kb, main
from ..utils import ADMIN_WHITELIST, only_role, gen_password

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

router_admin = Router()

role_kb = {
    'admin': admin_kb
}


# region Admin login - logout

@router_admin.message(Command('admin_login'))
@antispam(message_cooldown)
async def admin_login(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass  # safe removal

    uid = msg.from_user.id
    if uid not in ADMIN_WHITELIST:
        sent = await msg.answer(
            f'Нет прав. Ваш ID={uid}. Обратитесь к главному администратору (контактные данные), чтобы он добавил вас в whitelist.'
        )
        last_bot_msg_del[msg.chat.id] = sent.message_id
        return

    user_row = await query(
        'SELECT * FROM users WHERE telegram_id=?',
        (msg.from_user.id,), one=True
    )

    kb = role_kb.get('admin', ReplyKeyboardRemove())

    if not user_row:
        await execute(
            'REPLACE INTO users(telegram_id,username,full_name,role,password) VALUES(?,?,?,?,?)',
            (uid, msg.from_user.username or str(uid), 'Фамилия Имя Отчество', 'admin', '')
        )
        sent = await msg.answer('Вы вошли как admin', reply_markup=kb)
    else:
        sent = await msg.answer('Вы и так в аккаунте:\n'
                                f'логин: {user_row['username']}\n'
                                f'ФИО: {user_row['full_name']}\n'
                                f'Роль: {user_row['role']}\n', reply_markup=kb)
    last_bot_msg_del[msg.chat.id] = sent.message_id


# function to log admin out
async def do_admin_logout(msg: types.Message):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    uid = msg.from_user.id
    user_row = await query(
        'SELECT * FROM users WHERE telegram_id=?',
        (uid,), one=True
    )
    if not user_row:
        sent = await msg.answer('ERROR: вас нет в базе данных, как залогиненного пользователя')
    else:
        await execute(
            'DELETE FROM users WHERE telegram_id = ?',
            (uid,)
        )
        sent = await msg.answer('Вы вышли из аккаунта admin', reply_markup=main)
    last_bot_msg_del[msg.chat.id] = sent.message_id


# command version of logout
@router_admin.message(Command('admin_logout'))
@only_role('admin')
async def admin_logout(msg: types.Message, **kwargs):
    await do_admin_logout(msg)

    uid = msg.from_user.id
    user_row = await query(
        'SELECT * FROM users WHERE telegram_id=?',
        (uid,), one=True
    )
    if not user_row:
        await msg.answer('ERROR: вас нет в базе данных, как залогиненного пользователя')
    else:
        await execute(
            'DELETE FROM users WHERE telegram_id = ?',
            (uid,)
        )
        await msg.answer('Вы вышли из аккаунта admin', reply_markup=main)


# russificated version of admin logout
@router_admin.message(lambda msg: msg.text == "Выйти из админ-аккаунта")
@only_role('admin')
async def handle_logout_button(msg: types.Message, **kwargs):
    await do_admin_logout(msg)


# endregion

# region Users management: Add - Delete

# Add user russificated info on the /gen_creds command usage
@router_admin.message(lambda msg: msg.text == "Добавить пользователя")
@only_role('admin')
async def add_user_button(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    sent = await msg.answer('Чтобы добавить пользователей, используйте команду:\n'
                           '/gen_creds <role> <FromID> <ToID>\n'
                           'Создаст аккаунты для пользователей с login (номер студенческого/учительского) от FromID до ToID\n'
                           'В <role> можно подставить:\n'
                           'student - чтобы создать аккаунт для студента,\n'
                           'curator - чтобы создать аккаунт для куратора\n'
                           'Например: /gen_creds student 100 200', reply_markup=admin_kb)
    last_bot_msg_del[msg.chat.id] = sent.message_id
    return


# generating login - logouts for users (student / curator) in given bounds
@router_admin.message(Command('gen_creds'))
@only_role('admin')
@antispam(message_cooldown)
async def gen_creds(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    parts = msg.text.split()
    if len(parts) < 4:
        sent = await msg.answer('Использование: /gen_creds <role> <FromID> <ToID>', reply_markup=admin_kb)
        last_bot_msg_del[msg.chat.id] = sent.message_id
        return
    role, from_str, to_str = parts[1], parts[2], parts[3]

    if not (from_str.isdigit() and to_str.isdigit()):
        sent = await msg.answer('FromID и ToID должны быть числами.', reply_markup=admin_kb)
        last_bot_msg_del[msg.chat.id] = sent.message_id
        return
    low, high = int(from_str), int(to_str)

    if low > high:
        sent = await msg.answer(f'Неверный диапазон: {low} > {high}', reply_markup=admin_kb)
        last_bot_msg_del[msg.chat.id] = sent.message_id
        return

    # 1) we will find out in advance which logins are already in the DB
    existing = await query(
        """
        SELECT username
          FROM users
         WHERE CAST(username AS INTEGER) BETWEEN ? AND ?
        """,
        (low, high)
    )
    existing_usernames = {row['username'] for row in existing}

    # 2) Preparing the file and the lists
    filename = f"creds_{role}_{low}-{high}.txt"
    tmp_path = os.path.join(tempfile.gettempdir(), filename)
    created = skipped = 0

    with open(tmp_path, 'w', encoding='utf-8') as f:
        for uid in range(low, high + 1):
            login = str(uid)
            if login in existing_usernames:
                skipped += 1
                continue
            pwd = gen_password()
            full_name = 'Фамилия Имя Отчество'
            await execute(
                'INSERT INTO users(telegram_id,username,full_name,role,password) VALUES(?,?,?,?,?)',
                (None, login, full_name, role, pwd)
            )
            f.write(f"{login} — {pwd}\n")
            created += 1

    if created == 0:
        os.remove(tmp_path)
        sent = await msg.answer(
            f"Новых учёток не создано. Все логины из диапазона {low}-{high} уже существуют.",
            reply_markup=admin_kb
        )
        last_bot_msg_del[msg.chat.id] = sent.message_id
        return

    sent = await msg.answer_document(
        FSInputFile(tmp_path, filename=filename),
        caption=(
            f"Новых учёток создано: {created}\n"
            f"Пропущено (уже есть): {skipped}"
        ),
        reply_markup=admin_kb
    )
    last_bot_msg_del[msg.chat.id] = sent.message_id
    os.remove(tmp_path)


# Russificated info on delete users command
@router_admin.message(lambda msg: msg.text == "Удалить пользователя")
@only_role('admin')
@antispam(message_cooldown)
async def delete_user_button(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    sent = await msg.answer("Чтобы удалить пользователей, используйте команду:\n"
                           "/delete_users <from-to> [<from-to> ...]\n"
                           "Удалит пользователей с login в заданных диапазонах,в том числе удалит и их заявки\n"
                           "Например: /delete_users 100-200 1000-1344 50-150", reply_markup=admin_kb)
    last_bot_msg_del[msg.chat.id] = sent.message_id
    return


# delete users command
@router_admin.message(Command('delete_users'))
@only_role('admin')
@antispam(message_cooldown)
async def delete_users(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    tokens = msg.text.split()[1:]
    if not tokens:
        sent = await msg.answer("Использование: /delete_users <from-to> [<from-to> ...]", reply_markup=admin_kb)
        last_bot_msg_del[msg.chat.id] = sent.message_id
        return

    def parse_range(token: str) -> tuple[int, int]:
        if '-' not in token:
            raise ValueError(f"Неверный формат: '{token}'. Ожидается 'low-high'.")
        low_str, high_str = token.split('-', maxsplit=1)
        if not (low_str.isdigit() and high_str.isdigit()):
            raise ValueError(f"Границы должны быть числами: '{token}'.")
        low, high = int(low_str), int(high_str)
        if low > high:
            raise ValueError(f"В '{token}' lower > upper.")
        return low, high

    try:
        ranges = [parse_range(tok) for tok in tokens]
    except ValueError as e:
        sent = await msg.answer(str(e), reply_markup=admin_kb)
        last_bot_msg_del[msg.chat.id] = sent.message_id
        return

    total_users_deleted = 0
    for low, high in ranges:
        # Сначала активности
        await execute(
            "DELETE FROM activities WHERE student_id BETWEEN ? AND ?",
            (low, high)
        )
        # Потом сами пользователи
        await execute(
            "DELETE FROM users WHERE username BETWEEN ? AND ?",
            (low, high)
        )
        total_users_deleted += (high - low + 1)

    sent = await msg.answer(
        f"Пользователи удалены\n"
        f"Число выделенных для удаления пользователей: {total_users_deleted}\n"
        f"Все заявки, связанные с этими пользователями также удалены",
        reply_markup=admin_kb
    )
    last_bot_msg_del[msg.chat.id] = sent.message_id

# endregion
