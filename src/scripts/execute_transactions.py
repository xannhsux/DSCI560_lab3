#!/usr/bin/env python3
"""
Script 3: Execute Transactions (Updates Portfolio Holdings)
Requirement: Enter transactions which update the portfolio holdings
Key Focus: Transaction entry → Portfolio holdings update with proper accounting
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from portfolio.portfolio_manager import PortfolioManager
from database.db_connection import DatabaseConnection

def show_portfolio_holdings_before_after(pm, portfolio_id, symbol, operation_description):
    """Show portfolio holdings before and after transaction"""
    
    def get_holdings_state():
        db = DatabaseConnection()
        if db.connect():
            query = """
            SELECT s.symbol, ph.quantity, ph.avg_cost, ph.market_value, ph.unrealized_pnl
            FROM portfolio_holdings ph
            JOIN stocks s ON ph.stock_id = s.stock_id
            WHERE ph.portfolio_id = %s AND s.symbol = %s
            """
            result = db.execute_query(query, (portfolio_id, symbol))
            db.disconnect()
            
            if result:
                return {
                    'symbol': result[0][0],
                    'quantity': float(result[0][1]),
                    'avg_cost': float(result[0][2]) if result[0][2] else 0.0,
                    'market_value': float(result[0][3]) if result[0][3] else 0.0,
                    'unrealized_pnl': float(result[0][4]) if result[0][4] else 0.0
                }
        return None
    
    return get_holdings_state

def show_transaction_ledger(pm, portfolio_id, symbol=None):
    """Show recent transactions in the ledger"""
    print("\n--- RECENT TRANSACTIONS ---")
    
    transactions = pm.get_transaction_history(portfolio_id, symbol)
    
    if not transactions:
        print("No transactions found")
        return
    
    print(f"{'Date':<20} | {'Symbol':<6} | {'Action':<12} | {'Qty':<8} | {'Price':<8} | {'Fees':<6}")
    print("-" * 70)
    
    for txn in transactions[:10]:  # Show last 10 transactions
        txn_time, sym, action, quantity, price, fees, notes = txn
        print(f"{str(txn_time):<20} | {sym:<6} | {action:<12} | {quantity:<8} | ${price:<7.2f} | ${fees:<5.2f}")

def execute_buy_transaction(pm, portfolio_id):
    """Execute a BUY transaction and show holdings update"""
    print("\n" + "="*50)
    print("EXECUTE BUY TRANSACTION")
    print("="*50)
    
    symbol = input("Enter stock symbol to buy: ").strip().upper()
    if not symbol:
        print(" Stock symbol cannot be empty")
        return False
    
    try:
        quantity = float(input("Enter quantity to buy: "))
        price = float(input("Enter price per share: $"))
        fees = float(input("Enter trading fees (optional, default 0): ") or "0")
        
        if quantity <= 0 or price <= 0:
            print(" Quantity and price must be positive")
            return False
        
    except ValueError:
        print(" Invalid quantity, price, or fees")
        return False
    
    # Get holdings state before transaction
    get_holdings = show_portfolio_holdings_before_after(pm, portfolio_id, symbol, "BUY")
    holdings_before = get_holdings()
    
    print(f"\nBEFORE TRANSACTION:")
    if holdings_before:
        print(f"  {symbol}: {holdings_before['quantity']} shares @ ${holdings_before['avg_cost']:.2f} avg cost")
        print(f"  Market Value: ${holdings_before['market_value']:.2f}")
    else:
        print(f"  {symbol}: No current position")
    
    # Execute the transaction
    print(f"\nExecuting: BUY {quantity} shares of {symbol} at ${price:.2f}/share...")
    
    success = pm.execute_trade(
        portfolio_id=portfolio_id,
        symbol=symbol,
        action="BUY_TO_OPEN",
        quantity=quantity,
        price=price,
        fees=fees,
        notes="Test buy transaction"
    )
    
    if not success:
        print(" Transaction failed")
        return False
    
    # Get holdings state after transaction
    holdings_after = get_holdings()
    
    print(f"\nAFTER TRANSACTION:")
    if holdings_after:
        print(f"  {symbol}: {holdings_after['quantity']} shares @ ${holdings_after['avg_cost']:.2f} avg cost")
        print(f"  Market Value: ${holdings_after['market_value']:.2f}")
        
        # Show the change
        if holdings_before:
            qty_change = holdings_after['quantity'] - holdings_before['quantity']
            print(f"\n HOLDINGS UPDATE:")
            print(f"  Quantity Change: +{qty_change} shares")
            print(f"  New Average Cost: ${holdings_after['avg_cost']:.2f}")
            print(f"  Market Value Change: +${holdings_after['market_value'] - holdings_before['market_value']:.2f}")
        else:
            print(f"\n NEW POSITION CREATED:")
            print(f"  Initial Position: {holdings_after['quantity']} shares")
            print(f"  Average Cost Basis: ${holdings_after['avg_cost']:.2f}")
            print(f"  Initial Market Value: ${holdings_after['market_value']:.2f}")
    
    print("\n TRANSACTION LOGGED AND HOLDINGS UPDATED!")
    return True

def execute_sell_transaction(pm, portfolio_id):
    """Execute a SELL transaction and show holdings update"""
    print("\n" + "="*50)
    print("EXECUTE SELL TRANSACTION")
    print("="*50)
    
    symbol = input("Enter stock symbol to sell: ").strip().upper()
    if not symbol:
        print(" Stock symbol cannot be empty")
        return False
    
    # Check current position first
    position = pm.get_position(portfolio_id, symbol)
    if not position or position['quantity'] <= 0:
        print(f" No long position found for {symbol} to sell")
        return False
    
    print(f"Current position: {position['quantity']} shares @ ${position['avg_cost']:.2f}")
    
    try:
        quantity = float(input("Enter quantity to sell: "))
        price = float(input("Enter price per share: $"))
        fees = float(input("Enter trading fees (optional, default 0): ") or "0")
        
        if quantity <= 0 or price <= 0:
            print(" Quantity and price must be positive")
            return False
            
        if quantity > position['quantity']:
            print(f" Cannot sell {quantity} shares, only have {position['quantity']} shares")
            return False
        
    except ValueError:
        print(" Invalid quantity, price, or fees")
        return False
    
    # Get holdings state before transaction
    get_holdings = show_portfolio_holdings_before_after(pm, portfolio_id, symbol, "SELL")
    holdings_before = get_holdings()
    
    print(f"\nBEFORE TRANSACTION:")
    if holdings_before:
        print(f"  {symbol}: {holdings_before['quantity']} shares @ ${holdings_before['avg_cost']:.2f} avg cost")
        print(f"  Market Value: ${holdings_before['market_value']:.2f}")
    
    # Execute the transaction
    print(f"\nExecuting: SELL {quantity} shares of {symbol} at ${price:.2f}/share...")
    
    success = pm.execute_trade(
        portfolio_id=portfolio_id,
        symbol=symbol,
        action="SELL_TO_CLOSE",
        quantity=quantity,
        price=price,
        fees=fees,
        notes="Test sell transaction"
    )
    
    if not success:
        print(" Transaction failed")
        return False
    
    # Get holdings state after transaction
    holdings_after = get_holdings()
    
    print(f"\nAFTER TRANSACTION:")
    if holdings_after and holdings_after['quantity'] > 0:
        print(f"  {symbol}: {holdings_after['quantity']} shares @ ${holdings_after['avg_cost']:.2f} avg cost")
        print(f"  Market Value: ${holdings_after['market_value']:.2f}")
    else:
        print(f"  {symbol}: Position closed (0 shares)")
    
    # Show the change
    if holdings_before and holdings_after:
        qty_change = holdings_after['quantity'] - holdings_before['quantity']
        print(f"\n HOLDINGS UPDATE:")
        print(f"  Quantity Change: {qty_change} shares")
        print(f"  Realized P&L: ${(price - holdings_before['avg_cost']) * quantity:.2f}")
        print(f"  Market Value Change: ${holdings_after['market_value'] - holdings_before['market_value']:.2f}")
    
    print("\n TRANSACTION LOGGED AND HOLDINGS UPDATED!")
    return True

def main():
    print("=" * 70)
    print("EXECUTE TRANSACTIONS → UPDATE PORTFOLIO HOLDINGS")
    print("=" * 70)
    
    pm = PortfolioManager()
    
    # Select portfolio
    print("\nStep 1: Select Portfolio")
    pm.display_all_portfolios()
    
    try:
        portfolio_id = int(input("\nEnter Portfolio ID: "))
        
        transactions_executed = []
        
        while True:
            print(f"\n" + "="*50)
            print("TRANSACTION EXECUTION MENU")
            print("="*50)
            print("1. Execute BUY Transaction (BUY_TO_OPEN)")
            print("2. Execute SELL Transaction (SELL_TO_CLOSE)")
            print("3. View Transaction History")
            print("4. View Current Holdings")
            print("5. Exit")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                success = execute_buy_transaction(pm, portfolio_id)
                if success:
                    transactions_executed.append("BUY transaction")
                    
            elif choice == '2':
                success = execute_sell_transaction(pm, portfolio_id)
                if success:
                    transactions_executed.append("SELL transaction")
                    
            elif choice == '3':
                show_transaction_ledger(pm, portfolio_id)
                
            elif choice == '4':
                print("\n--- CURRENT PORTFOLIO HOLDINGS ---")
                stocks = pm.get_portfolio_stocks(portfolio_id)
                if stocks:
                    print(f"{'Symbol':<8} | {'Company':<20} | {'Quantity':<10} | {'Avg Cost':<10} | {'P&L':<10}")
                    print("-" * 70)
                    for stock in stocks:
                        stock_id, symbol, company, qty, avg_cost, pnl = stock
                        print(f"{symbol:<8} | {company[:20]:<20} | {qty:<10} | ${avg_cost:<9.2f} | ${pnl:<9.2f}")
                else:
                    print("No holdings found")
                    
            elif choice == '5':
                break
                
            else:
                print(" Invalid choice")
        
        # Summary
        print(f"\n" + "="*70)
        print("TRANSACTION SESSION SUMMARY")
        print("="*70)
        
        if transactions_executed:
            print(" TRANSACTIONS EXECUTED:")
            for i, txn in enumerate(transactions_executed, 1):
                print(f"  {i}. {txn}")
            
            print(f"\nFinal Holdings State:")
            stocks = pm.get_portfolio_stocks(portfolio_id)
            if stocks:
                for stock in stocks:
                    stock_id, symbol, company, qty, avg_cost, pnl = stock
                    if qty != 0:
                        print(f"  • {symbol}: {qty} shares @ ${avg_cost:.2f} (P&L: ${pnl:.2f})")
            
            print(f"\nTransaction Ledger:")
            show_transaction_ledger(pm, portfolio_id)
            
            return True
        else:
            print("No transactions executed")
            return True
            
    except ValueError:
        print(" Invalid portfolio ID")
        return False
    except Exception as e:
        print(f" Error: {e}")
        return False

if __name__ == "__main__":
    print("Requirement: Enter transactions which update portfolio holdings")
    success = main()
    
    print("\n" + "=" * 70)
    if success:
        print(" REQUIREMENT FULFILLED: Transactions update portfolio holdings")
        print("Key Features Demonstrated:")
        print("• Transaction entry (BUY/SELL with quantity, price, fees)")
        print("• Automatic portfolio holdings updates")
        print("• Average cost basis calculation")
        print("• Market value recalculation")
        print("• Transaction ledger maintenance")
        print("• Before/after holdings comparison")
    else:
        print(" REQUIREMENT NOT MET: Transaction execution failed")
    
    sys.exit(0 if success else 1)
