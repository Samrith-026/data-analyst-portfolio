"""Render reproducible SVG previews from checked-in synthetic query results."""

from __future__ import annotations

import csv
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1080, 520
LEFT, RIGHT, TOP, BOTTOM = 96, 1020, 132, 408
MONTH_LABELS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def render_chart(*, title: str, metric_label: str, values: list[float],
                 low: float, high: float, output: Path, axis_format: str) -> None:
    x_step = (RIGHT - LEFT) / (len(values) - 1)
    y_pos = lambda value: BOTTOM - (value - low) / (high - low) * (BOTTOM - TOP)
    x_pos = lambda index: LEFT + index * x_step
    ticks = [low + (high - low) * index / 4 for index in range(5)]
    points = " ".join(f"{x_pos(i):.1f},{y_pos(v):.1f}" for i, v in enumerate(values))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title description">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="description">Monthly 2025 {escape(metric_label)} from the checked-in synthetic analysis results.</desc>',
        '<rect width="1080" height="520" rx="22" fill="#0c1726"/>',
        '<text x="54" y="62" fill="#f5f8fc" font-family="Arial,sans-serif" font-size="28" font-weight="700">' + escape(title) + '</text>',
        '<text x="54" y="96" fill="#a7b5c7" font-family="Arial,sans-serif" font-size="15">2025 monthly results · reproducible synthetic data</text>',
        '<rect x="800" y="37" width="226" height="37" rx="18" fill="#153a42"/>',
        '<text x="913" y="61" text-anchor="middle" fill="#7ce7cf" font-family="Arial,sans-serif" font-size="13" font-weight="700">CASE STUDY PREVIEW</text>',
    ]
    for tick in ticks:
        y = y_pos(tick)
        parts.append(f'<line x1="{LEFT}" y1="{y:.1f}" x2="{RIGHT}" y2="{y:.1f}" stroke="#26384a" stroke-width="1"/>')
        parts.append(f'<text x="{LEFT - 16}" y="{y + 5:.1f}" text-anchor="end" fill="#a7b5c7" font-family="Arial,sans-serif" font-size="13">{escape(axis_format.format(tick))}</text>')
    parts.append(f'<polyline points="{points}" fill="none" stroke="#62dbc5" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    for i, value in enumerate(values):
        x, y = x_pos(i), y_pos(value)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="#0c1726" stroke="#62dbc5" stroke-width="3"/>')
        if i in (0, 3, 6, 9, 11):
            parts.append(f'<text x="{x:.1f}" y="{y - 13:.1f}" text-anchor="middle" fill="#e8f0f8" font-family="Arial,sans-serif" font-size="12">{escape(axis_format.format(value))}</text>')
    for i, label in enumerate(MONTH_LABELS):
        parts.append(f'<text x="{x_pos(i):.1f}" y="{BOTTOM + 31}" text-anchor="middle" fill="#a7b5c7" font-family="Arial,sans-serif" font-size="12">{label}</text>')
    parts.extend([
        '<line x1="54" y1="466" x2="1026" y2="466" stroke="#26384a"/>',
        '<text x="54" y="493" fill="#8193a8" font-family="Arial,sans-serif" font-size="12">Preview generated from the project’s exported query results; not a live service.</text>',
        '</svg>',
    ])
    output.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    retail = rows(ROOT / "retail-performance" / "results" / "analysis_1.csv")
    retail_values = [float(row["net_revenue"]) / 1000 for row in retail]
    render_chart(
        title="Retail Performance | Net Revenue by Month",
        metric_label="net revenue in USD thousands",
        values=retail_values,
        low=0,
        high=50,
        output=ROOT / "retail-performance" / "preview.svg",
        axis_format="${:.0f}k",
    )

    delivery = rows(ROOT / "distribution-sla" / "results" / "analysis_2.csv")
    otif_values = [float(row["otif_pct"]) for row in delivery]
    render_chart(
        title="Distribution SLA | Monthly OTIF",
        metric_label="on-time-in-full percentage",
        values=otif_values,
        low=60,
        high=80,
        output=ROOT / "distribution-sla" / "preview.svg",
        axis_format="{:.0f}%",
    )


if __name__ == "__main__":
    main()

