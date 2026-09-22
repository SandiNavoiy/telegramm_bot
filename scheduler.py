import logging
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import Config
from database import db
from rates_service import rates_service

logger = logging.getLogger(__name__)

class BotScheduler:
    """Планировщик фоновых задач (утренние отчеты в 09:00 МСК и часовые проверки отклонений)."""
    
    def __init__(self, bot=None):
        self.bot = bot
        self.timezone = pytz.timezone(Config.TIMEZONE)
        self.scheduler = BackgroundScheduler(timezone=self.timezone)

    def set_bot(self, bot):
        """Передача экземпляра Telegram-бота в планировщик."""
        self.bot = bot

    def format_rates_message(self, rates: dict[str, float], title: str) -> str:
        """Форматирование списка курсов валют в HTML-сообщение Telegram."""
        msg = f"<b>{title}</b>\n\n"
        for code, rate in rates.items():
            name = rates_service.supported_currencies.get(code, code)
            msg += f"• <b>{code}</b> ({name}): <code>{rate:,.4f}</code> RUB\n"
        return msg

    def send_broadcast(self, text: str):
        """Отправка сообщения всем зарегистрированным подписчикам."""
        if not self.bot:
            logger.warning("Экземпляр бота не установлен для рассылки!")
            return
            
        subscribers = db.get_subscribers()
        if not subscribers:
            logger.info("Подписчики для рассылки не найдены.")
            return

        for chat_id in subscribers:
            try:
                self.bot.send_message(chat_id, text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Не удалось отправить рассылку пользователю {chat_id}: {e}")

    def run_daily_baseline(self):
        """Ежедневная задача в 09:00 МСК: сохранение базовых утренних курсов и рассылка отчета."""
        now = datetime.now(self.timezone)
        date_str = now.strftime("%Y-%m-%d")
        logger.info(f"Запуск утренней фиксации курсов за {date_str} в 09:00 МСК...")

        rates = rates_service.get_all_rates()
        if not rates:
            logger.error("Не удалось получить курсы для утренней фиксации.")
            return

        # Сохраняем базовые курсы в БД
        db.save_baseline_rates(date_str, rates)

        # Формируем и отправляем утренний отчет
        title = f"🌅 Утренний курс валют на {now.strftime('%d.%m.%Y')} (09:00 МСК)"
        msg = self.format_rates_message(rates, title)
        msg += "\n<i>Курсы зафиксированы как базовые для отслеживания отклонений.</i>"

        self.send_broadcast(msg)

    def run_hourly_check(self):
        """Ежечасовая задача: проверка отклонений текущих курсов от утренних базовых (порог > 10%)."""
        now = datetime.now(self.timezone)
        date_str = now.strftime("%Y-%m-%d")
        logger.info(f"Запуск часовой проверки отклонений курсов за {date_str}...")

        # Получаем утренние базовые курсы за сегодня
        baseline_rates = db.get_baseline_rates(date_str)

        # Если бот запустился после 09:00 МСК и база за сегодня пуста, фиксируем текущие курсы
        if not baseline_rates:
            logger.info("Утренние базовые курсы за сегодня отсутствуют. Фиксируем текущие курсы...")
            current_rates = rates_service.get_all_rates()
            if current_rates:
                db.save_baseline_rates(date_str, current_rates)
                baseline_rates = current_rates

        if not baseline_rates:
            logger.warning("Нет базовых курсов для сравнения.")
            return

        # Запрашиваем текущие курсы
        current_rates = rates_service.get_all_rates()
        if not current_rates:
            logger.error("Не удалось получить текущие курсы для часовой проверки.")
            return

        # Сравниваем каждую валюту
        for code, current_rate in current_rates.items():
            base_rate = baseline_rates.get(code)
            if not base_rate or base_rate <= 0:
                continue

            # Расчет процента изменения
            diff_pct = ((current_rate - base_rate) / base_rate) * 100.0

            # Если отклонение больше или равно заданному порогу (10%)
            if abs(diff_pct) >= Config.DEVIATION_THRESHOLD_PERCENT:
                # Проверяем, не отправлялось ли уже уведомление по этой валюте сегодня
                if not db.has_alerted_today(date_str, code):
                    db.record_alert(date_str, code, current_rate, base_rate, diff_pct)
                    direction = "📈 Рост" if diff_pct > 0 else "📉 Падение"
                    name = rates_service.supported_currencies.get(code, code)
                    
                    alert_msg = (
                        f"🚨 <b>ВНИМАНИЕ! Сильное отклонение курса!</b>\n\n"
                        f"Валюта: <b>{code}</b> ({name})\n"
                        f"Утренний курс (09:00): <code>{base_rate:,.4f}</code> RUB\n"
                        f"Текущий курс: <code>{current_rate:,.4f}</code> RUB\n"
                        f"Отклонение: <b>{diff_pct:+.2f}%</b> ({direction})\n\n"
                        f"<i>Порог срабатывания: {Config.DEVIATION_THRESHOLD_PERCENT}%</i>"
                    )
                    logger.warning(f"Сработал алерт отклонения по {code}: {diff_pct:.2f}%")
                    self.send_broadcast(alert_msg)

    def start(self):
        """Запуск фонового планировщика задач."""
        # 1. Задача в 09:00 МСК каждый день
        self.scheduler.add_job(
            self.run_daily_baseline,
            CronTrigger(hour=9, minute=0, timezone=self.timezone),
            id="daily_baseline",
            replace_existing=True
        )

        # 2. Задача каждый час в 00 минут
        self.scheduler.add_job(
            self.run_hourly_check,
            CronTrigger(minute=0, timezone=self.timezone),
            id="hourly_check",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Планировщик задач успешно запущен (часовой пояс: МСК).")

# Глобальный экземпляр планировщика
bot_scheduler = BotScheduler()
