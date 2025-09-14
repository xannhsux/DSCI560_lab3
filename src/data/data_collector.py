from curses import longname
import yfinance as yf
import pandas as pd
import csv
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Union
from database.db_connection import DatabaseConnection
import os

class DataCollector:
    """
    Enhanced data collector for Yahoo Finance API with flexible date/period options
    """
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.data_cache = {}  # Cache for recently fetched data
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests
    
    def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            print(f"Rate limiting: waiting {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def get_stock_info(self, symbol: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Get comprehensive stock information including fundamentals with retry logic
        
        Args:
            symbol: Stock ticker symbol
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with stock information or None if error
        """
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
                ticker = yf.Ticker(symbol)
                info = ticker.info
                print(f"Info retrieved for {symbol} /n {info.get(longname)}")
                
                return {
                    'symbol': symbol,
                    'name': info.get('longName', 'N/A'),
                    'displayName': info.get('displayName', info.get('shortName', 'N/A')),
                    'exchange': info.get('exchange', 'N/A'),
                    'sector': info.get('sector', 'N/A'),
                    'industry': info.get('industry', 'N/A'),
                    'market_cap': info.get('marketCap'),
                    'current_price': info.get('currentPrice', info.get('regularMarketPrice')),
                    'previous_close': info.get('previousClose', info.get('regularMarketPreviousClose')),
                    'volume': info.get('volume', info.get('regularMarketVolume')),
                    'average_volume': info.get('averageVolume'),
                    'pe_ratio': info.get('trailingPE'),
                    'dividend_yield': info.get('dividendYield'),
                    'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                    'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                    'beta': info.get('beta'),
                    'eps': info.get('trailingEps', info.get('epsTrailingTwelveMonths')),
                    'book_value': info.get('bookValue'),
                    'price_to_book': info.get('priceToBook'),
                    'forward_pe': info.get('forwardPE'),
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
                    'analyst_count': info.get('numberOfAnalystOpinions', 0)
                }
                
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                    print(f"Rate limit hit on attempt {attempt + 1}/{max_retries}. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Error fetching info for {symbol}: {str(e)}")
                    if attempt < max_retries - 1:
                        print(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                        time.sleep(1)
                        continue
                    else:
                        return None
        
        print(f"Failed to fetch {symbol} after {max_retries} attempts")
        return None
    
    def get_historical_data(
                            self, 
                            symbol: str, 
                            period: str = '1y', 
                            interval: str = '1d', start: Optional[str] = None, 
                            end: Optional[str] = None
                            ) -> Optional[pd.DataFrame]:
        """
        Get historical price data with flexible date/period options
        
        Parameters:
        - symbol: Stock ticker symbol
        - period: Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max (use this OR start/end)
        - interval: Valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
        - start: Start date (string 'YYYY-MM-DD' or datetime object)
        - end: End date (string 'YYYY-MM-DD' or datetime object)
        
        Examples:
        - get_historical_data('AAPL', period='1y')
        - get_historical_data('AAPL', start='2024-01-01', end='2024-12-31')
        - get_historical_data('AAPL', start=datetime(2024,1,1), end=datetime(2024,12,31))
        
        Returns:
            DataFrame with historical data or None if error
        """
        try:
            self._rate_limit()
            
            ticker = yf.Ticker(symbol)
            
            # Use either period OR date range
            if start is not None or end is not None:
                hist = ticker.history(start=start, end=end, interval=interval)
            elif period is not None:
                hist = ticker.history(period=period, interval=interval)
            else:
                # Default to 1 year if nothing specified
                hist = ticker.history(period='1y', interval=interval)
            
            if not hist.empty:
                hist['Symbol'] = symbol
                hist.reset_index(inplace=True)
                self.data_cache[symbol] = hist
                print(f'First 5 entries of price data: {hist.head()}')
                print(f'df info: {hist.info()}')
                return hist
            else:
                print(f"No data found for {symbol}")
                return None
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
    
    def get_multiple_stocks_data(self, symbols: List[str], period: str = '1y', 
                               interval: str = '1d', start: Optional[str] = None, 
                               end: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple stocks
        
        Args:
            symbols: List of stock ticker symbols
            period: Time period for data
            interval: Data interval
            start: Start date
            end: End date
            
        Returns:
            Dictionary of {symbol: DataFrame}
        """
        all_data = {}
        for symbol in symbols:
            print(f"Fetching data for {symbol}...")
            data = self.get_historical_data(symbol, period=period, interval=interval, 
                                           start=start, end=end)
            if data is not None:
                all_data[symbol] = data
                print(f"First 5 entries of price data: {data.head()}")
        return all_data
    
    def get_real_time_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time stock quote (minute-level data)
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with latest quote data or None if error
        """
        try:
            self._rate_limit()
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            
            if not data.empty:
                latest = data.iloc[-1]
                return {
                    'symbol': symbol,
                    'timestamp': data.index[-1],
                    'price': float(latest['Close']),
                    'volume': int(latest['Volume']),
                    'high': float(latest['High']),
                    'low': float(latest['Low']),
                    'open': float(latest['Open'])
                }
            return None
        except Exception as e:
            print(f"Error fetching real-time quote for {symbol}: {str(e)}")
            return None
    
    def fetch_stock_data(self, symbol: str, period: str = '1y', interval: str = '1d') -> bool:
        """
        Fetch and store stock data (both basic info and historical data)
        
        Args:
            symbol: Stock ticker symbol
            period: Time period for historical data
            interval: Data interval
            
        Returns:
            Boolean indicating success
        """
        try:
            # First ensure stock is in database
            if not self.add_stock_to_database(symbol):
                return False
            
            # Get historical data
            historical_data = self.get_historical_data(symbol, period=period, interval=interval)
            if historical_data is None or historical_data.empty:
                print(f"No historical data available for {symbol}")
                return False
            
            # Store historical data
            stock_id = self.get_stock_id_by_symbol(symbol)
            if not stock_id:
                print(f"Could not find stock ID for {symbol}")
                return False
            
            return self._store_historical_data(stock_id, symbol, historical_data)
            
        except Exception as e:
            print(f"Error fetching stock data for {symbol}: {str(e)}")
            return False
    
    def _store_historical_data(self, stock_id: int, symbol: str, df: pd.DataFrame) -> bool:
        """Store historical data in database"""
        try:
            if not self.db.connect():
                print("Failed to connect to database")
                return False
            
            # Prepare data for insertion
            records = []
            for index, row in df.iterrows():
                # Handle different date sources - check if 'Date' column exists first
                try:
                    if 'Date' in df.columns:
                        # Use the Date column value
                        date_val = row['Date']
                    else:
                        # Use the index
                        date_val = index
                    
                    # Convert to proper date format
                    if hasattr(date_val, 'strftime'):
                        date_str = date_val.strftime('%Y-%m-%d')
                    elif hasattr(date_val, 'date'):
                        date_str = date_val.date().strftime('%Y-%m-%d')
                    else:
                        # Convert to pandas Timestamp then to date
                        date_str = pd.to_datetime(date_val).strftime('%Y-%m-%d')
                        
                except Exception as e:
                    print(f"Warning: Could not parse date {date_val}, skipping record: {e}")
                    continue
                
                records.append((
                    stock_id,
                    date_str,
                    float(row.get('Open', 0)),
                    float(row.get('High', 0)),
                    float(row.get('Low', 0)),
                    float(row.get('Close', 0)),
                    float(row.get('Adj Close', row.get('Close', 0))),
                    int(row.get('Volume', 0))
                ))
            
            # Insert historical data
            insert_query = """
            INSERT INTO stock_historical_data 
            (stock_id, date, open_price, high_price, low_price, close_price, adj_close_price, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            open_price = VALUES(open_price),
            high_price = VALUES(high_price),
            low_price = VALUES(low_price),
            close_price = VALUES(close_price),
            adj_close_price = VALUES(adj_close_price),
            volume = VALUES(volume)
            """
            
            for record in records:
                self.db.execute_update(insert_query, record)
            
            print(f"Stored {len(records)} historical records for {symbol}")
            return True
            
        except Exception as e:
            print(f"Error storing historical data for {symbol}: {str(e)}")
            return False
        finally:
            self.db.disconnect()
    
    def add_stock_to_database(self, symbol: str) -> bool:
        """
        Add a stock to the database by fetching info from Yahoo Finance
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Boolean indicating success
        """
        try:
            # Fetch comprehensive stock info from Yahoo Finance
            stock_info = self.get_stock_info(symbol.upper())
            print(f"Stock info retrieved for {symbol}: {stock_info}")
        
            if not stock_info:
                print(f"Could not fetch information for {symbol}")
                return False
            
            # Insert/update stock in database
            insert_query = """
            INSERT INTO stocks
            (symbol, company_name, display_name, sector, exchange)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                company_name = VALUES(company_name),
                display_name = VALUES(display_name),
                sector = VALUES(sector),
                exchange = VALUES(exchange),
                updated_at = CURRENT_TIMESTAMP
            """
            
            params = (
                stock_info['symbol'],
                stock_info['name'],
                stock_info.get('displayName', stock_info['name']),
                stock_info.get('sector', 'Unknown'),
                stock_info.get('exchange', 'Unknown')
            )
            
            result = self.db.execute_update(insert_query, params)
            if result >= 0:  # 0 means updated, >0 means inserted
                print(f" Added/Updated {symbol}: {stock_info['name']}")
                return True
            else:
                print(f" Failed to add {symbol} to database")
                return False
                
        except Exception as e:
            print(f"Error adding {symbol} to database: {e}")
            return False
    
    def add_stocks_from_list(self, symbols: List[str]) -> Dict[str, bool]:
        """
        Add multiple stocks to database from a list of ticker symbols
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary with {symbol: success_status}
        """
        results = {}
        
        print(f"Adding {len(symbols)} stocks to database...")
        print("=" * 50)
        
        for symbol in symbols:
            symbol = symbol.strip().upper()
            if symbol:  # Skip empty symbols
                results[symbol] = self.add_stock_to_database(symbol)
        
        # Summary
        successful = sum(1 for success in results.values() if success)
        failed = len(results) - successful
        
        print("\n" + "=" * 50)
        print(f"Summary: {successful} successful, {failed} failed")
        if failed > 0:
            failed_symbols = [sym for sym, success in results.items() if not success]
            print(f"Failed symbols: {', '.join(failed_symbols)}")
        
        return results
    
    def add_stocks_from_csv(self, csv_file_path: str, symbol_column: str = 'symbol') -> Dict[str, bool]:
        """
        Add stocks to database from a CSV file
        
        Args:
            csv_file_path: Path to CSV file
            symbol_column: Name of column containing ticker symbols
            
        Returns:
            Dictionary with {symbol: success_status}
        """
        if not os.path.exists(csv_file_path):
            print(f"CSV file not found: {csv_file_path}")
            return {}
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_file_path)
            
            if symbol_column not in df.columns:
                print(f"Column '{symbol_column}' not found in CSV. Available columns: {list(df.columns)}")
                return {}
            
            # Extract symbols
            symbols = df[symbol_column].dropna().tolist()
            symbols = [str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()]
            
            print(f"Found {len(symbols)} symbols in CSV file: {csv_file_path}")
            
            # Add stocks to database
            return self.add_stocks_from_list(symbols)
            
        except Exception as e:
            print(f"Error reading CSV file {csv_file_path}: {e}")
            return {}
        
    def get_stock_id_by_symbol(self, symbol: str) -> Optional[int]:
        """
        Get the database stock_id for a given symbol
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Stock ID or None if not found
        """
        try:
            query = "SELECT stock_id FROM stocks WHERE symbol = %s"
            result = self.db.execute_query(query, (symbol.upper(),))
            
            if result and len(result) > 0:
                return result[0][0]  # Return the stock_id
            return None
            
        except Exception as e:
            print(f"Error getting stock ID for {symbol}: {e}")
            return None
    
    def fetch_and_store_stock_data(self, symbol_or_portfolio_id, start_date: Optional[str] = None, 
                                  end_date: Optional[str] = None, period: Optional[str] = None,
                                  interval: str = '1d') -> bool:
        """
        Fetch historical data for all stocks in portfolio and store in database
        
        Args:
            portfolio_id: Portfolio ID
            start_date: Start date (use with end_date)
            end_date: End date (use with start_date)
            period: Period string (alternative to start/end dates)
            interval: Data interval
            
        Returns:
            Boolean indicating success
        """
        # Get all stocks in the portfolio
        query = """
        SELECT s.stock_id, s.symbol 
        FROM stocks s
        JOIN portfolio_holdings ph ON s.stock_id = ph.stock_id
        WHERE ph.portfolio_id = %s
        """
        
        stocks = self.db.execute_query(query, (portfolio_id,))
        
        if not stocks:
            print("No stocks found in portfolio")
            return False

        print(f"Starting to fetch data for {len(stocks)} stocks...")
        
        success_count = 0
        for stock_id, symbol in stocks:
            if self._fetch_and_store_single_stock(stock_id, symbol, start_date, end_date, period, interval):
                success_count += 1
                print(f" {symbol} data fetched and stored successfully")
            else:
                print(f" {symbol} data fetch failed")

        print(f"Completed! Successfully fetched data for {success_count}/{len(stocks)} stocks")
        return success_count > 0
    
    def _fetch_and_store_single_stock(self, stock_id: int, symbol: str, 
                                     start_date: Optional[str] = None, 
                                     end_date: Optional[str] = None, 
                                     period: Optional[str] = None,
                                     interval: str = '1d') -> bool:
        """
        Fetch and store historical data for a single stock
        
        Args:
            stock_id: Database stock ID
            symbol: Stock ticker symbol
            start_date: Start date
            end_date: End date
            period: Period string
            interval: Data interval
            
        Returns:
            Boolean indicating success
        """
        try:
            # Fetch data using the enhanced method
            hist = self.get_historical_data(symbol, period=period, interval=interval,
                                           start=start_date, end=end_date)
            
            if hist is None or hist.empty:
                print(f"Warning: No data found for {symbol}")
                return False
            
            # Store stock info/metadata
            stock_info = self.get_stock_info(symbol)
            if stock_info:
                self._update_stock_metadata(stock_id, stock_info)
            
            # Prepare data for insertion into stock_historical_data table
            insert_query = """
            INSERT INTO stock_historical_data 
            (stock_id, date, open_price, high_price, low_price, close_price, 
             adj_close_price, volume, daily_return)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                open_price = VALUES(open_price),
                high_price = VALUES(high_price),
                low_price = VALUES(low_price),
                close_price = VALUES(close_price),
                adj_close_price = VALUES(adj_close_price),
                volume = VALUES(volume),
                daily_return = VALUES(daily_return)
            """
            
            # Calculate daily returns
            hist['daily_return'] = hist['Close'].pct_change()
            
            inserted_count = 0
            for idx, row in hist.iterrows():
                # Handle Date column properly with better error handling
                try:
                    if 'Date' in hist.columns:
                        date_val = row['Date']
                    else:
                        date_val = idx
                    
                    # Convert to proper date format
                    if hasattr(date_val, 'strftime'):
                        date_str = date_val.strftime('%Y-%m-%d')
                    elif hasattr(date_val, 'date'):
                        date_str = date_val.date().strftime('%Y-%m-%d')
                    else:
                        # Convert to pandas Timestamp then to date
                        date_str = pd.to_datetime(date_val).strftime('%Y-%m-%d')
                        
                except Exception as e:
                    print(f"Warning: Could not parse date {date_val}, skipping record: {e}")
                    continue
                
                params = (
                    stock_id,
                    date_str,
                    float(row['Open']) if pd.notna(row['Open']) else None,
                    float(row['High']) if pd.notna(row['High']) else None,
                    float(row['Low']) if pd.notna(row['Low']) else None,
                    float(row['Close']) if pd.notna(row['Close']) else None,
                    float(row['Close']) if pd.notna(row['Close']) else None,  # Using Close as adj_close for simplicity
                    int(row['Volume']) if pd.notna(row['Volume']) else 0,
                    float(row['daily_return']) if pd.notna(row['daily_return']) else None
                )
                
                result = self.db.execute_update(insert_query, params)
                if result > 0:
                    inserted_count += 1
            
            print(f"  Inserted/Updated {inserted_count} records for {symbol}")
            return True
            
        except Exception as e:
            print(f"Error fetching/storing data for {symbol}: {e}")
            return False
    
    def _update_stock_metadata(self, stock_id: int, stock_info: Dict) -> bool:
        """
        Update comprehensive stock metadata in the database
        
        Args:
            stock_id: Database stock ID
            stock_info: Dictionary with stock information
            
        Returns:
            Boolean indicating success
        """
        try:
            update_query = """
            INSERT INTO stock_metadata 
            (stock_id, market_cap, current_price, previous_close, volume, average_volume,
             pe_ratio, forward_pe, dividend_yield, fifty_two_week_high, fifty_two_week_low,
             beta, eps, book_value, price_to_book, price_to_sales, profit_margins,
             return_on_equity, return_on_assets, debt_to_equity, revenue_growth,
             earnings_growth, recommendation_mean, target_high_price, target_low_price,
             target_mean_price, analyst_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                market_cap = VALUES(market_cap),
                current_price = VALUES(current_price),
                previous_close = VALUES(previous_close),
                volume = VALUES(volume),
                average_volume = VALUES(average_volume),
                pe_ratio = VALUES(pe_ratio),
                forward_pe = VALUES(forward_pe),
                dividend_yield = VALUES(dividend_yield),
                fifty_two_week_high = VALUES(fifty_two_week_high),
                fifty_two_week_low = VALUES(fifty_two_week_low),
                beta = VALUES(beta),
                eps = VALUES(eps),
                book_value = VALUES(book_value),
                price_to_book = VALUES(price_to_book),
                price_to_sales = VALUES(price_to_sales),
                profit_margins = VALUES(profit_margins),
                return_on_equity = VALUES(return_on_equity),
                return_on_assets = VALUES(return_on_assets),
                debt_to_equity = VALUES(debt_to_equity),
                revenue_growth = VALUES(revenue_growth),
                earnings_growth = VALUES(earnings_growth),
                recommendation_mean = VALUES(recommendation_mean),
                target_high_price = VALUES(target_high_price),
                target_low_price = VALUES(target_low_price),
                target_mean_price = VALUES(target_mean_price),
                analyst_count = VALUES(analyst_count),
                updated_at = CURRENT_TIMESTAMP
            """
            
            # Debug: Print what we received from Yahoo Finance
            print(f" Metadata received for stock_id {stock_id}:")
            for key, value in stock_info.items():
                if value not in [None, '', 'N/A', 0]:
                    print(f"   {key}: {value}")
            
            # Helper function to convert missing/invalid values to NULL for database
            def safe_value(val, allow_zero=False):
                if val is None or val == '' or val == 'N/A':
                    return None
                if not allow_zero and val == 0:
                    return None
                try:
                    # Try to convert to float for numeric fields
                    return float(val) if val != 0 or allow_zero else None
                except (ValueError, TypeError):
                    return None
            
            params = (
                stock_id,
                safe_value(stock_info.get('market_cap')),
                safe_value(stock_info.get('current_price')),
                safe_value(stock_info.get('previous_close')),
                safe_value(stock_info.get('volume'), allow_zero=True),  # Volume can be 0
                safe_value(stock_info.get('average_volume')),
                safe_value(stock_info.get('pe_ratio')),
                safe_value(stock_info.get('forward_pe')),
                safe_value(stock_info.get('dividend_yield'), allow_zero=True),  # Dividend yield can be 0
                safe_value(stock_info.get('fifty_two_week_high')),
                safe_value(stock_info.get('fifty_two_week_low')),
                safe_value(stock_info.get('beta')),
                safe_value(stock_info.get('eps')),
                safe_value(stock_info.get('book_value')),
                safe_value(stock_info.get('price_to_book')),
                safe_value(stock_info.get('price_to_sales')),
                safe_value(stock_info.get('profit_margins')),
                safe_value(stock_info.get('return_on_equity')),
                safe_value(stock_info.get('return_on_assets')),
                safe_value(stock_info.get('debt_to_equity'), allow_zero=True),  # Debt-to-equity can be 0
                safe_value(stock_info.get('revenue_growth')),
                safe_value(stock_info.get('earnings_growth')),
                safe_value(stock_info.get('recommendation_mean')),
                safe_value(stock_info.get('target_high_price')),
                safe_value(stock_info.get('target_low_price')),
                safe_value(stock_info.get('target_mean_price')),
                safe_value(stock_info.get('analyst_count'), allow_zero=True)  # Analyst count can be 0
            )
            
            self.db.execute_update(update_query, params)
            return True
            
        except Exception as e:
            print(f"Error updating stock metadata: {e}")
            return False
    
    def get_latest_portfolio_data(self, portfolio_id: int, days: int = 30) -> Dict[str, pd.DataFrame]:
        """
        Get latest data for all stocks in a portfolio
        
        Args:
            portfolio_id: Portfolio ID
            days: Number of days of data to fetch
            
        Returns:
            Dictionary of {symbol: DataFrame}
        """
        # Get all stocks in the portfolio
        query = """
        SELECT s.symbol 
        FROM stocks s
        JOIN portfolio_holdings ph ON s.stock_id = ph.stock_id
        WHERE ph.portfolio_id = %s
        """
        
        stocks = self.db.execute_query(query, (portfolio_id,))
        
        if not stocks:
            print("No stocks found in portfolio")
            return {}
        
        symbols = [stock[0] for stock in stocks]
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Fetch data for all symbols
        return self.get_multiple_stocks_data(
            symbols, 
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d')
        )


# Example usage
if __name__ == "__main__":
    collector = DataCollector()
    
    # Example 1: Add stocks from ticker list
    tickers = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    results = collector.add_stocks_from_list(tickers)
    print(f"Added {sum(results.values())} stocks successfully")
    
    # Example 2: use sample CSV
    csv_results = collector.add_stocks_from_csv("my_tickers.csv")
    
    # Example 3: Add single stock by ticker
    success = collector.add_stock_to_database('NVDA')
    
    # Example 4: Get data using period
    data = collector.get_historical_data('AAPL', period='1mo')
    if data is not None:
        print(f"Fetched {len(data)} records for AAPL (1 month)")
    
    # Example 5: Get data using specific dates
    data = collector.get_historical_data('GOOGL', start='2024-01-01', end='2024-03-31')
    if data is not None:
        print(f"Fetched {len(data)} records for GOOGL (Q1 2024)")
    
    # Example 6: Get intraday data
    data = collector.get_historical_data('MSFT', period='5d', interval='1h')
    if data is not None:
        print(f"Fetched {len(data)} hourly records for MSFT (5 days)")
    
    # Example 7: Get real-time quote
    quote = collector.get_real_time_quote('TSLA')
    if quote:
        print(f"TSLA current price: ${quote['price']:.2f}")
