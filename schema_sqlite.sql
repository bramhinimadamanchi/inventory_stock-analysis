CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS products (
    product_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    sku             TEXT NOT NULL UNIQUE,
    product_name    TEXT NOT NULL,
    category        TEXT NOT NULL,
    reorder_level   INTEGER NOT NULL DEFAULT 0 CHECK (reorder_level >= 0),
    unit_cost       REAL NOT NULL CHECK (unit_cost >= 0),
    opening_balance INTEGER NOT NULL DEFAULT 0 CHECK (opening_balance >= 0),
    current_stock   INTEGER NOT NULL DEFAULT 0 CHECK (current_stock >= 0)
);
CREATE TABLE IF NOT EXISTS stock_transactions (
    transaction_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id       INTEGER NOT NULL REFERENCES products(product_id),
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('IN','OUT','ADJ_IN','ADJ_OUT')),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    supplier_id      INTEGER NULL REFERENCES suppliers(supplier_id),
    reason           TEXT NULL,
    created_at       TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_txn_product_date ON stock_transactions(product_id, transaction_date);
CREATE TABLE IF NOT EXISTS audit_log (
    log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time TEXT DEFAULT CURRENT_TIMESTAMP,
    action     TEXT NOT NULL,
    product_id INTEGER NULL,
    details    TEXT NOT NULL
);
