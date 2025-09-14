import yfinance as yf
import time

class StockValidator:
    def __init__(self):
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests

    def validate_stock(self, symbol, max_retries: int = 3):
        """Validate if stock symbol is valid with rate limiting"""
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
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
                if "429" in str(e) or "Too Many Requests" in str(e):
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Rate limit hit validating {symbol}. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Error validating stock '{symbol}': {e}")
                    if attempt < max_retries - 1:
                        print(f"Retrying validation... (attempt {attempt + 2}/{max_retries})")
                        time.sleep(1)
                        continue
                    else:
                        return False
        
        print(f"Failed to validate {symbol} after {max_retries} attempts")
        return False

    def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            print(f"Rate limiting: waiting {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def get_stock_info(self, symbol, max_retries: int = 3):
        """Get detailed stock information with rate limiting"""
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Return all metadata fields that match the database schema
                return {
                    'symbol': symbol,
                    'name': info.get('longName', 'N/A'),
                    'sector': info.get('sector', 'N/A'),
                    'market_cap': info.get('marketCap'),
                    'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                    'previous_close': info.get('previousClose'),
                    'volume': info.get('volume') or info.get('regularMarketVolume'),
                    'average_volume': info.get('averageVolume'),
                    'pe_ratio': info.get('trailingPE'),
                    'forward_pe': info.get('forwardPE'),
                    'dividend_yield': info.get('dividendYield'),
                    'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                    'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                    'beta': info.get('beta'),
                    'eps': info.get('epsTrailingTwelveMonths') or info.get('trailingEps'),
                    'book_value': info.get('bookValue'),
                    'price_to_book': info.get('priceToBook'),
                    'price_to_sales': info.get('priceToSalesTrailing12Months'),
                    'profit_margins': info.get('profitMargins'),
                    'return_on_equity': info.get('returnOnEquity'),
                    'return_on_assets': info.get('returnOnAssets'),
                    'debt_to_equity': info.get('debtToEquity'),
                    'revenue_growth': info.get('revenueGrowth'),
                    'earnings_growth': info.get('earningsGrowth'),
                    'recommendation_mean': info.get('recommendationMean'),
                    'target_high_price': info.get('targetHighPrice'),
                    'target_low_price': info.get('targetLowPrice'),
                    'target_mean_price': info.get('targetMeanPrice'),
                    'analyst_count': info.get('numberOfAnalystOpinions')
                }
                
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                    print(f"Rate limit hit on attempt {attempt + 1}/{max_retries}. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Error getting stock info for '{symbol}': {e}")
                    if attempt < max_retries - 1:
                        print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                        time.sleep(1)
                        continue
                    else:
                        return None
        
        print(f"Failed to get info for {symbol} after {max_retries} attempts")
        return None