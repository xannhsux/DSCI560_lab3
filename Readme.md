# Stock Portfolio Management System (DSCI560_lab3)

This is a comprehensive stock portfolio management system that integrates with Yahoo Finance API for real-time and historical stock data collection. The system supports portfolio creation with stock lists, transaction execution, stock validation, and comprehensive portfolio management operations using a MySQL database backend.

## Docker Infrastructure and Initialization

### Docker Services Architecture

The system uses Docker containers orchestrated through docker-compose:

```bash
# Initialize and start all services
docker-compose up -d

# Stop all services
docker-compose down

# View running containers status
docker ps

# Access Python application container
docker exec -it stock_python_app bash
```

**Container Services:**

- **MySQL 8.4**: Primary database server (internal port 3306)
- **phpMyAdmin**: Web-based database administration at <http://localhost:8080>
- **Python Application**: Interactive container with source code volume mounted

### Database Connection Configuration

- **Internal Host**: mysql (Docker network communication)
- **External Host**: localhost (host machine access)
- **Database Name**: stock_analysis
- **Application User**: stock_user / Password: stock_password
- **Root Access**: root / Password: rootpassword

### Initial Database Setup

Database schema is automatically initialized from `sql/init.sql` on container startup. The initialization includes:

- Table creation with proper constraints and indexes
- Sample user data (user1, user2)
- Initial stock data (AAPL, GOOGL, MSFT, TSLA, AMZN)
- Sample portfolio structures

## Database Schema and Design

### Core Tables and Relationships

#### users Table

```sql
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

**Purpose**: User management and authentication
**Key Columns**:

- `user_id`: Primary key for user identification
- `username`: Unique username for login/identification
- `is_active`: Boolean flag for account status management

#### portfolios Table

```sql
CREATE TABLE portfolios (
    portfolio_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    portfolio_name VARCHAR(100) NOT NULL,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cash_balance DECIMAL(18,2) DEFAULT 0.00,
    total_value DECIMAL(18,2) DEFAULT 0.00,
    last_valued_at TIMESTAMP NULL DEFAULT NULL,
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

**Purpose**: Portfolio creation and tracking
**Key Columns**:

- `portfolio_id`: Primary key for portfolio identification
- `user_id`: Foreign key linking to portfolio owner
- `created_date`: Timestamp for portfolio creation tracking
- `cash_balance`: Available cash in portfolio
- `total_value`: Calculated total portfolio value

#### stocks Table

```sql
CREATE TABLE stocks (
    stock_id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    company_name VARCHAR(200),
    display_name VARCHAR(200),
    sector VARCHAR(100),
    exchange VARCHAR(100),
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**Purpose**: Stock information repository
**Key Columns**:

- `stock_id`: Primary key for stock identification
- `symbol`: Unique stock ticker symbol (e.g., AAPL, GOOGL)
- `company_name`: Full company name from Yahoo Finance
- `sector`: Business sector classification

#### portfolio_holdings Table

```sql
CREATE TABLE portfolio_holdings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    stock_id INT NOT NULL,
    quantity DECIMAL(20,6) NOT NULL DEFAULT 0,
    avg_cost DECIMAL(18,6) NOT NULL DEFAULT 0.0,
    market_value DECIMAL(18,2) DEFAULT 0.00,
    unrealized_pnl DECIMAL(18,6) DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES stocks(stock_id) ON DELETE CASCADE,
    UNIQUE KEY unique_portfolio_stock (portfolio_id, stock_id)
);
```

**Purpose**: Current portfolio positions tracking
**Key Columns**:

- `quantity`: Share count (positive=long, negative=short positions)
- `avg_cost`: Average cost basis per share (always positive)
- `market_value`: Current market value (quantity * current_price)
- `unrealized_pnl`: Unrealized profit/loss calculation
**Key Constraint**: `unique_portfolio_stock` ensures one record per stock per portfolio

#### portfolio_transactions Table

```sql
CREATE TABLE portfolio_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    stock_id INT NULL,
    txn_time DATETIME NOT NULL,
    action ENUM('BUY_TO_OPEN','BUY_TO_CLOSE','SELL_TO_CLOSE','SELL_TO_OPEN','DIVIDEND','SPLIT','CASH_IN','CASH_OUT','FEE','INTEREST'),
    quantity DECIMAL(20,6) NOT NULL DEFAULT 0.0,
    price DECIMAL(18,6) NOT NULL DEFAULT 0.0,
    txn_value DECIMAL(18,2) DEFAULT 0.00,
    fees DECIMAL(18,6) NOT NULL DEFAULT 0.0,
    notes VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES stocks(stock_id) ON DELETE SET NULL
);
```

**Purpose**: Immutable transaction ledger
**Key Columns**:

- `action`: Transaction type enumeration for position management
- `quantity`: Number of shares (always positive, direction from action)
- `price`: Price per share for the transaction
- `txn_value`: Calculated transaction value (quantity * price)
- `txn_time`: Execution timestamp for transaction ordering

#### stock_historical_data Table

```sql
CREATE TABLE stock_historical_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_id INT NOT NULL,
    date DATE NOT NULL,
    open_price DECIMAL(12,4),
    high_price DECIMAL(12,4),
    low_price DECIMAL(12,4),
    close_price DECIMAL(12,4),
    adj_close_price DECIMAL(12,4),
    volume BIGINT,
    daily_return DECIMAL(8,6),
    FOREIGN KEY (stock_id) REFERENCES stocks(stock_id) ON DELETE CASCADE,
    UNIQUE KEY unique_stock_date (stock_id, date)
);
```

**Purpose**: Historical price data storage
**Key Columns**:

- `date`: Trading date for price data
- `open_price, high_price, low_price, close_price`: OHLC price data
- `adj_close_price`: Adjusted closing price for splits/dividends
- `volume`: Trading volume
- `daily_return`: Calculated daily return percentage
**Key Constraint**: `unique_stock_date` prevents duplicate price records

#### stock_metadata Table

```sql
CREATE TABLE stock_metadata (
    stock_id INT PRIMARY KEY,
    market_cap BIGINT,
    current_price DECIMAL(12,4),
    pe_ratio DECIMAL(8,2),
    dividend_yield DECIMAL(5,4),
    beta DECIMAL(6,4),
    [25+ additional financial metrics],
    FOREIGN KEY (stock_id) REFERENCES stocks(stock_id) ON DELETE CASCADE
);
```

**Purpose**: Comprehensive financial metrics storage
**Key Columns**: 27 financial metrics including P/E ratios, beta, analyst recommendations, target prices, profit margins, and growth rates

## Application Script and Interface

### Main Application Interface (`src/main.py`)

The primary application provides a comprehensive menu-driven interface:

```bash
# Launch main application
docker exec -it stock_python_app python /app/src/main.py
```

**Menu Structure (13 Options)**:

1. Create New Portfolio
2. Create Portfolio with Stock List (NEW)
3. Manage Portfolio Stocks (Trading)  
4. Simple Portfolio Management (Add/Remove) (NEW)
5. Display All Portfolios (Enhanced) (NEW)
6. Fetch Portfolio Price Data (NEW)
7. Add Stock to Database (Direct)
8. Bulk Import from CSV
9. View Stock Information
10. Update Stock Metadata
11. Update Price Data (All Stocks)
12. Calculate Daily Returns (All Stocks)
13. Exit

### Core Application Components

#### Portfolio Manager (`src/portfolio/portfolio_manager.py`)

**Primary Methods**:

- `create_portfolio()`: Basic portfolio creation with user validation
- `create_portfolio_with_stocks()`: Create portfolio with initial stock list
- `add_stock_to_portfolio()`: Add stock without trading (composition management)
- `remove_stock_from_portfolio()`: Remove stock with position validation
- `execute_trade()`: Execute buy/sell transactions with holdings updates
- `display_enhanced_portfolios()`: Comprehensive portfolio display
- `fetch_portfolio_price_data()`: Date-range price data retrieval

#### Stock Validator (`src/portfolio/stock_validator.py`)

**Functionality**:

- Yahoo Finance API symbol validation
- Real-time stock information retrieval
- Error handling for invalid symbols
- Rate limiting with exponential backoff

#### Data Collector (`src/data/data_collector.py`)

**Key Methods**:

- `get_historical_data()`: Flexible date/period price data fetching
- `fetch_stock_data()`: Individual stock data retrieval and storage
- `add_stock_to_database()`: Stock information storage from Yahoo Finance
- `get_stock_info()`: Comprehensive financial metrics retrieval

### Portfolio Management Capabilities

#### Transaction Processing

The system implements a sophisticated transaction processing system:

1. **Transaction Entry**: User specifies action, quantity, price, fees
2. **Validation**: Stock existence, sufficient positions for sales
3. **Transaction Logging**: Immutable record in portfolio_transactions
4. **Holdings Update**: Automatic portfolio_holdings recalculation
5. **Cost Basis Calculation**: Weighted average cost tracking
6. **P&L Tracking**: Realized and unrealized profit/loss computation

#### Position Management

- **Long Positions**: Positive quantities in portfolio_holdings
- **Short Positions**: Negative quantities (if implemented)
- **Average Cost Basis**: Weighted calculation for multiple purchases
- **Market Value**: Real-time valuation based on current prices

## Individual Requirement Scripts

All requirement scripts are organized in the `src/scripts/` directory and automatically available in the container at `/app/src/scripts/`. When you download the project and run `docker-compose up -d`, all scripts will be immediately available without additional setup.

### 1. Portfolio Creation with Stock List and User Management

**Script**: `create_portfolio_with_stocks.py`
**Command**: `docker exec -it stock_python_app python /app/src/scripts/create_portfolio_with_stocks.py`

**Functionality**:

- User creation and selection (NEW FEATURE)
- Create new users with username and email validation
- Select from existing users or create new ones
- Portfolio naming and description
- Comma-separated stock symbol input
- Yahoo Finance symbol validation
- Automatic stock addition to portfolio
- Success/failure message display

**Enhanced User Flow**:

1. **User Management**: Enter existing User ID (1, 2, etc.) or 'new' to create a user
2. **New User Creation**: Provides username uniqueness validation and email input
3. **Portfolio Details**: Name and description input with validation
4. **Stock List Definition**: Comma-separated symbols with real-time validation

### 2. Portfolio Stock Management

**Script**: `manage_portfolio_stocks.py`  
**Command**: `docker exec -it stock_python_app python /app/src/scripts/manage_portfolio_stocks.py`

**Functionality**:

- Interactive portfolio selection
- Add stock with validation (displays "added successfully" or "invalid stock name")
- Remove stock with position verification
- Real-time portfolio state updates
- Portfolio details viewing

### 3. Transaction Execution and Holdings Updates

**Script**: `execute_transactions.py`
**Command**: `docker exec -it stock_python_app python /app/execute_transactions.py`

**Functionality**:

- BUY transaction execution (BUY_TO_OPEN)
- SELL transaction execution (SELL_TO_CLOSE)
- Before/after holdings comparison
- Automatic portfolio_holdings updates
- Average cost basis recalculation
- Transaction ledger maintenance
- Realized P&L calculation

### 4. Portfolio Price Data Fetching

**Script**: `fetch_portfolio_price_data.py`
**Command**: `docker exec -it stock_python_app python /app/fetch_portfolio_price_data.py`

**Functionality**:

- Portfolio stock identification
- Date range specification (periods: 1mo, 3mo, 6mo, 1y, etc.)
- Specific date range input (YYYY-MM-DD format)
- Bulk price data fetching for all portfolio stocks
- Database storage with duplicate prevention
- Data verification and integrity checking

### 5. Portfolio Display with Details

**Script**: `display_portfolios_with_details.py`
**Command**: `docker exec stock_python_app python /app/display_portfolios_with_details.py`

**Functionality**:

- Comprehensive portfolio information display
- Creation date prominent display
- Complete stock lists for each portfolio
- Portfolio ownership information
- Market value calculations
- Active positions vs watchlist distinction
- Chronological creation timeline
- System summary statistics

### 6. Master Requirements Overview

**Script**: `run_all_requirements.py`
**Command**: `docker exec stock_python_app python /app/run_all_requirements.py`

**Functionality**:

- Requirements documentation and explanation
- Script usage instructions
- Testing sequence guidance
- System architecture overview

## Technical Implementation Details

### Yahoo Finance Integration

**Supported Data Types**:

- Historical OHLCV data with configurable periods and intervals
- Real-time stock quotes and metadata
- Company fundamental data (27+ metrics)
- Symbol validation and error handling

**Rate Limiting**:

- 1-second minimum intervals between requests
- Exponential backoff on API errors
- Retry mechanisms for transient failures

**IMPORTANT - yfinance Package Version**:

- **CRITICAL**: The system requires yfinance version 0.2.65 or newer
- Older versions (e.g., 0.2.28) will hit rate limits immediately in Docker environments
- The `app/requirements.txt` file specifies `yfinance==0.2.65` which includes improved rate limiting
- If you encounter immediate rate limiting errors, verify your yfinance version and upgrade to the current version
- Check package dependencies after updating

### Data Integrity and Validation

- Prepared SQL statements prevent injection attacks
- Foreign key constraints maintain referential integrity
- Unique constraints prevent duplicate data
- Transaction atomicity ensures data consistency
- Input validation and error handling throughout

### Performance Optimizations

- Database connection pooling
- Indexed queries for fast data retrieval
- Batch operations for bulk data processing
- Caching mechanisms for recently fetched data

## Testing and Verification

### System Verification Command

```bash
docker exec stock_python_app python -c "
import sys; sys.path.append('/app/src')
from portfolio.portfolio_manager import PortfolioManager
pm = PortfolioManager()
print('System operational - all methods available')
"
```

### Database Status Check

```bash
docker exec stock_python_app python -c "
import sys; sys.path.append('/app/src')
from database.db_connection import DatabaseConnection
db = DatabaseConnection()
if db.connect(): print('Database connection successful')
"
```

The system provides comprehensive portfolio management functionality with proper transaction handling, stock validation, and data integrity maintenance suitable for educational and development purposes.
