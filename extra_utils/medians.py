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
    subnets = models.Subnet.objects.all()[5:15]
    for subnet in subnets:
        busses = models.FlexBus.objects.filter(subnet = subnet)
        print subnet.description
        print 'Total Busses Used:  ' + str(busses.count())
        trip_time = 0.0
        trip_ride_time = 0.0
        total_trips = 0
        trips_array  = []
        for bus in busses:
            trips = models.TripSegment.objects.filter(flexbus = bus) 
            total_trips += trips.count()
            for trip in trips:
                if trip.end_time < 9000:
                    trip_time = (trip.end_time - trip.earliest_start_time)
                    trips_array.append([trip_time,trip])

        trips_array.sort()
        median_trip = trips_array[(len(trips_array)/2)]
        if analyzer.get_total_time(median_trip[1].passenger) == -1:
            median_trip = trips_array[(len(trips_array)/2) - 1]
        print subnet.description
        print median_trip[0]
        print 'Passenger Id'
        print median_trip[1].passenger.id
        print 'total time'
        print analyzer.get_total_time(median_trip[1].passenger)
        print str(median_trip[1].passenger.start_lat) + ',' + str(median_trip[1].passenger.start_lng) 
        print str(median_trip[1].passenger.end_lat) + ',' + str(median_trip[1].passenger.end_lng)
        print '----------------------------------'
