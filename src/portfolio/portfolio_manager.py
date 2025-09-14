from database.db_connection import DatabaseConnection
from portfolio.stock_validator import StockValidator
import yfinance as yf
from datetime import datetime

class PortfolioManager:
    def __init__(self):
        self.db = DatabaseConnection()
        self.validator = StockValidator()

    def create_portfolio(self, name, description="", user_id=None):
        """Create a new portfolio for a specific user"""
        # Validate that user_id is provided
        if user_id is None:
            print("Error: User ID is required to create a portfolio")
            return False
        
        # Check if user exists and is active
        user_query = "SELECT user_id, username, is_active FROM users WHERE user_id = %s"
        user_result = self.db.execute_query(user_query, (user_id,))
        
        if not user_result:
            print(f"Error: User ID {user_id} does not exist")
            return False
        
        user_id_db, username, is_active = user_result[0]
        
        if not is_active:
            print(f"Error: User '{username}' (ID: {user_id}) is not active")
            return False
        
        print(f" Creating portfolio for user: {username} (ID: {user_id})")
        
        # Create portfolio with user_id
        query = "INSERT INTO portfolios (user_id, portfolio_name, description) VALUES (%s, %s, %s)"
        result = self.db.execute_update(query, (user_id, name, description))
        
        if result > 0:
            print(f"Portfolio '{name}' created successfully for {username}!")
            return True
        else:
            print("Failed to create portfolio!")
            return False

    def get_active_users(self):
        """Get all active users from the database"""
        query = "SELECT user_id, username, email FROM users WHERE is_active = 1 ORDER BY username"
        return self.db.execute_query(query)
    
    def display_active_users(self):
        """Display all active users in a formatted way"""
        users = self.get_active_users()
        if not users:
            print("No active users found in the system")
            return None
        
        print("\nActive Users:")
        print("-" * 40)
        print(f"{'ID':<3} | {'Username':<10} | {'Email'}")
        print("-" * 40)
        
        for user_id, username, email in users:
            print(f"{user_id:<3} | {username:<10} | {email}")
        
        return users

    def execute_trade(self, portfolio_id, symbol, action, quantity, price, fees=0.0, notes=""):
        """Execute a trade transaction"""
        # Get stock ID (assumes validation already done at UI level)
        stock_id = self._get_stock_id(symbol)
        if not stock_id:
            print(f"Error: '{symbol}' is not in the database. Add the stock to the database first before trading.")
            return False

        # Note: Stock validation should be done at the UI level before calling this method
        # This is a backup check in case method is called directly

        # Validate action
        valid_actions = ['BUY_TO_OPEN', 'BUY_TO_CLOSE', 'SELL_TO_CLOSE', 'SELL_TO_OPEN']
        if action not in valid_actions:
            print(f"Invalid action. Must be one of: {', '.join(valid_actions)}")
            return False

        # Validate quantity and price
        try:
            quantity = float(quantity)
            price = float(price)
            fees = float(fees) if fees else 0.0
            
            if quantity <= 0:
                print("Quantity must be positive")
                return False
            if price <= 0:
                print("Price must be positive")
                return False
        except (ValueError, TypeError):
            print("Invalid quantity, price, or fees")
            return False

        try:
            # 1. Record the transaction
            if not self._record_transaction(portfolio_id, stock_id, action, quantity, price, fees, notes):
                return False
            
            # 2. Update holdings based on the transaction
            if not self._update_holdings_from_transaction(portfolio_id, stock_id, action, quantity, price):
                return False
            
            print(f" {action}: {quantity} shares of {symbol} at ${price:.2f}/share")
            if fees > 0:
                print(f"  Fees: ${fees:.2f}")
            return True
            
        except Exception as e:
            print(f"Error executing trade: {e}")
            return False

    def close_position(self, portfolio_id, symbol):
        """Close entire position for a stock (requires current market price)"""
        # Get current position
        position = self.get_position(portfolio_id, symbol)
        if not position:
            print(f"No position found for {symbol}")
            return False
        
        quantity = position['quantity']
        if quantity == 0:
            print(f"No shares to close for {symbol}")
            return False
        
        # Get current market price (simplified - in real system would get real-time price)
        print(f"Current position: {quantity} shares of {symbol}")
        price_input = input(f"Enter current market price for {symbol}: $").strip()
        
        try:
            price = float(price_input)
            if price <= 0:
                print("Price must be positive")
                return False
        except (ValueError, TypeError):
            print("Invalid price")
            return False
        
        # Determine action based on current position
        if quantity > 0:
            # Long position - sell to close
            action = 'SELL_TO_CLOSE'
            trade_quantity = abs(quantity)
        else:
            # Short position - buy to close  
            action = 'BUY_TO_CLOSE'
            trade_quantity = abs(quantity)
        
        return self.execute_trade(portfolio_id, symbol, action, trade_quantity, price, notes="Position closed")

    def display_all_portfolios(self):
        """Display all portfolios"""
        query = """
        SELECT p.portfolio_id, p.portfolio_name, p.created_date, p.description,
               GROUP_CONCAT(s.symbol) as stocks
        FROM portfolios p
        LEFT JOIN portfolio_holdings ps ON p.portfolio_id = ps.portfolio_id
        LEFT JOIN stocks s ON ps.stock_id = s.stock_id
        GROUP BY p.portfolio_id, p.portfolio_name, p.created_date, p.description
        """
        
        results = self.db.execute_query(query)
        
        if not results:
            print("No portfolios found")
            return
        
        print("\n=== All Portfolios ===")
        for row in results:
            portfolio_id, name, created_date, description, stocks = row
            stocks_list = stocks.split(',') if stocks else ['No stocks']
            print(f"""
Portfolio ID: {portfolio_id}
Name: {name}
Created Date: {created_date}
Description: {description}
Stocks: {', '.join(stocks_list)}
""")

    def get_portfolio_stocks(self, portfolio_id):
        """Get all stocks with positions in a specific portfolio"""
        query = """
        SELECT s.stock_id, s.symbol, s.company_name, h.quantity, h.avg_cost, h.unrealized_pnl
        FROM stocks s
        JOIN portfolio_holdings h ON s.stock_id = h.stock_id
        WHERE h.portfolio_id = %s AND h.quantity != 0
        ORDER BY s.symbol
        """
        return self.db.execute_query(query, (portfolio_id,))

    def _record_transaction(self, portfolio_id, stock_id, action, quantity, price, fees, notes):
        """Record a transaction in the transaction ledger"""
        try:
            # Calculate transaction value
            txn_value = float(quantity) * float(price)
            
            query = """
            INSERT INTO portfolio_transactions 
            (portfolio_id, stock_id, txn_time, action, quantity, price, txn_value, fees, notes)
            VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s)
            """
            
            result = self.db.execute_update(query, (portfolio_id, stock_id, action, quantity, price, txn_value, fees, notes))
            return result > 0
            
        except Exception as e:
            print(f"Error recording transaction: {e}")
            return False
    
    def _update_holdings_from_transaction(self, portfolio_id, stock_id, action, quantity, price):
        """Update holdings based on a transaction"""
        try:
            # Get current position
            current_position = self._get_current_position(portfolio_id, stock_id)
            
            # Calculate new position based on action
            if action == 'BUY_TO_OPEN':
                new_quantity = current_position['quantity'] + quantity
                new_avg_cost = self._calculate_avg_cost(current_position, quantity, price, 'BUY')
            elif action == 'SELL_TO_CLOSE':
                new_quantity = current_position['quantity'] - quantity
                new_avg_cost = current_position['avg_cost']  # Avg cost doesn't change on sale
            elif action == 'SELL_TO_OPEN':  # Short selling
                new_quantity = current_position['quantity'] - quantity
                new_avg_cost = self._calculate_avg_cost(current_position, quantity, price, 'SELL')
            elif action == 'BUY_TO_CLOSE':  # Covering short
                new_quantity = current_position['quantity'] + quantity
                new_avg_cost = current_position['avg_cost']  # Avg cost doesn't change when covering
            
            # Calculate market value (using latest trade price as approximation for current market price)
            new_market_value = float(new_quantity) * float(price)
            
            # Upsert the holding
            if current_position['exists']:
                # Update existing holding
                update_query = """
                UPDATE portfolio_holdings 
                SET quantity = %s, avg_cost = %s, market_value = %s, last_updated = NOW()
                WHERE portfolio_id = %s AND stock_id = %s
                """
                result = self.db.execute_update(update_query, (new_quantity, new_avg_cost, new_market_value, portfolio_id, stock_id))
            else:
                # Create new holding
                insert_query = """
                INSERT INTO portfolio_holdings (portfolio_id, stock_id, quantity, avg_cost, market_value)
                VALUES (%s, %s, %s, %s, %s)
                """
                result = self.db.execute_update(insert_query, (portfolio_id, stock_id, new_quantity, new_avg_cost, new_market_value))
            
            return result >= 0
            
        except Exception as e:
            print(f"Error updating holdings: {e}")
            return False
    
    def _get_current_position(self, portfolio_id, stock_id):
        """Get current position for a stock in a portfolio"""
        query = """
        SELECT quantity, avg_cost FROM portfolio_holdings 
        WHERE portfolio_id = %s AND stock_id = %s
        """
        result = self.db.execute_query(query, (portfolio_id, stock_id))
        
        if result:
            return {
                'exists': True,
                'quantity': float(result[0][0]),
                'avg_cost': float(result[0][1])
            }
        else:
            return {
                'exists': False, 
                'quantity': 0.0,
                'avg_cost': 0.0
            }
    
    def _calculate_avg_cost(self, current_position, new_quantity, new_price, action_type):
        """Calculate new average cost basis"""
        current_qty = current_position['quantity']
        current_avg = current_position['avg_cost']
        
        if action_type == 'BUY':
            # Adding to position (long or covering short)
            if current_qty >= 0:  # Long position or no position
                total_cost = (current_qty * current_avg) + (new_quantity * new_price)
                total_quantity = current_qty + new_quantity
                return total_cost / total_quantity if total_quantity > 0 else new_price
            else:  # Covering part of short position
                return current_avg  # Avg cost basis doesn't change when covering shorts
        
        elif action_type == 'SELL':
            # Starting or adding to short position
            if current_qty <= 0:  # Short position or no position
                total_cost = abs(current_qty * current_avg) + (new_quantity * new_price)
                total_quantity = abs(current_qty) + new_quantity
                return total_cost / total_quantity if total_quantity > 0 else new_price
            else:  # Selling part of long position
                return current_avg  # Avg cost basis doesn't change when selling longs
        
        return current_avg
    
    def _get_stock_id(self, symbol):
        """Get stock ID if it exists in database (read-only, no creation)"""
        # Normalize symbol: strip whitespace and convert to uppercase
        normalized_symbol = symbol.strip().upper() if symbol else ""
        
        if not normalized_symbol:
            return None
            
        check_query = "SELECT stock_id FROM stocks WHERE UPPER(symbol) = %s"
        result = self.db.execute_query(check_query, (normalized_symbol,))
        return result[0][0] if result else None
    
    def get_position(self, portfolio_id, symbol):
        """Get current position for a stock"""
        # Get stock ID
        stock_query = "SELECT stock_id FROM stocks WHERE symbol = %s"
        stock_result = self.db.execute_query(stock_query, (symbol,))
        
        if not stock_result:
            return None
        
        stock_id = stock_result[0][0]
        
        # Get position
        position_query = """
        SELECT quantity, avg_cost, unrealized_pnl, last_updated
        FROM portfolio_holdings 
        WHERE portfolio_id = %s AND stock_id = %s
        """
        result = self.db.execute_query(position_query, (portfolio_id, stock_id))
        
        if result:
            return {
                'symbol': symbol,
                'quantity': float(result[0][0]),
                'avg_cost': float(result[0][1]),
                'unrealized_pnl': float(result[0][2]) if result[0][2] else 0.0,
                'last_updated': result[0][3]
            }
        return None
    
    def get_transaction_history(self, portfolio_id, symbol=None):
        """Get transaction history for a portfolio or specific stock"""
        if symbol:
            # Get transactions for specific stock
            query = """
            SELECT t.txn_time, s.symbol, t.action, t.quantity, t.price, t.fees, t.notes
            FROM portfolio_transactions t
            JOIN stocks s ON t.stock_id = s.stock_id
            WHERE t.portfolio_id = %s AND s.symbol = %s
            ORDER BY t.txn_time DESC
            """
            return self.db.execute_query(query, (portfolio_id, symbol))
        else:
            # Get all transactions for portfolio
            query = """
            SELECT t.txn_time, s.symbol, t.action, t.quantity, t.price, t.fees, t.notes
            FROM portfolio_transactions t
            LEFT JOIN stocks s ON t.stock_id = s.stock_id
            WHERE t.portfolio_id = %s
            ORDER BY t.txn_time DESC
            """
            return self.db.execute_query(query, (portfolio_id,))
    
    def _get_or_create_stock(self, symbol):
        """Get or create a stock record"""
        # Check if stock already exists
        check_query = "SELECT stock_id FROM stocks WHERE symbol = %s"
        result = self.db.execute_query(check_query, (symbol,))
        
        if result:
            return result[0][0]
        
        # Get stock information and create record
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            company_name = info.get('longName', symbol)
            sector = info.get('sector', 'Unknown')
            
            insert_query = """
            INSERT INTO stocks (symbol, company_name, sector) 
            VALUES (%s, %s, %s)
            """
            self.db.execute_update(insert_query, (symbol, company_name, sector))
            
            # Get the newly inserted stock ID
            result = self.db.execute_query(check_query, (symbol,))
            return result[0][0] if result else None
            
        except Exception as e:
            print(f"Error getting stock information: {e}")
            return None

    def add_stock_to_portfolio(self, portfolio_id, symbol, quantity=0):
        """Add a stock to portfolio without trading (for portfolio composition management)"""
        # Validate stock exists in database
        stock_id = self._get_stock_id(symbol)
        if not stock_id:
            print(f"Error: '{symbol}' is not in the database. Add the stock to the database first.")
            return False
        
        # Check if portfolio exists
        portfolio_query = "SELECT portfolio_name FROM portfolios WHERE portfolio_id = %s"
        portfolio_result = self.db.execute_query(portfolio_query, (portfolio_id,))
        if not portfolio_result:
            print(f"Error: Portfolio ID {portfolio_id} does not exist")
            return False
        
        portfolio_name = portfolio_result[0][0]
        
        try:
            # Check if stock is already in portfolio
            existing_query = """
            SELECT quantity FROM portfolio_holdings 
            WHERE portfolio_id = %s AND stock_id = %s
            """
            existing_result = self.db.execute_query(existing_query, (portfolio_id, stock_id))
            
            if existing_result:
                print(f"Stock {symbol} is already in portfolio '{portfolio_name}'")
                current_qty = existing_result[0][0]
                if current_qty != 0:
                    print(f"Current position: {current_qty} shares")
                return True
            
            # Add stock to portfolio with zero position (for watchlist/composition tracking)
            insert_query = """
            INSERT INTO portfolio_holdings (portfolio_id, stock_id, quantity, avg_cost, market_value)
            VALUES (%s, %s, %s, 0.0, 0.0)
            """
            
            result = self.db.execute_update(insert_query, (portfolio_id, stock_id, quantity))
            
            if result > 0:
                print(f" Added {symbol} to portfolio '{portfolio_name}'")
                return True
            else:
                print(f"Failed to add {symbol} to portfolio")
                return False
                
        except Exception as e:
            print(f"Error adding stock to portfolio: {e}")
            return False

    def remove_stock_from_portfolio(self, portfolio_id, symbol):
        """Remove a stock from portfolio (only if position is zero)"""
        # Get stock ID
        stock_id = self._get_stock_id(symbol)
        if not stock_id:
            print(f"Error: Stock '{symbol}' not found")
            return False
        
        # Check if portfolio exists
        portfolio_query = "SELECT portfolio_name FROM portfolios WHERE portfolio_id = %s"
        portfolio_result = self.db.execute_query(portfolio_query, (portfolio_id,))
        if not portfolio_result:
            print(f"Error: Portfolio ID {portfolio_id} does not exist")
            return False
        
        portfolio_name = portfolio_result[0][0]
        
        try:
            # Check current position
            position_query = """
            SELECT quantity FROM portfolio_holdings 
            WHERE portfolio_id = %s AND stock_id = %s
            """
            position_result = self.db.execute_query(position_query, (portfolio_id, stock_id))
            
            if not position_result:
                print(f"Stock {symbol} is not in portfolio '{portfolio_name}'")
                return False
            
            current_qty = float(position_result[0][0])
            
            if current_qty != 0:
                print(f"Cannot remove {symbol}: Current position is {current_qty} shares")
                print("Please close the position first using trading operations")
                return False
            
            # Remove stock from portfolio
            delete_query = """
            DELETE FROM portfolio_holdings 
            WHERE portfolio_id = %s AND stock_id = %s
            """
            
            result = self.db.execute_update(delete_query, (portfolio_id, stock_id))
            
            if result > 0:
                print(f" Removed {symbol} from portfolio '{portfolio_name}'")
                return True
            else:
                print(f"Failed to remove {symbol} from portfolio")
                return False
                
        except Exception as e:
            print(f"Error removing stock from portfolio: {e}")
            return False

    def create_portfolio_with_stocks(self, name, stock_symbols, description="", user_id=None):
        """Create a new portfolio and add multiple stocks to it"""
        # Create the portfolio first
        if not self.create_portfolio(name, description, user_id):
            return False
        
        # Get the newly created portfolio ID
        portfolio_query = """
        SELECT portfolio_id FROM portfolios 
        WHERE portfolio_name = %s AND user_id = %s 
        ORDER BY created_date DESC LIMIT 1
        """
        portfolio_result = self.db.execute_query(portfolio_query, (name, user_id))
        
        if not portfolio_result:
            print("Error: Could not retrieve newly created portfolio")
            return False
        
        portfolio_id = portfolio_result[0][0]
        print(f"Portfolio created with ID: {portfolio_id}")
        
        # Add stocks to the portfolio
        if stock_symbols:
            print(f"\nAdding {len(stock_symbols)} stocks to portfolio...")
            success_count = 0
            failed_stocks = []
            
            for symbol in stock_symbols:
                symbol = symbol.strip().upper()
                if symbol:  # Skip empty symbols
                    # Validate stock before adding
                    if self.validator.validate_stock(symbol):
                        if self.add_stock_to_portfolio(portfolio_id, symbol):
                            success_count += 1
                        else:
                            failed_stocks.append(symbol)
                    else:
                        print(f" Invalid stock symbol: {symbol}")
                        failed_stocks.append(symbol)
            
            print(f"\nStock addition summary:")
            print(f" Successfully added: {success_count} stocks")
            if failed_stocks:
                print(f" Failed: {', '.join(failed_stocks)}")
        
        return True

    def get_portfolio_with_details(self, portfolio_id):
        """Get detailed portfolio information including stocks and performance"""
        try:
            # Get portfolio basic info
            portfolio_query = """
            SELECT p.portfolio_id, p.portfolio_name, p.created_date, p.description, u.username
            FROM portfolios p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.portfolio_id = %s
            """
            portfolio_result = self.db.execute_query(portfolio_query, (portfolio_id,))
            
            if not portfolio_result:
                return None
            
            portfolio_info = {
                'portfolio_id': portfolio_result[0][0],
                'name': portfolio_result[0][1],
                'created_date': portfolio_result[0][2],
                'description': portfolio_result[0][3],
                'username': portfolio_result[0][4]
            }
            
            # Get stocks in portfolio
            stocks_query = """
            SELECT s.symbol, s.company_name, ph.quantity, ph.avg_cost, ph.market_value, ph.unrealized_pnl
            FROM portfolio_holdings ph
            JOIN stocks s ON ph.stock_id = s.stock_id
            WHERE ph.portfolio_id = %s
            ORDER BY s.symbol
            """
            stocks_result = self.db.execute_query(stocks_query, (portfolio_id,))
            
            portfolio_info['stocks'] = []
            total_market_value = 0.0
            
            for stock in stocks_result:
                stock_info = {
                    'symbol': stock[0],
                    'company_name': stock[1],
                    'quantity': float(stock[2]),
                    'avg_cost': float(stock[3]) if stock[3] else 0.0,
                    'market_value': float(stock[4]) if stock[4] else 0.0,
                    'unrealized_pnl': float(stock[5]) if stock[5] else 0.0
                }
                portfolio_info['stocks'].append(stock_info)
                total_market_value += stock_info['market_value']
            
            portfolio_info['total_market_value'] = total_market_value
            
            return portfolio_info
            
        except Exception as e:
            print(f"Error getting portfolio details: {e}")
            return None

    def display_enhanced_portfolios(self):
        """Display all portfolios with enhanced details"""
        query = """
        SELECT p.portfolio_id, p.portfolio_name, p.created_date, p.description, u.username,
               COUNT(ph.stock_id) as stock_count
        FROM portfolios p
        LEFT JOIN users u ON p.user_id = u.user_id
        LEFT JOIN portfolio_holdings ph ON p.portfolio_id = ph.portfolio_id
        GROUP BY p.portfolio_id, p.portfolio_name, p.created_date, p.description, u.username
        ORDER BY p.created_date DESC
        """
        
        results = self.db.execute_query(query)
        
        if not results:
            print("No portfolios found")
            return
        
        print("\n" + "=" * 80)
        print("ALL PORTFOLIOS")
        print("=" * 80)
        
        for row in results:
            portfolio_id, name, created_date, description, username, stock_count = row
            
            print(f"\nPortfolio ID: {portfolio_id}")
            print(f"Name: {name}")
            print(f"Owner: {username if username else 'Unknown'}")
            print(f"Created: {created_date}")
            print(f"Description: {description if description else 'No description'}")
            print(f"Number of stocks: {stock_count}")
            
            # Get stock details for this portfolio
            if stock_count > 0:
                stock_details = self.get_portfolio_stocks(portfolio_id)
                if stock_details:
                    print("Stocks:")
                    total_value = 0.0
                    for stock in stock_details:
                        symbol, company_name, quantity, avg_cost, unrealized_pnl = stock[1], stock[2], stock[3], stock[4], stock[5]
                        market_value = float(quantity) * float(avg_cost) if avg_cost else 0.0
                        total_value += market_value
                        
                        if quantity != 0:
                            print(f"  • {symbol} ({company_name}): {quantity} shares @ ${avg_cost:.2f}")
                        else:
                            print(f"  • {symbol} ({company_name}): Watchlist")
                    
                    if total_value > 0:
                        print(f"Total Portfolio Value: ${total_value:,.2f}")
            
            print("-" * 40)

    def fetch_portfolio_price_data(self, portfolio_id, start_date=None, end_date=None, period='1mo'):
        """Fetch price data for all stocks in a specific portfolio for a date range"""
        from data.data_collector import DataCollector
        
        # Get all stocks in the portfolio  
        stocks_query = """
        SELECT s.symbol FROM stocks s
        JOIN portfolio_holdings ph ON s.stock_id = ph.stock_id
        WHERE ph.portfolio_id = %s
        """
        
        stocks = self.db.execute_query(stocks_query, (portfolio_id,))
        
        if not stocks:
            print("No stocks found in portfolio")
            return False
        
        symbols = [stock[0] for stock in stocks]
        print(f"Fetching price data for {len(symbols)} stocks in portfolio...")
        print(f"Stocks: {', '.join(symbols)}")
        
        # Initialize data collector
        dc = DataCollector()
        success_count = 0
        
        for symbol in symbols:
            print(f"Fetching data for {symbol}...")
            
            try:
                if start_date and end_date:
                    # Use date range
                    success = dc.fetch_stock_data(symbol, interval='1d', start=start_date, end=end_date)
                else:
                    # Use period
                    success = dc.fetch_stock_data(symbol, period=period, interval='1d')
                
                if success:
                    success_count += 1
                    print(f" {symbol} data updated")
                else:
                    print(f" {symbol} data update failed")
                    
            except Exception as e:
                print(f" Error fetching {symbol}: {e}")
        
        print(f"\nCompleted: {success_count}/{len(symbols)} stocks updated successfully")
        return success_count > 0
