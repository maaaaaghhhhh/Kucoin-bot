import os
import time
import threading
import datetime
import requests
from flask import Flask

# ===== تلگرام =====
TELEGRAM_TOKEN = "8447614855:AAECwe6GXGQkCYzmc4DYkK0oI3Qjrfs9NAs"
CHAT_ID = "402657176"

# ===== تنظیمات عمومی =====
CHECK_INTERVAL = 300  # هر 5 دقیقه یک چرخه
TIMEFRAMES = ["5m", "15m"]
RANGE_MIN = 2.0       # حداقل درصد رنج
RANGE_MAX = 10.0      # حداکثر درصد رنج
MIN_QUOTE_VOL = 50_000  # حداقل حجم دلاری کندل بسته‌شده (USDT)

BINANCE_BASE = "https://api.binance.com"

# --- وب‌سرور برای آنلاین ماندن در Render ---
app = Flask(__name__)
@app.get("/")
def home():
    return "OK", 200

def run_server():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- ابزار تلگرام ---
def send_telegram(text: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text},
            timeout=15
        )
    except Exception as e:
        print("Telegram Error:", e)

# --- ابزار بایننس ---
def get_usdt_symbols():
    """فقط جفت‌های اسپات/USDT در وضعیت TRADING (بدون توکن‌های UP/DOWN)"""
    try:
        r = requests.get(f"{BINANCE_BASE}/api/v3/exchangeInfo", timeout=20)
        data = r.json()
        symbols = []
        for s in data.get("symbols", []):
            if (
                s.get("status") == "TRADING"
                and s.get("quoteAsset") == "USDT"
                and s.get("isSpotTradingAllowed", True)
            ):
                sym = s.get("symbol")
                # حذف توکن‌های اهرمی مثل BTCUP/BTCDOWN و موارد عجیب
                if sym and not sym.endswith("UPUSDT") and not sym.endswith("DOWNUSDT"):
                    symbols.append(sym)
        return symbols
    except Exception as e:
        print("Error fetching symbols:", e)
        return []

def fetch_klines(symbol: str, interval: str, limit: int = 50):
    """
    v3/klines -> لیست کندل‌ها از قدیم به جدید
    هر کندل: [0]openTime, [1]open, [2]high, [3]low, [4]close, [5]volume(base),
             [6]closeTime, [7]quoteAssetVolume(USDT), ...
    """
    try:
        url = f"{BINANCE_BASE}/api/v3/klines"
        resp = requests.get(url, params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=20)
        return resp.json()
    except Exception as e:
        print(f"Fetch klines error {symbol} {interval}: {e}")
        return []

def analyze_symbol(symbol: str, interval: str):
    """
    بر اساس 20 کندل بسته‌شده اخیر:
    - 20 کندل رنج (بدون آخرین کندل جاری) => از -22 تا -2
    - آخرین کندل بسته‌شده => -2
    - شرط: Range% بین [RANGE_MIN, RANGE_MAX] و آخرین کلوز بالای سقف رنج
           و حجم دلاری کندل آخر >= MIN_QUOTE_VOL
    """
    kl = fetch_klines(symbol, interval, limit=50)
    if not isinstance(kl, list) or len(kl) < 22:
        return None

    # آخرین کندل بسته‌شده: -2 (چون -1 ممکنه هنوز باز باشد)
    last_closed = kl[-2]
    range_window = kl[-22:-2]  # 20 کندل بسته‌شده قبل از آخرین بسته

    highs = [float(c[2]) for c in range_window]
    lows  = [float(c[3]) for c in range_window]
    if not highs or not lows:
        return None

    range_high = max(highs)
    range_low  = min(lows)
    if range_low <= 0:
        return None

    last_close = float(last_closed[4])
    last_quote_vol = float(last_closed[7])  # حجم دلاری کندل آخر (Quote Volume)

    range_pct = (range_high - range_low) / range_low * 100.0

    if (RANGE_MIN <= range_pct <= RANGE_MAX) and (last_close > range_high) and (last_quote_vol >= MIN_QUOTE_VOL):
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        return f"🚀 {symbol} | TF: {interval} | Range≈{range_pct:.2f}% | Vol≈{int(last_quote_vol):,} USDT\nTime: {ts} UTC"
    return None

def chunk_send(messages, chunk_limit=3500):
    """ارسال پیام‌های طولانی در چند بخش تا به محدودیت تلگرام نخوریم."""
    buf = ""
    for line in messages:
        if len(buf) + len(line) + 1 > chunk_limit:
            send_telegram(buf.strip())
            buf = ""
        buf += line + "\n"
    if buf.strip():
        send_telegram(buf.strip())

def main_loop():
    send_telegram("✅ Binance Range Bot started (TF: 5m & 15m | Range: 2–10% | Vol≥50k USDT).")
    symbols = get_usdt_symbols()
    print(f"Loaded {len(symbols)} USDT symbols.")

    while True:
        start = time.time()
        signals = []

        for tf in TIMEFRAMES:
            for sym in symbols:
                sig = analyze_symbol(sym, tf)
                if sig:
                    signals.append(sig)
                time.sleep(0.02)  # رعایت ریت‌لیمیت

        if signals:
            chunk_send(signals)
        else:
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            send_telegram(f"🔍 بررسی شد: سیگنالی پیدا نشد. ({ts} UTC)")

        elapsed = time.time() - start
        sleep_for = max(5, CHECK_INTERVAL - elapsed)
        time.sleep(sleep_for)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    main_loop()
