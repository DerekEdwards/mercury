from NITS.hermes import models
from NITS.hermes import views
from NITS.hermes import analyzer
import random, datetime

if __name__ == "__main__":

    SystemFlags = models.SystemFlags.objects.all()
    simulation_code = SystemFlags[0].simulation_code

    passengers = models.Passenger.objects.all()
    for passenger in passengers:
        total_time = analyzer.get_total_time(passenger)
        if total_time >= 0:
            trips = passenger.tripsegment_set.all().order_by('trip_sequence')
            
            print 'Passenger:  ' + str(passenger.id)
            print 'Start:  ' + str(passenger.start_lat) + ',' + str(passenger.start_lng)
            if trips.count() > 0:
                print 'Origin Station:  ' + trips[0].flexbus.subnet.description 
            else:
                print 'No Trips Created'
            print 'End:    ' + str(passenger.end_lat) + ',' + str(passenger.end_lng)
            if trips.count() > 1:
                print 'Destination Station:  ' + trips[1].flexbus.subnet.description 
            print 'Total Time: ' + str(float(total_time)/60)
            print 'Time Riding Static:  ' + str(float(analyzer.time_riding_static(passenger))/60)
            print '------------------------------------------------------------'

    print 'Total Passengers Created:  ' + str(passengers.count())
