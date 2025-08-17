import requests
import time
import datetime

# اطلاعات تلگرام
TELEGRAM_TOKEN = "8447614855:AAECwe6GXGQkCYzmc4DYkK0oI3Qjrfs9NAs"
CHAT_ID = "402657176"

# API بایننس
BINANCE_API = "https://api.binance.com/api/v3/klines"

# تابع ارسال پیام به تلگرام
def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram error:", e)

# بررسی رنج و شکست
def check_range(symbol, interval):
    try:
        url = f"{BINANCE_API}?symbol={symbol}&interval={interval}&limit=20"
        response = requests.get(url, timeout=10)
        data = response.json()

        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        volumes = [float(c[5]) for c in data]

        avg_volume = sum(volumes) / len(volumes)
        if avg_volume < 50000:  # حجم حداقل 50 هزار دلار
            return

        high = max(highs)
        low = min(lows)
        last_close = closes[-1]

        range_percent = (high - low) / low * 100

        if 2 <= range_percent <= 10:  # رنج بین 2 تا 10 درصد
            if last_close > high:  # شکست به سمت بالا
                msg = f"📈 {symbol} شکست رنج {range_percent:.2f}% در تایم {interval}"
                send_telegram_message(msg)

    except Exception as e:
        print(f"Error {symbol}-{interval}:", e)

# حلقه اصلی
symbols = []
try:
    r = requests.get("https://api.binance.com/api/v3/exchangeInfo")
    data = r.json()
    symbols = [s["symbol"] for s in data["symbols"] if s["quoteAsset"] == "USDT"]
except:
    print("Error loading Binance symbols")

while True:
    for sym in symbols:
        for tf in ["5m", "15m"]:
            check_range(sym, tf)

    print("Checked all symbols at", datetime.datetime.now())
    time.sleep(60)  # هر 1 دقیقه چک کند
