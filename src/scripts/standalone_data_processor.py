#!/usr/bin/env python3
"""
Standalone data processor that runs locally without database
Uses the actual production classes from src/ but skips database operations
"""
import sys
import os
sys.path.append('..')

from data.data_collector import DataCollector
from data.data_preprocessor import DataPreprocessor
from portfolio.stock_validator import StockValidator
import time
from datetime import datetime

class StandaloneDataProcessor:
    def __init__(self):
        self.api_call_count = 0
        self.last_call_time = 0
        self.call_history = []
        
        # Initialize production classes
        self.data_collector = DataCollector()
        self.data_preprocessor = DataPreprocessor()
        self.stock_validator = StockValidator()
        
    def log_api_call(self, symbol, call_type, success, error=None):
        """Log each API call for debugging"""
        self.api_call_count += 1
        current_time = time.time()
        
        call_info = {
            'call_number': self.api_call_count,
            'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3],
            'symbol': symbol,
            'call_type': call_type,
            'success': success,
            'error': str(error) if error else None,
            'time_since_last': current_time - self.last_call_time if self.last_call_time > 0 else 0
        }
        
        self.call_history.append(call_info)
        self.last_call_time = current_time
        
        # Print real-time log
        status = " SUCCESS" if success else " FAILED"
        print(f"[{call_info['timestamp']}] Call #{self.api_call_count}: {call_type}({symbol}) - {status}")
        if error:
            print(f"   Error: {error}")
        if call_info['time_since_last'] > 0:
            print(f"   Time since last call: {call_info['time_since_last']:.2f}s")
        print()

    def safe_ticker_info(self, symbol, wait_time=2):
        """Use production DataCollector.get_stock_info"""
        print(f"--- Getting ticker info for {symbol} ---")
        
        try:
            print("Using production DataCollector.get_stock_info()...")
            result = self.data_collector.get_stock_info(symbol)
            
            if result:
                self.log_api_call(symbol, "DataCollector.get_stock_info", True)
                
                print(f" Successfully retrieved info for {symbol}")
                print(f"   company_name: {result.get('name')}")
                print(f"   sector: {result.get('sector')}")
                print(f"   exchange: {result.get('exchange')}")
                print(f"   current_price: {result.get('current_price')}")
                print(f"   market_cap: {result.get('market_cap')}")
                print(f"   pe_ratio: {result.get('pe_ratio')}")
                
                return result
            else:
                self.log_api_call(symbol, "DataCollector.get_stock_info", False, "No data returned")
                return None
                
        except Exception as e:
            self.log_api_call(symbol, "DataCollector.get_stock_info", False, e)
            print(f" Error getting info for {symbol}: {e}")
            return None

    def safe_historical_data(self, symbol, period="1y", wait_time=2):
        """Use production DataCollector.get_historical_data"""
        print(f"--- Getting historical data for {symbol} ({period}) ---")
        
        try:
            print("Using production DataCollector.get_historical_data()...")
            hist = self.data_collector.get_historical_data(symbol, period=period)
            
            if hist is not None and not hist.empty:
                self.log_api_call(symbol, f"DataCollector.get_historical_data({period})", True)
                
                print(f" Successfully retrieved {len(hist)} records for {symbol}")
                print(f"   Date range: {hist.index[0]} to {hist.index[-1]}")
                print(f"   Recent close: ${float(hist['Close'].iloc[-1]):.2f}")
                print(f"   Recent volume: {int(hist['Volume'].iloc[-1]):,}")
                print(f"First five rows: {hist.head()}")
                
                return hist
            else:
                self.log_api_call(symbol, f"DataCollector.get_historical_data({period})", False, "Empty DataFrame returned")
                return None
                
        except Exception as e:
            self.log_api_call(symbol, f"DataCollector.get_historical_data({period})", False, e)
            print(f" Error getting historical data for {symbol}: {e}")
            return None

    def test_stock_validation(self, symbol):
        """Test production StockValidator"""
        print(f"--- Testing stock validation for {symbol} ---")
        
        try:
            print("Using production StockValidator.validate_stock()...")
            is_valid = self.stock_validator.validate_stock(symbol)
            
            if is_valid:
                self.log_api_call(symbol, "StockValidator.validate_stock", True)
                print(f" {symbol} validation passed")
                return True
            else:
                self.log_api_call(symbol, "StockValidator.validate_stock", False, "Invalid stock symbol")
                print(f" {symbol} validation failed")
                return False
                
        except Exception as e:
            self.log_api_call(symbol, "StockValidator.validate_stock", False, e)
            print(f" Error validating {symbol}: {e}")
            return False

    def process_single_stock(self, symbol):
        """Process a single stock with all production methods"""
        print("=" * 80)
        print(f"PROCESSING STOCK: {symbol}")
        print("=" * 80)
        
        # Method 1: Validate stock
        validation = self.test_stock_validation(symbol)
        
        # Method 2: Get basic info
        info = self.safe_ticker_info(symbol)
        
        # Method 3: Get historical data
        historical = self.safe_historical_data(symbol, period="1mo")
        
        return {
            'symbol': symbol,
            'validation': validation,
            'info': info,
            'historical': historical
        }

    def process_multiple_stocks(self, symbols):
        """Process multiple stocks to test rate limiting"""
        print("=" * 80)
        print(f"PROCESSING {len(symbols)} STOCKS")
        print("=" * 80)
        
        results = {}
        
        for i, symbol in enumerate(symbols):
            print(f"\n[Stock {i+1}/{len(symbols)}] Processing {symbol}")
            results[symbol] = self.process_single_stock(symbol)
        
        return results

    def print_summary(self):
        """Print summary of all API calls"""
        print("\n" + "=" * 80)
        print("API CALL SUMMARY")
        print("=" * 80)
        
        print(f"Total API calls made: {self.api_call_count}")
        
        successful_calls = [call for call in self.call_history if call['success']]
        failed_calls = [call for call in self.call_history if not call['success']]
        
        print(f"Successful calls: {len(successful_calls)}")
        print(f"Failed calls: {len(failed_calls)}")
        
        if failed_calls:
            print("\nFAILED CALLS DETAILS:")
            for call in failed_calls:
                print(f"  {call['timestamp']} - {call['call_type']}({call['symbol']}): {call['error']}")
        
        # Show timing between calls
        if len(self.call_history) > 1:
            print("\nCALL TIMING:")
            for i in range(1, len(self.call_history)):
                call = self.call_history[i]
                print(f"  Call {call['call_number']}: {call['time_since_last']:.2f}s after previous")

def main():
    print("Standalone Yahoo Finance Data Processor")
    print("=" * 80)
    
    processor = StandaloneDataProcessor()
    
    # Test with single stock first
    print("\n1. SINGLE STOCK TEST")
    single_result = processor.process_single_stock("AAPL")
    
    # Test with multiple stocks
    print("\n\n2. MULTIPLE STOCK TEST")
    symbols = ["MSFT", "GOOGL", "TSLA"]
    multiple_results = processor.process_multiple_stocks(symbols)
    
    # Print summary
    processor.print_summary()
    
    # Final recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    successful_calls = len([call for call in processor.call_history if call['success']])
    total_calls = len(processor.call_history)
    
    if successful_calls == total_calls:
        print(" ALL API CALLS SUCCESSFUL!")
        print("  - Yahoo Finance is working correctly")
        print("  - Rate limiting is not an issue")
        print("  - Database integration can proceed")
    elif successful_calls > total_calls * 0.5:
        print(" SOME API CALLS FAILED")
        print("  - Intermittent rate limiting detected")
        print("  - Increase wait times between calls")
        print("  - Implement more aggressive retry logic")
    else:
        print(" MOST API CALLS FAILED")
        print("  - Severe rate limiting in effect")
        print("  - Wait 10-15 minutes before trying again")
        print("  - Consider using cached data for development")

if __name__ == "__main__":
    main()
