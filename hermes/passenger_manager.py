import random, math, datetime

from extra_utils.variety_utils import log_traceback
from django.utils import simplejson
from django.http import HttpResponse
from django.db import connection

from NITS_CODE import settings
from hermes import models, views

@log_traceback
def get_passengers(request):
    """
    Get Passengers finds passengers that are available at the current second.  The second is encapsulated in the request
    if we are using survey passengers, we pull the passengers from a predefiend and preloaded list
    if we are generating passenger data we randomly create passenger locations
    @param request is a POST request containing the current second count and if we are generating passengers, it also contains the probability that a passenger will be created
    """
    if settings.USE_SURVEY_PASSENGERS:
        return get_survey_passengers(request)
    else:
        return generate_passengers(request)

@log_traceback
def get_survey_passengers(request):
    """
    Use this to pull passengers from the survey data.  The trips must first be loaded into the db using the Trip Load Script.
    This function will create the passenger objects and trip objects needed for each passenger
    @param request contains the simulation code and the second count into the simulation
    @return json object containing trips count, the second, and the trip ids to be inserted
    """
    simulation_code = int(request.POST['simulation_code'])
    second = int(request.POST['second'])

    ready = False
    while(not ready and second <= settings.SIMULATION_LENGTH):
        
        #Pull Passengers at this second
        passengers = models.SurveyPassenger.objects.filter(time_of_request = second)
    
        for passenger in passengers:
        
            new_passenger = models.Passenger.objects.create(start_lat=passenger.start_lat, start_lng=passenger.start_lng, end_lat=passenger.end_lat, end_lng=passenger.end_lng, simulation_code = simulation_code, time_of_request = second)
            new_passenger.save()

            ###########################
            ## Create Trips for these passengers
            ###########################
            views.create_trips(new_passenger, second)

            ##############
            ##This has been moved from script
            ##############
            ready_trips = models.TripSegment.objects.filter(earliest_start_time__lte = second, status = 1)
            if ready_trips:
                ready = True
                for trip in ready_trips:
                    if trip.static:
                        views.optimize_static_route(second, trip)
                    else:
                        flexbus, stop_array = views.insert_trip(second, trip)
                        order = views.simple_convert_sequence_to_locations(flexbus, second, stop_array)
            ##############

        if not ready:
            second += 1

    ### Check to see if trips are ready to be inserted.  Any passengers created above will have trips here
    ### This will also pull trips that were created earlier but weren't ready to be inserted
    ### If not trips or passengers are ready at this second, increment the second and keep looking for trips in the future
        #ready_trips = models.TripSegment.objects.filter(earliest_start_time__lte = second, status = 1)
        #trips_array = []
        #if ready_trips:
        #    ready = True
        #    for trip in ready_trips:
        #        trips_array.append(trip.id);
        #else:
        #    second += 1
            
        trips_array = [2,4,3]


    json_str = simplejson.dumps({"passengers":passengers.count(), "second":second, "ready_trips":trips_array})
    return HttpResponse(json_str)



@log_traceback
def generate_passengers(request):
    """
    this is currently set to handle creating passengers without a survey
    this function is currently not used and may need to be updated
    TODO:  This function contains a lot of hardcodes specific to MARTA.  Those need to be made generic.
    @param request containing the seconds into the simulation, the simulation code, and the rate at which passengers are created
    @return json object containing trips count, the second, and the trip ids to be inserted
    """
    #this generate passengers needs to be replaced with the MARTA SURVEY GENERATOR
    passengers_per_second = float(request.POST['passengers_per_second'])
    simulation_code = int(request.POST['simulation_code'])
    second = int(request.POST['second'])
    ##########################
    ##  Generate Passengers
    ##########################
    ready_trips = models.TripSegment.objects.filter(earliest_start_time__lte = second, status = 1)
    for trip in ready_trips:
        trip.delete()

    ready = False
    while(not ready):
    # Determines how many (if any) passengers to create
        random_num = random.random()
        if passengers_per_second < 1:
            if random_num > (1-passengers_per_second):
                passengers = 1
            else:
                passengers = 0
        else:
            passengers = round((passengers_per_second*2)*random_num)


    #Decide the locations for the passengers
        for passenger in range(passengers):
           # import pdb;pdb.set_trace()    
            subnets = models.Subnet.objects.all()
            origin_subnet_id = int(random.random()*subnets.count())
            destination_subnet_id = int(random.random()*subnets.count())

            origin_subnet = models.Subnet.objects.get(subnet_id = n)
            m = n + 19
            if(m > 38):
                m = m - 38
            destination_subnet = models.Subnet.objects.get(subnet_id = m)

            #Create radius coordinate for passneger with respect to the subnet center
            origin_magnitude = random.random()*origin_subnet.radius*(.017325)*.5 #Hack this is only for ATL's lat
            dest_magnitude = random.random()*destination_subnet.radius*(.017325)*.5
            origin_angle = random.random()*2.0
            dest_angle = random.random()*2.0
            
            #convert radians to cartesian coordiats in lat/lng
            px = float(origin_subnet.center_lng) + (origin_magnitude*math.cos(origin_angle*math.pi))
            py = float(origin_subnet.center_lat) + (origin_magnitude*math.sin(origin_angle*math.pi))
            dx = float(destination_subnet.center_lng) + (dest_magnitude*math.cos(dest_angle*math.pi))
            dy = float(destination_subnet.center_lat) + (dest_magnitude*math.sin(dest_angle*math.pi))

            new_passenger = models.Passenger.objects.create(start_lat=py, start_lng=px, end_lat=dy, end_lng=dx, simulation_code = simulation_code, time_of_request = second)
            new_passenger.save()

        ###########################
        ## Create Trips for these passengers
        ###########################
            views.get_candidate_vehicles(new_passenger, second)

        ### Check to see if trips are ready to be inserted.  Any passengers created above will have trips here
        ready_trips = models.TripSegment.objects.filter(earliest_start_time__lte = second, status = 1)
        trips_array = []
        if ready_trips:
            ready = True
            for trip in ready_trips:
                trips_array.append(trip.id);
        else:
            second += 1

        
    json_str = simplejson.dumps({"passengers":passengers, "second":second, "ready_trips":trips_array})
    return HttpResponse(json_str)


@log_traceback
def insert_survey_passengers(file_path):
    """
    TODO: Move this to an external script
    This function takes a file path containing a large set of passenger data and loads that passenger data into the survey_passenger table
    @param string file_path : the path to the csv file containing passenger data
    """
    cursor = connection.cursor()
    fp = open(file_path)
    line = fp.readline()
    index_str = ''
    insert_str = "insert into hermes_surveypassenger(survey_id, start_lat, start_lng, end_lat, end_lng, time_of_request) values "
    values_str = '(%s,"%s","%s","%s","%s",%s),'

    cnt = 0
    values = ''
    while line:
        line = fp.readline()
        if line:
            cnt += 1
            line = line.strip("\r\n").replace('"', '').split(",")

            start_hour = int(line[1])
            start_minute = int(line[2])
            second = (start_hour - 7)*3600 + start_minute*60
            values += values_str % (line[0], line[4], line[5], line[7], line[8] ,second)
            
            if cnt >= 100:
                try:
                    if insert_str:
                        cursor.execute(insert_str + values.rstrip(",")+";")
                        
                except Warning:
                    pass
                cnt = 0
                values = ""
        else:
            try:
                if insert_str:
                    cursor.execute(insert_str + values.rstrip(",")+";")    
            except Warning:
                pass
      
    cursor.close()
    fp.close()
    return



@log_traceback
def load_survey_passengers():
    """
    TODO: Move to a separate script
    This function calls the function to load survey passengers.
    """
    insert_survey_passengers(settings.SURVEY_PASSENGER_FILE)
    return True
