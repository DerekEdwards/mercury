import random, numpy, copy, urllib2, urllib, time, csv, datetime

from django.core.exceptions import ObjectDoesNotExist
from django.utils import simplejson
from django.http import HttpResponse
from extra_utils.variety_utils import log_traceback

from hermes import models, utils, planner_manager
from NITS_CODE import settings

@log_traceback
def create_trips(passenger, second):
    """
    Takes in a passenger.  Determines which buses can handle that passenger's trip.
    Create the trips or trip segments for the passenger with the correctly assigned busses
    @param passenger : passenger object seeking a vehicle
    @param second : the seconds count into the simulation
    """

    #if the passenger's origin and destination are within 5 minutes of each other, dDelete it!
    walking_time = planner_manager.get_optimal_walking_time([passenger.start_lat,passenger.start_lng], [passenger.end_lat, passenger.end_lng])
    if walking_time < 300:
        passenger.delete()
        return

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
        return

    if not start_buses and not end_buses: #This is a fully static trip
        if settings.CREATE_STATIC_TRIPS: #If we are tracking fully static trips, create the trip and store it in the db
            create_static_trip(passenger, [passenger.start_lat, passenger.start_lng], [passenger.end_lat, passenger.end_lng], trip_sequence = 0, earliest_start_time = second)
        else: #if we are not creating fully static trips, delete this passenger from consideration.
            passenger.delete()
        
    elif start_buses and (not end_buses): #The first leg is DRT, the rest of the trip is Static
        start_bus, end_bus = create_dynamic_trip(passenger, second, start_buses = start_buses, end_buses = None)
        create_static_trip(passenger, [start_bus.subnet.gateway.lat, start_bus.subnet.gateway.lng], [passenger.end_lat, passenger.end_lng], trip_sequence = 1)
    elif (not start_buses) and end_buses: #The final leg is DRT, the first portion is Static
        start_bus, end_bus = create_dynamic_trip(passenger, second, start_buses = None, end_buses = end_buses)
        create_static_trip(passenger, [passenger.start_lat, passenger.start_lng], [end_bus.subnet.gateway.lat, end_bus.subnet.gateway.lng], trip_sequence = 0, earliest_start_time = second)       
    else: #Both legs are DRT.
        start_bus, end_bus = create_dynamic_trip(passenger, second, start_buses, end_buses)
        if not (start_bus == end_bus):
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
        start_bus = which_bus(start_buses, passenger, second, True)
    if end_buses:
        end_bus = which_bus(end_buses, passenger, second, False)
    if not start_buses and not end_buses:
        return start_bus, end_bus

    if start_bus == end_bus:
        #If the two busses are the same bus, this can be handled by one bus without fixed transit
        #TODO: Try to make this happen if possible, instead of only checking to see if the same bus was chosen by accident
        models.TripSegment.objects.create(passenger = passenger, flexbus = start_bus, start_lat = passenger.start_lat, end_lat = passenger.end_lat, start_lng = passenger.start_lng, end_lng = passenger.end_lng, status = 1, earliest_start_time = second, trip_sequence = 0)
   
    elif start_buses and end_buses:
        models.TripSegment.objects.create(passenger = passenger, flexbus = start_bus, start_lat = passenger.start_lat, end_lat = start_bus.subnet.gateway.lat, start_lng = passenger.start_lng, end_lng = start_bus.subnet.gateway.lng, status = 1, earliest_start_time = second, trip_sequence = 0)
        models.TripSegment.objects.create(passenger = passenger, flexbus = None, start_lat = end_bus.subnet.gateway.lat, end_lat = passenger.end_lat, start_lng = end_bus.subnet.gateway.lng, end_lng = passenger.end_lng, status = 1, trip_sequence = 2)
    
    elif start_buses and (not end_buses):
        models.TripSegment.objects.create(passenger = passenger, flexbus = start_bus, start_lat = passenger.start_lat, end_lat = start_bus.subnet.gateway.lat, start_lng = passenger.start_lng, end_lng = start_bus.subnet.gateway.lng, status = 1, earliest_start_time = second, trip_sequence = 0)
    
    elif (not start_buses) and end_buses:
        models.TripSegment.objects.create(passenger = passenger, flexbus = None, start_lat = end_bus.subnet.gateway.lat, end_lat = passenger.end_lat, start_lng = end_bus.subnet.gateway.lng, end_lng = passenger.end_lng, status = 1, trip_sequence = 1)

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
    return simple_optimize_route(second, trip_segment, trip_segment.flexbus)

@log_traceback
def which_bus(busses, passenger, second, first_mile):
    """
    Takes in a query of buses and determines which one will be finished with its route first.
    If no routes are finished within 30 minutes.  A new bus is dispatched.
    @busses : a query of flexbus objects
    @first_mile : if this is the first mile of a trip this is true, if this is the last mile, then this is false
    @second : the seconds into the simulation
    @return : the bus with the shortest total trip
    """
    min_bus = None
    min_time = float('inf');
    min_cost = float('inf');

    for bus in busses:
        if first_mile:
            trip_geographic_mean  = find_geographic_average([[passenger.start_lat, passenger.start_lng], [bus.subnet.gateway.lat, bus.subnet.gateway.lng]])
        else:
            trip_geographic_mean  = find_geographic_average([[passenger.end_lat, passenger.end_lng], [bus.subnet.gateway.lat, bus.subnet.gateway.lng]])
  
        #Get the trips for each bus
        trips = models.TripSegment.objects.filter(flexbus = bus, end_time__gte = second, end_time__lt = 20000).order_by('-end_time')
        #If the bus has no trips, return this bus
        if trips.count() == 0:
            return bus

        #find geographic average of this bus's future stops
        stops = models.Stop.objects.filter(flexbus = bus, visit_time__gte = second)
        lat, lng, unused = get_flexbus_location(bus, second)
        points = [[lat,lng]]
        for stop in stops:
            points.append([stop.lat,stop.lng])
        geographic_mean = find_geographic_average(points)

        geographic_dist = utils.haversine_dist(trip_geographic_mean, geographic_mean)
        #If the bus has trips, save the trip which is scheduled to finish last.
        last_trip = trips[0]

        #Every kilometer away counts as a point and every two minutes that a vehicle is from finishing its current load is a point
        #this is a balance between geographic distance and time where every 2 minutes is the same as being a mile away.
        cost = geographic_dist/1000 + (last_trip.end_time - second)/120
        
        if cost < min_cost:
            min_cost = cost
            min_bus = bus

        #Check to find the min time, this will be used to see if the system needs an ew vehicle
        if (last_trip.end_time - second) < min_time:
            min_time = last_trip.end_time - second

    #If no bus is scheduld to be done in 15 minutes
    if min_time > 15*60:
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
def find_geographic_average(points):
    """
    This function takes in an array of points of the the form [[lat,lng], [lat,lng], ... ]
    The function finds the average lat and lng of all these points. It is used by the which_bus function has a heuristic method of finding a nearby bus without
    exhaustively searching every option for assigning a passenger
    @param points : array of points of the the form [[lat,lng], [lat,lng], ... ]
    @return : a lat,lng of the geographic center of these points
    """
    lats_avg = 0.0
    lngs_avg = 0.0
    index = 0
    
    for point in points:
        lats_avg += point[0]
        lngs_avg += point[1]
        index += 1
    
    return [lats_avg/index,lngs_avg/index]

@log_traceback
def get_candidate_vehicles_from_point_geofence(lat, lng):
    """
    This function takes in a point and returns the vehicles for every subnet geofence that this point lies within.  This is the set of vehicles that the passenger is eligible for. 
    TODO: If a subnet exists, but no buses are assigned to it.  This logic will not work.  consider revising.
    TODO:  In the future, gather any vehicles from subnets that touch any eligible subnet subnet.  This will allow for vehicles to travel between adjacent subnets.
    """
    subnets_in_range = []
    vehicles = []

    subnets = models.Subnet.objects.filter(active_in_study = True)
    for subnet in subnets:
        within, reason = within_coverage_area(lat, lng, subnet)
        if within:
            subnets_in_range.append(subnet)

    for subnet in subnets_in_range:
        subnet_vehicles = subnet.flexbus_set.all()
        for sv in subnet_vehicles:
            vehicles.append(sv)

    return vehicles
        

@log_traceback
def within_coverage_area(lat, lng, subnet):
    """
    The check list:
    1:  Are we within the geofence?
    2:  Is this partuclar subnet outside of a pocket? i.e., maybe the trip is within the geofecne but still more than the maximum time limit away
    3:  Are we outside the safe walking zone?
    4:  Is this subnet's gateway the closest gateway (optional) 
    
    Return False if any of these tests fail.

    @param lat : latitude of a passenger point
    @param lng : longitude of a passenger point
    @param subnet : a subnet object that we are testing this point agains
    @return : True if all tests pass, otherwise return false
    """

    #1 Check that we are within the larger geofence, this technically is not needed since we are double-checking the isochrone boundary in the next
    # test, but this is done bcause it is a very fast way to weed out illegal points without needing to do a static trip.  Also, if we are only 
    # concerned about the shape and not the driving time, this will still allow us to do that.
    if settings.CHECK_GEOFENCING:
        gw = subnet.gateway
        sides = models.FencePost.objects.filter(gateway = gw)
        if not point_within_geofence(lat,lng,sides):
            return False, 1


    #2 Check that we are not in a pocket, i.e. an area within the geofence but still beyond the maximum driving distance
    if settings.CHECK_DRIVING_TIME:
        geometry, distance, driving_time_to = planner_manager.get_optimal_vehicle_itinerary([lat,lng], [subnet.gateway.lat, subnet.gateway.lng])#To,From
        if driving_time_to > subnet.max_driving_time:
            return False, 2

        geometry, distance, driving_time_from = planner_manager.get_optimal_vehicle_itinerary([subnet.gateway.lat, subnet.gateway.lng], [lat,lng])#To,From
        if driving_time_from > subnet.max_driving_time:
            return False, 3

    #3 Check that we are not within the walking distance
    if settings.CHECK_WALKING_TIME:
        sns = models.Subnet.objects.all()
        for sn in sns:
            walking_time = planner_manager.get_optimal_walking_time([lat,lng], [sn.gateway.lat, sn.gateway.lng])
            if walking_time < subnet.max_walking_time:
                return False, 4

    #4 Check that this subnet's gateway is the closest gateway
    if settings.CHECK_OTHER_SUBNETS:
        subnets = models.Subnet.objects.all()
        for sn in subnets:
            if sn == subnet:
                continue
            geometry, distance, time_to = planner_manager.get_optimal_vehicle_itinerary([lat,lng], [sn.gateway.lat, sn.gateway.lng]) #TOLocation, FromLocation
            geometry, distance, time_from = planner_manager.get_optimal_vehicle_itinerary([sn.gateway.lat, sn.gateway.lng], [lat,lng]) #TOLocation, FromLocation
            if (time_to + time_from) < (driving_time_to + driving_time_from):
                return False, 5

    return True, None

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
def get_cost_from_array(i, j, stop_array, new_start, new_end, second):
    """
    This is the function that is used to to test the cost of assigning passengers in this particlar order.  It returns a float value for cost that combines both VMT and Passenger costs
    @param i : insertion point of the new_start location
    @param j : inesrtion point of the new_end location
    @param stop_array : the array of stops from the current location of the flexbus to the end of the route
    @param new_start : a stop object for the new pickup location
    @param new_end : a stop object for the new dropoff location
    @param second : time into the simulation
    @return the total combined operator and passenger costs
    """
    stop_array.insert(i, new_start)
    stop_array.insert(j, new_end)

    points = []
    for stop in stop_array:
        points.append([stop.lat, stop.lng])
        
    vmt = get_distance_from_array2(points)
    passenger_costs, time_array = get_total_passenger_costs(stop_array, second, i, j)
    
    return settings.ALPHA*vmt + settings.BETA*passenger_costs, time_array

@log_traceback
def get_total_passenger_costs(stops, second, i, j):
    """
    Given an array of stops.  Look at the stops that are drop offs, for each drop off determine the total time for this trip.  Sum all of the trip times
    @param points : an array of stops
    @param second : time into the simulation
    """
    points = []
    for stop in stops:
        points.append([stop.lat, stop.lng])

    total_time = second
    visit_times = [total_time]
    for index in range(len(points) - 1):
        geometry, distance, time =  planner_manager.get_optimal_vehicle_itinerary(points[index + 1], points[index]) #TOLocation, FromLocation
        if stops[index+1].type and time > 30: #for types 1 and 2, (i.e., these stops are drop offs or pickups, add 20 seconds for loading/unloading/uturning etc, the time>30 handles situations where we are not moving.  We shouldn't penalize for loading/unloading 20 seconds for every single passenger.
            time += 20
        total_time += time
        visit_times.append(total_time)

    index = 0
    total_passenger_time = 0
    #TODO: Take into account the initial wait of the passenger.  Meaning if we drop the passenger of to catch a train, but it is 20 min until the next train, the optimizer should know that
    for stop in stops:
        if stop.type == 2: #this is a dropoff
            end_time = visit_times[index]
            total_time_for_trip = end_time - stop.trip.earliest_start_time 
            total_passenger_time += total_time_for_trip
        index += 1

    return total_passenger_time, visit_times

@log_traceback
def get_distance_from_array2(points):
    """
    Given an array of lats and an array of lngs, find the total distance to travel the path
    @param points : an array of points of the form [lat,lng]
    @return the total physical distance to visit these points in the given order
    """
    distance = 0
    for index in range(len(points) - 1):
        distance += utils.haversine_dist(points[index], points[index+1])

    return distance


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
    The flexbus locations are estimated from open source routing machine
    @param flexbus : the bus we want to know the location of
    @param second : the time that we are concerned with
    @param flexbus_stops : optional paramter that prevents us from having to requery the bus' stops
    @return a triple representing the lat and lng of the vehicles as well as what percentage of the trip the bus has completed between he previous and next stops
    """
    if flexbus_stops == None:
        flexbus_stops = models.Stop.objects.filter(flexbus = flexbus).order_by('visit_time')

    next_stop = flexbus_stops.filter(visit_time__gt = second)
    last_stop = flexbus_stops.filter(visit_time__lte = second).order_by('-visit_time')

    if next_stop.count():
        next_stop = next_stop[0]
    else:
        if last_stop.count():
            return last_stop[0].lat, last_stop[0].lng, 0
        else:
            return flexbus.subnet.gateway.lat, flexbus.subnet.gateway.lng, 0

    if last_stop.count():
        last_stop = last_stop[0]
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
    
    #The flexbus is between two points that are a trivial distance apart
    if distance < 10: 
        return last_stop.lat, last_stop.lng, 0

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

    hours = int(current_time/3600)
    minutes = int((current_time - (hours*3600))/60)
    seconds = current_time - (minutes*60) - (hours*3600)
    
    trip_time = datetime.datetime(year = settings.SIMULATION_START_YEAR, month = settings.SIMULATION_START_MONTH, day = settings.SIMULATION_START_DAY, hour = hours, minute = minutes, second = seconds)
    
    walking_time, waiting_time, riding_time, initial_wait = planner_manager.get_optimal_transit_times([trip_segment.end_lat, trip_segment.end_lng], [trip_segment.start_lat, trip_segment.start_lng], trip_time)

    total_time = walking_time + waiting_time + riding_time

    trip_segment.status = 2
    trip_segment.start_time = second
    trip_segment.end_time = second + total_time
    trip_segment.walking_time = walking_time
    trip_segment.waiting_time = waiting_time
    trip_segment.riding_time = riding_time
    trip_segment.save()

    update_next_segment(trip_segment)
    
    return True 

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
    #If this trip is the final leg, it will not yet have a vehicle assigned.  Search for the optimal vehicle.
    #TODO:  This function will allow vehicles from other subnets to pickup the passenger even it the passenger is starting at a different Gateway
    if not flexbus:
        buses = get_candidate_vehicles_from_point_geofence(trip.start_lat, trip.start_lng)
        flexbus = which_bus(buses, trip.passenger, second, False)
        trip.flexbus = flexbus
        trip.save()
    

    previous_stops = models.Stop.objects.filter(flexbus = flexbus, visit_time__lt = second).order_by('visit_time')
    count = previous_stops.count() + 1
    future_stops = models.Stop.objects.filter(flexbus = flexbus, visit_time__gt = second).order_by('visit_time')

    this_stop = models.Stop.objects.filter(flexbus = flexbus, visit_time = second)
    if this_stop.count() > 0:
        this_stop = this_stop[0]
        count = this_stop.sequence
    else:
        flexbus_lat, flexbus_lng, diff_time = get_flexbus_location(flexbus, second)
        this_stop =  models.Stop.objects.create(flexbus = flexbus, visit_time = second, lat = flexbus_lat, lng = flexbus_lng, sequence = count, type = 0, trip = None)
        for stop in future_stops:
            stop.sequence += 1
            stop.save()

    import pdb
    #pdb.set_trace()


    stop_array = [this_stop]
    for stop in future_stops:
        stop_array.append(stop)
   
    trip.status = 2
    trip.save()

    new_start = models.Stop.objects.create(flexbus = flexbus, lat = trip.start_lat, lng = trip.start_lng, sequence = -1, visit_time = -1, type = 1, trip = trip)
    new_end = models.Stop.objects.create(flexbus = flexbus, lat = trip.end_lat, lng = trip.end_lng, sequence = -1, visit_time = -1, type = 2, trip = trip)
    shortest_distance = 'inf'
    shortest_i = 0
    shortest_j = 1
    min_time_array  = None

    #Try every scenerio for entering the dropoff and pickup location without changing the rest of the order
    for i in range(1, len(stop_array) + 1):
        for j in range(i + 1, len(stop_array) + 2):
            total_distance, time_array = get_cost_from_array(i, j, copy.copy(stop_array), new_start, new_end, second)
            #total_distance = get_distance_from_array(doinserted_lats, doinserted_lngs)
            if total_distance < shortest_distance:
                shortest_distance = copy.copy(total_distance)
                shortest_i = i
                shortest_j = j
                min_time_array = time_array

    import pdb
    #pdb.set_trace()

    stop_array.insert(shortest_i, new_start)
    stop_array.insert(shortest_j, new_end)

    index = 0
    for stop in stop_array:
        stop.visit_time = min_time_array[index]
        stop.save()
        index += 1

    update_trips(flexbus, second)

    return flexbus, stop_array

@log_traceback
def update_trips(flexbus, second):
    """
    Update all the trips assigned to this bus with respect to changes made at this second.
    @param flexbus : the flexbus that just had a trip added
    @param second : simulation time
    """
    trips = models.TripSegment.objects.filter(flexbus = flexbus, earliest_start_time__lte=second, end_time__gte=second)
    for trip in trips:
        update_trip_details(trip, second)

@log_traceback
def update_trip_details(trip, second):
    """
    Update the details for given trip at this second.  Also update any future legs of this trip
    @param trip : the trip that needs to be updated
    @param second : simulation time
    """
    stops = models.Stop.objects.filter(trip = trip, visit_time__gte = second)
    for stop in stops:
        if stop.type == 1:
            trip.start_time = stop.visit_time
        elif stop.type == 2:
            trip.end_time = stop.visit_time
        trip.save()
    
    update_next_segment(trip)        

    return

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
