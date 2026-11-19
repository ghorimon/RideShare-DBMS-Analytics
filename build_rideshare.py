from pathlib import Path
from datetime import datetime,timedelta
from collections import defaultdict
import random,json,math,zipfile
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN,MSO_ANCHOR
from pptx.oxml.xmlchemy import OxmlElement
import nbformat as nbf

ROOT=Path(__file__).resolve().parent; OUT=ROOT.parent
random.seed(261119); np.random.seed(261119)
# Reference data
zones=[{'zone_id':i,'zone_name':n,'city':'Bengaluru'} for i,n in enumerate(['Whitefield','Indiranagar','Koramangala','Electronic City','HSR Layout','MG Road','Hebbal','Jayanagar'],1)]
vehicle_types=[{'vehicle_type_id':1,'type_name':'Mini','base_fare':45,'per_km_rate':12,'per_min_rate':1.5},{'vehicle_type_id':2,'type_name':'Sedan','base_fare':65,'per_km_rate':15,'per_min_rate':1.8},{'vehicle_type_id':3,'type_name':'SUV','base_fare':90,'per_km_rate':19,'per_min_rate':2.2},{'vehicle_type_id':4,'type_name':'Auto','base_fare':30,'per_km_rate':10,'per_min_rate':1.2}]
first=['Aarav','Ishita','Kabir','Meera','Rohan','Ananya','Vihaan','Diya','Arjun','Sara','Dev','Nisha','Reyansh','Tara','Aditya','Maya','Neil','Kavya','Ishan','Riya']
last=['Sharma','Iyer','Mukherjee','Das','Patel','Nair','Mehta','Rao','Kapoor','Banerjee','Menon','Gupta','Sen','Bose','Verma','Roy']
def person(): return random.choice(first)+' '+random.choice(last)
riders=[{'rider_id':i,'rider_name':person(),'email':f'rider{i:04}@demo.invalid','signup_date':datetime(2024,1,1)+timedelta(days=random.randint(0,950)),'home_zone_id':random.randint(1,8)} for i in range(1,401)]
drivers=[{'driver_id':i,'driver_name':person(),'license_no':f'DEMO-{i:05}','join_date':datetime(2023,1,1)+timedelta(days=random.randint(0,1000)),'is_active':int(random.random()>.06)} for i in range(1,81)]
vehicles=[]
for i in range(1,101):
    vehicles.append({'vehicle_id':i,'driver_id':i if i<=80 else random.randint(1,80),'vehicle_type_id':random.randint(1,4),'registration_no':f'KA-DEMO-{i:04}','model':random.choice(['Swift','Dzire','Baleno','Amaze','Nexon','Ertiga','WagonR'])})
vt={x['vehicle_type_id']:x for x in vehicle_types}; trip_status=['Completed','Cancelled','Driver Cancelled','Rider Cancelled']; channels=['App','Web']
trips=[]; fares=[]; payments=[]; ratings=[]; histories=[]; gpsdocs=[]
start=datetime(2026,1,1); end=datetime(2026,10,31,23,59); span=int((end-start).total_seconds()/60)
for tid in range(10001,11201):
    created=start+timedelta(minutes=random.randint(0,span)); rider=random.choice(riders); driver=random.choice(drivers); vehicle=random.choice([v for v in vehicles if v['driver_id']==driver['driver_id']]); vtrow=vt[vehicle['vehicle_type_id']]
    pickup=random.randint(1,8); drop=random.choice([z for z in range(1,9) if z!=pickup]); km=round(random.uniform(1.2,28),2); mins=max(5,int(km*random.uniform(2.2,4.2))); status=random.choices(trip_status,[.82,.07,.07,.04])[0]
    surge=random.choice([1,1,1,1.2,1.4,1.6]); fare=round((vtrow['base_fare']+km*vtrow['per_km_rate']+mins*vtrow['per_min_rate'])*surge,2)
    completed=status=='Completed'; pay_status=random.choice(['Paid','Paid','Paid','Refunded']) if completed else random.choice(['Not Charged','Refunded'])
    trip={'trip_id':tid,'rider_id':rider['rider_id'],'driver_id':driver['driver_id'],'vehicle_id':vehicle['vehicle_id'],'pickup_zone_id':pickup,'drop_zone_id':drop,'requested_at':created,'pickup_at':created+timedelta(minutes=random.randint(2,14)) if completed else None,'dropoff_at':created+timedelta(minutes=random.randint(15,mins+20)) if completed else None,'trip_status':status,'booking_channel':random.choice(channels)}
    trips.append(trip); fares.append({'trip_id':tid,'distance_km':km,'duration_mins':mins if completed else 0,'base_fare':vtrow['base_fare'],'surge_multiplier':surge,'total_fare':fare if completed else 0.0}); payments.append({'payment_id':tid-10000,'trip_id':tid,'payment_method':random.choice(['UPI','Card','Wallet','Cash']),'payment_status':pay_status,'paid_at':created+timedelta(minutes=mins+5) if pay_status=='Paid' else None,'amount':fare if pay_status=='Paid' else 0.0})
    if completed and random.random()<.88: ratings.append({'rating_id':len(ratings)+1,'trip_id':tid,'rider_id':rider['rider_id'],'driver_id':driver['driver_id'],'rating':random.choices([1,2,3,4,5],[.02,.04,.10,.32,.52])[0],'feedback':random.choice(['Smooth ride','On time','Clean vehicle','Route could improve','Good experience'])})
    if status!='Completed': histories.append({'trip_id':tid,'old_status':'Requested','new_status':status,'changed_at':created+timedelta(minutes=random.randint(1,10)),'changed_by':'SYSTEM'})
    # Mongo GPS trace: ordered synthetic coordinate samples around Bengaluru (not actual trips)
    lat0=12.90+random.random()*.16; lon0=77.50+random.random()*.20; pts=[]
    for j in range(5): pts.append({'sequence':j+1,'timestamp':(created+timedelta(minutes=j*max(1,mins//4))).isoformat(),'coordinates':{'type':'Point','coordinates':[round(lon0+j*.002+random.uniform(-.001,.001),6),round(lat0+j*.001+random.uniform(-.001,.001),6)]},'event':['START','MOVING','MOVING','MOVING','END'][j]})
    gpsdocs.append({'trip_id':tid,'rider_id':rider['rider_id'],'driver_id':driver['driver_id'],'trip_status':status,'pickup_zone_id':pickup,'drop_zone_id':drop,'requested_at':created.isoformat(),'distance_km':km,'gps_points':pts})
# Force known open/requested demo trip and trigger status update
trips[-1]['trip_status']='Requested'
T=pd.DataFrame(trips).merge(pd.DataFrame(fares),on='trip_id').merge(pd.DataFrame(payments),on='trip_id').merge(pd.DataFrame(drivers)[['driver_id','driver_name']],on='driver_id').merge(pd.DataFrame(zones).rename(columns={'zone_id':'pickup_zone_id','zone_name':'pickup_zone'}),on='pickup_zone_id').merge(pd.DataFrame(zones).rename(columns={'zone_id':'drop_zone_id','zone_name':'drop_zone'}),on='drop_zone_id')
T['month']=pd.to_datetime(T.requested_at).dt.strftime('%Y-%m'); completed=T[T.trip_status=='Completed']; monthly=T.groupby('month').size().reset_index(name='trips'); zone_stats=T.groupby('pickup_zone').size().sort_values(ascending=False); driver_stats=completed.groupby('driver_name').agg(trips=('trip_id','count'),earnings=('total_fare','sum')).sort_values('trips',ascending=False).head(5); cancel_rate=float((T.trip_status!='Completed').mean()*100); avg_fare=float(completed.total_fare.mean()); avg_rating=float(pd.DataFrame(ratings).rating.mean()); avg_km=float(completed.distance_km.mean())
# SQL
schema='''CREATE DATABASE IF NOT EXISTS rideshare; USE rideshare;
CREATE TABLE zones(zone_id INT PRIMARY KEY, zone_name VARCHAR(80) NOT NULL UNIQUE, city VARCHAR(80) NOT NULL);
CREATE TABLE riders(rider_id INT PRIMARY KEY, rider_name VARCHAR(100) NOT NULL, email VARCHAR(150) UNIQUE NOT NULL, signup_date DATE NOT NULL, home_zone_id INT NOT NULL, FOREIGN KEY(home_zone_id) REFERENCES zones(zone_id));
CREATE TABLE drivers(driver_id INT PRIMARY KEY, driver_name VARCHAR(100) NOT NULL, license_no VARCHAR(30) UNIQUE NOT NULL, join_date DATE NOT NULL, is_active BOOLEAN NOT NULL, INDEX idx_driver_active(is_active));
CREATE TABLE vehicle_types(vehicle_type_id INT PRIMARY KEY, type_name VARCHAR(30) UNIQUE NOT NULL, base_fare DECIMAL(8,2) NOT NULL CHECK(base_fare>=0), per_km_rate DECIMAL(8,2) NOT NULL, per_min_rate DECIMAL(8,2) NOT NULL);
CREATE TABLE vehicles(vehicle_id INT PRIMARY KEY, driver_id INT NOT NULL, vehicle_type_id INT NOT NULL, registration_no VARCHAR(30) UNIQUE NOT NULL, model VARCHAR(50), FOREIGN KEY(driver_id) REFERENCES drivers(driver_id), FOREIGN KEY(vehicle_type_id) REFERENCES vehicle_types(vehicle_type_id));
CREATE TABLE trips(trip_id INT PRIMARY KEY, rider_id INT NOT NULL, driver_id INT NOT NULL, vehicle_id INT NOT NULL, pickup_zone_id INT NOT NULL, drop_zone_id INT NOT NULL, requested_at DATETIME NOT NULL, pickup_at DATETIME NULL, dropoff_at DATETIME NULL, trip_status ENUM('Requested','Completed','Cancelled','Driver Cancelled','Rider Cancelled') NOT NULL, booking_channel ENUM('App','Web') NOT NULL, FOREIGN KEY(rider_id) REFERENCES riders(rider_id), FOREIGN KEY(driver_id) REFERENCES drivers(driver_id), FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id), FOREIGN KEY(pickup_zone_id) REFERENCES zones(zone_id), FOREIGN KEY(drop_zone_id) REFERENCES zones(zone_id), INDEX idx_trip_time(requested_at), INDEX idx_trip_status(trip_status));
CREATE TABLE fare_details(trip_id INT PRIMARY KEY, distance_km DECIMAL(7,2) NOT NULL, duration_mins INT NOT NULL, base_fare DECIMAL(8,2) NOT NULL, surge_multiplier DECIMAL(4,2) NOT NULL, total_fare DECIMAL(10,2) NOT NULL, FOREIGN KEY(trip_id) REFERENCES trips(trip_id));
CREATE TABLE payments(payment_id INT PRIMARY KEY, trip_id INT NOT NULL UNIQUE, payment_method ENUM('UPI','Card','Wallet','Cash') NOT NULL, payment_status ENUM('Paid','Refunded','Not Charged') NOT NULL, paid_at DATETIME NULL, amount DECIMAL(10,2) NOT NULL, FOREIGN KEY(trip_id) REFERENCES trips(trip_id));
CREATE TABLE trip_ratings(rating_id INT PRIMARY KEY, trip_id INT NOT NULL UNIQUE, rider_id INT NOT NULL, driver_id INT NOT NULL, rating TINYINT NOT NULL CHECK(rating BETWEEN 1 AND 5), feedback VARCHAR(200), FOREIGN KEY(trip_id) REFERENCES trips(trip_id), FOREIGN KEY(rider_id) REFERENCES riders(rider_id), FOREIGN KEY(driver_id) REFERENCES drivers(driver_id));
CREATE TABLE trip_status_history(history_id INT AUTO_INCREMENT PRIMARY KEY, trip_id INT NOT NULL, old_status VARCHAR(30), new_status VARCHAR(30), changed_at DATETIME NOT NULL, changed_by VARCHAR(30), FOREIGN KEY(trip_id) REFERENCES trips(trip_id));
DELIMITER $$
CREATE TRIGGER trg_trip_status_audit AFTER UPDATE ON trips FOR EACH ROW BEGIN IF OLD.trip_status <> NEW.trip_status THEN INSERT INTO trip_status_history(trip_id,old_status,new_status,changed_at,changed_by) VALUES(NEW.trip_id,OLD.trip_status,NEW.trip_status,NOW(),'SYSTEM'); END IF; END$$
DELIMITER ;
CREATE OR REPLACE VIEW vw_trip_performance AS SELECT t.trip_id,t.trip_status,t.requested_at,z1.zone_name AS pickup_zone,z2.zone_name AS drop_zone,d.driver_name,f.distance_km,f.duration_mins,f.total_fare,p.payment_status FROM trips t JOIN zones z1 ON t.pickup_zone_id=z1.zone_id JOIN zones z2 ON t.drop_zone_id=z2.zone_id JOIN drivers d ON t.driver_id=d.driver_id JOIN fare_details f ON t.trip_id=f.trip_id JOIN payments p ON t.trip_id=p.trip_id;
'''
(ROOT/'sql/schema.sql').write_text(schema)
def q(v):
    if v is None:return 'NULL'
    if isinstance(v,(datetime,pd.Timestamp)):return "'"+v.strftime('%Y-%m-%d %H:%M:%S')+"'"
    if isinstance(v,(int,np.integer)):return str(int(v))
    if isinstance(v,(float,np.floating)):return str(round(float(v),3))
    return "'"+str(v).replace("'","\\'")+"'"
def insert(table,rows,cols):
    out=[]
    for i in range(0,len(rows),200):
        out.append(f"INSERT INTO {table} ({','.join(cols)}) VALUES\n"+',\n'.join('('+','.join(q(r[c]) for c in cols)+')' for r in rows[i:i+200])+';')
    return '\n'.join(out)
seed=['USE rideshare;',insert('zones',zones,['zone_id','zone_name','city']),insert('riders',riders,['rider_id','rider_name','email','signup_date','home_zone_id']),insert('drivers',drivers,['driver_id','driver_name','license_no','join_date','is_active']),insert('vehicle_types',vehicle_types,['vehicle_type_id','type_name','base_fare','per_km_rate','per_min_rate']),insert('vehicles',vehicles,['vehicle_id','driver_id','vehicle_type_id','registration_no','model']),insert('trips',trips,['trip_id','rider_id','driver_id','vehicle_id','pickup_zone_id','drop_zone_id','requested_at','pickup_at','dropoff_at','trip_status','booking_channel']),insert('fare_details',fares,['trip_id','distance_km','duration_mins','base_fare','surge_multiplier','total_fare']),insert('payments',payments,['payment_id','trip_id','payment_method','payment_status','paid_at','amount']),insert('trip_ratings',ratings,['rating_id','trip_id','rider_id','driver_id','rating','feedback'])]
(ROOT/'sql/data.sql').write_text('-- Synthetic reproducible dataset.\n'+'\n'.join(seed))
queries='''USE rideshare;
-- 1. Trips by month
SELECT DATE_FORMAT(requested_at,'%Y-%m') month,COUNT(*) trips FROM trips GROUP BY month ORDER BY month;
-- 2. Trips by pickup zone
SELECT z.zone_name,COUNT(*) trips FROM trips t JOIN zones z ON t.pickup_zone_id=z.zone_id GROUP BY z.zone_id,z.zone_name ORDER BY trips DESC;
-- 3. Average fare by vehicle type
SELECT vt.type_name,ROUND(AVG(f.total_fare),2) avg_fare,COUNT(*) completed_trips FROM fare_details f JOIN trips t ON f.trip_id=t.trip_id JOIN vehicles v ON t.vehicle_id=v.vehicle_id JOIN vehicle_types vt ON v.vehicle_type_id=vt.vehicle_type_id WHERE t.trip_status='Completed' GROUP BY vt.type_name;
-- 4. Driver earnings and trip count
SELECT d.driver_name,COUNT(*) trips,SUM(f.total_fare) earnings,ROUND(AVG(r.rating),2) avg_rating FROM drivers d JOIN trips t ON d.driver_id=t.driver_id JOIN fare_details f ON f.trip_id=t.trip_id LEFT JOIN trip_ratings r ON r.trip_id=t.trip_id WHERE t.trip_status='Completed' GROUP BY d.driver_id,d.driver_name ORDER BY earnings DESC LIMIT 10;
-- 5. Cancellation rate by zone
SELECT z.zone_name,COUNT(*) requests,SUM(t.trip_status<>'Completed') cancelled,ROUND(100*AVG(t.trip_status<>'Completed'),1) cancellation_pct FROM trips t JOIN zones z ON t.pickup_zone_id=z.zone_id GROUP BY z.zone_id,z.zone_name ORDER BY cancellation_pct DESC;
-- 6. Hourly demand
SELECT HOUR(requested_at) request_hour,COUNT(*) trip_requests FROM trips GROUP BY HOUR(requested_at) ORDER BY request_hour;
-- Demo: run once; trip 11200 is seeded as Requested
-- UPDATE trips SET trip_status='Cancelled' WHERE trip_id=11200;
-- SELECT * FROM trip_status_history WHERE trip_id=11200;
'''
(ROOT/'sql/queries.sql').write_text(queries)
# Mongo JSONL
with (ROOT/'mongodb/gps_trip_points.jsonl').open('w') as f:
    for d in gpsdocs:f.write(json.dumps(d)+'\n')
mjs='''use('rideshare');
db.gps_trip_points.createIndex({trip_id:1},{unique:true});
db.gps_trip_points.createIndex({driver_id:1,requested_at:-1});
db.gps_trip_points.createIndex({'gps_points.coordinates':'2dsphere'});
// CRUD examples
db.gps_trip_points.findOne({trip_id:10001});
db.gps_trip_points.updateOne({trip_id:10001},{$set:{reviewed:true}});
// Insert/delete are shown against a disposable demo record:
// db.gps_trip_points.insertOne({trip_id:99999,driver_id:1,gps_points:[]});
// db.gps_trip_points.deleteOne({trip_id:99999});
// Pipeline 1: trip counts by pickup zone and status
db.gps_trip_points.aggregate([{$group:{_id:{zone:'$pickup_zone_id',status:'$trip_status'},trips:{$sum:1}}},{$sort:{trips:-1}}]);
// Pipeline 2: average distance by driver
db.gps_trip_points.aggregate([{$group:{_id:'$driver_id',trips:{$sum:1},avg_distance_km:{$avg:'$distance_km'}}},{$sort:{trips:-1}},{$limit:10}]);
'''
(ROOT/'mongodb/rideshare_mongodb.js').write_text(mjs)
# Metrics and charts
monthly.to_csv(ROOT/'assets/monthly_trips.csv',index=False)
fig,ax=plt.subplots(figsize=(7,3.5));ax.plot(monthly.month,monthly.trips,marker='o');ax.set_title('Monthly Trip Requests');ax.set_xlabel('Month');ax.set_ylabel('Trips');ax.tick_params(axis='x',rotation=45);ax.grid(axis='y',alpha=.25);fig.tight_layout();fig.savefig(ROOT/'assets/monthly_trips.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(7,3.5));zone_stats.plot(kind='bar',ax=ax);ax.set_title('Trip Requests by Pickup Zone');ax.set_xlabel('Pickup zone');ax.set_ylabel('Trips');fig.tight_layout();fig.savefig(ROOT/'assets/trips_by_zone.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,2.8));ax.axis('off');ax.set_title('Driver performance · top 5 by completed trips',loc='left',fontweight='bold');tab=ax.table(cellText=[[n,int(r.trips),f'₹{r.earnings:,.0f}'] for n,r in driver_stats.iterrows()],colLabels=['Driver','Trips','Fare value'],loc='center',cellLoc='center');tab.auto_set_font_size(False);tab.set_fontsize(8);tab.scale(1,1.5);fig.tight_layout();fig.savefig(ROOT/'assets/driver_performance.png',dpi=180);plt.close(fig)
# ER diagram
fig,ax=plt.subplots(figsize=(12,7));ax.set_xlim(0,12);ax.set_ylim(0,7);ax.axis('off')
boxes={'zones':(.3,5.1,2,1,'ZONES','PK zone_id\nzone_name'),'riders':(3,5.1,2.2,1,'RIDERS','PK rider_id\nFK home_zone_id'),'drivers':(6,5.1,2.2,1,'DRIVERS','PK driver_id\nlicense_no'),'vehicles':(9,5.1,2.5,1,'VEHICLES','PK vehicle_id\nFK driver_id, vehicle_type_id'),'vehicle_types':(9,2.9,2.5,1,'VEHICLE TYPES','PK vehicle_type_id\nrate attributes'),'trips':(4.5,2.9,2.5,1.3,'TRIPS','PK trip_id\nFK rider, driver, vehicle, zones'),'fares':(.7,2.9,2.5,1,'FARE DETAILS','PK/FK trip_id\ndistance, duration, fare'),'payments':(4.5,.7,2.5,1,'PAYMENTS','PK payment_id\nFK trip_id'),'ratings':(8,.7,2.5,1,'TRIP RATINGS','PK rating_id\nFK trip, rider, driver')}
for x,y,w,h,t,b in boxes.values():
 ax.add_patch(plt.Rectangle((x,y),w,h,facecolor='#EAF3FA',edgecolor='#0967A5',lw=1.5));ax.text(x+w/2,y+h-.22,t,ha='center',weight='bold',color='#075B94',fontsize=8);ax.text(x+w/2,y+.32,b,ha='center',fontsize=7)
for a,b in [((2.3,5.5),(3,5.5)),((8.2,5.5),(9,5.5)),((10.2,5.1),(10.2,3.9)),((4.1,5.1),(5.1,4.2)),((7.1,5.1),(6.7,4.2)),((9,5.1),(6.8,4.2)),((4.5,3.5),(3.2,3.5)),((5.7,2.9),(5.7,1.7)),((7,2.9),(8.8,1.7))]:ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',color='#68798A'))
ax.set_title('RideShare relational model · normalised operational schema',fontsize=13,weight='bold',color='#075B94');fig.tight_layout();fig.savefig(ROOT/'assets/rideshare_erd.png',dpi=180);plt.close(fig)
# notebook
nb=nbf.v4.new_notebook();nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}}
nb.cells=[nbf.v4.new_markdown_cell('# RideShare — Python DB-API Analytics\nSynthetic Bengaluru ride-hailing dataset. Install `mysql-connector-python pandas matplotlib`. Set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD and MYSQL_DATABASE.'),nbf.v4.new_code_cell("import os, mysql.connector, pandas as pd, matplotlib.pyplot as plt\nconn=mysql.connector.connect(host=os.getenv('MYSQL_HOST','localhost'),user=os.getenv('MYSQL_USER','root'),password=os.getenv('MYSQL_PASSWORD',''),database=os.getenv('MYSQL_DATABASE','rideshare'))\ncur=conn.cursor()\nprint('Connected to RideShare')"),nbf.v4.new_code_cell("sql=\"SELECT DATE_FORMAT(requested_at,'%Y-%m') month, COUNT(*) trips FROM trips GROUP BY month ORDER BY month\"\ncur.execute(sql); df=pd.DataFrame(cur.fetchall(),columns=[c[0] for c in cur.description]); df.head()"),nbf.v4.new_code_cell("plt.figure(figsize=(9,4)); plt.plot(df.month,df.trips,marker='o'); plt.title('Monthly Trip Requests'); plt.xticks(rotation=45); plt.ylabel('Trips'); plt.tight_layout(); plt.show()"),nbf.v4.new_code_cell("sql=\"SELECT z.zone_name, COUNT(*) trips FROM trips t JOIN zones z ON t.pickup_zone_id=z.zone_id GROUP BY z.zone_id,z.zone_name ORDER BY trips DESC\"\ncur.execute(sql); zones_df=pd.DataFrame(cur.fetchall(),columns=[c[0] for c in cur.description]); zones_df"),nbf.v4.new_code_cell("plt.figure(figsize=(8,4)); plt.bar(zones_df.zone_name,zones_df.trips); plt.title('Trips by Pickup Zone'); plt.xticks(rotation=35); plt.tight_layout(); plt.show()"),nbf.v4.new_code_cell("cur.close(); conn.close(); print('Connection closed')")]
nbf.write(nb,ROOT/'notebooks/rideshare_analysis.ipynb')
# README
rows={k:len(v) for k,v in [('zones',zones),('riders',riders),('drivers',drivers),('vehicle_types',vehicle_types),('vehicles',vehicles),('trips',trips),('fare_details',fares),('payments',payments),('trip_ratings',ratings)]}
metrics={'synthetic_data':True,'seed':261119,'row_counts':rows,'total_rows':sum(rows.values()),'cancel_rate_pct':round(cancel_rate,1),'avg_completed_fare':round(avg_fare,2),'avg_rating':round(avg_rating,2),'avg_completed_distance_km':round(avg_km,2),'monthly_trips':monthly.to_dict('records'),'zone_trip_counts':zone_stats.to_dict()}
(ROOT/'metrics_snapshot.json').write_text(json.dumps(metrics,indent=2))
(ROOT/'README.md').write_text(f'''# RideShare — Cab Trip and Driver Performance Analytics\n\nProblem Statement 10 from the supplied DBMS assignment. MySQL 8+ relational database and MongoDB GPS event documents. All generated records are synthetic, use seed 261119, and do not represent a real ride-hailing operator.\n\n## Dataset\n- {rows['riders']} riders; {rows['drivers']} drivers; {rows['vehicles']} vehicles; {rows['trips']} trips; {rows['fare_details']} fare rows; {rows['payments']} payment rows; {rows['trip_ratings']} ratings.\n- Total relational seed rows: {sum(rows.values())}.\n- Date coverage: January–October 2026.\n\n## Files\n- `sql/schema.sql`: 10 tables, keys, constraints, indexes, audit trigger and performance view.\n- `sql/data.sql`: synthetic seed inserts.\n- `sql/queries.sql`: six analytics queries plus trigger demo.\n- `notebooks/rideshare_analysis.ipynb`: DB-API connection, SQL, Pandas and charts.\n- `mongodb/gps_trip_points.jsonl`: one GPS trace document per trip.\n- `mongodb/rideshare_mongodb.js`: indexes, CRUD and two aggregation pipelines.\n- `assets/`: ER diagram, charts and supporting data.\n- `speaker_script.md`: oral presentation notes.\n\n## Setup\n1. Run `mysql -u root -p < sql/schema.sql`.\n2. Load seed data: `mysql -u root -p rideshare < sql/data.sql`.\n3. Run SQL queries from `sql/queries.sql`. To demo trigger: `UPDATE trips SET trip_status='Cancelled' WHERE trip_id=11200;` then query `trip_status_history`.\n4. Install `pip install mysql-connector-python pandas matplotlib jupyterlab` and set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE before running notebook.\n5. Import MongoDB: `mongoimport --db rideshare --collection gps_trip_points --file mongodb/gps_trip_points.jsonl --type json`. Run `mongodb/rideshare_mongodb.js` in mongosh.\n\n## Normalisation\nThe relational design separates riders, drivers, vehicles, vehicle types, zones, trips, fare details, payments, ratings and trip status history. Examples: `driver_id → driver_name, license_no, join_date, is_active`; `trip_id → rider_id, driver_id, vehicle_id, requested_at, trip_status`; `vehicle_type_id → base_fare, per_km_rate, per_min_rate`. This prevents repeating driver, zone and pricing attributes on every trip.\n\nMetrics in the presentation are calculated from the supplied synthetic dataset. They are demonstrative, not actual platform KPIs.\n''')
# Speaker notes
(ROOT/'speaker_script.md').write_text(f'''# RideShare — speaker notes\n\n**Slide 1:** RideShare is a cab trip and driver performance analytics database. It models ride requests, assignments, vehicle types, trip fares, payments and ratings.\n\n**Slide 2:** The relational model separates zones, riders, drivers, vehicles, vehicle types, trips, fare details, payments and ratings. Primary and foreign keys preserve relationships. Pricing attributes live in vehicle_types rather than being duplicated for every trip, supporting 3NF.\n\n**Slide 3:** The SQL schema includes constraints and indexes. The AFTER UPDATE trigger records trip status changes in trip_status_history. The vw_trip_performance view joins trips to zones, drivers, fare details and payments. The queries analyse demand, fare, driver earnings, ratings and cancellations.\n\n**Slide 4:** Python connects through MySQL Connector/Python DB-API, executes SQL through a cursor, loads rows into Pandas and plots monthly trip demand and pickup-zone demand. The generated sample has {len(trips):,} trips, a {cancel_rate:.1f}% non-completed trip share, and an average completed fare of ₹{avg_fare:.2f}. These are synthetic results, not industry benchmarks.\n\n**Slide 5:** MongoDB stores each trip's ordered GPS samples as an array of nested location documents. This suits event-like location traces. Indexes support trip lookup, driver timelines and geospatial queries. CRUD and aggregation examples are in the JS file.\n\n**Slide 6:** Key findings: {cancel_rate:.1f}% of requests were not completed in this synthetic sample; average completed fare was ₹{avg_fare:.2f}; average trip rating was {avg_rating:.2f}/5. The live demo shows the ER model, status trigger, SQL analytics, notebook charts and MongoDB GPS aggregations.\n''')
(ROOT/'submission_checklist.md').write_text('''# Submission checklist\n- [ ] Verify student name, registration number, guide and date on slide 1.\n- [ ] Run MySQL schema and data scripts.\n- [ ] Execute the six SQL queries and demonstrate the audit trigger.\n- [ ] Configure MySQL credentials and run all notebook cells.\n- [ ] Import JSONL into MongoDB and run indexes, CRUD and aggregation examples.\n- [ ] Add GitHub URL after uploading the project.\n- [ ] Rehearse the speaker notes.\n\nAll generated data is synthetic; do not describe it as real operator data.\n''')
# PPT fill original template
prs=Presentation(str(ROOT/'template_reference.pptx')); BLUE=RGBColor(7,91,148); DARK=RGBColor(31,51,68); MUTED=RGBColor(90,105,120)
def st(sh,text,size=12,bold=None,color=DARK,font='Aptos'):
 tf=sh.text_frame;tf.clear();tf.word_wrap=True;tf.margin_left=Pt(4);tf.margin_right=Pt(4);tf.margin_top=Pt(2);tf.margin_bottom=Pt(2)
 for i,line in enumerate(text.split('\n')):
  p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.space_after=Pt(2);p._p.get_or_add_pPr().append(OxmlElement('a:buNone'))
  for r in p.runs:r.font.name=font;r.font.size=Pt(size);r.font.bold=bold;r.font.color.rgb=color
def fill(tab,rows,fs=8):
 while len(tab.rows)<len(rows):tab._tbl.append(__import__('copy').deepcopy(tab._tbl.tr_lst[-1]))
 while len(tab.rows)>len(rows):tab._tbl.remove(tab._tbl.tr_lst[-1])
 for ri,row in enumerate(rows):
  for ci,val in enumerate(row):
   c=tab.cell(ri,ci);c.text=str(val);c.vertical_anchor=MSO_ANCHOR.MIDDLE
   for p in c.text_frame.paragraphs:
    for r in p.runs:r.font.name='Aptos';r.font.size=Pt(fs);r.font.bold=(ri==0);r.font.color.rgb=RGBColor(255,255,255) if ri==0 else DARK
   c.fill.solid();c.fill.fore_color.rgb=RGBColor(9,103,165) if ri==0 else RGBColor(234,243,250) if ri%2 else RGBColor(255,255,255)
def pic(slide,path,x,y,w,h):slide.shapes.add_picture(str(path),Inches(x),Inches(y),width=Inches(w),height=Inches(h))
# Slide 1
s=prs.slides[0];st(s.shapes[5],'RideShare',25,True,BLUE);st(s.shapes[6],'Problem statement no. 10   ·   Domain: Transport',11,color=MUTED);fill(s.shapes[7].table,[['#','Student name','Reg. no.','Part presented'],['1','Rimon Ghosh','26MSDSR060','Schema · SQL · Python · MongoDB']],9);st(s.shapes[8],'Individual project · Cab Trip and Driver Performance Analytics',9,color=MUTED);st(s.shapes[9],'Database: MySQL 8.0+  +  MongoDB',11);st(s.shapes[10],'Guide / Examiner: Om Prakash Chaurasia     Date: 19/11/2026',10);st(s.shapes[11],'GitHub: [Add repository URL after upload]',10)
# Slide 2
s=prs.slides[1];pic(s,ROOT/'assets/rideshare_erd.png',.55,2.45,6.35,3.9);fill(s.shapes[5].table,[['Table','Primary key','Foreign keys'],['zones','zone_id','—'],['riders','rider_id','home_zone_id'],['drivers','driver_id','—'],['vehicle_types','vehicle_type_id','—'],['vehicles','vehicle_id','driver_id, vehicle_type_id'],['trips','trip_id','rider, driver, vehicle, pickup/drop zones'],['fare_details','trip_id','trip_id'],['payments','payment_id','trip_id'],['trip_ratings','rating_id','trip_id, rider_id, driver_id'],['trip_status_history','history_id','trip_id']],6.5);sh=s.shapes[5];[setattr(r,'height',Inches(.235)) for r in sh.table.rows];st(s.shapes[8],'Functional dependency: driver_id → driver_name, license_no, join_date, is_active.\nHighest normal form: 3NF.\nRedundancy removed: driver, zone and vehicle pricing attributes are stored once in parent tables.',9)
# Slide 3
s=prs.slides[2];st(s.shapes[4],"CREATE TABLE trips (\n trip_id INT PRIMARY KEY,\n rider_id INT NOT NULL, driver_id INT NOT NULL,\n vehicle_id INT NOT NULL,\n requested_at DATETIME NOT NULL,\n trip_status ENUM('Requested','Completed','Cancelled'),\n FOREIGN KEY (rider_id) REFERENCES riders(rider_id),\n FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)\n);",8,font='Consolas');st(s.shapes[5],'Trigger: trg_trip_status_audit · AFTER UPDATE · logs every status change.\nView: vw_trip_performance · joins trip, zone, driver, fare and payment details.\nRows loaded: '+f'{sum(rows.values()):,} across 9 tables.',9);fill(s.shapes[7].table,[['Business question','SQL features','Result'],['Which zones generate demand?','JOIN · GROUP BY · COUNT','Rank pickup zones'],['What is the average fare by vehicle?','JOIN · AVG','Compare vehicle types'],['Which drivers earn most?','JOIN · SUM · GROUP BY','Rank driver earnings'],['Where are cancellations highest?','CASE · AVG · GROUP BY','Cancellation % by zone']],7);pic(s,ROOT/'assets/driver_performance.png',6.8,5.0,5.5,1.25)
# Slide 4
s=prs.slides[3];st(s.shapes[4],'import mysql.connector, pandas as pd\nconn = mysql.connector.connect(\n host="localhost", user="root",\n password="<from environment>",\n database="rideshare")\ncur = conn.cursor()\ncur.execute("SELECT ...")\ndf = pd.DataFrame(cur.fetchall())',9,font='Consolas');st(s.shapes[5],'DB-API runs SQL; Pandas structures results; Matplotlib visualises demand and zones.',9);pic(s,ROOT/'assets/monthly_trips.png',5.5,2.0,3.4,2.4);pic(s,ROOT/'assets/trips_by_zone.png',9.15,2.0,3.5,2.4);st(s.shapes[10],f'Insight 1: {len(trips):,} trip requests across ten months.\nInsight 2: {cancel_rate:.1f}% of requests were not completed in this synthetic sample.\nInsight 3: Average completed fare was ₹{avg_fare:.2f}; average rating {avg_rating:.2f}/5.',9)
# Slide 5
s=prs.slides[4];sample=gpsdocs[0];pt=sample['gps_points'][0];doc={'trip_id':sample['trip_id'],'driver_id':sample['driver_id'],'trip_status':sample['trip_status'],'distance_km':sample['distance_km'],'gps_points':[{'sequence':pt['sequence'],'event':pt['event'],'coordinates':pt['coordinates']['coordinates']}]};st(s.shapes[4],json.dumps(doc,indent=2),8,font='Consolas');st(s.shapes[5],'Indexes: trip_id (unique), driver_id + requested_at, GPS coordinates (2dsphere).',8);st(s.shapes[6],'CRUD: insert · find · update · delete (examples in JS file).',8);st(s.shapes[9],"db.gps_trip_points.aggregate([\n {$group: {\n   _id: '$driver_id',\n   trips: {$sum: 1},\n   avg_km: {$avg: '$distance_km'}\n }},\n {$sort: {trips: -1}}, {$limit: 10}\n])",8,font='Consolas');pic(s,ROOT/'assets/driver_performance.png',5.1,4.75,3.5,1.5);fill(s.shapes[12].table,[['Aspect','MySQL','MongoDB'],['Schema','Structured','Flexible'],['Relations','PK / FK joins','Embedded arrays'],['Best for','Trips & payments','GPS event traces'],['Our choice','Transactional data','Location history']],7);st(s.shapes[13],'GPS traces contain ordered coordinate/time samples and can vary in length. MongoDB stores the trip path as a nested array and supports geospatial indexing.',8)
# Slide 6
s=prs.slides[5];st(s.shapes[4],f'Finding 1: {cancel_rate:.1f}% non-completed requests in the generated sample.\nFinding 2: Average completed fare: ₹{avg_fare:.2f}.\nFinding 3: Average trip rating: {avg_rating:.2f}/5.',9);st(s.shapes[6],'Challenge: Managing sequential GPS points and structured trip records.\nHow solved: Relational keys for trips; MongoDB documents for GPS arrays.\nLearning: Match storage model to data shape and query needs.',9);st(s.shapes[9],'1. Show the ER model and 3NF tables.\n2. Update trip 11200 and inspect the audit trigger.\n3. Run demand, fare and driver SQL queries.\n4. Execute Python notebook and charts.\n5. Demonstrate MongoDB CRUD and GPS aggregations.',9);st(s.shapes[10],'Files: schema.sql · data.sql · queries.sql · notebook · MongoDB JSONL/JS · README',8);st(s.shapes[11],'Thank you · Questions',15,True,BLUE)
for idx in [2,3,4,5]:
 tx=prs.slides[idx].shapes.add_textbox(Inches(8.6),Inches(6.78),Inches(3.2),Inches(.18));p=tx.text_frame.paragraphs[0];p.text='Synthetic Python-generated demonstration data';p.alignment=PP_ALIGN.RIGHT
 for r in p.runs:r.font.size=Pt(6.5);r.font.italic=True;r.font.color.rgb=MUTED
ppt=OUT/'RideShare_DBMS_Project_Presentation_Rimon_Ghosh.pptx';prs.save(ppt)
print('Built',ppt,'metrics',metrics)
