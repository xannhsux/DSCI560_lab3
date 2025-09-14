#!/usr/bin/env python3
"""
Script 2: Manage Portfolio Stocks (Add/Remove Operations)
Requirement: User should be able to add/remove stocks from portfolio with validation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from portfolio.portfolio_manager import PortfolioManager
from database.db_connection import DatabaseConnection

def add_stock_to_portfolio(pm, portfolio_id):
    """Add a stock to portfolio with validation"""
    print("\n--- ADD STOCK TO PORTFOLIO ---")
    
    symbol = input("Enter stock symbol to add: ").strip().upper()
    if not symbol:
        print(" Stock symbol cannot be empty")
        return False
    
    print(f"Validating stock symbol '{symbol}'...")
    
    # Validate stock using Yahoo Finance
    if not pm.validator.validate_stock(symbol):
        print(f" INVALID STOCK NAME: '{symbol}' is not a valid stock symbol")
        return False
    
    # Add stock to portfolio
    success = pm.add_stock_to_portfolio(portfolio_id, symbol)
    
    if success:
        print(f" ADDED SUCCESSFULLY: '{symbol}' added to portfolio")
        return True
    else:
        print(f" Failed to add '{symbol}' to portfolio")
        return False

def remove_stock_from_portfolio(pm, portfolio_id):
    """Remove a stock from portfolio"""
    print("\n--- REMOVE STOCK FROM PORTFOLIO ---")
    
    symbol = input("Enter stock symbol to remove: ").strip().upper()
    if not symbol:
        print(" Stock symbol cannot be empty")
        return False
    
    success = pm.remove_stock_from_portfolio(portfolio_id, symbol)
    
    if success:
        print(f" REMOVED SUCCESSFULLY: '{symbol}' removed from portfolio")
        return True
    else:
        print(f" Failed to remove '{symbol}' from portfolio")
        return False

def display_portfolio_details(pm, portfolio_id):
    """Display detailed portfolio information"""
    print("\n--- PORTFOLIO DETAILS ---")
    
    details = pm.get_portfolio_with_details(portfolio_id)
    if not details:
        print(" Portfolio not found")
        return False
    
    print(f"Portfolio Name: {details['name']}")
    print(f"Owner: {details['username']}")
    print(f"Created: {details['created_date']}")
    print(f"Description: {details['description']}")
    print(f"Total Market Value: ${details['total_market_value']:.2f}")
    
    print(f"\nStocks in Portfolio ({len(details['stocks'])}):")
    if details['stocks']:
        for stock in details['stocks']:
            if stock['quantity'] != 0:
                print(f"  • {stock['symbol']} ({stock['company_name']}): {stock['quantity']} shares @ ${stock['avg_cost']:.2f}")
            else:
                print(f"  • {stock['symbol']} ({stock['company_name']}): Watchlist")
    else:
        print("  No stocks in portfolio")
    
    return True

def main():
    print("=" * 60)
    print("MANAGE PORTFOLIO STOCKS")
    print("=" * 60)
    
    pm = PortfolioManager()
    
    # Display available portfolios
    print("\nStep 1: Select Portfolio")
    pm.display_all_portfolios()
    
    try:
        portfolio_id = int(input("\nEnter Portfolio ID: "))
        
        # Verify portfolio exists and show current state
        if not display_portfolio_details(pm, portfolio_id):
            return False
        
        operations_performed = []
        
        while True:
            print(f"\n" + "=" * 40)
            print("PORTFOLIO MANAGEMENT OPTIONS")
            print("=" * 40)
            print("1. Add Stock to Portfolio")
            print("2. Remove Stock from Portfolio") 
            print("3. View Portfolio Details")
            print("4. Exit")
            
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == '1':
                success = add_stock_to_portfolio(pm, portfolio_id)
                if success:
                    operations_performed.append("Added stock")
                    
            elif choice == '2':
                success = remove_stock_from_portfolio(pm, portfolio_id)
                if success:
                    operations_performed.append("Removed stock")
                    
            elif choice == '3':
                display_portfolio_details(pm, portfolio_id)
                
            elif choice == '4':
                break
                
            else:
                print(" Invalid choice")
        
        # Summary
        print(f"\n" + "=" * 60)
        print("PORTFOLIO MANAGEMENT SESSION COMPLETE")
        print("=" * 60)
        
        if operations_performed:
            print(" OPERATIONS PERFORMED:")
            for i, op in enumerate(operations_performed, 1):
                print(f"  {i}. {op}")
            
            print("\nFinal Portfolio State:")
            display_portfolio_details(pm, portfolio_id)
            return True
        else:
            print("No changes made to portfolio")
            return True
            
    except ValueError:
        print(" Invalid portfolio ID")
        return False
    except Exception as e:
        print(f" Error: {e}")
        return False

if __name__ == "__main__":
    print("Requirement: Manage portfolio with add/remove operations and validation")
    success = main()
    
    print("\n" + "=" * 60)
    if success:
        print(" REQUIREMENT FULFILLED: Portfolio management with validation")
        print("Key Features Demonstrated:")
        print("• Add stock to portfolio with validation")
        print("• Remove stock from portfolio")
        print("• Display appropriate messages ('added successfully', 'invalid stock name')")
        print("• Real-time portfolio state updates")
    else:
        print(" REQUIREMENT NOT MET: Portfolio management failed")
    
    sys.exit(0 if success else 1)
