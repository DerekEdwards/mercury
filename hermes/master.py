from django.utils import simplejson
from django.http import HttpResponse
from extra_utils.variety_utils import log_traceback

from NITS_CODE import settings
from hermes import models, passenger_manager
from hermes import load_gateways, particle_swarm_manager


@log_traceback
def clear_data():
    """
    This function is called to clear survey_passenger data, passengers_in_transit, all trips, stops, vehicles and gateways from the db.
    The difference between survey_passengers and passengers is that survey passengers represent only the start, end, and trip time for passengers collected from asurvey.  The passenger field is created for passengers after they have made a request.
    """
     
    if settings.DELETE_SURVEY_PASSENGERS:
        survey_passengers = models.SurveyPassenger.objects.all()
        survey_passengers.delete()
    passengers = models.Passenger.objects.all()
    passengers.delete()
    trips = models.TripSegment.objects.all()
    trips.delete()
    stops = models.Stop.objects.all()
    stops.delete()
    vehicles = models.FlexBus.objects.all()
    vehicles.delete()
    gateways = models.Gateway.objects.all()
    gateways.delete()

@log_traceback
def create_gateways():
    """
    This function loads in the train station gateways from a list of lat,lngs
    """
    load_gateways.main()

@log_traceback
def create_subnets():
    """
    This is where the demand responsive subnets are created.
    Currently the Gateways are preloaded (one for each marta rail station)
    TODO: For future research, this is where the amorphous subnets will be created.  It will likely require a schema change to handle this.
    """
    gateways = models.Gateway.objects.all()
    print 'There are ' + str(gateways.count()) + ' rail stations.'
    
    for gateway in gateways:
        subnet,created = models.Subnet.objects.get_or_create(gateway = gateway, subnet_id = gateway.gateway_id)
        subnet.description = gateway.description + ' SUBNET'
        subnet.center_lat = gateway.lat
        subnet.center_lng = gateway.lng
        if created:
            subnet.max_driving_time = settings.DEFAULT_MAX_DRIVING_TIME
            subnet.max_walking_time = settings.DEFAULT_MAX_WALKING_TIME
        
        #8 is midtown, 21 is chamblee, 20 is doraville
        if subnet.subnet_id == 20:
            subnet.active_in_study = True
            particle = particle_swarm_manager.get_current_particle()
            subnet.max_driving_time = particle.x1
            subnet.max_walking_time = particle.x2
        subnet.radius = 2
        subnet.save()
        
@log_traceback
def create_busses():
    """
    This function creates 4 buses for each subnet.  
    TODO:  Why four buses?  
    """
    subnets = models.Subnet.objects.filter(active_in_study = True)
    id = 1
    for subnet in subnets:
        for i in range(1):
            flexbus, created = models.FlexBus.objects.get_or_create(vehicle_id = id, subnet = subnet)
            id += 1

@log_traceback
def initialize_simulation(request):
    """
    This function clears data from previous simulations, creates the gateways from a list, creates circular subnets, and creates a bus for each subnet
    This simulation code is also updated here.
    TODO:  This function could use some GUI action.  Settings like which subnets are active, which gateways to use, size of the iscrhones etc. should be set via gui
    """
    #Update the simulation code
    SystemFlags = models.SystemFlags.objects.all()
    SystemFlags = SystemFlags[0]
    simulation_code = SystemFlags.simulation_code
    simulation_code += 1
    SystemFlags.simulation_code = simulation_code
    SystemFlags.saving_data = False
    SystemFlags.second = 0
    SystemFlags.save()

    print 'Clearing Data...'
    clear_data()

    if settings.USE_PSO:
        print 'Initializing Particles'
        #particle_swarm_manager.initialize_particles()

    print 'Creating Gateways...'
    create_gateways()
    print 'Creating Subnets...'
    create_subnets()
    print 'Creating Busses...'
    create_busses()
    if settings.USE_SURVEY_PASSENGERS and settings.DELETE_SURVEY_PASSENGERS:
        print 'Uploading Survey Passengers'
        passenger_manager.load_survey_passengers()
        print 'Done loading survey passengers' 
        if settings.PRESCREEN_PASSENGERS: 
            passenger_manager.prescreen_passengers()

    
    json_str = simplejson.dumps({"simulation_code":simulation_code, "simulation_length":settings.SIMULATION_LENGTH})
    return HttpResponse(json_str)

 
