from flask import Flask, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# API keys — set via Render or local .env
FINNHUB_KEY = os.getenv("FINNHUB_KEY", "d3ktp81r01qp3ucpk3ngd3ktp81r01qp3ucpk3o0")
TWELVE_KEY = os.getenv("TWELVE_KEY", "50316174ec0041b9850b1a1003960280")

# @app.route("/stock/<symbol>", methods=["GET"])
# def get_stock(symbol):
#     """Fetch stock data for a given symbol."""
#     data = fetch_stock(symbol)
#     return jsonify(data)


@app.route("/stock/finn/<symbol>", methods=["GET"])
def get_finn_stock(symbol):
    """Fetch stock data for a given symbol."""
    data = fetch_from_finnhub(symbol)
    return jsonify(data)



@app.route("/stock/twelve/<symbol>", methods=["GET"])
def get_twelve_stock(symbol):
    """Fetch stock data for a given symbol."""
    data = fetch_from_twelvedata(symbol)
    print(data)
    return jsonify(data)




def fetch_from_finnhub(symbol: str):
    """Fetch stock data from Finnhub API."""
    try:
        symbol = symbol.upper().strip()
        quote_url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
        profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={FINNHUB_KEY}"

        quote = requests.get(quote_url, timeout=10).json()
        profile = requests.get(profile_url, timeout=10).json()

        if not quote.get("c"):  # No current price
            return None

        change_percent = None
        if quote.get("pc"):
            try:
                change_percent = round(((quote["c"] - quote["pc"]) / quote["pc"]) * 100, 2)
            except ZeroDivisionError:
                change_percent = None

        return {
            "source": "finnhub",
            "symbol": symbol,
            "name": profile.get("name"),
            "price": quote.get("c"),
            "open": quote.get("o"),
            "high": quote.get("h"),
            "low": quote.get("l"),
            "prev_close": quote.get("pc"),
            "change_percent": change_percent,
            "market_cap": profile.get("marketCapitalization"),
            "exchange": profile.get("exchange")
        }

    except Exception as e:
        print(f"⚠️ Finnhub failed for {symbol}: {e}")
        return None


def fetch_from_twelvedata(symbol: str):
    """Fetch stock data from Twelve Data API."""
    try:
        symbol = symbol.upper().strip()
        url = f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={TWELVE_KEY}"
        td = requests.get(url, timeout=10).json()

        return {
                "source": "twelvedata",
                "symbol": td.get("symbol"),
                "name": td.get("name"),
                "price": td.get("price"),
                "open": td.get("open"),
                "high": td.get("high"),
                "low": td.get("low"),
                "volume": td.get("volume"),
                "change_percent": td.get("percent_change"),
                "exchange": td.get("exchange"),
                "timezone": td.get("timezone")
            }

    except Exception as e:
        print(f"⚠️ Twelve Data failed for {symbol}: {e}")
    return None


def fetch_stock(symbol: str):
    """Try Finnhub first, fallback to Twelve Data."""
    data = fetch_from_finnhub(symbol)
    if data:
        return data

    data = fetch_from_twelvedata(symbol)
    if data:
        return data

    return {"symbol": symbol, "error": "No data available"}



if __name__ == "__main__":
    app.run(debug=True)
