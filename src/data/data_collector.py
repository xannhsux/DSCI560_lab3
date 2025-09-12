import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from database.db_connection import DatabaseConnection

class DataCollector:
    def __init__(self):
        self.db = DatabaseConnection()

    def fetch_and_store_stock_data(self, portfolio_id, start_date, end_date):
        """Fetch historical data for all stocks in portfolio and store in database"""
        # Get all stocks in the portfolio
        query = """
        SELECT s.stock_id, s.symbol 
        FROM stocks s
        JOIN portfolio_stocks ps ON s.stock_id = ps.stock_id
        WHERE ps.portfolio_id = %s
        """
        
        stocks = self.db.execute_query(query, (portfolio_id,))
        
        if not stocks:
            print("No stocks found in portfolio")
            return False

        print(f"Starting to fetch data for {len(stocks)} stocks...")
        
        success_count = 0
        for stock_id, symbol in stocks:
            if self._fetch_stock_data(stock_id, symbol, start_date, end_date):
                success_count += 1
                print(f"✓ {symbol} data fetched successfully")
            else:
                print(f"✗ {symbol} data fetch failed")

        print(f"Completed! Successfully fetched data for {success_count}/{len(stocks)} stocks")
        return success_count > 0

    def _fetch_stock_data(self, stock_id, symbol, start_date, end_date):
        """Fetch historical data for a single stock"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                print(f"Warning: No data found for {symbol} in the specified date range")
                return False

            # Prepare data for insertion
            insert_query = """
            INSERT IGNORE INTO stock_prices 
            (stock_id, date, open_price, high_price, low_price, close_price, adjusted_close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            inserted_count = 0
            for date, row in hist.iterrows():
                params = (
                    stock_id,
                    date.date(),
                    float(row['Open']) if pd.notna(row['Open']) else None,
                    float(row['High']) if pd.notna(row['High']) else None,
                    float(row['Low']) if pd.notna(row['Low']) else None,
                    float(row['Close']) if pd.notna(row['Close']) else None,
                    float(row['Close']) if pd.notna(row['Close']) else None,  # Simplified handling
                    int(row['Volume']) if pd.notna(row['Volume']) else 0
                )
                
                result = self.db.execute_update(insert_query, params)
                if result > 0:
                    inserted_count += 1

            print(f"  Inserted {inserted_count} data records for {symbol}")
            return True

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return False

    def get_latest_data(self, symbol, days=30):
        """Get latest stock data for quick analysis"""
        try:
            ticker = yf.Ticker(symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            hist = ticker.history(start=start_date, end=end_date)
            return hist
            
        except Exception as e:
            print(f"Error getting latest data for {symbol}: {e}")
            return None