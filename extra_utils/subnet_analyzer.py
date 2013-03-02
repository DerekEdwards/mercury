from NITS.hermes import models
from NITS.hermes import views
from NITS.hermes import analyzer
import random, datetime

if __name__ == "__main__":


    SystemFlags = models.SystemFlags.objects.all()
    simulation_code = SystemFlags[0].simulation_code
    worst_subnets = []
    for i in range(10):
        worst_subnets.append(0)
    all_times  = []   
    worst_average = 0
    worst_vehicle = None
    subnets = models.Subnet.objects.all()
    for subnet in subnets:
        busses = models.FlexBus.objects.filter(subnet = subnet)
        print subnet.description
        print 'Total Busses Used:  ' + str(busses.count())
        trip_time = 0.0
        trip_ride_time = 0.0
        total_trips = 0
        for bus in busses:
            trips = models.TripSegment.objects.filter(flexbus = bus) 
            total_trips += trips.count()
            for trip in trips:
                if trip.end_time < 9000:
                    trip_time += (trip.end_time - trip.earliest_start_time)
                    trip_ride_time += (trip.end_time - trip.start_time)
        average_trip_time = trip_time/total_trips
        all_times.append([average_trip_time,subnet.description, total_trips])
        if average_trip_time > worst_subnets[9]:
            worst_subnets[9] = average_trip_time
            worst_subnets.sort(reverse=True)
        if average_trip_time > worst_average:
            worst_average = average_trip_time
            worst_subnet = subnet
        print 'Average Trip Time:  ' + str(average_trip_time)
        print 'Average Ride Time:  ' + str(trip_ride_time/total_trips)
        print 'Total Trips Served:  ' + str(total_trips)
        print '-------------------------------------------------------'
    print worst_subnets
    all_times.sort(reverse = True)
#    print all_times
#    for time in all_times:
#        print time
    
    print 'Worst Bus is from Subnet:  ' + worst_subnet.description
    print '.....its average trip time was:  ' + str(worst_average)

    print "Now performing extra analysis on worst subnet==============="

    busses = models.FlexBus.objects.filter(subnet = worst_subnet)
    print worst_subnet.description + ' used ' + str(busses.count()) + ' buses.'
    print 'The id of this subnet is:  ' + str(worst_subnet.subnet_id)
"""    
    for bus in busses:
        trips = models.TripSegment.objects.filter(flexbus = bus)

        print 'The Distance between each of these trips locations from the gateway in meters'
        for trip in trips:
            start_distance = analyzer.haversine_dist([trip.start_lat, trip.start_lng], [worst_subnet.gateway.lat, worst_subnet.gateway.lng])
            end_distance = analyzer.haversine_dist([trip.end_lat, trip.end_lng], [worst_subnet.gateway.lat, worst_subnet.gateway.lng])
            print 'Distance to start:  ' + str(start_distance) + ',   Distance to end:  ' + str(end_distance)
            if start_distance > 2000:
                print str(trip.start_lat) + ',' + str(trip.start_lng)
            if end_distance > 2000:
                print str(trip.end_lat) + ',' + str(trip.end_lng)
            
"""
