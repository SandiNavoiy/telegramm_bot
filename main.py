import logging
import sys
import os
import telebot
from telebot import types

from config import Config
from database import db
from rates_service import rates_service
from scheduler import bot_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TelegramBot")

# Проверка конфигурации и инициализация бота Telegram
Config.validate()
bot = telebot.TeleBot(Config.BOT_TOKEN)

def get_main_keyboard():
    """Создание интерактивной клавиатуры Telegram со всеми валютами и криптовалютами."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    # Фиатные валюты
    btn_usd = types.KeyboardButton("💵 USD")
    btn_eur = types.KeyboardButton("💶 EUR")
    btn_byn = types.KeyboardButton("🇧🇾 BYN")
    btn_cad = types.KeyboardButton("🇨🇦 CAD")
    btn_gbp = types.KeyboardButton("💷 GBP")
    
    # Криптовалюты
    btn_btc = types.KeyboardButton("🟧 BTC")
    btn_eth = types.KeyboardButton("🔷 ETH")
    btn_sol = types.KeyboardButton("🟣 SOL")
    btn_kas = types.KeyboardButton("⚡ KAS")
    btn_xmr = types.KeyboardButton("🔒 XMR")
    
    # Системные кнопки
    btn_all = types.KeyboardButton("📊 Все курсы")
    btn_status = types.KeyboardButton("ℹ️ Статус")
    
    markup.add(btn_usd, btn_eur, btn_byn)
    markup.add(btn_cad, btn_gbp)
    markup.add(btn_btc, btn_eth, btn_sol)
    markup.add(btn_kas, btn_xmr)
    markup.add(btn_all, btn_status)
    return markup

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    """Обработчик команд /start и /help."""
    db.add_subscriber(message.chat.id, message.from_user.username)
    
    welcome_text = (
        f"👋 <b>Привет, {message.from_user.first_name or 'пользователь'}!</b>\n\n"
        f"Я бот отслеживания курсов валют и криптовалют.\n\n"
        f"<b>Поддерживаемые активы:</b>\n"
        f"• <b>Фиат (к RUB)</b>: USD, EUR, BYN, CAD, GBP.\n"
        f"• <b>Крипта (к USD)</b>: BTC, ETH, SOL, KAS, XMR.\n\n"
        f"<b>Что я умею:</b>\n"
        f"• Ежедневно в <b>09:00 по Москве</b> автоматически отправлять утренний сводный курс.\n"
        f"• Запоминать утренний курс и каждый час проверять отклонения.\n"
        f"• При отклонении курса более чем на <b>10%</b> — мгновенно отправлять предупреждение.\n\n"
        f"Вы автоматически подписаны на рассылку отчетов и уведомлений (ID: <code>{message.chat.id}</code>)."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=get_main_keyboard())

@bot.message_handler(commands=["subscribe"])
def subscribe_cmd(message):
    """Команда подписки на утренние отчеты и уведомления."""
    db.add_subscriber(message.chat.id, message.from_user.username)
    bot.send_message(message.chat.id, "✅ Вы успешно подписались на утренние отчеты в 09:00 МСК и алеты при изменении курса >10%.", reply_markup=get_main_keyboard())

@bot.message_handler(commands=["unsubscribe"])
def unsubscribe_cmd(message):
    """Команда отписки от утренних отчетов и уведомлений."""
    db.remove_subscriber(message.chat.id)
    bot.send_message(message.chat.id, "❌ Вы отписались от рассылок и уведомлений. Вы можете продолжать запрашивать курсы вручную.", reply_markup=get_main_keyboard())

@bot.message_handler(commands=["test_report"])
def test_report_cmd(message):
    """Тестовая отправка 09:00 МСК отчета для проверки доставки сообщений."""
    bot.send_message(message.chat.id, "⏳ Генерируем тестовый 09:00 МСК отчет...")
    db.add_subscriber(message.chat.id, message.from_user.username)
    bot_scheduler.run_daily_baseline()

@bot.message_handler(commands=["rates"])
def send_all_rates(message):
    """Команда получения сводки по всем валютам."""
    bot.send_chat_action(message.chat.id, "typing")
    rates = rates_service.get_all_rates()
    if not rates:
        bot.send_message(message.chat.id, "❌ Не удалось получить актуальные курсы валют. Попробуйте позже.")
        return

    text = bot_scheduler.format_rates_message(rates, "📊 Актуальные курсы валют и криптовалют")
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=get_main_keyboard())

@bot.message_handler(commands=["status"])
def send_status(message):
    """Команда получения статуса подписки и текущих утренних курсов."""
    subscribers = db.get_subscribers()
    is_subbed = message.chat.id in subscribers
    sub_status = "✅ Подписан" if is_subbed else "❌ Не подписан (/subscribe)"
    
    date_str, baseline = db.get_latest_baseline_rates()
    
    status_text = (
        f"ℹ️ <b>Статус бота</b>\n\n"
        f"• Ваша подписка: {sub_status}\n"
        f"• Идентификатор чата: <code>{message.chat.id}</code>\n"
        f"• Всего подписчиков: <b>{len(subscribers)}</b>\n"
    )
    
    if date_str and baseline:
        status_text += f"\n📌 <b>Утренние базовые курсы ({date_str}):</b>\n"
        for code, r in baseline.items():
            is_crypto = rates_service.is_crypto(code)
            unit = "USD" if is_crypto else "RUB"
            prefix = "$" if is_crypto else ""
            fmt = f"{prefix}{r:,.4f}" if code == "KAS" else f"{prefix}{r:,.2f}"
            status_text += f"• {code}: <code>{fmt}</code> {unit}\n"
    else:
        status_text += "\n📌 Утренние базовые курсы пока не зафиксированы."

    bot.send_message(message.chat.id, status_text, parse_mode="HTML", reply_markup=get_main_keyboard())

@bot.message_handler(content_types=["text"])
def handle_text(message):
    """Обработчик текстовых сообщений от пользователя (выбор кнопок или ввод названия валюты)."""
    txt = message.text.strip().lower()
    
    # Все курсы
    if "все курсы" in txt or txt == "все" or txt == "rates":
        send_all_rates(message)
        return

    # Статус
    if "статус" in txt or txt == "status":
        send_status(message)
        return

    # Словарь алиасов валют на русском и английском
    currency_map = {
        "usd": ["usd", "💵 usd", "доллар", "доллара", "бакс"],
        "eur": ["eur", "💶 eur", "евро"],
        "byn": ["byn", "🇧🇾 byn", "белорусский рубль", "белорусский", "рубль рб"],
        "cad": ["cad", "🇨🇦 cad", "канадский доллар", "канадский"],
        "gbp": ["gbp", "💷 gbp", "фунт", "фунта", "стерлинг"],
        "btc": ["btc", "🟧 btc", "bitcoin", "биткоин", "биток"],
        "eth": ["eth", "🔷 eth", "ethereum", "эфириум", "эфир"],
        "sol": ["sol", "🟣 sol", "solana", "солана", "соль"],
        "kas": ["kas", "⚡ kas", "kaspa", "каспа"],
        "xmr": ["xmr", "🔒 xmr", "monero", "монеро"]
    }

    selected_symbol = None
    for symbol, aliases in currency_map.items():
        if any(alias == txt or alias in txt.split() for alias in aliases):
            selected_symbol = symbol.upper()
            break

    if not selected_symbol:
        bot.send_message(
            message.chat.id,
            'Некорректный ввод. Выберите валюту из меню ниже.',
            reply_markup=get_main_keyboard()
        )
        return

    bot.send_chat_action(message.chat.id, "typing")
    rate = rates_service.get_rate(selected_symbol)
    
    if rate is None:
        bot.send_message(message.chat.id, f"❌ Не удалось получить курс для {selected_symbol}.")
        return

    name = rates_service.supported_currencies.get(selected_symbol, selected_symbol)
    is_crypto = rates_service.is_crypto(selected_symbol)
    unit = "USD" if is_crypto else "RUB"
    target_name = "доллару США ($)" if is_crypto else "рублю"
    prefix = "$" if is_crypto else ""
    
    fmt_rate = f"{prefix}{rate:,.4f}" if selected_symbol == "KAS" else f"{prefix}{rate:,.2f}"
    response_msg = f"Курс <b>{selected_symbol}</b> ({name}) к {target_name}: <code>{fmt_rate}</code> {unit}"
    
    # Сравнение с утренним базовым курсом при его наличии
    date_str, baseline = db.get_latest_baseline_rates()
    base_rate = baseline.get(selected_symbol) if baseline else None
    if base_rate and base_rate > 0:
        diff_pct = ((rate - base_rate) / base_rate) * 100.0
        fmt_base = f"{prefix}{base_rate:,.4f}" if selected_symbol == "KAS" else f"{prefix}{base_rate:,.2f}"
        response_msg += f"\n<i>(Утренний курс: {fmt_base} {unit}, изменение: {diff_pct:+.2f}%)</i>"

    bot.send_message(message.chat.id, response_msg, parse_mode="HTML", reply_markup=get_main_keyboard())

if __name__ == "__main__":
    logger.info("Запуск Telegram-бота курсов валют (к RUB) и криптовалют (к USD)...")
    
    # Передаем экземпляр бота в планировщик и запускаем его
    bot_scheduler.set_bot(bot)
    bot_scheduler.start()
    
    # Первоначальная проверка при запуске
    try:
        bot_scheduler.run_hourly_check()
    except Exception as e:
        logger.error(f"Первоначальная проверка при запуске завершилась с ошибкой: {e}")

    logger.info("Бот успешно запущен и готов к работе...")
    
    # Бесконечный цикл обработки сообщений
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
