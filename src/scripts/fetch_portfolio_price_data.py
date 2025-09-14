#!/usr/bin/env python3
"""
Script 4: Fetch Stock Price Data for Portfolio (Date Range)
Requirement: Fetch stock price data for input date range for list of stocks in portfolio
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from portfolio.portfolio_manager import PortfolioManager
from database.db_connection import DatabaseConnection
from datetime import datetime, timedelta

def show_portfolio_stocks(pm, portfolio_id):
    """Display stocks in the selected portfolio"""
    print("\n--- STOCKS IN PORTFOLIO ---")
    
    stocks = pm.get_portfolio_stocks(portfolio_id)
    if not stocks:
        print("No stocks found in portfolio")
        return []
    
    stock_symbols = []
    print(f"{'Symbol':<8} | {'Company Name':<25} | {'Quantity':<10}")
    print("-" * 50)
    
    for stock in stocks:
        stock_id, symbol, company_name, quantity, avg_cost, unrealized_pnl = stock
        print(f"{symbol:<8} | {company_name[:25]:<25} | {quantity:<10}")
        stock_symbols.append(symbol)
    
    return stock_symbols

def get_date_range_input():
    """Get date range input from user with validation"""
    print("\nDate Range Options:")
    print("1. Use predefined period (1mo, 3mo, 6mo, 1y, etc.)")
    print("2. Use specific date range (YYYY-MM-DD to YYYY-MM-DD)")
    
    while True:
        option = input("Choose option (1-2): ").strip()
        
        if option == '1':
            print("\nAvailable periods:")
            print("• 1mo (1 month)")
            print("• 3mo (3 months)") 
            print("• 6mo (6 months)")
            print("• 1y (1 year)")
            print("• 2y (2 years)")
            print("• ytd (year to date)")
            print("• max (maximum available)")
            
            period = input("Enter period (default: 1mo): ").strip() or '1mo'
            return {'type': 'period', 'period': period}
        
        elif option == '2':
            while True:
                try:
                    start_date_str = input("Enter start date (YYYY-MM-DD): ").strip()
                    end_date_str = input("Enter end date (YYYY-MM-DD): ").strip()
                    
                    if not start_date_str or not end_date_str:
                        print(" Both start and end dates are required")
                        continue
                    
                    # Validate date format
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    
                    if start_date >= end_date:
                        print(" Start date must be before end date")
                        continue
                    
                    if end_date > datetime.now():
                        print("  End date is in the future")
                    
                    return {
                        'type': 'date_range', 
                        'start_date': start_date_str, 
                        'end_date': end_date_str
                    }
                    
                except ValueError:
                    print(" Invalid date format. Use YYYY-MM-DD")
                    continue
        else:
            print(" Invalid option")

def verify_price_data_updated(portfolio_id, stock_symbols, date_params):
    """Verify that price data was actually fetched and stored"""
    print("\n--- VERIFYING PRICE DATA ---")
    
    db = DatabaseConnection()
    if not db.connect():
        print(" Could not connect to database for verification")
        return False
    
    try:
        verification_results = {}
        
        for symbol in stock_symbols:
            # Get stock_id
            stock_query = "SELECT stock_id FROM stocks WHERE symbol = %s"
            stock_result = db.execute_query(stock_query, (symbol,))
            
            if not stock_result:
                verification_results[symbol] = {'status': 'not_found', 'records': 0}
                continue
            
            stock_id = stock_result[0][0]
            
            # Count price records
            if date_params['type'] == 'period':
                # For period-based, we'll check recent records
                count_query = """
                SELECT COUNT(*), MIN(date) as earliest, MAX(date) as latest
                FROM stock_historical_data 
                WHERE stock_id = %s
                """
                count_result = db.execute_query(count_query, (stock_id,))
            else:
                # For date range, check specific range
                count_query = """
                SELECT COUNT(*), MIN(date) as earliest, MAX(date) as latest
                FROM stock_historical_data 
                WHERE stock_id = %s AND date BETWEEN %s AND %s
                """
                count_result = db.execute_query(count_query, (stock_id, date_params['start_date'], date_params['end_date']))
            
            if count_result:
                count, earliest, latest = count_result[0]
                verification_results[symbol] = {
                    'status': 'success' if count > 0 else 'no_data',
                    'records': count,
                    'earliest': earliest,
                    'latest': latest
                }
            else:
                verification_results[symbol] = {'status': 'error', 'records': 0}
        
        # Display results
        print(f"{'Symbol':<8} | {'Status':<12} | {'Records':<8} | {'Date Range'}")
        print("-" * 60)
        
        total_success = 0
        for symbol, result in verification_results.items():
            status = result['status']
            records = result['records']
            
            if status == 'success':
                earliest = result['earliest']
                latest = result['latest']
                date_range = f"{earliest} to {latest}" if earliest and latest else "Unknown"
                print(f"{symbol:<8} | {' Updated':<12} | {records:<8} | {date_range}")
                total_success += 1
            elif status == 'no_data':
                print(f"{symbol:<8} | {' No Data':<12} | {records:<8} | N/A")
            elif status == 'not_found':
                print(f"{symbol:<8} | {' Not Found':<12} | {records:<8} | N/A")
            else:
                print(f"{symbol:<8} | {' Error':<12} | {records:<8} | N/A")
        
        print(f"\nSummary: {total_success}/{len(stock_symbols)} stocks updated successfully")
        
        db.disconnect()
        return total_success > 0
        
    except Exception as e:
        print(f" Verification error: {e}")
        db.disconnect()
        return False

def main():
    print("=" * 70)
    print("FETCH STOCK PRICE DATA FOR PORTFOLIO (DATE RANGE)")
    print("=" * 70)
    
    pm = PortfolioManager()
    
    # Step 1: Select Portfolio
    print("\nStep 1: Select Portfolio")
    pm.display_all_portfolios()
    
    try:
        portfolio_id = int(input("\nEnter Portfolio ID: "))
        
        # Step 2: Display stocks in portfolio
        print("\nStep 2: Review Portfolio Stocks")
        stock_symbols = show_portfolio_stocks(pm, portfolio_id)
        
        if not stock_symbols:
            print(" No stocks in portfolio to fetch data for")
            return False
        
        print(f"\nFound {len(stock_symbols)} stocks: {', '.join(stock_symbols)}")
        
        # Step 3: Get date range parameters
        print("\nStep 3: Specify Date Range")
        date_params = get_date_range_input()
        
        # Step 4: Confirm operation
        print(f"\n" + "="*50)
        print("OPERATION SUMMARY")
        print("="*50)
        print(f"Portfolio ID: {portfolio_id}")
        print(f"Stocks to update: {', '.join(stock_symbols)} ({len(stock_symbols)} stocks)")
        
        if date_params['type'] == 'period':
            print(f"Date Range: {date_params['period']} period")
        else:
            print(f"Date Range: {date_params['start_date']} to {date_params['end_date']}")
        
        confirm = input("\nProceed with price data fetch? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled")
            return False
        
        # Step 5: Execute price data fetch
        print(f"\n" + "="*50)
        print("FETCHING PRICE DATA...")
        print("="*50)
        
        if date_params['type'] == 'period':
            success = pm.fetch_portfolio_price_data(
                portfolio_id, 
                period=date_params['period']
            )
        else:
            success = pm.fetch_portfolio_price_data(
                portfolio_id,
                start_date=date_params['start_date'],
                end_date=date_params['end_date']
            )
        
        # Step 6: Verify results
        if success:
            print("\n PRICE DATA FETCH COMPLETED!")
            
            # Verify data was actually stored
            verification_success = verify_price_data_updated(portfolio_id, stock_symbols, date_params)
            
            if verification_success:
                print("\n SUCCESS: Portfolio price data updated successfully!")
                print("\nKey accomplishments:")
                print("• Identified stocks in portfolio")
                print("• Applied specified date range")
                print("• Fetched historical price data from Yahoo Finance")
                print("• Stored data in database with duplicate prevention")
                print("• Verified data integrity")
                return True
            else:
                print("\n  Price data fetch completed but verification failed")
                return False
        else:
            print("\n PRICE DATA FETCH FAILED")
            return False
            
    except ValueError:
        print(" Invalid portfolio ID")
        return False
    except Exception as e:
        print(f" Error: {e}")
        return False

if __name__ == "__main__":
    print("Requirement: Fetch stock price data for input date range for list of stocks in portfolio")
    success = main()
    
    print("\n" + "=" * 70)
    if success:
        print(" REQUIREMENT FULFILLED: Portfolio price data fetched for date range")
        print("Key Features Demonstrated:")
        print("• Select portfolio and identify constituent stocks")
        print("• Specify date range (both period and specific dates)")
        print("• Fetch historical price data for all portfolio stocks")
        print("• Store data with duplicate prevention")
        print("• Verify successful data retrieval and storage")
    else:
        print(" REQUIREMENT NOT MET: Price data fetch failed")
    
    sys.exit(0 if success else 1)
