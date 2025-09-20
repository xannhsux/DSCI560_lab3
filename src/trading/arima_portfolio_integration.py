#!/usr/bin/env python3
"""
ARIMA Integration with Portfolio Management System
Connects ARIMA predictions to your existing portfolio infrastructure
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.db_connection import DatabaseConnection
from portfolio.portfolio_manager import PortfolioManager
from data.data_collector import DataCollector
from trading.arima_algorithm import ARIMATradingAlgorithm

class ARIMAPortfolioTrader:
    """
    Integration class that connects ARIMA algorithm with portfolio management
    """
    
    def __init__(self, portfolio_id, initial_capital=10000):
        """
        Initialize ARIMA portfolio trader
        
        Args:
            portfolio_id: ID of portfolio to trade
            initial_capital: Starting capital
        """
        self.portfolio_id = portfolio_id
        self.initial_capital = initial_capital
        
        # Initialize components
        self.db = DatabaseConnection()
        self.portfolio_manager = PortfolioManager()
        self.data_collector = DataCollector()
        self.arima_algo = ARIMATradingAlgorithm(
            confidence_threshold=0.02,
            prediction_horizon=5
        )
        
        self.trading_history = []
        self.performance_metrics = {}
        
    def fetch_stock_data_from_db(self, symbol, days=365):
        """
        Fetch historical stock data from database
        
        Args:
            symbol: Stock symbol
            days: Number of days of historical data
            
        Returns:
            pd.Series: Price series
        """
        if not self.db.connect():
            raise ConnectionError("Failed to connect to database")
        
        try:
            # Get stock_id
            stock_query = "SELECT stock_id FROM stocks WHERE symbol = %s"
            stock_result = self.db.execute_query(stock_query, (symbol,))
            
            if not stock_result:
                print(f"Stock {symbol} not found in database")
                return None
            
            stock_id = stock_result[0][0]
            
            # Fetch historical data
            data_query = """
            SELECT date, close_price 
            FROM stock_historical_data 
            WHERE stock_id = %s 
            AND date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ORDER BY date ASC
            """
            
            data_result = self.db.execute_query(data_query, (stock_id, days))
            
            if not data_result:
                print(f"No historical data found for {symbol}")
                return None
            
            # Convert to pandas Series
            df = pd.DataFrame(data_result, columns=['date', 'close_price'])
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            price_series = df['close_price'].astype(float)
            
            print(f"✓ Fetched {len(price_series)} days of data for {symbol}")
            print(f"  Date range: {price_series.index[0]} to {price_series.index[-1]}")
            print(f"  Price range: ${price_series.min():.2f} - ${price_series.max():.2f}")
            
            return price_series
            
        finally:
            self.db.disconnect()
    
    def train_arima_model(self, symbol, lookback_days=365):
        """
        Train ARIMA model on stock data
        
        Args:
            symbol: Stock symbol to train on
            lookback_days: Days of historical data to use
            
        Returns:
            Fitted ARIMA model
        """
        print(f"\n=== Training ARIMA Model for {symbol} ===")
        
        # Fetch data
        price_data = self.fetch_stock_data_from_db(symbol, lookback_days)
        
        if price_data is None or len(price_data) < 30:
            print("Insufficient data for ARIMA training")
            return None
        
        # Determine optimal order and reuse fitted model from grid search
        optimal_order, model, _ = self.arima_algo.find_optimal_order(price_data)

        if model is None:
            print("Failed to fit ARIMA model with available data")
            return None

        # Persist fitted model so downstream predictions use it directly
        self.arima_algo.model = model

        print(f"\n✓ ARIMA{optimal_order} model fitted successfully")
        
        return model
    
    def generate_portfolio_signals(self):
        """
        Generate trading signals for all stocks in portfolio
        
        Returns:
            dict: Signals for each stock
        """
        print("\n=== Generating Portfolio Trading Signals ===")
        
        # Get portfolio stocks
        stocks = self.portfolio_manager.get_portfolio_stocks(self.portfolio_id)
        
        if not stocks:
            print("No stocks in portfolio")
            return {}
        
        signals = {}
        
        for stock in stocks:
            stock_id, symbol, company_name, quantity, avg_cost, _ = stock
            
            print(f"\nAnalyzing {symbol} ({company_name})...")
            print(f"  Current position: {quantity} shares @ ${avg_cost:.2f}")
            
            # Train model for this stock
            model = self.train_arima_model(symbol)
            
            if model is None:
                signals[symbol] = {
                    'action': 'HOLD',
                    'confidence': 0,
                    'reason': 'Insufficient data for prediction'
                }
                continue
            
            # Generate predictions
            predictions = self.arima_algo.predict_prices(steps_ahead=5)
            
            # Get current price (last known price from data)
            price_data = self.fetch_stock_data_from_db(symbol, days=5)
            if price_data is not None and len(price_data) > 0:
                current_price = float(price_data.iloc[-1])
            else:
                current_price = avg_cost  # Fallback to average cost
            
            # Generate signal
            signal = self.arima_algo.generate_signals(current_price, predictions)
            signals[symbol] = signal
            
            print(f"\n  Signal for {symbol}:")
            print(f"    Action: {signal['action']}")
            print(f"    Confidence: {signal['confidence']:.2%}")
            print(f"    Expected Return: {signal.get('expected_return', 0):.2%}")
            
        return signals
    
    def execute_trades(self, signals, max_position_size=0.2):
        """
        Execute trades based on ARIMA signals
        
        Args:
            signals: Trading signals for each stock
            max_position_size: Maximum position size as fraction of portfolio
            
        Returns:
            list: Executed trades
        """
        print("\n=== Executing Trades Based on ARIMA Signals ===")
        
        executed_trades = []
        
        for symbol, signal in signals.items():
            if signal['action'] == 'HOLD':
                print(f"{symbol}: HOLDING - {signal['reason']}")
                continue
            
            # Get current position
            position = self.portfolio_manager.get_position(self.portfolio_id, symbol)
            
            if signal['action'] == 'BUY':
                # Calculate position size based on confidence
                position_size = min(
                    signal['confidence'] * max_position_size,
                    max_position_size
                )
                
                # Calculate shares to buy
                trade_value = self.initial_capital * position_size
                shares_to_buy = int(trade_value / signal['current_price'])
                
                if shares_to_buy > 0:
                    print(f"\n{symbol}: BUY SIGNAL")
                    print(f"  Shares to buy: {shares_to_buy}")
                    print(f"  Price: ${signal['current_price']:.2f}")
                    print(f"  Total value: ${shares_to_buy * signal['current_price']:.2f}")
                    
                    # Execute trade through portfolio manager
                    success = self.portfolio_manager.execute_trade(
                        self.portfolio_id,
                        symbol,
                        'BUY_TO_OPEN',
                        shares_to_buy,
                        signal['current_price'],
                        fees=0,
                        notes=f"ARIMA signal - Expected return: {signal['expected_return']:.2%}"
                    )
                    
                    if success:
                        executed_trades.append({
                            'timestamp': datetime.now(),
                            'symbol': symbol,
                            'action': 'BUY',
                            'shares': shares_to_buy,
                            'price': signal['current_price'],
                            'signal': signal
                        })
            
            elif signal['action'] == 'SELL' and position and position['quantity'] > 0:
                # Sell based on confidence (partial or full)
                shares_to_sell = int(position['quantity'] * signal['confidence'])
                
                if shares_to_sell > 0:
                    print(f"\n{symbol}: SELL SIGNAL")
                    print(f"  Shares to sell: {shares_to_sell}")
                    print(f"  Price: ${signal['current_price']:.2f}")
                    print(f"  Total value: ${shares_to_sell * signal['current_price']:.2f}")
                    
                    # Execute trade
                    success = self.portfolio_manager.execute_trade(
                        self.portfolio_id,
                        symbol,
                        'SELL_TO_CLOSE',
                        shares_to_sell,
                        signal['current_price'],
                        fees=0,
                        notes=f"ARIMA signal - Expected return: {signal['expected_return']:.2%}"
                    )
                    
                    if success:
                        executed_trades.append({
                            'timestamp': datetime.now(),
                            'symbol': symbol,
                            'action': 'SELL',
                            'shares': shares_to_sell,
                            'price': signal['current_price'],
                            'signal': signal
                        })
        
        self.trading_history.extend(executed_trades)
        
        print(f"\n✓ Executed {len(executed_trades)} trades")
        return executed_trades
    
    def calculate_portfolio_performance(self):
        """
        Calculate portfolio performance metrics
        
        Returns:
            dict: Performance metrics
        """
        print("\n=== Portfolio Performance Metrics ===")
        
        # Get current portfolio value
        portfolio_details = self.portfolio_manager.get_portfolio_with_details(self.portfolio_id)
        
        if not portfolio_details:
            print("Could not fetch portfolio details")
            return {}
        
        current_value = portfolio_details['total_market_value']
        
        # Calculate returns
        total_return = (current_value - self.initial_capital) / self.initial_capital
        
        # Calculate trade statistics
        num_trades = len(self.trading_history)
        winning_trades = sum(1 for t in self.trading_history 
                           if t['signal'].get('expected_return', 0) > 0)
        
        # Calculate Sharpe ratio (simplified)
        if len(self.trading_history) > 0:
            returns = []
            for i in range(1, len(self.trading_history)):
                prev_trade = self.trading_history[i-1]
                curr_trade = self.trading_history[i]
                if prev_trade['symbol'] == curr_trade['symbol']:
                    ret = (curr_trade['price'] - prev_trade['price']) / prev_trade['price']
                    returns.append(ret)
            
            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = (avg_return - 0.02/252) / std_return if std_return > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        self.performance_metrics = {
            'initial_capital': self.initial_capital,
            'current_value': current_value,
            'total_return': total_return,
            'num_trades': num_trades,
            'winning_trades': winning_trades,
            'win_rate': winning_trades / num_trades if num_trades > 0 else 0,
            'sharpe_ratio': sharpe_ratio
        }
        
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Current Value: ${current_value:,.2f}")
        print(f"Total Return: {total_return:.2%}")
        print(f"Number of Trades: {num_trades}")
        print(f"Win Rate: {self.performance_metrics['win_rate']:.2%}")
        print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        
        return self.performance_metrics
    
    def run_trading_cycle(self):
        """
        Run a complete trading cycle: analyze, signal, trade, evaluate
        
        Returns:
            dict: Results of trading cycle
        """
        print("=" * 80)
        print("ARIMA TRADING CYCLE")
        print("=" * 80)
        print(f"Portfolio ID: {self.portfolio_id}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Timestamp: {datetime.now()}")
        
        # Generate signals
        signals = self.generate_portfolio_signals()
        
        if not signals:
            print("No signals generated")
            return {}
        
        # Execute trades
        trades = self.execute_trades(signals)
        
        # Calculate performance
        performance = self.calculate_portfolio_performance()
        
        results = {
            'timestamp': datetime.now(),
            'signals': signals,
            'trades': trades,
            'performance': performance
        }
        
        return results


class ARIMABacktester:
    """
    Backtesting system for ARIMA trading strategy
    """
    
    def __init__(self, portfolio_id):
        self.portfolio_id = portfolio_id
        self.db = DatabaseConnection()
        self.arima_algo = ARIMATradingAlgorithm()
        
    def backtest_portfolio(self, start_date, end_date, initial_capital=10000):
        """
        Backtest ARIMA strategy on portfolio
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital
            
        Returns:
            dict: Backtest results
        """
        print(f"\n=== Backtesting Portfolio {self.portfolio_id} ===")
        print(f"Period: {start_date} to {end_date}")
        print(f"Initial Capital: ${initial_capital:,.2f}")
        
        if not self.db.connect():
            print("Failed to connect to database")
            return {}
        
        try:
            # Get portfolio stocks
            stocks_query = """
            SELECT DISTINCT s.symbol 
            FROM stocks s
            JOIN portfolio_holdings ph ON s.stock_id = ph.stock_id
            WHERE ph.portfolio_id = %s
            """
            
            stocks_result = self.db.execute_query(stocks_query, (self.portfolio_id,))
            
            if not stocks_result:
                print("No stocks in portfolio")
                return {}
            
            symbols = [stock[0] for stock in stocks_result]
            print(f"Stocks to backtest: {', '.join(symbols)}")
            
            # Initialize portfolio
            portfolio_value = initial_capital
            cash = initial_capital
            positions = {symbol: 0 for symbol in symbols}
            trades = []
            daily_values = []
            
            # Backtest each stock
            for symbol in symbols:
                print(f"\nBacktesting {symbol}...")
                
                # Fetch historical data
                data_query = """
                SELECT date, close_price 
                FROM stock_historical_data shd
                JOIN stocks s ON shd.stock_id = s.stock_id
                WHERE s.symbol = %s 
                AND date BETWEEN %s AND %s
                ORDER BY date ASC
                """
                
                data_result = self.db.execute_query(
                    data_query, 
                    (symbol, start_date, end_date)
                )
                
                if not data_result or len(data_result) < 100:
                    print(f"  Insufficient data for {symbol}")
                    continue
                
                # Convert to Series
                df = pd.DataFrame(data_result, columns=['date', 'price'])
                price_series = pd.Series(
                    df['price'].values.astype(float),
                    index=pd.to_datetime(df['date'])
                )
                
                # Backtest using ARIMA
                backtest_result = self.arima_algo.backtest(
                    price_series,
                    train_size=0.8,
                    initial_capital=initial_capital / len(symbols)  # Equal allocation
                )
                
                # Aggregate results
                portfolio_value += backtest_result['final_value'] - backtest_result['initial_capital']
                trades.extend(backtest_result['portfolio']['trades'])
                
            # Calculate final metrics
            total_return = (portfolio_value - initial_capital) / initial_capital
            
            results = {
                'initial_capital': initial_capital,
                'final_value': portfolio_value,
                'total_return': total_return,
                'num_trades': len(trades),
                'symbols_tested': symbols
            }
            
            print(f"\n=== Backtest Summary ===")
            print(f"Final Portfolio Value: ${portfolio_value:,.2f}")
            print(f"Total Return: {total_return:.2%}")
            print(f"Total Trades: {len(trades)}")
            
            return results
            
        finally:
            self.db.disconnect()


def main():
    """
    Main function to run ARIMA trading system
    """
    print("=" * 80)
    print("ARIMA TRADING SYSTEM WITH PORTFOLIO INTEGRATION")
    print("=" * 80)
    
    # Configuration
    PORTFOLIO_ID = 1  # Change to your portfolio ID
    INITIAL_CAPITAL = 10000
    
    # Initialize trader
    trader = ARIMAPortfolioTrader(
        portfolio_id=PORTFOLIO_ID,
        initial_capital=INITIAL_CAPITAL
    )
    
    # Run trading cycle
    print("\n1. RUNNING TRADING CYCLE")
    print("-" * 40)
    results = trader.run_trading_cycle()
    
    # Run backtest
    print("\n2. RUNNING BACKTEST")
    print("-" * 40)
    backtester = ARIMABacktester(portfolio_id=PORTFOLIO_ID)
    
    # Backtest for last year
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365)
    
    backtest_results = backtester.backtest_portfolio(
        start_date=start_date,
        end_date=end_date,
        initial_capital=INITIAL_CAPITAL
    )
    
    # Summary
    print("\n" + "=" * 80)
    print("TRADING SESSION COMPLETE")
    print("=" * 80)
    
    if results:
        print("\nLive Trading Results:")
        print(f"  Signals Generated: {len(results.get('signals', {}))}")
        print(f"  Trades Executed: {len(results.get('trades', []))}")
        if 'performance' in results:
            print(f"  Current Return: {results['performance']['total_return']:.2%}")
    
    if backtest_results:
        print("\nBacktest Results:")
        print(f"  Backtested Symbols: {', '.join(backtest_results['symbols_tested'])}")
        print(f"  Historical Return: {backtest_results['total_return']:.2%}")
    
    print("\nNext Steps:")
    print("1. Fine-tune ARIMA parameters")
    print("2. Add risk management rules")
    print("3. Implement position sizing")
    print("4. Add stop-loss and take-profit levels")
    
    return results, backtest_results


if __name__ == "__main__":
    # Check if running in Docker
    if os.path.exists('/.dockerenv'):
        print("Running in Docker container")
        
        # Test database connection
        db = DatabaseConnection()
        if not db.connect():
            print("ERROR: Cannot connect to database")
            print("Please ensure MySQL container is running")
            sys.exit(1)
        db.disconnect()
        
        # Run main trading system
        try:
            results, backtest = main()
        except Exception as e:
            print(f"Error running trading system: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Running locally (not in Docker)")
        print("Note: Database connection may fail if not properly configured")
        
        # Run demo mode with sample data
        from trading.arima_algorithm import run_arima_demo
        algo, demo_results = run_arima_demo()
        
        print("\nDemo completed successfully!")
        print("To run with real data, please use Docker environment")
