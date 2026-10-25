"""Business logic: products, suppliers, stock movements, reconciliation."""
from datetime import date

IN_TYPES = ("IN", "ADJ_IN")
OUT_TYPES = ("OUT", "ADJ_OUT")
ALL_TYPES = IN_TYPES + OUT_TYPES


class InsufficientStockError(Exception):
    """Raised when a movement would make stock negative."""


class InventoryService:
    def __init__(self, db):
        self.db = db

    # ---------- master data ----------
    def add_supplier(self, name):
        if not name.strip():
            raise ValueError("Supplier name required")
        self.db.execute("INSERT INTO suppliers (supplier_name) VALUES (?)", (name.strip(),))
        return self.db.query("SELECT supplier_id FROM suppliers WHERE supplier_name=?", (name.strip(),))[0]["supplier_id"]

    def add_product(self, sku, name, category, reorder_level, unit_cost, opening_balance=0):
        if reorder_level < 0 or unit_cost < 0 or opening_balance < 0:
            raise ValueError("reorder_level, unit_cost and opening_balance must be >= 0")
        with self.db.transaction():
            pid = self.db.execute(
                "INSERT INTO products (sku, product_name, category, reorder_level, unit_cost, "
                "opening_balance, current_stock) VALUES (?,?,?,?,?,?,?)",
                (sku, name, category, reorder_level, unit_cost, opening_balance, opening_balance))
            self._log("PRODUCT_ADDED", pid, f"{sku} opening_balance={opening_balance}")
        return pid

    def get_product_id(self, sku):
        r = self.db.query("SELECT product_id FROM products WHERE sku=?", (sku,))
        if not r:
            raise ValueError(f"Unknown SKU: {sku}")
        return r[0]["product_id"]

    # ---------- movements ----------
    def stock_in(self, product_id, qty, supplier_id=None, when=None):
        return self._record(product_id, "IN", qty, when, supplier_id, None)

    def stock_out(self, product_id, qty, when=None, reason=None):
        return self._record(product_id, "OUT", qty, when, None, reason)

    def adjust(self, product_id, qty_change, reason, when=None):
        """Signed manual correction (damage, count difference...). Reason is mandatory."""
        if qty_change == 0:
            raise ValueError("Adjustment cannot be zero")
        t = "ADJ_IN" if qty_change > 0 else "ADJ_OUT"
        return self._record(product_id, t, abs(qty_change), when, None, reason)

    def _record(self, product_id, ttype, qty, when, supplier_id, reason):
        if ttype not in ALL_TYPES:
            raise ValueError("Invalid transaction type")
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Quantity must be a positive integer")
        if ttype.startswith("ADJ") and not (reason and reason.strip()):
            raise ValueError("Adjustments require a reason")
        when = str(when or date.today())
        lock = " FOR UPDATE" if self.db.backend == "mysql" else ""
        with self.db.transaction():
            row = self.db.query("SELECT current_stock, sku FROM products WHERE product_id=?" + lock, (product_id,))
            if not row:
                raise ValueError(f"Unknown product_id {product_id}")
            cur, sku = row[0]["current_stock"], row[0]["sku"]
            new = cur + qty if ttype in IN_TYPES else cur - qty
            if new < 0:                                   # never silently negative
                raise InsufficientStockError(
                    f"{sku}: cannot remove {qty}, only {cur} in stock")
            tid = self.db.execute(
                "INSERT INTO stock_transactions (product_id, transaction_date, transaction_type, "
                "quantity, supplier_id, reason) VALUES (?,?,?,?,?,?)",
                (product_id, when, ttype, qty, supplier_id, reason))
            self.db.execute("UPDATE products SET current_stock=? WHERE product_id=?", (new, product_id))
            self._log(ttype, product_id, f"txn={tid} qty={qty} {cur}->{new}" + (f" reason={reason}" if reason else ""))
        return tid

    def _log(self, action, product_id, details):
        self.db.execute("INSERT INTO audit_log (action, product_id, details) VALUES (?,?,?)",
                        (action, product_id, details))

    # ---------- reconciliation ----------
    def reconcile(self):
        """Recompute stock = opening + IN/ADJ_IN - OUT/ADJ_OUT from history and compare with stored value.
        Also detects running balances that dipped below zero (e.g. from back-dated entries)."""
        issues = []
        for p in self.db.query("SELECT product_id, sku, opening_balance, current_stock FROM products"):
            txs = self.db.query(
                "SELECT transaction_type t, quantity q FROM stock_transactions WHERE product_id=? "
                "ORDER BY transaction_date, transaction_id", (p["product_id"],))
            bal, low = p["opening_balance"], p["opening_balance"]
            for x in txs:
                bal += x["q"] if x["t"] in IN_TYPES else -x["q"]
                low = min(low, bal)
            if bal != p["current_stock"]:
                issues.append(f"{p['sku']}: stored {p['current_stock']} != calculated {bal}")
            if low < 0:
                issues.append(f"{p['sku']}: running balance went negative ({low}) in history")
        return issues
