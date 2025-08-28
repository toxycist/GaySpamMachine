import telebot
import dotenv
from os import getenv, path
import requests
from bs4 import BeautifulSoup
import random
import schedule
import time
import threading
import json

dotenv.load_dotenv()
TOKEN = getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)

DB_FILE = path.join(path.dirname(path.abspath(__file__)), "user_states.json")
data = {}
with open(DB_FILE, "r") as file:
    data = json.load(file)

@bot.message_handler(commands = ['start'])
def start(message):
    bot.send_message(message.chat.id, """Привет, Тонечка ! 🫰💜\n----------\nЭтот бот был создан специально для тебя, чтобы ты с наибольшими удобствами занималась своим любимым делом - читала гейские манхвы)\n----------\nКоманды:\n/start - Запустить бота\n/nov - Посмотреть новинки этого прекрасного жанра\n/pop - Посмотреть самые популярные манхвы\n/top - Посмотреть манхвы с самым высоким рейтингом\n/rand - Посмотреть случайный тайтл\n/sub - Подписаться на ежедневную рассылку случайной гей манхвы\n/unsub - Отписаться от ежедневной рассылки случайной гей манхвы\n----------\nПриятного пользования ! 🫶""")

def get_first_five_manhwas(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    manhwas = soup.find_all("div", class_="item-grid")
    manhwa_data = []

    for manhwa in manhwas[:5]:
        rating = manhwa.find("div", class_="label-rating")
        rating = rating.text if rating else None

        img = manhwa.find("img", class_="item-grid-image")
        img_url = img["src"] if img else None

        title_tag = manhwa.find("a", class_="fw-medium")
        title = title_tag.text.strip() if title_tag else None
        link = title_tag["href"] if title_tag else None

        year_type = manhwa.find("div", class_="text-muted")
        year = year_type.text.split(",")[0] if year_type else None

        manhwa_data.append({
            "title": title,
            "link": link,
            "rating": rating,
            "image": img_url,
            "year": year
        })
    
    return manhwa_data

def get_random_manhwa(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    manhwas = soup.find_all("div", class_="item-grid")
    manhwa_data = []

    manhwa = random.choice(manhwas)

    rating = manhwa.find("div", class_="label-rating")
    rating = rating.text if rating else None

    img = manhwa.find("img", class_="item-grid-image")
    img_url = img["src"] if img else None

    title_tag = manhwa.find("a", class_="fw-medium")
    title = title_tag.text.strip() if title_tag else None
    link = title_tag["href"] if title_tag else None

    year_type = manhwa.find("div", class_="text-muted")
    year = year_type.text.split(",")[0] if year_type else None

    manhwa_data.append({
        "title": title,
        "link": link,
        "rating": rating,
        "image": img_url,
        "year": year
    })
    
    return manhwa_data

def send_manhwas(chat_id, manhwa_data):
    for i, manhwa in enumerate(reversed(manhwa_data)):
        bot.send_photo(chat_id, 
                       photo=manhwa["image"],
                       caption= f"""{len(manhwa_data) - i}. {manhwa["title"]}\nРейтинг: {manhwa["rating"]}\nГод выпуска: {manhwa["year"]}\n<a href="https://mangahub.ru{manhwa["link"]}">Читать</a>""",
                       parse_mode="HTML")

@bot.message_handler(commands = ['nov'])
def nov(message):
    manhwa_data = get_first_five_manhwas("https://mangahub.ru/explore/type-is-manhwa/genres-is-shounen_ai/status-is-nor-preview/sort-is-date")
    send_manhwas(message.chat.id, manhwa_data)

@bot.message_handler(commands = ['pop'])
def pop(message):
    manhwa_data = get_first_five_manhwas("https://mangahub.ru/explore/type-is-manhwa/genres-is-shounen_ai/status-is-nor-preview/sort-is-views")
    send_manhwas(message.chat.id, manhwa_data)

@bot.message_handler(commands = ['top'])
def top(message):
    manhwa_data = get_first_five_manhwas("https://mangahub.ru/explore/type-is-manhwa/genres-is-shounen_ai/status-is-nor-preview/sort-is-rating")
    send_manhwas(message.chat.id, manhwa_data)

@bot.message_handler(commands = ['rand'])
def rand(message):
    url = "https://mangahub.ru/explore/type-is-manhwa/genres-is-shounen_ai/status-is-nor-preview/sort-is-date"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    last_page_num = int([a for a in soup.select("li.page-item a") if a.get("rel") != ["next"]][-1].text)

    manhwa_data = get_random_manhwa(url + f"?page={random.randint(1, last_page_num)}")
    send_manhwas(message.chat.id, manhwa_data)

def send_daily_manhwa(message):
    bot.send_message(message.chat.id, "Привеет, твоя ежедневная манхва)")
    rand(message)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(10)

def is_subscribed(user_id):
    return data.get(str(user_id), {}).get("subscribed", False)

def update_user(user_id, **kwargs):
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {}
    data[user_id].update(kwargs)
    with open(DB_FILE, "w") as file:
        json.dump(data, file, indent=4)

@bot.message_handler(commands = ['sub'])
def sub(message):
    if is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "Ты и так уже подписана на эту рассылку)")
        return
    bot.send_message(message.chat.id, "Ураа! Ты подписалась на ежедневную рассылку случайной гей манхвы в 17:00!")
    update_user(message.from_user.id, subscribed=True)
    schedule.every().day.at("17:00").do(send_daily_manhwa, message)
    threading.Thread(target=run_scheduler, daemon=True).start()

@bot.message_handler(commands = ['unsub'])
def unsub(message):
    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, "Ты и так не подписана на эту рассылку(что, кстати, можно легко исправить 😇)")
        return
    bot.send_message(message.chat.id, "Ну вот( Ты отписалась от ежедневной рассылки случайной гей манхвы..")
    update_user(message.from_user.id, subscribed=False)
    schedule.clear()

print("GaySpamMachine is running...")
bot.infinity_polling()