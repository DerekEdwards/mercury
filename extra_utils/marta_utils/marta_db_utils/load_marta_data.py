"""
This is the main marta data loading script. All the other scripts will be called by this file.
If in future we add any other data parser (or) format converter, make sure that its being
called from here.
"""
import os, re, sys
from utils.variety_utils import log_traceback
from cxze.tracad import models
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from cxze.tracad.templatetags import custom_filters

@log_traceback
def update_direction():
    """
    This function opens the file routes_directions, which contains the short names of routes
    and the directions (N,W,S,E). It then gets the route and the trips associated with the route.
    For each trip, its direction is compared with the direction_type of the route and following
    are the possiblitied allowed - dt -> direction_type, d -> trip.direction
    dt:1 d:0 -> 1, dt:1 d:1 -> 0, dt:2 d:0 -> 2, dt:2 d:1 -> 3, dt:3 d:0 -> 3,
    dt:3 d:1 -> 2, dt:0 d:0 -> 0, dt:0 d:1 -> 1.
    Values 0 -> SouthBound, 1 -> NorthBound, 2 -> EastBound, 3 -> WestBound
    """
    fp = open("routes_directions.txt")
    line = fp.readline()
    line = list(line)
    while len(line) > 1:
        line = fp.readline().strip("\r\n").split(",")
        #Reason for not using just not line is, sometimes just a new line
        #character produces an empty string and creates an list like [""]
        #this evaluates False for 'not line'
        if len(line) > 1:
            route_short_name, direction_type = line
            direction_type = int(direction_type)
            try:
                route = models.Route.objects.get(short_name = route_short_name)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                print "route not there (or) multiple routes with same short name: ", route_short_name
                continue
            trips = route.routetrip_set.all()
            for trip in trips:
                if direction_type == 1 and trip.direction == 0:
                    trip.full_direction = 1
                elif direction_type == 1 and trip.direction == 1:
                    trip.full_direction = 0
                elif direction_type == 2 and trip.direction == 0:
                    trip.full_direction = 2
                elif direction_type == 2 and trip.direction == 1:
                    trip.full_direction = 3
                elif direction_type == 3 and trip.direction == 0:
                    trip.full_direction = 3
                elif direction_type == 3 and trip.direction == 1:
                    trip.full_direction = 2
                else:
                    trip.full_direction = trip.direction
                trip.save()
            print 'done with route: ', route_short_name
    fp.close()
    return


@log_traceback
def rename_stops():
    """
    Gets all the stops and splits it based on @. If the second part consists
    of only numbers, then the stop is renamed as second_part first_part.
    """
    stops = models.Stop.objects.all()
    for stop in stops:
        stop_name = stop.name.split("@")
        if (len(stop_name) > 1) and (re.findall("^\d+$", stop_name[1])):
            stop.name = "%s %s" % (stop_name[1], stop_name[0])
            stop.save()


@log_traceback
def update_headsign():
    """
    For route 26 - which has no headsign set for any trip, this function
    sets it as the route's full name.
    """
    route = models.Route.objects.get(short_name = "26")
    route_trips = route.routetrip_set.all()
    route_trips.update(headsign = route.name)

@log_traceback
def load_streets():
    """
    This function reads through the list of road names from the file
    formalizes them and loads them into the database.
    """
    fp = open("./atlanta_roads.txt")
    line = fp.readline()

    while line:
        line = line.strip("\n")
        line = custom_filters.formalize_address(line)
        st, created = models.Streets.objects.get_or_create(name = line)
        line = fp.readline()

    fp.close()


@log_traceback
def delete_invalid_trips():
    """
    Iterates through all trips and checks the number of stops served for that trip. If the
    count is less than 4, then its considered as invalid trips, and its related stoptime
    objects and trip are deleted. Routes which officially serve 4 or lesser stops are
    stored in the excluded list.
    @params - None
    @output - None
    """
    #Routes which officially only serve at instances less than 4 stops.
    #this list is obtained by running a script and then manually verifying them
    #in the UI.
    excluded_list = ["201", "GREEN", "BLUE", "RED", "GOLD", "521", "143"]
    trips = models.RouteTrip.objects.all()

    for trip in trips:
        if trip.route.short_name not in excluded_list:
            stoptimes_count = trip.stoptime_set.count()
            if stoptimes_count < 4:
                print trip.id, trip.trip_id, trip.route.short_name, stoptimes_count
                stoptimes = trip.stoptime_set.all()
                stoptimes.delete()
                trip.delete()
    return
                


if __name__ == "__main__":
    """
    The main loops executes the files in the following order,
    gtfs_loader -> Gets all marta schedules in gtfs format and loads that in our DB.
    update_direction -> Marta uses same values of 0,1 for N,W,S,E directions. This is
    updated by this function.
    rename_stops -> Iterates through all the stops and if stop name is of street@number
    format, it is renamed as number street format.
    avl_loader -> Loads all marta AVL data (real time trips and blocks, used by their GPS
    device) into our DB.
    load_service_ids -> Marta avl trips initally have their service ids set to null, they
    are set to proper values by this file.
    create_trip_mapping -> The trips and block used by Marta AVL and GTFS data are entirely
    different. This function creates the relationship between them and stores it in DB.
    """
    try:
        os.system("python ./gtfs_loader.py")
    except Exception, e:
        print "Exception occured while running gtfs_loader.py."
        print "Exception: ", e
        sys.exit(1)

    update_direction()
    rename_stops()
    update_headsign()
    load_streets()
    delete_invalid_trips()
    
    try:
        os.system("python ./avl_loader.py")
    except Exception, e:
        print "Exception occured while running avl_loader.py"
        print "Exception: ", e
        sys.exit(1)

    try:
        os.system("python ./load_service_ids.py")
    except Exception, e:
        print "Exception occured while running load_service_ids.py"
        print "Exception: ", e
        sys.exit(1)
    

    try:
        os.system("python ./create_trip_mapping.py")
    except Exception, e:
        print "Exception occured while running create_trip_mapping.py"
        print "Exception: ", e
        sys.exit(1)
    
    
