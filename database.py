import sqlite3
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных SQLite для хранения подписчиков, утренних курсов и логов алертов."""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DB_PATH
        self._init_db()

    def _get_connection(self):
        """Создание соединения с базой данных SQLite."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Инициализация таблиц базы данных."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица активных подписчиков (chat_id Telegram)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица утренних базовых курсов валют (зафиксированных в 09:00 МСК)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS baseline_rates (
                    date TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    rate REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (date, currency)
                )
            """)
            
            # Таблица истории отправленных алертов (чтобы не спамить повторными уведомлениями в один день)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    alerted_rate REAL NOT NULL,
                    baseline_rate REAL NOT NULL,
                    deviation_percent REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("База данных успешно инициализирована.")

    # --- Управление подписчиками ---

    def add_subscriber(self, chat_id: int, username: str = None):
        """Добавить пользователя в список подписчиков на рассылку."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO subscribers (chat_id, username)
                VALUES (?, ?)
            """, (chat_id, username))
            conn.commit()
            logger.info(f"Добавлен подписчик chat_id: {chat_id}")

    def remove_subscriber(self, chat_id: int):
        """Удалить пользователя из списка подписчиков."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
            conn.commit()
            logger.info(f"Удален подписчик chat_id: {chat_id}")

    def get_subscribers(self) -> list[int]:
        """Получить список всех ID чатов подписчиков."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT chat_id FROM subscribers")
            rows = cursor.fetchall()
            subscribers = [row['chat_id'] for row in rows]
            
            # Если в конфигурации указан ADMIN_CHAT_ID, добавляем его в список при отсутствии
            if Config.ADMIN_CHAT_ID and Config.ADMIN_CHAT_ID not in subscribers:
                subscribers.append(Config.ADMIN_CHAT_ID)
                
            return subscribers

    # --- Управление утренними базовыми курсами ---

    def save_baseline_rates(self, date_str: str, rates: dict[str, float]):
        """Сохранить утренние базовые курсы (зафиксированные в 09:00 МСК) для даты YYYY-MM-DD."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for currency, rate in rates.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO baseline_rates (date, currency, rate, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (date_str, currency.upper(), rate))
            conn.commit()
            logger.info(f"Базовые курсы сохранены на дату {date_str}: {rates}")

    def get_baseline_rates(self, date_str: str) -> dict[str, float]:
        """Получить утренние базовые курсы для указанной даты (YYYY-MM-DD)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT currency, rate FROM baseline_rates WHERE date = ?", (date_str,))
            rows = cursor.fetchall()
            return {row['currency']: row['rate'] for row in rows}

    def get_latest_baseline_rates(self) -> tuple[str, dict[str, float]]:
        """Получить базовые курсы за последнюю имеющуюся дату."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT date FROM baseline_rates ORDER BY date DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None, {}
            date_str = row['date']
            rates = self.get_baseline_rates(date_str)
            return date_str, rates

    # --- Управление алертами ---

    def record_alert(self, date_str: str, currency: str, current_rate: float, baseline_rate: float, deviation_percent: float):
        """Записать факт отправки алерта об отклонении курса."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alerts_log (date, currency, alerted_rate, baseline_rate, deviation_percent)
                VALUES (?, ?, ?, ?, ?)
            """, (date_str, currency.upper(), current_rate, baseline_rate, deviation_percent))
            conn.commit()

    def has_alerted_today(self, date_str: str, currency: str) -> bool:
        """Проверить, отправлялось ли уже сегодня уведомление об отклонении для данной валюты."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM alerts_log
                WHERE date = ? AND currency = ?
            """, (date_str, currency.upper()))
            row = cursor.fetchone()
            return row['count'] > 0

# Глобальный экземпляр менеджера базы данных
db = DatabaseManager()
