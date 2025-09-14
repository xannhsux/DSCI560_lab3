#!/usr/bin/env python3
"""
Script 5: Display Portfolios with Creation Date and Stock Lists
Requirement: Display all portfolios with creation date and list of stocks in the portfolio
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from portfolio.portfolio_manager import PortfolioManager
from database.db_connection import DatabaseConnection

def display_comprehensive_portfolio_info(pm):
    """Display comprehensive portfolio information including all required details"""
    print("=" * 80)
    print("COMPREHENSIVE PORTFOLIO DISPLAY")
    print("=" * 80)
    
    # Get all portfolios with detailed information
    query = """
    SELECT 
        p.portfolio_id, 
        p.portfolio_name, 
        p.created_date, 
        p.description, 
        u.username,
        u.user_id,
        COUNT(ph.stock_id) as stock_count,
        SUM(CASE WHEN ph.quantity != 0 THEN ph.market_value ELSE 0 END) as total_market_value
    FROM portfolios p
    LEFT JOIN users u ON p.user_id = u.user_id
    LEFT JOIN portfolio_holdings ph ON p.portfolio_id = ph.portfolio_id
    GROUP BY p.portfolio_id, p.portfolio_name, p.created_date, p.description, u.username, u.user_id
    ORDER BY p.created_date DESC
    """
    
    db = DatabaseConnection()
    if not db.connect():
        print(" Could not connect to database")
        return False
    
    try:
        portfolios = db.execute_query(query)
        
        if not portfolios:
            print(" No portfolios found in the system")
            db.disconnect()
            return True
        
        print(f"Found {len(portfolios)} portfolios in the system\n")
        
        for i, portfolio in enumerate(portfolios, 1):
            (portfolio_id, name, created_date, description, username, user_id, 
             stock_count, total_market_value) = portfolio
            
            print(f"  PORTFOLIO #{i}")
            print("━" * 60)
            print(f" Portfolio ID: {portfolio_id}")
            print(f" Name: {name}")
            print(f" Owner: {username} (ID: {user_id})")
            print(f" Creation Date: {created_date}")  # KEY REQUIREMENT
            print(f" Description: {description if description else 'No description provided'}")
            print(f" Total Market Value: ${(total_market_value or 0):.2f}")
            
            # Get detailed stock list for this portfolio - KEY REQUIREMENT
            stock_query = """
            SELECT 
                s.symbol, 
                s.company_name, 
                ph.quantity, 
                ph.avg_cost, 
                ph.market_value,
                ph.last_updated
            FROM portfolio_holdings ph
            JOIN stocks s ON ph.stock_id = s.stock_id
            WHERE ph.portfolio_id = %s
            ORDER BY s.symbol
            """
            
            stocks = db.execute_query(stock_query, (portfolio_id,))
            
            print(f" Stocks in Portfolio: {stock_count} total")
            
            if stocks:
                # Separate active positions from watchlist items
                active_positions = [s for s in stocks if s[2] != 0]  # quantity != 0
                watchlist_items = [s for s in stocks if s[2] == 0]   # quantity == 0
                
                if active_positions:
                    print(f"    Active Positions ({len(active_positions)}):")
                    print(f"      {'Symbol':<8} | {'Company':<20} | {'Shares':<8} | {'Avg Cost':<10} | {'Value':<10}")
                    print("      " + "-" * 65)
                    
                    for stock in active_positions:
                        symbol, company, qty, avg_cost, market_val, last_updated = stock
                        company_short = company[:18] if company else "N/A"
                        print(f"      {symbol:<8} | {company_short:<20} | {qty:<8.2f} | ${avg_cost:<9.2f} | ${market_val:<9.2f}")
                
                if watchlist_items:
                    print(f"    Watchlist Items ({len(watchlist_items)}):")
                    for stock in watchlist_items:
                        symbol, company, qty, avg_cost, market_val, last_updated = stock
                        company_short = company[:30] if company else "N/A"
                        print(f"      • {symbol} - {company_short}")
                
                # Summary list of all stocks - KEY REQUIREMENT
                all_symbols = [s[0] for s in stocks]
                print(f"    Complete Stock List: {', '.join(all_symbols)}")
                
            else:
                print("    No stocks in this portfolio")
            
            print()  # Spacing between portfolios
        
        # Summary statistics
        print("=" * 80)
        print(" PORTFOLIO SYSTEM SUMMARY")
        print("=" * 80)
        
        total_portfolios = len(portfolios)
        portfolios_with_stocks = len([p for p in portfolios if p[6] > 0])  # stock_count > 0
        total_unique_stocks = db.execute_query("SELECT COUNT(DISTINCT stock_id) FROM portfolio_holdings")[0][0]
        
        print(f"Total Portfolios: {total_portfolios}")
        print(f"Portfolios with Stocks: {portfolios_with_stocks}")
        print(f"Unique Stocks Across All Portfolios: {total_unique_stocks}")
        
        # Show creation date range
        if portfolios:
            earliest_date = min(p[2] for p in portfolios if p[2])
            latest_date = max(p[2] for p in portfolios if p[2])
            print(f"Portfolio Creation Date Range: {earliest_date} to {latest_date}")
        
        db.disconnect()
        return True
        
    except Exception as e:
        print(f" Error displaying portfolios: {e}")
        db.disconnect()
        return False

def display_portfolio_creation_timeline(pm):
    """Show portfolios in chronological order of creation"""
    print("\n" + "=" * 60)
    print("PORTFOLIO CREATION TIMELINE")
    print("=" * 60)
    
    db = DatabaseConnection()
    if not db.connect():
        print(" Could not connect to database")
        return False
    
    try:
        timeline_query = """
        SELECT 
            p.portfolio_name,
            p.created_date,
            u.username,
            COUNT(ph.stock_id) as stock_count
        FROM portfolios p
        LEFT JOIN users u ON p.user_id = u.user_id
        LEFT JOIN portfolio_holdings ph ON p.portfolio_id = ph.portfolio_id
        GROUP BY p.portfolio_id, p.portfolio_name, p.created_date, u.username
        ORDER BY p.created_date ASC
        """
        
        timeline = db.execute_query(timeline_query)
        
        if timeline:
            print(f"{'Date':<12} | {'Portfolio Name':<20} | {'Owner':<10} | {'Stocks'}")
            print("-" * 55)
            
            for entry in timeline:
                name, created_date, username, stock_count = entry
                date_str = str(created_date).split()[0]  # Just the date part
                name_short = name[:18] if len(name) > 18 else name
                username_short = username[:8] if username and len(username) > 8 else (username or "N/A")
                
                print(f"{date_str:<12} | {name_short:<20} | {username_short:<10} | {stock_count}")
        
        db.disconnect()
        return True
        
    except Exception as e:
        print(f" Error displaying timeline: {e}")
        db.disconnect()
        return False

def main():
    print("=" * 80)
    print("DISPLAY ALL PORTFOLIOS WITH CREATION DATE AND STOCK LISTS")
    print("=" * 80)
    
    pm = PortfolioManager()
    
    try:
        # Main comprehensive display
        print("\n  COMPREHENSIVE PORTFOLIO INFORMATION")
        success1 = display_comprehensive_portfolio_info(pm)
        
        if not success1:
            return False
        
        # Timeline view
        print("\n  PORTFOLIO CREATION TIMELINE")
        success2 = display_portfolio_creation_timeline(pm)
        
        # Enhanced display using portfolio manager method
        print("\n  ENHANCED PORTFOLIO DISPLAY (via PortfolioManager)")
        print("=" * 60)
        try:
            pm.display_enhanced_portfolios()
            success3 = True
        except Exception as e:
            print(f" Enhanced display error: {e}")
            success3 = False
        
        return success1 and success2 and success3
        
    except Exception as e:
        print(f" Error: {e}")
        return False

if __name__ == "__main__":
    print("Requirement: Display all portfolios with creation date and list of stocks")
    success = main()
    
    print("\n" + "=" * 80)
    if success:
        print(" REQUIREMENT FULFILLED: Portfolio display with creation dates and stock lists")
        print("\nKey Features Demonstrated:")
        print("•  Portfolio creation dates prominently displayed")
        print("•  Complete list of stocks in each portfolio")
        print("•  Portfolio ownership information")
        print("•  Market value calculations")
        print("•  Active positions vs watchlist distinction")
        print("•  Chronological creation timeline")
        print("•  Portfolio system summary statistics")
        print("\nAll portfolios are shown with their creation dates and complete stock lists as required.")
    else:
        print(" REQUIREMENT NOT MET: Portfolio display failed")
    
    print("\nNext steps:")
    print("• Use 'create_portfolio_with_stocks.py' to create new portfolios")
    print("• Use 'manage_portfolio_stocks.py' to modify portfolio stock lists")
    
    sys.exit(0 if success else 1)
