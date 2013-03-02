"""
This file reads the Marta GTFS data files and loads them into our DB in our format.
It also maintains the foreign key relations. Marta has some times greater than
24 hours, the scripts resets those times and then populates the RouteStops table
with stops in order, server by a route.
"""

from utils.variety_utils import log_traceback
from cxze.tracad import models
import datetime
from django.db import connection

@log_traceback
def insert_values(file_path, val_type):
    """
    This function gets the GTFS format file path and the mode/value type as inputs. Since django
    has no proper bulk inserts we are doing raw sql query insert. Since the insert strings cannot
    be greater than x-len, there has to be a limit on each insert. To perform this, we read 100 lines
    at a time and then construct the insert strings with them. Once all the data is loaded, we create
    indexes for that specific table.
    @params file_path : the path to the file that contains the gtfs data to be loaded in
    @params val_type : a string that determines what type of data we are uploading i.e. (route, stop, trip, shape, or stoptime data).
    """
    cursor = connection.cursor()
    fp = open(file_path)
    line = fp.readline()
    index_str = ''
    if val_type == 'route':
        insert_str = "insert into tracad_route (route_id, short_name, name, description, route_type, route_url, color, route_text_color) values "
        values_str = '(%s,"%s","%s","%s",%s,"%s","%s","%s"),'
        index_str = 'create index route_short_name_idx on tracad_route(short_name);'
        index_str += 'create index route_name_idx on tracad_route(name);'
        index_str += 'create index route_id_idx on tracad_route(route_id);'
        
    elif val_type == 'stop':
        insert_str = "insert into tracad_stop (stop_id, stop_code, name, description, stop_lat, stop_lon, zone_id, stop_url, location_type, parent_station) values "
        values_str = '(%s,"%s","%s","%s","%s","%s",%s,"%s",%s, %s),'
        index_str = 'create index stop_name_idx on tracad_stop(name);'
        index_str += 'create index stop_id_idx on tracad_stop(stop_id);'
        
    elif val_type == 'trip':
        insert_str = 'insert into tracad_routetrip (route_id, service_id, trip_id, headsign, direction, block_id, shape_id) values '
        values_str = '((select id from tracad_route where route_id=%s), %s, %s, "%s", %s, %s, %s),'
        index_str = 'create index trip_shape_idx on tracad_routetrip(shape_id);'
        index_str += 'create index trip_route_idx on tracad_routetrip(route_id);'
        index_str += 'create index trip_headsign_dir_service_idx on tracad_routetrip(headsign, full_direction, service_id);'
        index_str += 'create index trip_id_idx on tracad_routetrip(trip_id);'
        
    elif val_type == 'shape':
        insert_str = 'insert into tracad_shape (shape_id, lat, lng, waypoint_sequence, shape_dist_traveled) values '
        values_str = '(%s, "%s", "%s", %s, %s),'
        index_str = 'create index shape_id_idx on tracad_shape(shape_id);'
        index_str += 'create index shape_id_waypoint_idx on tracad_shape(waypoint_sequence, shape_id);'
        index_str += 'create index shape_id_dist_idx on tracad_shape(shape_dist_traveled, shape_id);'
        
    elif val_type == 'stop_time':
        insert_str = 'insert into tracad_stoptime (trip_id, route_id, arrival_time, departure_time, stop_id, stop_sequence, stop_headsign, pickup_type, dropoff_type, shape_dist_traveled) values '
        values_str = '((select id from tracad_routetrip where trip_id=%s), (select route_id from tracad_routetrip where trip_id=%s), "%s", "%s", (select id from tracad_stop where stop_id=%s), %s, "%s", %s, %s, "%s"),'
        index_str = 'create index stoptime_trip_sequence_idx on tracad_stoptime(stop_sequence, trip_id);'
        index_str += 'create index stoptime_trip_deptime_idx on tracad_stoptime(departure_time, trip_id);'
        index_str += 'create index stoptime_trip_stop_idx on tracad_stoptime(trip_id, stop_id);'
        index_str += 'create index stoptime_trip_route_idx on tracad_stoptime(trip_id, route_id);'
        index_str += 'create index stoptime_trip_shape_idx on tracad_stoptime(shape_dist_traveled, trip_id, departure_time);'
        index_str += 'create index stoptime_trip_stop_dep_idx on tracad_stoptime(departure_time, trip_id, stop_id);'
        index_str += 'create index stoptime_trip on tracad_stoptime(trip_id);'
        index_str += 'create index stoptime_route on tracad_stoptime(route_id);'
        index_str += 'create index stoptime_stop on tracad_stoptime(stop_id);'
        
    cnt = 0
    values = ''
    while line:
        line = fp.readline()
        if line:
            cnt += 1
            line = line.strip("\r\n").replace('"', '').split(",")
            if val_type == 'route':
                values += values_str % (line[0], line[2], line[3], line[4], '"' + line[5] + '"', line[6], line[7], line[8])
            elif val_type == 'stop':
                values += values_str % (line[0], line[1], line[2], line[3], line[4], line[5], (line[6]!='' and line[6] or '0'), line[7], (line[8]!='' and line[8] or '0'), (line[9]!='' and line[9] or '0'))
            elif val_type == 'trip':
                values += values_str % (line[0], line[1], line[2], line[3], line[4], line[5], line[6])
            elif val_type == 'shape':
                values += values_str % (line[0], line[1], line[2], line[3], line[4])
            elif val_type == 'stop_time':
                values += values_str % (line[0], line[0], line[1].strip(' '), line[2].strip(' '), line[3], line[4], line[5], line[6], line[7], line[8])
            if cnt >= 100:
                try:
                    if insert_str:
                        cursor.execute(insert_str + values.rstrip(",")+";")
                except Warning:
                    pass
                cnt = 0
                values = ""
        else:
            try:
                if insert_str:
                    cursor.execute(insert_str + values.rstrip(",")+";")    
            except Warning:
                pass
    print val_type, ' data insert over, creating indexes.'
    if index_str:
        cursor.execute(index_str)
    cursor.close()
    fp.close()
    return



if __name__=='__main__':
    """
    The main loop calls the insert_values function for loading GTFS data into our DB in the
    following order, stops -> routes -> route trips -> shapes -> stop times. Once all the data
    is loaded, since marta has times greater than 24 hours - we run a loop which updates all the
    stoptimes which are greater than 24hours. After this we populate the RouteStops with list
    of stops served by a route.
    """
    start = datetime.datetime.now()
    
    insert_values("./gtfs_data/stops.txt", 'stop')
    print 'stop inserts over'
    insert_values("./gtfs_data/routes.txt", 'route')
    print 'route inserts over'
    insert_values("./gtfs_data/trips.txt", 'trip')
    print 'trips inserts over'
    insert_values("./gtfs_data/shapes.txt", 'shape')
    print 'path inserts over'
    insert_values("./gtfs_data/stop_times.txt", 'stop_time')
    print 'stop times inserts over'
    
    cursor = connection.cursor()
    data_gte_24hr = True
    loop_num = 1
    while data_gte_24hr:
        print 'loop_num in data_gte_24hr: ', loop_num
        try:
            st = models.StopTime.objects.filter(departure_time__gte = datetime.time(23, 59, 59))
            print st
            data_gte_24hr = False
        except ValueError:
            arrival_time_upd = 'update tracad_stoptime set arrival_time = (select timediff(arrival_time, "%s")) where arrival_time >= "%s";'
            arrival_time_upd = arrival_time_upd % ("24:00:00", "24:00:00")
            departure_time_upd = 'update tracad_stoptime set departure_time = (select timediff(departure_time, "%s")) where departure_time >= "%s";'
            departure_time_upd = departure_time_upd % ("24:00:00", "24:00:00")
            try:
                cursor.execute(arrival_time_upd)
            except Warning:
                pass

            try:
                cursor.execute(departure_time_upd)
            except Warning:
                pass
        loop_num += 1

    cursor.close()
    print "done with updating the stop times greater than 24 hrs."

    routes = models.Route.objects.all()
    for route in routes:
        stop_times = route.stoptime_set.filter(stop_sequence=1)
        trips = [stop_time.trip for stop_time in stop_times]
        trip = trips[0]
        trip_cnt = trip.stoptime_set.count()
        for t in trips:
            if t.stoptime_set.count() > trip_cnt:
                trip = t
                trip_cnt = t.stoptime_set.count()
        trip_stop_times = trip.stoptime_set.all().order_by('stop_sequence')
        for stop_time in trip_stop_times:
            route_stop, created = models.RouteStops.objects.get_or_create(stop=stop_time.stop, 
                                                                          route=stop_time.route, 
                                                                          sequence=stop_time.stop_sequence)
            if not created:
                print route_stop.id, ' already exists'
        print 'RouteStops done with route: ', route.name
            
    end = datetime.datetime.now()
    diff = end - start
    print 'start: ', start, ', end: ', end
    print 'stats, time took in - days: ', diff.days, ', seconds: ', diff.seconds, ', microseconds: ', diff.microseconds
