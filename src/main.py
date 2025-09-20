from portfolio.portfolio_manager import PortfolioManager
from data.data_collector import DataCollector
from data.data_preprocessor import DataPreprocessor
from database.db_connection import DatabaseConnection
from datetime import datetime, timedelta
import time

class StockAnalysisApp:
    def __init__(self):
        self.portfolio_manager = PortfolioManager()
        self.data_collector = DataCollector()
        self.data_preprocessor = DataPreprocessor()
        
    def run(self):
        """Main application loop"""
        print("=== Stock Price Analysis & Algorithmic Trading System ===")
        print("Waiting for database connection...")
        
        # Wait for database to be ready
        db = DatabaseConnection()
        if not db.connect():
            print("Failed to connect to database. Exiting...")
            return
        db.disconnect()
        
        while True:
            self.display_menu()
            choice = input("\nEnter your choice (1-13): ").strip()
            
            if choice == '1':
                self.create_portfolio_flow()
            elif choice == '2':
                self.create_portfolio_with_stocks_flow()
            elif choice == '3':
                self.manage_portfolio_stocks()
            elif choice == '4':
                self.simple_portfolio_management_flow()
            elif choice == '5':
                self.display_enhanced_portfolios()
            elif choice == '6':
                self.fetch_portfolio_price_data_flow()
            elif choice == '7':
                self.add_stock_direct_flow()
            elif choice == '8':
                self.bulk_import_flow()
            elif choice == '9':
                self.view_stock_info()
            elif choice == '10':
                self.update_stock_metadata_flow()
            elif choice == '11':
                self.update_all_stock_price_data_flow()
            elif choice == '12':
                self.calculate_daily_returns_flow()
            elif choice == '13':
                self.run_arima_trading()
            elif choice == '14':
                print("Thank you for using the Stock Analysis System!")
                break
            else:
                print("Invalid choice. Please try again.")
            
            input("\nPress Enter to continue...")

    def display_menu(self):
        """Display main menu"""
        print("\n" + "="*50)
        print("MAIN MENU")
        print("="*50)
        print("1. Create New Portfolio")
        print("2. Create Portfolio with Stock List")
        print("3. Manage Portfolio Stocks (Trading)")
        print("4. Simple Portfolio Management (Add/Remove)")
        print("5. Display All Portfolios (Enhanced)")
        print("6. Fetch Portfolio Price Data")
        print("7. Add Stock to Database (Direct)")
        print("8. Bulk Import from CSV")
        print("9. View Stock Information")
        print("10. Update Stock Metadata")
        print("11. Update Price Data (All Stocks)")
        print("12. Calculate Daily Returns (All Stocks)")
        print("13. Run ARIMA Trading Algorithm") 
        print("14. Exit")

    def create_portfolio_flow(self):
        """Create a new portfolio"""
        print("\n--- Create New Portfolio ---")
        
        # First, display available users and get user selection
        users = self.portfolio_manager.display_active_users()
        if not users:
            return
        
        try:
            user_id = int(input("\nEnter User ID to create portfolio for: ").strip())
            
            # Validate user ID exists in the list
            valid_user_ids = [user[0] for user in users]  # user[0] is user_id
            if user_id not in valid_user_ids:
                print(f"Error: User ID {user_id} is not valid. Please select from the list above.")
                return
                
        except ValueError:
            print("Error: Please enter a valid numeric User ID")
            return
        
        # Get portfolio details
        name = input("Enter portfolio name: ").strip()
        if not name:
            print("Portfolio name cannot be empty")
            return
            
        description = input("Enter description (optional): ").strip()
        
        # Create portfolio with user validation
        self.portfolio_manager.create_portfolio(name, description, user_id)

    def manage_portfolio_stocks(self):
        """Manage stocks in a portfolio"""
        print("\n--- Manage Portfolio Stocks ---")
        self.display_portfolios()
        
        try:
            portfolio_id = int(input("Enter portfolio ID: "))
            
            while True:
                print("\n1. Execute Trade (Buy/Sell)")
                print("2. Close Position")
                print("3. View Positions")
                print("4. View Transaction History")
                print("5. Back to Main Menu")
                
                choice = input("Enter choice: ").strip()
                
                if choice == '1':
                    self._execute_trade_flow(portfolio_id)
                elif choice == '2':
                    symbol = input("Enter stock symbol to close: ").strip().upper()
                    if not symbol:
                        print("Stock symbol cannot be empty")
                        continue
                    
                    # Check if stock exists in database
                    stock_id = self.portfolio_manager._get_stock_id(symbol)
                    if not stock_id:
                        print(f" Error: '{symbol}' is not in the database.")
                        print("   Cannot close position for a stock not in the database.")
                        continue
                    
                    self.portfolio_manager.close_position(portfolio_id, symbol)
                elif choice == '3':
                    self._view_positions(portfolio_id)
                elif choice == '4':
                    self._view_transaction_history(portfolio_id)
                elif choice == '5':
                    break
                else:
                    print("Invalid choice")
                    
        except ValueError:
            print("Invalid portfolio ID")

    def display_portfolios(self):
        """Display all portfolios"""
        print("\n--- All Portfolios ---")
        self.portfolio_manager.display_all_portfolios()

    def fetch_stock_data_flow(self):
        """Fetch historical stock data"""
        print("\n--- Fetch Stock Data ---")
        
        symbol = input("Enter stock symbol: ").strip().upper()
        if not symbol:
            print("Stock symbol cannot be empty")
            return
        
        print("\nSelect period for data collection:")
        print("1. 1 year (default)")
        print("2. 6 months") 
        print("3. 3 months")
        print("4. 1 month")
        print("5. Custom period")
        
        period_choice = input("Enter choice (1-5): ").strip()
        
        period_map = {
            '1': '1y',
            '2': '6mo', 
            '3': '3mo',
            '4': '1mo'
        }
        
        if period_choice in period_map:
            period = period_map[period_choice]
            print(f"Fetching {period} of data for {symbol}...")
            success = self.data_collector.fetch_stock_data(symbol, period=period)
            if success:
                print(f"Successfully fetched data for {symbol}")
            else:
                print(f"Failed to fetch data for {symbol}")
        elif period_choice == '5':
            period = input("Enter custom period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max): ").strip()
            print(f"Fetching {period} of data for {symbol}...")
            success = self.data_collector.fetch_stock_data(symbol, period=period)
            if success:
                print(f"Successfully fetched data for {symbol}")
            else:
                print(f"Failed to fetch data for {symbol}")
        else:
            print("Invalid choice, using 1 year default")
            success = self.data_collector.fetch_stock_data(symbol, period="1y")
            if success:
                print(f"Successfully fetched 1 year of data for {symbol}")
            else:
                print(f"Failed to fetch data for {symbol}")

    # def preprocess_data_flow(self):
    #     """Preprocess stock data"""
    #     print("\n--- Data Preprocessing ---")
    #     
    #     symbol = input("Enter stock symbol to preprocess: ").strip().upper()
    #     
    #     # Get stock ID
    #     db = DatabaseConnection()
    #     db.connect()
    #     
    #     stock_query = "SELECT stock_id FROM stocks WHERE symbol = %s"
    #     result = db.execute_query(stock_query, (symbol,))
    #     
    #     if not result:
    #         print(f"Stock {symbol} not found")
    #         return
    #     
    #     stock_id = result[0][0]
    #     
    #     print("\nPreprocessing options:")
    #     print("1. Calculate Daily Returns")
    #     print("2. Handle Missing Values")
    #     print("3. Calculate Moving Averages")
    #     print("4. All of the above")
    #     
    #     choice = input("Enter choice: ").strip()
    #     
    #     if choice in ['1', '4']:
    #         self.data_preprocessor.calculate_daily_returns(stock_id)
    #     
    #     if choice in ['2', '4']:
    #         method = input("Choose method (forward_fill/backward_fill/interpolate): ").strip()
    #         if method in ['forward_fill', 'backward_fill', 'interpolate']:
    #             self.data_preprocessor.handle_missing_values(stock_id, method)
    #         else:
    #             print("Invalid method")
    #     
    #     if choice in ['3', '4']:
    #         self.data_preprocessor.calculate_moving_averages(stock_id)
    #     
    #     db.disconnect()

    def add_stock_direct_flow(self):
        """Add stock directly to database (without portfolio)"""
        print("\n--- Add Stock to Database ---")
        symbol = input("Enter stock symbol: ").strip().upper()
        
        if not symbol:
            print("Stock symbol cannot be empty")
            return
        
        print(f"Adding {symbol} to database...")
        success = self.data_collector.add_stock_to_database(symbol)
        
        if success:
            print(f"Successfully added {symbol} to database")
        else:
            print(f"Failed to add {symbol} to database")

    def bulk_import_flow(self):
        """Bulk import stocks from CSV file"""
        print("\n--- Bulk Import from CSV ---")
        csv_path = input("Enter path to CSV file: ").strip()
        
        if not csv_path:
            print("CSV file path cannot be empty")
            return
        
        print(f"Importing stocks from {csv_path}...")
        results = self.data_collector.bulk_add_from_csv(csv_path)
        
        if results:
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            print(f"Import completed: {successful}/{total} stocks added successfully")
            
            # Show details
            for symbol, success in results.items():
                status = "" if success else ""
                print(f"  {status} {symbol}")
        else:
            print("No results returned from import")

    def view_stock_info(self):
        """View detailed stock information"""
        print("\n--- Stock Information ---")
        symbol = input("Enter stock symbol: ").strip().upper()
        
        from portfolio.stock_validator import StockValidator
        validator = StockValidator()
        
        info = validator.get_stock_info(symbol)
        if info:
            print(f"\nStock Information for {symbol}:")
            print(f"Company Name: {info['name']}")
            print(f"Sector: {info['sector']}")
            print(f"Current Price: ${info['current_price']}")
            print(f"Market Cap: ${info['market_cap']:,}" if isinstance(info['market_cap'], (int, float)) else f"Market Cap: {info['market_cap']}")
            print(f"P/E Ratio: {info['pe_ratio']}")
        else:
            print(f"Could not retrieve information for {symbol}")

    def update_stock_metadata_flow(self):
        """Update stock metadata for existing stocks"""
        print("\n--- Update Stock Metadata ---")
        print("Choose an option:")
        print("1. Update metadata for a specific stock")
        print("2. Update metadata for all stocks in database")
        
        choice = input("Enter choice (1-2): ").strip()
        
        if choice == '1':
            symbol = input("Enter stock symbol: ").strip().upper()
            if symbol:
                print(f"\nUpdating metadata for {symbol}...")
                success = self._update_single_stock_metadata(symbol)
                if success:
                    print(f" Successfully updated metadata for {symbol}")
                else:
                    print(f" Failed to update metadata for {symbol}")
        
        elif choice == '2':
            print("\nWarning: This will update metadata for ALL stocks in the database.")
            confirm = input("Are you sure? (y/N): ").strip().lower()
            if confirm == 'y':
                self._update_all_stock_metadata()
            else:
                print("Operation cancelled")
        
        else:
            print("Invalid choice")

    def _update_single_stock_metadata(self, symbol):
        """Update metadata for a single stock"""
        try:
            # Get stock info from Yahoo Finance
            from portfolio.stock_validator import StockValidator
            validator = StockValidator()
            
            stock_info = validator.get_stock_info(symbol)
            if not stock_info:
                print(f"Could not fetch info for {symbol}")
                return False
            
            # Get stock_id from database
            db = DatabaseConnection()
            if not db.connect():
                print("Failed to connect to database")
                return False
            
            result = db.execute_query("SELECT stock_id FROM stocks WHERE symbol = %s", (symbol,))
            if not result:
                print(f"Stock {symbol} not found in database")
                db.disconnect()
                return False
            
            stock_id = result[0][0]
            
            # Update metadata using data collector
            success = self.data_collector._update_stock_metadata(stock_id, stock_info)
            db.disconnect()
            return success
            
        except Exception as e:
            print(f"Error updating metadata for {symbol}: {e}")
            return False

    def _update_all_stock_metadata(self):
        """Update metadata for all stocks in database"""
        try:
            # Get all stocks from database
            db = DatabaseConnection()
            if not db.connect():
                print("Failed to connect to database")
                return
            
            stocks = db.execute_query("SELECT symbol FROM stocks ORDER BY symbol")
            if not stocks:
                print("No stocks found in database")
                db.disconnect()
                return
            
            print(f"\nUpdating metadata for {len(stocks)} stocks...")
            successful = 0
            failed = 0
            
            from portfolio.stock_validator import StockValidator
            validator = StockValidator()
            
            for i, (symbol,) in enumerate(stocks, 1):
                print(f"[{i}/{len(stocks)}] Processing {symbol}...")
                
                try:
                    # Rate limiting
                    if i > 1:
                        print(" Waiting 2 seconds (rate limiting)...")
                        time.sleep(2)
                    
                    success = self._update_single_stock_metadata(symbol)
                    if success:
                        successful += 1
                        print(f" {symbol} updated")
                    else:
                        failed += 1
                        print(f" {symbol} failed")
                        
                except Exception as e:
                    failed += 1
                    print(f" {symbol} error: {e}")
            
            print(f"\n Metadata update complete:")
            print(f" Successful: {successful}")
            print(f" Failed: {failed}")
            print(f" Total processed: {successful + failed}")
            
            db.disconnect()
            
        except Exception as e:
            print(f"Error during bulk metadata update: {e}")

    # def data_quality_report(self):
    #     """Generate data quality report"""
    #     print("\n--- Data Quality Report ---")
    #     symbol = input("Enter stock symbol: ").strip().upper()
    #     
    #     # Get stock ID
    #     db = DatabaseConnection()
    #     db.connect()
    #     
    #     stock_query = "SELECT stock_id FROM stocks WHERE symbol = %s"
    #     result = db.execute_query(stock_query, (symbol,))
    #     
    #     if not result:
    #         print(f"Stock {symbol} not found")
    #         return
    #     
    #     stock_id = result[0][0]
    #     self.data_preprocessor.get_data_quality_report(stock_id)
    #     
    #     db.disconnect()

    def update_all_stock_price_data_flow(self):
        """Update price data for all stocks in the database"""
        print("\n--- Update Price Data (All Stocks) ---")
        
        try:
            # Get all stocks from database
            db = DatabaseConnection()
            if not db.connect():
                print("Failed to connect to database")
                return
            
            stocks = db.execute_query("SELECT symbol FROM stocks ORDER BY symbol")
            if not stocks:
                print("No stocks found in database")
                db.disconnect()
                return
            
            print(f"Found {len(stocks)} stocks in database")
            
            # Ask user for period
            print("\nSelect period for price data update:")
            print("1. 1 month (recommended to avoid rate limits)")
            print("2. 3 months") 
            print("3. 6 months")
            print("4. 1 year")
            print("5. Custom period")
            
            period_choice = input("Enter choice (1-5, default=1): ").strip()
            
            period_map = {
                '1': '1mo',
                '2': '3mo', 
                '3': '6mo',
                '4': '1y'
            }
            
            if period_choice in period_map:
                period = period_map[period_choice]
            elif period_choice == '5':
                period = input("Enter custom period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max): ").strip()
                if not period:
                    period = "1mo"
            else:
                print("Invalid choice, using 1 month default")
                period = "1mo"
            
            print(f"\nUpdating price data for all stocks with period: {period}")
            print("  This may take several minutes due to rate limiting...")
            
            confirm = input("Continue? (y/N): ").strip().lower()
            if confirm != 'y':
                print("Operation cancelled")
                db.disconnect()
                return
            
            print(f"\nStarting bulk price data update for {len(stocks)} stocks...")
            successful = 0
            failed = 0
            
            for i, (symbol,) in enumerate(stocks, 1):
                print(f"\n[{i}/{len(stocks)}] Processing {symbol}...")
                
                try:
                    # Rate limiting between requests
                    if i > 1:
                        print(" Waiting 2 seconds (rate limiting)...")
                        time.sleep(2)
                    
                    success = self.data_collector.fetch_stock_data(symbol, period=period)
                    if success:
                        successful += 1
                        print(f" {symbol} - Price data updated successfully")
                    else:
                        failed += 1
                        print(f" {symbol} - Failed to update price data")
                        
                except Exception as e:
                    failed += 1
                    print(f" {symbol} - Error: {e}")
            
            print(f"\n Bulk price data update complete:")
            print(f" Successful: {successful}")
            print(f" Failed: {failed}")
            print(f" Total processed: {successful + failed}")
            
            db.disconnect()
            
        except Exception as e:
            print(f"Error during bulk price data update: {e}")

    def _execute_trade_flow(self, portfolio_id):
        """Handle trade execution flow"""
        print("\n--- Execute Trade ---")
        
        try:
            # Get trade details
            symbol = input("Enter stock symbol (e.g., AAPL): ").strip().upper()
            if not symbol:
                print("Stock symbol cannot be empty")
                return
            
            # Check if stock exists in database before continuing
            stock_id = self.portfolio_manager._get_stock_id(symbol)
            if not stock_id:
                print(f" Error: '{symbol}' is not in the database.")
                print("   Please add the stock to the database first using 'Add Stock to Database' option.")
                return
            
            print(f" Found {symbol} in database")
            print("\nSelect action:")
            print("1. BUY_TO_OPEN (Buy to open long position)")
            print("2. SELL_TO_CLOSE (Sell to close long position)")
            print("3. SELL_TO_OPEN (Sell to open short position)")
            print("4. BUY_TO_CLOSE (Buy to close short position)")
            
            action_choice = input("Enter choice (1-4): ").strip()
            action_map = {
                '1': 'BUY_TO_OPEN',
                '2': 'SELL_TO_CLOSE', 
                '3': 'SELL_TO_OPEN',
                '4': 'BUY_TO_CLOSE'
            }
            
            if action_choice not in action_map:
                print("Invalid action choice")
                return
            
            action = action_map[action_choice]
            
            # Get quantity and price
            quantity = float(input("Enter quantity (number of shares): "))
            price = float(input(f"Enter price per share for {symbol}: $"))
            fees_input = input("Enter fees/commissions (optional, default=0): ").strip()
            fees = float(fees_input) if fees_input else 0.0
            notes = input("Enter notes (optional): ").strip()
            
            # Execute the trade
            success = self.portfolio_manager.execute_trade(
                portfolio_id, symbol, action, quantity, price, fees, notes
            )
            
            if success:
                print(" Trade executed successfully!")
            else:
                print(" Trade execution failed!")
                
        except (ValueError, TypeError):
            print("Invalid input. Please enter valid numbers for quantity, price, and fees.")
        except Exception as e:
            print(f"Error executing trade: {e}")
    
    def _view_positions(self, portfolio_id):
        """View all positions in portfolio"""
        print("\n--- Current Positions ---")
        stocks = self.portfolio_manager.get_portfolio_stocks(portfolio_id)
        
        if not stocks:
            print("No positions in this portfolio")
            return
        
        print(f"{'Symbol':<8} {'Company':<25} {'Qty':<12} {'Avg Cost':<12} {'P&L':<12}")
        print("-" * 75)
        
        for stock_id, symbol, company_name, quantity, avg_cost, unrealized_pnl in stocks:
            pnl_str = f"${unrealized_pnl:.2f}" if unrealized_pnl else "$0.00"
            print(f"{symbol:<8} {company_name[:24]:<25} {quantity:<12.2f} ${avg_cost:<11.2f} {pnl_str:<12}")
    
    def _view_transaction_history(self, portfolio_id):
        """View transaction history for portfolio"""
        print("\n--- Transaction History ---")
        
        # Option to filter by symbol
        filter_choice = input("Filter by symbol? (y/N): ").strip().lower()
        symbol = None
        if filter_choice == 'y':
            symbol = input("Enter symbol to filter: ").strip().upper()
        
        transactions = self.portfolio_manager.get_transaction_history(portfolio_id, symbol)
        
        if not transactions:
            print("No transactions found")
            return
        
        print(f"{'Date/Time':<20} {'Symbol':<8} {'Action':<15} {'Qty':<10} {'Price':<10} {'Fees':<8} {'Notes'}")
        print("-" * 95)
        
        for txn_time, txn_symbol, action, quantity, price, fees, notes in transactions:
            txn_symbol_str = txn_symbol if txn_symbol else "CASH"
            notes_str = notes[:20] if notes else ""
            print(f"{str(txn_time):<20} {txn_symbol_str:<8} {action:<15} {quantity:<10.2f} ${price:<9.2f} ${fees:<7.2f} {notes_str}")

    def calculate_daily_returns_flow(self):
        """Calculate daily returns for all stocks in the database"""
        print("\n--- Calculate Daily Returns (All Stocks) ---")
        
        try:
            # Get database connection
            db = DatabaseConnection()
            if not db.connect():
                print("Failed to connect to database")
                return
            
            # Check how many stocks have NULL daily returns
            check_query = """
            SELECT COUNT(*) 
            FROM stock_historical_data 
            WHERE daily_return IS NULL
            """
            null_count_result = db.execute_query(check_query)
            null_count = null_count_result[0][0] if null_count_result else 0
            
            print(f"Found {null_count} records with NULL daily returns")
            
            if null_count == 0:
                print("All records already have daily returns calculated!")
                db.disconnect()
                return
            
            # Confirm with user
            proceed = input(f"Calculate daily returns for all stocks? (y/n, default=y): ").strip().lower()
            if proceed and proceed != 'y':
                print("Operation cancelled")
                db.disconnect()
                return
            
            print("\nCalculating daily returns...")
            
            # Use the data preprocessor to update daily returns
            success = self.data_preprocessor.update_daily_returns_in_database(db)
            
            if success:
                # Check results
                final_check = db.execute_query(check_query)
                final_null_count = final_check[0][0] if final_check else 0
                calculated_count = null_count - final_null_count
                
                print(f"\n Successfully calculated daily returns for {calculated_count} records")
                if final_null_count > 0:
                    print(f"Note: {final_null_count} records still have NULL daily returns (likely first trading day for each stock)")
            else:
                print("\n Failed to calculate daily returns")
            
            db.disconnect()
            
        except Exception as e:
            print(f"\nError calculating daily returns: {e}")

    def create_portfolio_with_stocks_flow(self):
        """Create a new portfolio with initial stock list"""
        print("\n--- Create Portfolio with Stock List ---")
        
        # Get portfolio details
        users = self.portfolio_manager.display_active_users()
        if not users:
            print("No active users found. Cannot create portfolio.")
            return
        
        try:
            user_id = int(input("\nEnter User ID to create portfolio for: "))
            name = input("Enter portfolio name: ").strip()
            description = input("Enter portfolio description (optional): ").strip()
            
            if not name:
                print("Portfolio name cannot be empty")
                return
            
            # Get stock symbols
            print("\nEnter stock symbols (comma-separated, e.g., AAPL,GOOGL,MSFT):")
            stocks_input = input("Stock symbols: ").strip()
            
            if stocks_input:
                stock_symbols = [symbol.strip().upper() for symbol in stocks_input.split(',')]
                print(f"Creating portfolio with stocks: {', '.join(stock_symbols)}")
            else:
                stock_symbols = []
                print("Creating empty portfolio")
            
            # Create portfolio with stocks
            success = self.portfolio_manager.create_portfolio_with_stocks(
                name, stock_symbols, description, user_id
            )
            
            if success:
                print(f"\n Portfolio '{name}' created successfully!")
            else:
                print("\n Failed to create portfolio")
                
        except ValueError:
            print("Invalid user ID")
        except Exception as e:
            print(f"Error: {e}")

    def simple_portfolio_management_flow(self):
        """Simple portfolio management - add/remove stocks without trading"""
        print("\n--- Simple Portfolio Management ---")
        
        # Display portfolios
        self.portfolio_manager.display_all_portfolios()
        
        try:
            portfolio_id = int(input("\nEnter Portfolio ID: "))
            
            while True:
                print("\nSimple Portfolio Management Options:")
                print("1. Add Stock to Portfolio")
                print("2. Remove Stock from Portfolio")
                print("3. View Portfolio Details")
                print("4. Back to Main Menu")
                
                choice = input("\nEnter your choice (1-4): ").strip()
                
                if choice == '1':
                    symbol = input("Enter stock symbol to add: ").strip().upper()
                    if symbol:
                        # Validate stock first
                        if self.portfolio_manager.validator.validate_stock(symbol):
                            self.portfolio_manager.add_stock_to_portfolio(portfolio_id, symbol)
                        else:
                            print(f" Invalid stock symbol: {symbol}")
                    else:
                        print("Stock symbol cannot be empty")
                
                elif choice == '2':
                    symbol = input("Enter stock symbol to remove: ").strip().upper()
                    if symbol:
                        self.portfolio_manager.remove_stock_from_portfolio(portfolio_id, symbol)
                    else:
                        print("Stock symbol cannot be empty")
                
                elif choice == '3':
                    details = self.portfolio_manager.get_portfolio_with_details(portfolio_id)
                    if details:
                        print(f"\n--- Portfolio Details ---")
                        print(f"Name: {details['name']}")
                        print(f"Owner: {details['username']}")
                        print(f"Created: {details['created_date']}")
                        print(f"Description: {details['description']}")
                        print(f"Total Market Value: ${details['total_market_value']:.2f}")
                        print(f"\nStocks ({len(details['stocks'])}):")
                        for stock in details['stocks']:
                            if stock['quantity'] != 0:
                                print(f"  • {stock['symbol']}: {stock['quantity']} shares @ ${stock['avg_cost']:.2f}")
                            else:
                                print(f"  • {stock['symbol']}: Watchlist")
                    else:
                        print("Portfolio not found")
                
                elif choice == '4':
                    break
                
                else:
                    print("Invalid choice")
                
        except ValueError:
            print("Invalid portfolio ID")
        except Exception as e:
            print(f"Error: {e}")

    def display_enhanced_portfolios(self):
        """Display portfolios with enhanced details"""
        print("\n--- Enhanced Portfolio Display ---")
        self.portfolio_manager.display_enhanced_portfolios()

    def fetch_portfolio_price_data_flow(self):
        """Fetch price data for stocks in a specific portfolio"""
        print("\n--- Fetch Portfolio Price Data ---")
        
        # Display portfolios
        self.portfolio_manager.display_all_portfolios()
        
        try:
            portfolio_id = int(input("\nEnter Portfolio ID: "))
            
            print("\nDate Range Options:")
            print("1. Use predefined period (1mo, 3mo, 6mo, 1y, etc.)")
            print("2. Use specific date range")
            
            option = input("Choose option (1-2): ").strip()
            
            if option == '1':
                print("\nAvailable periods:")
                print("1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max")
                period = input("Enter period (default 1mo): ").strip() or '1mo'
                
                success = self.portfolio_manager.fetch_portfolio_price_data(
                    portfolio_id, period=period
                )
                
            elif option == '2':
                start_date = input("Enter start date (YYYY-MM-DD): ").strip()
                end_date = input("Enter end date (YYYY-MM-DD): ").strip()
                
                if not start_date or not end_date:
                    print("Both start and end dates are required")
                    return
                
                success = self.portfolio_manager.fetch_portfolio_price_data(
                    portfolio_id, start_date=start_date, end_date=end_date
                )
                
            else:
                print("Invalid option")
                return
            
            if success:
                print("\n Portfolio price data updated successfully!")
            else:
                print("\n Failed to update portfolio price data")
                
        except ValueError:
            print("Invalid portfolio ID")
        except Exception as e:
            print(f"Error: {e}")

    def run_arima_trading(self):
        """Run ARIMA trading algorithm"""
        print("\n--- ARIMA Trading Algorithm ---")
        
        # Import ARIMA module
        from trading.arima_algorithm import ARIMATradingAlgorithm
        from scripts.run_arima_trading import analyze_portfolio
        
        # Display portfolios
        self.portfolio_manager.display_all_portfolios()
        
        try:
            portfolio_id = int(input("\nEnter Portfolio ID for ARIMA analysis: "))
            
            print("\nRunning ARIMA analysis...")
            results = analyze_portfolio(portfolio_id)
            
            if results is None:
                print("\n⚠️ No stocks in this portfolio. Add holdings before running ARIMA.")
            elif results:
                print("\n✅ ARIMA analysis complete!")
            else:
                print("\n❌ ARIMA analysis failed")
                
        except ValueError:
            print("Invalid portfolio ID")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    app = StockAnalysisApp()
    app.run()
