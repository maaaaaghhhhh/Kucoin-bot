import requests
import time
import pandas as pd
from binance.client import Client

# توکن و آیدی تلگرام شما
TELEGRAM_TOKEN = "8447614855:AAECwe6GXGQkCYzmc4DYkK0oI3Qjrfs9NAs"
TELEGRAM_CHAT_ID = "402657176"

# کلاینت بایننس (برای داده‌ها نیاز به API key نداره)
client = Client()

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("خطا در ارسال تلگرام:", e)

def get_klines(symbol, interval, limit=50):
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            "time","o","h","l","c","v","ct","qv","nt","tb","tbv","ig"
        ])
        df["o"] = df["o"].astype(float)
        df["h"] = df["h"].astype(float)
        df["l"] = df["l"].astype(float)
        df["c"] = df["c"].astype(float)
        return df
    except Exception as e:
        print("خطا در دریافت داده:", e)
        return None

def check_range(symbol, interval):
    df = get_klines(symbol, interval, 50)
    if df is None or df.empty:
        return None

    high = df["h"].max()
    low = df["l"].min()
    last_close = df["c"].iloc[-1]

    range_percent = (high - low) / low * 100

    if 2 <= range_percent <= 10:
        if last_close > high * 0.995:  # نزدیک شکست سقف
            return f"{symbol} | TF: {interval} | Range: {range_percent:.2f}% | Break ↑"
    return None

def main():
    while True:
        try:
            tickers = client.get_ticker()
            usdt_pairs = [t["symbol"] for t in tickers if t["symbol"].endswith("USDT")]

            found = False
            for symbol in usdt_pairs:
                for interval in ["5m", "15m"]:
                    signal = check_range(symbol, interval)
                    if signal:
                        send_telegram(signal)
                        found = True

            if not found:
                send_telegram("✅ بررسی شد: سیگنالی در این لحظه نبود.")

        except Exception as e:
            print("Error in main loop:", e)

        time.sleep(300)  # هر 5 دقیقه یکبار

if __name__ == "__main__":
    main()
