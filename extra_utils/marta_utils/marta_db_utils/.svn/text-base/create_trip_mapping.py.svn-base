from cxze.tracad import models
from utils.variety_utils import log_traceback
import datetime

@log_traceback
def map_trip(trip, result, avl_trip_id = None, avl_block_id = None):
    """
    This function gets/creates an gtfs_avl_map based on the trip id and sets
    the avl block id, trip id for that object.
    @param trip - gtfs trip
    @param result - the result of the mapping
    @avl_trip_id - id of matching avl trip, None if there is no match
    @avl_block_id - id of matching avl block, None if there is no match
    """
    gtfs_avl_map, created = models.gtfs_avl_map.objects.get_or_create(trip_id = trip.id)
    gtfs_avl_map.trip_id = trip.id
    gtfs_avl_map.block_id = trip.block_id

    gtfs_avl_map.avl_trip_id = avl_trip_id
    gtfs_avl_map.avl_block_id = avl_block_id

    gtfs_avl_map.result = result
    gtfs_avl_map.save()


@log_traceback
def indepth_map_trip(stops, avl_stops):
    """
    This function gets the list of stops, by stoptimes and avl_stoptimes as input.
    It compares the list and if they are same (including the sequence) then the
    avl_stoptime and stoptimes objects are similar.
    @param stops - a list of gtfs stops
    @param avl_stops - a list of avl stops
    @return - true if route match, false if not
    """
    for index in range(0, len(stops)):
        
        if (stops[index].hour != avl_stops[index].hour) or (stops[index].minute != avl_stops[index].minute):
            return False
        
    return True

@log_traceback
def keep_searching(stops, trip, avl_stops_array, result, avl_trips):
    """
    This function gets the list of stoptimes objects, its associated trip and
    avl trips, array of avl stoptime objects for those avl trips as input.
    It then calls the indepth_map_trip, to compare the stoptime object with each
    avl stoptime. if they match, then we store the relation in gtfs_avl_map.
    @param stops - set of gtfs stops on a trip
    @param trip - a gtfs trip object
    @param avl_stops_array - an array of avl_stops
    @param result - integer indicating result of the mapping
    @param avl_trips - a list of avl_trips
    @return - true if success, false if not
    """
    stops_set = set(stops)
    index = 0
    for avl_stops in avl_stops_array:
        match = indepth_map_trip(stops, avl_stops)
        if match:
            avl_trip = avl_trips[index]
            map_trip(trip, result, avl_trip_id = avl_trip.trip_id, avl_block_id = avl_trip.block_id)
            return True
    
    print 'Trip Matching Fail'
    print 'GTFS trip_id'
    print trip.trip_id
    return False

@log_traceback
def run_mapping(trips):
    """
    This function gets a list of route trips and the short names of routes that run those trips.
    It then gets the list of avl trips based on route short names array. Also from the given list
    of trips, we get the stoptimes for them. For the list of avl trips, get the list of avl stoptimes.
    These two stoptime lists are compared and if they match, then the relationship is stored
    in the gtfs_avl_map.
    @param trips - a gtfs trips array
    """
    trip_stops = []
    for trip in trips:
        route_name = trip.route.short_name

        #Ther is not AVL data for rail, so skip those trips
        if route_name == 'BLUE' or route_name == 'RED' or route_name == 'GOLD' or route_name == 'GREEN':
            s = 'Skipping:  ' + route_name
            print s
            continue
        
        matching_avl_trips = []
        matching_avl_stops = []
        trip_stops = trip.stoptime_set.all().order_by('departure_time')
        trip_stops = trip_stops.values_list('departure_time', flat = True)
        trip_stops_cnt = len(trip_stops)

        avl_trips = models.avl_trip.objects.filter(route_abbr = trip.route.short_name, service_id = trip.service_id)
        for avl_trip in avl_trips:
            avl_stops = models.avl_stoptime.objects.filter(trip_id = avl_trip.trip_id).order_by("crossing_time")
            avl_stops = avl_stops.values_list('crossing_time', flat = True)
            avl_stops_cnt = len(avl_stops)

            if trip_stops[0].hour == avl_stops[0].hour and trip_stops[0].minute == avl_stops[0].minute:
                if trip_stops[trip_stops_cnt -1].hour == avl_stops[avl_stops_cnt - 1].hour and trip_stops[trip_stops_cnt -1].minute == avl_stops[avl_stops_cnt - 1].minute:
                    matching_avl_trips.append(avl_trip)
                    matching_avl_stops.append(avl_stops)
                
        if len(matching_avl_trips) == 1:
            map_trip(trip, 0, avl_trip_id = matching_avl_trips[0].trip_id, avl_block_id = matching_avl_trips[0].block_id)
        elif len(matching_avl_trips) > 1:
            result = keep_searching(trip_stops, trip, matching_avl_stops, 1, matching_avl_trips)
            if not(result):
                map_trip(trip, 5, avl_trip_id = matching_avl_trips[0].trip_id, avl_block_id = matching_avl_trips[0].block_id)
        else:
            print 'NO Match or In depth search'
            map_trip(trip,4)
            
        
if __name__ == '__main__':
    """
    The main loop gets all the route trips objects and then slices them. These
    slices and the route short names, of these trips are passed as input to run_mapping,
    which then creates and store the gtfs to avl mapping.
    Result: 0, Successful mapping.  No indepth search required.
    Result: 1, Successful mapping.  Indepth search required.
    Result: 2, No mapping found.  No indpeth search performed.
    Result: 4, No mapping found.  Indepth search failed. 
    """
    start = datetime.datetime.now()
    trips_cnt = models.RouteTrip.objects.count()
    step_cnt = 100
    for i in range(0, trips_cnt, step_cnt):
        trips = models.RouteTrip.objects.all()[i:i+step_cnt]
        run_mapping(trips)
        print 'trips_cnt: ', i

    end = datetime.datetime.now()
    print (end - start)
