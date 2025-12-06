import requests
import os

FINNHUB_KEY = os.getenv("FINNHUB_KEY", "d3ktp81r01qp3ucpk3ngd3ktp81r01qp3ucpk3o0")
symbol = "AAPL"

# 1️⃣ Get quote data
quote_url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
quote_data = requests.get(quote_url).json()

# 2️⃣ Get company profile (for name, sector, etc.)
profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={FINNHUB_KEY}"
profile_data = requests.get(profile_url).json()

# 3️⃣ Combine results
stock = {
    "symbol": symbol,
    "name": profile_data.get("name"),
    "price": quote_data.get("c"),
    "open": quote_data.get("o"),
    "high": quote_data.get("h"),
    "low": quote_data.get("l"),
    "prev_close": quote_data.get("pc"),
    "change_percent": round(((quote_data.get("c") - quote_data.get("pc")) / quote_data.get("pc")) * 100, 2)
        if quote_data.get("pc") else None,
    "market_cap": profile_data.get("marketCapitalization"),
    "exchange": profile_data.get("exchange"),
}

print(stock)
