import requests
import os

API_KEY = os.getenv("FMP_KEY", "GeC0jNFseudCAK8tfpEEosLZ4AY8Katm")  # get your key from FMP dashboard
symbol = "AAPL"


url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={API_KEY}"
response = requests.get(url)
data = response.json()[0]

print({
    "symbol": data["symbol"],
    "price": data["price"],
    "change_percent": data["changesPercentage"],
    "volume": data["volume"],
    "market_cap": data["marketCap"],
    "open": data["open"],
    "high": data["dayHigh"],
    "low": data["dayLow"]
})
