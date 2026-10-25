"""CLI for the Inventory and Stock Analysis System.
   python main.py demo            -> init DB, seed data, generate all reports
   python main.py <command> ...   -> see --help
"""
import argparse, os
from inventory.db import Database
from inventory.service import InventoryService, InsufficientStockError
from inventory import report


def main():
    ap = argparse.ArgumentParser(description="Inventory and Stock Analysis System")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="create tables")
    sub.add_parser("demo", help="reset DB, seed sample data, produce reports")
    sub.add_parser("report", help="generate reports and charts into ./outputs")
    sub.add_parser("reconcile", help="verify history reconciles with stored stock")
    sub.add_parser("audit", help="show audit log")
    p = sub.add_parser("add-supplier"); p.add_argument("name")
    p = sub.add_parser("add-product")
    for a in ("sku", "name", "category"): p.add_argument(a)
    p.add_argument("reorder_level", type=int); p.add_argument("unit_cost", type=float)
    p.add_argument("--opening", type=int, default=0)
    p = sub.add_parser("stock-in"); p.add_argument("sku"); p.add_argument("qty", type=int)
    p.add_argument("--supplier", type=int); p.add_argument("--date")
    p = sub.add_parser("stock-out"); p.add_argument("sku"); p.add_argument("qty", type=int); p.add_argument("--date")
    p = sub.add_parser("adjust", help="signed change, e.g. -3, with reason")
    p.add_argument("sku"); p.add_argument("change", type=int); p.add_argument("reason"); p.add_argument("--date")
    a = ap.parse_args()

    if a.cmd == "demo":
        from seed_data import seed
        from inventory import config
        if config.DB_BACKEND == "sqlite" and os.path.exists(config.SQLITE_PATH):
            os.remove(config.SQLITE_PATH)
    db = Database(); svc = InventoryService(db)
    try:
        if a.cmd in ("init", "demo"):
            db.init_schema()
        if a.cmd == "demo":
            seed(svc); print("Demo data loaded.")
            print(report.generate(db)); print("\nReconciliation:", svc.reconcile() or "OK - all stock reconciles")
        elif a.cmd == "report": print(report.generate(db))
        elif a.cmd == "reconcile": print(svc.reconcile() or "OK - all stock reconciles")
        elif a.cmd == "audit":
            for r in db.query("SELECT event_time, action, details FROM audit_log ORDER BY log_id DESC LIMIT 30"):
                print(r["event_time"], r["action"], r["details"])
        elif a.cmd == "add-supplier": print("supplier_id", svc.add_supplier(a.name))
        elif a.cmd == "add-product": print("product_id", svc.add_product(a.sku, a.name, a.category, a.reorder_level, a.unit_cost, a.opening))
        elif a.cmd == "stock-in": print("txn", svc.stock_in(svc.get_product_id(a.sku), a.qty, a.supplier, a.date))
        elif a.cmd == "stock-out": print("txn", svc.stock_out(svc.get_product_id(a.sku), a.qty, a.date))
        elif a.cmd == "adjust": print("txn", svc.adjust(svc.get_product_id(a.sku), a.change, a.reason, a.date))
    except InsufficientStockError as e:
        print("REJECTED:", e)
    except ValueError as e:
        print("ERROR:", e)
    finally:
        db.close()


if __name__ == "__main__":
    main()
