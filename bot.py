import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from calculator import calculate_surebet
from database import get_user_settings, update_user_bank, update_user_step
from scanner import start_scanning

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

active_tasks = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="🔎 Запустить сканер"), types.KeyboardButton(text="🛑 Остановить сканер")],
        [types.KeyboardButton(text="⚙️ Настройки"), types.KeyboardButton(text="❓ Помощь")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    start_text = (
        "👋 **Добро пожаловать в Вилочный Бот!**\n\n"
        "Используй меню ниже для управления сканером и настройками.\n\n"
        "📌 **Быстрые команды:**\n"
        "• `/calc 2.10 2.05` — ручной расчёт вилки\n"
        "• `/setbank 150000` — сменить банк\n"
        "• `/setstep 500` — сменить шаг округления"
    )
    await message.answer(start_text, reply_markup=keyboard)

@dp.message(F.text == "🔎 Запустить сканер")
async def start_scanner_btn(message: types.Message):
    chat_id = message.chat.id
    
    if chat_id in active_tasks and not active_tasks[chat_id].done():
        await message.answer("ℹ️ Сканер уже активно работает.")
        return

    await message.answer("🟢 Сканер реальных вилок запущен!\nОжидайте отфильтрованные сигналы в этом чате...")
    
    task = asyncio.create_task(start_scanning(bot, chat_id))
    active_tasks[chat_id] = task

@dp.message(F.text == "🛑 Остановить сканер")
async def stop_scanner_btn(message: types.Message):
    chat_id = message.chat.id
    if chat_id in active_tasks and not active_tasks[chat_id].done():
        active_tasks[chat_id].cancel()
        del active_tasks[chat_id]
        await message.answer("🛑 Сканер остановлен.")
    else:
        await message.answer("ℹ️ Сканер и так выключен.")

@dp.message(F.text == "❓ Помощь")
async def help_btn(message: types.Message):
    help_text = (
        "📖 **Справка по работе с ботом:**\n\n"
        "1. **Запустить сканер** — проверяет совпадение линий ТБ и ТМ строго на один и тот же тотал.\n"
        "2. **Фильтры:** отсекаются микро-вилки (<0.1%), опечатки линий (>5.0%) и БК-клоны.\n"
        "3. **Ручной расчёт:** отправь команду `/calc 2.10 2.05`."
    )
    await message.answer(help_text)

@dp.message(Command("calc"))
async def cmd_calc(message: types.Message):
    args = message.text.split()
    if len(args) < 3:
        await message.answer("⚠️ Использование: `/calc 2.10 2.05`")
        return
    try:
        k1 = float(args[1])
        k2 = float(args[2])
        bank, step = await get_user_settings(message.chat.id, 100000.0, 500)
        res = calculate_surebet(k1, k2, bank, round_step=step)
        
        if res.has_surebet:
            ans = (
                f"🎯 **ВИЛКА НАЙДЕНА ({res.profit_percent}%)**\n\n"
                f"🔹 Ставка 1 (K={res.k1}): *{res.s1:,} ₸*\n"
                f"🔹 Ставка 2 (K={res.k2}): *{res.s2:,} ₸*\n\n"
                f"💰 Затраты: *{res.total_spent:,} ₸*\n"
                f"📈 Прибыль: *{res.profit:,} ₸*"
            ).replace(",", " ")
        else:
            ans = f"❌ **Вилки нет.** Доходность: `{res.profit_percent}%`"
        await message.answer(ans)
    except ValueError:
        await message.answer("⚠️ Введите корректные коэффициенты числами.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
