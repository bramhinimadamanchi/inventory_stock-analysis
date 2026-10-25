"""Generate realistic demo data through the service layer (so all rules are enforced)."""
import random
from datetime import date, timedelta
from inventory.service import InventoryService, InsufficientStockError

PRODUCTS = [  # sku, name, category, reorder, cost, opening, popularity(avg daily out), supplier idx
    ("EL-001", "USB-C Cable 1m", "Electronics", 40, 3.50, 150, 6, 0),
    ("EL-002", "Wireless Mouse", "Electronics", 25, 8.75, 80, 3, 0),
    ("EL-003", "Bluetooth Speaker", "Electronics", 15, 22.00, 40, 1.2, 0),
    ("ST-001", "A4 Paper Ream", "Stationery", 60, 4.20, 200, 7, 1),
    ("ST-002", "Gel Pen Box (10)", "Stationery", 30, 2.80, 120, 4, 1),
    ("ST-003", "Spiral Notebook", "Stationery", 35, 1.90, 100, 3, 1),
    ("HK-001", "Hand Sanitizer 500ml", "Housekeeping", 30, 3.10, 90, 4, 2),
    ("HK-002", "Floor Cleaner 1L", "Housekeeping", 20, 4.60, 60, 2, 2),
    ("HK-003", "Trash Bags (30)", "Housekeeping", 25, 2.40, 70, 0.3, 2),
    ("FN-001", "Office Chair", "Furniture", 5, 65.00, 20, 0.15, 0),
    ("FN-002", "Standing Desk", "Furniture", 3, 140.00, 8, 0.1, 0),
    ("EL-004", "Webcam HD", "Electronics", 12, 18.50, 30, 0, 0),   # dead stock example
]


def seed(svc, days=90, rng_seed=7):
    rnd = random.Random(rng_seed)
    sup = [svc.add_supplier(n) for n in ("TechSource Pvt Ltd", "OfficeWorld Traders", "CleanCo Supplies")]
    meta = {}
    for sku, name, cat, rl, cost, op, pop, si in PRODUCTS:
        pid = svc.add_product(sku, name, cat, rl, cost, op)
        meta[pid] = (sku, rl, pop, sup[si])
    start = date.today() - timedelta(days=days)
    for d in range(days + 1):
        day = start + timedelta(days=d)
        for pid, (sku, rl, pop, sid) in meta.items():
            if pop and rnd.random() < min(.95, pop / 2 + .3):
                q = max(1, int(rnd.gauss(pop, pop * .5)))
                try:
                    svc.stock_out(pid, q, when=day)
                except InsufficientStockError:
                    pass
            cur = svc.db.query("SELECT current_stock FROM products WHERE product_id=?", (pid,))[0]["current_stock"]
            # restock when low, except two items left low on purpose for the demo
            if cur <= rl and sku not in ("EL-002", "HK-001") and pop:
                svc.stock_in(pid, int(rl * 2.5), supplier_id=sid, when=day)
            elif cur <= rl and sku in ("EL-002", "HK-001") and d < days - 25:
                svc.stock_in(pid, int(rl * 2.5), supplier_id=sid, when=day)
    # logged adjustments
    svc.adjust(svc.get_product_id("EL-003"), -2, "Damaged in storage", when=date.today() - timedelta(days=10))
    svc.adjust(svc.get_product_id("ST-002"), 3, "Stock count correction", when=date.today() - timedelta(days=5))
