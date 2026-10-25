# Inventory and Stock Analysis System (Project 11)

Tracks stock-in / stock-out movements, calculates current stock from opening balance + transactions,
flags low-stock items, and analyses movement and valuation with Pandas, NumPy and Matplotlib.
Reorder output is a **recommendation only** (configurable thresholds) - nothing is purchased automatically.

## Quick start (demo - runs with no database server)
```
pip install -r requirements.txt
python main.py demo          # creates DB, loads sample data, writes reports/charts to ./outputs
python -m unittest tests.test_inventory
```

## Using MySQL
```
mysql -u root -p -e "CREATE DATABASE inventory_db"
export DB_BACKEND=mysql MYSQL_USER=root MYSQL_PASSWORD=yourpass MYSQL_DATABASE=inventory_db
python main.py demo
```
(Schema: `schema_mysql.sql`. `schema_sqlite.sql` is the equivalent used for the zero-setup demo.)

## CLI
```
python main.py add-supplier "Acme Ltd"
python main.py add-product SKU-1 "Widget" Hardware 20 5.50 --opening 100
python main.py stock-in SKU-1 50 --supplier 1
python main.py stock-out SKU-1 30
python main.py adjust SKU-1 -2 "Damaged in transit"
python main.py report | reconcile | audit
```

## Tables
products, suppliers, stock_transactions (as specified) + `audit_log`.
Extra columns: `products.opening_balance`, `products.current_stock` (cached, verified by reconciliation),
`stock_transactions.reason`. Transaction types: `IN`, `OUT`, `ADJ_IN`, `ADJ_OUT`.

## How the acceptance criteria are met
| Criterion | Implementation |
|---|---|
| Stock cannot silently become negative | `_record()` locks the product row (`SELECT ... FOR UPDATE` on MySQL), rejects with `InsufficientStockError`, and rolls back the whole transaction. DB `CHECK (current_stock >= 0)` is a second safety net. |
| All adjustments are logged | Adjustments are `ADJ_IN/ADJ_OUT` rows with a mandatory reason, and every movement also writes an `audit_log` entry (before -> after stock). |
| History reconciles with current stock | `reconcile()` recalculates opening + signed transactions per product, compares with stored stock, and flags any running balance that dipped below zero. The report also recalculates stock from history. |

## Outputs (./outputs)
current_stock_report.csv, low_stock_list.csv, movement_analysis.csv, summary_report.txt,
stock_level_chart.png, stock_movement_chart.png, low_stock_chart.png, inventory_value_chart.png

## Configurable thresholds (`inventory/config.py` or env vars)
`TARGET_MULT` (order up to reorder_level x N), `WINDOW_DAYS` (movement window),
fast/slow percentiles for Fast / Medium / Slow / No-movement classification.

## Structure
```
main.py  seed_data.py  schema_mysql.sql  schema_sqlite.sql
inventory/ config.py db.py service.py analytics.py charts.py report.py
tests/test_inventory.py
```
