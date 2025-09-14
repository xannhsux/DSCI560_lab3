"""
Data Preprocessor Module for Stock Market Analysis
Handles data cleaning, validation, and feature engineering for Yahoo Finance data
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Preprocessor for stock market data with focus on:
    1. Data validation and error checking
    2. Missing data handling (forward fill)
    3. Daily returns calculation
    4. Feature engineering for analysis
    """
    
    def __init__(self):
        pass  # Yahoo Finance data is assumed to be correct
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate RSI (Relative Strength Index)
        
        Args:
            prices: Series of prices
            period: Period for RSI calculation (default 14)
            
        Returns:
            Series of RSI values
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
        
    def validate_dataframe(self, df: pd.DataFrame, symbol: str) -> Tuple[bool, List[str]]:
        """
        Validate that dataframe has required columns and reasonable data
        
        Args:
            df: DataFrame to validate
            symbol: Stock symbol for logging
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        
        # Check if dataframe is empty
        if df.empty:
            issues.append(f"{symbol}: DataFrame is empty")
            return False, issues
        
        # Check for required columns
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            issues.append(f"{symbol}: Missing columns: {missing_columns}")
            return False, issues
        
        # Check for minimum number of records
        if len(df) < 2:
            issues.append(f"{symbol}: Insufficient data (only {len(df)} records)")
            return False, issues
        
        
        # Check data recency
        df['Date'] = pd.to_datetime(df['Date'])
        last_date = df['Date'].max()
        days_old = (datetime.now() - last_date).days
        if days_old > 30:
            issues.append(f"{symbol}: Data is {days_old} days old")
        
        return len(issues) == 0, issues
    
    def handle_missing_data(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Handle missing data with forward filling strategy
        
        Args:
            df: DataFrame with potential missing data
            symbol: Stock symbol for logging
            
        Returns:
            DataFrame with missing data handled
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Ensure Date column is datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Sort by date
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Forward fill price data (carry forward last known price)
        price_columns = ['Open', 'High', 'Low', 'Close']
        if 'Adj Close' in df.columns:
            price_columns.append('Adj Close')
        
        for col in price_columns:
            if col in df.columns:
                # Count missing values before filling
                missing_before = df[col].isna().sum()
                if missing_before > 0:
                    logger.info(f"{symbol}: Forward filling {missing_before} missing values in {col}")
                
                # Forward fill then backward fill (for any missing at the start)
                df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
        
        # Handle volume separately (missing volume = 0)
        if 'Volume' in df.columns:
            volume_missing = df['Volume'].isna().sum()
            if volume_missing > 0:
                logger.info(f"{symbol}: Setting {volume_missing} missing volume values to 0")
                df['Volume'] = df['Volume'].fillna(0)
        
        # Check if we still have any NaN values
        remaining_nan = df.isna().sum().sum()
        if remaining_nan > 0:
            logger.warning(f"{symbol}: {remaining_nan} NaN values remain after preprocessing")
        
        return df
    
    def calculate_returns(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Calculate various return metrics for analysis
        
        Args:
            df: DataFrame with price data
            symbol: Stock symbol for logging
            
        Returns:
            DataFrame with return columns added
        """
        if df.empty or len(df) < 2:
            return df
        
        df = df.copy()
        
        # Ensure Date column is datetime and sort
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Calculate daily returns (percentage)
        df['daily_return'] = df['Close'].pct_change() * 100
        
        # Calculate log returns (better for statistical analysis)
        df['log_return'] = np.log(df['Close'] / df['Close'].shift(1))
        
        # Calculate cumulative returns
        df['cumulative_return'] = (1 + df['daily_return']/100).cumprod() - 1
        
        # Calculate intraday return (close vs open)
        df['intraday_return'] = ((df['Close'] - df['Open']) / df['Open']) * 100
        
        # Calculate overnight return (open vs previous close)
        df['overnight_return'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100
        
        # Calculate volatility metrics
        # 5-day rolling volatility
        df['volatility_5d'] = df['daily_return'].rolling(window=5, min_periods=2).std()
        
        # 20-day rolling volatility (approximately monthly)
        df['volatility_20d'] = df['daily_return'].rolling(window=20, min_periods=5).std()
        
        # Simple Moving Averages (SMA)
        df['sma_50'] = df['Close'].rolling(window=50, min_periods=1).mean()
        df['sma_100'] = df['Close'].rolling(window=100, min_periods=1).mean()
        df['sma_200'] = df['Close'].rolling(window=200, min_periods=1).mean()
        
        # Exponential Moving Averages (EMA)
        df['ema_8'] = df['Close'].ewm(span=8, adjust=False).mean()
        df['ema_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        # MACD (Moving Average Convergence Divergence)
        ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # RSI (Relative Strength Index)
        df['rsi'] = self.calculate_rsi(df['Close'], period=14)
        
        # Price relative to moving averages
        df['price_to_sma50'] = (df['Close'] / df['sma_50'] - 1) * 100
        df['price_to_sma200'] = (df['Close'] / df['sma_200'] - 1) * 100
        
        # Volume metrics
        df['volume_ma_20'] = df['Volume'].rolling(window=20, min_periods=1).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_ma_20']
        
        logger.info(f"{symbol}: Calculated returns and technical indicators")
        
        return df
    
    def add_market_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add market-related features for analysis
        
        Args:
            df: DataFrame with basic price data
            
        Returns:
            DataFrame with additional market features
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Trading range metrics
        df['daily_range'] = df['High'] - df['Low']
        df['daily_range_pct'] = (df['daily_range'] / df['Open']) * 100
        
        # Gap detection (opening vs previous close)
        df['gap'] = df['Open'] - df['Close'].shift(1)
        df['gap_pct'] = (df['gap'] / df['Close'].shift(1)) * 100
        
        # High/Low position within the day
        df['close_to_high'] = (df['High'] - df['Close']) / df['daily_range']
        df['close_to_low'] = (df['Close'] - df['Low']) / df['daily_range']
        
        # Bollinger Bands
        df['bb_middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = (df['Close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        return df
    
    def preprocess_stock_data(self, df: pd.DataFrame, symbol: str, 
                            validate: bool = True,
                            handle_missing: bool = True,
                            calculate_features: bool = True) -> pd.DataFrame:
        """
        Main preprocessing pipeline for stock data
        
        Args:
            df: Raw DataFrame from Yahoo Finance
            symbol: Stock symbol
            validate: Whether to validate data
            handle_missing: Whether to handle missing data
            calculate_features: Whether to calculate additional features
            
        Returns:
            Preprocessed DataFrame ready for analysis
        """
        # Step 1: Validation
        if validate:
            is_valid, issues = self.validate_dataframe(df, symbol)
            if not is_valid and not issues[0].endswith("DataFrame is empty"):
                logger.warning(f"{symbol} validation issues: {'; '.join(issues)}")
            if issues and issues[0].endswith("DataFrame is empty"):
                logger.error(f"{symbol}: Cannot process empty DataFrame")
                return df
        
        # Step 2: Handle missing data
        if handle_missing:
            df = self.handle_missing_data(df, symbol)
        
        # Step 3: Calculate returns and features
        if calculate_features:
            df = self.calculate_returns(df, symbol)
            df = self.add_market_features(df)
        
        # Step 4: Final cleanup
        # Remove any remaining NaN in calculated fields
        return_columns = ['daily_return', 'log_return', 'overnight_return', 'intraday_return']
        for col in return_columns:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        # Add symbol column if not present
        if 'Symbol' not in df.columns:
            df['Symbol'] = symbol
        
        logger.info(f"{symbol}: Preprocessing complete. Shape: {df.shape}")
        
        return df
    
    def preprocess_portfolio(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Preprocess multiple stocks for portfolio analysis
        
        Args:
            stock_data: Dictionary of {symbol: DataFrame}
            
        Returns:
            Dictionary of preprocessed DataFrames
        """
        preprocessed = {}
        
        for symbol, df in stock_data.items():
            logger.info(f"Preprocessing {symbol}...")
            preprocessed[symbol] = self.preprocess_stock_data(df, symbol)
        
        # Log summary statistics
        total_records = sum(len(df) for df in preprocessed.values())
        logger.info(f"Portfolio preprocessing complete: {len(preprocessed)} stocks, {total_records} total records")
        
        return preprocessed
    
    def create_portfolio_matrix(self, stock_data: Dict[str, pd.DataFrame], 
                              value_column: str = 'daily_return') -> pd.DataFrame:
        """
        Create a matrix of aligned stock data for portfolio analysis
        
        Args:
            stock_data: Dictionary of preprocessed DataFrames
            value_column: Column to use for the matrix (e.g., 'daily_return', 'Close')
            
        Returns:
            DataFrame with dates as index and stocks as columns
        """
        if not stock_data:
            return pd.DataFrame()
        
        # Collect all data
        frames = []
        for symbol, df in stock_data.items():
            if value_column in df.columns:
                temp = df[['Date', value_column]].copy()
                temp = temp.rename(columns={value_column: symbol})
                temp = temp.set_index('Date')
                frames.append(temp)
        
        if not frames:
            logger.warning(f"No data found for column: {value_column}")
            return pd.DataFrame()
        
        # Combine all frames
        matrix = pd.concat(frames, axis=1, join='outer')
        
        # Sort by date
        matrix = matrix.sort_index()
        
        logger.info(f"Created portfolio matrix: {matrix.shape} for {value_column}")
        
        return matrix

    def update_daily_returns_in_database(self, db_connection, stock_id: int = None, symbol: str = None):
        """
        Update daily returns for stock data already in the database
        
        Args:
            db_connection: Database connection object
            stock_id: Stock ID to update (optional)
            symbol: Stock symbol to update (optional, used if stock_id not provided)
        """
        try:
            # Get stock_id if symbol provided
            if symbol and not stock_id:
                stock_query = "SELECT stock_id FROM stocks WHERE symbol = %s"
                result = db_connection.execute_query(stock_query, (symbol,))
                if not result:
                    logger.error(f"Stock {symbol} not found in database")
                    return False
                stock_id = result[0][0]
            
            # Get historical data for the stock, ordered by date
            if stock_id:
                query = """
                SELECT date, close_price 
                FROM stock_historical_data 
                WHERE stock_id = %s 
                ORDER BY date ASC
                """
                data = db_connection.execute_query(query, (stock_id,))
                
                if not data or len(data) < 2:
                    logger.warning(f"Insufficient data for stock_id {stock_id} to calculate daily returns")
                    return False
                
                # Convert to DataFrame for easier calculation
                df = pd.DataFrame(data, columns=['date', 'close_price'])
                df['close_price'] = pd.to_numeric(df['close_price'])
                
                # Calculate daily returns
                df['daily_return'] = df['close_price'].pct_change()
                
                # Update each record in the database
                update_query = """
                UPDATE stock_historical_data 
                SET daily_return = %s 
                WHERE stock_id = %s AND date = %s
                """
                
                updated_count = 0
                for idx, row in df.iterrows():
                    if pd.notna(row['daily_return']):  # Skip the first row which will be NaN
                        db_connection.execute_update(
                            update_query, 
                            (float(row['daily_return']), stock_id, row['date'])
                        )
                        updated_count += 1
                
                logger.info(f"Updated daily returns for {updated_count} records for stock_id {stock_id}")
                return True
            else:
                # Update all stocks if no specific stock provided
                stocks_query = "SELECT stock_id, symbol FROM stocks"
                stocks = db_connection.execute_query(stocks_query)
                
                if not stocks:
                    logger.warning("No stocks found in database")
                    return False
                
                total_updated = 0
                for stock_id, symbol in stocks:
                    if self.update_daily_returns_in_database(db_connection, stock_id=stock_id):
                        total_updated += 1
                
                logger.info(f"Updated daily returns for {total_updated} stocks")
                return total_updated > 0
                
        except Exception as e:
            logger.error(f"Error updating daily returns: {e}")
            return False


# Example usage
if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    
    # Preprocess single stock
    processed = preprocessor.preprocess_stock_data(sample_data, 'TEST')
    print(f"Processed shape: {processed.shape}")
    print(f"Columns: {processed.columns.tolist()}")