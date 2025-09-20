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


# ===================== MOCK TRADING ENVIRONMENT =====================

class MockTradingEnvironment:
    def __init__(self, initial_capital=10000, risk_free_rate=0.02):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.shares = 0
        self.portfolio_values = []
        self.risk_free_rate = risk_free_rate  # 年化无风险利率

    def step(self, price, signal):
        """
        price: 当前价格
        signal: "BUY" / "SELL" / "HOLD"
        """
        if signal == "BUY" and self.cash > price:
            shares_to_buy = int(self.cash / price)
            self.shares += shares_to_buy
            self.cash -= shares_to_buy * price
        elif signal == "SELL" and self.shares > 0:
            self.cash += self.shares * price
            self.shares = 0

        portfolio_value = self.cash + self.shares * price
        self.portfolio_values.append(portfolio_value)
        return portfolio_value

    def evaluate(self):
        values = pd.Series(self.portfolio_values)
        returns = values.pct_change().dropna()

        total_return = (values.iloc[-1] - values.iloc[0]) / values.iloc[0]
        avg_daily_return = returns.mean()
        daily_volatility = returns.std()

        # 年化 (252 个交易日)
        ann_return = (1 + avg_daily_return) ** 252 - 1 if not returns.empty else 0
        ann_volatility = daily_volatility * np.sqrt(252) if not returns.empty else 0
        sharpe_ratio = (ann_return - self.risk_free_rate) / ann_volatility if ann_volatility > 0 else np.nan

        return {
            "final_value": values.iloc[-1],
            "total_return": total_return,
            "annualized_return": ann_return,
            "annualized_volatility": ann_volatility,
            "sharpe_ratio": sharpe_ratio
        }


# ===================== PORTFOLIO TRADER =====================

class ARIMAPortfolioTrader:
    """
    Integration class that connects ARIMA algorithm with portfolio management
    """

    def __init__(self, portfolio_id, initial_capital=10000):
        self.portfolio_id = portfolio_id
        self.initial_capital = initial_capital

        self.db = DatabaseConnection()
        self.portfolio_manager = PortfolioManager()
        self.data_collector = DataCollector()
        self.arima_algo = ARIMATradingAlgorithm(
            confidence_threshold=0.02,
            prediction_horizon=5
        )

        s
