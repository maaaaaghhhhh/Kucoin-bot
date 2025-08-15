import requests
import time
import ccxt

# ===== اطلاعات تلگرام =====
TELEGRAM_TOKEN = "8447614855:AAECwe6GXGQkCYzmc4DYkK0oI3Qjrfs9NAs"
CHAT_ID = "402657176"

# ===== اتصال به کوکوین =====
exchange = ccxt.kucoin()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("خطا در ارسال پیام تلگرام:", e)

def is_range_breakout(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=20)
        closes = [c[4] for c in ohlcv]
        high = max(closes[:-1])
        low = min(closes[:-1])
        last_close = closes[-1]
        
        range_percent = (high - low) / low * 100
        
        # شرط رنج: تغییرات کمتر از 3 درصد (شُل‌تر)
        if range_percent <= 3 and last_close > high:
            return True
    except:
        pass
    return False

def main():
    while True:
        try:
            markets = exchange.load_markets()
            usdt_pairs = [symbol for symbol in markets if symbol.endswith("/USDT")]
            signals = []
            
            for pair in usdt_pairs:
                if is_range_breakout(pair):
                    signals.append(pair)
            
            if signals:
                msg = "🚀 شکست رنج شناسایی شد:\n" + "\n".join(signals)
            else:
                msg = "🔍 بررسی شد - سیگنالی یافت نشد"
            
            send_telegram_message(msg)
            
        except Exception as e:
            print("خطا در اجرای ربات:", e)
        
        time.sleep(300)  # هر ۵ دقیقه

if __name__ == "__main__":
    main()
