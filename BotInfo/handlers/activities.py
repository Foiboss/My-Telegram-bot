import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from BotInfo.handlers.antispam import antispam
from BotInfo.handlers.auth import delete_prev, remember_bot_msg

from ..config import TOKEN, message_cooldown
from ..db import execute, query
from ..utils import only_role, get_name_data, send_curator_list
from ..keyboards import lk_kb, student_kb, cancel_kb


async def send_curator_input_photo(msg: types.Message):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    photo_path = os.path.join(project_root, 'Photos', 'curator.png')
    photo = FSInputFile(photo_path)
    sent = await msg.answer_photo(photo=photo, caption='Введите ФИО куратора:', reply_markup=cancel_kb)
    remember_bot_msg(msg.chat.id, sent.message_id)


router_activities = Router()

# region Add activity


class AddActivitySG(StatesGroup):
    student_id = State()
    full_name = State()
    title = State()
    event_status = State()
    cert_choice = State()
    cert_url = State()
    cert_file = State()
    curator = State()


@router_activities.message(lambda msg: msg.text == "Отмена")
async def cancel_add_activity(msg: types.Message, state: FSMContext):
    await state.clear()

    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    sent = await msg.answer(
        'Добавление активности отменено',
        reply_markup=student_kb
    )
    remember_bot_msg(msg.chat.id, sent.message_id)


@router_activities.message(lambda msg: msg.text == "Добавить активность")
@only_role('student')
@antispam(message_cooldown)
async def cmd_add_activity(msg: types.Message, state: FSMContext, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    user = await query(
        'SELECT id, full_name, username FROM users WHERE telegram_id=?',
        (msg.from_user.id,), one=True)
    if not user:
        sent = await msg.answer('Вас нет в базе, авторизуйтесь', reply_markup=student_kb)
        remember_bot_msg(msg.chat.id, sent.message_id)
        return

    await state.update_data(student_id=user['username'])
    await state.update_data(full_name=user['full_name'])
    await state.set_state(AddActivitySG.title)

    this_file = os.path.abspath(__file__)
    script_dir = os.path.dirname(this_file)  # …/project/handlers
    project_root = os.path.dirname(script_dir)  # …/project
    photo_path = os.path.join(project_root, 'Photos', 'event.jpg')
    photo = FSInputFile(photo_path)
    sent = await msg.answer_photo(photo=photo, caption="Введите название активности:", reply_markup=cancel_kb)
    remember_bot_msg(msg.chat.id, sent.message_id)
    return


# title step
@router_activities.message(AddActivitySG.title)
async def process_title(msg: types.Message, state: FSMContext):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    await state.update_data(title=msg.text.strip())
    await state.set_state(AddActivitySG.event_status)
    this_file = os.path.abspath(__file__)
    script_dir = os.path.dirname(this_file)  # …/project/handlers
    project_root = os.path.dirname(script_dir)  # …/project
    photo_path = os.path.join(project_root, 'Photos', 'status.png')
    photo = FSInputFile(photo_path)
    sent = await msg.answer_photo(photo=photo, caption='Выберите статус мероприятия:\n'
                    'например: международный, всероссийский, городской, региональный, внутривузовский...',
                    reply_markup=cancel_kb)
    remember_bot_msg(msg.chat.id, sent.message_id)
    return


# event status step
@router_activities.message(AddActivitySG.event_status)
async def process_event_status(msg: types.Message, state: FSMContext):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    await state.update_data(event_status=msg.text.strip())
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Ссылка')],
            [KeyboardButton(text='Файл')],
            [KeyboardButton(text='Пропустить')],
            [KeyboardButton(text='Отмена')]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await state.set_state(AddActivitySG.cert_choice)
    this_file = os.path.abspath(__file__)
    script_dir = os.path.dirname(this_file)  # …/project/handlers
    project_root = os.path.dirname(script_dir)  # …/project
    photo_path = os.path.join(project_root, 'Photos', 'certificate.png')
    photo = FSInputFile(photo_path)
    sent = await msg.answer_photo(photo=photo, caption='Выберите тип подтверждения:', reply_markup=kb)
    remember_bot_msg(msg.chat.id, sent.message_id)
    return


# 1 certificate variant choice step (3 variants bellow)
@router_activities.message(AddActivitySG.cert_choice)
async def process_choice(msg: types.Message, state: FSMContext):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    text = msg.text.strip().lower()
    if text == 'ссылка':
        await state.set_state(AddActivitySG.cert_url)
        sent = await msg.answer('Отправьте URL документа:', reply_markup=cancel_kb)
        remember_bot_msg(msg.chat.id, sent.message_id)
    elif text == 'файл':
        await state.set_state(AddActivitySG.cert_file)
        sent = await msg.answer('Пришлите файл документом:', reply_markup=cancel_kb)
        remember_bot_msg(msg.chat.id, sent.message_id)
    elif text == 'пропустить':
        await state.update_data(cert_url=None, cert_file_id=None, cert_file_link=None)
        await state.set_state(AddActivitySG.curator)
        await send_curator_list(msg)
        await send_curator_input_photo(msg)
    else:
        sent = await msg.answer('Неверный выбор. Выберите из клавиатуры')
        remember_bot_msg(msg.chat.id, sent.message_id)


# 2 certificate url choice step
@router_activities.message(AddActivitySG.cert_url)
async def process_url(msg: types.Message, state: FSMContext):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    await state.update_data(cert_url=msg.text.strip(), cert_file_id=None, cert_file_link=None)
    await state.set_state(AddActivitySG.curator)
    await send_curator_list(msg)
    await send_curator_input_photo(msg)


# 3 certificate document choice step
@router_activities.message(AddActivitySG.cert_file, F.content_type == types.ContentType.DOCUMENT)
async def process_file(msg: types.Message, state: FSMContext):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    file_id = msg.document.file_id
    file = await msg.bot.get_file(file_id)
    file_link = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"
    await state.update_data(cert_url=file_link, cert_file_id=file_id, cert_file_link=file_link)
    await state.set_state(AddActivitySG.curator)
    await send_curator_list(msg)
    await send_curator_input_photo(msg)


# not a document error handler
@router_activities.message(AddActivitySG.cert_file, F.content_type != types.ContentType.DOCUMENT)
async def process_bad_file(msg: types.Message):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    sent = await msg.answer('Ожидался документ. Пожалуйста, пришлите файл документом.', reply_markup=cancel_kb)
    remember_bot_msg(msg.chat.id, sent.message_id)


# curator step
@router_activities.message(AddActivitySG.curator)
async def process_curator(msg: types.Message, state: FSMContext):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    text = msg.text.strip()
    # Check for placeholder
    if text.lower() == "фамилия имя отчество":
        sent = await msg.answer(
            "❗ Вы ввели некорректное ФИО куратора. "
            "Пожалуйста, выберите имя из списка и введите корректное ФИО.",
            reply_markup=cancel_kb
        )
        remember_bot_msg(msg.chat.id, sent.message_id)
        return

    # Check full name format
    try:
        name = get_name_data(text)
    except ValueError:
        sent = await msg.answer(
            "❗ Неверный формат ФИО.\n"
            "Пожалуйста, введите три слова через пробел: Фамилия Имя Отчество",
            reply_markup=cancel_kb
        )
        remember_bot_msg(msg.chat.id, sent.message_id)
        return

    # Check if full name of curator exists in database
    curator = await query(
        "SELECT id FROM users WHERE role = 'curator' AND full_name = ?",
        (name,), one=True
    )
    if not curator:
        sent = await msg.answer(
            "❗ Куратор с таким ФИО не найден. \n"
            "Пожалуйста, введите имя существующего в базе данных куратора",
            reply_markup=cancel_kb
        )
        remember_bot_msg(msg.chat.id, sent.message_id)
        return

    data = await state.get_data()

    await execute(
        '''INSERT INTO activities(
             student_id, full_name, 
             title, event_status, cert_url, cert_file_id, cert_file_link,
             curator_full_name, confirmed
           ) VALUES(?,?,?,?,?,?,?,?,0)''',
        (
            data['student_id'], data['full_name'],
            data['title'], data['event_status'], data.get('cert_url'), data.get('cert_file_id'), data.get('cert_file_link'),
            name
        )
    )
    await state.clear()

    # first message: text otchet
    lines = [
        f"Студенческий: {data['student_id']}",
        f"Имя: {data['full_name']}",
        f"Название: {data['title']}",
        f"Статус мероприятия: {data['event_status']}",
        f"Куратор: {msg.text.strip()}"
    ]
    sent = await msg.answer('Активность добавлена:\n' + '\n'.join(lines), reply_markup=student_kb)
    remember_bot_msg(msg.chat.id, sent.message_id)

    # if user sent file - resend it to him
    file_link = data.get('cert_file_link')
    if file_link:
        sent = await msg.answer(data['cert_file_id'], caption="📄 Ваш загруженный файл")
        remember_bot_msg(msg.chat.id, sent.message_id)
    elif data.get('cert_url'):
        # if user sent url - resend it
        sent = await msg.answer(f"🔗 Ссылка на подтверждение: {data['cert_url']}")
        remember_bot_msg(msg.chat.id, sent.message_id)
    else:
        sent = await msg.answer("— без подтверждений —")
        remember_bot_msg(msg.chat.id, sent.message_id)

# endregion

# region Requests management (student)


# Student request management profile open command
@router_activities.message(lambda msg: msg.text == "Профиль")
async def open_lk(msg: types.Message):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    sent = await msg.answer("Добро пожаловать в профиль", reply_markup=lk_kb)
    remember_bot_msg(msg.chat.id, sent.message_id)


# Student's request check (russificated variant)
@router_activities.message(lambda msg: msg.text == "Мои заявки")
@only_role('student')
async def my_requests_button(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    return await my_requests(msg, **kwargs)


# Student's request check (original command)
@router_activities.message(Command('my_requests'))
@only_role('student')
@antispam(message_cooldown)
async def my_requests(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    # get student's id and full name
    user = await query("SELECT username FROM users WHERE telegram_id=?", (msg.from_user.id,), one=True)

    # don't check existing of user as it's already checked by @only_role

    # get user's requests
    rows = await query(
        """
        SELECT id, title, event_status, cert_url, curator_full_name, confirmed
          FROM activities
         WHERE student_id = ?
        """,
        (user['username'],)
    )
    if not rows:
        sent = await msg.answer("У вас ещё нет поданных заявок.", reply_markup=student_kb)
        remember_bot_msg(msg.chat.id, sent.message_id)
        return

    texts = []
    for r in rows:
        status = {0: "Ожидает", 1: "Подтверждена", -1: "Отклонена"}.get(r['confirmed'], str(r['confirmed']))
        texts.append(
            f"#{r['id']}: «{r['title']}»\n"
            f"Статус мероприятия: «{r['event_status']}»\n"
            f"Документ: {r['cert_url']}\n"
            f"Куратор: {r['curator_full_name']}\n"
            f"Статус заявки: {status}"
        )

    # separate so it won't be long enough to exceed the limits of telegram 1 message
    for chunk in ("\n\n".join(texts))[0:4000].split("\n\n"):
        sent = await msg.answer(chunk, reply_markup=student_kb)
        remember_bot_msg(msg.chat.id, sent.message_id)


# getting back to student's main menu
@router_activities.message(lambda msg: msg.text == "Назад")
@only_role('student')
async def back_to_menu(msg: types.Message, **kwargs):
    await delete_prev(msg.chat.id, msg.bot)
    try:
        await msg.delete()
    except:
        pass

    sent = await msg.answer('Вы вернулись в главное меню', reply_markup=student_kb)
    remember_bot_msg(msg.chat.id, sent.message_id)

# endregion

# region Requests management (curator)


# curator revues requests
@router_activities.message(lambda msg: msg.text == "Заявки")
@only_role('curator')
@antispam(message_cooldown)
async def review_requests(msg: types.Message, **kwargs):
    # find curators row
    curator_row = await query(
        'SELECT * FROM users WHERE telegram_id=?',
        (msg.from_user.id,), one=True
    )
    curator_full_name = curator_row["full_name"]
    rows = await query(
        'SELECT id, student_id, full_name, title FROM activities WHERE curator_full_name = ? AND confirmed = 0',
        (curator_full_name,)
    )
    if not rows: # not found any requests assigned to curators name
        return await msg.answer('У вас нет новых заявок для проверки.')

    for r in rows: # show requests and allow to accept/decline it
        text = (f"Заявка #{r['id']} — студент {r['student_id']}\n"
                f"ФИО — {r['full_name']}\n"
                f"Мероприятие — {r['title']}")
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text='✅ Подтвердить', callback_data=f"approve:{r['id']}"),
                    InlineKeyboardButton(text='❌ Отклонить', callback_data=f"reject:{r['id']}")
                ]
            ]
        )
        await msg.answer(text, reply_markup=kb)


# curator accepts request


@router_activities.callback_query(lambda c: c.data and c.data.startswith('approve:'))
@only_role('curator')
async def callback_approve(cb: types.CallbackQuery, **kwargs):
    act_id = int(cb.data.split(':', 1)[1])
    await execute('UPDATE activities SET confirmed = 1 WHERE id = ?', (act_id,))
    await cb.message.edit_reply_markup()  # убираем кнопки
    await cb.answer('Заявка подтверждена')


# curator declines request

@router_activities.callback_query(lambda c: c.data and c.data.startswith('reject:'))
@only_role('curator')
async def callback_reject(cb: types.CallbackQuery, **kwargs):
    act_id = int(cb.data.split(':', 1)[1])
    await execute('UPDATE activities SET confirmed = -1 WHERE id = ?', (act_id,))
    await cb.message.edit_reply_markup()  # убираем кнопки
    await cb.answer('Заявка отклонена')

# endregion
