import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

import os

TOKEN = os.getenv("TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()

TEACHERS = {}
CONVERSATIONS = {}
USER_TO_CONV = {}
conv_seq = 1000

class StudentFlow(StatesGroup):
    wait_teacher = State()
    wait_problem = State()

@dp.message(F.text == "/start")
async def start(m: Message):
    await m.answer(
        "Привет! Я анонимный школьный чат.\n"
        "Если ты учитель: /teacher\n"
        "Если ты ученик: /student"
    )

@dp.message(F.text == "/teacher")
async def teacher(m: Message):
    if not m.from_user.username:
        await m.answer("Нужно включить username в Telegram.")
        return
    TEACHERS[m.from_user.username.lower()] = m.from_user.id
    await m.answer("Вы зарегистрированы как учитель.")

@dp.message(F.text == "/student")
async def student(m: Message, state: FSMContext):
    await state.set_state(StudentFlow.wait_teacher)
    await m.answer("Введите @username учителя")

@dp.message(StudentFlow.wait_teacher)
async def got_teacher(m: Message, state: FSMContext):
    username = m.text.strip().lstrip("@").lower()
    if username not in TEACHERS:
        await m.answer("Учитель не найден. Попросите написать /teacher.")
        return
    await state.update_data(teacher_username=username)
    await state.set_state(StudentFlow.wait_problem)
    await m.answer("Опишите проблему одним сообщением.")

@dp.message(StudentFlow.wait_problem)
async def got_problem(m: Message, state: FSMContext):
    global conv_seq
    data = await state.get_data()
    teacher_id = TEACHERS[data["teacher_username"]]
    student_id = m.from_user.id

    conv_seq += 1
    conv_id = conv_seq

    CONVERSATIONS[conv_id] = {"student": student_id, "teacher": teacher_id, "status": "open"}
    USER_TO_CONV[student_id] = conv_id
    USER_TO_CONV[teacher_id] = conv_id

    await bot.send_message(
        teacher_id,
        "Анонимный ученик пишет:\n\n" + m.text
    )
    await m.answer("Сообщение отправлено.")
    await state.clear()

@dp.message()
async def relay(m: Message):
    sender = m.from_user.id
    conv_id = USER_TO_CONV.get(sender)
    if not conv_id:
        return

    conv = CONVERSATIONS.get(conv_id)
    if not conv or conv["status"] != "open":
        return

    if sender == conv["student"]:
        receiver = conv["teacher"]
        prefix = "Ученик:\n"
    else:
        receiver = conv["student"]
        prefix = "Учитель:\n"

    await bot.send_message(receiver, prefix + m.text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
