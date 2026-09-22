import os
import sys
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Loyiha muhiti va analyzer modulini yuklash
sys.path.append(os.path.dirname(__file__))
from analyzer import analyze_food_image

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi!")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

def get_author_markup():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("💬 Qo'llab-quvvatlash (@uzb106)", url="https://t.me/uzb106")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name or "Do'stim"
    welcome_text = (
        f"Assalomu alaykum, <b>{user_name}</b>! 👋\n\n"
        "Men <b>EDA.AI</b> — taom kaloriyasini va tarkibini aniqlovchi aqlli yordamchingizman. 🥗\n\n"
        "📸 <b>Menga istalgan taom suratini yuboring</b>, men:\n"
        "• Taom nomi va taxminiy vaznini aniqlayman\n"
        "• Umumiy kaloriyasini (kkal) hisoblayman\n"
        "• Oqsil, yog' va uglevodlar (BJU) balansini chiqaraman\n"
        "• Masalliqlar va foydali tavsiyalar beraman!\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👨‍💻 <b>Muallif:</b> Qobilov Abubakr\n"
        "💬 <b>Qo'llab-quvvatlash:</b> @uzb106\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "<i>Suratni kameradan olib yoki galereyadan yuborishingiz mumkin.</i>"
    )
    bot.reply_to(message, welcome_text, reply_markup=get_author_markup())

@bot.message_handler(commands=['about'])
def send_about(message):
    about_text = (
        "🤖 <b>EDA.AI Taom Tahlilchi Boti</b>\n\n"
        "Sun'iy intellekt (Gemini Vision) asosida ishlaydigan taomlar va sog'lom ovqatlanish tahlilchisi.\n\n"
        "👨‍💻 <b>Loyiha muallifi:</b> Qobilov Abubakr\n"
        "💬 <b>Qo'llab-quvvatlash va aloqa:</b> @uzb106"
    )
    bot.reply_to(message, about_text, reply_markup=get_author_markup())

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "<b>Qanday ishlatiladi?</b>\n\n"
        "1. Tushlik, kechki ovqat yoki gazaklaringiz suratini botga yuboring. 📸\n"
        "2. O'rnatilgan sun'iy intellekt taomni avtomatik tahlil qiladi. 🥗\n"
        "3. Bir necha soniyada uning kaloriyasi va masalliqlari haqida to'liq hisobot olasiz! ⚡"
    )
    bot.reply_to(message, help_text)

@bot.message_handler(content_types=['photo'])
def handle_food_photo(message):
    chat_id = message.chat.id
    status_msg = bot.reply_to(message, "🔍 <i>Taomingiz tahlil qilinmoqda, iltimos kuting...</i>")

    try:
        # Eng sifatli rasm variantini olish
        photo_info = message.photo[-1]
        file_info = bot.get_file(photo_info.file_id)
        image_bytes = bot.download_file(file_info.file_path)

        # O'rnatilgan sun'iy intellekt orqali tahlil
        res = analyze_food_image(
            image_bytes=image_bytes,
            mime_type="image/jpeg"
        )

        # Masalliqlar ro'yxatini shakllantirish
        ing_text = ""
        for ing in res.ingredients:
            ing_text += f"  • {ing.name} (~{int(ing.amount_g)}g)\n"

        # Chiroyli formatlangan natija
        result_caption = (
            f"🍽 <b>{res.food_name}</b>\n"
            f"📍 <i>{res.cuisine_type}</i>\n"
            f"⚖️ <b>Porsiya:</b> ~{int(res.total_weight_g)} g  |  🎯 <b>Ishonch:</b> {res.confidence}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔥 <b>Umumiy kaloriya:</b> {int(res.calories)} kkal\n"
            f"🥩 <b>Oqsil (Protein):</b> {res.protein} g\n"
            f"🥑 <b>Yog' (Fats):</b> {res.fats} g\n"
            f"🍞 <b>Uglevod (Carbs):</b> {res.carbs} g\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🥕 <b>Aniqlangan masalliqlar:</b>\n{ing_text}\n"
            f"💡 <b>Xulosa va tavsiya:</b>\n{res.dietary_advice}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👨‍💻 <b>Muallif:</b> Qobilov Abubakr  |  💬 @uzb106\n"
        )

        bot.delete_message(chat_id, status_msg.message_id)
        bot.reply_to(message, result_caption, reply_markup=get_author_markup())

    except Exception as e:
        print(f"Tahlil xatosi: {e}")
        bot.edit_message_text(
            "❌ <i>Kechirasiz, taomni tahlil qilishda xatolik yuz berdi. "
            "Iltimos, taomni yorug'roq joyda va yaqinroqdan suratga olib qayta yuboring.</i>",
            chat_id,
            status_msg.message_id
        )

@bot.message_handler(content_types=['text'])
def handle_other_messages(message):
    bot.reply_to(
        message,
        "Iltimos, menga <b>taom suratini</b> yuboring! 📸\n"
        "Men uning kaloriyasini va barcha ozuqaviy qiymatini hisoblab beraman."
    )

import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"EDA.AI Bot 24/7 is Active!")
        
    def log_message(self, format, *args):
        return

def start_health_server():
    try:
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        server.serve_forever()
    except Exception as e:
        print("Health server xatoligi:", e)

if __name__ == "__main__":
    # Bulutli serverlarda (Render, Railway va h.k.) 24/7 ishlashi uchun fon veb-serveri
    threading.Thread(target=start_health_server, daemon=True).start()
    print("[EDA.AI] Telegram boti muvaffaqiyatli ishga tushirildi...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print("Telegram ulanish xatosi, 5 soniyadan keyin qayta ulanadi:", e)
            time.sleep(5)
