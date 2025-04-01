import os
import time
import requests
import telebot
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
#API KEY сервиса
API_KEY = os.getenv("API_KEY")
#API KEY стелеграм бота и обьявляем сам бот
bot = telebot.TeleBot(TOKEN)

#Стартовое сообщение

@bot.message_handler(commands=["start"])
def start(m, res=False):
    bot.send_message(m.chat.id, 'Я на связи. Введи название валюты - Usd, Eur, Cad, Gbp )')


# Получение сообщений от юзера
@bot.message_handler(content_types=["text"])
def handle_text(message):
    if message.text.title() not in ["Usd", "Eur", "Cad", "Gbp"]:
        bot.send_message(message.chat.id, 'Некорректный ввод: напишите "Usd", "Eur","Cad", "Gbp"')


    elif message.text.title() == "Usd":
        url = f"https://api.apilayer.com/exchangerates_data/latest?base={message.text.title()}"
        response = requests.get(url, headers={'apikey': API_KEY})
        #Загоняем из json, иначе не понимает
        data = response.json()
        # Вынимаем данные
        rate = data["rates"]["RUB"]
        bot.send_message(message.chat.id, f'Курс USD к рублю: {rate}')
        #Задержка от особо умных
        time.sleep(30)
    elif message.text.title() == "Eur":
        url = f"https://api.apilayer.com/exchangerates_data/latest?base={message.text}"
        response = requests.get(url, headers={'apikey': API_KEY})
        data = response.json()
        rate = data["rates"]["RUB"]
        bot.send_message(message.chat.id, f'Курс EUR к рублю: {rate}')
        time.sleep(30)
    elif message.text.title() == "Cad":
        url = f"https://api.apilayer.com/exchangerates_data/latest?base={message.text}"
        response = requests.get(url, headers={'apikey': API_KEY})
        data = response.json()
        rate = data["rates"]["RUB"]
        bot.send_message(message.chat.id, f'Курс CAD к рублю: {rate}')
        time.sleep(30)

    elif message.text.title() == "Gbp":
        url = f"https://api.apilayer.com/exchangerates_data/latest?base={message.text}"
        response = requests.get(url, headers={'apikey': API_KEY})
        data = response.json()
        rate = data["rates"]["RUB"]
        bot.send_message(message.chat.id, f'Курс GBP к рублю: {rate}')
        time.sleep(30)


# Запускаем бота
bot.polling(none_stop=True, interval=0)
