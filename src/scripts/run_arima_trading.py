#!/usr/bin/env python3
"""
Quick start script for ARIMA trading with your portfolio
Place this in src/scripts/run_arima_trading.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import your existing modules
from database.db_connection import DatabaseConnection
from portfolio.portfolio_manager import PortfolioManager
from data.data_collector import DataCollector

# Import ARIMA algorithm
sys.path.append(os.path.join(os.path.dirname(__file__), '../trading'))
from arima_algorithm import ARIMATradingAlgorithm

def fetch_and_predict(symbol):
    """
    Fetch data from database and make ARIMA predictions
    """
    print(f"\n{'='*60}")
    print(f"ARIMA ANALYSIS FOR {symbol}")
    print(f"{'='*60}")
    
    # Connect to database
    db = DatabaseConnection()
    if not db.connect():
        print("Failed to connect to database")
        return None
    
    try:
        # Get stock_id
        stock_query = "SELECT stock_id FROM stocks WHERE symbol = %s"
        stock_result = db.execute_query(stock_query, (symbol,))
        
        if not stock_result:
            print(f"Stock {symbol} not found in database")
            # Try to add it
            dc = DataCollector()
            if dc.add_stock_to_database(symbol):
                print(f"Added {symbol} to database")
                # Fetch historical data
                dc.fetch_stock_data(symbol, period='1y')
                # Retry query
                stock_result = db.execute_query(stock_query, (symbol,))
            else:
                return None
        
        stock_id = stock_result[0][0]
        
        # Fetch historical data
        data_query = """
        SELECT date, close_price 
        FROM stock_historical_data 
        WHERE stock_id = %s 
        AND close_price IS NOT NULL
        ORDER BY date ASC
        LIMIT 365
        """
        
        data_result = db.execute_query(data_query, (stock_id,))
        
        if not data_result or len(data_result) < 30:
            print(f"Insufficient historical data for {symbol}")
            print("Fetching from Yahoo Finance...")
            
            # Fetch using data collector
            dc = DataCollector()
            dc.fetch_stock_data(symbol, period='1y')
            
            # Refresh DB connection to pick up newly inserted history
            db.disconnect()
            if not db.connect():
                print("Failed to reconnect to database after data fetch")
                return None

            # Retry query
            data_result = db.execute_query(data_query, (stock_id,))
            
            if not data_result or len(data_result) < 30:
                print("Still insufficient data")
                return None
        
        # Convert to pandas Series
        df = pd.DataFrame(data_result, columns=['date', 'close_price'])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        price_series = df['close_price'].astype(float)
        
        print(f"✓ Loaded {len(price_series)} days of price data")
        print(f"  Date range: {price_series.index[0].date()} to {price_series.index[-1].date()}")
        print(f"  Current price: ${price_series.iloc[-1]:.2f}")
        
        # Initialize ARIMA
        arima = ARIMATradingAlgorithm(
            confidence_threshold=0.02,
            prediction_horizon=5
        )
        
        # Test stationarity
        print("\n1. STATIONARITY TEST")
        print("-" * 40)
        is_stationary, _, p_value, _ = arima.test_stationarity(price_series)
        
        # Find optimal parameters
        print("\n2. FINDING OPTIMAL ARIMA PARAMETERS")
        print("-" * 40)
        optimal_order, model, _ = arima.find_optimal_order(
            price_series,
            max_p=3,
            max_d=2,
            max_q=3
        )

        if model is None:
            print("Failed to fit ARIMA model; skipping predictions")
            return None

        # Persist fitted model/order so prediction step can run
        arima.model = model
        arima.best_order = optimal_order
        
        # Make predictions
        print("\n3. GENERATING PREDICTIONS")
        print("-" * 40)
        predictions = arima.predict_prices(steps_ahead=5)
        
        # Generate trading signal
        print("\n4. TRADING SIGNAL")
        print("-" * 40)
        current_price = price_series.iloc[-1]
        signal = arima.generate_signals(current_price)
        
        print(f"\nCurrent Price: ${current_price:.2f}")
        print(f"5-Day Prediction: ${predictions['prediction'].iloc[-1]:.2f}")
        print(f"\n📊 SIGNAL: {signal['action']}")
        print(f"   Confidence: {signal['confidence']:.2%}")
        print(f"   Expected Return: {signal.get('expected_return', 0):.2%}")
        print(f"   Reason: {signal['reason']}")
        
        # Backtest
        print("\n5. BACKTESTING")
        print("-" * 40)
        backtest = arima.backtest(
            price_series,
            train_size=0.8,
            initial_capital=10000
        )
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'predictions': predictions,
            'signal': signal,
            'backtest': backtest,
            'model': arima
        }
        
    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        db.disconnect()


def analyze_portfolio(portfolio_id):
    """
    Analyze all stocks in a portfolio using ARIMA
    """
    print(f"\n{'='*80}")
    print(f"PORTFOLIO ARIMA ANALYSIS")
    print(f"{'='*80}")
    
    pm = PortfolioManager()
    
    # Get portfolio stocks
    stocks = pm.get_portfolio_stocks(portfolio_id)
    
    if not stocks:
        print(f"No stocks found in portfolio {portfolio_id}")
        return None
    
    print(f"\nAnalyzing portfolio {portfolio_id} with {len(stocks)} stocks")
    
    results = {}
    buy_signals = []
    sell_signals = []
    hold_signals = []
    
    for stock in stocks:
        stock_id, symbol, company_name, quantity, avg_cost, _ = stock
        
        print(f"\nAnalyzing {symbol} ({company_name})")
        print(f"Current position: {quantity} shares @ ${avg_cost:.2f}")
        
        result = fetch_and_predict(symbol)
        
        if result:
            results[symbol] = result
            
            # Categorize signals
            if result['signal']['action'] == 'BUY':
                buy_signals.append(symbol)
            elif result['signal']['action'] == 'SELL':
                sell_signals.append(symbol)
            else:
                hold_signals.append(symbol)
    
    # Summary
    print(f"\n{'='*80}")
    print("PORTFOLIO SUMMARY")
    print(f"{'='*80}")
    
    print(f"\n🟢 BUY SIGNALS ({len(buy_signals)}):")
    for symbol in buy_signals:
        signal = results[symbol]['signal']
        print(f"  {symbol}: Expected return {signal['expected_return']:.2%}, Confidence {signal['confidence']:.0%}")
    
    print(f"\n🔴 SELL SIGNALS ({len(sell_signals)}):")
    for symbol in sell_signals:
        signal = results[symbol]['signal']
        print(f"  {symbol}: Expected return {signal['expected_return']:.2%}, Confidence {signal['confidence']:.0%}")
    
    print(f"\n⚪ HOLD SIGNALS ({len(hold_signals)}):")
    for symbol in hold_signals:
        print(f"  {symbol}")
    
    # Calculate aggregate metrics
    if results:
        avg_expected_return = np.mean([r['signal'].get('expected_return', 0) for r in results.values()])
        avg_backtest_return = np.mean([r['backtest']['total_return'] for r in results.values()])
        
        print(f"\n📈 AGGREGATE METRICS:")
        print(f"  Average Expected Return: {avg_expected_return:.2%}")
        print(f"  Average Backtest Return: {avg_backtest_return:.2%}")
    
    return results


def main():
    """
    Main function to run ARIMA analysis
    """
    print("=" * 80)
    print("ARIMA TRADING ALGORITHM - QUICK START")
    print("=" * 80)
    
    # Menu
    print("\nOptions:")
    print("1. Analyze single stock")
    print("2. Analyze entire portfolio")
    print("3. Quick demo with sample stocks")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        symbol = input("Enter stock symbol: ").strip().upper()
        if symbol:
            result = fetch_and_predict(symbol)
            if result:
                print("\n✅ Analysis complete!")
    
    elif choice == '2':
        # Display portfolios
        pm = PortfolioManager()
        pm.display_all_portfolios()
        
        try:
            portfolio_id = int(input("\nEnter Portfolio ID: "))
            results = analyze_portfolio(portfolio_id)
            if results is None:
                print("\n⚠️ No stocks in this portfolio. Add holdings before running ARIMA.")
            elif results:
                print("\n✅ Portfolio analysis complete!")
            else:
                print("\n❌ Portfolio analysis failed to generate any results")
        except ValueError:
            print("Invalid portfolio ID")
    
    elif choice == '3':
        # Quick demo
        demo_stocks = ['AAPL', 'GOOGL', 'MSFT']
        print(f"\nRunning demo with: {', '.join(demo_stocks)}")
        
        for symbol in demo_stocks:
            result = fetch_and_predict(symbol)
            if result:
                print(f"\n✅ {symbol} analyzed successfully")
    
    else:
        print("Invalid choice")
    
    print("\n" + "=" * 80)
    print("ARIMA ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nKey Achievements:")
    print("✓ Implemented ARIMA model with automatic parameter selection")
    print("✓ Generated buy/sell signals with confidence levels")
    print("✓ Backtested strategy with historical data")
    print("✓ Integrated with existing portfolio system")
    
    print("\nNext Steps for Lab 4:")
    print("1. Create mock trading environment")
    print("2. Calculate portfolio performance metrics")
    print("3. Implement Sharpe ratio calculation")
    print("4. Prepare for team competition")


if __name__ == "__main__":
    main()
