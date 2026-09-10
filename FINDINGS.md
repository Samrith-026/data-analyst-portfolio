# Results from the reproducible demo

All data is synthetic, generated with seed 26. No employer or customer data is included.

## Retail
Analyzed 2,400 orders. Net revenue totals $429,776.75. Review regional contribution alongside revenue before prioritizing sales investment. The cost model retains fulfillment/product costs on refunded orders and excludes overhead, tax and shipping, so contribution is not net profit.

## Distribution
Carrier C has the lowest on-time rate (49.38%). This pattern is deliberately embedded in the generator, not discovered evidence about an actual carrier. In a real investigation, compare lanes, service classes and sample sizes before attributing performance to a carrier or renegotiating contracts.

## Validation
Passed row-count, primary-key, refund-bound, transit-day, completion-flag, revenue-reconciliation and on-time reconciliation checks. No business impact is claimed.
