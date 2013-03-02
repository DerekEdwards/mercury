/* Please run the following commands before running this sql file
 *
 * Prerequisites:
 * (1) Current MARTA DB is present in marta_bustrack database
 * (2) Current BATMA DB is present in old_batma database
 * (3) Create a database with name bustrack_batma (this will hold the BATMA data in the new format)
 * (4) $ mysqldump -u root -p marta_bustrack --no-data > /tmp/marta_schema.sql
 * (5) $ mysqldump -u root -p marta_bustrack > /tmp/marta_data.sql
 * (6) $ mysqldump -u root -p old_batma > /tmp/batma_data.sql
 * Note: Some of the tables are copied from MARTA (like flags), some from old BATMA DB directly, while are modified to fit to new format.
 */

/* DELETE ALL (Allows this script to be run multiple times without crapping out) */
DELETE FROM bustrack_batma.tracad_systemflags;
DELETE FROM bustrack_batma.tracad_specialads;
DELETE FROM bustrack_batma.tracad_latlngs;
DELETE FROM bustrack_batma.tracad_people;
DELETE FROM bustrack_batma.tracad_route;
DELETE FROM bustrack_batma.tracad_routepath;
DELETE FROM bustrack_batma.tracad_trip;
DELETE FROM bustrack_batma.tracad_stop;
DELETE FROM bustrack_batma.tracad_stoptime;
DELETE FROM bustrack_batma.tracad_vanphoneid;
DELETE FROM bustrack_batma.tracad_vanphonecallback;
DELETE FROM bustrack_batma.tracad_group;
DELETE FROM bustrack_batma.tracad_location;
DELETE FROM bustrack_batma.tracad_name;
DELETE FROM bustrack_batma.tracad_userprofile;
DELETE FROM bustrack_batma.tracad_locationhistory;
DELETE FROM bustrack_batma.tracad_feedbackmessages;
DELETE FROM bustrack_batma.tracad_streets;
DELETE FROM bustrack_batma.tracad_patchthrunumber;
DELETE FROM bustrack_batma.tracad_vandispatchpatchthru;
DELETE FROM bustrack_batma.tracad_usercallback;

/* INSERT ALL */
INSERT INTO bustrack_batma.tracad_systemflags SELECT * FROM marta_bustrack.tracad_systemflags;
INSERT INTO bustrack_batma.tracad_specialads SELECT * FROM old_batma.tracad_specialads;
INSERT INTO bustrack_batma.tracad_latlngs SELECT * FROM old_batma.tracad_latlngs;
INSERT INTO bustrack_batma.tracad_people SELECT * FROM old_batma.tracad_people;
/* TODO: Think about what how to port old_batma.tracad_vandrivertrack without any loss in data */
INSERT INTO bustrack_batma.tracad_route (id, short_name, name, description, color, disabled, cur_trip_num, next_leg_id, circular, route_id, route_type, route_url, route_text_color) SELECT id, short_name, name, `desc`, color, disabled, 0, NULL, True, id, 3, NULL, NULL FROM old_batma.tracad_route;
INSERT INTO bustrack_batma.tracad_routepath (id, route_id, lat, lng, waypoint_sequence, shape_id, shape_dist_traveled, headsign) SELECT (id, route_id, lat, lng, waypoint_sequence, route_id, NULL, NULL) FROM old_batma.tracad_routepath;
/* TODO: from above: 1. Create story to populate shape_dist_traveled 
                     2. Populate headsign */
/* TODO: Check if tracad_routeservicedates is not needed */
INSERT INTO bustrack_batma.tracad_routetrip (id, route_id, full_route_id, headsign, routetrip_name, direction, full_direction, trip_number, last_run, trip_id, service_id, block_id, shape_id) SELECT (id, route_id, 0, headsign, short_name, direction, 0, NULL, NULL, ?, ?, ?, ?) FROM old_batma.tracad_routetrip; /* TODO: Ask this */
INSERT INTO bustrack_batma.tracad_stop (id, name, description, stop_code, disabled, location_id, stop_id, stop_lat, stop_lon, zone_id, stop_url, location_type, parent_station) SELECT (id, name, `desc`, code, disabled, location_id, id, NULL, NULL, NULL, NULL, NULL, NULL) FROM old_batma.tracad_stop;
/* TODO: Populate tracad_routestops table separately for a foreign key relationship */
INSERT INTO bustrack_batma.tracad_stoptime (id, trip_id, full_trip_id, route_id, full_route_id, stop_id, full_stop_id, arrival_time, departure_time, predicted_arrival_time, prediction_timestamp, historical_times, historical_average, stop_sequence, pickup_type, dropoff_type, shape_dist_traveled, stop_headsign) SELECT (id, trip_id, 0, route_id, 0, stop_id, 0, arrival_time, departure_time, NULL, NULL, '', 0, stop_sequence, 0, 0, 0, '') FROM old_batma.tracad_stoptime; /* TODO: Arun, plz check this */
/* Assuming DailyStats and PopularityStats will be populated on the fly */
/* Nothing to be ported for FeaturedLocation and related tables */
INSERT INTO bustrack_batma.tracad_vanphoneid SELECT * FROM old_batma.tracad_vanphoneid;
INSERT INTO bustrack_batma.tracad_vanphonecallback SELECT * FROM old_batma.tracad_vanphonecallback;
/* TODO: Arun, can VanMulTrack populate itself without having to port it ? */
INSERT INTO bustrack_batma.tracad_group SELECT * FROM old_batma.tracad_group;
INSERT INTO bustrack_batma.tracad_location SELECT * FROM old_batma.tracad_location;
INSERT INTO bustrack_batma.tracad_name SELECT * FROM old_batma.tracad_name;
/* Nothing to be ported for ServiceBoundary and PhoneQwerty */
INSERT INTO bustrack_batma.tracad_userprofile (id, user_id, phone_number, contact_preference, phone_number_extension, phone_number_validated, phone_number_validation_code, email_validated, email_validation_code) SELECT (id, user_id, phone_number, NULL, NULL, 0, 1234, 0, 1234) FROM old_batma.tracad_userprofile; /* TODO: Arun, plz check */
INSERT INTO bustrack_batma.tracad_locationhistory SELECT * FROM old_batma.tracad_locationhistory;
INSERT INTO bustrack_batma.tracad_feedbackmessages (id, timestamp, caller, audio_url, registration_message) SELECT (id, date, caller, audio_url, registration_message) FROM old_batma.tracad_feedbackmessages;
INSERT INTO bustrack_batma.tracad_streets SELECT * FROM old_batma.tracad_streets;
INSERT INTO bustrack_batma.tracad_patchthrunumber SELECT * FROM old_batma.tracad_patchthrunumber;
INSERT INTO bustrack_batma.tracad_vandispatchpatchthru SELECT * FROM old_batma.tracad_vandispatchpatchthru;
INSERT INTO bustrack_batma.tracad_usercallback SELECT * FROM old_batma.tracad_usercallback;
/* Rest new tables */


