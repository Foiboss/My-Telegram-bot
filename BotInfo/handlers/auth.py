import os
import sys
from datetime import timedelta

from aiogram import types, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile, ReplyKeyboardRemove

from BotInfo.handlers.antispam import antispam
from ..config import message_cooldown
from ..db import query, execute
from ..keyboards import main, student_kb, curator_kb, admin_kb
from ..utils import only_role, gen_password

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

router_auth = Router()

# Storing the bot's last message in the chat to delete messages
last_bot_msg_del: dict[int, list[int]] = {}


async def delete_prev(chat_id: int, bot: Bot):
    msg_id = last_bot_msg_del.get(chat_id, [])
    for mid in msg_id:
        try:
            await bot.delete_message(chat_id, mid)
        except:
            pass


def remember_bot_msg(chat_id: int, message_id: int, limit: int = 10):
    lst = last_bot_msg_del.setdefault(chat_id, [])
    lst.append(message_id)
    if len(lst) > limit:
        lst.pop(0)


class AuthSG(StatesGroup):
    login = State()
    password = State()


# Dictionary of roles → keyboards
role_kb = {
    'student': student_kb,
    'curator': curator_kb
}


# start command
@router_auth.message(Command('start'))
@antispam(message_cooldown)
async def cmd_start(msg: types.Message, **kwargs):
    # delete user msg and previous bot msg
    await delete_prev(msg.chat.id, msg.bot)
    await msg.delete()
    # path to photo
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    photo_path = os.path.join(project_root, 'Photos', 'gasu.png')
    photo = FSInputFile(photo_path)
    sent = await msg.answer_photo(
        photo=photo,
        caption=f'👋 Привет, {msg.from_user.first_name}!\n'
                'Этот бот предназначен для сбора информации о твоих внеучебных достижениях.\n'
                '🔐 Для начала необходимо авторизоваться.\n\n'
                '✏️ Кстати, не забудь сменить ФИО у себя в профиле,\n'
                'чтобы твои коллеги могли тебя узнать! Там же ты можешь сменить и пароль от аккаунта',
        reply_markup=main
    )
    remember_bot_msg(msg.chat.id, sent.message_id)


# @router_auth.message(lambda msg: msg.text == '👥 Сгенерировать студента и куратора')
# @antispam(timedelta(minutes=2))
# async def gen_two_creds(msg: types.Message, **kwargs):
#     await delete_prev(msg.chat.id, msg.bot)
#     text = '✅ Сохраните эти данные надёжно:\n'
#
#     # student
#     login = gen_password()
#     password = gen_password()
#     await execute(
#         'INSERT INTO users(telegram_id,username,full_name,role,password) VALUES(?,?,?,?,?)',
#         (None, login, 'Фамилия Имя Отчество', 'student', password)
#     )
#     text += f'Student: {login} - {password}\n'
#
#     # curator
#     login = gen_password()
#     password = gen_password()
#     await execute(
#         'INSERT INTO users(telegram_id,username,full_name,role,password) VALUES(?,?,?,?,?)',
#         (None, login, 'Фамилия Имя Отчество', 'curator', password)
#     )
#     text += f'Curator: {login} - {password}\n'
#
#     await msg.answer(text, reply_markup=main)



# region User login

@router_auth.message(lambda msg: msg.text == "🔑 Авторизация")
@antispam(message_cooldown)
async def login_start(msg: types.Message, state: FSMContext, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    await msg.delete()

    row = await query('SELECT * FROM users WHERE telegram_id=?', (msg.from_user.id,), one=True)
    if row:
        role = row["role"]
        if role == "student":
            kb = student_kb
        elif role == "curator":
            kb = curator_kb
        elif role == "admin":
            kb = admin_kb
        else:
            kb = ReplyKeyboardRemove()
        # If is already logged in
        sent = await msg.answer(
            'Вы и так в аккаунте:\n'
            f'логин: {row["username"]}\n'
            f'ФИО: {row["full_name"]}\n'
            f'роль: {row["role"]}',
            reply_markup=kb
        )
        remember_bot_msg(msg.chat.id, sent.message_id)
        return

    # start FSM logging in
    await state.set_state(AuthSG.login)
    sent = await msg.answer('Введите логин:', reply_markup=ReplyKeyboardRemove())
    remember_bot_msg(msg.chat.id, sent.message_id)


# login step
@router_auth.message(AuthSG.login)
async def process_login(msg: types.Message, state: FSMContext):
    await delete_prev(msg.chat.id, msg.bot)
    await msg.delete()

    await state.update_data(login=msg.text.strip())
    await state.set_state(AuthSG.password)
    sent = await msg.answer('Введите пароль:')
    remember_bot_msg(msg.chat.id, sent.message_id)


# password step
@router_auth.message(AuthSG.password)
async def process_password(msg: types.Message, state: FSMContext):
    await delete_prev(msg.chat.id, msg.bot)
    await msg.delete()

    data = await state.get_data()
    login = data.get('login')
    pwd = msg.text.strip()

    # find user by given login and password
    user = await query(
        'SELECT * FROM users WHERE username=? AND password=?',
        (login, pwd), one=True
    )
    await state.clear()  # очищаем FSM

    if not user:
        # if incorrect - return to main menu
        sent = await msg.answer(
            'Неверный логин или пароль. Попробуйте снова.',
            reply_markup=main
        )
        remember_bot_msg(msg.chat.id, sent.message_id)
        return
    if user: # if found - login user and send welcome message
        role_key = user['role'].strip().lower()
        kb = role_kb.get(user['role'], main)
        sent = await msg.answer(
            f'Вы вошли как {user["role"]}',
            reply_markup=kb
        )
        remember_bot_msg(msg.chat.id, sent.message_id)

        await execute(
            'UPDATE users SET telegram_id=? WHERE username=?',
            (msg.from_user.id, login)
        )

# endregion


# logout command (russificated)
@router_auth.message(lambda msg: msg.text == '🚪 Выйти из аккаунта')
@only_role('student', 'curator')
async def logout(msg: types.Message, state: FSMContext, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    await msg.delete()

    # 1) Reset the telegram_id to the database
    await execute('UPDATE users SET telegram_id = NULL WHERE telegram_id = ?', (msg.from_user.id,))
    # 2) Cleaning all the user's FSM data
    await state.clear()
    # 3) Remove the keyboard and send a reply
    sent = await msg.answer('✅ Вы вышли из аккаунта', reply_markup=main)
    remember_bot_msg(msg.chat.id, sent.message_id)
