#!/usr/bin/env python3
"""
Script 1: Create Portfolio with Stock List
Requirement: User should have option to create a portfolio and define a list of stocks to be included
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from portfolio.portfolio_manager import PortfolioManager
from database.db_connection import DatabaseConnection

def create_new_user():
    """Create a new user"""
    print("\n" + "="*40)
    print("CREATE NEW USER")
    print("="*40)
    
    username = input("Enter username: ").strip()
    if not username:
        print(" Username cannot be empty")
        return None
    
    email = input("Enter email (optional): ").strip()
    
    db = DatabaseConnection()
    if db.connect():
        try:
            # Check if username already exists
            check_query = "SELECT user_id FROM users WHERE username = %s"
            existing = db.execute_query(check_query, (username,))
            
            if existing:
                print(f"  Username '{username}' already exists")
                db.disconnect()
                return None
            
            # Create new user
            insert_query = """
            INSERT INTO users (username, email) 
            VALUES (%s, %s)
            """
            result = db.execute_update(insert_query, (username, email))
            
            if result > 0:
                # Get the new user ID
                user_id_result = db.execute_query("SELECT LAST_INSERT_ID()")
                if user_id_result:
                    user_id = user_id_result[0][0]
                    print(f"  User '{username}' created successfully with ID: {user_id}")
                    # Ensure the transaction is committed
                    if hasattr(db.connection, 'commit'):
                        db.connection.commit()
                    db.disconnect()
                    return user_id
                else:
                    print("  Failed to get new user ID")
                    db.disconnect()
                    return None
            else:
                print("  Failed to insert new user")
                db.disconnect()
                return None
                
        except Exception as e:
            print(f"  Error creating user: {e}")
            db.disconnect()
            return None
    else:
        print("  Could not connect to database")
        return None

def main():
    print("=" * 60)
    print("CREATE PORTFOLIO WITH STOCK LIST")
    print("=" * 60)
    
    pm = PortfolioManager()
    
    # Display available users
    print("\nStep 1: Select or Create User")
    users = pm.display_active_users()
    
    print("\nOptions:")
    print("• Enter existing User ID (e.g., 1, 2)")
    print("• Enter 'new' to create a new user")
    
    user_choice = input("\nEnter User ID or 'new': ").strip().lower()
    
    try:
        if user_choice == 'new':
            user_id = create_new_user()
            if user_id is None:
                print("  Failed to create new user")
                return False
            
            # Refresh the PortfolioManager's database connection to see the new user
            print("Refreshing database connection...")
            pm.db.disconnect()
            if not pm.db.connect():
                print("  Failed to reconnect to database")
                return False
        else:
            user_id = int(user_choice)
            
            # Validate user exists
            if not users:
                print("  No active users found")
                return False
            
            # Check if user_id exists in the users list
            user_ids = [user[0] for user in users]  # Assuming user[0] is user_id
            if user_id not in user_ids:
                print(f"  User ID {user_id} not found")
                return False
        
        # Get portfolio details
        print("\nStep 2: Portfolio Details")
        portfolio_name = input("Enter portfolio name: ").strip()
        description = input("Enter portfolio description (optional): ").strip()
        
        if not portfolio_name:
            print(" Portfolio name cannot be empty")
            return False
        
        # Get stock list
        print("\nStep 3: Define Stock List")
        print("Enter stock symbols separated by commas (e.g., AAPL,GOOGL,MSFT,TSLA)")
        stocks_input = input("Stock symbols: ").strip()
        
        if not stocks_input:
            print(" No stocks specified")
            return False
        
        stock_symbols = [symbol.strip().upper() for symbol in stocks_input.split(',')]
        
        print(f"\nCreating portfolio '{portfolio_name}' with stocks: {', '.join(stock_symbols)}")
        print("Validating stocks and creating portfolio...")
        
        # Create portfolio with stocks
        success = pm.create_portfolio_with_stocks(
            portfolio_name, 
            stock_symbols, 
            description, 
            user_id
        )
        
        if success:
            print(f"\n SUCCESS!")
            print(f"Portfolio '{portfolio_name}' created with {len(stock_symbols)} stocks")
            
            # Show the created portfolio
            print("\nPortfolio Details:")
            pm.display_enhanced_portfolios()
            return True
        else:
            print(f"\n FAILED to create portfolio")
            return False
            
    except ValueError:
        print(" Invalid user ID")
        return False
    except Exception as e:
        print(f" Error: {e}")
        return False

if __name__ == "__main__":
    print("Requirement: Create portfolio and define list of stocks to be included")
    success = main()
    
    print("\n" + "=" * 60)
    if success:
        print("  REQUIREMENT FULFILLED: Portfolio created with stock list")
        print("  NEW FEATURE: User creation functionality added!")
        print("Key Features Demonstrated:")
        print("• Create new users or select existing ones")
        print("• Portfolio creation with comprehensive validation")
        print("• Stock list input with comma-separated symbols")
        print("• Automatic stock validation via Yahoo Finance")
        print("• Real-time portfolio display after creation")
    else:
        print("  REQUIREMENT NOT MET: Failed to create portfolio")
    
    print("\nNext steps:")
    print("• Use 'manage_portfolio_stocks.py' to add/remove stocks")
    print("• Use 'execute_transactions.py' to buy/sell stocks")
    sys.exit(0 if success else 1)
