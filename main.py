import requests
import pandas as pd
import numpy as np
import ta
import time

# ==== CONFIG ====
FINNHUB_TOKEN = "your_finnhub_token"
BOT_TOKEN = "your_telegram_bot_token"
CHAT_ID = "your_chat_id"
SYMBOL = "BINANCE:BTCUSDT"   # Example, can change later
TIMEFRAME = "1"  # in minutes

# ==== FUNCTIONS ====

def get_candles(symbol, resolution="1", count=100):
    url = f"https://finnhub.io/api/v1/crypto/candle?symbol={symbol}&resolution={resolution}&count={count}&token={FINNHUB_TOKEN}"
    res = requests.get(url).json()
    if res.get("s") != "ok":
        return None
    df = pd.DataFrame({
        "t": res["t"],
        "o": res["o"],
        "h": res["h"],
        "l": res["l"],
        "c": res["c"],
        "v": res["v"]
    })
    df["time"] = pd.to_datetime(df["t"], unit="s")
    return df


def calculate_indicators(df):
    df["EMA_fast"] = ta.trend.EMAIndicator(df["c"], window=9).ema_indicator()
    df["EMA_slow"] = ta.trend.EMAIndicator(df["c"], window=21).ema_indicator()
    df["RSI"] = ta.momentum.RSIIndicator(df["c"], window=14).rsi()
    macd = ta.trend.MACD(df["c"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    boll = ta.volatility.BollingerBands(df["c"], window=20, window_dev=2)
    df["BB_high"] = boll.bollinger_hband()
    df["BB_low"] = boll.bollinger_lband()
    df["CCI"] = ta.trend.CCIIndicator(df["h"], df["l"], df["c"], window=20).cci()
    return df


def get_signal(df):
    latest = df.iloc[-1]
    votes = []

    # EMA crossover
    if latest["EMA_fast"] > latest["EMA_slow"]:
        votes.append("BUY")
    else:
        votes.append("SELL")

    # RSI
    if latest["RSI"] < 30:
        votes.append("BUY")
    elif latest["RSI"] > 70:
        votes.append("SELL")

    # MACD
    if latest["MACD"] > latest["MACD_signal"]:
        votes.append("BUY")
    else:
        votes.append("SELL")

    # Bollinger
    if latest["c"] < latest["BB_low"]:
        votes.append("BUY")
    elif latest["c"] > latest["BB_high"]:
        votes.append("SELL")

    # CCI
    if latest["CCI"] < -100:
        votes.append("BUY")
    elif latest["CCI"] > 100:
        votes.append("SELL")

    # Final decision by majority
    signal = max(set(votes), key=votes.count)
    return signal


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, json=payload)


# ==== MAIN LOOP ====
while True:
    try:
        df = get_candles(SYMBOL, resolution=TIMEFRAME, count=100)
        if df is not None:
            df = calculate_indicators(df)
            signal = get_signal(df)
            msg = f"📊 Signal for {SYMBOL}\n➡️ {signal}"
            send_telegram(msg)
            print(msg)
    except Exception as e:
        print("Error:", e)

    time.sleep(60)  # run every 1 min
