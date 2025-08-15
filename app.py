import time
import datetime
import requests
import ccxt

# ===== تنظیمات تلگرام =====
TELEGRAM_TOKEN = "8447614855:AAECwe6GXGQkCYzmc4DYkK0oI3Qjrfs9NAs"
CHAT_ID = "402657176"

# ===== تنظیمات بات =====
CHECK_INTERVAL = 300          # هر چند ثانیه یکبار کل مارکت‌ها بررسی شوند (اینجا 5 دقیقه)
RANGE_PCTS = [2, 3]           # درصدهای رنجی که می‌خوای مقایسه بشن
TIMEFRAMES = ["5m", "15m"]    # تایم‌فریم‌های مورد بررسی
MIN_LAST_CANDLE_USD_VOL = 50_000  # حداقل حجم دلاری آخرین کندل بسته‌شده

# ===== اتصال به بایننس با ccxt (بدون نیاز به API Key برای دیتای عمومی) =====
exchange = ccxt.binance({
    "enableRateLimit": True,  # مدیریت ریت‌لیمیت
    "options": {"adjustForTimeDifference": True}
})

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=15)
    except Exception as e:
        print("Telegram Error:", e)

def load_usdt_spot_symbols():
    markets = exchange.load_markets()
    symbols = []
    for sym, info in markets.items():
        # فقط جفت‌های اسپات با USDT
        if info.get("spot") and sym.endswith("/USDT"):
            symbols.append(sym)
    return symbols

def fetch_ohlcv_safe(symbol: str, timeframe: str, limit: int = 20):
    try:
        # ccxt برمی‌گردونه: [timestamp, open, high, low, close, volume]
        data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return data
    except Exception as e:
        print(f"Fetch OHLCV error for {symbol} {timeframe}: {e}")
        return []

def is_up_breakout_within_range(ohlcv, max_range_pct: float) -> tuple[bool, float, float, float]:
    """
    بررسی می‌کند که:
    - 19 کندل بسته‌شده اخیر (همه به جز آخرین کندل در آرایه) در یک رنج <= max_range_pct باشند
    - آخرین کندل بسته‌شده بالای سقف رنج بسته شده باشد
    برمی‌گرداند: (True/False, range_pct, range_high, last_close)
    """
    if len(ohlcv) < 20:
        return (False, 0.0, 0.0, 0.0)

    # آخرین آیتم معمولاً آخرین کندل بسته‌شده است (ccxt اغلب کندل جاری را نمی‌دهد)
    closed = ohlcv[:-1]  # همه به جز آخرین برای محاسبه رنج (محافظه‌کارانه‌تر)
    last = ohlcv[-1]

    highs = [c[2] for c in closed]
    lows  = [c[3] for c in closed]

    if not highs or not lows:
        return (False, 0.0, 0.0, 0.0)

    range_high = max(highs)
    range_low  = min(lows)

    if range_low <= 0:
        return (False, 0.0, 0.0, 0.0)

    range_pct = (range_high - range_low) / range_low * 100.0
    last_close = float(last[4])

    if range_pct <= max_range_pct and last_close > range_high:
        return (True, range_pct, range_high, last_close)

    return (False, range_pct, range_high, last_close)

def last_candle_usd_volume(ohlcv) -> float:
    """
    حجم دلاری کندل آخر = volume * close
    """
    if not ohlcv:
        return 0.0
    last = ohlcv[-1]
    close = float(last[4])
    vol   = float(last[5])
    return vol * close

def main():
    # جلوگیری از ارسال هشدار تکراری: کلید = (symbol, timeframe, pct) و مقدار = آخرین زمان ارسال
    last_alert_at = {}

    # سلام اولیه
    send_telegram_message("✅ Binance Range Breakout Bot started (TF: 5m & 15m | Range: 2% & 3%).")

    symbols = load_usdt_spot_symbols()
    print(f"{len(symbols)} USDT spot pairs loaded.")

    while True:
        loop_start = time.time()
        any_signal = False
        signals_text = []

        for tf in TIMEFRAMES:
            for sym in symbols:
                # دیتای کندل‌ها
                ohlcv = fetch_ohlcv_safe(sym, tf, limit=20)
                if len(ohlcv) < 20:
                    continue

                # فیلتر حجم دلاری کندل آخر
                usd_vol = last_candle_usd_volume(ohlcv)
                if usd_vol < MIN_LAST_CANDLE_USD_VOL:
                    continue

                # بررسی برای هر آستانه رنج
                for pct in RANGE_PCTS:
                    ok, range_pct, range_high, last_close = is_up_breakout_within_range(ohlcv, pct)
                    if ok:
                        key = (sym, tf, pct)
                        now = time.time()
                        # ضداسپم: برای هر کلید حداقل 30 دقیقه بین هشدارها فاصله
                        if now - last_alert_at.get(key, 0) > 1800:
                            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                            msg = (
                                f"🚀 {sym} | TF: {tf} | Range≤{pct}%\n"
                                f"Range%≈{range_pct:.2f} | LastClose={last_close:.6g}\n"
                                f"LastCandle USD Vol≈{int(usd_vol):,}\n"
                                f"Time: {ts} UTC"
                            )
                            signals_text.append(msg)
                            last_alert_at[key] = now
                            any_signal = True

                # وقفه کوچک برای رعایت ریت‌لیمیت
                time.sleep(0.02)

        if any_signal:
            # اگر چند سیگنال داشتیم همه را در یک پیام می‌فرستیم
            send_telegram_message("\n\n".join(signals_text))
        else:
            # اگر هیچ سیگنالی نبود
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            send_telegram_message(f"🔍 بررسی شد: سیگنالی پیدا نشد. ({ts} UTC)")

        # فاصله بین چرخه‌ها
        elapsed = time.time() - loop_start
        sleep_for = max(5, CHECK_INTERVAL - elapsed)
        time.sleep(sleep_for)

if __name__ == "__main__":
    import datetime
    main()
