import datetime
from time import time
from cxze.tracad import trac_utils, models, gps_views
from utils.variety_utils import log_traceback

@log_traceback
def update_gps_pos(routes_values):
    """
    Takes in the array of information delivered from marta_crawl and updates the vanmultrack and newest vantrack in gps_pos_mult_generic
    @param routes_values - array of data for each bus that contains, lat, lng, route short name, adherence, route description, bus_id,  and timestamp, 
    """
    for route_values in routes_values:
        for route in route_values:
            bus_values = route_values[route]
            route = models.Route.objects.get(short_name = route)

            for bus_value in bus_values:
                #Unpack the string that is the lng and lat
                latitude = str(bus_value[0])
                latitude = latitude[0] + latitude[1] + '.' + latitude[2] + latitude[3] + latitude[4] + latitude[5] + latitude[6] + latitude[7]
                longitude = str(bus_value[1])
                longitude = longitude[0] + longitude[1] +  longitude[2] + '.'  +  longitude[3] +  longitude[4] +  longitude[5] +  longitude[6] +  longitude[7] +  longitude[8]
                now = datetime.datetime.now()

                #Unpack Marta Time
                msg_time = bus_value[5]
                year = int(msg_time[0:4])
                month = int(msg_time[5:7])
                day = int(msg_time[8:10])
                hour = int(msg_time[11:13])
                minute = int(msg_time[14:16])
                second = int(msg_time[17:19])
                report_time = datetime.datetime(year, month, day, hour, minute, second)

                #Unpack Route_ID
                block_abbr = bus_value[3]
                route_id = block_abbr.split('-')
                route_id = int(route_id[0])

                adherence = int(bus_value[4])
                #####################
                ##Convert AVL trip into a GTFS trip
                ######################

                service_id = trac_utils.get_service_id(report_time)
                #Get the avl trip
                avl_trip = models.avl_trip.objects.filter(block_abbr = block_abbr, service_id = service_id)
                if avl_trip.count() < 1:
                    continue 
                #Get the block for the AVL Trip
                avl_block_id = avl_trip[0].block_id

                #Using the mapping, get all mapppings between the AVL and GTFS block
                block_id = models.gtfs_avl_map.objects.filter(avl_block_id = avl_block_id)[:1]

                if block_id.count() < 1:
                    continue

                #This is the GTFS block
                block_id = block_id[0].block_id

                ###################
                #This takes an adherence, report_time, and  block id and find the correspond trip
                #TODO: This line sometimes takes 15 seconds for a single trip, look into other solutions.
                
                cur_trip = get_cur_trip(block_id, adherence, report_time)
                if not(cur_trip):
                    continue

                #########################
                cur_route = models.Route.objects.get(short_name = route_id)
                vehicle_id = bus_value[2]
                vehicle, created = models.Vehicle.objects.get_or_create(vehicle_id = vehicle_id)
                vehicle.cur_route_trip = cur_trip
                vehicle.save()
                gps_views.update_gps_position(vehicle, report_time, adherence, latitude, longitude)

@log_traceback
def get_cur_trip(block_id, adherence, report_time):

    adherence = datetime.timedelta(0,adherence*60)
    adjusted_time = adherence + report_time
    adjusted_time = datetime.time(adjusted_time.hour, adjusted_time.minute, adjusted_time.second)

    trips = models.RouteTrip.objects.filter(block_id = block_id).values_list('id')
    stoptimes = models.StopTime.objects.filter(trip__id__in = trips, departure_time__gte = adjusted_time).order_by('departure_time')[:1]
    trip = None
    stoptime = None
    if len(stoptimes) > 0:
        stoptime = stoptimes[0]
        trip = stoptimes[0].trip
        
    return trip


