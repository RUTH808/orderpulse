"""OrderPulse CLI: deterministic local warehouse and decision report."""
import argparse, html, json, time
from pathlib import Path
import duckdb
import dataio
from reporting import report, table, save_json, environment

def build(raw,output):
    t=time.perf_counter();output=Path(output);output.mkdir(parents=True,exist_ok=True)
    frames=dataio.load(raw)
    for name,key in [('orders',['order_id']),('customers',['customer_id']),('sellers',['seller_id']),('products',['product_id']),('items',['order_id','order_item_id']),('payments',['order_id','payment_sequential'])]:
        if frames[name][key].isna().any().any() or frames[name].duplicated(key).any():raise ValueError(f'{name}: null or duplicate primary key; run MetricTrust first')
    con=duckdb.connect(str(output/'warehouse.duckdb'))
    try:
        for name,frame in frames.items():con.register(name,frame)
        con.execute(Path(__file__).with_name('warehouse.sql').read_text())
        q=lambda sql:con.execute(sql).df()
        k=q("SELECT COUNT(*) orders,COUNT(is_late) eligible_deliveries,SUM(CAST(is_late AS INT)) late_deliveries,ROUND(100*AVG(CAST(is_late AS INT)),2) late_pct,ROUND(SUM(merchandise_brl),2) merchandise_brl,ROUND(SUM(paid_brl),2) payments_brl,ROUND(100*AVG(CAST(order_status='canceled' AS INT)),2) canceled_pct FROM fact_orders").iloc[0].to_dict()
        monthly=q('SELECT * FROM monthly_kpis');sellers=q('SELECT * FROM seller_scorecard')
        states=q('SELECT customer_state,COUNT(*) orders,COUNT(is_late) delivery_denominator,ROUND(100*AVG(CAST(is_late AS INT)),2) late_pct,ROUND(AVG(review_score),2) review_score FROM fact_orders GROUP BY 1 ORDER BY orders DESC')
        review=q('SELECT is_late,COUNT(*) orders_with_review,ROUND(AVG(review_score),2) mean_review_score FROM fact_orders WHERE is_late IS NOT NULL AND review_score IS NOT NULL GROUP BY 1 ORDER BY 1')
        export=output/'exports';export.mkdir(exist_ok=True)
        for name in ['fact_orders','fact_items','fact_payments','dim_customer','dim_seller','dim_product','dim_date']:
            q('SELECT * FROM '+name).to_csv(export/(name+'.csv'),index=False)
        for name,frame in [('monthly_kpis',monthly),('seller_scorecard',sellers),('state_kpis',states)]:frame.to_csv(export/(name+'.csv'),index=False)
        metrics={'dataset':'synthetic demo' if (Path(raw)/'DEMO.txt').exists() else 'Olist public marketplace data','source_rows':{k:len(v) for k,v in frames.items()},'kpis':k,'build_seconds':time.perf_counter()-t,'environment':environment(),'source_manifest':dataio.manifest(raw)}
        save_json(output/'metrics.json',metrics)
        sections=[('Monthly delivery performance',table(monthly.to_dict('records'),monthly.columns)),('States to investigate',table(states.to_dict('records'),states.columns)),('Seller review queue: at least 30 eligible deliveries', '<p>Ranked by affected late-order count. Multi-seller orders appear once for each seller; seller totals are not additive. Delays are order-level associations, not causal attribution.</p>'+table(sellers.head(40).to_dict('records'),sellers.columns)),('Delivery timing and reviews',table(review.to_dict('records'),review.columns)),('Definitions and exclusions','<p>Late = actual delivery date after promised date, among delivered orders with both timestamps. Cancellation denominator = all orders. Merchandise value excludes freight; neither value nor payments equal profit. Missing delivery timestamps are excluded, never treated as on time. Review score uses the latest recorded review per order. Dispatch = purchase to carrier handoff; transit = handoff to customer. Negative stage durations are excluded.</p>')]
        report(output/'dashboard.html','OrderPulse','Order-level metrics that survive multi-item and split-payment joins. '+metrics['dataset'],sections,{'Orders':f"{int(k['orders']):,}",'Late deliveries':f"{k['late_pct']:.2f}%",'Eligible deliveries':f"{int(k['eligible_deliveries']):,}"})
        text=f"# Findings\n\nDataset: {metrics['dataset']}.\n\n- Analyzed {int(k['orders']):,} orders; {int(k['eligible_deliveries']):,} have evaluable delivery dates.\n- Late-delivery share: {k['late_pct']:.2f}%; cancellations: {k['canceled_pct']:.2f}% of all orders.\n- Investigate high-volume sellers in exports/seller_scorecard.csv, checking dispatch and transit stages separately.\n- Compare review scores by delivery status as an association, not a causal effect.\n- Audit incomplete boundary months before interpreting growth. Historical Olist data do not represent current business performance.\n"
        (output/'FINDINGS.md').write_text(text)
        return metrics
    finally:con.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['demo','download','build']);p.add_argument('--raw',default='data/raw');p.add_argument('--output',default='results');a=p.parse_args()
    if a.command=='download':dataio.fetch(a.raw);return
    raw=dataio.demo(a.raw) if a.command=='demo' else Path(a.raw)
    print(json.dumps(build(raw,a.output),indent=2))
if __name__=='__main__':main()
