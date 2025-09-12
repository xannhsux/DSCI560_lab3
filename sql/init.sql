l
-- Create
database tables
USE stock_analysis;
-- User portfolio table
CREATE TABLE IF NO
T EXISTS portfolios (
portfolio_id INT AUT
O
_INCREMENT PRIMARY KEY,
portfolio_name VARCHAR(100)NO
T NULL,
created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
description TEXT
);
-- Stock in
formation table
CREATE TABLE IF NO
T EXISTS stocks (
stock_id INT AUT
O
_INCREMENT PRIMARY KEY,
symbol VARCHAR(10)NO
T NULL UNIQUE,
company_name VARCHAR(200),
sector VARCHAR(100),
added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Portfolio-stock relation
ship table
CREATE TABLE IF NO
T EXISTS portfolio_stocks (
id INT AUT
O
_INCREMENT PRIMARY KEY,
portfolio_id INT,
stock_id INT,
added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (portfolio_id)REFERENCES portfolios(portfolio_id)ON DELETE CASCADE,
FOREIGN KEY (stock_id)REFERENCES stocks(stock_id)ON DELETE CASCADE,
UNIQUE KEY unique_portfolio_stock (portfolio_id, stock_id)
);
-- Stock historical data table
CREATE TABLE IF NO
T EXISTS stock_prices (
id INT AUT
O
_INCREMENT PRIMARY KEY,
stock_id INT,
date DATE,
open_price DECIMAL(10,2),
high_price DECIMAL(10,2),
low_price DECIMAL(10,2),
close_price DECIMAL(10,2),
adjusted_close DECIMAL(10,2),
volume BIGINT,
daily_return DECIMAL(8,4),
Step 3: Python Application Code
src/database/db_connection.py
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (stock_id)REFERENCES stocks(stock_id)ON DELETE CASCADE,
UNIQUE KEY unique_stock_date (stock_id,date)
);
-- In
sert sample
data
INSERT IGNORE INT
O stocks (symbol, company_name, sector)VALUES
('AAPL','Apple Inc.','Technology'),
('GOOGL','Alphabet Inc.','Technology'),
('MSFT','Microsoft Corporation','Technology'),
('TSLA','Tesla, Inc.','Automotive'),
('AMZN','Amazon.com, Inc.','E-commerce');