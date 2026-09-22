# 🤖 Telegram Currency Exchange Bot (Курсы валют и алерты)

Обновленный Telegram бот для отслеживания курсов валют (USD, EUR, CAD, GBP, Kaspa, Monero), отправки ежедневных утренних отчетов в 09:00 по Москве и авто-оповещений при отклонении курса > 10%.

---

## 🌟 Основные возможности
1. **Запрос курсов по требованию**: Поддержка `USD`, `EUR`, `CAD`, `GBP`, `Kaspa (KAS)`, `Monero (XMR)`.
2. **Интерактивные кнопки**: Удобная клавиатура Telegram в меню.
3. **Ежедневный отчет в 09:00 МСК**: Автоматическая рассылка утреннего курса всем подписчикам.
4. **Фиксация утреннего курса**: Базовый курс сохраняется в базу SQLite.
5. **Часовая проверка и алерты (>10%)**: Каждый час проверяется отклонение от утреннего курса. Если курс изменился более чем на 10%, бот мгновенно отправляет предупреждение.
6. **Надежность на VPS**:
   - Автономная работа 24/7 с автоматическим перезапуском при сбоях сети.
   - База данных SQLite (`bot_data.db`) сохраняет подписчиков и утренние курсы при перезагрузке сервера.
   - Подробные логи в файле `bot.log`.

---

## 🛠️ Настройка и Запуск

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка конфигурации `.env`
Отредактируйте файл `.env` в корне проекта:
```ini
TOKEN=ваш_токен_от_BotFather
TIMEZONE=Europe/Moscow
DEVIATION_THRESHOLD_PERCENT=10.0
```

### 3. Локальный запуск
```bash
python main.py
```

---

## 🚀 Развертывание на виртуальном сервере (Linux VPS)

### Вариант 1: Через Systemd (Рекомендуется)
1. Склонируйте проект на сервер в папку `/opt/telegramm_bot`:
   ```bash
   git clone <ваш_репозиторий> /opt/telegramm_bot
   cd /opt/telegramm_bot
   ```
2. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Скопируйте и отредактируйте `.env`:
   ```bash
   cp .env.example .env
   nano .env
   ```
4. Скопируйте файл службы systemd и запустите сервис:
   ```bash
   cp telegram_bot.service /etc/systemd/system/
   systemctl daemon-reload
   systemctl enable telegram_bot
   systemctl start telegram_bot
   ```
5. Проверка статуса и логов:
   ```bash
   systemctl status telegram_bot
   journalctl -u telegram_bot -f
   ```

---

### Вариант 2: Через Docker
```bash
docker build -t telegram-currency-bot .
docker run -d --name currency_bot --env-file .env --restart always telegram-currency-bot
```
