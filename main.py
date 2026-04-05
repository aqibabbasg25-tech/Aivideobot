import os
import telebot
from flask import Flask, request
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables for local testing (Render handles this automatically in production)
load_dotenv()

# --- Configuration ---
# Get tokens from environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN") # Hugging Face API key as per your provided code
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # You might still need this for DALL-E, if HF router doesn't route it

# Render.com provides a PORT environment variable
PORT = int(os.environ.get('PORT', 5000))
WEBHOOK_URL_BASE = os.getenv("WEBHOOK_URL_BASE") # e.g., "https://your-render-app-name.onrender.com"
WEBHOOK_URL_PATH = "/webhook/" + BOT_TOKEN # Unique path for our webhook

# --- Bot and API Clients ---
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize OpenAI client with Hugging Face router base URL
# As per your JS example, we'll try to use HF router for OpenAI calls.
# Note: For DALL-E 3, direct OpenAI client might be more stable.
# If HF router doesn't support DALL-E 3, you might need a separate OpenAI client initialized without base_url for DALL-E.
openai_client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN, # Using HF_TOKEN as api_key for HF router
)

# For DALL-E 3, it's generally recommended to use the standard OpenAI endpoint
# If the above openai_client (via HF router) fails for DALL-E, uncomment and use this:
# dall_e_client = OpenAI(api_key=OPENAI_API_KEY)


app = Flask(__name__)

# --- Bot Message Handlers ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "नमस्ते! मैं एक AI bot हूँ जो आपके prompts के आधार पर तस्वीरें बना सकता हूँ। मुझे बस बताएं कि आप क्या बनाना चाहते हैं!")
    bot.reply_to(message, "उदाहरण: 'एक बिल्ली अंतरिक्ष यात्री के रूप में'")

@bot.message_handler(func=lambda message: True) # Handles all other text messages
def handle_message(message):
    prompt = message.text
    bot.reply_to(message, f'मैं "{prompt}" के लिए आपकी तस्वीर बना रहा हूँ, कृपया प्रतीक्षा करें...')

    try:
        # Try generating image using DALL-E 3
        # If HF router supports DALL-E 3 with the provided setup:
        image_response = openai_client.images.generate(
            model="dall-e-3", # Specify DALL-E 3 model
            prompt=prompt,
            n=1,
            size="1024x1024",
            response_format='url'
        )
        image_url = image_response.data[0].url
        bot.send_photo(message.chat.id, image_url, caption=f'यह रही आपकी तस्वीर: "{prompt}"')

        # If HF router does NOT support DALL-E 3 and you're using a separate dall_e_client:
        # image_response = dall_e_client.images.generate(
        #     model="dall-e-3",
        #     prompt=prompt,
        #     n=1,
        #     size="1024x1024",
        #     response_format='url'
        # )
        # image_url = image_response.data[0].url
        # bot.send_photo(message.chat.id, image_url, caption=f'यह रही आपकी तस्वीर: "{prompt}"')

    except Exception as e:
        print(f"Error generating image: {e}")
        bot.reply_to(message, "तस्वीर बनाते समय एक त्रुटि हुई। कृपया सुनिश्चित करें कि आपका prompt उपयुक्त है या बाद में पुनः प्रयास करें।")
        # You can add more detailed error logging here

# --- Flask Webhook Setup ---
@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '!', 200
    else:
        return 'Invalid content type', 403

# --- Main application execution ---
if __name__ == '__main__':
    # Set webhook only once when the app starts
    if WEBHOOK_URL_BASE and BOT_TOKEN:
        print(f"Setting webhook to: {WEBHOOK_URL_BASE}{WEBHOOK_URL_PATH}")
        bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)
        print(f"Bot started on port {PORT} with webhook.")
        app.run(host='0.0.0.0', port=PORT)
    else:
        print("WEBHOOK_URL_BASE or BOT_TOKEN not set. Exiting.")
        print("Please set TELEGRAM_BOT_TOKEN and WEBHOOK_URL_BASE environment variables.")
        print("For local testing without webhook, you can use `bot.polling()` but it's not for Render.com.")
