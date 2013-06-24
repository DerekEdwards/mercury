from django.utils import simplejson
from django.http import HttpResponse
from extra_utils.extra_shortcuts import render_response

from extra_utils.variety_utils import log_traceback

from NITS_CODE import settings
from hermes import models, passenger_manager
from hermes import load_gateways, particle_swarm_manager
import datetime

@log_traceback
def calc_headway():
    start = datetime.time(7,0)
    end = datetime.time(19,0)
    routes = models.Route.objects.all()

    good_routes = []
    total_trips = 0
    for route in routes:
        if route.short_name == '201':
            continue
        print route.short_name
        
        trips = models.Trip.objects.filter(route = route, service_id = 5)
        trips_count = 0
        for trip in trips:
            st = models.StopTime.objects.filter(trip = trip, stop_sequence = 1, departure_time__lte=end)
            if st.count() > 0:
                if st[0].arrival_time >= start and st[0].arrival_time < end:
                    trips_count += 1
                    total_trips += 1
        headway = 2*12*60.0/trips_count
        if headway <= 15:
            good_route = {}
            good_route['route'] = route.short_name
            good_route['headway'] = headway
            good_routes.append(good_route)
        print 'Headway:  ' + str(headway)
        print 'Trips Count:  ' + str(trips_count)
        print '-----------------'
                                         

    print 'Routes Count:  ' + str(routes.count())
    print 'Average Headway:  ' + str((2*12*60.0/total_trips)*routes.count())


    for gr in good_routes:
        print gr

    return good_routes

@log_traceback
def stops(request):
    return render_response(request, 'stops.html', {})

@log_traceback
def get_stops(request):
    routes = calc_headway()
    stops  = []
    for route in routes:
        print 'getting route info for  ' + route['route']
        rt = models.Route.objects.get(short_name = route['route'])
        trip = models.Trip.objects.filter(route = rt)[0]
        stoptimes = models.Shape.objects.filter(shape_id = trip.shape_id)
        for st in stoptimes:
            if not(st in stops):
                stops.append(st)
        
        #trip = models.Trip.objects.filter(route = rt, direction = 0)[1]
        #stoptimes = models.StopTime.objects.filter(trip = trip)
        #for st in stoptimes:
        #    if not(st in stops):
        #        stops.append(st)
    locs = []
    for stop in stops:
        locs.append([stop.lat, stop.lng])
        
    json_str = simplejson.dumps({"stops":locs})
    return HttpResponse(json_str)


from django.core.files import File

def write_trips():
    f = File(open('passenger_trips.csv', 'w'));
    passengers = models.Passenger.objects.all().order_by('id')
    f.write('passenger,est,st,et,fromlat,fromlng,tolat,tolng,walking,static \n')
    for passenger in passengers:
        trips = models.TripSegment.objects.filter(passenger = passenger).order_by('trip_sequence')
        passenger_string = str(passenger.id) 
        for trip in trips:
            #est, st, et, fromlat, fromlng, tolat, tolng, trip.walking, trip.static
            passenger_string += ',' + str(trip.earliest_start_time) + ',' + str(trip.start_time) + ',' + str(trip.end_time)
            passenger_string += ',' + str(trip.start_lat) + ',' + str(trip.start_lng) + ',' + str(trip.end_lat) + ',' + str(trip.end_lng)
            passenger_string += ',' + str(trip.static) + ',' + str(trip.walking)
            passenger_string += '\n'

        f.write(passenger_string)

    f.close()
