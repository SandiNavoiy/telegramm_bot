import json

import requests
import telebot




@bot.message_handler(commands=["start"])
def start(m, res=False):
    bot.send_message(m.chat.id, 'Я на связи. Веди название валюты - USD или EUR )')
# Получение сообщений от юзера
@bot.message_handler(content_types=["text"])


def handle_text(message):
    bot.send_message(message.chat.id, 'Вы написали: ' + message.text)
# Запускаем бота
bot.polling(none_stop=True, interval=0)