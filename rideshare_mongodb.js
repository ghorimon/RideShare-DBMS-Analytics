use('rideshare');
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
