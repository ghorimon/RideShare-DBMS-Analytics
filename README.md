# RideShare — Cab Trip and Driver Performance Analytics

Problem Statement 10 from the supplied DBMS assignment. MySQL 8+ relational database and MongoDB GPS event documents. All generated records are synthetic, use seed 261119, and do not represent a real ride-hailing operator.

## Dataset
- 400 riders; 80 drivers; 100 vehicles; 1200 trips; 1200 fare rows; 1200 payment rows; 861 ratings.
- Total relational seed rows: 5053.
- Date coverage: January–October 2026.

## Files
- `sql/schema.sql`: 10 tables, keys, constraints, indexes, audit trigger and performance view.
- `sql/data.sql`: synthetic seed inserts.
- `sql/queries.sql`: six analytics queries plus trigger demo.
- `notebooks/rideshare_analysis.ipynb`: DB-API connection, SQL, Pandas and charts.
- `mongodb/gps_trip_points.jsonl`: one GPS trace document per trip.
- `mongodb/rideshare_mongodb.js`: indexes, CRUD and two aggregation pipelines.
- `assets/`: ER diagram, charts and supporting data.
- `speaker_script.md`: oral presentation notes.

## Setup
1. Run `mysql -u root -p < sql/schema.sql`.
2. Load seed data: `mysql -u root -p rideshare < sql/data.sql`.
3. Run SQL queries from `sql/queries.sql`. To demo trigger: `UPDATE trips SET trip_status='Cancelled' WHERE trip_id=11200;` then query `trip_status_history`.
4. Install `pip install mysql-connector-python pandas matplotlib jupyterlab` and set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE before running notebook.
5. Import MongoDB: `mongoimport --db rideshare --collection gps_trip_points --file mongodb/gps_trip_points.jsonl --type json`. Run `mongodb/rideshare_mongodb.js` in mongosh.

## Normalisation
The relational design separates riders, drivers, vehicles, vehicle types, zones, trips, fare details, payments, ratings and trip status history. Examples: `driver_id → driver_name, license_no, join_date, is_active`; `trip_id → rider_id, driver_id, vehicle_id, requested_at, trip_status`; `vehicle_type_id → base_fare, per_km_rate, per_min_rate`. This prevents repeating driver, zone and pricing attributes on every trip.

Metrics in the presentation are calculated from the supplied synthetic dataset. They are demonstrative, not actual platform KPIs.
