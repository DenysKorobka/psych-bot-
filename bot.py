"""
Бот-візитка психолога / коуча
==============================
Telegram-бот-шаблон для психологів:
- Воронка довіри (про психолога, підходи, відгуки)
- Тест самодіагностики (7 питань)
- Онлайн-запис на консультацію
- Безкоштовні матеріали (PDF/гайд)
- Daily check-in
- AI-помічник (Claude API) — відповідає як м'який терапевт
"""

import os
import json
import logging
from datetime import datetime, time
from anthropic import AsyncAnthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

# ─── Логування ────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Токени (зі змінних середовища) ──────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВАШ_ТОКЕН_ТУТ")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
PSYCHOLOGIST_CHAT_ID = os.environ.get("PSYCHOLOGIST_CHAT_ID", "")  # куди йдуть заявки

# ─── Anthropic клієнт ─────────────────────────────────────────────────────────
anthropic_client = AsyncAnthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None

# ─── Файл даних ───────────────────────────────────────────────────────────────
DATA_FILE = "users_data.json"

# ══════════════════════════════════════════════════════════════════════════════
#  КОНТЕНТ БОТА
# ══════════════════════════════════════════════════════════════════════════════

PSYCHOLOGIST = {
    "name": "Олена Коваленко",
    "title": "Психолог · Коуч · 5 років практики",
    "tagline": "Простір для самопізнання та змін 💚",
    "about": (
        "Мене звати *Олена*.\n\n"
        "Я практикуючий психолог та коуч.\n\n"
        "🔹 5 років практики\n"
        "🔹 300+ проведених сесій\n"
        "🔹 Клієнти з 7 країн\n\n"
        "Я допомагаю людям:\n"
        "• зрозуміти себе та свої реакції\n"
        "• впоратися з тривожністю та вигоранням\n"
        "• налагодити стосунки з собою та іншими\n"
        "• знайти внутрішню опору в складні моменти"
    ),
    "approach": (
        "🧠 *Підхід у роботі*\n\n"
        "Я працюю в інтегративному підході, поєднуючи:\n\n"
        "• *КПТ* — когнітивно-поведінкова терапія\n"
        "  Змінюємо думки, що заважають жити\n\n"
        "• *Схема-терапія*\n"
        "  Працюємо з глибинними переконаннями\n\n"
        "• *Mindfulness*\n"
        "  Вчимося бути тут і зараз без оцінювання\n\n"
        "_Ми не копаємось у минулому заради болю —_\n"
        "_ми шукаємо там ресурс для теперішнього._"
    ),
    "education": (
        "🎓 *Освіта та кваліфікація*\n\n"
        "• Київський університет ім. Шевченка\n"
        "  Факультет психології, магістр\n\n"
        "• Сертифікат КПТ — Інститут когнітивної терапії\n\n"
        "• Навчання схема-терапії (ISST)\n\n"
        "• Регулярна супервізія та особиста терапія"
    ),
}

SERVICES = {
    "individual": {
        "title": "Індивідуальна консультація",
        "duration": "60 хвилин",
        "price": "70$",
        "description": (
            "💬 *Індивідуальна консультація*\n\n"
            "⏱ 60 хвилин · 💵 70$\n\n"
            "Що відбувається на сесії:\n"
            "• Розбір вашої ситуації та запиту\n"
            "• Індивідуальні рекомендації\n"
            "• Практичні інструменти\n"
            "• План роботи\n\n"
            "_Перша сесія — знайомство та визначення напряму роботи._"
        ),
    },
    "coaching": {
        "title": "Коучинг-програма",
        "duration": "4 зустрічі / місяць",
        "price": "240$",
        "description": (
            "🌱 *Коучинг-програма*\n\n"
            "⏱ 4 зустрічі протягом місяця · 💵 240$\n\n"
            "Що включено:\n"
            "• Глибока робота над вашим запитом\n"
            "• Підтримка між сесіями у Telegram\n"
            "• Домашні практики та завдання\n"
            "• Трекер прогресу\n\n"
            "_Для тих, хто готовий до системних змін._"
        ),
    },
    "emergency": {
        "title": "Екстрена підтримка",
        "duration": "30 хвилин",
        "price": "40$",
        "description": (
            "🆘 *Екстрена підтримка*\n\n"
            "⏱ 30 хвилин · 💵 40$\n\n"
            "Коли потрібно:\n"
            "• Гостра тривога або паніка\n"
            "• Важке рішення треба прийняти зараз\n"
            "• Гостра криза у стосунках\n\n"
            "_Відповідь протягом 2 годин в робочий час._"
        ),
    },
}

TOPICS = {
    "anxiety": {
        "label": "😰 Тривожність",
        "text": (
            "😰 *Тривожність*\n\n"
            "Я допомагаю клієнтам, які відчувають:\n\n"
            "• Постійне внутрішнє напруження\n"
            "• Страх майбутнього і катастрофізацію\n"
            "• Нав'язливі тривожні думки\n"
            "• Панічні атаки або їх передчуття\n"
            "• Труднощі з розслабленням\n\n"
            "На консультації ми *знайдемо корінь тривоги* та опрацюємо "
            "конкретні інструменти для стабілізації стану."
        ),
    },
    "relations": {
        "label": "💔 Стосунки",
        "text": (
            "💔 *Стосунки*\n\n"
            "Я допомагаю, коли:\n\n"
            "• Конфлікти повторюються по колу\n"
            "• Важко встановити особисті кордони\n"
            "• Є залежність або токсична прив'язаність\n"
            "• Переживаєте розставання або зраду\n"
            "• Складно відчути близькість з партнером\n\n"
            "Ми розбираємо *патерни*, що тягнуться з дитинства, "
            "і вчимося будувати стосунки по-новому."
        ),
    },
    "selfesteem": {
        "label": "🪞 Самооцінка",
        "text": (
            "🪞 *Самооцінка та впевненість*\n\n"
            "Я допомагаю, коли:\n\n"
            "• Хронічно порівнюєте себе з іншими\n"
            "• Важко відстоювати свою думку\n"
            "• Синдром самозванця заважає рухатись вперед\n"
            "• Важко приймати компліменти\n"
            "• Відчуття, що «я недостатньо хороший(а)»\n\n"
            "Разом ми знайдемо *глибинні переконання* про себе "
            "і замінимо їх на ті, що підтримують."
        ),
    },
    "burnout": {
        "label": "🔥 Вигорання",
        "text": (
            "🔥 *Вигорання*\n\n"
            "Я допомагаю, коли:\n\n"
            "• Немає сил і мотивації навіть для улюблених речей\n"
            "• Відчуття порожнечі та апатії\n"
            "• Роздратованість на всіх і все\n"
            "• Хронічна втома, що не минає після відпочинку\n"
            "• «Я просто виконую функції»\n\n"
            "Ми відновимо *ресурс* і знайдемо причину виснаження."
        ),
    },
    "identity": {
        "label": "🔍 Пошук себе",
        "text": (
            "🔍 *Пошук себе*\n\n"
            "Я допомагаю, коли:\n\n"
            "• Відчуття, що живете «не своє» життя\n"
            "• Не розумієте чого хочете насправді\n"
            "• Страх змін паралізує\n"
            "• Криза сенсу і цілей\n"
            "• Питання «хто я?» залишається без відповіді\n\n"
            "Разом ми *дослідимо вашу ідентичність* і знайдемо "
            "напрямок, який резонує з вашою справжньою природою."
        ),
    },
    "other": {
        "label": "💬 Інша тема",
        "text": (
            "💬 *Інша тема*\n\n"
            "Кожна ситуація унікальна.\n\n"
            "Якщо ваш запит не підпадає під жодну категорію — "
            "це не означає, що я не зможу допомогти.\n\n"
            "Напишіть мені напряму — і ми разом визначимо, "
            "чи підходить моя допомога для вашої ситуації."
        ),
    },
}

TESTIMONIALS = [
    {
        "text": "Після трьох місяців роботи з Оленою я нарешті навчилась говорити «ні» без почуття провини. Звучить просто — але для мене це було революцією.",
        "author": "Марія, 31 рік",
    },
    {
        "text": "Я прийшов із панічними атаками, які траплялись по кілька разів на тиждень. Через 2 місяці — жодної. Ми зрозуміли причину, і це змінило все.",
        "author": "Андрій, 28 років",
    },
    {
        "text": "Олена допомогла мені вийти з токсичних стосунків і не повертатись. Не просто підтримала — а дала інструменти, які реально працюють.",
        "author": "Катерина, 35 років",
    },
    {
        "text": "Я була скептиком щодо психологів. Але після першої сесії зрозуміла — це те, чого мені не вистачало роками. Безпечно, глибоко, без осуду.",
        "author": "Юля, 26 років",
    },
]

FREE_MATERIALS = [
    {
        "id": "anxiety_guide",
        "title": "5 способів заспокоїти тривогу за 10 хвилин",
        "description": "Практичний гайд з техніками, які реально працюють у момент тривоги",
        "emoji": "😮‍💨",
        "url": "https://example.com/anxiety-guide.pdf",  # замінити на реальне посилання
    },
    {
        "id": "boundaries_checklist",
        "title": "Чеклист: «Чи є у мене особисті кордони?»",
        "description": "15 запитань, які покажуть де ваші кордони порушуються",
        "emoji": "✅",
        "url": "https://example.com/boundaries.pdf",
    },
    {
        "id": "burnout_test",
        "title": "Тест на вигорання + план відновлення",
        "description": "Визначте рівень вигорання та отримайте персональний план",
        "emoji": "🔋",
        "url": "https://example.com/burnout.pdf",
    },
]

# ── Питання тесту ─────────────────────────────────────────────────────────────
TEST_QUESTIONS = [
    {
        "id": 1,
        "text": "Як часто ви відчуваєте тривогу або внутрішнє напруження?",
        "options": [
            ("Рідко або ніколи", 0),
            ("Іноді, але швидко минає", 1),
            ("Досить часто", 2),
            ("Майже постійно", 3),
        ],
    },
    {
        "id": 2,
        "text": "Як у вас зі сном?",
        "options": [
            ("Сплю добре, прокидаюсь відпочилим(ою)", 0),
            ("Іноді важко заснути", 1),
            ("Часто погано сплю або прокидаюсь рано", 2),
            ("Постійні проблеми зі сном", 3),
        ],
    },
    {
        "id": 3,
        "text": "Чи відчуваєте емоційне виснаження або порожнечу?",
        "options": [
            ("Ні, відчуваю себе наповненим(ою)", 0),
            ("Іноді відчуваю втому", 1),
            ("Часто відчуваю виснаження", 2),
            ("Постійна порожнеча і апатія", 3),
        ],
    },
    {
        "id": 4,
        "text": "Як складаються ваші стосунки з близькими?",
        "options": [
            ("Все добре, почуваюсь зрозумілим(ою)", 0),
            ("Є невеликі непорозуміння", 1),
            ("Часті конфлікти або дистанція", 2),
            ("Стосунки дуже напружені або їх майже немає", 3),
        ],
    },
    {
        "id": 5,
        "text": "Чи є у вас відчуття сенсу та мотивації у житті?",
        "options": [
            ("Так, знаю навіщо прокидаюсь", 0),
            ("Іноді втрачаю напрямок", 1),
            ("Часто відчуваю безглуздість", 2),
            ("Відчуття, що живу «на автопілоті»", 3),
        ],
    },
    {
        "id": 6,
        "text": "Як ви реагуєте на стрес?",
        "options": [
            ("Справляюсь спокійно", 0),
            ("Іноді реагую гостро, але відновлююсь", 1),
            ("Стрес довго не відпускає", 2),
            ("Навіть дрібниці виводять з рівноваги", 3),
        ],
    },
    {
        "id": 7,
        "text": "Чи задоволені ви собою та своїм життям загалом?",
        "options": [
            ("Так, в цілому все добре", 0),
            ("Є що покращити, але загалом ok", 1),
            ("Часто відчуваю незадоволення", 2),
            ("Постійне відчуття, що щось не так", 3),
        ],
    },
]

def get_test_result(score: int) -> dict:
    if score <= 4:
        return {
            "level": "🟢 Стабільний стан",
            "text": (
                "Ваш емоційний стан загалом стабільний.\n\n"
                "Це чудово! Але навіть у стабільному стані робота з психологом "
                "допомагає глибше пізнати себе, покращити стосунки та розкрити потенціал.\n\n"
                "_Профілактична робота — найефективніша._"
            ),
            "cta": True,
        }
    elif score <= 10:
        return {
            "level": "🟡 Є зони для уваги",
            "text": (
                "Ваш результат показує, що є кілька зон, які потребують уваги.\n\n"
                "Можливо, ви вже відчуваєте, що щось «не так», але ще не розуміли що саме. "
                "Це хороший момент для початку роботи — поки ситуація не поглибилась.\n\n"
                "_Краще почати зараз, ніж чекати поки стане гірше._"
            ),
            "cta": True,
        }
    elif score <= 16:
        return {
            "level": "🟠 Потрібна підтримка",
            "text": (
                "Ваш результат вказує на значний рівень емоційного навантаження.\n\n"
                "Ви, мабуть, давно несете це в собі. Втома від цього цілком природна. "
                "Важливо не залишатись з цим наодинці — підтримка психолога може суттєво "
                "змінити якість вашого повсякденного життя.\n\n"
                "_Перший крок — найважчий. Але ви вже зробили його, пройшовши цей тест._"
            ),
            "cta": True,
        }
    else:
        return {
            "level": "🔴 Рекомендую звернутись",
            "text": (
                "Ваш результат говорить про те, що зараз вам справді важко.\n\n"
                "Я бачу, що ви несете дуже багато. Це потребує уваги та підтримки. "
                "Будь ласка, не відкладайте — зверніться до фахівця.\n\n"
                "_Звернутись по допомогу — це не слабкість. Це сміливість._"
            ),
            "cta": True,
        }

# ── Запис на прийом — стани ───────────────────────────────────────────────────
BOOKING_STEPS = ["format", "name", "contact", "request"]

BOOKING_FORMATS = {
    "online": "🌐 Онлайн (Zoom/Google Meet)",
    "offline": "🏢 Офлайн (Київ, вул. Хрещатик 1)",
}

# ══════════════════════════════════════════════════════════════════════════════
#  РОБОТА З ДАНИМИ
# ══════════════════════════════════════════════════════════════════════════════

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(data: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "started_at": None,
            "test_score": None,
            "test_answers": [],
            "test_step": 0,
            "booking": {},
            "booking_step": None,
            "checkin_enabled": False,
            "ai_mode": False,
            "ai_history": [],
            "materials_received": [],
        }
    return data[uid]

# ══════════════════════════════════════════════════════════════════════════════
#  КЛАВІАТУРИ
# ══════════════════════════════════════════════════════════════════════════════

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧑‍💼 Про психолога", callback_data="about_psychologist")],
        [InlineKeyboardButton("💭 Чим я можу допомогти", callback_data="topics_menu")],
        [InlineKeyboardButton("📋 Пройти тест", callback_data="test_start")],
        [InlineKeyboardButton("💼 Консультації та ціни", callback_data="services_menu")],
        [InlineKeyboardButton("📅 Записатись", callback_data="book_start")],
        [InlineKeyboardButton("🎁 Безкоштовні матеріали", callback_data="materials_menu")],
        [InlineKeyboardButton("⭐️ Відгуки", callback_data="testimonials")],
        [InlineKeyboardButton("🤖 AI-помічник", callback_data="ai_start")],
        [InlineKeyboardButton("📞 Поставити питання", callback_data="ask_question")],
    ])

def back_to_menu():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")
    ]])

def back_row(callback: str = "main_menu", label: str = "← Назад"):
    return [InlineKeyboardButton(label, callback_data=callback)]

# ══════════════════════════════════════════════════════════════════════════════
#  AI-ПОМІЧНИК (Claude)
# ══════════════════════════════════════════════════════════════════════════════

AI_SYSTEM_PROMPT = """Ти — теплий, уважний AI-помічник психолога Олени. 
Ти відповідаєш українською мовою.

Твоя роль:
- Надавати емоційну підтримку та розуміння
- Допомагати людині краще зрозуміти свій стан
- Задавати м'які уточнюючі запитання
- Ніколи не ставити діагнозів
- Не замінювати живого психолога

Стиль спілкування:
- Тепло і без осуду
- Коротко і по суті (2-4 речення)
- Якщо людина в кризі — м'яко направляй до запису на консультацію
- Іноді завершуй відповідь одним запитанням до людини

Обмеження:
- Ти не даєш медичних порад
- Ти не обговорюєш теми, не пов'язані з психологічним станом
- Якщо запит виходить за рамки — м'яко поверни до теми"""

async def get_ai_response(history: list, user_message: str) -> str:
    if not anthropic_client:
        return (
            "AI-помічник зараз недоступний. "
            "Але ви завжди можете записатись на консультацію до Олени 💚"
        )
    
    messages = history[-10:] + [{"role": "user", "content": user_message}]
    
    try:
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=AI_SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return (
            "Вибачте, сталась технічна помилка. "
            "Ви можете написати Олені напряму 💚"
        )

# ══════════════════════════════════════════════════════════════════════════════
#  ОБРОБНИКИ КОМАНД
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_data()
    user = get_user(db, update.effective_user.id)
    if not user["started_at"]:
        user["started_at"] = datetime.now().isoformat()
    save_data(db)

    first_name = update.effective_user.first_name or "друже"
    text = (
        f"Привіт, {first_name}! 👋\n\n"
        f"Я бот психолога *{PSYCHOLOGIST['name']}*.\n\n"
        f"_{PSYCHOLOGIST['tagline']}_\n\n"
        "Тут ти можеш:\n"
        "• дізнатись більше про мою роботу\n"
        "• пройти короткий тест самодіагностики\n"
        "• записатись на консультацію\n"
        "• отримати безкоштовні матеріали\n"
        "• поговорити з AI-помічником\n\n"
        "Обери, з чого хочеш почати 👇"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )

# ══════════════════════════════════════════════════════════════════════════════
#  СМАРТ-EDIT (як у попередньому боті)
# ══════════════════════════════════════════════════════════════════════════════

async def smart_edit(query, text, reply_markup, parse_mode="Markdown"):
    try:
        if query.message.photo or query.message.document:
            await query.message.delete()
            await query.message.chat.send_message(
                text=text, parse_mode=parse_mode, reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                text, parse_mode=parse_mode, reply_markup=reply_markup
            )
    except Exception:
        try:
            await query.edit_message_text(
                text, parse_mode=parse_mode, reply_markup=reply_markup
            )
        except Exception:
            await query.message.reply_text(
                text, parse_mode=parse_mode, reply_markup=reply_markup
            )

# ══════════════════════════════════════════════════════════════════════════════
#  ОБРОБНИК CALLBACK-КНОПОК
# ══════════════════════════════════════════════════════════════════════════════

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cb = query.data

    db = load_data()
    user = get_user(db, query.from_user.id)

    # ── Головне меню ──────────────────────────────────────────────────────────
    if cb == "main_menu":
        user["ai_mode"] = False
        save_data(db)
        first_name = query.from_user.first_name or "друже"
        await smart_edit(query,
            f"Привіт, {first_name}! 👋\n\nОберіть що хочете зробити:",
            reply_markup=main_menu_keyboard()
        )

    # ── Про психолога ─────────────────────────────────────────────────────────
    elif cb == "about_psychologist":
        await smart_edit(query,
            PSYCHOLOGIST["about"],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🧠 Підхід у роботі", callback_data="about_approach")],
                [InlineKeyboardButton("🎓 Освіта", callback_data="about_education")],
                [InlineKeyboardButton("📅 Записатись", callback_data="book_start")],
                back_row(),
            ])
        )

    elif cb == "about_approach":
        await smart_edit(query,
            PSYCHOLOGIST["approach"],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Записатись", callback_data="book_start")],
                back_row("about_psychologist", "← Про психолога"),
            ])
        )

    elif cb == "about_education":
        await smart_edit(query,
            PSYCHOLOGIST["education"],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Записатись", callback_data="book_start")],
                back_row("about_psychologist", "← Про психолога"),
            ])
        )

    # ── Теми допомоги ─────────────────────────────────────────────────────────
    elif cb == "topics_menu":
        buttons = [
            [InlineKeyboardButton(t["label"], callback_data=f"topic_{key}")]
            for key, t in TOPICS.items()
        ]
        buttons.append(back_row())
        await smart_edit(query,
            "💭 *Чим я можу допомогти*\n\nОберіть тему, яка зараз найбільше відгукується:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif cb.startswith("topic_"):
        key = cb.split("_", 1)[1]
        topic = TOPICS.get(key)
        if topic:
            await smart_edit(query,
                topic["text"],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📅 Записатись", callback_data="book_start")],
                    [InlineKeyboardButton("📋 Пройти тест", callback_data="test_start")],
                    back_row("topics_menu", "← Назад до тем"),
                ])
            )

    # ── Послуги ───────────────────────────────────────────────────────────────
    elif cb == "services_menu":
        await smart_edit(query,
            "💼 *Консультації та ціни*\n\nОберіть формат:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Індивідуальна консультація — 70$", callback_data="service_individual")],
                [InlineKeyboardButton("🌱 Коучинг-програма — 240$", callback_data="service_coaching")],
                [InlineKeyboardButton("🆘 Екстрена підтримка — 40$", callback_data="service_emergency")],
                back_row(),
            ])
        )

    elif cb.startswith("service_"):
        key = cb.split("_", 1)[1]
        service = SERVICES.get(key)
        if service:
            await smart_edit(query,
                service["description"],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📅 Записатись", callback_data="book_start")],
                    [InlineKeyboardButton("❓ Поставити питання", callback_data="ask_question")],
                    back_row("services_menu", "← До послуг"),
                ])
            )

    # ── ТЕСТ ─────────────────────────────────────────────────────────────────
    elif cb == "test_start":
        user["test_step"] = 0
        user["test_answers"] = []
        save_data(db)
        await smart_edit(query,
            "📋 *Тест самодіагностики*\n\n"
            "7 коротких питань, щоб краще зрозуміти свій стан.\n"
            "Займе лише *2–3 хвилини*.\n\n"
            "_Відповідай чесно — результат лише для тебе_ 🔒",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Почати тест", callback_data="test_question_0")],
                back_row(),
            ])
        )

    elif cb.startswith("test_question_"):
        q_idx = int(cb.split("_")[-1])
        if q_idx >= len(TEST_QUESTIONS):
            # Показуємо результат
            score = sum(user.get("test_answers", []))
            result = get_test_result(score)
            user["test_score"] = score
            save_data(db)

            text = (
                f"📊 *Результат тесту*\n\n"
                f"{result['level']}\n\n"
                f"{result['text']}"
            )
            await smart_edit(query, text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📅 Записатись на консультацію", callback_data="book_start")],
                    [InlineKeyboardButton("💬 Поговорити з AI-помічником", callback_data="ai_start")],
                    back_row(),
                ])
            )
            return

        q = TEST_QUESTIONS[q_idx]
        progress = f"Питання {q_idx + 1} з {len(TEST_QUESTIONS)}"
        progress_bar = "🟢" * (q_idx + 1) + "⚪" * (len(TEST_QUESTIONS) - q_idx - 1)

        buttons = [
            [InlineKeyboardButton(opt[0], callback_data=f"test_answer_{q_idx}_{opt[1]}")]
            for opt in q["options"]
        ]
        await smart_edit(query,
            f"_{progress}_\n{progress_bar}\n\n*{q['text']}*",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif cb.startswith("test_answer_"):
        parts = cb.split("_")
        q_idx = int(parts[2])
        answer = int(parts[3])

        answers = user.get("test_answers", [])
        if len(answers) <= q_idx:
            answers.append(answer)
        else:
            answers[q_idx] = answer
        user["test_answers"] = answers
        save_data(db)

        # Наступне питання
        next_q = q_idx + 1
        context.user_data["test_next"] = next_q
        await handle_callback_by_data(query, context, db, user, f"test_question_{next_q}")

    # ── ЗАПИС ─────────────────────────────────────────────────────────────────
    elif cb == "book_start":
        user["booking"] = {}
        user["booking_step"] = "format"
        save_data(db)
        await smart_edit(query,
            "📅 *Запис на консультацію*\n\n"
            "Давайте оберемо зручний формат 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Онлайн (Zoom/Meet)", callback_data="book_format_online")],
                [InlineKeyboardButton("🏢 Офлайн (Київ)", callback_data="book_format_offline")],
                back_row(),
            ])
        )

    elif cb.startswith("book_format_"):
        fmt = cb.split("_")[-1]
        user["booking"]["format"] = BOOKING_FORMATS.get(fmt, fmt)
        user["booking_step"] = "name"
        save_data(db)
        await smart_edit(query,
            f"✅ Формат: *{BOOKING_FORMATS.get(fmt)}*\n\n"
            "Як вас звати?\n\n"
            "_Напишіть своє ім'я у відповідь 👇_",
            reply_markup=InlineKeyboardMarkup([back_row("book_start", "← Назад")])
        )

    elif cb == "book_service_confirm":
        # Підтвердження запису після вибору послуги
        booking = user.get("booking", {})
        text = (
            "✅ *Заявку прийнято!*\n\n"
            f"📋 *Деталі:*\n"
            f"• Ім'я: {booking.get('name', '—')}\n"
            f"• Контакт: {booking.get('contact', '—')}\n"
            f"• Формат: {booking.get('format', '—')}\n"
            f"• Запит: {booking.get('request', 'не вказано')}\n\n"
            "Олена зв'яжеться з вами протягом *2–4 годин* в робочий час.\n\n"
            "_Дякуємо за довіру! 💚_"
        )
        user["booking_step"] = None
        save_data(db)
        await smart_edit(query, text, reply_markup=back_to_menu())
        await notify_psychologist(context.bot, booking)

    # ── МАТЕРІАЛИ ─────────────────────────────────────────────────────────────
    elif cb == "materials_menu":
        buttons = [
            [InlineKeyboardButton(
                f"{m['emoji']} {m['title']}", callback_data=f"material_{m['id']}"
            )]
            for m in FREE_MATERIALS
        ]
        buttons.append(back_row())
        await smart_edit(query,
            "🎁 *Безкоштовні матеріали*\n\n"
            "Оберіть що хочете отримати:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif cb.startswith("material_"):
        mat_id = cb.split("_", 1)[1]
        material = next((m for m in FREE_MATERIALS if m["id"] == mat_id), None)
        if material:
            received = user.get("materials_received", [])
            if mat_id not in received:
                received.append(mat_id)
                user["materials_received"] = received
                save_data(db)

            await smart_edit(query,
                f"{material['emoji']} *{material['title']}*\n\n"
                f"{material['description']}\n\n"
                f"📎 [Завантажити матеріал]({material['url']})\n\n"
                "_Якщо матеріал був корисним — ви завжди можете записатись на консультацію 💚_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📅 Записатись", callback_data="book_start")],
                    back_row("materials_menu", "← До матеріалів"),
                ])
            )

    # ── ВІДГУКИ ───────────────────────────────────────────────────────────────
    elif cb == "testimonials":
        text = "⭐️ *Відгуки клієнтів*\n\n"
        for t in TESTIMONIALS:
            text += f"«{t['text']}»\n— _{t['author']}_\n\n"
        await smart_edit(query, text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Записатись", callback_data="book_start")],
                back_row(),
            ])
        )

    # ── AI-ПОМІЧНИК ───────────────────────────────────────────────────────────
    elif cb == "ai_start":
        user["ai_mode"] = True
        user["ai_history"] = []
        save_data(db)
        await smart_edit(query,
            "🤖 *AI-помічник*\n\n"
            "Привіт! Я AI-асистент психолога Олени.\n\n"
            "Можу:\n"
            "• вислухати та підтримати\n"
            "• допомогти розібратись у своєму стані\n"
            "• відповісти на запитання про психологію\n\n"
            "⚠️ _Я не замінюю живого психолога, але можу стати першим кроком._\n\n"
            "*Про що хочеш поговорити?* 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Головне меню", callback_data="ai_exit")]
            ])
        )

    elif cb == "ai_exit":
        user["ai_mode"] = False
        save_data(db)
        await smart_edit(query,
            "Повертаємось до головного меню 👇",
            reply_markup=main_menu_keyboard()
        )

    # ── ПИТАННЯ ───────────────────────────────────────────────────────────────
    elif cb == "ask_question":
        user["booking_step"] = "free_question"
        save_data(db)
        await smart_edit(query,
            "📞 *Поставити питання*\n\n"
            "Напишіть ваше питання — Олена відповість найближчим часом.\n\n"
            "_Надрукуйте питання у відповідь 👇_",
            reply_markup=InlineKeyboardMarkup([back_row()])
        )

    # ── DAILY CHECK-IN ────────────────────────────────────────────────────────
    elif cb == "checkin_good":
        await smart_edit(query,
            "😊 *Радий(а) чути!*\n\n"
            "Підтримуй себе і сьогодні:\n"
            "• зроби щось маленьке для себе\n"
            "• зверни увагу на гарне\n\n"
            "_Якщо захочеш поговорити — я тут 💚_",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 AI-помічник", callback_data="ai_start")],
                back_row(),
            ])
        )

    elif cb == "checkin_ok":
        await smart_edit(query,
            "😐 *Нормально — теж добре*\n\n"
            "Іноді «нормально» — це чесна відповідь.\n\n"
            "Що могло б зробити сьогоднішній день трохи кращим?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Поговорити з AI", callback_data="ai_start")],
                back_row(),
            ])
        )

    elif cb == "checkin_hard":
        await smart_edit(query,
            "😔 *Дякую, що поділились*\n\n"
            "Важкі дні бувають у всіх. Ви не самотні.\n\n"
            "Можу запропонувати:\n"
            "• поговорити з AI-помічником\n"
            "• записатись на консультацію\n\n"
            "_Ви заслуговуєте підтримки_ 💚",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Поговорити зараз", callback_data="ai_start")],
                [InlineKeyboardButton("📅 Записатись до Олени", callback_data="book_start")],
                back_row(),
            ])
        )


async def handle_callback_by_data(query, context, db, user, data_str):
    """Внутрішній виклик handle_callback з довільним data."""
    query.data = data_str
    await handle_callback.__wrapped__(
        type('U', (), {'callback_query': query, 'effective_user': query.from_user})(),
        context
    ) if hasattr(handle_callback, '__wrapped__') else None


# ══════════════════════════════════════════════════════════════════════════════
#  ОБРОБНИК ТЕКСТОВИХ ПОВІДОМЛЕНЬ
# ══════════════════════════════════════════════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_data()
    user = get_user(db, update.effective_user.id)
    text = update.message.text.strip()

    # ── AI-режим ──────────────────────────────────────────────────────────────
    if user.get("ai_mode"):
        await update.message.chat.send_action("typing")
        history = user.get("ai_history", [])
        response = await get_ai_response(history, text)

        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": response})
        user["ai_history"] = history[-20:]
        save_data(db)

        await update.message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Записатись до Олени", callback_data="book_start")],
                [InlineKeyboardButton("🏠 Головне меню", callback_data="ai_exit")],
            ])
        )
        return

    # ── Крок запису: ім'я ─────────────────────────────────────────────────────
    if user.get("booking_step") == "name":
        user["booking"]["name"] = text
        user["booking_step"] = "contact"
        save_data(db)
        await update.message.reply_text(
            f"Приємно познайомитись, *{text}*! 👋\n\n"
            "Вкажіть ваш контакт для зв'язку:\n"
            "_(Telegram @username або номер телефону)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([back_row("book_start", "← Скасувати")])
        )
        return

    # ── Крок запису: контакт ──────────────────────────────────────────────────
    if user.get("booking_step") == "contact":
        user["booking"]["contact"] = text
        user["booking_step"] = "request"
        save_data(db)
        await update.message.reply_text(
            "Чудово! 📝\n\n"
            "Коротко опишіть ваш запит або з чим хочете попрацювати.\n"
            "_(Якщо не знаєте як описати — просто напишіть «не знаю» або «хочу поговорити»)_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([back_row("book_start", "← Скасувати")])
        )
        return

    # ── Крок запису: запит ────────────────────────────────────────────────────
    if user.get("booking_step") == "request":
        user["booking"]["request"] = text
        user["booking_step"] = "service"
        save_data(db)

        booking = user["booking"]
        await update.message.reply_text(
            f"✅ *Майже готово!*\n\n"
            f"📋 Перевірте дані:\n"
            f"• Ім'я: *{booking.get('name')}*\n"
            f"• Контакт: *{booking.get('contact')}*\n"
            f"• Формат: *{booking.get('format')}*\n"
            f"• Запит: _{booking.get('request')}_\n\n"
            "Тепер оберіть формат консультації:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Індивідуальна — 70$", callback_data="book_service_confirm")],
                [InlineKeyboardButton("🌱 Коучинг-програма — 240$", callback_data="book_service_confirm")],
                [InlineKeyboardButton("🆘 Екстрена підтримка — 40$", callback_data="book_service_confirm")],
                back_row("book_start", "← Почати заново"),
            ])
        )
        return

    # ── Вільне питання ────────────────────────────────────────────────────────
    if user.get("booking_step") == "free_question":
        user["booking_step"] = None
        save_data(db)

        await update.message.reply_text(
            "✅ *Питання надіслано!*\n\n"
            "Олена відповість найближчим часом 💚",
            parse_mode="Markdown",
            reply_markup=back_to_menu()
        )
        await notify_psychologist(
            context.bot,
            {"type": "question", "text": text, "from": update.effective_user.username or str(update.effective_user.id)}
        )
        return

    # ── Нічого не підходить ───────────────────────────────────────────────────
    await update.message.reply_text(
        "Не зрозумів вас 🙂\n\nСкористайтесь меню 👇",
        reply_markup=main_menu_keyboard()
    )


# ══════════════════════════════════════════════════════════════════════════════
#  СПОВІЩЕННЯ ПСИХОЛОГУ
# ══════════════════════════════════════════════════════════════════════════════

async def notify_psychologist(bot, booking: dict):
    if not PSYCHOLOGIST_CHAT_ID:
        logger.info(f"Нова заявка (психолог не налаштований): {booking}")
        return
    try:
        if booking.get("type") == "question":
            text = (
                f"❓ *Нове питання*\n\n"
                f"Від: @{booking.get('from', '?')}\n\n"
                f"_{booking.get('text')}_"
            )
        else:
            text = (
                f"📅 *Нова заявка на консультацію*\n\n"
                f"👤 Ім'я: {booking.get('name', '—')}\n"
                f"📞 Контакт: {booking.get('contact', '—')}\n"
                f"🌐 Формат: {booking.get('format', '—')}\n"
                f"💬 Запит: {booking.get('request', 'не вказано')}\n"
                f"🕐 Час: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
        await bot.send_message(PSYCHOLOGIST_CHAT_ID, text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Помилка надсилання психологу: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  DAILY CHECK-IN
# ══════════════════════════════════════════════════════════════════════════════

async def send_daily_checkin(bot):
    db = load_data()
    for uid, user in db.items():
        if not user.get("checkin_enabled", False):
            continue
        try:
            await bot.send_message(
                chat_id=int(uid),
                text=(
                    "☀️ *Доброго ранку!*\n\n"
                    "Як ви сьогодні почуваєтесь?"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🙂 Добре", callback_data="checkin_good"),
                        InlineKeyboardButton("😐 Нормально", callback_data="checkin_ok"),
                        InlineKeyboardButton("😔 Важко", callback_data="checkin_hard"),
                    ]
                ])
            )
        except Exception as e:
            logger.warning(f"Check-in не надіслано {uid}: {e}")


# ── Команда увімкнення check-in ──────────────────────────────────────────────
async def cmd_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_data()
    user = get_user(db, update.effective_user.id)
    user["checkin_enabled"] = not user.get("checkin_enabled", False)
    save_data(db)

    status = "увімкнено ✅" if user["checkin_enabled"] else "вимкнено ❌"
    await update.message.reply_text(
        f"Щоденний check-in {status}\n\n"
        f"{'Буду питати як ти вранці о 9:00 🌅' if user['checkin_enabled'] else 'Більше не турбуватиму вранці'}",
        reply_markup=back_to_menu()
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════════════════════════════════════

scheduler = AsyncIOScheduler(jobstores={"default": MemoryJobStore()})


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("checkin", cmd_checkin))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Daily check-in щодня о 9:00
    scheduler.add_job(
        send_daily_checkin,
        trigger="cron",
        hour=9,
        minute=0,
        args=[app.bot],
        id="daily_checkin"
    )
    scheduler.start()

    logger.info("Бот психолога запущено!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
