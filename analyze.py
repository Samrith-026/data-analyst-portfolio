"""Rebuild two synthetic-data analytics case studies using only Python's standard library."""
from pathlib import Path
import csv
import json
import random
import sqlite3
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parent
random.seed(26)
con = sqlite3.connect(':memory:')
con.executescript('''
CREATE TABLE orders(order_id INTEGER PRIMARY KEY, order_date TEXT, region TEXT, category TEXT, customer_id INTEGER, units INTEGER, gross_sales REAL, discount REAL, refunds REAL, cost REAL);
CREATE TABLE shipments(shipment_id INTEGER PRIMARY KEY, month TEXT, carrier TEXT, region TEXT, promised_days INTEGER, actual_days INTEGER, complete INTEGER);
''')
orders = []
shipments = []
for i in range(1, 2401):
    day = date(2025, 1, 1) + timedelta(days=random.randrange(365))
    units = random.randint(1, 5)
    gross = units * random.choice([25, 45, 80, 120])
    discount = round(gross * random.choice([0, .05, .15]), 2)
    refund = round((gross - discount) if random.random() < .06 else 0, 2)
    orders.append((i, day.isoformat(), random.choice(['North','South','East','West']), random.choice(['Office','Home','Technology']), random.randint(1, 500), units, gross, discount, refund, round(gross*.58,2)))
    carrier = random.choice(['Carrier A','Carrier B','Carrier C'])
    actual = random.choice([2,3,3,4,5,6] if carrier == 'Carrier C' else [1,2,2,3,3,4])
    shipments.append((i, day.strftime('%Y-%m'), carrier, random.choice(['North','South','East','West']), 3, actual, int(random.random() > .04)))
con.executemany('INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?)', orders)
con.executemany('INSERT INTO shipments VALUES (?,?,?,?,?,?,?)', shipments)

def export(query, path):
    result = con.execute(query)
    columns = [x[0] for x in result.description]
    rows = result.fetchall()
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f); writer.writerow(columns); writer.writerows(rows)
    return [dict(zip(columns, row)) for row in rows]

for folder, table in [('retail-performance','orders'), ('distribution-sla','shipments')]:
    target = ROOT / folder
    (target/'data').mkdir(parents=True, exist_ok=True)
    (target/'results').mkdir(exist_ok=True)
    export(f'SELECT * FROM {table}', target/'data'/'synthetic_data.csv')
    queries = (target/'analysis.sql').read_text().split(';')
    results = []
    for n, query in enumerate(queries):
        if query.strip():
            results.append(export(query, target/'results'/f'analysis_{n+1}.csv'))
    (target/'results'/'results.json').write_text(json.dumps(results, indent=2))

# Independent reconciliation and bounds checks fail the build on bad outputs.
assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 2400
assert con.execute('SELECT COUNT(DISTINCT order_id) FROM orders').fetchone()[0] == 2400
assert con.execute('SELECT COUNT(*) FROM orders WHERE refunds > gross_sales-discount OR units<=0').fetchone()[0] == 0
assert con.execute('SELECT COUNT(*) FROM shipments WHERE actual_days<0 OR complete NOT IN (0,1)').fetchone()[0] == 0
python_net = sum(o[6]-o[7]-o[8] for o in orders)
sql_net = con.execute('SELECT SUM(gross_sales-discount-refunds) FROM orders').fetchone()[0]
assert abs(python_net-sql_net) < .01
on_time = sum(s[5]<=s[4] for s in shipments)
assert on_time == con.execute('SELECT SUM(actual_days<=promised_days) FROM shipments').fetchone()[0]

retail = json.loads((ROOT/'retail-performance/results/results.json').read_text())
sla = json.loads((ROOT/'distribution-sla/results/results.json').read_text())
def bars(rows, label, metric):
    maximum=max(r[metric] for r in rows)
    return ''.join(f'<div class="row"><b>{r[label]}</b><div class="bar" style="width:{r[metric]/maximum*70:.1f}%"></div><span>{r[metric]:,.2f}</span></div>' for r in rows)
html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Data Analyst Portfolio | Samrith Uppala</title><style>body{font:16px system-ui;background:#f4f6fa;color:#162b40;max-width:1000px;margin:40px auto;padding:24px}section{background:white;padding:28px;border-radius:14px;margin:24px 0}h1{font-size:36px}.row{display:flex;align-items:center;gap:12px;margin:14px 0}.row b{width:100px}.bar{height:22px;background:#148579}small{color:#526477}</style><h1>Business performance analytics</h1><p>Durga Samrith Uppala | SQL • Python • KPI reporting</p><p><strong>Synthetic demonstration data.</strong> These case studies demonstrate analysis methods; results are not real company outcomes.</p>'''
html += '<section><h2>Retail performance</h2><p>Net revenue by region (USD)</p>'+bars(retail[1], 'region','net_revenue')+'<small>Net revenue = gross sales − discounts − refunds. Contribution subtracts modeled product cost only.</small></section>'
html += '<section><h2>Distribution service levels</h2><p>On-time delivery by carrier (%)</p>'+bars(sla[0], 'carrier','on_time_pct')+'<small>On time = actual transit days ≤ promised transit days. OTIF additionally requires a complete shipment.</small></section></html>'
(ROOT/'index.html').write_text(html, encoding='utf-8')
worst=min(sla[0], key=lambda r:r['on_time_pct'])
(ROOT/'FINDINGS.md').write_text(f'''# Results from the reproducible demo

All data is synthetic, generated with seed 26. No employer or customer data is included.

## Retail
Analyzed 2,400 orders. Net revenue totals ${sql_net:,.2f}. Review regional contribution alongside revenue before prioritizing sales investment. The cost model retains fulfillment/product costs on refunded orders and excludes overhead, tax and shipping, so contribution is not net profit.

## Distribution
{worst['carrier']} has the lowest on-time rate ({worst['on_time_pct']:.2f}%). This pattern is deliberately embedded in the generator, not discovered evidence about an actual carrier. In a real investigation, compare lanes, service classes and sample sizes before attributing performance to a carrier or renegotiating contracts.

## Validation
Passed row-count, primary-key, refund-bound, transit-day, completion-flag, revenue-reconciliation and on-time reconciliation checks. No business impact is claimed.
''', encoding='utf-8')
print(f'PASS: 2 projects, 4800 synthetic records; net revenue ${sql_net:,.2f}; all reconciliation checks passed.')
