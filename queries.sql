USE rideshare;
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
