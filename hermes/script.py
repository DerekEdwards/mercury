from extra_utils.variety_utils import log_traceback
from django.utils import simplejson
from django.http import HttpResponse

from hermes import models, views

@log_traceback
def insert_trip(request):
    """
    insert_trip reads in an array of trip ids, pulls those ids from the db an inserts them optimally
    TODO: Move this to VIEWS, there is no need for a separate file for this
    @param request contains a POST string parameter called 'trip_ids' of the form [id1, id2, id3] as well as the 'second' parameter
    """
    trip_ids = request.POST['trip_ids']

    #Remove the first and last characters (They are just brackets)
    trip_ids = trip_ids[1:-1]
    trip_ids = trip_ids.split(',');

    for idx in range(len(trip_ids)):
        if trip_ids[idx] == '': #No trips were returned, we have reached the end of the simulation
            json_str = simplejson.dumps({"success":True})
            return HttpResponse(json_str)
        trip_ids[idx] = int(trip_ids[idx])

    second = int(request.POST['second'])        
   
    for trip_id in trip_ids:
        print 'Inserting Trip:  ' + str(trip_id)
        trip = models.TripSegment.objects.get(id = trip_id)
        if trip.static:
            views.optimize_static_route(second, trip)
        else:
            flexbus, stop_array = views.insert_trip(second, trip)
            order = views.simple_convert_sequence_to_locations(flexbus, second, stop_array)

    json_str = simplejson.dumps({"success":True})
    return HttpResponse(json_str)

                    
