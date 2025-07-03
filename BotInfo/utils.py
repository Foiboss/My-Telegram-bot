import json
import random
import string
import tempfile
from typing import List, Tuple

from aiogram import types
from aiogram.types import FSInputFile

from BotInfo.db import query
from config import WHITELIST_FILE


def load_whitelist() -> List[int]:
    """
    Gets admin list
    :return: empty list, if file doesn't exist or is corrupted
    """
    try:
        # Open the whitelist file and parse JSON
        with open(WHITELIST_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Return the 'admins' list
            return data.get('admins', [])
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file is missing or invalid, return an empty whitelist
        return []


# Load once at startup
ADMIN_WHITELIST: List[int] = load_whitelist()


#region Generation of login and passwords

def gen_mult_login_password(from_id: int, to_id: int) -> Tuple[(str, str)]:
    """
    Generate a tuple of logins and passwords pairs
    - login: from from_id to to_id IDs
    - password: uses gen_password() to generate
    :param from_id: id of the first generated login-password pair
    :param to_id: id of the last generated login-password pair
    :return: a tuple of pair of login and password
    """
    pairs: Tuple[Tuple[str, str]] = []
    for i in range(to_id - from_id + 1):
        login = str(from_id + i)
        # Random password of 8 letters and digits
        password = gen_password()
        pairs.append((login, password))
    return pairs

def gen_login_password(id: int) -> (str, str):
    """
    Generate a pair of login and password
    - login: given ID
    - password: uses gen_password() to generate
    :param id: given id for login-password pair
    :return: a pair of login and password
    """
    return str(id), gen_password()

def gen_password() -> str:
    """
    Generate a password for user
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


def only_role(*allowed_roles: str):
    """
    Decorator, that restricts command usage only to the persons mentioned in allowed_roles
    :param allowed_roles: roles that can use the command
    """
    def decorator(func):
        async def wrapper(msg: types.Message, *args, **kwargs):
            user = await query(
                "SELECT role FROM users WHERE telegram_id = ?",
                (msg.from_user.id,), one=True
            )
            if not user or user["role"] not in allowed_roles:
                return await msg.answer(
                    f"Доступно только для ролей: {', '.join(allowed_roles)}"
                )
            return await func(msg, *args, **kwargs)
        return wrapper
    return decorator

# endregion


def get_name_data(text: str) -> str:
    """
    If text is a name - returns name, if not - raises a value error
    :param text: text to check if it's a name
    :return: text param if succeeds
    :raises ValueError: If text isn't a name
    """
    parts = text.strip().split(maxsplit=2)
    if len(parts) < 2 or len(parts) > 3:
        raise ValueError("Неверный формат ФИО")
    return text


async def send_curator_list(msg: types.Message):
    """
    Sends curators names in chat in .txt file
    """
    # Get all curators from database (not the ones with full_name = ЭФамилия Имя ОтчествоЭ)
    rows = await query(
        "SELECT full_name FROM users WHERE role = 'curator' AND full_name <> 'Фамилия Имя Отчество'"
    )
    if not rows:
        await msg.answer("❗ В системе не найдено ни одного куратора.")
        return

    # write in temp file
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False, encoding='utf-8') as tf:
        for r in rows:
            tf.write(r['full_name'] + '\n')
        tf.flush()
        path = tf.name

    # send file to student
    return await msg.answer_document(
        FSInputFile(path, filename="curators_list.txt"),
        caption="📄 Список доступных кураторов"
    )

async def noop() -> None:
    """
    Empty coroutine stub
    """
    return None