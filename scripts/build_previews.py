"""Render readable, high-resolution SVG case-study previews from checked-in SQL results."""
from __future__ import annotations
import csv
from html import escape
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
W, H = 1440, 760
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))

def text(x, y, value, size=20, color="#d7e2ee", weight=400, anchor="start"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}">{escape(str(value))}</text>'

def render(*, output: Path, title: str, subtitle: str, metric: str, values: list[float], low: float, high: float, ticks: list[float], format_axis, kpis: list[tuple[str, str]], color="#62dbc5"):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title description">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="description">{escape(subtitle)} {escape(metric)} chart, rendered from the case study SQL results.</desc>',
        '<rect width="100%" height="100%" rx="24" fill="#0c1726"/>',
        text(64, 72, title, 38, "#f5f8fc", 700),
        text(64, 111, subtitle, 20, "#a7b5c7"),
        '<rect x="1134" y="43" width="240" height="42" rx="21" fill="#153a42"/>',
        text(1254, 70, "SQL RESULTS · SYNTHETIC", 15, "#7ce7cf", 700, "middle"),
    ]
    kx, ky, gap, kw, kh = 64, 146, 18, 316, 112
    for i, (label, value) in enumerate(kpis):
        x = kx + i * (kw + gap)
        parts.append(f'<rect x="{x}" y="{ky}" width="{kw}" height="{kh}" rx="13" fill="#142235" stroke="#26384a"/>')
        parts.append(text(x + 20, ky + 34, label, 16, "#a7b5c7", 500))
        parts.append(text(x + 20, ky + 79, value, 29, "#f5f8fc", 700))
    left, right, top, bottom = 130, 1350, 340, 642
    y = lambda v: bottom - ((v - low) / (high - low)) * (bottom - top)
    x = lambda i: left + i * (right - left) / (len(values) - 1)
    parts.append(text(64, 312, metric, 22, "#f5f8fc", 600))
    for tick in ticks:
        ty = y(tick)
        parts.append(f'<line x1="{left}" y1="{ty:.1f}" x2="{right}" y2="{ty:.1f}" stroke="#26384a" stroke-width="1"/>')
        parts.append(text(left - 18, ty + 6, format_axis(tick), 16, "#a7b5c7", 400, "end"))
    points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
    parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')
    for i, v in enumerate(values):
        parts.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="7" fill="#0c1726" stroke="{color}" stroke-width="4"/>')
        parts.append(text(x(i), bottom + 32, MONTHS[i], 16, "#a7b5c7", 400, "middle"))
    parts.append(text(64, 724, "Static case-study visualization · generated from the checked-in query output · no live business data", 15, "#8193a8"))
    parts.append("</svg>")
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")

retail = rows(ROOT / "retail-performance" / "results" / "analysis_1.csv")
customers = rows(ROOT / "retail-performance" / "results" / "analysis_3.csv")[0]
orders = sum(int(row["orders"]) for row in retail)
revenue = sum(float(row["net_revenue"]) for row in retail)
avg_order = revenue / orders
render(
    output=ROOT / "retail-performance" / "preview.svg",
    title="Sales & Customer Analytics",
    subtitle=f"Retail SQL case study · 2025 · {orders:,} generated orders",
    metric="Monthly net revenue · USD",
    values=[float(row["net_revenue"]) for row in retail], low=0, high=50000,
    ticks=[0, 12500, 25000, 37500, 50000], format_axis=lambda v: f"${v/1000:.0f}k",
    kpis=[("NET REVENUE", f"${revenue:,.0f}"), ("AVERAGE ORDER", f"${avg_order:,.2f}"), ("OBSERVED CUSTOMERS", str(int(customers["customers"]))), ("REPEAT CUSTOMER RATE", f"{float(customers['repeat_customer_pct']):.1f}%")],
)

sla = rows(ROOT / "distribution-sla" / "results" / "analysis_2.csv")
carriers = rows(ROOT / "distribution-sla" / "results" / "analysis_1.csv")
shipments = sum(int(row["shipments"]) for row in carriers)
best = max(carriers, key=lambda row: float(row["otif_pct"]))
monthly = [float(row["otif_pct"]) for row in sla]
render(
    output=ROOT / "distribution-sla" / "preview.svg",
    title="Distribution Service-Level Analysis",
    subtitle=f"Shipment SQL case study · 2025 · {shipments:,} generated shipments",
    metric="Monthly on-time-in-full (OTIF) rate",
    values=monthly, low=55, high=85,
    ticks=[55, 65, 75, 85], format_axis=lambda v: f"{v:.0f}%",
    kpis=[("SHIPMENTS", f"{shipments:,}"), ("HIGHEST OTIF", f"{best['carrier']} · {float(best['otif_pct']):.2f}%"), ("MONTHLY PEAK", f"{max(monthly):.2f}%"), ("COMPARISON", "Synthetic data")], color="#8ab8ff",
)

