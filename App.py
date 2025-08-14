import os
import time
import datetime
import requests
import threading
from flask import Flask

# ================= تنظیمات =================
TELEGRAM_TOKEN = "8447614855:AAECwe6GXGQkCYzmc4DYkK0oI3Qjrfs9NAs"  # جایگزین توکن شما
CHAT_ID = "402657176"                       # جایگزین Chat ID شما
CHECK_INTERVAL = 60  # بررسی هر 60 ثانیه

# ================= وب‌سرور برای Render =================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!", 200

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# ================= توابع اصلی =================
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

def get_spot_usdt_pairs():
    url = "https://api.kucoin.com/api/v1/symbols"
    r = requests.get(url).json()
    return [x['symbol'] for x in r['data'] if x['quoteCurrency'] == "USDT" and x['enableTrading']]

def get_klines(symbol, interval="5min"):
    url = f"https://api.kucoin.com/api/v1/market/candles?type={interval}&symbol={symbol}"
    r = requests.get(url).json()
    return r['data']  # [time, open, close, high, low, volume]

def is_range_and_breakout(candles):
    if len(candles) < 21:
        return False
    closes = [float(c[2]) for c in candles[1:21]]  # 20 کندل بسته شده
    highs = [float(c[3]) for c in candles[1:21]]
    lows = [float(c[4]) for c in candles[1:21]]

    high_level = max(highs)
    low_level = min(lows)

    if (high_level - low_level) / low_level > 0.015:
        return False

    last_close = float(candles[1][2])
    return last_close > high_level

def bot_loop():
    send_telegram_message("✅ KuCoin Range Breakout Bot Started.")
    pairs = get_spot_usdt_pairs()
    print(f"{len(pairs)} pairs found.")

    last_alert = {}

    while True:
        try:
            for symbol in pairs:
                candles = get_klines(symbol)
                if is_range_and_breakout(candles):
                    now_ts = int(time.time())
                    if now_ts - last_alert.get(symbol, 0) > 1800:  # هر 30 دقیقه یک هشدار
                        msg = f"🚀 {symbol} | 5m range breakout up\nTime: {datetime.datetime.utcnow()} UTC"
                        print(msg)
                        send_telegram_message(msg)
                        last_alert[symbol] = now_ts
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print("Error:", e)
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    bot_loop()
