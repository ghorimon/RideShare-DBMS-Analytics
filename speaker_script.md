# RideShare — speaker notes

**Slide 1:** RideShare is a cab trip and driver performance analytics database. It models ride requests, assignments, vehicle types, trip fares, payments and ratings.

**Slide 2:** The relational model separates zones, riders, drivers, vehicles, vehicle types, trips, fare details, payments and ratings. Primary and foreign keys preserve relationships. Pricing attributes live in vehicle_types rather than being duplicated for every trip, supporting 3NF.

**Slide 3:** The SQL schema includes constraints and indexes. The AFTER UPDATE trigger records trip status changes in trip_status_history. The vw_trip_performance view joins trips to zones, drivers, fare details and payments. The queries analyse demand, fare, driver earnings, ratings and cancellations.

**Slide 4:** Python connects through MySQL Connector/Python DB-API, executes SQL through a cursor, loads rows into Pandas and plots monthly trip demand and pickup-zone demand. The generated sample has 1,200 trips, a 19.4% non-completed trip share, and an average completed fare of ₹416.27. These are synthetic results, not industry benchmarks.

**Slide 5:** MongoDB stores each trip's ordered GPS samples as an array of nested location documents. This suits event-like location traces. Indexes support trip lookup, driver timelines and geospatial queries. CRUD and aggregation examples are in the JS file.

**Slide 6:** Key findings: 19.4% of requests were not completed in this synthetic sample; average completed fare was ₹416.27; average trip rating was 4.25/5. The live demo shows the ER model, status trigger, SQL analytics, notebook charts and MongoDB GPS aggregations.
