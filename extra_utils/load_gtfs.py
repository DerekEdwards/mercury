from utils.variety_utils import log_traceback
from utils import logger

from ridecell.rdispatch import rdispatch_utils, models
import datetime, optparse

from django.db import connection

@log_traceback
def insert_values(file_path, val_type):
    """
    This function reads through the GTFS format file given as input and based on the file (identified by the val_type)
    chooses the appropriate insert sql query. Reads the file, a line at a time and creates the insert value. 
    Keeps reading and constructs the insert value for 100 lines, then executes the sql query and performs the actual
    insert in the table. Using cursor for inserting values, although not the ideal way, currently with very little knowledge
    and options available in django for bulk insert, we are using this now. 
    TODO: As our knowledge on django improves we need to change this. 

    INPUT - file_path - full path of the file, from which the value is to be inserted. 
    val_type - type of table to be processed. 

    OUTPUT - writes the contents of the input file into the appropriate table. No value is returned.
    """
    cursor = connection.cursor()
    fp = open(file_path)
    line = fp.readline()
    if val_type == 'route':
        insert_str = "insert into rdispatch_route (route_id, short_name, name, description, route_type, route_url, color, route_text_color) values "        
        values_str = '(%s,"%s","%s","%s",%s,"%s","%s","%s"),' 
    elif val_type == 'stop':
        insert_str = "insert into rdispatch_stop (stop_id, stop_code, name, description, stop_lat, stop_lon, zone_id, stop_url, location_type, parent_station) values "        
        values_str = '(%s,"%s","%s","%s","%s","%s",%s,"%s",%s, %s),'
    elif val_type == 'trip':
        insert_str = 'insert into rdispatch_routetrip (route_id, service_id, trip_id, headsign, direction, block_id, shape_id) values '
        values_str = '((select id from rdispatch_route where route_id=%s), %s, %s, "%s", %s, %s, %s),'
    elif val_type == 'shape':
        insert_str = 'insert into rdispatch_shape (shape_id, lat, lng, waypoint_sequence, shape_dist_traveled) values '
        values_str = '(%s, "%s", "%s", %s, "%s"),'
    elif val_type == 'stop_time':
        insert_str = 'insert into rdispatch_stoptime (trip_id, route_id, arrival_time, departure_time, stop_id, stop_sequence, stop_headsign, pickup_type, dropoff_type, shape_dist_traveled) values '
        values_str = '((select id from rdispatch_routetrip where trip_id=%s), (select route_id from rdispatch_routetrip where trip_id=%s), "%s", "%s", (select id from rdispatch_stop where stop_id=%s), %s, "%s", %s, %s, "%s"),'
    cnt = 0
    values = ''
    while line:
        line = fp.readline()
        if line:
            cnt += 1
            line = line.strip("\r\n").replace('"', '').split(",")
            if val_type == 'route':
                values += values_str % (line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7])
            elif val_type == 'stop':
                values += values_str % (line[0], line[1], line[2], line[3], line[4], line[5], (line[6]!='' and line[6] or '0'), line[7], (line[8]!='' and line[8] or '0'), (line[9]!='' and line[9] or '0'))
            elif val_type == 'trip':
                values += values_str % (line[0], line[1], line[2], line[3], line[4], line[5], line[6])
            elif val_type == 'shape':
                values += values_str % (line[0], line[1], line[2], line[3], line[4])
            elif val_type == 'stop_time':
                values += values_str % (line[0], line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7], line[8])
            if cnt >= 100:
                try:
                    cursor.execute(insert_str + values.rstrip(",")+";")
                except Warning:
                    pass
                cnt = 0
                values = ""
        else:
            try:
                cursor.execute(insert_str + values.rstrip(",")+";")    
            except Warning:
                pass
    cursor.close()
    fp.close()
    return



if __name__=='__main__':
    """
    This where the execution begins if the file is run from console. Checks for the mode as command line argument.
    If none is set, then it defaults it to 0 and then starts executing the section of script which loads all the GTFS
    data into the DB. If mode is called with 1, the function runs the section which establishes the route stops relation
    and populates the RouteStops table. 
    Any other mode value, the file doesn nothing but just prints out the start and end time and exits.
    """
    parser = optparse.OptionParser()
    parser.add_option("-m", "--mode", default = '0')
    (options, args) = parser.parse_args()
    print options.mode, args
    start = datetime.datetime.now()
    if options.mode == '0':
        insert_values("/Users/aelangovan6/Desktop/Jun22/stops.txt", 'stop')
        print 'stop inserts over'
        insert_values("/Users/aelangovan6/Desktop/Jun22/routes.txt", 'route')
        print 'route inserts over'
        insert_values("/Users/aelangovan6/Desktop/Jun22/trips.txt", 'trip')
        print 'trips inserts over'
        insert_values("/Users/aelangovan6/Desktop/Jun22/shapes.txt", 'shape')
        print 'path inserts over'
        insert_values("/Users/aelangovan6/Desktop/Jun22/stop_times.txt", 'stop_time')
        print 'stop times inserts over'
        print 'update rdispatch_stoptime set arrival_time = (arrival_time - "%s") where arrival_time >= "%s";' % ("24:00:00", "24:00:00")
        print 'update rdispatch_stoptime set departure_time = (departure_time - "%s") where departure_time >= "%s";' % ("24:00:00", "24:00:00")
        print "Enter the above mentioned commands in mysql and then run the file again with --mode=1 options in command line"
    elif options.mode == '1':
        #gets all the route in the system. Then loops through each routes, stoptime entries and checks which trips
        #has the maximum number of stops. That is assumed to have incorporate all the stops that would be served
        #by the route. Then entries are created for that route and the set of stops in the RouteStops table.
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
            print 'done with route: ', route.name

    end = datetime.datetime.now()
    diff = end - start
    print 'start: ', start, ', end: ', end
    print 'stats, time took in - days: ', diff.days, ', seconds: ', diff.seconds, ', microseconds: ', diff.microseconds


