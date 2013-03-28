from hermes import models
from hermes import utils

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

    
