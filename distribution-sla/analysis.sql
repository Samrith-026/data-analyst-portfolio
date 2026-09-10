SELECT carrier, COUNT(*) AS shipments,
 ROUND(100.0*SUM(actual_days<=promised_days)/COUNT(*),2) AS on_time_pct,
 ROUND(100.0*SUM(actual_days<=promised_days AND complete=1)/COUNT(*),2) AS otif_pct,
 ROUND(AVG(MAX(actual_days-promised_days,0)),2) AS avg_delay_days_all_shipments
FROM shipments GROUP BY carrier ORDER BY on_time_pct DESC;

SELECT month, COUNT(*) AS shipments,
 ROUND(100.0*SUM(actual_days<=promised_days AND complete=1)/COUNT(*),2) AS otif_pct
FROM shipments GROUP BY month ORDER BY month;
