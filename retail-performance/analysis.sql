SELECT substr(order_date,1,7) AS month, COUNT(*) AS orders,
 ROUND(SUM(gross_sales-discount-refunds),2) AS net_revenue,
 ROUND(SUM(gross_sales-discount-refunds-cost),2) AS contribution,
 ROUND(SUM(gross_sales-discount-refunds)/COUNT(*),2) AS average_order_value
FROM orders GROUP BY month ORDER BY month;

SELECT region, COUNT(*) AS orders,
 ROUND(SUM(gross_sales-discount-refunds),2) AS net_revenue,
 ROUND(SUM(gross_sales-discount-refunds-cost),2) AS contribution
FROM orders GROUP BY region ORDER BY net_revenue DESC;

WITH customer_orders AS (
 SELECT customer_id, COUNT(*) AS orders FROM orders GROUP BY customer_id
)
SELECT COUNT(*) AS customers, SUM(orders>1) AS repeat_customers,
 ROUND(100.0*SUM(orders>1)/COUNT(*),2) AS repeat_customer_pct FROM customer_orders;
