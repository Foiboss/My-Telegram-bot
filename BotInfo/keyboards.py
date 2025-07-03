from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Main Keyboard
main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Авторизация')]
],  resize_keyboard=True,
    input_field_placeholder='Выберите пункт меню.')


# Student Keyboard
student_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Изменить пароль'), KeyboardButton(text='Изменить ФИО')],
    [KeyboardButton(text='Добавить активность'), KeyboardButton(text='Профиль')],
    [KeyboardButton(text='Выйти из аккаунта')]
],  resize_keyboard=True,
    input_field_placeholder='Выберите пункт меню.')


# Student Request Management Keyboard
lk_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Мои заявки'), KeyboardButton(text='Мои данные')],
    [KeyboardButton(text='Назад')]
],  resize_keyboard=True,
    input_field_placeholder='Выберите пункт меню.')


# Curator Keyboard
curator_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Изменить пароль'), KeyboardButton(text='Изменить ФИО')],
    [KeyboardButton(text='Заявки')],
    [KeyboardButton(text='Мои данные'), KeyboardButton(text='Выйти из аккаунта')]
],  resize_keyboard=True,
    input_field_placeholder='Выберите пункт меню.')


# Admin Keyboard
admin_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Добавить пользователя'), KeyboardButton(text='Удалить пользователя')],
    [KeyboardButton(text='Выгрузить пользователей'), KeyboardButton(text='Выгрузить активности')],
    [KeyboardButton(text='Мои данные'), KeyboardButton(text='Выйти из админ-аккаунта')]
],  resize_keyboard=True,
    input_field_placeholder='Выберите пункт меню.')

cancel_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Отмена')]
],  resize_keyboard=True,
    input_field_placeholder='Выберите пункт меню.')
