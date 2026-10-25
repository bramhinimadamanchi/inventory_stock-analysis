"""Matplotlib charts."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def stock_levels_chart(history, products, movement, path, top_n=5):
    fig, ax = plt.subplots(figsize=(10, 5))
    skus = movement.head(top_n)["sku"].tolist()
    rl = dict(zip(products["sku"], products["reorder_level"]))
    for i, s in enumerate(skus):
        line, = ax.plot(history.index, history[s], label=s, color=f"C{i}")
        ax.axhline(rl[s], color=f"C{i}", linestyle=":", alpha=.6)
    ax.set(title=f"Stock level over time - top {top_n} fast movers (dotted = reorder level)",
           xlabel="Date", ylabel="Units in stock")
    ax.legend(); ax.grid(alpha=.3); fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(path, dpi=130); plt.close(fig)


def movement_chart(movement, path, window):
    m = movement.sort_values("qty_out", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 6)); y = range(len(m)); h = 0.4
    ax.barh([i + h / 2 for i in y], m["qty_out"], h, label="Stock out", color="#d9534f")
    ax.barh([i - h / 2 for i in y], m["qty_in"], h, label="Stock in", color="#5cb85c")
    ax.set_yticks(list(y)); ax.set_yticklabels(m["sku"])
    ax.set(title=f"Product movement - last {window} days", xlabel="Units")
    ax.legend(); ax.grid(axis="x", alpha=.3); fig.tight_layout()
    fig.savefig(path, dpi=130); plt.close(fig)


def low_stock_chart(report, path):
    low = report[report["calculated_stock"] <= report["reorder_level"]]
    fig, ax = plt.subplots(figsize=(8, 4 + 0.2 * len(low)))
    if low.empty:
        ax.text(.5, .5, "No items below reorder level", ha="center"); ax.axis("off")
    else:
        y = range(len(low)); h = 0.4
        ax.barh([i + h / 2 for i in y], low["calculated_stock"], h, label="Current stock", color="#f0ad4e")
        ax.barh([i - h / 2 for i in y], low["reorder_level"], h, label="Reorder level", color="#777")
        ax.set_yticks(list(y)); ax.set_yticklabels(low["sku"]); ax.legend()
        ax.set(title="Low-stock items", xlabel="Units")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def valuation_chart(by_cat, total, path):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(by_cat.index, by_cat.values, color="#337ab7")
    for i, v in enumerate(by_cat.values):
        ax.text(i, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=8)
    ax.set(title=f"Estimated inventory value by category (total {total:,.2f})", ylabel="Value")
    plt.setp(ax.get_xticklabels(), rotation=20); fig.tight_layout()
    fig.savefig(path, dpi=130); plt.close(fig)
