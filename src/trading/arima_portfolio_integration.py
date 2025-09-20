#!/usr/bin/env python3
"""ARIMA portfolio integration and backtesting utilities."""

import os
import sys
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Ensure repo modules are importable when running as a script
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.db_connection import DatabaseConnection
from portfolio.portfolio_manager import PortfolioManager
from data.data_collector import DataCollector
from trading.arima_algorithm import ARIMATradingAlgorithm


class MockTradingEnvironment:
    """Utility class for evaluating a stream of portfolio values."""

    def __init__(self, initial_capital: float = 10000.0, risk_free_rate: float = 0.02) -> None:
        self.initial_capital = float(initial_capital)
        self.risk_free_rate = risk_free_rate

    def evaluate_series(self, value_series: pd.Series) -> Dict[str, float]:
        values = pd.Series(value_series, dtype=float)

        if values.empty:
            return {
                "initial_value": self.initial_capital,
                "final_value": self.initial_capital,
                "total_return": 0.0,
                "annualized_return": 0.0,
                "annualized_volatility": 0.0,
                "sharpe_ratio": np.nan,
                "value_series": values
            }

        returns = values.pct_change().dropna()
        initial_value = values.iloc[0]
        final_value = values.iloc[-1]
        total_return = (final_value - initial_value) / initial_value if initial_value else 0.0

        if returns.empty:
            annualized_return = 0.0
            annualized_volatility = 0.0
            sharpe_ratio = np.nan
        else:
            avg_daily_return = returns.mean()
            daily_volatility = returns.std()
            annualized_return = (1 + avg_daily_return) ** 252 - 1
            annualized_volatility = daily_volatility * np.sqrt(252)
            sharpe_ratio = (
                (annualized_return - self.risk_free_rate) / annualized_volatility
                if annualized_volatility > 0 else np.nan
            )

        return {
            "initial_value": initial_value,
            "final_value": final_value,
            "total_return": total_return,
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_volatility,
            "sharpe_ratio": sharpe_ratio,
            "value_series": values
        }


class ARIMAPortfolioTrader:
    """Run ARIMA-based trading simulations across a portfolio of stocks."""

    def __init__(
        self,
        portfolio_id: int,
        initial_capital: float = 10000.0,
        risk_free_rate: float = 0.02,
        min_history: int = 90
    ) -> None:
        self.portfolio_id = portfolio_id
        self.initial_capital = float(initial_capital)
        self.risk_free_rate = risk_free_rate
        self.min_history = min_history

        self.db = DatabaseConnection()
        self.portfolio_manager = PortfolioManager()
        self.data_collector = DataCollector()

        self.results: Optional[Dict] = None

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def fetch_stock_data_from_db(self, symbol: str, lookback_days: int = 365) -> Optional[pd.Series]:
        try:
            start_date = (datetime.utcnow() - timedelta(days=lookback_days)).date()
            query = """
                SELECT h.date, h.close_price
                FROM stock_historical_data h
                JOIN stocks s ON s.stock_id = h.stock_id
                WHERE s.symbol = %s AND h.date >= %s
                ORDER BY h.date ASC
            """
            rows = self.db.execute_query(query, (symbol, start_date))
            if not rows:
                return None

            df = pd.DataFrame(rows, columns=["date", "close_price"])
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            return df["close_price"].astype(float)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Error fetching data for {symbol}: {exc}")
            return None

    # ------------------------------------------------------------------
    # Simulation entry point
    # ------------------------------------------------------------------
    def run_portfolio_simulation(
        self,
        lookback_days: int = 365,
        train_size: float = 0.8
    ) -> Optional[Dict]:
        stocks = self.portfolio_manager.get_portfolio_stocks(self.portfolio_id)
        if not stocks:
            print("No stocks found in the selected portfolio.")
            return None

        allocation_per_stock = self.initial_capital / len(stocks)
        value_series_map: Dict[str, pd.Series] = {}
        share_series_map: Dict[str, pd.Series] = {}
        per_stock_reports: Dict[str, Dict] = {}
        trade_log: List[Dict] = []

        try:
            for stock_id, symbol, company_name, quantity, avg_cost, _ in stocks:
                print(f"\nProcessing {symbol} ({company_name})")
                price_series = self.fetch_stock_data_from_db(symbol, lookback_days)

                if price_series is None or len(price_series) < self.min_history:
                    print("  Insufficient historical data, fetching from Yahoo Finance...")
                    self.data_collector.fetch_stock_data(symbol, period='2y')
                    price_series = self.fetch_stock_data_from_db(symbol, lookback_days)

                if price_series is None or len(price_series) < self.min_history:
                    print(f"  Skipping {symbol}; still insufficient data after refresh.")
                    continue

                algo = ARIMATradingAlgorithm(
                    confidence_threshold=0.02,
                    prediction_horizon=5
                )

                backtest = algo.backtest(
                    price_series,
                    train_size=train_size,
                    initial_capital=allocation_per_stock
                )

                portfolio = backtest['portfolio']
                portfolio_values = portfolio.get('portfolio_values', [])
                share_history = portfolio.get('share_history', [])

                value_series = pd.Series([allocation_per_stock] + portfolio_values, dtype=float)
                share_series = pd.Series([0.0] + share_history, dtype=float)
                value_series.index = range(len(value_series))
                share_series.index = range(len(share_series))

                value_series_map[symbol] = value_series
                share_series_map[symbol] = share_series

                per_stock_reports[symbol] = {
                    'final_value': backtest['final_value'],
                    'total_return': backtest['total_return'],
                    'buy_hold_return': backtest['buy_hold_return'],
                    'excess_return': backtest['excess_return'],
                    'trades': portfolio.get('trades', []),
                    'value_series': value_series,
                    'share_series': share_series,
                    'timeline': portfolio.get('timeline', [])
                }

                for trade in portfolio.get('trades', []):
                    trade_log.append({
                        'symbol': symbol,
                        'date': trade['date'],
                        'action': trade['action'],
                        'price': float(trade['price']),
                        'shares': float(trade['shares']),
                        'value': float(trade['value'])
                    })
        finally:
            self.db.disconnect()

        if not value_series_map:
            print("Portfolio simulation skipped: no stocks contained sufficient data.")
            return None

        value_history = self._align_series(value_series_map)
        share_history = self._align_series(share_series_map)
        total_values = value_history.sum(axis=1)

        metrics = self._calculate_portfolio_metrics(total_values)

        self.results = {
            'value_history': value_history,
            'share_history': share_history,
            'total_values': total_values,
            'metrics': metrics,
            'trade_log': trade_log,
            'per_stock': per_stock_reports
        }

        return self.results

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def _align_series(self, series_map: Dict[str, pd.Series]) -> pd.DataFrame:
        max_length = max(len(series) for series in series_map.values())
        target_index = range(max_length)

        aligned = {}
        for symbol, series in series_map.items():
            aligned[symbol] = (
                series.reindex(target_index)
                .ffill()
                .bfill()
            )

        return pd.DataFrame(aligned, index=target_index)

    def _calculate_portfolio_metrics(self, total_values: pd.Series) -> Dict[str, float]:
        env = MockTradingEnvironment(
            initial_capital=self.initial_capital,
            risk_free_rate=self.risk_free_rate
        )
        metrics = env.evaluate_series(total_values)
        return metrics

    def print_report(self, results: Optional[Dict] = None, sample_trades: int = 5) -> None:
        if results is None:
            results = self.results

        if not results:
            print("No simulation results to display. Run run_portfolio_simulation() first.")
            return

        metrics = results['metrics']
        value_history = results['value_history']
        share_history = results['share_history']

        print("\n=== PORTFOLIO PERFORMANCE SUMMARY ===")
        print(f"Initial Capital: ${metrics['initial_value']:,.2f}")
        print(f"Final Portfolio Value: ${metrics['final_value']:,.2f}")
        print(f"Total Return: {metrics['total_return']:.2%}")
        print(f"Annualized Return: {metrics['annualized_return']:.2%}")
        print(f"Annualized Volatility: {metrics['annualized_volatility']:.2%}")
        sharpe = metrics['sharpe_ratio']
        sharpe_str = f"{sharpe:.2f}" if not pd.isna(sharpe) else "N/A"
        print(f"Sharpe Ratio: {sharpe_str}")

        print("\nFinal Share Holdings:")
        final_holdings = share_history.iloc[-1]
        for symbol, shares in final_holdings.items():
            print(f"  {symbol}: {shares:.2f} shares")

        print("\nPer-Stock Results:")
        for symbol, report in results['per_stock'].items():
            print(
                f"  {symbol}: Return {report['total_return']:.2%}, "
                f"Final Value ${report['final_value']:.2f}, Trades {len(report['trades'])}"
            )

        if results['trade_log']:
            print("\nSample Trades:")
            for trade in results['trade_log'][:sample_trades]:
                trade_date = trade['date']
                date_str = trade_date.strftime('%Y-%m-%d') if hasattr(trade_date, 'strftime') else trade_date
                print(
                    f"  {date_str} - {trade['symbol']} {trade['action']} "
                    f"{trade['shares']:.0f} @ ${trade['price']:.2f}"
                )

        print("\nPortfolio value history is available via results['value_history'].")


def main() -> None:
    print("ARIMA PORTFOLIO TRADING ANALYSIS")

    try:
        portfolio_id = int(input("Enter Portfolio ID: ").strip())
    except ValueError:
        print("Invalid portfolio ID provided.")
        return

    capital_input = input("Enter initial capital (default 10000): ").strip()
    initial_capital = float(capital_input) if capital_input else 10000.0

    trader = ARIMAPortfolioTrader(
        portfolio_id=portfolio_id,
        initial_capital=initial_capital
    )

    results = trader.run_portfolio_simulation()
    if results:
        trader.print_report(results)
    
    

if __name__ == "__main__":
    main()
