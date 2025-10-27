import asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import time

app = Flask(__name__)
CORS(app)

# -----------------------------
# Cache for sector/industry data
# -----------------------------
SECTOR_CACHE = {}

# -----------------------------
# Helper Functions
# -----------------------------
async def fetch_sector_info(symbol):
    """Fetch sector info only if missing."""
    if symbol in SECTOR_CACHE:
        return SECTOR_CACHE[symbol]

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        sector = info.get("sector", "Unknown")
        industry = info.get("industry", "Unknown")
        SECTOR_CACHE[symbol] = {"sector": sector, "industry": industry}
        await asyncio.sleep(0.2)  # Prevent Yahoo rate limit
        return SECTOR_CACHE[symbol]
    except Exception as e:
        print(f"⚠️ Could not fetch sector info for {symbol}: {e}")
        return {"sector": "Unknown", "industry": "Unknown"}


async def fetch_quote(symbol):
    """Fetch real-time quote data for a single stock."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Fetch sector only once per symbol
        sector_info = await fetch_sector_info(symbol)

        price = info.get("regularMarketPrice")
        volume = info.get("regularMarketVolume")
        avg_volume = info.get("averageDailyVolume10Day") or info.get("averageDailyVolume3Month") or 1
        relative_volume = (volume or 0) / avg_volume if avg_volume else 0

        change_percent = info.get("regularMarketChangePercent")
        change = info.get("regularMarketChange")

        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol,
            "price": price,
            "open": info.get("open") or info.get("regularMarketOpen"),
            "high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
            "low": info.get("dayLow") or info.get("regularMarketDayLow"),
            "volume": volume,
            "avg_volume": avg_volume,
            "relative_volume": relative_volume,
            "change_percent": change_percent,
            "market_cap": info.get("marketCap"),
            "shares_float": info.get("floatShares"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "sector": sector_info.get("sector"),
            "industry": sector_info.get("industry"),
            "country": info.get("country"),
        }
    except Exception as e:
        print(f"⚠️ Error fetching {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


async def process_symbols(symbols):
    """Process all symbols one by one to avoid 429 rate limits."""
    results = []
    for symbol in symbols:
        data = await fetch_quote(symbol)
        results.append(data)
        await asyncio.sleep(0.1)  # 10 per second safely
    return results


# -----------------------------
# API Endpoint
# -----------------------------
@app.route("/quote", methods=["GET"])
async def quote_get():
    """Endpoint: /quote?symbols=AAPL,MSFT,TSLA"""
    symbols_param = request.args.get("symbols")

    if not symbols_param:
        return jsonify({
            "success": False,
            "error": "No symbols provided. Use /quote?symbols=AAPL,MSFT,..."
        }), 400

    symbols = [s.strip().upper() for s in symbols_param.split(",") if s.strip()]
    print(f"🔍 Fetching quotes for {len(symbols)} symbols: {symbols[:5]}...")

    results = await process_symbols(symbols)
    valid_results = [r for r in results if r.get("price") is not None]

    return jsonify({
        "success": True,
        "count": len(valid_results),
        "data": valid_results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })


# -----------------------------
# Entrypoint for Render
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
