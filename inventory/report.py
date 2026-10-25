"""Generate all expected outputs into ./outputs."""
from pathlib import Path
from . import analytics as A, charts, config


def generate(db, out_dir="outputs"):
    out = Path(out_dir); out.mkdir(exist_ok=True)
    products, tx = A.load(db)
    rep = A.current_stock_report(products, tx)
    low = A.low_stock(rep)
    mov = A.movement_table(products, rep, tx)
    total, by_cat = A.valuation(rep)
    hist = A.stock_history(products, tx, days=60)

    rep.to_csv(out / "current_stock_report.csv", index=False)
    low.to_csv(out / "low_stock_list.csv", index=False)
    mov.to_csv(out / "movement_analysis.csv", index=False)
    charts.stock_levels_chart(hist, products, mov, out / "stock_level_chart.png")
    charts.movement_chart(mov, out / "stock_movement_chart.png", config.ANALYSIS_WINDOW_DAYS)
    charts.low_stock_chart(rep, out / "low_stock_chart.png")
    charts.valuation_chart(by_cat, total, out / "inventory_value_chart.png")

    lines = ["=== CURRENT STOCK REPORT ===", rep.drop(columns=["matches_stored"]).to_string(index=False),
             "", "=== LOW-STOCK LIST (recommendations only) ===",
             low.to_string(index=False) if len(low) else "None",
             "", f"=== MOVEMENT (last {config.ANALYSIS_WINDOW_DAYS} days) ===",
             mov[["sku", "product_name", "qty_in", "qty_out", "avg_daily_out", "days_of_cover",
                  "movement_class"]].to_string(index=False),
             "", "=== ESTIMATED INVENTORY VALUE ===", by_cat.round(2).to_string(),
             f"TOTAL: {total:,.2f}"]
    text = "\n".join(lines)
    (out / "summary_report.txt").write_text(text)
    return text
