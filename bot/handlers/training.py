from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from data.shared import main_menu_keyboard, course_titles, courses  # Імпортуємо із shared.py
from data.progress import update_module_progress

router = Router()

class TrainingState(StatesGroup):
    choosing_course = State()
    choosing_module = State()


def get_all_modules():
    modules = []
    for course in courses.values():
        modules.extend(course["modules"].keys())
    return modules

def course_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"course:{key}")]
        for key, name in course_titles.items()
    ] + [[InlineKeyboardButton(text="🏠 Меню", callback_data="to_menu")]])


def module_navigation_keyboard(course_key: str, module_index: int, is_last: bool = False):
    buttons = []

    if not is_last:
        buttons.append(InlineKeyboardButton(text="➡️ Наступний модуль", callback_data=f"module:{course_key}:{module_index + 1}"))
    else:
        buttons.append(InlineKeyboardButton(text="🏁 Завершити курс", callback_data="finish_course"))

    # Додаємо кнопку для тестування
    buttons.append(InlineKeyboardButton(text="📝 Пройти тестування", callback_data=f"start_quiz:{course_key}:{module_index}"))

    buttons.append(InlineKeyboardButton(text="🏠 Меню", callback_data="to_menu"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

@router.message(F.text == "📘 Почати/Продовжити навчання")
async def start_training(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📚 Оберіть навчальний курс:", reply_markup=course_inline_keyboard())
    await state.set_state(TrainingState.choosing_course)

@router.callback_query(F.data.startswith("course:"))
async def open_course(callback: CallbackQuery, state: FSMContext):
    course_key = callback.data.split(":", 1)[1]
    course_name = course_titles.get(course_key)
    if not course_name:
        await callback.message.answer("❗️ Помилка: курс не знайдено.")
        return
    await state.update_data(course=course_key)
    await callback.message.edit_text(f"📖 Обрано курс: <b>{course_name}</b>\n\n📘 Починаємо з першого модуля ⬇️", parse_mode="HTML")
    await send_module(callback.message, course_key, 0)


async def send_module(message: Message, course_key: str, module_index: int):
    course = courses[course_key]
    modules = list(course["modules"].values())  # Отримуємо список модулів
    module_titles = list(course["modules"].keys())  # Отримуємо ідентифікатори модулів

    if module_index >= len(modules):
        # Якщо всі модулі завершені
        await message.answer("✅ Всі модулі завершено.")
        return

    module = modules[module_index]
    module_id = module_titles[module_index]  # Отримуємо ідентифікатор модуля

    # Оновлюємо прогрес
    update_module_progress(message.from_user.id, course_key, module_id)

    # Відображення модуля
    header = f"<b>📘 {module['title']}</b>\n\n"
    summary = "\n".join(f"• {line}" for line in module["summary"])
    summary_text = f"<b>Короткий зміст:</b>\n{summary}\n\n"
    description = f"<b>Опис:</b>\n{module['description']}"

    full_text = header + summary_text + description

    # Telegram обмежує текст повідомлення до 4096 символів
    chunks = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]

    for i, chunk in enumerate(chunks):
        if i == len(chunks) - 1:
            # Останній блок з кнопками
            await message.answer(
                chunk,
                parse_mode="HTML",
                reply_markup=module_navigation_keyboard(course_key, module_index, is_last=(module_index == len(modules) - 1))
            )
        else:
            await message.answer(chunk, parse_mode="HTML")


@router.callback_query(F.data.startswith("module:"))
async def next_module(callback: CallbackQuery, state: FSMContext):
    _, course_name, module_index = callback.data.split(":", 2)
    await send_module(callback.message, course_name, int(module_index))

@router.callback_query(F.data == "finish_course")
async def finish_course(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🎉 Ви успішно завершили курс! Вітаємо!\n\n🧪 Можна перейти до тестування або повернутись у головне меню.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🧪 До тесту", callback_data="to_test"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="to_menu")
            ]
        ])
    )

@router.callback_query(F.data == "to_menu")
async def return_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("🔙 Ви повернулись у головне меню.", reply_markup=main_menu_keyboard)