import os, datetime, copy

from django.utils import simplejson
from django.http import HttpResponse
from extra_utils.extra_shortcuts import render_response
from extra_utils.variety_utils import log_traceback
from django.core.exceptions import ObjectDoesNotExist

from hermes import models, utils, views, planner_manager, particle_swarm_manager
from NITS_CODE import settings

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
def show_survey_colors(request):
    return render_response(request, 'colors.html', {})

@log_traceback
def get_summary_data(request):
    starts, start_static, ends, end_static, VMT, vehicle_count, vehicle_avg_VMT, passenger_count, average_distance_meters, average_speed_mph, average_time, h_static_time = get_summary_data_generic()

    json_str = simplejson.dumps({"starts":starts, "start_static":start_static, "ends":ends, "end_static":end_static, "VMT":VMT, "vehicle_count":vehicle_count, "vehicle_avg_VMT":vehicle_avg_VMT, "completed_passenger_count":passenger_count, "avg_distance":average_distance_meters, "avg_mph":average_speed_mph, "avg_time":average_time,"h_static_time":h_static_time})
    return HttpResponse(json_str)


def get_summary_data_generic():
    
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
        
    passenger_count, average_distance_meters, average_time, average_speed_meters_per_second, h_static_time, total_time, walking_time, hypothetical_static_time, hwalk =  get_passenger_details()
    average_speed_mph = 2.23694*average_speed_meters_per_second

    VMT, vehicle_count, vehicle_avg_VMT, total_vehicle_cost = get_flexbus_details()
    
    return starts, start_static, ends, end_static, VMT, vehicle_count, vehicle_avg_VMT, passenger_count, average_distance_meters, average_speed_mph, average_time, h_static_time
    

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
def get_survey_colors(request):

    passengers = models.SurveyPassenger.objects.all().order_by('survey_id')
    pmin = int(request.GET['id'])
    pmax = pmin + 1000
    passengers = passengers[pmin:pmax]
    subnets = models.Subnet.objects.all()

    starts = []
    start_colors = []
    ends  = []
    end_colors = []

    index = 0
    for passenger in passengers:
        index += 1
        print index
        if index % 10: # we don't have to do every passenger, just a sampling
            continue
        closest_subnet = None
        min_distance = float('inf')
        for sn in subnets:        
            geometry, distance, time_to = planner_manager.get_optimal_vehicle_itinerary([passenger.start_lat,passenger.start_lng], [sn.gateway.lat, sn.gateway.lng])
            geometry, distance, time_from = planner_manager.get_optimal_vehicle_itinerary([sn.gateway.lat, sn.gateway.lng],[passenger.start_lat,passenger.start_lng])
            if (time_to + time_from) < min_distance:
                min_distance = (time_to + time_from)
                closest_subnet = sn
        starts.append([passenger.start_lat, passenger.start_lng])
        start_colors.append(closest_subnet.subnet_id)


        closest_subnet = None
        min_distance = float('inf')
        for sn in subnets:        
            geometry, distance, time_to = planner_manager.get_optimal_vehicle_itinerary([passenger.end_lat,passenger.end_lng], [sn.gateway.lat, sn.gateway.lng])
            geometry, distance, time_from = planner_manager.get_optimal_vehicle_itinerary([sn.gateway.lat, sn.gateway.lng],[passenger.end_lat,passenger.end_lng])
            if (time_to + time_from) < min_distance:
                min_distance = (time_to + time_from)
                closest_subnet = sn
        ends.append([passenger.end_lat, passenger.end_lng])
        end_colors.append(closest_subnet.subnet_id)

    json_str = simplejson.dumps({"starts":starts, "ends":ends, "start_colors":start_colors, "end_colors":end_colors})
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
    
    json_str = simplejson.dumps({"starts":starts, "ends":ends, "times":times, "stops":stop_array, "flexbus_location":flexbus_location, "second":second, "max_driving_time":vehicle.subnet.max_driving_time, "max_walking_time":vehicle.subnet.max_walking_time})
    return HttpResponse(json_str)

@log_traceback
def get_passenger_details():
    passengers = models.Passenger.objects.all()
    total_time  = 0.0
    total_distance  = 0.0
    completed_passenger_count = 0.0
    hypothetical_static_time = 0.0
    walking_time = 0.0
    static_walking_time = 0.0
    for passenger in passengers:
        trips = passenger.tripsegment_set.all().order_by('trip_sequence')
        if trips[trips.count() - 1].end_time > 24*3600: #This trip never ended, ignore this passenger, he's still en route
            print trips[trips.count()-1].static
            print trips[trips.count()-1].earliest_start_time
            print '-------------------------'
            continue
        completed_passenger_count += 1
        passenger_total_time = (trips[trips.count()-1].end_time - trips[0].earliest_start_time)
        total_time += passenger_total_time
        total_distance += utils.haversine_dist([passenger.start_lat, passenger.start_lng], [passenger.end_lat, passenger.end_lng])
        for trip in trips:
            if trip.walking:
                print 'Walking Time:  ' + str(walking_time)
                walking_time += trip.end_time - trip.start_time
            if trip.static:
                walking_time += trip.walking_time

        #hypothetical transit trip for comparison
        current_time = passenger.time_of_request + settings.SIMULATION_START_TIME
        hours = int(current_time/3600)
        minutes = int((current_time - (hours*3600))/60)
        seconds = current_time - (minutes*60) - (hours*3600)
        trip_time = datetime.datetime(year = settings.SIMULATION_START_YEAR, month = settings.SIMULATION_START_MONTH, day = settings.SIMULATION_START_DAY, hour = hours, minute = minutes, second = seconds)
        hwalk, hwait, hride, hunused = planner_manager.get_optimal_transit_times([passenger.end_lat, passenger.end_lng], [passenger.start_lat, passenger.start_lng], trip_time)
        print str(passenger.start_lat) + ',' + str(passenger.start_lng)
        print str(passenger.end_lat) + ',' + str(passenger.end_lng)
        print hwalk, hwait, hride
        print passenger_total_time, trips[0].earliest_start_time - trips[0].end_time, trips[0].walking
        
        print '&&&&&'
        if (hwalk + hwait + hride == False):
            print 'THIS SHOULD NEVER SHOW UP'
        hypothetical_static_time += (hwalk + hwait + hride)
        static_walking_time += hwalk

    avg_distance = total_distance/completed_passenger_count
    avg_time = total_time/completed_passenger_count
    avg_speed = avg_distance/avg_time
    h_static_time = hypothetical_static_time/completed_passenger_count

    return completed_passenger_count, avg_distance, avg_time, avg_speed, h_static_time, total_time, walking_time, hypothetical_static_time, static_walking_time

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
    total_vehicle_cost = 0
    for flexbus in flexbuses:
        stops = flexbus.stop_set.all().order_by('visit_time')
        vehicle_VMT = 0
        if stops.count():
            vehicle_count += 1
            for idx in range(stops.count() - 1):
                point_VMT = utils.haversine_dist([stops[idx].lat, stops[idx].lng], [stops[idx+1].lat, stops[idx+1].lng])
                vehicle_VMT += point_VMT
                VMT += point_VMT
            time = settings.SIMULATION_LENGTH - stops[0].visit_time
            time_cost = time*(125.0/3600)
            print time_cost
            mileage_cost = settings.DRT_CPM*vehicle_VMT
            print mileage_cost
            print '-----'
            vehicle_cost = max(time_cost, mileage_cost) 
            
            total_vehicle_cost += vehicle_cost

    if vehicle_count == 0:
        vmt_per_vehicle = 0
    else:
        vmt_per_vehicle = VMT/vehicle_count

        
    return VMT, vehicle_count, vmt_per_vehicle, total_vehicle_cost

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
def save_data_status(request):
    """
    A request objects passes in a simulation code.
    If a simulation_result object exists for this code, return true, else return false
    """
    simulation_code = int(request.GET['simulation_code'])
    print simulation_code
    try:
        simulation_result = models.SimulationResult.objects.get(simulation_code = simulation_code)
        result = True
    except ObjectDoesNotExist:
        result = False
        json_str = simplejson.dumps({"result":result})
        return HttpResponse(json_str)

    json_str = simplejson.dumps({"result":True})
    return HttpResponse(json_str)


@log_traceback
def save_data(request):
    """
    After a simulation is run, take dump of the db.
    TODO:  This functions contains some hardcoding that should be moved out.
    """
    
    SystemFlags = models.SystemFlags.objects.all()
    SystemFlags = SystemFlags[0]
    saving_data = SystemFlags.saving_data
    if saving_data:
        json_str = simplejson.dumps({"result":False, "finished":False})
        return HttpResponse(json_str)
    else:
        SystemFlags.saving_data = True 
        SystemFlags.save()
        
    gw = models.Gateway.objects.get(gateway_id = 8)
    subnet = models.Subnet.objects.get(gateway = gw)
    time = datetime.datetime.now()
    total_passengers = models.Passenger.objects.all()

    description = 'RADIUS2_SMPL_MTOWN_W3_WEEKDAY_d_' + str(subnet.max_driving_time) + "_w_" + str(subnet.max_walking_time) + '_' + str(time.date()) + '-' + str(time.time()) 

    ###Dump the DB
    target_dir = '/home/derek/Code/results/'
    os.system("mysqldump -uroot -ppword temp > " + target_dir + description + ".sql")    
    print 'db dumped'
    ###Create a SimulationResult entry
    #Meta Data
    print 'creating a sim entry'
    sim_results = models.SimulationResult(description = description)
    sim_results.timestamp = time
    sim_results.simulation_code = SystemFlags.simulation_code
    sim_results.simulation_set = SystemFlags.simulation_set

    #Passenger Data
    print 'getting that passenger data'
    completed_passenger_count, avg_distance, avg_time, avg_speed, h_avg_static_time, total_time, walking_time, hypothetical_static_time, hwalk = get_passenger_details()
    sim_results.started_trips = total_passengers.count()
    sim_results.completed_trips = completed_passenger_count
    sim_results.DRT_time_avg = avg_time
    sim_results.FRT_time_avg = h_avg_static_time
    sim_results.average_distance = avg_distance
    sim_results.DRT_walking_total = walking_time
    sim_results.FRT_walking_total = hwalk

    #Vehicle Data
    print 'getting vehicle data'
    VMT, vehicle_count, vehicle_avg_VMT, total_vehicle_cost = get_flexbus_details()
    FRT_VMT, trips_served = static_vmt_within_zone(5) #get static vehicle details for service id 5
    sim_results.total_DRT_VMT  = VMT
    sim_results.total_FRT_VMT_saved = FRT_VMT
    sim_results.total_DRT_vehicles_used = vehicle_count 
    sim_results.total_DRT_cost = total_vehicle_cost

    #Total Cost
    print 'saving the total cost'
    #This adds
    sim_results.total_net_cost = settings.PASSENGER_VOT*completed_passenger_count*(avg_time - h_avg_static_time) + settings.PASSENGER_VOT*2*(walking_time - hwalk) + (total_vehicle_cost - settings.FRT_CPM*FRT_VMT) 
        

    print 'updating the PSO'
    ###Updates the simulation parameters and decides whether to run it again
    if settings.USE_PSO:
        particle = particle_swarm_manager.get_current_particle()
        particle_swarm_manager.update_particle(particle, sim_results.total_net_cost)
        next_particle = particle_swarm_manager.get_current_particle()
        if next_particle.step < 6:
            subnet.max_driving_time = next_particle.x1
            subnet.max_walking_time = next_particle.x2
            subnet.save()
            json_str = simplejson.dumps({"result":True})
        else:
            json_str = simplejson.dumps({"result":False, "finished":True})
        SystemFlags.saving_data = False
        SystemFlags.save()
       

    else:
        subnet.max_driving_time += 240
        subnet.save()

        if subnet.max_driving_time <= 600:
            json_str = simplejson.dumps({"result":True})
        else:
            subnet.max_driving_time = 120
            subnet.max_walking_time += 300
            subnet.save()
            if subnet.max_walking_time <= 900: 
                json_str = simplejson.dumps({"result":True})
            else:
                json_str = simplejson.dumps({"result":False})
        
    
    sim_results.save()
    return HttpResponse(json_str)

@log_traceback
def passengers_per_subnet(subnet_id):
    subnet_count = 0

    subnet = models.Subnet.objects.get(subnet_id = subnet_id)
    subnets = models.Subnet.objects.all()
    passengers = models.SurveyPassenger.objects.all()
    index = 0
    for passenger in passengers:
        print index
        index += 1
        print passenger.id
        print '-----'
        closest_start = True
        closest_end = True

        geometry, distance, time_to_midtown_start = planner_manager.get_optimal_vehicle_itinerary([passenger.start_lat,passenger.start_lng], [subnet.gateway.lat, subnet.gateway.lng]) 
        geometry, distance, time_from_midtown_start = planner_manager.get_optimal_vehicle_itinerary([subnet.gateway.lat, subnet.gateway.lng], [passenger.start_lat,passenger.start_lng])
        geometry, distance, time_to_midtown_end = planner_manager.get_optimal_vehicle_itinerary([passenger.end_lat,passenger.end_lng], [subnet.gateway.lat, subnet.gateway.lng]) 
        geometry, distance, time_from_midtown_end = planner_manager.get_optimal_vehicle_itinerary([subnet.gateway.lat, subnet.gateway.lng], [passenger.end_lat,passenger.end_lng])
        
        walking_time = planner_manager.get_optimal_walking_time([passenger.start_lat,passenger.start_lng], [subnet.gateway.lat, subnet.gateway.lng])
        if walking_time < subnet.max_walking_time:
            closest_start = False

        walking_time = planner_manager.get_optimal_walking_time([passenger.end_lat,passenger.end_lng], [subnet.gateway.lat, subnet.gateway.lng])
        if walking_time < subnet.max_walking_time:
            closest_end = False
            
                   
        for sn in subnets:
            if sn == subnet:
                continue
            geometry, distance, time_to = planner_manager.get_optimal_vehicle_itinerary([passenger.start_lat,passenger.start_lng], [sn.gateway.lat, sn.gateway.lng])
            geometry, distance, time_from = planner_manager.get_optimal_vehicle_itinerary([sn.gateway.lat, sn.gateway.lng], [passenger.start_lat,passenger.start_lng]) 
            if (time_to + time_from) < (time_to_midtown_start + time_from_midtown_start):
                closest_start = False
                break

        for sn in subnets:
            if sn == subnet:
                continue
            geometry, distance, time_to = planner_manager.get_optimal_vehicle_itinerary([passenger.end_lat,passenger.end_lng], [sn.gateway.lat, sn.gateway.lng])
            geometry, distance, time_from = planner_manager.get_optimal_vehicle_itinerary([sn.gateway.lat, sn.gateway.lng], [passenger.end_lat,passenger.end_lng]) 
            if (time_to + time_from) < (time_to_midtown_end + time_from_midtown_end):
                closest_end = False

        if closest_start or closest_end:
            subnet_count += 1

    
    print subnet_count
    return subnet_count


@log_traceback
def static_vmt_within_zone(service_id = 5):
    subnets = models.Subnet.objects.filter(active_in_study = True)

    start_time = settings.SIMULATION_START_TIME
    duration = settings.SIMULATION_LENGTH/6
    end_time = start_time + duration

    hours = int(start_time/3600)
    minutes = int((start_time - (hours*3600))/60)
    seconds = int(start_time - (minutes*60) - (hours*3600))
    start = datetime.time(hours, minutes, seconds)

    hours = int(end_time/3600)
    minutes = int((end_time - (hours*3600))/60)
    seconds = int(end_time - (minutes*60) - (hours*3600))
    end = datetime.time(hours, minutes, seconds)

    stops = models.StaticStop.objects.all()
    stop_count = stops.count()
    trips = []
    
    progress = 0
    total_vmt = 0
    trips_served = 0
    shape_dict = {}
    for stop in stops:
        progress += 1
        print 'Percent Complete Calculating Static VMT:  ' + str(100*progress/stop_count)
        for subnet in subnets:
            result, reason = views.within_coverage_area(stop.lat, stop.lng, subnet)
            if result or reason == 4:
                stoptimes = models.StopTime.objects.filter(departure_time__gte = start, departure_time__lte = end, stop = stop)
                for stoptime in stoptimes:
                    
                    if not(stoptime.trip.service_id == service_id):
                        continue
                    if not(stoptime.trip in trips):
                        trips_served += 1
                        trips.append(stoptime.trip)
                        if stoptime.trip.shape_id in shape_dict: #if we have already calculated this shape before, pull htat data from the dictionary
                            total_vmt += shape_dict[stoptime.trip.shape_id]
                        else:
                            shapes = models.Shape.objects.filter(shape_id = stoptime.trip.shape_id).order_by('shape_dist_traveled')
                            last_shape = None
                            trip_distance = 0
                            shape_idx = 0
                            shapes_count= shapes.count()
                            for shape in shapes:
                                shape_idx += 1
                                if shape_idx % 10:
                                    continue
                                result, reason = views.within_coverage_area(shape.lat, shape.lng, subnet)
                                if result or reason == 4:
                                    result = True
                                else:
                                    result = False

                                if result and last_shape:
                                    trip_distance += utils.haversine_dist([last_shape.lat, last_shape.lng], [shape.lat, shape.lng])
                                    last_shape = copy.copy(shape)
                                if (not result) and last_shape:
                                    trip_distance += utils.haversine_dist([last_shape.lat, last_shape.lng], [shape.lat, shape.lng])
                                    last_shape = None
                                if result and (not last_shape):
                                    last_shape = copy.copy(shape)
                            shape_dict[shape.shape_id] = trip_distance
                            total_vmt += trip_distance
                            print total_vmt

    print total_vmt
    print trips_served

    return total_vmt*6, trips_served*6

@log_traceback
def headway_output():
    """
    For every stop in the system, output the lat,lng, and average headway for a weekday 
    """

    lat_range = .0045/5
    lng_range = .0054/5

    import csv
    csvWriter = open('headway.csv', 'w')

    stops = models.StaticStop.objects.all()
    FiveAM = datetime.time(5,0,0)
    Midnight = datetime.time(23,59,59)
    index = 1.0
    stop_count = stops.count()
    for stop in stops:
 
        print float(index/stop_count)
        index += 1
        stoptimes = models.StopTime.objects.filter(stop = stop, departure_time__lte = Midnight, departure_time__gte = FiveAM).order_by('departure_time')
        weekday_stoptimes = []
        for st in stoptimes:
            if st.trip.route.id > 92:  #don't count rail in this
                continue
            if st.trip.service_id == 5:
                weekday_stoptimes.append(st)

        if len(weekday_stoptimes) < 2:
            continue

        first_stop = weekday_stoptimes[0].departure_time
        last_stop = weekday_stoptimes[len(weekday_stoptimes) - 1].departure_time

        lapse = last_stop.hour*3600 + last_stop.minute*60 + last_stop.second - first_stop.hour*3600 - first_stop.minute*60 - first_stop.second

        avg_headway = float(lapse)/len(weekday_stoptimes)/60
        #skip outliers
        if avg_headway > 61:
            continue

        min_lat = stop.lat - lat_range
        max_lat = stop.lat + lat_range
        min_lng = stop.lng - lng_range
        max_lng = stop.lng + lng_range

        starts_in_range = models.SurveyPassenger.objects.filter(start_lat__gte = min_lat, start_lat__lte = max_lat, start_lng__gte = min_lng, start_lng__lte = max_lng)
        ends_in_range = models.SurveyPassenger.objects.filter(end_lat__gte = min_lat, end_lat__lte = max_lat, end_lng__gte = min_lng, end_lng__lte = max_lng)
        locs_in_range = starts_in_range.count() + ends_in_range.count()

        csvWriter.write(str(stop.lat) + ',' + str(stop.lng) + ',' + str(avg_headway) + ',' + str(locs_in_range))
        csvWriter.write('\n')
    csvWriter.close()

        
