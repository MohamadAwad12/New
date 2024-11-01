# Initialize eventlet monkey patch before other imports
import eventlet
eventlet.monkey_patch()

import os
import time
import logging
import requests
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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
        'holdings': 166344.74

    },
    'GME': {
        'address': '8wXtPeU6557ETkp9WHFY1n1EcU6NxDvbAggHGsMYiHsB',
        'holdings': 14943435.79

    },
    'USA': {
        'address': '69kdRLyP5DTRkpHraaSZAQbWmAwzF9guKjZfzMXzcbAs',
        'holdings': 117594077307.36
    }
}

class PriceTracker:
    @staticmethod
    def get_token_price(token_address):
        """
        Fetch token price from DEX Screener with retry mechanism
        
        Args:
            token_address (str): The token address to fetch price for
            
        Returns:
            dict: Token price and market data
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

        logger.info(f"Fetching price for {token_address}")

        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()

                data = response.json()
                if not data.get('pairs'):
                    logger.error(f"No pairs found for {token_address}")
                    return default_response

                # Prioritize Raydium pairs, otherwise take the first pair
                pairs = data['pairs']
                pair = next(
                    (p for p in pairs if p['dexId'] == 'raydium'),
                    pairs[0] if pairs else None
                )

                if not pair:
                    logger.error(f"No valid pair found for {token_address}")
                    return default_response

                price = float(pair['priceUsd'])
                logger.info(f"Price found for {token_address}: ${price:.8f}")

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
                logger.error(f"Request error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return default_response

            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return default_response

    @staticmethod
    def update_prices():
        """
        Continuous price update loop for all tokens
        """
        while True:
            try:
                prices = {}
                total_value = 0

                for token_name, token_info in TOKENS.items():
                    try:
                        address = token_info['address']
                        holdings = token_info['holdings']

                        market_data = PriceTracker.get_token_price(address)
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

                        logger.info(f"{token_name}: Price=${price:.8f}, Value=${value:.2f}")

                    except Exception as e:
                        logger.error(f"Error processing {token_name}: {str(e)}")
                        continue

                market_data = {
                    'prices': prices,
                    'total_value': total_value
                }

                logger.info(f"Broadcasting update to clients. Total value: ${total_value:.2f}")
                socketio.emit('price_update', market_data)

            except Exception as e:
                logger.error(f"Update loop error: {str(e)}")

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
    logger.info('Client connected')
    emit('status', {'message': 'Connected to price feed'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

def initialize_app():
    """Initialize the application and start the price tracker"""
    try:
        logger.info("Initializing price tracker...")
        
        # Start price update thread
        price_thread = Thread(target=PriceTracker.update_prices)
        price_thread.daemon = True
        price_thread.start()
        
        logger.info("Price tracker initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        return False

if __name__ == '__main__':
    # Initialize the application
    if initialize_app():
        # Get port from environment variable or use default
        port = int(os.environ.get('PORT', 5000))
        
        # Run the application
        logger.info(f"Starting server on port {port}")
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False
        )
    else:
        logger.error("Application failed to initialize")
