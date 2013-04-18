from django.utils import simplejson
from django.http import HttpResponse
from extra_utils.extra_shortcuts import render_response
from extra_utils.variety_utils import log_traceback


from hermes import models
from hermes import utils

def index(request):
    """
    Show the index map for the isochrone map
    @input request : a get request
    @return request response
    """
    return render_response(request, 'results.html', {})

def get_passenger_results(request):
    vehicle_id = int(request.GET['vehicle_id'])
    vehicle  = models.FlexBus.objects.get(vehicle_id = vehicle_id)
    
    trips = models.TripSegment.objects.filter(flexbus = vehicle)
    starts = []
    ends = []
    times = []
    for trip in trips:
        starts.append([trip.start_lat, trip.start_lng])
        ends.append([trip.end_lat, trip.end_lng])
        times.append(trip.end_time - trip.earliest_start_time)
    
    stop_array = []    
    stops = models.Stop.objects.filter(flexbus = vehicle).order_by('visit_time')
    for stop in stops:
        stop_array.append([stop.lat, stop.lng])

    json_str = simplejson.dumps({"starts":starts, "ends":ends, "times":times, "stops":stop_array})
    return HttpResponse(json_str)


def simple_passenger_results():
    passengers = models.Passenger.objects.all()
    for passenger in passengers:
        trips = passenger.tripsegment_set.all().order_by('trip_sequence')
        
        print 'Passenger:  ' + str(passenger.id)
        print 'Start:  ' + str(passenger.start_lat) + ',' + str(passenger.start_lng)
        print 'End:    ' + str(passenger.end_lat) + ',' + str(passenger.end_lng)

        arrival_time = trips[trips.count() - 1].end_time
        print 'Total Travel Time:  ' + str(arrival_time - passenger.time_of_request)
        print 'Total Distance:  ' + str(utils.haversine_dist([passenger.start_lat, passenger.start_lng], [passenger.end_lat, passenger.end_lng]))
      
        for trip in trips:
            print '-----Trip ' + str(trip.trip_sequence) + '-----' 
            print 'Start: ' + str(trip.start_lat) + ',' + str(trip.start_lng)
            print 'End: ' + str(trip.end_lat) + ',' + str(trip.end_lng)
            print 'Earliest Start Time:  ' + str(trip.earliest_start_time)
            print 'Start Time:  ' + str(trip.start_time)
            print 'End Time:  ' + str(trip.end_time)
            print 'Static?:  ' + str(trip.static)

        print '------------------------------------------------------------'
    
    print 'Total Passengers Created:  ' + str(passengers.count())

def flextrip_summary():
    trips = models.TripSegment.objects.filter(static = False)

    scheduled_trips = 0
    wait_time = 0
    ride_time = 0
    total_time = 0
    distance_traveled = 0
    
    for trip in trips:
        if trip.start_time:
            scheduled_trips += 1
            wait_time += trip.start_time - trip.earliest_start_time
            ride_time += trip.end_time - trip.start_time
            total_time += trip.end_time - trip.earliest_start_time
            distance_traveled += utils.haversine_dist([trip.start_lat, trip.start_lng], [trip.end_lat, trip.end_lng])

    print 'Total trips served:   ' + str(scheduled_trips)
    print 'Average total time:   ' + str(total_time/scheduled_trips)
    print 'Average ride time:    ' + str(ride_time/scheduled_trips)
    print 'Average wait time:    ' + str(wait_time/scheduled_trips)
    print 'Average distance (m): ' + str(distance_traveled/scheduled_trips)
    print 'Average speed (m/s):  ' + str(distance_traveled/total_time)
    print 'Average speed (mph):  ' + str(2.23694*distance_traveled/total_time)

def print_flexbus_picks_and_drops(flexbus):
    trips = models.TripSegment.objects.filter(flexbus = flexbus)
    for trip in trips:
        print str(trip.start_lat) + ',' + str(trip.start_lng)
        print str(trip.end_lat) + ',' + str(trip.end_lng)


def print_flexbus_path():
    flexbuses = models.FlexBus.objects.all()
    for flexbus in flexbuses:
        if flexbus.stop_set.count() > 0:
            stops = flexbus.stop_set.all().order_by('visit_time')
            
            print 'Total Stops by vehicle_id ' + str(flexbus.vehicle_id) +':  ' + str(stops.count())
            for stop in stops:
                print str(stop.lat) + ',' + str(stop.lng)
            print '----------------------------------------'    


def simple_flexbus_results():
    flexbuses =  models.FlexBus.objects.all()

    for flexbus in flexbuses:
        stops = flexbus.stop_set.all().order_by('sequence')
        if stops.count() > 0:
            print 'Flexbus Id:  ' + str(flexbus.id)
            print 'Flexbus Subnet:  ' + str(flexbus.subnet.description)
            for stop in stops:
                print '-----Stop:  ' + str(stop.sequence) + '-----'
                print str(stop.lat) + ',' + str(stop.lng)
                print 'Visit Time:  ' + str(stop.visit_time)
            print '-----------------------------------------------'


def printable_flexbus_results():
    flexbuses =  models.FlexBus.objects.all()

    for flexbus in flexbuses:
        stops = flexbus.stop_set.all().order_by('sequence')
        if stops.count() > 0:
            print 'Flexbus Id:  ' + str(flexbus.id)
            print 'Flexbus Subnet:  ' + str(flexbus.subnet.description)
            for stop in stops:
                print str(stop.lat) + ',' + str(stop.lng)
            print '-----------------------------------------------'

def summary_of_results():
    flexbuses = models.FlexBus.objects.all()
    VMT = 0
    vehicle_count = 0
    for flexbus in flexbuses:
        stops = flexbus.stop_set.all().order_by('sequence')
        if stops.count():
            vehicle_count += 1
            for idx in range(stops.count() - 1):
                VMT += utils.haversine_dist([stops[idx].lat, stops[idx].lng], [stops[idx+1].lat, stops[idx+1].lng])

    print 'Total VMT:  ' + str(VMT) + ' meters.'
    print 'Total Vehicles Used:  ' + str(vehicle_count)
 
            
    total_travel_time = 0
    total_p2p_distance= 0
    passengers = models.Passenger.objects.all()
    for passenger in passengers:
        trips = passenger.tripsegment_set.all().order_by('trip_sequence')
            
        arrival_time = trips[trips.count() - 1].end_time
        total_travel_time += (arrival_time - passenger.time_of_request)
        total_p2p_distance += (utils.haversine_dist([passenger.start_lat, passenger.start_lng], [passenger.end_lat, passenger.end_lng]))
        
    print 'Total Passengers Created:  ' + str(passengers.count())
    print 'Total Travel Time:  ' + str(total_travel_time)
    print 'Average Travel Time:  ' + str(total_travel_time/passengers.count())
    print 'Total Distance Traveled:  ' + str(total_p2p_distance)
    print 'Average Distance Traveled:  ' + str(total_p2p_distance/passengers.count())

    
