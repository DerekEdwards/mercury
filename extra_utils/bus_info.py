from hermes import models

flexbus = models.FlexBus.objects.get(vehicle_id = 1)
print flexbus.subnet.description
stops = models.Stop.objects.filter(flexbus = flexbus).order_by('sequence')

trips = models.TripSegment.objects.filter(flexbus = flexbus)
for trip in trips:
    print str(trip.start_lat) + ',' + str(trip.start_lng) + ' ----> ' + str(trip.end_lat) + ',' + str(trip.end_lng) + '   EST:  ' + str(trip.earliest_start_time) + '    ST:  ' + str(trip.start_time) + '   ET:  ' + str(trip.end_time)

for stop in stops:
    print str(stop.sequence) + '    ' + str(stop.visit_time) + '    ' + str(stop.lat) + ',' + str(stop.lng)


fbs = models.FlexBus.objects.all()
for fb in fbs:
    trips = models.TripSegment.objects.filter(flexbus = fb).count()
    print 'Flexbus ' + str(fb.vehicle_id) + ' has ' + str(trips) + ' trips assigned.  SUBNET:  ' + str(fb.subnet.description)

"""



flexbuses = models.FlexBus.objects.all()
bus1 = flexbuses[0]
bus2 = flexbuses[20]

print bus1.gateway_lat
print bus1.gateway_lng
print bus2.gateway_lat
print bus2.gateway_lng

from hermes import views
print views.route_planner(bus1, bus2, 45)
"""
