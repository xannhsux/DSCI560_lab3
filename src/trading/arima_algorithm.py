#!/usr/bin/env python3
"""
ARIMA-based Trading Algorithm for Stock Price Prediction
DSCI-560 Lab 4: Algorithm Development
"""

import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class ARIMATradingAlgorithm:
    """
    ARIMA-based trading algorithm for stock price prediction and signal generation
    
    Features:
    - Automatic ARIMA order selection using AIC/BIC
    - Stationarity testing and differencing
    - Buy/Sell signal generation based on predictions
    - Performance metrics calculation
    """
    
    def __init__(self, confidence_threshold=0.02, prediction_horizon=5):
        """
        Initialize ARIMA trading algorithm
        
        Args:
            confidence_threshold: Minimum predicted return to generate signals (2% default)
            prediction_horizon: Number of days to predict ahead (5 days default)
        """
        self.confidence_threshold = confidence_threshold
        self.prediction_horizon = prediction_horizon
        self.model = None
        self.best_order = None
        self.predictions = None
        self.signals = []
        
    def test_stationarity(self, timeseries, significance_level=0.05):
        """
        Test if time series is stationary using Augmented Dickey-Fuller test
        
        Args:
            timeseries: Price series to test
            significance_level: Significance level for test (default 0.05)
            
        Returns:
            tuple: (is_stationary, adf_statistic, p_value, critical_values)
        """
        result = adfuller(timeseries, autolag='AIC')
        
        adf_statistic = result[0]
        p_value = result[1]
        critical_values = result[4]
        
        is_stationary = p_value < significance_level
        
        print(f"ADF Statistic: {adf_statistic:.6f}")
        print(f"p-value: {p_value:.6f}")
        print(f"Critical Values:")
        for key, value in critical_values.items():
            print(f"   {key}: {value:.3f}")
        
        if is_stationary:
            print("✓ Series is stationary")
        else:
            print("✗ Series is non-stationary (needs differencing)")
            
        return is_stationary, adf_statistic, p_value, critical_values
    
    def find_optimal_order(self, timeseries, max_p=5, max_d=2, max_q=5, seasonal=False):
        """
        Find optimal ARIMA order using grid search with AIC/BIC criteria
        
        Args:
            timeseries: Price series to fit
            max_p: Maximum AR order to test
            max_d: Maximum differencing order to test  
            max_q: Maximum MA order to test
            seasonal: Whether to include seasonal components
            
        Returns:
            tuple: Best (p, d, q) order based on AIC
        """
        print("\nSearching for optimal ARIMA parameters...")
        
        best_aic = np.inf
        best_bic = np.inf
        best_order = None
        best_model = None
        
        # Test for stationarity to determine d
        is_stationary, _, _, _ = self.test_stationarity(timeseries)
        
        if is_stationary:
            d_range = [0]
        else:
            d_range = range(1, max_d + 1)
        
        results = []
        
        for d in d_range:
            for p in range(max_p + 1):
                for q in range(max_q + 1):
                    # Skip the (0,0,0) model
                    if p == 0 and d == 0 and q == 0:
                        continue
                        
                    try:
                        model = ARIMA(timeseries, order=(p, d, q))
                        fitted_model = model.fit()
                        
                        aic = fitted_model.aic
                        bic = fitted_model.bic
                        
                        results.append({
                            'order': (p, d, q),
                            'AIC': aic,
                            'BIC': bic
                        })
                        
                        if aic < best_aic:
                            best_aic = aic
                            best_bic = bic
                            best_order = (p, d, q)
                            best_model = fitted_model
                            
                        print(f"   ARIMA{(p,d,q)} - AIC: {aic:.2f}, BIC: {bic:.2f}")
                        
                    except Exception as e:
                        continue
        
        print(f"\n✓ Best ARIMA order: {best_order}")
        print(f"  AIC: {best_aic:.2f}")
        print(f"  BIC: {best_bic:.2f}")
        
        self.best_order = best_order
        return best_order, best_model, results
    
    def fit_arima(self, train_data, order=None):
        """
        Fit ARIMA model to training data
        
        Args:
            train_data: Training price data
            order: ARIMA order tuple (p,d,q), if None will auto-select
            
        Returns:
            Fitted ARIMA model
        """
        if order is None:
            order, model, _ = self.find_optimal_order(train_data)
            self.model = model
        else:
            self.best_order = order
            arima_model = ARIMA(train_data, order=order)
            self.model = arima_model.fit()
            
        print(f"\n✓ ARIMA{self.best_order} model fitted successfully")
        
        # Print model summary
        print("\nModel Summary:")
        print(self.model.summary().tables[1])
        
        return self.model
    
    def predict_prices(self, steps_ahead=None):
        """
        Generate price predictions using fitted ARIMA model
        
        Args:
            steps_ahead: Number of periods to forecast
            
        Returns:
            DataFrame with predictions and confidence intervals
        """
        if self.model is None:
            raise ValueError("Model must be fitted before prediction")
            
        if steps_ahead is None:
            steps_ahead = self.prediction_horizon
            
        # Generate forecast
        forecast_result = self.model.forecast(steps=steps_ahead)
        
        # Get prediction intervals
        forecast_df = pd.DataFrame({
            'prediction': forecast_result,
            'date': pd.date_range(
                start=pd.Timestamp.today(), 
                periods=steps_ahead, 
                freq='D'
            )
        })
        
        self.predictions = forecast_df
        
        print(f"\n✓ Generated {steps_ahead}-day price predictions")
        print(forecast_df)
        
        return forecast_df
    
    def generate_signals(self, current_price, predictions=None):
        """
        Generate trading signals based on ARIMA predictions
        
        Args:
            current_price: Current stock price
            predictions: Price predictions (uses self.predictions if None)
            
        Returns:
            dict: Trading signal with action and confidence
        """
        if predictions is None:
            predictions = self.predictions
            
        if predictions is None or predictions.empty:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No predictions available'}
        
        # Calculate expected returns
        predicted_price = predictions['prediction'].iloc[-1]  # Use last prediction
        expected_return = (predicted_price - current_price) / current_price
        
        # Generate signal based on threshold
        signal = {}
        
        if expected_return > self.confidence_threshold:
            signal = {
                'action': 'BUY',
                'confidence': min(expected_return / self.confidence_threshold, 1.0),
                'expected_return': expected_return,
                'predicted_price': predicted_price,
                'current_price': current_price,
                'reason': f'Expected return of {expected_return:.2%} exceeds threshold'
            }
        elif expected_return < -self.confidence_threshold:
            signal = {
                'action': 'SELL',
                'confidence': min(abs(expected_return) / self.confidence_threshold, 1.0),
                'expected_return': expected_return,
                'predicted_price': predicted_price,
                'current_price': current_price,
                'reason': f'Expected loss of {expected_return:.2%} exceeds threshold'
            }
        else:
            signal = {
                'action': 'HOLD',
                'confidence': 1.0 - abs(expected_return) / self.confidence_threshold,
                'expected_return': expected_return,
                'predicted_price': predicted_price,
                'current_price': current_price,
                'reason': f'Expected return of {expected_return:.2%} within threshold'
            }
        
        self.signals.append({
            'timestamp': datetime.now(),
            'signal': signal
        })
        
        return signal
    
    def backtest(self, price_data, train_size=0.8, initial_capital=10000):
        """
        Backtest the ARIMA trading strategy
        
        Args:
            price_data: Historical price data
            train_size: Proportion of data for training
            initial_capital: Starting capital for backtesting
            
        Returns:
            dict: Backtesting results with performance metrics
        """
        # Split data
        split_idx = int(len(price_data) * train_size)
        train_data = price_data[:split_idx]
        test_data = price_data[split_idx:]
        
        print(f"\n=== Backtesting ARIMA Strategy ===")
        print(f"Training samples: {len(train_data)}")
        print(f"Testing samples: {len(test_data)}")
        
        # Fit model on training data
        self.fit_arima(train_data)
        
        # Initialize portfolio
        portfolio = {
            'cash': initial_capital,
            'shares': 0,
            'total_value': initial_capital,
            'trades': [],
            'portfolio_values': []
        }
        
        # Simulate trading
        for i in range(len(test_data) - self.prediction_horizon):
            current_price = test_data.iloc[i]
            
            # Retrain model with expanding window (optional, computationally expensive)
            # For now, use initial model
            
            # Make prediction
            forecast = self.model.forecast(steps=self.prediction_horizon)
            temp_predictions = pd.DataFrame({'prediction': forecast})
            
            # Generate signal
            signal = self.generate_signals(current_price, temp_predictions)
            
            # Execute trade based on signal
            if signal['action'] == 'BUY' and portfolio['cash'] > current_price:
                # Buy as many shares as possible
                shares_to_buy = int(portfolio['cash'] / current_price)
                if shares_to_buy > 0:
                    cost = shares_to_buy * current_price
                    portfolio['shares'] += shares_to_buy
                    portfolio['cash'] -= cost
                    
                    portfolio['trades'].append({
                        'date': i,
                        'action': 'BUY',
                        'price': current_price,
                        'shares': shares_to_buy,
                        'value': cost
                    })
                    
            elif signal['action'] == 'SELL' and portfolio['shares'] > 0:
                # Sell all shares
                revenue = portfolio['shares'] * current_price
                portfolio['cash'] += revenue
                
                portfolio['trades'].append({
                    'date': i,
                    'action': 'SELL',
                    'price': current_price,
                    'shares': portfolio['shares'],
                    'value': revenue
                })
                
                portfolio['shares'] = 0
            
            # Calculate portfolio value
            portfolio['total_value'] = portfolio['cash'] + portfolio['shares'] * current_price
            portfolio['portfolio_values'].append(portfolio['total_value'])
        
        # Calculate final metrics
        final_value = portfolio['total_value']
        total_return = (final_value - initial_capital) / initial_capital
        
        # Calculate buy-and-hold benchmark
        buy_hold_return = (test_data.iloc[-1] - test_data.iloc[0]) / test_data.iloc[0]
        
        results = {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'buy_hold_return': buy_hold_return,
            'excess_return': total_return - buy_hold_return,
            'num_trades': len(portfolio['trades']),
            'portfolio': portfolio
        }
        
        print(f"\n=== Backtest Results ===")
        print(f"Initial Capital: ${initial_capital:,.2f}")
        print(f"Final Value: ${final_value:,.2f}")
        print(f"Total Return: {total_return:.2%}")
        print(f"Buy & Hold Return: {buy_hold_return:.2%}")
        print(f"Excess Return: {results['excess_return']:.2%}")
        print(f"Number of Trades: {results['num_trades']}")
        
        return results
    
    def calculate_metrics(self, actual, predicted):
        """
        Calculate prediction accuracy metrics
        
        Args:
            actual: Actual prices
            predicted: Predicted prices
            
        Returns:
            dict: Dictionary of metrics (MAE, RMSE, MAPE)
        """
        mae = mean_absolute_error(actual, predicted)
        rmse = np.sqrt(mean_squared_error(actual, predicted))
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        
        metrics = {
            'MAE': mae,
            'RMSE': rmse,
            'MAPE': mape
        }
        
        print(f"\n=== Prediction Metrics ===")
        print(f"Mean Absolute Error (MAE): ${mae:.2f}")
        print(f"Root Mean Squared Error (RMSE): ${rmse:.2f}")
        print(f"Mean Absolute Percentage Error (MAPE): {mape:.2f}%")
        
        return metrics
    
    def plot_predictions(self, historical_data, predictions, title="ARIMA Predictions"):
        """
        Plot historical data and predictions
        
        Args:
            historical_data: Historical price data
            predictions: Predicted prices
            title: Plot title
        """
        plt.figure(figsize=(12, 6))
        
        # Plot historical data
        plt.plot(range(len(historical_data)), historical_data, 
                label='Historical', color='blue', linewidth=2)
        
        # Plot predictions
        pred_start = len(historical_data)
        pred_range = range(pred_start, pred_start + len(predictions))
        plt.plot(pred_range, predictions['prediction'], 
                label='Predictions', color='red', linewidth=2, linestyle='--')
        
        plt.xlabel('Time')
        plt.ylabel('Price ($)')
        plt.title(title)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()


def run_arima_demo():
    """
    Demonstration of ARIMA trading algorithm
    """
    print("=" * 80)
    print("ARIMA TRADING ALGORITHM DEMONSTRATION")
    print("=" * 80)
    
    # Generate sample data (replace with real data from your database)
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    
    # Simulate stock prices with trend and noise
    trend = np.linspace(100, 120, len(dates))
    seasonal = 5 * np.sin(np.arange(len(dates)) * 2 * np.pi / 30)
    noise = np.random.normal(0, 2, len(dates))
    prices = trend + seasonal + noise
    
    price_series = pd.Series(prices, index=dates)
    
    # Initialize ARIMA algorithm
    arima_algo = ARIMATradingAlgorithm(
        confidence_threshold=0.02,  # 2% threshold
        prediction_horizon=5         # 5-day predictions
    )
    
    # Test stationarity
    print("\n1. STATIONARITY TEST")
    print("-" * 40)
    arima_algo.test_stationarity(price_series)
    
    # Find optimal ARIMA order
    print("\n2. PARAMETER OPTIMIZATION")
    print("-" * 40)
    optimal_order, model, results = arima_algo.find_optimal_order(
        price_series,
        max_p=3,
        max_d=2,
        max_q=3
    )
    
    # Generate predictions
    print("\n3. PRICE PREDICTIONS")
    print("-" * 40)
    predictions = arima_algo.predict_prices(steps_ahead=10)
    
    # Generate trading signal
    print("\n4. TRADING SIGNAL")
    print("-" * 40)
    current_price = price_series.iloc[-1]
    signal = arima_algo.generate_signals(current_price)
    
    print(f"\nCurrent Price: ${current_price:.2f}")
    print(f"Signal: {signal['action']}")
    print(f"Confidence: {signal['confidence']:.2%}")
    print(f"Expected Return: {signal['expected_return']:.2%}")
    print(f"Reason: {signal['reason']}")
    
    # Backtest strategy
    print("\n5. BACKTESTING")
    print("-" * 40)
    backtest_results = arima_algo.backtest(
        price_series,
        train_size=0.8,
        initial_capital=10000
    )
    
    # Plot results
    print("\n6. VISUALIZATION")
    print("-" * 40)
    arima_algo.plot_predictions(price_series, predictions)
    
    return arima_algo, backtest_results


if __name__ == "__main__":
    # Run demonstration
    algo, results = run_arima_demo()
    
    print("\n" + "=" * 80)
    print("ARIMA ALGORITHM IMPLEMENTATION COMPLETE")
    print("=" * 80)
    print("\nKey Features Implemented:")
    print("✓ Automatic stationarity testing (ADF test)")
    print("✓ Optimal parameter selection using AIC/BIC")
    print("✓ ARIMA model fitting and prediction")
    print("✓ Buy/Sell signal generation with confidence levels")
    print("✓ Backtesting with performance metrics")
    print("✓ Visualization of predictions")
    
    print("\nNext Steps:")
    print("1. Integrate with your database to fetch real stock data")
    print("2. Combine with portfolio management system")
    print("3. Implement real-time trading simulation")
    print("4. Add more sophisticated risk management")