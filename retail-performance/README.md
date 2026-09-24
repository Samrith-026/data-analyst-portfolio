# Retail Performance Analysis

![Synthetic monthly net revenue preview from the checked-in retail case study results](preview.svg)

This case study explores revenue, contribution, order value, and repeat purchasing across a generated year of retail orders. It uses synthetic data and makes no claims about an actual business.

## Preview

The chart above is rendered from [`results/analysis_1.csv`](results/analysis_1.csv), which is produced by the executable SQL in [`analysis.sql`](analysis.sql). It is a static case study graphic, not a live dashboard.

## Key questions

- How do monthly and regional net revenue and contribution change?
- What is the average order value after discounts and refunds?
- What share of observed customers placed more than one order?

## Reproduce

From the portfolio root:

```sh
python analyze.py
python scripts/build_previews.py
```

The SQL executes against an in-memory SQLite database. [`data/synthetic_data.csv`](data/synthetic_data.csv) contains 2,400 generated orders and is reproducible from the seeded generator.

