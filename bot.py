import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from database import init_db, add_meal, get_today_meals, get_today_total, delete_meal

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

DAILY_LIMIT = 1800  # Ваш дневной лимит калорий


# Состояния для пошагового ввода еды
class AddMeal(StatesGroup):
    waiting_for_name = State()
    waiting_for_calories = State()


# Клавиатура
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🍽 Добавить приём пищи")],
        [KeyboardButton(text="📊 Статистика за день")],
        [KeyboardButton(text="🗑 Удалить запись")],
    ],
    resize_keyboard=True,
)


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет! Я твой трекер калорий 🍎\n"
        f"Дневной лимит: {DAILY_LIMIT} ккал\n\n"
        f"Записывай всё, что ешь, и я посчитаю за тебя!",
        reply_markup=main_kb,
    )


# === ДОБАВЛЕНИЕ ЕДЫ (FSM) ===
@dp.message(F.text == "🍽 Добавить приём пищи")
async def meal_start(message: types.Message, state: FSMContext):
    await message.answer("Что вы съели? Напишите название:")
    await state.set_state(AddMeal.waiting_for_name)


@dp.message(AddMeal.waiting_for_name)
async def meal_name(message: types.Message, state: FSMContext):
    await state.update_data(meal_name=message.text)
    await message.answer(
        f"Записал: {message.text}\nТеперь напишите количество калорий (число):"
    )
    await state.set_state(AddMeal.waiting_for_calories)


@dp.message(AddMeal.waiting_for_calories)
async def meal_calories(message: types.Message, state: FSMContext):
    # Проверяем, что пользователь ввёл число
    if not message.text.isdigit():
        await message.answer("⚠️ Введите число! Например: 350")
        return

    calories = int(message.text)
    data = await state.get_data()
    meal_name_text = data["meal_name"]

    # Сохраняем в базу
    add_meal(message.from_user.id, meal_name_text, calories)

    # Считаем итог за день
    total = get_today_total(message.from_user.id)
    remaining = DAILY_LIMIT - total

    if remaining > 0:
        status = f"✅ Осталось на сегодня: {remaining} ккал"
    else:
        status = f"🔴 Лимит превышен на {abs(remaining)} ккал!"

    await message.answer(
        f"🍽 Записано: {meal_name_text} — {calories} ккал\n"
        f"📊 Итого за день: {total} / {DAILY_LIMIT} ккал\n"
        f"{status}"
    )
    await state.clear()


# === СТАТИСТИКА ===
@dp.message(F.text == "📊 Статистика за день")
async def day_stats(message: types.Message):
    meals = get_today_meals(message.from_user.id)
    total = get_today_total(message.from_user.id)

    if not meals:
        await message.answer("Сегодня пока ничего не записано. Начните с кнопки 🍽")
        return

    text = "📋 Ваш дневник за сегодня:\n\n"
    for meal in meals:
        text += f"• {meal[1]} — {meal[2]} ккал ({meal[3]})\n"

    remaining = DAILY_LIMIT - total
    if remaining > 0:
        text += (
            f"\n📊 Итого: {total} / {DAILY_LIMIT} ккал\n✅ Осталось: {remaining} ккал"
        )
    else:
        text += f"\n📊 Итого: {total} / {DAILY_LIMIT} ккал\n🔴 Превышение: {abs(remaining)} ккал"

    await message.answer(text)


# === УДАЛЕНИЕ ЗАПИСИ ===
@dp.message(F.text == "🗑 Удалить запись")
async def delete_start(message: types.Message):
    meals = get_today_meals(message.from_user.id)

    if not meals:
        await message.answer("Сегодня записей нет — удалять нечего 🤷")
        return

    # Создаём инлайн-кнопку для каждой записи
    buttons = []
    for meal in meals:
        meal_id, name, cals, time = meal
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"❌ {name} — {cals} ккал", callback_data=f"del_{meal_id}"
                )
            ]
        )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Какую запись удалить?", reply_markup=kb)


@dp.callback_query(F.data.startswith("del_"))
async def process_delete(callback: CallbackQuery):
    meal_id = int(callback.data.split("_")[1])
    delete_meal(meal_id)

    # Обновляем итог
    total = get_today_total(callback.from_user.id)
    remaining = DAILY_LIMIT - total

    await callback.message.answer(
        f"🗑 Запись удалена!\n📊 Итого за день: {total} / {DAILY_LIMIT} ккал\n✅ Осталось: {remaining} ккал"
    )
    await callback.answer()


async def main():
    init_db()
    print("CalorieBot is running!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
