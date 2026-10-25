-- MySQL schema for Inventory and Stock Analysis System
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id   INT AUTO_INCREMENT PRIMARY KEY,
    supplier_name VARCHAR(120) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    product_id      INT AUTO_INCREMENT PRIMARY KEY,
    sku             VARCHAR(40)  NOT NULL UNIQUE,
    product_name    VARCHAR(150) NOT NULL,
    category        VARCHAR(80)  NOT NULL,
    reorder_level   INT          NOT NULL DEFAULT 0 CHECK (reorder_level >= 0),
    unit_cost       DECIMAL(12,2) NOT NULL CHECK (unit_cost >= 0),
    opening_balance INT          NOT NULL DEFAULT 0 CHECK (opening_balance >= 0),
    current_stock   INT          NOT NULL DEFAULT 0 CHECK (current_stock >= 0)  -- cached; reconciled against history
);

CREATE TABLE IF NOT EXISTS stock_transactions (
    transaction_id   INT AUTO_INCREMENT PRIMARY KEY,
    product_id       INT NOT NULL,
    transaction_date DATE NOT NULL,
    transaction_type ENUM('IN','OUT','ADJ_IN','ADJ_OUT') NOT NULL,
    quantity         INT NOT NULL CHECK (quantity > 0),
    supplier_id      INT NULL,
    reason           VARCHAR(255) NULL,   -- mandatory for adjustments
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id)  REFERENCES products(product_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
    INDEX idx_txn_product_date (product_id, transaction_date)
);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id     INT AUTO_INCREMENT PRIMARY KEY,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action     VARCHAR(40) NOT NULL,
    product_id INT NULL,
    details    VARCHAR(500) NOT NULL
);
