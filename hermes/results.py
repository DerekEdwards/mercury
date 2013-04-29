import os, datetime

from django.utils import simplejson
from django.http import HttpResponse
from extra_utils.extra_shortcuts import render_response
from extra_utils.variety_utils import log_traceback

from hermes import models, utils, views

def index(request):
    """
    Show the index map for the results map
    @input request : a get request
    @return request response
    """
    return render_response(request, 'results.html', {})

def show_summary(request):
    """
    Show the index map for the summary page
    @input request : a get request
    @return request response
    """
    return render_response(request, 'summary.html', {})

def show_survey_passengers(request):
    return render_response(request, 'survey.html', {})

@log_traceback
def get_summary_data(request):
    passengers = models.Passenger.objects.all()

    starts = []
    start_static = []
    ends  = []
    end_static = []
    for passenger in passengers:
        starts.append([passenger.start_lat, passenger.start_lng])
        ends.append([passenger.end_lat, passenger.end_lng])
        trips = models.TripSegment.objects.filter(passenger = passenger).order_by('trip_sequence')

        #For each location identify it this was a static or dymanic stop
        start_static.append(trips[0].static)
        end_static.append(trips[trips.count() - 1].static)
        
    passenger_count, average_distance_meters, average_time, average_speed_meters_per_second =  get_passenger_details()
    average_speed_mph = 2.23694*average_speed_meters_per_second

    VMT, vehicle_count, vehicle_avg_VMT = get_flexbus_details()
    json_str = simplejson.dumps({"starts":starts, "start_static":start_static, "ends":ends, "end_static":end_static, "VMT":VMT, "vehicle_count":vehicle_count, "vehicle_avg_VMT":vehicle_avg_VMT, "completed_passenger_count":passenger_count, "avg_distance":average_distance_meters, "avg_mph":average_speed_mph, "avg_time":average_time})
    return HttpResponse(json_str)

@log_traceback
def get_survey_data(request):
    passengers = models.SurveyPassenger.objects.all()

    starts = []
    ends  = []
    for passenger in passengers:
        starts.append([passenger.start_lat, passenger.start_lng])
        ends.append([passenger.end_lat, passenger.end_lng])
 

    json_str = simplejson.dumps({"starts":starts, "ends":ends})
    return HttpResponse(json_str)


@log_traceback
def show_live_map(request):
    "This gets the data for the big LIVE map of passenger and flexbus details"

    SystemFlags = models.SystemFlags.objects.all()
    SystemFlags = SystemFlags[0]
        
    vehicle_id = int(request.GET['vehicle_id'])
    vehicle  = models.FlexBus.objects.get(vehicle_id = vehicle_id)
    second = request.GET['second'] 
 
    if second == 'NOW':
        second = SystemFlags.second
    elif int(second) > SystemFlags.second:
        second = SystemFlags.second
    else:
        second = int(second)

    trips = models.TripSegment.objects.filter(flexbus = vehicle, earliest_start_time__lte = second).order_by('earliest_start_time')
    
    starts = []
    ends = []
    times = []
    for trip in trips:
        starts.append([trip.start_lat, trip.start_lng])
        ends.append([trip.end_lat, trip.end_lng])
        times.append([trip.earliest_start_time, trip.start_time, trip.end_time, trip.end_time - trip.earliest_start_time])
    
    stop_array = []    

    lat, lng, unused = views.get_flexbus_location(vehicle, second)

    flexbus_location = [lat, lng]
    
    json_str = simplejson.dumps({"starts":starts, "ends":ends, "times":times, "stops":stop_array, "flexbus_location":flexbus_location, "second":second})
    return HttpResponse(json_str)


def get_passenger_details():
    passengers = models.Passenger.objects.all()
    total_time  = 0.0
    total_distance  = 0.0
    completed_passenger_count = 0.0
    for passenger in passengers:
        trips = passenger.tripsegment_set.all().order_by('trip_sequence')
        if trips[trips.count() - 1].end_time > 24*3600: #This trip never ended, ignore this passenger, he's still en route
            print trips[trips.count()-1].static
            print trips[trips.count()-1].earliest_start_time
            print '-------------------------'
            continue
        completed_passenger_count += 1
        total_time += (trips[trips.count()-1].end_time - trips[0].earliest_start_time)
        total_distance += utils.haversine_dist([passenger.start_lat, passenger.start_lng], [passenger.end_lat, passenger.end_lng])

    avg_distance = total_distance/completed_passenger_count
    avg_time = total_time/completed_passenger_count
    avg_speed = avg_distance/avg_time

    return completed_passenger_count, avg_distance, avg_time, avg_speed

def flextrip_summary():
    trips = models.TripSegment.objects.filter()

    scheduled_trips = 0
    wait_time = 0
    ride_time = 0
    total_time = 0
    distance_traveled = 0
    
    for trip in trips:
       if trip.start_time and not(trip.static):
            scheduled_trips += 1
            wait_time += trip.start_time - trip.earliest_start_time
            ride_time += trip.end_time - trip.start_time
            total_time += trip.end_time - trip.earliest_start_time
            distance_traveled += utils.haversine_dist([trip.start_lat, trip.start_lng], [trip.end_lat, trip.end_lng])

    total_trips_served = scheduled_trips
    average_total_time  = total_time/scheduled_trips
    average_ride_time  = ride_time/scheduled_trips
    average_wait_time = wait_time/scheduled_trips
    average_distance_meters = distance_traveled/scheduled_trips
    average_speed_meters_per_second = distance_traveled/total_time
    average_speed_mph = (2.23694*distance_traveled/total_time)

    return scheduled_trips, average_distance_meters, average_speed_mph, average_total_time 
    
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

def get_flexbus_details():
    flexbuses = models.FlexBus.objects.all()
    VMT = 0
    vehicle_count = 0
    for flexbus in flexbuses:
        stops = flexbus.stop_set.all().order_by('sequence')
        if stops.count():
            vehicle_count += 1
            for idx in range(stops.count() - 1):
                VMT += utils.haversine_dist([stops[idx].lat, stops[idx].lng], [stops[idx+1].lat, stops[idx+1].lng])

    return VMT, vehicle_count, VMT/vehicle_count

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
    passengers_finished = 0
    passengers = models.Passenger.objects.all()
    for passenger in passengers:
        trips = passenger.tripsegment_set.all().order_by('trip_sequence')
        if trips[trips.count() -1].end_time < 10000:    
            passengers_finished += 1
            arrival_time = trips[trips.count() - 1].end_time
            total_travel_time += (arrival_time - passenger.time_of_request)
            total_p2p_distance += (utils.haversine_dist([passenger.start_lat, passenger.start_lng], [passenger.end_lat, passenger.end_lng]))
        
    print 'Total Passengers Created:  ' + str(passengers_finished)
    print 'Total Travel Time:  ' + str(total_travel_time)
    print 'Average Travel Time:  ' + str(total_travel_time/passengers.count())
    print 'Total Distance Traveled:  ' + str(total_p2p_distance)
    print 'Average Distance Traveled:  ' + str(total_p2p_distance/passengers.count())

@log_traceback
def save_data(request):
    """
    After a simulation is run, take dump of the db.
    TODO:  This functions contains some hardcoding that could be moved out.
    """
    gw = models.Gateway.objects.get(gateway_id = 8)
    subnet = models.Subnet.objects.get(gateway = gw)
    time = datetime.datetime.now()
    target_dir = '/home/derek/Code/results/'
    db_name = 'midtown_11thru2_driving_' + str(subnet.max_driving_time) + "_walking_" + str(subnet.max_walking_time) + '_' + str(time.date()) + '-' + str(time.time()) + '.sql'

    os.system("mysqldump -uroot -ppword NITS > " + target_dir + db_name)    
    
    subnet.max_driving_time += 120
    subnet.save()

    if subnet.max_driving_time < 901:
        json_str = simplejson.dumps({"result":True})
    else:
        json_str = simplejson.dumps({"result":False})

    return HttpResponse(json_str)
