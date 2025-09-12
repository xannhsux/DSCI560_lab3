from database.db_connection import DatabaseConnection
from portfolio.stock_validator import StockValidator
import yfinance as yf
from datetime import datetime

class PortfolioManager:
    def __init__(self):
        self.db = DatabaseConnection()
        self.validator = StockValidator()

    def create_portfolio(self, name, description=""):
        """Create a new portfolio"""
        query = "INSERT INTO portfolios (portfolio_name, description) VALUES (%s, %s)"
        result = self.db.execute_update(query, (name, description))
        
        if result > 0:
            print(f"Portfolio '{name}' created successfully!")
            return True
        else:
            print("Failed to create portfolio!")
            return False

    def add_stock_to_portfolio(self, portfolio_id, symbol):
        """Add a stock to the portfolio"""
        # Validate stock symbol
        if not self.validator.validate_stock(symbol):
            print(f"Error: '{symbol}' is not a valid stock symbol")
            return False

        # Get or create stock record
        stock_id = self._get_or_create_stock(symbol)
        if not stock_id:
            print(f"Unable to get information for stock '{symbol}'")
            return False

        # Add to portfolio
        query = """
        INSERT INTO portfolio_stocks (portfolio_id, stock_id) 
        VALUES (%s, %s)
        """
        try:
            result = self.db.execute_update(query, (portfolio_id, stock_id))
            if result > 0:
                print(f"Stock '{symbol}' successfully added to portfolio")
                return True
            else:
                print("Failed to add stock")
                return False
        except:
            print(f"Stock '{symbol}' is already in this portfolio")
            return False

    def remove_stock_from_portfolio(self, portfolio_id, symbol):
        """Remove a stock from the portfolio"""
        # Get stock ID
        stock_query = "SELECT stock_id FROM stocks WHERE symbol = %s"
        stock_result = self.db.execute_query(stock_query, (symbol,))
        
        if not stock_result:
            print(f"Stock '{symbol}' not found")
            return False
        
        stock_id = stock_result[0][0]
        
        # Remove from portfolio
        remove_query = """
        DELETE FROM portfolio_stocks 
        WHERE portfolio_id = %s AND stock_id = %s
        """
        result = self.db.execute_update(remove_query, (portfolio_id, stock_id))
        
        if result > 0:
            print(f"Stock '{symbol}' removed from portfolio")
            return True
        else:
            print(f"Stock '{symbol}' not found in portfolio")
            return False

    def display_all_portfolios(self):
        """Display all portfolios"""
        query = """
        SELECT p.portfolio_id, p.portfolio_name, p.created_date, p.description,
               GROUP_CONCAT(s.symbol) as stocks
        FROM portfolios p
        LEFT JOIN portfolio_stocks ps ON p.portfolio_id = ps.portfolio_id
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
        """Get all stocks in a specific portfolio"""
        query = """
        SELECT s.stock_id, s.symbol, s.company_name
        FROM stocks s
        JOIN portfolio_stocks ps ON s.stock_id = ps.stock_id
        WHERE ps.portfolio_id = %s
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