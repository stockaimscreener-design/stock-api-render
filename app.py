from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import asyncio
import aiohttp

app = Flask(__name__)
CORS(app)

# -----------------------------
# Async Yahoo Fetch (keeps your response structure)
def fetch_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if not price:
            return None

        volume = info.get('volume') or info.get('regularMarketVolume')
        avg_volume = info.get('averageDailyVolume10Day')
        prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')

        # Calculate change percent
        change_percent = None
        if price and prev_close and prev_close != 0:
            change_percent = round(((price - prev_close) / prev_close) * 100, 4)

        # Calculate relative volume
        relative_volume = None
        if volume and avg_volume and avg_volume != 0:
            relative_volume = round(volume / avg_volume, 2)

        return {
            'symbol': symbol,
            'name': info.get('longName') or info.get('shortName'),
            'price': price,
            'open': info.get('open') or info.get('regularMarketOpen'),
            'high': info.get('dayHigh') or info.get('regularMarketDayHigh'),
            'low': info.get('dayLow') or info.get('regularMarketDayLow'),
            'volume': volume,
            'avg_volume': avg_volume,
            'change_percent': change_percent,
            'market_cap': info.get('marketCap'),
            'shares_float': info.get('floatShares'),
            'relative_volume': relative_volume,
            'pe_ratio': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'dividend_yield': info.get('dividendYield'),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'country': info.get('country'),
        }

    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

# -----------------------------
# Helper: batch process for large lists
# -----------------------------
async def process_symbols(symbols, batch_size=100):
    """Breaks large symbol lists into smaller batches for efficiency."""
    results = []
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        tasks = [fetch_stock_data(s) for s in batch]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
    return results


# -----------------------------
# GET /quote — for smaller symbol lists (old version)
# -----------------------------
@app.route("/quote", methods=["GET"])
async def quote_get():
    symbols = request.args.get("symbols", "")
    if not symbols:
        return jsonify({"error": "symbols query param missing"}), 400

    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    results = await process_symbols(symbol_list)

    return jsonify({
        "status": "success",
        "count": len(results),
        "data": results
    })


# -----------------------------
# POST /quote — for large symbol lists via JSON
# -----------------------------
@app.route("/quote", methods=["POST"])
async def quote_post():
    data = request.get_json(silent=True)
    if not data or "symbols" not in data:
        return jsonify({"error": "JSON body must include a 'symbols' list"}), 400

    symbol_list = [s.strip().upper() for s in data["symbols"] if isinstance(s, str) and s.strip()]
    results = await process_symbols(symbol_list)

    return jsonify({
        "status": "success",
        "count": len(results),
        "data": results
    })


# -----------------------------
# Health Check
# -----------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Stock API running on Render!"})


# -----------------------------
# App Entrypoint
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
