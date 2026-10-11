-- One row per order in fact_orders; each child source is aggregated BEFORE joining.
CREATE OR REPLACE TABLE dim_customer AS SELECT customer_id, customer_unique_id, customer_state FROM customers;
CREATE OR REPLACE TABLE dim_seller AS SELECT seller_id, seller_state FROM sellers;
CREATE OR REPLACE TABLE dim_product AS SELECT product_id, product_category_name FROM products;
CREATE OR REPLACE TABLE fact_items AS SELECT order_id, order_item_id, product_id, seller_id,
 CAST(price AS DECIMAL(18,2)) AS price_brl, CAST(freight_value AS DECIMAL(18,2)) AS freight_brl FROM items;
CREATE OR REPLACE TABLE fact_payments AS SELECT order_id, payment_sequential, payment_type,
 CAST(payment_value AS DECIMAL(18,2)) AS paid_brl FROM payments;
CREATE OR REPLACE TABLE fact_orders AS
WITH item_totals AS (SELECT order_id,SUM(price_brl) merchandise_brl,SUM(freight_brl) freight_brl,COUNT(*) item_count FROM fact_items GROUP BY order_id),
 payment_totals AS (SELECT order_id,SUM(paid_brl) paid_brl FROM fact_payments GROUP BY order_id),
 latest_review AS (SELECT order_id,CAST(review_score AS INT) review_score FROM reviews
 QUALIFY ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY TRY_CAST(review_answer_timestamp AS TIMESTAMP) DESC, review_id DESC)=1)
SELECT o.order_id,o.customer_id,c.customer_state,o.order_status,
 TRY_CAST(o.order_purchase_timestamp AS TIMESTAMP) purchased_at,
 TRY_CAST(o.order_delivered_carrier_date AS TIMESTAMP) carrier_at,
 TRY_CAST(o.order_delivered_customer_date AS TIMESTAMP) delivered_at,
 TRY_CAST(o.order_estimated_delivery_date AS TIMESTAMP) estimated_at,
 t.merchandise_brl,t.freight_brl,t.item_count,p.paid_brl,r.review_score,
 CASE WHEN o.order_status='delivered' AND TRY_CAST(o.order_delivered_customer_date AS TIMESTAMP) IS NOT NULL AND TRY_CAST(o.order_estimated_delivery_date AS TIMESTAMP) IS NOT NULL
 THEN CAST(o.order_delivered_customer_date AS DATE)>CAST(o.order_estimated_delivery_date AS DATE) END AS is_late,
 CASE WHEN TRY_CAST(o.order_delivered_carrier_date AS TIMESTAMP)>=TRY_CAST(o.order_purchase_timestamp AS TIMESTAMP)
 THEN date_diff('second',TRY_CAST(o.order_purchase_timestamp AS TIMESTAMP),TRY_CAST(o.order_delivered_carrier_date AS TIMESTAMP))/86400.0 END dispatch_days,
 CASE WHEN TRY_CAST(o.order_delivered_customer_date AS TIMESTAMP)>=TRY_CAST(o.order_delivered_carrier_date AS TIMESTAMP)
 THEN date_diff('second',TRY_CAST(o.order_delivered_carrier_date AS TIMESTAMP),TRY_CAST(o.order_delivered_customer_date AS TIMESTAMP))/86400.0 END transit_days
FROM orders o LEFT JOIN dim_customer c USING(customer_id) LEFT JOIN item_totals t USING(order_id)
LEFT JOIN payment_totals p USING(order_id) LEFT JOIN latest_review r USING(order_id);
CREATE OR REPLACE TABLE dim_date AS SELECT DISTINCT CAST(purchased_at AS DATE) date, date_part('year',purchased_at) year_number, date_part('month',purchased_at) month_number FROM fact_orders;
CREATE OR REPLACE VIEW monthly_kpis AS SELECT strftime(purchased_at,'%Y-%m') AS month,COUNT(*) orders,
 COUNT(is_late) delivery_denominator,ROUND(100*AVG(CAST(is_late AS INT)),2) late_pct,
 ROUND(SUM(merchandise_brl),2) merchandise_brl FROM fact_orders GROUP BY 1 ORDER BY 1;
CREATE OR REPLACE VIEW seller_scorecard AS
WITH seller_orders AS (SELECT DISTINCT seller_id,order_id FROM fact_items)
SELECT s.seller_id, d.seller_state, COUNT(*) orders,COUNT(o.is_late) delivery_denominator,
 SUM(CAST(o.is_late AS INT)) late_orders,ROUND(100*AVG(CAST(o.is_late AS INT)),2) late_pct,
 ROUND(AVG(o.review_score),2) review_score,ROUND(AVG(o.dispatch_days),2) dispatch_days,
 ROUND(AVG(o.transit_days),2) transit_days
FROM seller_orders s JOIN fact_orders o USING(order_id) LEFT JOIN dim_seller d USING(seller_id)
GROUP BY 1,2 HAVING COUNT(o.is_late)>=30 ORDER BY late_orders DESC,seller_id;
