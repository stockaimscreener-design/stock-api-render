# =========================================
# app.py — Render-ready Flask + Yahoo Finance API
# =========================================
import asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf

# -----------------------------
# Flask App Setup
# -----------------------------
app = Flask(__name__)
CORS(app)


# -----------------------------
# Fetch Stock Data Function
# -----------------------------
def fetch_stock_data(symbol):
    """
    Fetch stock data safely from Yahoo Finance.
    Returns a dictionary or None if data unavailable.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Basic price data
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not price:
            return None

        volume = info.get("volume") or info.get("regularMarketVolume")
        avg_volume = info.get("averageDailyVolume10Day")
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

        # Change percent
        change_percent = None
        if price and prev_close and prev_close != 0:
            change_percent = round(((price - prev_close) / prev_close) * 100, 4)

        # Relative volume
        relative_volume = None
        if volume and avg_volume and avg_volume != 0:
            relative_volume = round(volume / avg_volume, 2)

        # Build response dictionary
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName"),
            "price": price,
            "open": info.get("open") or info.get("regularMarketOpen"),
            "high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
            "low": info.get("dayLow") or info.get("regularMarketDayLow"),
            "volume": volume,
            "avg_volume": avg_volume,
            "change_percent": change_percent,
            "market_cap": info.get("marketCap"),
            "shares_float": info.get("floatShares"),
            "relative_volume": relative_volume,
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
        }

    except Exception as e:
        print(f"⚠️ Error fetching {symbol}: {e}")
        return None


# -----------------------------
# Async Batch Processor
# -----------------------------
async def process_symbols(symbols):
    """
    Processes symbols in batches asynchronously using threads.
    Each Yahoo call runs in its own background thread.
    """
    results = []
    batch_size = 50  # adjust if needed for rate-limit handling

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]

        # Run blocking fetches in background threads
        tasks = [asyncio.to_thread(fetch_stock_data, s) for s in batch]

        # Wait for all tasks to finish
        batch_results = await asyncio.gather(*tasks)

        # Keep only successful results
        results.extend([r for r in batch_results if r])

    return results


# -----------------------------
# API Route
# -----------------------------
@app.route("/quote", methods=["GET"])
async def quote_get():
    """
    Example: /quote?symbols=AAPL,MSFT,TSLA
    Returns stock data for provided symbols.
    """
    symbols = request.args.get("symbols")
    if not symbols:
        return jsonify({"error": "No symbols provided"}), 400

    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    results = await process_symbols(symbol_list)
    return jsonify({"data": results})


# -----------------------------
# App Entrypoint
# -----------------------------
if __name__ == "__main__":
    # Render start command will run this
    app.run(host="0.0.0.0", port=8000)
