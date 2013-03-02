from NITS.hermes import models
from NITS.hermes import views
from NITS.hermes import analyzer
import random, datetime
import copy

if __name__ == "__main__":

    SystemFlags = models.SystemFlags.objects.all()
    simulation_code = SystemFlags[0].simulation_code
    print 'Simulation Code:  ' + str(simulation_code)

    busses = models.FlexBus.objects.all().order_by('vehicle_id')
    total_bus_distance = 0.0

    for bus in busses:
        stops = models.Stop.objects.filter(flexbus = bus).order_by('sequence')
        last_stop_lat = bus.subnet.gateway.lat
        last_stop_lng = bus.subnet.gateway.lng
        
        bus_distance =  0.0
        for stop in stops:
            print str(last_stop_lat) + ',' + str(last_stop_lng)
            bus_distance += analyzer.haversine_dist([last_stop_lat, last_stop_lng], [stop.lat, stop.lng])
            last_stop_lat = copy.copy(stop.lat)
            last_stop_lng = copy.copy(stop.lng)
            
        total_bus_distance += bus_distance       

        trips = bus.tripsegment_set.all()
        
        print 'Bus ' + str(bus.vehicle_id) + ' distance:  ' + str(bus_distance)
        print '.....total number of stops:  ' + str(stops.count())
        print '.....total number of trips:  ' + str(trips.count())
        print '-------------------------------------------------------------'

    print 'Bus Count:  ' + str(busses.count())
    print 'Total Bus Distance:  ' + str(total_bus_distance)
