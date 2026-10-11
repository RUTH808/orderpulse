# Power BI Desktop integration

The executed dashboard is `results/dashboard.html`. This folder contains Power Query/DAX authoring templates, not a prebuilt or verified PBIX. Power BI Desktop is not available in the build environment; validate these templates there before claiming a deployed Power BI report.

1. Run the Python pipeline on demo or Olist data.
2. In Power BI Desktop (Windows), Get Data > Text/CSV and import the generated exports (OrderPulse) or quality_summary.csv (MetricTrust).
3. For OrderPulse use `load_orders.pq` in a blank query after adding the ExportFolder parameter. Name the query fact_orders. Create a one-to-many, single-direction relationship from dim_customer[customer_id] to fact_orders[customer_id]. Relate dim_date[date] to fact_orders[purchase_date]. Keep order-level measures on fact_orders; do not create an ambiguous direct relationship between items and payments. Use the exported seller_scorecard separately for seller analysis; its seller-order grain is non-additive across sellers.
4. Paste each named expression from measures.dax as a separate measure. Set percentage display formats. Compare counts and currency totals with results/metrics.json before publishing.
5. Suggested report pages: executive KPIs, delivery trends, seller investigations (OrderPulse); rule pass rates, blocking errors, reconciliation exceptions (MetricTrust). Add month/state slicers where the grain supports them. Publish and configure refresh only after validating local relationships, credentials, and service licensing.
