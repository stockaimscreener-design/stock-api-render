"""
StockAim Multi-Source Stock Data API
Supports: Polygon.io, Alpha Vantage, Finnhub
Falls back between sources if one fails or rate limits
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import os
import time
from functools import wraps

app = Flask(__name__)
CORS(app)

# API Configuration
POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY', '')
ALPHAVANTAGE_API_KEY = os.environ.get('ALPHAVANTAGE_API_KEY', '')
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', '')

# Rate limiting cache
_cache = {}
_cache_ttl = 60  # Cache for 60 seconds

def cache_response(ttl=60):
    """Simple cache decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            if cache_key in _cache:
                cached_data, cached_time = _cache[cache_key]
                if time.time() - cached_time < ttl:
                    return cached_data
            
            result = func(*args, **kwargs)
            _cache[cache_key] = (result, time.time())
            return result
        return wrapper
    return decorator


# ============================================
# POLYGON.IO DATA SOURCE
# Free tier: 5 API calls/minute
# ============================================

def get_polygon_quote(symbol):
    """Get current quote from Polygon"""
    if not POLYGON_API_KEY:
        return None
    
    try:
        # Previous day's data (free tier)
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
        params = {'adjusted': 'true', 'apiKey': POLYGON_API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if data.get('status') != 'OK' or not data.get('results'):
            return None
        
        result = data['results'][0]
        
        return {
            'symbol': symbol,
            'price': result.get('c'),  # close
            'open': result.get('o'),
            'high': result.get('h'),
            'low': result.get('l'),
            'volume': result.get('v'),
            'prev_close': result.get('c'),
            'timestamp': result.get('t'),
            'source': 'polygon'
        }
    except Exception as e:
        print(f"Polygon error for {symbol}: {e}")
        return None


def get_polygon_stock_details(symbol):
    """Get stock details (market cap, float, etc.) from Polygon"""
    if not POLYGON_API_KEY:
        return None
    
    try:
        url = f"https://api.polygon.io/v3/reference/tickers/{symbol}"
        params = {'apiKey': POLYGON_API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if data.get('status') != 'OK' or not data.get('results'):
            return None
        
        result = data['results']
        
        return {
            'symbol': symbol,
            'name': result.get('name'),
            'market_cap': result.get('market_cap'),
            'shares_outstanding': result.get('share_class_shares_outstanding'),
            'exchange': result.get('primary_exchange'),
            'sector': result.get('sic_description'),
            'source': 'polygon'
        }
    except Exception as e:
        print(f"Polygon details error for {symbol}: {e}")
        return None


# ============================================
# ALPHA VANTAGE DATA SOURCE
# Free tier: 25 API calls/day
# ============================================

@cache_response(ttl=300)  # Cache for 5 minutes
def get_alphavantage_quote(symbol):
    """Get current quote from Alpha Vantage"""
    if not ALPHAVANTAGE_API_KEY:
        return None
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': ALPHAVANTAGE_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if 'Global Quote' not in data or not data['Global Quote']:
            return None
        
        quote = data['Global Quote']
        
        price = float(quote.get('05. price', 0))
        prev_close = float(quote.get('08. previous close', 0))
        change_percent = None
        
        if price and prev_close and prev_close != 0:
            change_percent = round(((price - prev_close) / prev_close) * 100, 4)
        
        return {
            'symbol': symbol,
            'price': price,
            'open': float(quote.get('02. open', 0)),
            'high': float(quote.get('03. high', 0)),
            'low': float(quote.get('04. low', 0)),
            'volume': int(quote.get('06. volume', 0)),
            'prev_close': prev_close,
            'change_percent': change_percent,
            'source': 'alphavantage'
        }
    except Exception as e:
        print(f"Alpha Vantage error for {symbol}: {e}")
        return None


@cache_response(ttl=3600)  # Cache for 1 hour
def get_alphavantage_overview(symbol):
    """Get company overview from Alpha Vantage"""
    if not ALPHAVANTAGE_API_KEY:
        return None
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol,
            'apikey': ALPHAVANTAGE_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if not data or 'Symbol' not in data:
            return None
        
        return {
            'symbol': symbol,
            'name': data.get('Name'),
            'market_cap': int(data.get('MarketCapitalization', 0)),
            'shares_float': int(float(data.get('SharesFloat', 0))),
            'sector': data.get('Sector'),
            'industry': data.get('Industry'),
            'exchange': data.get('Exchange'),
            'source': 'alphavantage'
        }
    except Exception as e:
        print(f"Alpha Vantage overview error for {symbol}: {e}")
        return None


# ============================================
# FINNHUB DATA SOURCE
# Free tier: 60 API calls/minute
# ============================================

def get_finnhub_quote(symbol):
    """Get current quote from Finnhub"""
    if not FINNHUB_API_KEY:
        return None
    
    try:
        url = "https://finnhub.io/api/v1/quote"
        params = {
            'symbol': symbol,
            'token': FINNHUB_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if not data or data.get('c') == 0:
            return None
        
        price = data.get('c')  # current price
        prev_close = data.get('pc')  # previous close
        change_percent = None
        
        if price and prev_close and prev_close != 0:
            change_percent = round(((price - prev_close) / prev_close) * 100, 4)
        
        return {
            'symbol': symbol,
            'price': price,
            'open': data.get('o'),
            'high': data.get('h'),
            'low': data.get('l'),
            'prev_close': prev_close,
            'change_percent': change_percent,
            'timestamp': data.get('t'),
            'source': 'finnhub'
        }
    except Exception as e:
        print(f"Finnhub error for {symbol}: {e}")
        return None


def get_finnhub_profile(symbol):
    """Get company profile from Finnhub"""
    if not FINNHUB_API_KEY:
        return None
    
    try:
        url = "https://finnhub.io/api/v1/stock/profile2"
        params = {
            'symbol': symbol,
            'token': FINNHUB_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if not data or 'ticker' not in data:
            return None
        
        return {
            'symbol': symbol,
            'name': data.get('name'),
            'market_cap': int(data.get('marketCapitalization', 0) * 1_000_000),  # Convert from millions
            'shares_outstanding': int(data.get('shareOutstanding', 0) * 1_000_000),
            'exchange': data.get('exchange'),
            'industry': data.get('finnhubIndustry'),
            'source': 'finnhub'
        }
    except Exception as e:
        print(f"Finnhub profile error for {symbol}: {e}")
        return None


# ============================================
# UNIFIED DATA AGGREGATION
# ============================================

def get_stock_data(symbol):
    """
    Get complete stock data using best available source
    Priority: Finnhub (best free tier) -> Polygon -> Alpha Vantage
    """
    symbol = symbol.upper()
    
    # Try Finnhub first (60 calls/min - best for MVP)
    quote = get_finnhub_quote(symbol)
    profile = get_finnhub_profile(symbol)
    
    # Fallback to Polygon if Finnhub fails
    if not quote:
        quote = get_polygon_quote(symbol)
        if not profile:
            profile = get_polygon_stock_details(symbol)
    
    # Fallback to Alpha Vantage (save this for last - only 25 calls/day)
    if not quote:
        quote = get_alphavantage_quote(symbol)
        if not profile:
            profile = get_alphavantage_overview(symbol)
    
    if not quote:
        return None
    
    # Merge quote and profile data
    result = {**quote}
    
    if profile:
        result.update({
            'name': profile.get('name') or result.get('name'),
            'market_cap': profile.get('market_cap') or result.get('market_cap'),
            'shares_float': profile.get('shares_float') or profile.get('shares_outstanding'),
            'sector': profile.get('sector'),
            'industry': profile.get('industry'),
            'exchange': profile.get('exchange')
        })
    
    # Calculate relative volume if we have historical data
    if result.get('volume'):
        # For MVP, we'll calculate RVOL in the sync job using historical averages
        result['relative_volume'] = None
    
    return result


def get_historical_data(symbol):
    """
    Get historical data for breakout detection
    Uses Polygon aggregates (free tier)
    """
    if not POLYGON_API_KEY:
        return None
    
    try:
        symbol = symbol.upper()
        
        # Get 1 year of daily data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'apiKey': POLYGON_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if data.get('status') != 'OK' or not data.get('results'):
            return None
        
        results = data['results']
        
        # Calculate key levels
        highs = [r['h'] for r in results]
        lows = [r['l'] for r in results]
        volumes = [r['v'] for r in results]
        
        high_52w = max(highs) if highs else None
        low_52w = min(lows) if lows else None
        
        # Last 20 days
        high_20d = max(highs[-20:]) if len(highs) >= 20 else None
        
        # Last 50 days
        high_50d = max(highs[-50:]) if len(highs) >= 50 else None
        
        # Average volume (last 20 days)
        avg_volume_20d = int(sum(volumes[-20:]) / 20) if len(volumes) >= 20 else None
        
        return {
            'symbol': symbol,
            'high_52w': high_52w,
            'low_52w': low_52w,
            'high_20d': high_20d,
            'high_50d': high_50d,
            'avg_volume_20d': avg_volume_20d,
            'source': 'polygon'
        }
    except Exception as e:
        print(f"Historical data error for {symbol}: {e}")
        return None


# ============================================
# API ENDPOINTS
# ============================================

@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'version': '3.0',
        'data_sources': {
            'polygon': bool(POLYGON_API_KEY),
            'alphavantage': bool(ALPHAVANTAGE_API_KEY),
            'finnhub': bool(FINNHUB_API_KEY)
        },
        'endpoints': {
            '/quote': 'GET - Current quotes (max 50 symbols)',
            '/historical': 'GET - Historical data for single symbol',
            '/batch-historical': 'POST - Historical data for multiple symbols (max 25)',
            '/complete': 'POST - Complete data (quote + historical) (max 10)',
            '/health': 'GET - Health check'
        }
    })


@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'api_keys_configured': {
            'polygon': bool(POLYGON_API_KEY),
            'alphavantage': bool(ALPHAVANTAGE_API_KEY),
            'finnhub': bool(FINNHUB_API_KEY)
        }
    })


@app.route('/quote', methods=['GET'])
def get_quote():
    """
    Get quotes for multiple symbols
    Usage: /quote?symbols=AAPL,MSFT,GOOGL
    Max: 50 symbols per request (reduced for free tier APIs)
    """
    symbols_param = request.args.get('symbols', '')
    
    if not symbols_param:
        return jsonify({'error': 'Missing symbols parameter'}), 400
    
    symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
    
    if not symbols:
        return jsonify({'error': 'No valid symbols provided'}), 400
    
    if len(symbols) > 50:
        return jsonify({'error': 'Maximum 50 symbols per request'}), 400
    
    results = []
    errors = []
    
    for symbol in symbols:
        data = get_stock_data(symbol)
        if data:
            results.append(data)
        else:
            errors.append(symbol)
        
        # Small delay to avoid rate limits
        time.sleep(0.1)
    
    response = {
        'success': True,
        'count': len(results),
        'data': results,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if errors:
        response['errors'] = {
            'count': len(errors),
            'symbols': errors
        }
    
    return jsonify(response)


@app.route('/historical', methods=['GET'])
def get_historical():
    """
    Get historical data for a single symbol
    Usage: /historical?symbol=AAPL
    """
    symbol = request.args.get('symbol', '').upper().strip()
    
    if not symbol:
        return jsonify({'error': 'Missing symbol parameter'}), 400
    
    data = get_historical_data(symbol)
    
    if not data:
        return jsonify({'error': f'No historical data found for {symbol}'}), 404
    
    return jsonify({
        'success': True,
        'data': data,
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/batch-historical', methods=['POST'])
def batch_historical():
    """
    Get historical data for multiple symbols
    Usage: POST /batch-historical
    Body: {"symbols": ["AAPL", "MSFT", "GOOGL"]}
    Max: 25 symbols per request (Polygon free tier limit)
    """
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    symbols = data.get('symbols', [])
    
    if not symbols or not isinstance(symbols, list):
        return jsonify({'error': 'Invalid symbols array'}), 400
    
    symbols = [s.strip().upper() for s in symbols if isinstance(s, str) and s.strip()]
    
    if not symbols:
        return jsonify({'error': 'No valid symbols provided'}), 400
    
    if len(symbols) > 25:
        return jsonify({'error': 'Maximum 25 symbols per request'}), 400
    
    results = []
    errors = []
    
    for symbol in symbols:
        historical = get_historical_data(symbol)
        if historical:
            results.append(historical)
        else:
            errors.append(symbol)
        
        # Delay for rate limiting (Polygon: 5 calls/min)
        time.sleep(12)  # 12 seconds = 5 calls/minute
    
    response = {
        'success': True,
        'count': len(results),
        'data': results,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if errors:
        response['errors'] = {
            'count': len(errors),
            'symbols': errors
        }
    
    return jsonify(response)


@app.route('/complete', methods=['POST'])
def get_complete():
    """
    Get complete data (quote + historical) for multiple symbols
    Usage: POST /complete
    Body: {"symbols": ["AAPL", "MSFT"]}
    Max: 10 symbols per request (very rate-limited)
    """
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    symbols = data.get('symbols', [])
    
    if not symbols or not isinstance(symbols, list):
        return jsonify({'error': 'Invalid symbols array'}), 400
    
    symbols = [s.strip().upper() for s in symbols if isinstance(s, str) and s.strip()]
    
    if not symbols:
        return jsonify({'error': 'No valid symbols provided'}), 400
    
    if len(symbols) > 10:
        return jsonify({'error': 'Maximum 10 symbols per request'}), 400
    
    results = []
    errors = []
    
    for symbol in symbols:
        try:
            quote = get_stock_data(symbol)
            historical = get_historical_data(symbol)
            
            if quote:
                complete_data = {**quote}
                if historical:
                    complete_data.update({
                        'high_52w': historical['high_52w'],
                        'low_52w': historical['low_52w'],
                        'high_20d': historical['high_20d'],
                        'high_50d': historical['high_50d'],
                        'avg_volume_20d': historical['avg_volume_20d'],
                    })
                results.append(complete_data)
            else:
                errors.append(symbol)
            
            # Rate limiting
            time.sleep(15)  # Be conservative
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            errors.append(symbol)
    
    response = {
        'success': True,
        'count': len(results),
        'data': results,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if errors:
        response['errors'] = {
            'count': len(errors),
            'symbols': errors
        }
    
    return jsonify(response)


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


#Commented out for Vercel deployment
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)