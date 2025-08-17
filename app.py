import time
import requests
from kucoin.client import Market

# توکن و آی‌دی تلگرام
TELEGRAM_TOKEN = "8447614855:AAECwe6GXGQkCYzmc4DYkK0oI3Qjrfs9NAs"
CHAT_ID = "402657176"

# اتصال به API کوکوین
client = Market(url='https://api.kucoin.com')

# تابع ارسال پیام تلگرام
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram error:", e)

# بررسی جفت ارزها
def check_pairs():
    try:
        symbols = client.get_symbol_list()
        usdt_pairs = [s['symbol'] for s in symbols if s['symbol'].endswith("USDT")]
    except Exception as e:
        send_telegram_message(f"❌ خطا در دریافت جفت ارزها: {e}")
        return

    signals_found = False
    for pair in usdt_pairs:
        for tf in ["5min", "15min"]:
            try:
                klines = client.get_kline(pair, tf, 100)
                closes = [float(k[2]) for k in klines]  # قیمت بسته شدن
                high = max(closes)
                low = min(closes)
                last_price = closes[-1]

                if low == 0:
                    continue

                range_percent = ((high - low) / low) * 100

                # بررسی محدوده رنج بین ۲٪ تا ۱۰٪
                if 2 <= range_percent <= 10:
                    # بررسی شکست به سمت بالا
                    if last_price > high * 0.995:
                        msg = f"📈 شکست رنج {range_percent:.2f}% در {pair} ({tf})"
                        send_telegram_message(msg)
                        signals_found = True

            except Exception as e:
                print(f"Error with {pair} - {tf}: {e}")

    if not signals_found:
        send_telegram_message("ℹ️ هیچ سیگنالی در این دور پیدا نشد.")

# اجرای مداوم هر ۵ دقیقه
while True:
    check_pairs()
    time.sleep(300)  # 300 ثانیه = ۵ دقیقه
