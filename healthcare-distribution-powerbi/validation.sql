-- Grain: one fulfilled order / shipment. Monetary values are USD.
SELECT COUNT(*) Orders,
 ROUND(SUM(GrossSales-Discount-Refund),2) NetRevenue,
 ROUND(SUM(GrossSales-Discount-Refund-COGS-Freight-Penalty-Expedite),2) Contribution,
 ROUND(SUM(Penalty+Expedite),2) ServiceFailureCost,
 AVG(1.0*OnTime*InFull) OTIF
FROM FactOrders;

SELECT c.Carrier, COUNT(*) Orders, AVG(1.0*f.OnTime*f.InFull) OTIF,
 ROUND(SUM(f.Penalty+f.Expedite),2) ServiceFailureCost
FROM FactOrders f JOIN DimCarrier c ON c.CarrierKey=f.CarrierKey
GROUP BY c.Carrier ORDER BY ServiceFailureCost DESC;

SELECT d.YearMonth, ROUND(SUM(f.GrossSales-f.Discount-f.Refund),2) NetRevenue,
 ROUND(SUM(f.GrossSales-f.Discount-f.Refund-f.COGS-f.Freight-f.Penalty-f.Expedite),2) Contribution
FROM FactOrders f JOIN DimDate d ON d.Date=f.OrderDate
GROUP BY d.YearMonth ORDER BY d.YearMonth;

SELECT c.Region, COUNT(*) Orders,
 ROUND(SUM(f.GrossSales-f.Discount-f.Refund),2) NetRevenue,
 ROUND(SUM(f.Penalty+f.Expedite),2) ServiceFailureCost
FROM FactOrders f JOIN DimCustomer c ON c.CustomerKey=f.CustomerKey
GROUP BY c.Region ORDER BY ServiceFailureCost DESC;
