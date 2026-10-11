"""Load Olist CSVs, or generate clearly labelled deterministic demo fixtures."""
from pathlib import Path
import hashlib, json, random, zipfile
import pandas as pd
from reporting import download
FILES={'orders':'olist_orders_dataset.csv','items':'olist_order_items_dataset.csv','payments':'olist_order_payments_dataset.csv','reviews':'olist_order_reviews_dataset.csv','customers':'olist_customers_dataset.csv','products':'olist_products_dataset.csv','sellers':'olist_sellers_dataset.csv'}

def load(raw):
    raw=Path(raw)
    return {k:pd.read_csv(raw/v,keep_default_na=False).replace('',None) for k,v in FILES.items()}

def fetch(raw):
    raw=Path(raw);raw.mkdir(parents=True,exist_ok=True)
    zpath=download('https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce',raw/'olist.zip')
    with zipfile.ZipFile(zpath) as z:
        for name in FILES.values():
            (raw/name).write_bytes(z.read(name))
    return raw

def manifest(raw):
    raw=Path(raw)
    return {name:{'sha256':hashlib.sha256((raw/file).read_bytes()).hexdigest(),'bytes':(raw/file).stat().st_size} for name,file in FILES.items()}

def demo(raw,n=500,seed=42):
    raw=Path(raw);raw.mkdir(parents=True,exist_ok=True);rng=random.Random(seed)
    data={k:[] for k in FILES}
    for j in range(20):
        data['sellers'].append(dict(seller_id=f's{j}',seller_state=['SP','RJ','MG'][j%3]))
        data['products'].append(dict(product_id=f'p{j}',product_category_name=['housewares','electronics','fashion'][j%3]))
    for i in range(n):
        start=pd.Timestamp('2018-01-01')+pd.Timedelta(days=i%180)
        dispatch=start+pd.Timedelta(days=rng.randint(1,5))
        delivery=dispatch+pd.Timedelta(days=rng.randint(2,18))
        status='canceled' if i%31==0 else 'delivered'
        data['customers'].append(dict(customer_id=f'c{i}',customer_unique_id=f'u{i//2}',customer_state=['SP','RJ','MG'][i%3]))
        data['orders'].append(dict(order_id=f'o{i}',customer_id=f'c{i}',order_status=status,order_purchase_timestamp=str(start),order_approved_at=str(start),order_delivered_carrier_date=str(dispatch) if status=='delivered' else None,order_delivered_customer_date=str(delivery) if status=='delivered' else None,order_estimated_delivery_date=str(start+pd.Timedelta(days=15))))
        amount=0
        for j in range(1,1+rng.randint(1,3)):
            price=rng.randint(2000,30000)/100;freight=rng.randint(500,2500)/100;amount+=price+freight
            data['items'].append(dict(order_id=f'o{i}',order_item_id=j,product_id=f'p{(i+j)%20}',seller_id=f's{(i+j)%20}',price=price,freight_value=freight,shipping_limit_date=str(start+pd.Timedelta(days=6))))
        pieces=2 if i%7==0 else 1
        for j in range(pieces):data['payments'].append(dict(order_id=f'o{i}',payment_sequential=j+1,payment_type='credit_card',payment_value=round(amount/pieces,2),payment_installments=1))
        data['reviews'].append(dict(review_id=f'r{i}',order_id=f'o{i}',review_score=2 if delivery>start+pd.Timedelta(days=15) else 5,review_answer_timestamp=str(delivery),review_creation_date=str(delivery)))
    for k,rows in data.items():pd.DataFrame(rows).to_csv(raw/FILES[k],index=False)
    (raw/'DEMO.txt').write_text('Synthetic fixture; not Olist observations. Seed 42.\n')
    return raw
