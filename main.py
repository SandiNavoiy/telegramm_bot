import telebot
import config


bot = telebot.TeleBot('6033109078:AAEm9HFaZT8UrMCQcdcE5BI5Kt56NNCkwRO')

@bot.message_handler(content_types=["text"])
def repeat_all_messages(message):
    bot.send_message(message.chat.id, message.text)

if __name__ == '__main__':
    bot.infinity_polling(True)