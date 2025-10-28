import asyncio
import requests
from telegram import Bot
from datetime import datetime, timezone
import json
import os

# ========================
# 🔧 CONFIGURATION
# ========================
BOT_TOKEN = "8338340082:AAEsoaqZFzeOMk7fD5_KOSltRc07RHY7BXw"
CHANNEL_ID = "-1003212268545"
INTERVAL = 60  # seconds between checks
ALERT_FILE = "alert_history.json"  # store daily alerts
DELTA_API = "https://api.delta.exchange/v2"

# ========================
# 💾 Load previous alerts
# ========================
if os.path.exists(ALERT_FILE):
    with open(ALERT_FILE, "r") as f:
        alert_history = json.load(f)
else:
    alert_history = {}


# ========================
# 📤 Telegram Alert
# ========================
async def send_alert(bot: Bot, message: str):
    """Send alert message to Telegram channel."""
    await bot.send_message(chat_id=CHANNEL_ID, text=message)


# ========================
# 💹 Fetch Futures + Perpetual
# ========================
async def fetch_symbols():
    """Fetch only Futures and Perpetual products from Delta Exchange."""
    url = f"{DELTA_API}/products"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json().get("result", [])

    symbols = [
        item["symbol"]
        for item in data
        if item.get("state") == "live"
        and item.get("contract_type") in ["futures", "perpetual_futures"]
    ]

    print(f"✅ Found {len(symbols)} live Futures/Perpetual symbols.")
    if symbols:
        print("🔹 Sample:", symbols[:10])
    return symbols


# ========================
# 🧠 Alert History Check
# ========================
def already_alerted_today(symbol, alert_type):
    """Check if symbol already alerted for this type today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return alert_history.get(symbol, {}).get(alert_type) == today


def mark_alerted(symbol, alert_type):
    """Mark symbol as alerted today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if symbol not in alert_history:
        alert_history[symbol] = {}
    alert_history[symbol][alert_type] = today
    with open(ALERT_FILE, "w") as f:
        json.dump(alert_history, f, indent=2)


# ========================
# 📈 Main Logic
# ========================
async def check_markets(bot: Bot):
    """Check 24H high/low for Futures + Perpetual (only 1 alert/day)."""
    all_symbols = await fetch_symbols()

    if not all_symbols:
        print("⚠️ No active futures/perpetual symbols found — check API or filters.")
        return

    while True:
        try:
            url = f"{DELTA_API}/tickers"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            tickers = response.json().get("result", [])
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            now_time = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

            for item in tickers:
                symbol = item["symbol"]
                if symbol not in all_symbols:
                    continue

                price = float(item.get("spot_price", 0))
                high = float(item.get("high", 0))
                low = float(item.get("low", 0))

                if price == 0 or high == 0 or low == 0:
                    continue

                msg = None

                # 🚀 HIGH BREAKOUT
                if price >= high and not already_alerted_today(symbol, "high"):
                    msg = (
                        f"🚀 {symbol} broke its 24H HIGH!\n"
                        f"💰 Price: {price}\n📈 Prev High: {high}\n"
                        f"📅 Date: {today}\n⏰ Time: {now_time}"
                    )
                    mark_alerted(symbol, "high")

                # ⚠️ LOW BREAKOUT
                elif price <= low and not already_alerted_today(symbol, "low"):
                    msg = (
                        f"⚠️ {symbol} broke its 24H LOW!\n"
                        f"💰 Price: {price}\n📉 Prev Low: {low}\n"
                        f"📅 Date: {today}\n⏰ Time: {now_time}"
                    )
                    mark_alerted(symbol, "low")

                if msg:
                    print(msg)
                    await send_alert(bot, msg)

            print("✅ Checked all Futures + Perpetual symbols.")
            await asyncio.sleep(INTERVAL)

        except Exception as e:
            print(f"❌ Error: {e}")
            await asyncio.sleep(30)


# ========================
# 🚀 MAIN
# ========================
async def main():
    bot = Bot(token=BOT_TOKEN)
    now_ist = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"📉 Delta Futures + Perpetual High/Low Alert Bot running ({now_ist})")
    await check_markets(bot)


if __name__ == "__main__":
    asyncio.run(main())
