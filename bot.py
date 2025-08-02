from flask import Flask, request
from binance.client import Client
import os
import requests
import threading
import time
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Tải dữ liệu sentiment của NLTK lần đầu
nltk.download('vader_lexicon')

# ====== CẤU HÌNH ======
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
PASSPHRASE = os.getenv("BOT_PASSPHRASE")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")      # Bot Telegram
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")          # ID nhóm/cá nhân Telegram
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY")    # API từ CryptoPanic

client = Client(API_KEY, API_SECRET, testnet=False)
app = Flask(__name__)

# ====== SENTIMENT ANALYSIS ======
sia = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    score = sia.polarity_scores(text)
    if score['compound'] >= 0.05:
        return "Tích cực 👍"
    elif score['compound'] <= -0.05:
        return "Tiêu cực 👎"
    else:
        return "Trung lập 😐"

# ====== GỬI TELEGRAM ======
def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    requests.post(url, data=data)

# ====== LẤY TIN TỨC TỪ CRYPTOPANIC ======
def get_crypto_news():
    url = "https://cryptopanic.com/api/v1/posts/"
    params = {"auth_token": CRYPTOPANIC_API_KEY, "public": "true"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get('results', [])
    return []

def news_worker():
    sent_ids = set()
    while True:
        news_list = get_crypto_news()
        for news in news_list:
            if news['id'] not in sent_ids:
                title = news['title']
                link = news['url']
                sentiment = analyze_sentiment(title)
                msg = f"📰 <b>{title}</b>\n{link}\nSentiment: {sentiment}"
                send_telegram_message(msg)
                sent_ids.add(news['id'])
        time.sleep(600)  # Lặp mỗi 10 phút

# ====== FUTURES WEBHOOK ======
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data['passphrase'] != PASSPHRASE:
        return {"error": "Unauthorized"}, 403

    symbol = data['symbol']
    side = data['side'].upper()
    quantity = float(data['quantity'])
    leverage = int(data.get('leverage', 10))
    tp = float(data.get('tp', 0))
    sl = float(data.get('sl', 0))

    client.futures_change_leverage(symbol=symbol, leverage=leverage)

    order = client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)

    if tp > 0:
        client.futures_create_order(symbol=symbol, side="SELL" if side == "BUY" else "BUY",
                                    type="TAKE_PROFIT_MARKET", stopPrice=tp, closePosition=True)

    if sl > 0:
        client.futures_create_order(symbol=symbol, side="SELL" if side == "BUY" else "BUY",
                                    type="STOP_MARKET", stopPrice=sl, closePosition=True)

    send_telegram_message(f"📈 Đã vào lệnh {side} {symbol} SL: {sl} TP: {tp}")
    return {"message": "Order executed", "order": order}

# ====== CHẠY BOT ======
if __name__ == "__main__":
    threading.Thread(target=news_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
