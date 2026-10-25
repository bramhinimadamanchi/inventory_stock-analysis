"""Pandas / NumPy analysis: stock report, low stock, movement, valuation, history."""
from datetime import date, timedelta
import numpy as np
import pandas as pd
from . import config
from .service import IN_TYPES


def load(db):
    products = pd.DataFrame(db.query("SELECT * FROM products"))
    tx = pd.DataFrame(db.query("SELECT * FROM stock_transactions"))
    if tx.empty:
        tx = pd.DataFrame(columns=["transaction_id", "product_id", "transaction_date",
                                   "transaction_type", "quantity", "supplier_id", "reason"])
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"])
    tx["quantity"] = tx["quantity"].astype(int)
    tx["signed_qty"] = np.where(tx["transaction_type"].isin(IN_TYPES), tx["quantity"], -tx["quantity"])
    products["unit_cost"] = products["unit_cost"].astype(float)
    return products, tx


def current_stock_report(products, tx):
    """Current stock recalculated from opening balance + transactions (and checked vs stored value)."""
    net = tx.groupby("product_id")["signed_qty"].sum()
    df = products.copy()
    df["calculated_stock"] = df["opening_balance"] + df["product_id"].map(net).fillna(0).astype(int)
    df["matches_stored"] = df["calculated_stock"] == df["current_stock"]
    df["stock_value"] = np.round(df["calculated_stock"].to_numpy() * df["unit_cost"].to_numpy(), 2)
    return df[["sku", "product_name", "category", "opening_balance", "calculated_stock",
               "reorder_level", "unit_cost", "stock_value", "matches_stored"]]


def low_stock(report, multiplier=None):
    """Items at/below reorder level + a *suggested* (not automatic) order quantity."""
    m = multiplier or config.TARGET_STOCK_MULTIPLIER
    low = report[report["calculated_stock"] <= report["reorder_level"]].copy()
    low["suggested_order_qty"] = np.maximum(np.ceil(low["reorder_level"] * m) - low["calculated_stock"], 0).astype(int)
    return low.sort_values("calculated_stock")[["sku", "product_name", "calculated_stock", "reorder_level",
                                                "suggested_order_qty"]]


def movement_table(products, report, tx, window=None):
    window = window or config.ANALYSIS_WINDOW_DAYS
    start = pd.Timestamp(date.today() - timedelta(days=window))
    w = tx[tx["transaction_date"] >= start]
    df = report.copy()
    df.insert(0, "product_id", products["product_id"].values)
    df["qty_out"] = df["product_id"].map(w[w.transaction_type == "OUT"].groupby("product_id")["quantity"].sum()).fillna(0).astype(int)
    df["qty_in"] = df["product_id"].map(w[w.transaction_type == "IN"].groupby("product_id")["quantity"].sum()).fillna(0).astype(int)
    df["avg_daily_out"] = np.round(df["qty_out"] / window, 2)
    with np.errstate(divide="ignore"):
        cover = np.where(df["avg_daily_out"] > 0, df["calculated_stock"] / df["avg_daily_out"], np.inf)
    df["days_of_cover"] = np.where(np.isinf(cover), np.nan, np.round(cover, 1))
    moving = df.loc[df["qty_out"] > 0, "qty_out"].to_numpy()
    if len(moving):
        hi = np.percentile(moving, config.FAST_PERCENTILE)
        lo = np.percentile(moving, config.SLOW_PERCENTILE)
    else:
        hi = lo = 0
    df["movement_class"] = np.select(
        [df["qty_out"] == 0, df["qty_out"] >= hi, df["qty_out"] <= lo],
        ["No movement", "Fast", "Slow"], default="Medium")
    return df.sort_values("qty_out", ascending=False)


def valuation(report):
    """Estimated inventory value (qty x unit cost) in total and by category."""
    total = float(np.sum(report["calculated_stock"].to_numpy() * report["unit_cost"].to_numpy()))
    by_cat = report.groupby("category")["stock_value"].sum().sort_values(ascending=False)
    return round(total, 2), by_cat


def stock_history(products, tx, days=60):
    """Daily closing stock per product = opening + cumulative signed movements."""
    end = pd.Timestamp(date.today())
    first = min(end - pd.Timedelta(days=days - 1), tx["transaction_date"].min() if len(tx) else end)
    idx = pd.date_range(first, end)
    cols = {}
    for p in products.itertuples():
        t = tx[tx.product_id == p.product_id]
        daily = t.groupby("transaction_date")["signed_qty"].sum().reindex(idx, fill_value=0)
        cols[p.sku] = p.opening_balance + daily.cumsum()
    return pd.DataFrame(cols, index=idx).iloc[-days:]
