import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

class Config:
    # Токен бота Telegram (поддерживает ключи TOKEN или BOT_TOKEN)
    BOT_TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN", "")
    
    # Необязательный API ключ для сервиса APILayer
    API_KEY = os.getenv("API_KEY", "")
    
    # Необязательный Telegram ID администратора
    _admin_id = os.getenv("ADMIN_CHAT_ID", "")
    ADMIN_CHAT_ID = int(_admin_id) if _admin_id.isdigit() else None
    
    # Путь к файлу базы данных SQLite
    DB_PATH = os.getenv("DB_PATH", "bot_data.db")
    
    # Часовой пояс работы бота (по умолчанию Москва)
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
    
    # Пороговый процент отклонения курса для отправки алертов (по умолчанию 10%)
    DEVIATION_THRESHOLD_PERCENT = float(os.getenv("DEVIATION_THRESHOLD_PERCENT", "10.0"))

    @classmethod
    def validate(cls):
        """Проверка наличия обязательных настроек."""
        if not cls.BOT_TOKEN or cls.BOT_TOKEN == "your_telegram_bot_token_here":
            raise ValueError("Ошибка: Не указан BOT_TOKEN в файле .env или переменных окружения!")
