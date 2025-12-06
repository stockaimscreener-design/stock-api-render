from flask import Flask, jsonify, request
import yfinance as yf
from flask_cors import CORS
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_stock_data(symbol):
    """Fetch current quote data for a single symbol"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if not price:
            return None
        
        volume = info.get('volume') or info.get('regularMarketVolume')
        avg_volume = info.get('averageDailyVolume10Day') or info.get('averageVolume10days')
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
            'prev_close': prev_close,
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'exchange': info.get('exchange'),
        }
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return None


def get_historical_data(symbol):
    """Fetch historical data for breakout detection"""
    try:
        ticker = yf.Ticker(symbol)
        
        # Get 1 year of historical data
        hist = ticker.history(period="1y")
        
        if hist.empty:
            return None
        
        # Calculate key levels
        high_52w = float(hist['High'].max())
        low_52w = float(hist['Low'].min())
        
        # Last 20 trading days high
        high_20d = float(hist['High'].tail(20).max()) if len(hist) >= 20 else None
        
        # Last 50 trading days high  
        high_50d = float(hist['High'].tail(50).max()) if len(hist) >= 50 else None
        
        # Calculate average volume (last 20 days)
        avg_volume_20d = int(hist['Volume'].tail(20).mean()) if len(hist) >= 20 else None
        
        return {
            'symbol': symbol,
            'high_52w': high_52w,
            'low_52w': low_52w,
            'high_20d': high_20d,
            'high_50d': high_50d,
            'avg_volume_20d': avg_volume_20d,
        }
    except Exception as e:
        logger.error(f"Error fetching historical for {symbol}: {e}")
        return None


@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'version': '2.0',
        'endpoints': {
            '/quote': 'GET - Current quotes (max 100 symbols)',
            '/historical': 'GET - Historical data for single symbol',
            '/batch-historical': 'POST - Historical data for multiple symbols (max 50)',
            '/complete': 'POST - Complete data (quote + historical) for multiple symbols',
            '/health': 'GET - Health check'
        }
    })


@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/quote', methods=['GET'])
def get_quote():
    """
    Get current quotes for multiple symbols
    Usage: /quote?symbols=AAPL,MSFT,GOOGL
    Max: 100 symbols per request
    """
    symbols_param = request.args.get('symbols', '')
    
    if not symbols_param:
        return jsonify({'error': 'Missing symbols parameter'}), 400
    
    symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
    
    if not symbols:
        return jsonify({'error': 'No valid symbols provided'}), 400
    
    if len(symbols) > 100:
        return jsonify({'error': 'Maximum 100 symbols per request'}), 400
    
    results = []
    errors = []
    
    for symbol in symbols:
        data = get_stock_data(symbol)
        if data:
            results.append(data)
        else:
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


@app.route('/historical', methods=['GET'])
def get_historical():
    """
    Get historical data for a single symbol
    Usage: /historical?symbol=AAPL
    Returns: 52W high/low, 20D high, 50D high, avg volume
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
    Max: 50 symbols per request (historical data is slower)
    """
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    symbols = data.get('symbols', [])
    
    if not symbols:
        return jsonify({'error': 'Missing symbols array'}), 400
    
    if not isinstance(symbols, list):
        return jsonify({'error': 'Symbols must be an array'}), 400
    
    # Clean and validate symbols
    symbols = [s.strip().upper() for s in symbols if isinstance(s, str) and s.strip()]
    
    if not symbols:
        return jsonify({'error': 'No valid symbols provided'}), 400
    
    if len(symbols) > 50:
        return jsonify({'error': 'Maximum 50 symbols per request'}), 400
    
    results = []
    errors = []
    
    for symbol in symbols:
        historical = get_historical_data(symbol)
        if historical:
            results.append(historical)
        else:
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


@app.route('/complete', methods=['POST'])
def get_complete():
    """
    Get complete data (current quote + historical) for multiple symbols
    Usage: POST /complete
    Body: {"symbols": ["AAPL", "MSFT"]}
    Max: 25 symbols per request (this is data-intensive)
    
    This is useful for initial universe population or full refreshes
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
        try:
            # Get both quote and historical data
            quote = get_stock_data(symbol)
            historical = get_historical_data(symbol)
            
            if quote:
                # Merge data
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
                
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
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


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# Commented out to prevent auto-execution during imports and vercel deployments
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)