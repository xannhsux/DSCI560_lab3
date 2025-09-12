from portfolio.portfolio_manager import PortfolioManager
from data.data_collector import DataCollector
#from data.data_preprocessor import DataPreprocessor
from database.db_connection import DatabaseConnection
from datetime import datetime, timedelta
import time

class StockAnalysisApp:
    def __init__(self):
        self.portfolio_manager = PortfolioManager()
        self.data_collector = DataCollector()
        # self.data_preprocessor = DataPreprocessor()
        
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
            choice = input("\nEnter your choice (1-8): ").strip()
            
            if choice == '1':
                self.create_portfolio_flow()
            elif choice == '2':
                self.manage_portfolio_stocks()
            elif choice == '3':
                self.display_portfolios()
            elif choice == '4':
                self.fetch_stock_data_flow()
            # elif choice == '5':
            #     self.preprocess_data_flow()
            elif choice == '6':
                self.view_stock_info()
            # elif choice == '7':
            #     self.data_quality_report()
            elif choice == '8':
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
        print("2. Manage Portfolio Stocks")
        print("3. Display All Portfolios")
        print("4. Fetch Stock Data")
        # print("5. Preprocess Data")
        print("6. View Stock Information")
        # print("7. Data Quality Report")
        print("8. Exit")

    def create_portfolio_flow(self):
        """Create a new portfolio"""
        print("\n--- Create New Portfolio ---")
        name = input("Enter portfolio name: ").strip()
        description = input("Enter description (optional): ").strip()
        
        if name:
            self.portfolio_manager.create_portfolio(name, description)
        else:
            print("Portfolio name cannot be empty")

    def manage_portfolio_stocks(self):
        """Manage stocks in a portfolio"""
        print("\n--- Manage Portfolio Stocks ---")
        self.display_portfolios()
        
        try:
            portfolio_id = int(input("Enter portfolio ID: "))
            
            while True:
                print("\n1. Add Stock")
                print("2. Remove Stock")
                print("3. View Portfolio Stocks")
                print("4. Back to Main Menu")
                
                choice = input("Enter choice: ").strip()
                
                if choice == '1':
                    symbol = input("Enter stock symbol (e.g., AAPL): ").strip().upper()
                    self.portfolio_manager.add_stock_to_portfolio(portfolio_id, symbol)
                elif choice == '2':
                    symbol = input("Enter stock symbol to remove: ").strip().upper()
                    self.portfolio_manager.remove_stock_from_portfolio(portfolio_id, symbol)
                elif choice == '3':
                    stocks = self.portfolio_manager.get_portfolio_stocks(portfolio_id)
                    if stocks:
                        print("\nStocks in portfolio:")
                        for stock_id, symbol, company_name in stocks:
                            print(f"- {symbol}: {company_name}")
                    else:
                        print("No stocks in this portfolio")
                elif choice == '4':
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
        self.display_portfolios()
        
        try:
            portfolio_id = int(input("Enter portfolio ID: "))
            
            print("\nEnter date range for data collection:")
            start_date = input("Start date (YYYY-MM-DD) or press Enter for 30 days ago: ").strip()
            end_date = input("End date (YYYY-MM-DD) or press Enter for today: ").strip()
            
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            print(f"Fetching data from {start_date} to {end_date}...")
            self.data_collector.fetch_and_store_stock_data(portfolio_id, start_date, end_date)
            
        except ValueError:
            print("Invalid input")

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

if __name__ == "__main__":
    app = StockAnalysisApp()
    app.run()