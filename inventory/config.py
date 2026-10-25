"""Configurable thresholds and DB settings (override with environment variables)."""
import os

DB_BACKEND = os.getenv("DB_BACKEND", "sqlite")          # 'sqlite' (demo) or 'mysql'
SQLITE_PATH = os.getenv("SQLITE_PATH", "inventory.db")
MYSQL = dict(
    host=os.getenv("MYSQL_HOST", "localhost"),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DATABASE", "inventory_db"),
)

# Analysis thresholds (recommendations only - no automatic purchasing)
TARGET_STOCK_MULTIPLIER = float(os.getenv("TARGET_MULT", 2.0))  # reorder up to level * multiplier
ANALYSIS_WINDOW_DAYS = int(os.getenv("WINDOW_DAYS", 30))
FAST_PERCENTILE = 75   # out-qty at/above this percentile => Fast
SLOW_PERCENTILE = 25   # at/below => Slow
