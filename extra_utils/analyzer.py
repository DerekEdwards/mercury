from hermes import models
from hermes import views
import time
import random, datetime


from googlemaps import GoogleMaps

    
gmaps = GoogleMaps('ABQIAAAAsn6aAGbw79H9E1JOWbQQjhSlVGwKjeu8iET79lxLMDKkElrCQBTD0ANguvwut7gCuc8I7Es8GyfDiQ')

def gmaps_driving(start, end):
    time.sleep(1)
    dirs = gmaps.directions((start[0], start[1]), (end[0],end[1]))
#    dirs.getPolyLine()
    total_seconds = 0
    if dirs:
        steps = dirs['Directions']['Routes'][0]['Steps']
        for step in steps:
            total_seconds += float( step['Duration']['seconds'])
            point = step['Point']['coordinates']
    print total_seconds
    return total_seconds


from math import sin, cos, pi, atan2, sqrt

EARTH_RADIUS = 6371000 #in meters
def haversine_dist(start, end):
    """
    Finds the straight line distance between two points in meters. 
    """
    dlat = to_rad(end[0] - start[0])
    dlon = to_rad(end[1] - start[1])

    tmp_dist = sin(dlat/2)*sin(dlat/2) + cos(to_rad(start[0]))*cos(to_rad(end[1]))*sin(dlon/2)*sin(dlon/2)
    tmp_dist = 2*atan2(sqrt(tmp_dist), sqrt(1-tmp_dist))
    tmp_dist *= EARTH_RADIUS
    return tmp_dist

def to_rad(deg):
    return deg*pi/180

def to_deg(rad):
    return rad*180/pi

def time_riding_static(passenger):
    trips = passenger.tripsegment_set.all().order_by('trip_sequence')
    if trips.count() > 1:
        return trips[1].earliest_start_time - trips[0].end_time
    else:
        return 0

#Print results for a passenger that is waling.
def walking_passenger(passenger):
    passenger_speed = 50 #seconds per block
    trips = passenger.tripsegment_set.all().order_by('trip_sequence')

    if trips.count() < 2:
        trip = trips[0]
        walking_time = views.get_distance(trip.start_lat, trip.start_lng, trip.end_lat, trip.end_lng)*passenger_speed
        riding_time = 0
        total_time = walking_time
    else:
        walking_time = 0
        for trip in trips:
            walking_time += views.get_distance(trip.start_lat, trip.start_lng, trip.end_lat, trip.end_lng)*passenger_speed
            
        initial_walking_time = views.get_distance(trips[0].start_lat, trips[0].start_lng, trips[0].end_lat, trips[0].end_lat)*passenger_speed
        reach_time, train1, train2 = views.route_planner_from_points(trips[0].end_lat, trips[0].end_lng, trips[1].start_lat, trips[1].start_lng, initial_walking_time + passenger.time_of_request)
        print 'Reach First Gateway Time:  ' + str(initial_walking_time + passenger.time_of_request)
        print 'Reach Second Gateway Time:  ' + str(reach_time)
        riding_time = reach_time - (initial_walking_time + passenger.time_of_request)
        total_time = walking_time + riding_time

    return walking_time, riding_time, total_time


def walking_passenger_more_trains(passenger):
    passenger_speed = 50
    trips = passenger.tripsegment_set.all().order_by('trip_sequence')
    if trips.count() < 2:
        trip = trips[0]
        walking_time = views.get_distance(trip.start_lat, trip.start_lng, trip.end_lat, trip.end_lng)*passenger_speed
        riding_time = 0
        total_time = walking_time

    else:
        dist_1 = min(passenger.start_lat%10, 10 - (passenger.start_lat%10)) + min(passenger.start_lng%10, 10 - (passenger.start_lng%10))
        dist_2 = min(passenger.end_lat%10, 10 - (passenger.end_lat%10)) + min(passenger.end_lng%10, 10 - (passenger.end_lng%10))
        total_time = (dist_1 + dist_2)*passenger_speed
#        riding_time =
    return total_time

def driving_passengers(passenger):
    passenger_speed = 7.5 #20mph
    return haversine_dist(passenger.start_lat, passenger.start_lng, passenger.end_lat, passenger.end_lng)*passenger_speed

def get_total_time(passenger):
    trips = passenger.tripsegment_set.all().order_by('trip_sequence')
    if trips.count() > 1:
        if trips[1].end_time < 50000:
            return trips[1].end_time - trips[0].earliest_start_time
        else:
            return -1
    else:
        return trips[0].end_time - trips[0].earliest_start_time
    
if __name__ == "__main__":

    print gmaps_driving((34.1, -84.2),(34.1,-84.3))

    SystemFlags = models.SystemFlags.objects.all()
    simulation_code = SystemFlags[0].simulation_code
    print 'Simulation Code:  ' + str(simulation_code)

    passengers = models.Passenger.objects.all()
#    passengers = models.Passenger.objects.filter(simulation_code = simulation_code)

    true_total_time = 0
    true_total_time_count = 0
    true_walking_time = 0
    true_extra_walking_time = 0
    true_passenger_distance = 0
    automobile_total_time = 0
    total_time  = 0
    fulfulled_requests = 0
    driving_time = 0
    print 'Passenger Count'
    print passengers.count()
    for passenger in passengers:
        trips = models.TripSegment.objects.filter(passenger = passenger)
        if trips[0].end_time > 9000:
            continue
        if trips.count() > 1:
            if trips[1].end_time > 9000:
                continue
        
        my_total = get_total_time(passenger)
        if not(my_total == -1):
            true_passenger_distance += haversine_dist([passenger.start_lat, passenger.start_lng], [passenger.end_lat, passenger.end_lng])
            #driving_time += gmaps_driving([passenger.start_lat, passenger.start_lng], [passenger.end_lat, passenger.end_lng])
            true_total_time += my_total
            true_total_time_count += 1
        
        trips = passenger.tripsegment_set.all().order_by('trip_sequence')

    true_passenger_distance = float(true_passenger_distance)
    print true_passenger_distance
    avg_dist = true_passenger_distance/true_total_time_count
    print 'Avt Distance Meters'
    print avg_dist
    avg_time = float(true_total_time)/true_total_time_count
    print 'Avg Time Minutes'
    print avg_time/60
    print avg_dist*3600/(avg_time)
#    print driving_time/true_total_time_count
