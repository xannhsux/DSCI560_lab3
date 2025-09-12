import yfinance as yf

class StockValidator:
    def __init__(self):
        pass

    def validate_stock(self, symbol):
        """Validate if stock symbol is valid"""
        try:
            ticker = yf.Ticker(symbol)
            # Try to get basic info to verify stock exists
            info = ticker.info
            
            # Check if we have valid data
            if 'regularMarketPrice' in info or 'currentPrice' in info:
                return True
            elif info.get('longName') or info.get('shortName'):
                return True
            else:
                # Try to get historical data as final verification
                hist = ticker.history(period="1d")
                return not hist.empty
                
        except Exception as e:
            print(f"Error validating stock '{symbol}': {e}")
            return False

    def get_stock_info(self, symbol):
        """Get detailed stock information"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'name': info.get('longName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'current_price': info.get('currentPrice', 'N/A'),
                'market_cap': info.get('marketCap', 'N/A'),
                'pe_ratio': info.get('trailingPE', 'N/A')
            }
        except Exception as e:
            print(f"Error getting stock info for '{symbol}': {e}")
            return None