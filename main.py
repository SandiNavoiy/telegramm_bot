import time
import requests
import telebot

#API KEY сервиса
API_KEY = 'nhWcDR9FQnh1fkniA6dKLhCsBC41ZHoh'
#API KEY стелеграм бота и обьявляем сам бот
bot = telebot.TeleBot('6033109078:AAEm9HFaZT8UhMCQcdcE5BI5Kt56NNCkwR0')

#Стартовое сообщение

@bot.message_handler(commands=["start"])
def start(m, res=False):
    bot.send_message(m.chat.id, 'Я на связи. Веди название валюты - USD или EUR )')


# Получение сообщений от юзера
@bot.message_handler(content_types=["text"])
def handle_text(message):
    if message.text not in ["USD", "EUR"]:
        bot.send_message(message.chat.id, 'Некорректный ввод: напишите "USD", "EUR"')


    elif message.text == "USD":
        url = f"https://api.apilayer.com/exchangerates_data/latest?base={message.text}"
        response = requests.get(url, headers={'apikey': API_KEY})
        #Загоняем из json, иначе не понимает
        data = response.json()
        # Вынимаем данные
        rate = data["rates"]["RUB"]
        bot.send_message(message.chat.id, f'Курс USD к рублю: {rate}')
        #Задержка от особо умных
        time.sleep(30)
    elif message.text == "EUR":
        url = f"https://api.apilayer.com/exchangerates_data/latest?base={message.text}"
        response = requests.get(url, headers={'apikey': API_KEY})
        data = response.json()
        rate = data["rates"]["RUB"]
        bot.send_message(message.chat.id, f'Курс EUR к рублю: {rate}')
        time.sleep(30)


# Запускаем бота
bot.polling(none_stop=True, interval=0)
