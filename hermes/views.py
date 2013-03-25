import random, numpy, copy, urllib2, urllib, time, csv, datetime

from django.core.exceptions import ObjectDoesNotExist
from django.utils import simplejson
from django.http import HttpResponse
from extra_utils.variety_utils import log_traceback

from hermes import models, utils, planner_manager
from NITS_CODE import settings

#This bus speed is used for some very crude vehicle location estimation.  It is used as stop gap measure since I was violating the Google Maps API
#TODO: Build an Open Source Routing Machine for Atlanta to hande vehicle routing issues
#http://project-osrm.org/
BUS_SPEED = 6.705 #Meters per Second ~= 15 mph

#############################################
#TODO: Have this read a GTFS-based trip planner.  These times are MARTA specific
#Builds the transit matrix
transit_matrix = []
transit_row  = []
transit_reader = csv.reader(open('hermes/bin/transit_times.csv', 'r'))
for row in transit_reader:
    for entry in row:
        transit_row.append(float(entry))
    transit_matrix.append(row)
    transit_row = []
#############################################

@log_traceback
def route_planner(flexbus_start, flexbus_end, time):
    """
    route_planner finds the time that it takes to travel between two subnets via fixed route transit
    @param flexbus_start : flexbus object that the passenger will be departing from
    @param flexbus_end : flexbus object that the passenger will be traveling towards
    @param time : datetime object future future use with a trip planner
    @return : triplet containing total transit time, total walking time, and total waiting time
    """
    #TODO: Replace this with a GTFS-based trip planner
    #This line looks up travel times between MARTA stations in the transit_matrix.  7.5 minutes is added to account for average headways
    transit_time =  (float(transit_matrix[flexbus_start.subnet.gateway.gateway_id - 1][flexbus_end.subnet.gateway.gateway_id -1]) + 7.5)*60.0
    return transit_time, 0, 0

@log_traceback
def create_trips(passenger, second):
    """
    Takes in a passenger.  Determines which buses can handle that passenger's trip.
    Create the trips or trip segments for the passenger with the correctly assigned busses
    @param passenger : passenger object seeking a vehicle
    @param second : the seconds count into the simulation
    """

    if settings.USE_CIRCULAR_SUBNET:
        # Get the busses for the passenger's starting subnet
        start_buses = get_candidate_vehicles_from_point_radius(passenger.start_lat, passenger.start_lng)
        # Get the busses for the passenger's ending subnet
        end_buses = get_candidate_vehicles_from_point_radius(passenger.end_lat, passenger.end_lng)
    elif settings.USE_ISOCHRONE_SUBNET:
        # Get the busses for the passenger's starting subnet
        start_buses = get_candidate_vehicles_from_point_geofence(passenger.start_lat, passenger.start_lng)
        # Get the busses for the passenger's ending subnet
        end_buses = get_candidate_vehicles_from_point_geofence(passenger.end_lat, passenger.end_lng)
    else:
        print 'NO SUBNET TYPE IS CHOSEN!!!! ERROR ERROR ERROR!!!!!'
        return

    if not start_buses and not end_buses: #This is a fully static trip
        create_static_trip(passenger, [passenger.start_lat, passenger.start_lng], [passenger.end_lat, passenger.end_lng], trip_sequence = 0, earliest_start_time = second)
    elif start_buses and (not end_buses): #The first leg is DRT, the rest of the trip is Static
        start_bus, end_bus = create_dynamic_trip(passenger, second, start_buses = start_buses, end_buses = None)
        create_static_trip(passenger, [start_bus.subnet.gateway.lat, start_bus.subnet.gateway.lng], [passenger.end_lat, passenger.end_lng], trip_sequence = 1)
    elif (not start_buses) and end_buses: #The final leg is DRT, the first portion is Static
        start_bus, end_bus = create_dynamic_trip(passenger, second, start_buses = None, end_buses = end_buses)
        create_static_trip(passenger, [passenger.start_lat, passenger.start_lng], [end_bus.subnet.gateway.lat, end_bus.subnet.gateway.lng], trip_sequence = 0, earliest_start_time = second)       
    else: #Both legs are DRT.
        start_bus, end_bus = create_dynamic_trip(passenger, second, start_buses, end_buses)
        create_static_trip(passenger, [start_bus.subnet.gateway.lat, start_bus.subnet.gateway.lng], [end_bus.subnet.gateway.lat, end_bus.subnet.gateway.lng], trip_sequence = 1)
    return

@log_traceback
def create_dynamic_trip(passenger, second, start_buses = None, end_buses = None):
    """
    Creates DRT trips.
    @param passenger : passenger object 
    @param buses : array of potential buses
    @param next_leg__buses : array of potential end_buses (optional) It's included to take into account the chance that a single vehicle can handle both trips.
    TODO: Consider the situation where a single vehicle can handle the entire trip
    TODO: Find a way to not assign a bus to trips that are not ready to start yet.
    """
    start_bus = None
    end_bus = None
    if start_buses:
        start_bus = which_bus(start_buses, passenger, second)
    if end_buses:
        end_bus = which_bus(end_buses, passenger, second)
    if not start_buses and not end_buses:
        return start_bus, end_bus

    if start_bus == end_bus:
        #If the two busses are the same bus, this can be handled by one bus without fixed transit
        #TODO: Try to make this happen if possible, instead of only checking to see if the same bus was chosen by accident
        models.TripSegment.objects.create(passenger = passenger, flexbus = start_bus, start_lat = passenger.start_lat, end_lat = passenger.end_lat, start_lng = passenger.start_lng, end_lng = passenger.end_lng, status = 1, earliest_start_time = second, trip_sequence = 0)
    elif start_buses and end_buses:
        models.TripSegment.objects.create(passenger = passenger, flexbus = start_bus, start_lat = passenger.start_lat, end_lat = start_bus.subnet.gateway.lat, start_lng = passenger.start_lng, end_lng = start_bus.subnet.gateway.lng, status = 1, earliest_start_time = second, trip_sequence = 0)
        models.TripSegment.objects.create(passenger = passenger, flexbus = end_bus, start_lat = end_bus.subnet.gateway.lat, end_lat = passenger.end_lat, start_lng = end_bus.subnet.gateway.lng, end_lng = passenger.end_lng, status = 1, trip_sequence = 2)
    elif start_buses and (not end_buses):
        models.TripSegment.objects.create(passenger = passenger, flexbus = start_bus, start_lat = passenger.start_lat, end_lat = start_bus.subnet.gateway.lat, start_lng = passenger.start_lng, end_lng = start_bus.subnet.gateway.lng, status = 1, earliest_start_time = second, trip_sequence = 0)
    elif (not start_buses) and end_buses:
        models.TripSegment.objects.create(passenger = passenger, flexbus = end_bus, start_lat = end_bus.subnet.gateway.lat, end_lat = passenger.end_lat, start_lng = end_bus.subnet.gateway.lng, end_lng = passenger.end_lng, status = 1, trip_sequence = 1)

    return start_bus, end_bus

@log_traceback
def create_static_trip(passenger, start_loc, end_loc, trip_sequence, earliest_start_time = None):
    """
    Given a passenger object, create a static trip for that object.  Do not yet fill in the times, simply create the object.
    @param passenger : a passenger object
    @param earliest_start_time : time in seconds
    @param start_loc : a tuple of the form [start_lat, start_lng]
    @param end_loc : a tuple of the form [end_lat, end_lng]
    @param trip_sequence : the sequence of the trip.  In a typical NITS trip with both a first and last mile DRT trip, the trip sequence will be 1.  0 = first leg, 1 = second leg, 2 = third leg.
    """
    static_trip = models.TripSegment.objects.create(passenger = passenger, earliest_start_time = earliest_start_time, start_lat = start_loc[0], start_lng = start_loc[1], end_lat = end_loc[0], end_lng = end_loc[1], status = 1, trip_sequence = trip_sequence, static = 1)

    static_trip.save()
    return
    
@log_traceback
def insert_trip(second, trip_segment):
    """
    Takes in a trip, selects the current optimization scheme and passes that vehicle along for route optimization
    @param second : seconds into the simulation
    @param trip_segment : trip object that has been inserted and is ready for optimization
    """
    #TODO: create a settings entry to select the optimization scheme we want to use
    return simple_optimize_route(second, trip_segment, trip_segment.flexbus)
    #return ga_optimize_route(second, trip_segment.flexbus)
    #return heuristic_optimize_route(second, trip_segment.flexbus)

@log_traceback
def which_bus(busses, passenger, second):
    """
    Takes in a query of buses and determines which one will be finished with its route first.
    If no routes are finished within 30 minutes.  A new bus is dispatched.
    TODO: We should make this a smarter algorithm.  Do not simply put the passenger on the bus with the least burden.  This does not take into account the locatino of the passenger.
    @busses : a query of flexbus objects
    @second : the seconds into the simulation
    @return : the bus with the shortest total trip
    """
    min_bus = None
    min_time = float('inf');
    for bus in busses:
        #Get the trips for each bus
        trips = models.TripSegment.objects.filter(flexbus = bus, end_time__gte = second, end_time__lt = 20000)
        #If the bus has no trips, return this bus
        if trips.count() == 0:
            return bus

        #If the bus has trips, save the trip which is scheduled to finish last.
        last_trip = None
        last_time = 0
        for trip in trips:
            if trip.end_time > last_time:
                last_time = trip.end_time
                last_trip = trip

        #If this busses last trip is the earlist trip so far, save it
        if (last_time - second) < min_time:
            min_time = last_time - second
            min_bus = bus

    #If no bus is scheduld to be done in 30 minutes, create a new bus to handle this request
    if min_time > 30*60:
        vehicles = models.FlexBus.objects.all()
        id = vehicles.count() + 1
        if len(busses) > 0:
            flexbus, created = models.FlexBus.objects.get_or_create(vehicle_id = id, subnet = bus.subnet)
        else: #TODO, this simply assigns the passenger to the subnet of the last bus in the queue, not necessariliy the best
            flexbus, created = models.FlexBus.objects.get_or_create(vehicle_id = id, subnet = bus.subnet)
        return flexbus
    else:
        return min_bus

@log_traceback
def get_candidate_vehicles_from_point_geofence(lat, lng):
    """
    This function takes in a point and returns the vehicles for every subnet geofence that this point lies within.  This is the set of vehicles that the passenger is eligible for. 
    TODO: If a subnet exists, but no buses are assigned to it.  This logic will not work.  consider revising.
    TODO:  In the future, gather any vehicles from subnets that touch any eligible subnet subnet.  This will allow for vehicles to travel between adjacent subnets.
    """
    subnets_in_range = []
    vehicles = []

    subnets = models.Subnet.objects.all()
    for subnet in subnets:
        gw = subnet.gateway
        sides = models.FencePost.objects.filter(gateway = gw)
        if point_within_geofence(lat, lng, sides):
            subnets_in_range.append(subnet)

    for subnet in subnets_in_range:
        subnet_vehicles = subnet.flexbus_set.all()
        for sv in subnet_vehicles:
            vehicles.append(sv)

    return vehicles
        

@log_traceback
def point_within_geofence(lat, lng, sides):
    """
    This function takes in lat, lng, and a query of FencePost objects and returns True if the lat,lng is within the FencePost perimeter
    or a false otherwise
    @param lat : float latitude of point
    @param lng : float longitude of point
    @param sides : a query of FencePost objects
    """
    sides_cnt = sides.count()
    if sides_cnt < 3:
        return False

    sides = sides.order_by('sequence')
    pointStatus = False
    j = sides_cnt - 1

    for i in range(sides_cnt):
        if ((sides[i].lat < lat and sides[j].lat >= lat) or (sides[j].lat < lat and sides[i].lat >= lat)):
            if ((sides[i].lng + ((lat - sides[i].lat)/(sides[j].lat - sides[i].lat))*(sides[j].lng - sides[i].lng)) < lng):
                pointStatus = not pointStatus
        j = i
    
    return pointStatus

@log_traceback
def get_candidate_vehicles_from_point_radius(lat, lng):
    """
    Take in a point, and determine which buses can visit this point.  Return those busses
    This function finds all subnet gateways that are within 1800 meters of the point. The function returns all vehicles within any subnet in range.  The function also returns the closest subnet.
    @param lat : latitude
    @param lng : longitude
    @return vehicles, closest_subnet : return a set of vehicles that are eligible to service this trip as well as the appropriate subnet    
    """
    #For the simplest case, there is one bus per subnet.
    subnets = models.Subnet.objects.all()
    min_dist = settings.CIRCULAR_SUBNET_RADIUS 
    min_subnet = None
    closest_dist = float('inf')
    closest_subnet = None
    subnets_in_range = []
    vehicles = []
    # Assign passenger to the subnet that's center is closest to the passengers lat/lng
    for subnet in subnets:
        distance = utils.haversine_dist([float(subnet.center_lat), float(subnet.center_lng)], [lat, lng])
        if distance < min_dist:
            subnets_in_range.append(subnet)
        if distance < closest_dist:
            closest_subnet = subnet

    for subnet in subnets_in_range:
        subnet_vehicles = subnet.flexbus_set.all()
        for sv in subnet_vehicles:
            vehicles.append(sv)

    return vehicles

@log_traceback
def randperm(n):
    """
    create a random permutation of n integers in the range of n
    This is used in the Genetic Algorithm optimization approach
    @param n : integer
    @return an array of integers
    """
    t = range(n)
    random.shuffle(t)
    return t

@log_traceback
def fix_order(V, full_trips_count):
    """
    This is what separates DARP from TSP
    When creating random generations we must ensure that the passenger's dropoff locations is not visited before that passenger's
    pickup location. Used with the Genetic Algorithm Optimizer
    @param V : an array of pickup and drop off locations
    @param full_trips_count : the number of trips that have not yet been started
    @return an array of location where we ensure that passengers are not dropped off before they are picked up
    """

    for idx1 in range(full_trips_count):
        a=copy.copy(V.index(idx1))
        b=copy.copy(V.index(idx1+(full_trips_count)))
        if a > b:
            V[b] = idx1
            V[a] = idx1 + full_trips_count

    return V

@log_traceback
def get_distance_from_array(lats, lngs):
    """
    Given an array of lats and an array of lngs, find the total distance to travel the path
    @param lats : an array of lats
    @param lngs : an array of lngs to go with the lats
    @return the total physical distance to visit these points in the given order
    """
    distance = 0
    for index in range(len(lats) - 1):
        distance += utils.haversine_dist([lats[index], lngs[index]], [lats[index + 1], lngs[index + 1]])

    return distance
  
@log_traceback
def update_next_segment(trip):
    """
    When a trip segment has been assigned an end_time, this functino is called to alert the next trip_segment to when it can begin
    @param trip : the first leg of a passenger's trip
    """
    try:
        next_trip = models.TripSegment.objects.get(passenger = trip.passenger, trip_sequence = trip.trip_sequence + 1)
    except ObjectDoesNotExist:
        return
    
    next_trip.earliest_start_time = trip.end_time + 1 #the static trip can start 1 second after the dynamic trip ends
    
    next_trip.save()

@log_traceback
def assign_time(trip, time, mode):
    """
    Save trip start and end times
    @param trip : a trip object to be updated
    @param mode : does the time represent and ending or beginning time?
    @param time : the number of seconds into the simulation 
    """
    #mode 1: assign start_time
    #mode 2: assign end_time

    if mode == 1:
        trip.start_time = int(time)
        trip.save()
    elif mode == 2:
        trip.end_time = int(time)
        trip.save()
    return

@log_traceback
def get_flexbus_location(flexbus, second, flexbus_stops = None):
    """
    Given a flexbus, the current time, and an optional list of stops, this function returns the location of the bus at the given time.
    Given a flexbus and list of stops for that bus, determine the current location fo the bus.
    This function needs serious work.  It previously pulled data from Google Maps but this violates the google MAPS API terms.
    The current makes a very rough estimate of the busses position using staight line estimates.  
    TODO: This needs to be changed to handle OSRM (Open Source Routing Machine) results.  OSRM allows for vehicle routing without API restrictions.
    @param flexbus : the bus we want to know the location of
    @param second : the time that we are concerned with
    @param flexbus_stops : optional paramter that prevents us from having to requery the bus' stops
    @return a triple representing the lat and lng of the vehicles as well as what percentage of the trip the bus has completed between he previous and next stops
    """
    if flexbus_stops == None:
        flexbus_stops = models.Stop.objects.filter(flexbus = flexbus).order_by('sequence')

    next_stop = flexbus_stops.filter(visit_time__gt = second)

    if next_stop.count():
        next_stop = next_stop[0]
    else:
        return flexbus.subnet.gateway.lat, flexbus.subnet.gateway.lng, 0

    last_stop = flexbus_stops.filter(visit_time__lte = second)
    
    if last_stop.count():
        last_stop = last_stop[last_stop.count() - 1]
        last_stop_lat = last_stop.lat
        last_stop_lng = last_stop.lng
        last_stop_time = last_stop.visit_time
    else:
        last_stop_lat = flexbus.subnet.gateway.lat
        last_stop_lng = flexbus.subnet.gateway.lng
        last_stop_time = second

    if last_stop_time == second:
        return last_stop_lat, last_stop_lng, 0


    ## If we made it this far, that means that the vehicle is between two stops.  This is the most likely scenario.
    percent_complete = float(second - last_stop_time)/float(next_stop.visit_time - last_stop_time) 

    geometry, distance, travel_time = planner_manager.get_optimal_vehicle_itinerary([next_stop.lat, next_stop.lng], [last_stop.lat, last_stop.lng])
    points = planner_manager.decode_line(geometry)

    #This assumes that the travel speed is constant between these two points.  It obviously is not, but on the average this will be the case.
    #TODO:  look for a solution that does not assume a constant speed between points.  
    approx_distance = distance*percent_complete

    total_distance = 0
    first_time = True
    for point in points:
        if first_time:
            first_time = False
            last_point = point
            if total_distance >= approx_distance:
                flexbus_location = point
                break
        else:
            leg_distance = utils.haversine_dist([last_point[0], last_point[1]], [point[0], point[1]])
            previous_distance = total_distance
            total_distance += leg_distance
            if total_distance >= approx_distance:
                flexbus_location = get_intermediate_point(last_point, point, approx_distance, previous_distance, total_distance)
                break
            else:
                last_point = point
    
    return flexbus_location[0], flexbus_location[1], 0

@log_traceback
def get_intermediate_point(last_point, next_point, current_distance, last_distance, next_distance):
    """
    This function is used to find the location of a flexbus.  Given the prevoius point along a shape, the next point along the shape, the shape_dist_traveled of both shapes and the shape_dist_traveled of the flexbus' current location, return the lat,lng of the flexbus
    @param last_point : [lat, lng] of the previous point along the shape
    @param next_point : [lat, lng] of the next point along the shape
    @param current_distance : the shape_dist_traveled of the current location of the flexbus
    @param last_distance : the shape_dist_traveled of the previous point along the shape
    @param next_distance : the shape_dist_traveled of the next point along the shape
    @return : [lat, lng] of the flexbus' location
    """
    percent_between_points = float(current_distance - last_distance)/float(next_distance - last_distance)
    
    lat = percent_between_points*(next_point[0] - last_point[0]) + last_point[0]
    lng = percent_between_points*(next_point[1] - last_point[1]) + last_point[1]

    return [lat,lng]


@log_traceback
def get_cost(flexbus_lat, flexbus_lng, second, sequence, locations, new_trips, unstarted_trips, started_trips, new_trips_count, full_trips_count):
    """
    given a vehicles location a set of trips and sequences, calculate the cost of visiting the locations
    @param flexbus_lat : current lat of the bus
    @param flexbus_lng : current lng of the bus
    @param second : current time
    @param sequence : the sequence in which to visit the given locations
    @param locations : the locations to be visited
    @param new_trips : newly requested trips
    @param unstarted_trips : trips that have not started but are not newly requested
    @param started_trips : trips that have already started
    @param new_trips_count : how many trips are new
    @param full_trips_count : how many trips have not yet started
    @return the cost of visiting the trips given the sequence
    """
    time = second
    speed = BUS_SPEED
    stop_order = []
    new_trips_cost = [0 for x in range(new_trips_count)]
    unstarted_trips_cost = [0 for x in range(full_trips_count - new_trips_count)]
    started_trips_cost = []
    
    for index in range(len(sequence)):
        stop = sequence[index]
        stop_order.append(locations[stop])
        if index: #TODO  Improve this bad approximation of bus speed
            previous_stop = sequence[index - 1]
            travel_time = utils.haversine_dist([locations[stop][0], locations[stop][1]], [locations[previous_stop][0], locations[previous_stop][1]])*(1/speed)
        else:
            travel_time = utils.haversine_dist([flexbus_lat, flexbus_lng], [locations[stop][0], locations[stop][1]])*(1/speed)

        
        time += travel_time

        #1 = assign start_time
        #2 = assign end_time 

        #P/U time of new trips:
        if stop < new_trips_count:
            continue

        #P/U time of unstarted trips, that aren't new
        elif stop < full_trips_count:
            continue

        #D/O time of new_trips
        elif stop < (new_trips_count + full_trips_count):
            trip = new_trips[stop - full_trips_count]
            new_trips_cost[stop - full_trips_count] = time - trip.earliest_start_time

        #D/O time of unstarted trips, that aren't new    
        elif stop < 2*full_trips_count:
            trip = unstarted_trips[stop - full_trips_count - new_trips_count]
            unstarted_trips_cost[stop - full_trips_count - new_trips_count] = time - trip.earliest_start_time

        #D/O time of started trips
        else:
            trip = started_trips[stop - 2*full_trips_count]
            started_trips_cost.append(time - trip.earliest_start_time)
            
    cost = sum(new_trips_cost) + sum(unstarted_trips_cost) + sum(started_trips_cost)
    return cost

@log_traceback
def convert_sequence_to_locations(flexbus, second, sequence, locations, new_trips, unstarted_trips, started_trips, new_trips_count, full_trips_count):
    """
    Convert a sequence of stops into the stop lat,lngs
    Assign start_time and end_time to trips
    @param flexbus_lat : current lat of the bus
    @param flexbus_lng : current lng of the bus
    @param second : current time
    @param sequence : the sequence in which to visit the given locations
    @param locations : the locations to be visited
    @param new_trips : newly requested trips
    @param unstarted_trips : trips that have not started but are not newly requested
    @param started_trips : trips that have already started
    @param new_trips_count : how many trips are new
    @param full_trips_count : how many trips have not yet started
    @return the order in which the stops are visited
    """
    sim_time = second
    speed = BUS_SPEED
    stop_order = []

    #########################################
    # PART 1 - Purge all of the flexbus's future stops and get the current location of the vehicle
    ##########################################

    flexbus_stops = models.Stop.objects.filter(flexbus = flexbus).order_by('visit_time')
    previous_stops = flexbus_stops.filter(visit_time__lte = second)
    flexbus_lat, flexbus_lng, other_time = get_flexbus_location(flexbus, second, flexbus_stops)

    #The bus has prevoius stops
    if previous_stops:
        count = previous_stops[previous_stops.count() - 1].sequence + 1
        models.Stop.objects.create(flexbus = flexbus, lat = flexbus_lat, lng = flexbus_lng, sequence = count, visit_time = second)
        count += 1
    #The bus has not yet left the station
    else:
        models.Stop.objects.create(flexbus = flexbus, lat = flexbus.subnet.gateway.lat, lng = flexbus.subnet.gateway.lng, sequence = 0, visit_time = second)
        count = 1
        
    future_stops = flexbus_stops.filter(visit_time__gt = second)
    future_stops.delete()
    
    #########################################
    # PART 2 - Get the actual driving results and route path
    ##########################################

        
    for index in range(len(sequence)):
        stop = sequence[index]
        stop_order.append(locations[stop])
        if index:
            previous_stop = sequence[index - 1]
            travel_time = utils.get_google_distance(locations[stop][0], locations[stop][1], locations[previous_stop][0], locations[previous_stop][1])
        else:
            travel_time = utils.get_google_distance(flexbus_lat, flexbus_lng, locations[stop][0], locations[stop][1])
        flexbus_stop = models.Stop.objects.create(flexbus = flexbus, lat = locations[stop][0], lng = locations[stop][1], sequence = count, visit_time = sim_time + travel_time)
                     
        count += 1
        sim_time += travel_time

        #1 = assign start_time
        #2 = assign end_time 

        #P/U time of new trips:
        if stop < new_trips_count:
            assign_time(new_trips[stop], sim_time, 1)

        #P/U time of unstarted trips, that aren't new
        elif stop < full_trips_count:
            assign_time(unstarted_trips[stop - new_trips_count], sim_time, 1)

        #D/O time of new_trips
        elif stop < (new_trips_count + full_trips_count):
            trip = new_trips[stop - full_trips_count]
            assign_time(trip, sim_time, 2)
            update_next_segment(trip)

        #D/O time of unstarted trips, that aren't new    
        elif stop < 2*full_trips_count:
            trip = unstarted_trips[stop - full_trips_count - new_trips_count]
            assign_time(trip, sim_time, 2)
            update_next_segment(trip)

        #D/O time of started trips
        else:
            trip = started_trips[stop - 2*full_trips_count]
            assign_time(trip, sim_time, 2)
            update_next_segment(trip)

    #Add a stoptime for returning to the gateway
    travel_time = utils.haversine_dist([flexbus.subnet.gateway.lat, flexbus.subnet.gateway.lng], [locations[len(locations) - 1][0], locations[len(locations) - 1][1]])*(1/speed)
    flexbus_stop = models.Stop.objects.create(flexbus = flexbus, lat = flexbus.subnet.gateway.lat, lng = flexbus.subnet.gateway.lng, sequence = count, visit_time = sim_time + travel_time)

    return stop_order

@log_traceback
def simple_convert_sequence_to_locations(flexbus, second, stop_array):
    """
    This function converts sequences to physical locations and is meant to be used with the simple hueristic method.
    Convert a sequence of stops into the stop lat,lngs
    Assign start_time and end_time to trips
    @param flexbus_lat : current lat of the bus
    @param flexbus_lng : current lng of the bus
    @param second : current time
    @param sequence : the sequence in which to visit the given locations
    @param locations : the locations to be visited
    @param new_trips : newly requested trips
    @param unstarted_trips : trips that have not started but are not newly requested
    @param started_trips : trips that have already started
    @param new_trips_count : how many trips are new
    @param full_trips_count : how many trips have not yet started
    @return the order in which the stops are visited
    """
    sim_time = second
    speed = BUS_SPEED
    stop_order = []

    sequence = stop_array[0].sequence

    for stop in stop_array:
        stop.sequence = sequence
        stop.save()
        sequence += 1
        
    for index in range(len(stop_array) - 2):
        travel_time = utils.get_google_distance(stop_array[index].lat, stop_array[index].lng, stop_array[index+1].lat, stop_array[index+1].lng)
        stop_array[index + 1].visit_time = sim_time + travel_time
        stop_array[index + 1].save()
                     
        sim_time += travel_time

        #Update the times for the trips that these stops represent
        if stop_array[index + 1].trip: #if this stop is for a trip and not an intermediate stop, update this trip and the next trip
            assign_time(stop_array[index + 1].trip, sim_time, stop_array[index + 1].type)
            update_next_segment(stop_array[index + 1].trip)

    #Add a stoptime for returning to the gateway
    travel_time = utils.get_google_distance(flexbus.subnet.gateway.lat, flexbus.subnet.gateway.lng, stop_array[len(stop_array) - 1].lat, stop_array[len(stop_array) - 1].lng)
    flexbus_stop = models.Stop.objects.create(flexbus = flexbus, lat = flexbus.subnet.gateway.lat, lng = flexbus.subnet.gateway.lng, sequence = sequence, visit_time = sim_time + travel_time)

    for stop in stop_array:
        print str(stop.lat) + ',' + str(stop.lng)

    return stop_array

@log_traceback
def ga_optimize_route(second, flexbus):
    """
    Genetic Algorithm Optimization Routine
    Given the current time and a bus, optimize the bus' route from the stops assigned to it.
    @param second : the time
    @param flexbus : a flexbus object
    Returns the order and cost
    """

    flexbus_lat, flexbus_lng, diff_time = get_flexbus_location(flexbus, second)

    #Get all the trips belonging to the bus
    trips = models.TripSegment.objects.filter(flexbus = flexbus)
    started_trips = trips.filter(start_time__lte = second, end_time__gt = second)
    unstarted_trips = trips.filter(earliest_start_time__lte = second, end_time__gt = second, start_time__gt = second)
    new_trips = trips.filter(earliest_start_time__lte = second, start_time = None)
    new_trips.update(status = 2)
                          
    new_trips_count = new_trips.count()
    full_trips_count = unstarted_trips.count()+ new_trips_count

    trip_starts = []
    trip_ends = []
    #Get the start and end locations associated with those trips
    for trip in new_trips:
        trip_starts.append([trip.start_lat, trip.start_lng])
        trip_ends.append([trip.end_lat, trip.end_lng])

    for trip in unstarted_trips:
        trip_starts.append([trip.start_lat, trip.start_lng])
        trip_ends.append([trip.end_lat, trip.end_lng])

    for trip in started_trips:
        trip_ends.append([trip.end_lat, trip.end_lng])
    
    #Convert the list of trips into one long array

    #The first half of the array is the list of starting locations
    #and the second half o the array is the list of ending locations
    locations = trip_starts
    locations.extend(trip_ends)
          
    #Create initial variables for the optimizer
    pop_size = 100 #Number of genes in each generation
    num_iter = 1000 #Number of generations to run
    num_stops = len(locations) #The number of stop

    #Create an initial population with random sequences
    pop = []
    for k in range(pop_size):
        pop.append(randperm(num_stops))

    #Set the initial minimum to infinity
    global_min = float('inf')
    #Temporary variable
    tmp_pop = []

    #Run the GA
    for iter in range(num_iter):
        
        total_dist = [] #The array of costs for each gene
        for k in range(pop_size):
            #Correct any issues with the orderting (i.e. fix issues with D/O's being visited before P/U's
            pop[k] = fix_order(pop[k], full_trips_count)

            total_dist.append(get_cost(flexbus_lat, flexbus_lng, second, pop[k], locations, new_trips, unstarted_trips, started_trips, new_trips_count, full_trips_count))


        #Find the minimum cost gene from this generation
        min_dist = min(total_dist)
        #If this generaitons minimum cost gene is the smallest encountered so far, save it.
        if(global_min > min_dist):
            global_min = min_dist
            opt_rte = pop[total_dist.index(min_dist)]


        ###################################
        ### Randomize and Mutate
        ####################################

        #Generate a randome sequence of genes
        rand_gene_order = randperm(pop_size)

        ###Iterate through each gene in the generation
        # Use the order defined by rand_gene_order, taking 5 genes at a time
        for j in range(pop_size/5):
            p = (j+1)*5
            rand_entries = copy.copy(rand_gene_order[p-5:p])
            rtes = []
            dists = []
            #Get the routes and costs of each of the 5 genes
            for entry in rand_entries:
                rtes.append(pop[entry])
                dists.append(total_dist[entry])


            #Take only the best gene from the set of five
            #This is now saved as best_of_rtes
            idx = dists.index(min(dists))
            best_of_rtes = copy.copy(rtes[idx])

            #Generate two random numbers for mutation purposes
            #The numbers will be in the range of the number of stops
            ins_pts = [int(random.random()*num_stops),  int(random.random()*num_stops)]
    
            I = min(ins_pts) #The smaller of the two random numbers
            J = max(ins_pts) #The larger of the two random numbers

            #For each best_of_rtes gene, perform 5 operations, as described below
            for idx in range(5):

                if idx == 0: #do nothing
                    tmp_pop.append(best_of_rtes)

                if idx == 1: #flip:  take all sequence between stops I and J, and reverse their order
                    temp = copy.copy(best_of_rtes[I:J+1])
                    temp.reverse()
                    temp_best = copy.copy(best_of_rtes)
                    temp_best[I:J+1] = temp
                    tmp_pop.append(temp_best)
                   
                elif idx == 2: #Swap:  Swap the Ith and Jth elements of best_of_rtes
                    tempI = copy.copy(best_of_rtes[I])
                    tempJ = copy.copy(best_of_rtes[J])
                    temp_best = copy.copy(best_of_rtes)
                    temp_best[I] = tempJ
                    temp_best[J] = tempI
                    tmp_pop.append(temp_best)

                elif idx == 3: #Slide:  Slide all the elements from I+1 to J down one slot.  Then put the Ith element in the Jth slot.
                    tmp = copy.copy(best_of_rtes[I])
                    temp_best = copy.copy(best_of_rtes)
                    temp_best[I:J] = copy.copy(best_of_rtes[I+1:J+1])
                    temp_best[J] = tmp
                    tmp_pop.append(temp_best)
                    
                elif idx == 4: #Create a totally new permuation
                    tmp_pop.append(randperm(num_stops))

        #####################################
        ###### End Randomizing and Mutating
        #####################################

        #Replace the old population with the new one one
        pop = tmp_pop 
        tmp_pop = []
        
    return flexbus, opt_rte, locations, new_trips, unstarted_trips, started_trips, new_trips_count, full_trips_count

@log_traceback
def optimize_static_route(second, trip_segment):
    """
    This function takes in a static trip_segment and a time then finds an optimal static itinerary for that trip.
    The various trip times are updated for this itinerary and the next trip segment is updated to reflect thetime that this trip will be over
    @param second : seconds into the simulation
    @param trip_segment : a TripSegment object for a static trip
    """
    if not trip_segment.static:
        print 'ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR'

    current_time = second + settings.SIMULATION_START_TIME
    hour = int(current_time/3600)
    minute = int((current_time - (hour*3600))/60)
    second = current_time - (minute*60) - (hour*3600)

    trip_time = datetime.datetime(year = settings.SIMULATION_START_YEAR, month = settings.SIMULATION_START_MONTH, day = settings.SIMULATION_START_DAY, hour = hour, minute = minute, second = second)
    walking_time, waiting_time, riding_time = planner_manager.get_optimal_transit_times([trip_segment.start_lat, trip_segment.start_lng], [trip_segment.end_lat, trip_segment.end_lng], trip_time)

    total_time = walking_time + waiting_time + riding_time

    trip_segment.status = 2
    trip_segment.start_time = second
    trip_segment.end_time = second + total_time
    trip_segment.walking_time = walking_time
    trip_segment.waiting_time = waiting_time
    trip_segment.riding_time = riding_time
    trip_segment.save()

    update_next_segment(trip_segment)
    
    return

@log_traceback    
def simple_optimize_route(second, trip, flexbus):
    """
    Simple Heuristic Algorithm Optimization Routine
    It works by not changing the order of any of the other passengers and inserting the passenger at each possible location for a single vehicle and them simply selecting the order with minimum cost.
    Given the current time and a bus, optimize the bus' route from the stops assigned to it.
    @param second : the time
    @param flexbus : a flexbus object
    Returns the order and cost
    """
    flexbus_lat, flexbus_lng, diff_time = get_flexbus_location(flexbus, second)

    previous_stops = models.Stop.objects.filter(flexbus = flexbus, visit_time__lt = second).order_by('visit_time')

    count = previous_stops.count() + 1

    future_stops = models.Stop.objects.filter(flexbus = flexbus, sequence__gte = count).order_by('visit_time')

    for stop in future_stops:
        stop.sequence += 1
        stop.save()

    this_stop =  models.Stop.objects.create(flexbus = flexbus, lat = flexbus_lat, lng = flexbus_lng, sequence = count, visit_time = second, type = 0, trip = None) 

    stop_array = [this_stop]
    lats_array = [flexbus_lat]
    lngs_array = [flexbus_lng]
    for stop in future_stops:
        stop_array.append(stop)
        lats_array.append(stop.lat)
        lngs_array.append(stop.lng)
   
    trip.status = 2
    trip.save()

    new_start = models.Stop.objects.create(flexbus = flexbus, lat = trip.start_lat, lng = trip.start_lng, sequence = -1, visit_time = -1, type = 1, trip = trip)
    new_end = models.Stop.objects.create(flexbus = flexbus, lat = trip.end_lat, lng = trip.end_lng, sequence = -1, visit_time = -1, type = 2, trip = trip)
    shortest_distance = 'inf'
    shortest_i = 0
    shortest_j = 1

    #Try every scenerio for entering the dropoff and pickup location without changing the rest of the order
    for i in range(1, len(lats_array) + 1):
        puinserted_lats = copy.copy(lats_array)
        puinserted_lngs = copy.copy(lngs_array)
        puinserted_lats.insert(i, trip.start_lat)
        puinserted_lngs.insert(i, trip.start_lng)

        for j in range(i + 1, len(puinserted_lngs) + 1):
            doinserted_lats = copy.copy(puinserted_lats)
            doinserted_lngs = copy.copy(puinserted_lngs)
            doinserted_lats.insert(j, trip.end_lat)
            doinserted_lngs.insert(j, trip.end_lng)
            doinserted_lats.append(flexbus.subnet.gateway.lat)
            doinserted_lngs.append(flexbus.subnet.gateway.lng)
            total_distance = get_distance_from_array(doinserted_lats, doinserted_lngs)
            if total_distance < shortest_distance:
                shortest_distance = copy.copy(total_distance)
                shortest_i = i
                shortest_j = j
                  
    lats_array.insert(shortest_i, trip.start_lat)
    lats_array.insert(shortest_j, trip.end_lat)
    lngs_array.insert(shortest_i, trip.start_lng)
    lngs_array.insert(shortest_j, trip.end_lng)
    stop_array.insert(shortest_i, new_start)
    stop_array.insert(shortest_j, new_end)

    return flexbus, stop_array

@log_traceback
def heuristic_optimize_route(second, flexbus):
    """
    This is a test method built for experimentation.  It will either be integrated with the other optimizaton options or it will be deleted before 'release'
    @param second : the time
    @param flexbus : a flexbus object
    Returns the order and cost
    """

    flexbus_lat, flexbus_lng, diff_time = get_flexbus_location(flexbus, second)

    #Get all the trips belonging to the bus
    trips = models.TripSegment.objects.filter(flexbus = flexbus)
    started_trips = trips.filter(start_time__lte = second, end_time__gt = second)
    unstarted_trips = trips.filter(earliest_start_time__lte = second, end_time__gt = second, start_time__gt = second)
    new_trips = trips.filter(earliest_start_time__lte = second, start_time = None)
    new_trips.update(status = 2)
                      

    #IF the fifth position is a 1, this location is a pickup, if it is a 2, it is a drop off, if it is a 0 it is the bus location or the depot
    #    [[stop1_time, stop1_lat, stop1_lng, stop1_trip_id, 1]
    locations = [[second, flexbus_lat, flexbus_lng, None, 0]]
    #Get the start and end locations associated with those trips

    for trip in unstarted_trips:
        locations.append([trip.start_time, trip.start_lat, trip.start_lng, trip.id, 1])
        locations.append([trip.end_time, trip.end_lat, trip.end_lng, trip.id, 2])

    for trip in started_trips:
        locations.append([trip.end_time, trip.end_lat, trip.end_lng, trip.id, 2])

    locations.sort()

    for trip in new_trips:

      lats_array = []
      lngs_array = []
      for idx in range(len(locations)):
        lats_array.append(locations[idx][1])
        lngs_array.append(locations[idx][2])

      shortest_distance = 'inf'
      shortest_i = 0
      shortest_j = 1

      #Try every scneario for entering the dropoff and pickup location without changing the rest of the order
      for i in range(len(locations) + 1):
          puinserted_lats = copy.copy(lats_array)
          puinserted_lngs = copy.copy(lngs_array)
          puinserted_lats.insert(i, trip.start_lat)
          puinserted_lngs.insert(i, trip.start_lng)

          for j in range(i + 1, len(puinserted_lngs) + 1):
              doinserted_lats = copy.copy(puinserted_lats)
              doinserted_lngs = copy.copy(puinserted_lngs)
              doinserted_lats.insert(j, trip.end_lat)
              doinserted_lngs.insert(j, trip.end_lng)
              doinserted_lats.append(flexbus.subnet.gateway.lat)
              doinserted_lngs.append(flexbus.subnet.gateway.lng)
              total_distance = get_distance_from_array(doinserted_lats, doinserted_lngs)
              if total_distance < shortest_distance:
                  shortest_distance = total_distance
                  shortest_i = i
                  shortest_j = j
                  
      locations.insert(shortest_i,[None, trip.start_lat, trip.end_lng, trip.id, 1])
      locations.insert(shortest_j,[None, trip.end_lat, trip.end_lng, trip.id, 2])

    return 0
        
#    return flexbus, opt_rte, locations, new_trips, unstarted_trips, started_trips, new_trips_count, full_trips_count

@log_traceback
def generate_statistics(request):
    """
    This function generates some final statistics for the previously run simulation.
    TODO: Move to a statistics file
    @param request : a simple get request to /generate_statics/
    @param httpresponse of a json object containing basic statistics information
    """
    #TODO: pass in a simulation_number
    total_flex_ride_time = []
    first_leg_time = []
    second_leg_time = []
    total_initial_wait = []
    total_xfer_wait = []
    total_distance = []
    first_leg_distance = []
    second_leg_distance = []

    passengers = models.Passenger.objects.all()
    for passenger in passengers:
        trips = models.TripSegment.objects.filter(passenger = passenger)
        passenger_total_ride_time = 0
        total_distance.append(utils.haversine_dist([passenger.start_lat, passenger.start_lng], [passenger.end_lat, passenger.end_lng]))
       
        for trip in trips:
            if trip.start_time:
                leg_time = trip.end_time - trip.start_time
                leg_distance = utils.haversine_dist([trip.start_lat, trip.start_lng], [trip.end_lat, trip.end_lng])
                passenger_total_ride_time += leg_time

                if trip.trip_sequence == 1:
                    first_trip = trip
                    passenger.time_waiting_initial = trip.start_time - trip.earliest_start_time
                    first_leg_time.append(leg_time)
                    first_leg_distance.append(float(leg_distance))
                    total_initial_wait.append(trip.start_time - trip.earliest_start_time)
                elif trip.trip_sequence == 2:
                    passenger.time_waiting_transfer = trip.start_time - trip.earliest_start_time
                    passenger.time_riding_static = trip.earliest_start_time - first_trip.end_time
                    second_leg_time.append(leg_time)
                    second_leg_distance.append(float(leg_distance))
                    total_xfer_wait.append(trip.start_time - trip.earliest_start_time)

        passenger.total_time = trip.end_time - passenger.time_of_request            
        passenger.save()
        total_flex_ride_time.append(passenger_total_ride_time)

    #######Print Stats############

    sum_total_flex_time = sum(total_flex_ride_time)
    sum_total_distance = sum(total_distance)

    sum_first_leg_time = sum(first_leg_time)
    sum_first_leg_distance = sum(first_leg_distance)
    sum_total_initial_wait = sum(total_initial_wait)
    sum_second_leg_time = sum(second_leg_time)
    sum_second_leg_distance = sum(second_leg_distance)
    sum_total_xfer_wait = sum(total_xfer_wait)

    total_passengers = str(passengers.count())
    print 'Total Number of Passengers:  ' + total_passengers
    avg_ride_time = str(float(sum_total_flex_time)/len(total_flex_ride_time))
    print 'Average Ride Time:  ' + avg_ride_time
    avg_total_distance = str(float(sum_total_distance)/(len(total_distance)))
    print 'Average Total Passenger Distance:  ' + avg_total_distance
    avg_flex_distance = str((float(sum_first_leg_distance) + float(sum_second_leg_distance))/len(first_leg_distance))
    print 'Average Flex Passenger Distance:  ' + avg_flex_distance
    avg_time_per_block = str((float(sum_total_flex_time)/len(total_flex_ride_time))/(float(sum_total_distance)/len(total_distance)))
    print 'Average Time per Block Distance:  ' + avg_time_per_block
    
    json_str = simplejson.dumps({"Total Passengers":str(passengers.count()), "Avg Ride Time":avg_ride_time, "Avg Total Distance":avg_total_distance, "Avg Time Per Block":avg_time_per_block})
    return HttpResponse(json_str)
