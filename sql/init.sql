
-- Create database and use it
CREATE DATABASE IF NOT EXISTS stock_analysis;
USE stock_analysis;

-- Users table 
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- User portfolio table
CREATE TABLE IF NOT EXISTS portfolios (
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

-- Stock information table
CREATE TABLE IF NOT EXISTS stocks (
    stock_id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    company_name VARCHAR(200),
    display_name VARCHAR(200),
    sector VARCHAR(100),
    exchange VARCHAR(100),
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);


-- Portfolio holdings table
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    stock_id INT NOT NULL,
    quantity DECIMAL(20,6) NOT NULL DEFAULT 0, -- positive=long position, negative=short position
    avg_cost DECIMAL(18,6) NOT NULL DEFAULT 0.0, -- average cost basis (always positive)
    market_value DECIMAL(18,2) DEFAULT 0.00, -- current market value (quantity * current_price)
    unrealized_pnl DECIMAL(18,6) DEFAULT 0.0, -- unrealized profit/loss
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES stocks(stock_id) ON DELETE CASCADE,
    UNIQUE KEY unique_portfolio_stock (portfolio_id, stock_id)
);

-- Portfolio transaction ledger (immutable)
CREATE TABLE IF NOT EXISTS portfolio_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    stock_id INT NULL, -- allow NULL for pure cash events
    txn_time DATETIME NOT NULL,
    action ENUM(
        'BUY_TO_OPEN',      -- Buy to open long position
        'BUY_TO_CLOSE',     -- Buy to close short position
        'SELL_TO_CLOSE',    -- Sell to close long position
        'SELL_TO_OPEN',     -- Sell to open short position (short selling)
        'DIVIDEND',         -- Dividend payment
        'SPLIT',            -- Stock split
        'CASH_IN',          -- Cash deposit
        'CASH_OUT',         -- Cash withdrawal
        'FEE',              -- Trading fees/commissions
        'INTEREST'          -- Interest earned/paid
    ) NOT NULL,
    quantity DECIMAL(20,6) NOT NULL DEFAULT 0.0, -- shares (always positive, direction determined by action)
    price DECIMAL(18,6) NOT NULL DEFAULT 0.0,    -- price per share for trades; 0 for non-trade events
    txn_value DECIMAL(18,2) DEFAULT 0.00,        -- transaction value (quantity * price)
    fees DECIMAL(18,6) NOT NULL DEFAULT 0.0,     -- transaction fees/commissions
    notes VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES stocks(stock_id) ON DELETE SET NULL,
    INDEX idx_pt_portfolio_time (portfolio_id, txn_time),
    INDEX idx_pt_stock_time (stock_id, txn_time),
    INDEX idx_pt_action (action)
);

-- Stock historical data table (aligned with Yahoo Finance API)
CREATE TABLE IF NOT EXISTS stock_historical_data (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(stock_id) ON DELETE CASCADE,
    UNIQUE KEY unique_stock_date (stock_id, date),
    INDEX idx_stock_date (stock_id, date),
    INDEX idx_date (date)
);

-- Stock metadata table (for additional Yahoo Finance info)
CREATE TABLE IF NOT EXISTS stock_metadata (
    stock_id INT PRIMARY KEY,
    market_cap BIGINT,
    current_price DECIMAL(12,4),
    previous_close DECIMAL(12,4),
    volume BIGINT,
    average_volume BIGINT,
    pe_ratio DECIMAL(8,2),
    forward_pe DECIMAL(8,2),
    dividend_yield DECIMAL(5,4),
    fifty_two_week_high DECIMAL(12,4),
    fifty_two_week_low DECIMAL(12,4),
    beta DECIMAL(6,4),
    eps DECIMAL(8,4),
    book_value DECIMAL(12,4),
    price_to_book DECIMAL(8,4),
    price_to_sales DECIMAL(8,4),
    profit_margins DECIMAL(6,4),
    return_on_equity DECIMAL(6,4),
    return_on_assets DECIMAL(6,4),
    debt_to_equity DECIMAL(8,4),
    revenue_growth DECIMAL(6,4),
    earnings_growth DECIMAL(6,4),
    recommendation_mean DECIMAL(3,1),
    target_high_price DECIMAL(12,4),
    target_low_price DECIMAL(12,4),
    target_mean_price DECIMAL(12,4),
    analyst_count INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(stock_id) ON DELETE CASCADE
);

-- Insert sample data
INSERT IGNORE INTO users (username, email) VALUES 
('user1', 'user1@example.com'),
('user2', 'user2@example.com');

INSERT IGNORE INTO stocks (symbol, company_name, display_name, sector, exchange) VALUES
('AAPL', 'Apple Inc.', 'Apple Inc.', 'Technology', 'NMS'),
('GOOGL', 'Alphabet Inc.', 'Alphabet Inc.', 'Communication Services', 'NMS'),
('MSFT', 'Microsoft Corporation', 'Microsoft Corporation', 'Technology', 'NMS'),
('TSLA', 'Tesla, Inc.', 'Tesla, Inc.', 'Consumer Cyclical', 'NMS'),
('AMZN', 'Amazon.com, Inc.', 'Amazon.com, Inc.', 'Consumer Cyclical', 'NMS');

INSERT IGNORE INTO portfolios (user_id, portfolio_name, description) VALUES 
(1, 'User 1 Portfolio', 'Noraml portfolio'),
(1, 'User 2 Portfolio', 'Normal portfolio'),
(2, 'User 1 Growth Portfolio', 'High growth potential stocks');