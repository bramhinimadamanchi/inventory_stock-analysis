import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from inventory.db import Database
from inventory.service import InventoryService, InsufficientStockError


class T(unittest.TestCase):
    def setUp(self):
        self.db = Database("sqlite", ":memory:"); self.db.init_schema()
        self.s = InventoryService(self.db)
        self.pid = self.s.add_product("X1", "Widget", "Cat", 5, 10.0, opening_balance=10)

    def stock(self):
        return self.db.query("SELECT current_stock c FROM products")[0]["c"]

    def test_stock_flow(self):
        self.s.stock_in(self.pid, 5); self.s.stock_out(self.pid, 3)
        self.assertEqual(self.stock(), 12)

    def test_negative_blocked_and_nothing_written(self):
        with self.assertRaises(InsufficientStockError):
            self.s.stock_out(self.pid, 11)
        self.assertEqual(self.stock(), 10)
        self.assertEqual(self.db.query("SELECT COUNT(*) n FROM stock_transactions")[0]["n"], 0)

    def test_adjustment_needs_reason_and_is_logged(self):
        with self.assertRaises(ValueError):
            self.s.adjust(self.pid, -1, "")
        self.s.adjust(self.pid, -2, "Damaged")
        self.assertEqual(self.stock(), 8)
        logs = self.db.query("SELECT * FROM audit_log WHERE action='ADJ_OUT'")
        self.assertEqual(len(logs), 1)

    def test_invalid_quantity(self):
        for bad in (0, -1, 2.5):
            with self.assertRaises(ValueError):
                self.s.stock_in(self.pid, bad)

    def test_reconcile(self):
        self.s.stock_in(self.pid, 4); self.s.stock_out(self.pid, 6)
        self.assertEqual(self.s.reconcile(), [])
        self.db.execute("UPDATE products SET current_stock=99")   # tamper
        self.assertTrue(self.s.reconcile())


if __name__ == "__main__":
    unittest.main()
