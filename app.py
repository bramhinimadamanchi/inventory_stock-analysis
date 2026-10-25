"""Interactive website. Run:  python app.py   then open  http://127.0.0.1:5000"""
import time
from flask import Flask, request, redirect, url_for, flash, render_template_string, send_from_directory
from inventory.db import Database
from inventory.service import InventoryService, InsufficientStockError
from inventory import report, analytics as A, config

app = Flask(__name__)
app.secret_key = "inventory-demo"


def get_svc():
    db = Database()
    return db, InventoryService(db)


def setup():
    db, svc = get_svc()
    db.init_schema()
    if not db.query("SELECT 1 FROM products LIMIT 1"):
        from seed_data import seed
        seed(svc)
    db.close()


PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Inventory System</title>
<style>
:root{--bg:#f5f7fb;--card:#fff;--text:#1d2433;--accent:#2f6fed;--line:#dfe4ee;--bad:#d9534f;--good:#2e9e5b}
@media (prefers-color-scheme: dark){:root{--bg:#12161f;--card:#1b2130;--text:#e8ecf5;--accent:#7aa2ff;--line:#2c3447}}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,Arial,sans-serif;background:var(--bg);color:var(--text)}
header{background:var(--accent);color:#fff;padding:18px;text-align:center}header h1{margin:0;font-size:1.5rem}
main{max-width:1050px;margin:auto;padding:12px}section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:14px 0}
h2{margin-top:0;color:var(--accent)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
form{display:flex;flex-direction:column;gap:8px}label{font-size:.85rem}
input,select,button{padding:8px;border-radius:8px;border:1px solid var(--line);font-size:1rem;background:var(--bg);color:var(--text)}
button{background:var(--accent);color:#fff;border:0;cursor:pointer;font-weight:600}
.msg{padding:10px;border-radius:8px;margin:8px 0;color:#fff}.msg.error{background:var(--bad)}.msg.ok{background:var(--good)}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
.low{color:var(--bad);font-weight:700}.big{font-size:2rem;font-weight:700}img{max-width:100%;height:auto}
nav a{color:#fff;margin:0 8px}
</style></head><body>
<header><h1>Inventory and Stock Analysis System</h1>
<nav><a href="/">Dashboard</a><a href="/audit">Audit log</a><a href="/reconcile">Reconcile</a></nav></header><main>
{% with msgs = get_flashed_messages(with_categories=true) %}{% for c,m in msgs %}<div class="msg {{c}}">{{m}}</div>{% endfor %}{% endwith %}
{% block body %}{% endblock %}
</main></body></html>"""

DASH = PAGE.replace("{% block body %}{% endblock %}", """
<section><h2>Estimated inventory value</h2><div class="big">{{ total }}</div></section>
<section><h2>Record stock movement</h2><div class="grid">
<form method="post" action="/stock-in"><b>Stock IN (received)</b>
 <label>Product</label><select name="sku">{% for p in prods %}<option value="{{p.sku}}">{{p.sku}} - {{p.product_name}}</option>{% endfor %}</select>
 <label>Quantity</label><input type="number" name="qty" min="1" required>
 <label>Supplier</label><select name="supplier">{% for s in sups %}<option value="{{s.supplier_id}}">{{s.supplier_name}}</option>{% endfor %}</select>
 <button>Add stock</button></form>
<form method="post" action="/stock-out"><b>Stock OUT (sold/used)</b>
 <label>Product</label><select name="sku">{% for p in prods %}<option value="{{p.sku}}">{{p.sku}} - {{p.product_name}}</option>{% endfor %}</select>
 <label>Quantity</label><input type="number" name="qty" min="1" required>
 <button>Remove stock</button></form>
<form method="post" action="/adjust"><b>Adjustment (needs reason)</b>
 <label>Product</label><select name="sku">{% for p in prods %}<option value="{{p.sku}}">{{p.sku}} - {{p.product_name}}</option>{% endfor %}</select>
 <label>Change (e.g. -2 or 3)</label><input type="number" name="change" required>
 <label>Reason</label><input name="reason" placeholder="Damaged, count correction..." required>
 <button>Save adjustment</button></form>
<form method="post" action="/add-product"><b>New product</b>
 <input name="sku" placeholder="SKU e.g. TS-001" required><input name="name" placeholder="Product name" required>
 <input name="category" placeholder="Category" required><input type="number" name="reorder" placeholder="Reorder level" min="0" required>
 <input type="number" step="0.01" name="cost" placeholder="Unit cost" min="0" required><input type="number" name="opening" placeholder="Opening balance" min="0" value="0">
 <button>Add product</button></form></div></section>
<section><h2>Low-stock list <span class="low">({{ low|length }} items)</span></h2><div class="scroll">
<table><tr><th>SKU</th><th>Product</th><th>In stock</th><th>Reorder level</th><th>Suggested order</th></tr>
{% for r in low %}<tr><td>{{r.sku}}</td><td>{{r.product_name}}</td><td class="low">{{r.calculated_stock}}</td><td>{{r.reorder_level}}</td><td>{{r.suggested_order_qty}}</td></tr>{% else %}<tr><td colspan=5>All good - nothing is low.</td></tr>{% endfor %}</table></div></section>
<section><h2>Current stock</h2><div class="scroll"><table><tr><th>SKU</th><th>Product</th><th>Category</th><th>Stock</th><th>Reorder</th><th>Unit cost</th><th>Value</th></tr>
{% for r in rep %}<tr><td>{{r.sku}}</td><td>{{r.product_name}}</td><td>{{r.category}}</td><td class="{{ 'low' if r.calculated_stock<=r.reorder_level }}">{{r.calculated_stock}}</td><td>{{r.reorder_level}}</td><td>{{r.unit_cost}}</td><td>{{r.stock_value}}</td></tr>{% endfor %}</table></div></section>
<section><h2>Movement (last {{ window }} days)</h2><div class="scroll"><table><tr><th>SKU</th><th>Product</th><th>In</th><th>Out</th><th>Avg/day</th><th>Days of cover</th><th>Class</th></tr>
{% for r in mov %}<tr><td>{{r.sku}}</td><td>{{r.product_name}}</td><td>{{r.qty_in}}</td><td>{{r.qty_out}}</td><td>{{r.avg_daily_out}}</td><td>{{ '-' if r.days_of_cover!=r.days_of_cover else r.days_of_cover }}</td><td>{{r.movement_class}}</td></tr>{% endfor %}</table></div></section>
<section><h2>Charts</h2>{% for c in ['stock_level_chart','stock_movement_chart','low_stock_chart','inventory_value_chart'] %}<img src="/chart/{{c}}.png?t={{ts}}" alt="{{c}}">{% endfor %}</section>
""")


def page(body_title, inner):
    return render_template_string(PAGE.replace("{% block body %}{% endblock %}", inner))


@app.route("/")
def dashboard():
    db, svc = get_svc()
    try:
        report.generate(db)
        products, tx = A.load(db)
        rep = A.current_stock_report(products, tx)
        low = A.low_stock(rep)
        mov = A.movement_table(products, rep, tx)
        total, _ = A.valuation(rep)
        sups = db.query("SELECT * FROM suppliers")
        return render_template_string(
            DASH, total=f"{total:,.2f}", prods=products.to_dict("records"), sups=sups,
            low=low.to_dict("records"), rep=rep.to_dict("records"), mov=mov.to_dict("records"),
            window=config.ANALYSIS_WINDOW_DAYS, ts=int(time.time()))
    finally:
        db.close()


def run_action(fn):
    db, svc = get_svc()
    try:
        msg = fn(svc)
        flash(msg, "ok")
    except InsufficientStockError as e:
        flash(f"REJECTED: {e}", "error")
    except Exception as e:
        flash(f"Error: {e}", "error")
    finally:
        db.close()
    return redirect(url_for("dashboard"))


@app.post("/stock-in")
def stock_in():
    f = request.form
    return run_action(lambda s: (s.stock_in(s.get_product_id(f["sku"]), int(f["qty"]), int(f["supplier"])),
                                 f"Added {f['qty']} to {f['sku']}")[1])


@app.post("/stock-out")
def stock_out():
    f = request.form
    return run_action(lambda s: (s.stock_out(s.get_product_id(f["sku"]), int(f["qty"])),
                                 f"Removed {f['qty']} from {f['sku']}")[1])


@app.post("/adjust")
def adjust():
    f = request.form
    return run_action(lambda s: (s.adjust(s.get_product_id(f["sku"]), int(f["change"]), f["reason"]),
                                 f"Adjustment saved for {f['sku']} and logged")[1])


@app.post("/add-product")
def add_product():
    f = request.form
    return run_action(lambda s: (s.add_product(f["sku"].strip(), f["name"], f["category"], int(f["reorder"]),
                                               float(f["cost"]), int(f["opening"] or 0)),
                                 f"Product {f['sku']} added")[1])


@app.route("/chart/<name>.png")
def chart(name):
    return send_from_directory("outputs", f"{name}.png", max_age=0)


@app.route("/audit")
def audit():
    db, _ = get_svc()
    rows = db.query("SELECT event_time, action, details FROM audit_log ORDER BY log_id DESC LIMIT 100")
    db.close()
    inner = "<section><h2>Audit log (latest 100)</h2><div class='scroll'><table><tr><th>Time</th><th>Action</th><th>Details</th></tr>" + \
            "".join(f"<tr><td>{r['event_time']}</td><td>{r['action']}</td><td>{r['details']}</td></tr>" for r in rows) + "</table></div></section>"
    return page("Audit", inner)


@app.route("/reconcile")
def reconcile():
    db, svc = get_svc()
    issues = svc.reconcile()
    db.close()
    body = "<p>OK - every product's stock matches its transaction history.</p>" if not issues else "<ul>" + "".join(f"<li>{i}</li>" for i in issues) + "</ul>"
    return page("Reconcile", f"<section><h2>Reconciliation check</h2>{body}</section>")


if __name__ == "__main__":
    setup()
    print("Open this in your browser:  http://127.0.0.1:5000")
    app.run(debug=False)
