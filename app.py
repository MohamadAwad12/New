# Initialize eventlet monkey patch before other imports
import eventlet
eventlet.monkey_patch()

import os
import time
import logging
import requests
import json
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from threading import Thread
from datetime import datetime

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

# Token configuration
TOKENS = {
    'PONKE': {
        'address': '5z3EqYQo9HiCEs3R84RCDMu2n7anpDMxRhdK8PSWmrRC',
        'holdings': 1000000
    },
    'GME': {
        'address': '8wXtPeU6557ETkp9WHFY1n1EcU6NxDvbAggHGsMYiHsB',
        'holdings': 1000000
    },
    'USA': {
        'address': '69kdRLyP5DTRkpHraaSZAQbWmAwzF9guKjZfzMXzcbAs',
        'holdings': 1000000
    }
}

class PriceTracker:
    @staticmethod
    def get_token_price(token_address):
        """
        Fetch token price from DEX Screener with enhanced error handling and logging
        """
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        max_retries = 3
        retry_delay = 1
        default_response = {
            'price': 0,
            'priceChange24h': 0,
            'volume24h': 0,
            'liquidity': 0,
            'fdv': 0,
            'dexId': 'unknown',
            'pairAddress': ''
        }

        logger.info(f"[{datetime.now()}] Attempting to fetch price for {token_address}")

        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        for attempt in range(max_retries):
            try:
                logger.debug(f"[{datetime.now()}] Attempt {attempt + 1} for {token_address}")
                
                response = session.get(url, timeout=15)
                logger.debug(f"[{datetime.now()}] Response status: {response.status_code}")
                logger.debug(f"[{datetime.now()}] Response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                
                data = response.json()
                logger.debug(f"[{datetime.now()}] Response data: {json.dumps(data)[:500]}...")  # Log first 500 chars

                if not data.get('pairs'):
                    logger.error(f"[{datetime.now()}] No pairs found for {token_address}")
                    logger.debug(f"Full response: {json.dumps(data)}")
                    return default_response

                # Prioritize Raydium pairs
                pairs = data['pairs']
                raydium_pairs = [p for p in pairs if p['dexId'] == 'raydium']
                
                if raydium_pairs:
                    pair = raydium_pairs[0]
                    logger.info(f"[{datetime.now()}] Found Raydium pair for {token_address}")
                elif pairs:
                    pair = pairs[0]
                    logger.info(f"[{datetime.now()}] Using first available pair for {token_address}")
                else:
                    logger.error(f"[{datetime.now()}] No valid pairs found for {token_address}")
                    return default_response

                price = float(pair['priceUsd'])
                logger.info(f"[{datetime.now()}] Successfully fetched price for {token_address}: ${price:.8f}")

                return {
                    'price': price,
                    'priceChange24h': float(pair.get('priceChange', {}).get('h24', 0)),
                    'volume24h': float(pair.get('volume', {}).get('h24', 0)),
                    'liquidity': float(pair.get('liquidity', {}).get('usd', 0)),
                    'fdv': float(pair.get('fdv', 0)),
                    'dexId': pair.get('dexId', ''),
                    'pairAddress': pair.get('pairAddress', '')
                }

            except requests.exceptions.RequestException as e:
                logger.error(f"[{datetime.now()}] Request error on attempt {attempt + 1}/{max_retries} for {token_address}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"[{datetime.now()}] Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return default_response

            except json.JSONDecodeError as e:
                logger.error(f"[{datetime.now()}] JSON decode error for {token_address}: {str(e)}")
                logger.debug(f"Raw response content: {response.text[:500]}...")  # Log first 500 chars
                return default_response

            except Exception as e:
                logger.error(f"[{datetime.now()}] Unexpected error for {token_address}: {str(e)}")
                logger.exception("Detailed traceback:")
                return default_response

    @staticmethod
    def update_prices():
        """
        Continuous price update loop with enhanced error handling
        """
        while True:
            try:
                logger.debug(f"[{datetime.now()}] Starting price update cycle")
                prices = {}
                total_value = 0
                update_successful = False

                for token_name, token_info in TOKENS.items():
                    try:
                        address = token_info['address']
                        holdings = token_info['holdings']

                        logger.info(f"[{datetime.now()}] Fetching data for {token_name}")
                        market_data = PriceTracker.get_token_price(address)
                        
                        if market_data['price'] > 0:
                            update_successful = True
                        
                        price = market_data['price']
                        value = price * holdings
                        total_value += value

                        prices[token_name] = {
                            'price': price,
                            'holdings': holdings,
                            'value': value,
                            'priceChange24h': market_data['priceChange24h'],
                            'volume24h': market_data['volume24h'],
                            'liquidity': market_data['liquidity'],
                            'fdv': market_data['fdv'],
                            'dexId': market_data['dexId'],
                            'pairAddress': market_data['pairAddress'],
                            'timestamp': time.time()
                        }

                        logger.info(f"[{datetime.now()}] {token_name}: Price=${price:.8f}, Value=${value:.2f}")

                    except Exception as e:
                        logger.error(f"[{datetime.now()}] Error processing {token_name}: {str(e)}")
                        logger.exception("Detailed traceback:")
                        continue

                if update_successful:
                    market_data = {
                        'prices': prices,
                        'total_value': total_value
                    }

                    logger.info(f"[{datetime.now()}] Broadcasting update. Total value: ${total_value:.2f}")
                    socketio.emit('price_update', market_data)
                else:
                    logger.error(f"[{datetime.now()}] No valid prices fetched in this cycle")

            except Exception as e:
                logger.error(f"[{datetime.now()}] Update loop error: {str(e)}")
                logger.exception("Detailed traceback:")

            finally:
                time.sleep(3)  # Price update interval

# Route handlers
@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

# Socket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"[{datetime.now()}] Client connected from {request.remote_addr}")
    emit('status', {'message': 'Connected to price feed'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"[{datetime.now()}] Client disconnected")

def initialize_app():
    """Initialize the application and start the price tracker"""
    try:
        logger.info(f"[{datetime.now()}] Initializing price tracker...")
        
        # Start price update thread
        price_thread = Thread(target=PriceTracker.update_prices)
        price_thread.daemon = True
        price_thread.start()
        
        logger.info(f"[{datetime.now()}] Price tracker initialized successfully")
        return True
    except Exception as e:
        logger.error(f"[{datetime.now()}] Failed to initialize application: {str(e)}")
        logger.exception("Detailed traceback:")
        return False

if __name__ == '__main__':
    # Initialize the application
    if initialize_app():
        # Get port from environment variable or use default
        port = int(os.environ.get('PORT', 5000))
        
        # Run the application
        logger.info(f"[{datetime.now()}] Starting server on port {port}")
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False
        )
    else:
        logger.error(f"[{datetime.now()}] Application failed to initialize")
