import duckdb,pandas as pd,pytest
from dataio import demo,FILES
from app import build

def test_grain_and_money(tmp_path):
 raw=demo(tmp_path/'raw',n=70);out=tmp_path/'out';m=build(raw,out)
 assert m['kpis']['orders']==70
 items=pd.read_csv(raw/FILES['items']);payments=pd.read_csv(raw/FILES['payments'])
 assert abs(m['kpis']['merchandise_brl']-items.price.sum())<.01
 assert abs(m['kpis']['payments_brl']-payments.payment_value.sum())<.01
 with duckdb.connect(str(out/'warehouse.duckdb')) as c:
  assert c.execute('select count(*)=count(distinct order_id) from fact_orders').fetchone()[0]

def test_missing_delivery_excluded(tmp_path):
 raw=demo(tmp_path/'raw',n=40);f=raw/FILES['orders'];df=pd.read_csv(f);df.loc[df.order_id=='o1','order_delivered_customer_date']=None;df.to_csv(f,index=False)
 assert build(raw,tmp_path/'out')['kpis']['eligible_deliveries']==37

def test_duplicate_order_rejected(tmp_path):
 raw=demo(tmp_path/'raw',n=5);f=raw/FILES['orders'];d=pd.read_csv(f);pd.concat([d,d.iloc[:1]]).to_csv(f,index=False)
 with pytest.raises(ValueError,match='duplicate'):build(raw,tmp_path/'out')

def test_duplicate_reviews_do_not_multiply(tmp_path):
 raw=demo(tmp_path/'raw',n=5);f=raw/FILES['reviews'];d=pd.read_csv(f);extra=d.iloc[:1].copy();extra['review_answer_timestamp']='2020-01-01';extra['review_score']=1;pd.concat([d,extra]).to_csv(f,index=False)
 build(raw,tmp_path/'out')
 with duckdb.connect(str(tmp_path/'out/warehouse.duckdb')) as c:
  assert c.execute("select review_score from fact_orders where order_id='o0'").fetchone()[0]==1
  assert c.execute('select count(*) from fact_orders').fetchone()[0]==5
