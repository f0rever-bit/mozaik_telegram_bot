from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import os
import httpx
import re

from handlers.start import main_menu_keyboard  # ІМПОРТ головної клавіатури

router = Router()

faq_data = {
    "🔑 Активація mozaBook": "Для активації використовуйте код Classroom+ у налаштуваннях програми.",
    "🌐 Реєстрація в mozaWeb": "Перейдіть на https://www.mozaweb.com та натисніть 'Зареєструватися'.",
    "💾 Збереження уроків": "Ви можете зберігати уроки у PDF або у форматі mozaBook.",
    "🧩 Вставка відео/3D-сцен": "Через меню вставки виберіть тип контенту: відео або 3D-сцена.",
    "📱 Проблеми з входом": "Переконайтесь, що ваш акаунт активований та використовується правильний пароль.",
}

class FAQState(StatesGroup):
    awaiting_question = State()

faq_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=question)] for question in faq_data.keys()] + [
        [KeyboardButton(text="🧠 Інше питання")],
        [KeyboardButton(text="🏠 Меню")]
    ],
    resize_keyboard=True
)

def markdown_to_html(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    return text

@router.message(F.text == "❓ Часті питання (FAQ)")
async def show_faq(message: Message, state: FSMContext):
    await message.answer("Оберіть питання зі списку або задайте своє:", reply_markup=faq_keyboard)
    await state.set_state(FAQState.awaiting_question)

@router.message(F.text.in_(faq_data.keys()))
async def send_direct_faq(message: Message, state: FSMContext):
    await message.answer(f"📌 <b>Відповідь:</b>{faq_data[message.text]}", parse_mode="HTML")

@router.message(F.text == "🧠 Інше питання")
async def ask_custom_faq(message: Message, state: FSMContext):
    await message.answer("Напишіть своє запитання — я постараюсь відповісти, спираючись на базу знань (FAQ).")

@router.message(F.text == "🏠 Меню")
async def exit_to_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔙 Ви повернулись у головне меню. Оберіть дію:", reply_markup=main_menu_keyboard)

@router.message(FAQState.awaiting_question)
async def handle_custom_question(message: Message, state: FSMContext):
    if message.text == "🏠 Меню":
        await exit_to_menu(message, state)
        return

    user_question = message.text
    await message.answer("⏳ Формулюю відповідь у зручному форматі...")

    faq_summary = "\n".join([f"• {k}: {v}" for k, v in faq_data.items()])

    styled_prompt = f"""Ти освітній Telegram-бот. Відповідай українською мовою, стисло, доброзичливо, структуровано.

📌 Завжди використовуй:
— емодзі для візуального орієнтування
— жирний текст для ключових понять
— нумеровані або марковані списки
— поради або попередження (з ⚠️ чи 💡) при потребі

Не пиши довгих абзаців — краще використовуй списки. Відповідай як досвідчений онлайн-асистент для вчителів.

📚 Ось база знань FAQ:
{faq_summary}
"""

    api_url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/mozaik_edpro_bot",
        "X-Title": "Mozaik Edu Bot"
    }

    payload = {
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "messages": [
            {"role": "system", "content": styled_prompt},
            {"role": "user", "content": user_question}
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)
            result = response.json()

        if "choices" in result:
            reply = result["choices"][0]["message"]["content"]
        else:
            reply = f"⚠️ Не вдалося отримати відповідь: {result}"

        max_length = 4000
        for i in range(0, len(reply), max_length):
            chunk = markdown_to_html(reply[i:i+max_length])
            await message.answer(chunk, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"⚠️ Сталася помилка:\n<code>{str(e)}</code>")
