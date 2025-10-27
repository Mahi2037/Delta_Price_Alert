import asyncio
import requests
from telegram import Bot

BOT_TOKEN = "8338340082:AAEsoaqZFzeOMk7fD5_KOSltRc07RHY7BXw"
CHANNEL_ID = "-1003212268545"

INTERVAL = 60  # check every 1 minute


async def send_alert(bot: Bot, message: str):
    """Send alert message to Telegram channel."""
    await bot.send_message(chat_id=CHANNEL_ID, text=message)


async def fetch_futures_symbols():
    """Fetch only futures symbols from Delta Exchange."""
    url = "https://api.delta.exchange/v2/products"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json().get("result", [])

    futures = [
        item["symbol"]
        for item in data
        if item.get("contract_type") == "futures" and item.get("status") == "live"
    ]

    print(f"✅ Found {len(futures)} live futures symbols.")
    return futures


async def check_futures(bot: Bot):
    """Check 24h high/low breakouts for futures only."""
    last_alerted = {}

    # Fetch all futures symbols once
    futures_symbols = await fetch_futures_symbols()

    while True:
        try:
            url = "https://api.delta.exchange/v2/tickers"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json().get("result", [])

            for item in data:
                symbol = item["symbol"]

                # Skip if not a futures symbol
                if symbol not in futures_symbols:
                    continue

                price = float(item["spot_price"])
                high_24h = float(item["high"])
                low_24h = float(item["low"])

                if price == 0 or high_24h == 0 or low_24h == 0:
                    continue

                msg = None

                if price >= high_24h and last_alerted.get(symbol) != "high":
                    msg = (
                        f"🚀 {symbol} just broke its 24h HIGH!\n"
                        f"Price: {price}\nPrev High: {high_24h}"
                    )
                    last_alerted[symbol] = "high"

                elif price <= low_24h and last_alerted.get(symbol) != "low":
                    msg = (
                        f"⚠️ {symbol} just broke its 24h LOW!\n"
                        f"Price: {price}\nPrev Low: {low_24h}"
                    )
                    last_alerted[symbol] = "low"

                if msg:
                    print(msg)
                    await send_alert(bot, msg)

            print("✅ Checked all futures.")
            await asyncio.sleep(INTERVAL)

        except Exception as e:
            print(f"❌ Error: {e}")
            await asyncio.sleep(30)


async def main():
    bot = Bot(token=BOT_TOKEN)
    print("🚀 Delta Futures 24H High/Low Alert Bot running...")
    await check_futures(bot)


if __name__ == "__main__":
    asyncio.run(main())
