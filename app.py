from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import asyncio
import aiohttp

app = Flask(__name__)
CORS(app)

# -----------------------------
# Async Yahoo Fetch (keeps your response structure)
# -----------------------------
async def fetch_symbol(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        return {
            "symbol": symbol,
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "previousClose": info.get("previousClose"),
            "change": round(
                ((info.get("currentPrice") or info.get("regularMarketPrice", 0)) - info.get("previousClose", 0))
                / info.get("previousClose", 1)
                * 100,
                2,
            ) if info.get("previousClose") else None,
            "volume": info.get("volume"),
            "exchange": info.get("exchange"),
            "marketCap": info.get("marketCap"),
            "currency": info.get("currency"),
            "name": info.get("shortName") or info.get("longName"),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


# -----------------------------
# Helper: batch process for large lists
# -----------------------------
async def process_symbols(symbols, batch_size=100):
    """Breaks large symbol lists into smaller batches for efficiency."""
    results = []
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        tasks = [fetch_symbol(s) for s in batch]
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
