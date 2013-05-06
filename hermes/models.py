from django.db import models

class SystemFlags(models.Model):
    """
    simulation_code : unique identifier for each time a simulation is run
    """
    simulation_code = models.IntegerField(null = False, default = 0)
    simulation_set = models.IntegerField(null = True)
    #there is a need for a global seconds definition
    second = models.IntegerField(null = False, default = 0)
    
class SimulationResults(models.Model):
    """
    Each time a simulation is run, it's basic results will be stored in one of these objects
    simulation_code: unique code for this simulation, set by the systemflags
    simulation_description: string description
    
    passenger_count: total number of passenger trips started
    DRT_passenger_count: total number of passengers using DRT whose trip has started
    FRT_passenger_count: total number of passengers using FRT whose trip has started
    
    completed_passenger_count: total number of completed passenger trips
    completed_DRT_passenger_count: total number of completed passenger trips where one or more portions were DRT
    completed_FRT_passenger_count: total number of complted passenger trips where the entire trip was FRT
    
    total_DRT_time: total trip time of passengers using DRT
    total_DRT_distance: total trip distances of passengers using DRT
    total_FRT_time: total trip of passengers using static only
    total_FRT_distance:  total trip distances of passengers using static only
    
    total_DRT_vehicles: total number of DRT vehicles used
    total_DRT_VMT:  the total distance traveled by these vehicles
    total_FRT_VMT_within_zone: the total distances of FRT vehicle VMT within the DRT zone (assuming no DRT was used) during the time of the simulation

    total_hypothetical_FRT_time: total FRT time assuming that no DRT was used for any passenger (this is what we are trying to beat)
    """
    #META
    simulation_code = models.IntegerField(null = False)
    simulation_description = models.CharField(max_length = 250, null = True)
    
    #Passenger Counts
    passenger_count = models.IntegerField(null = False)
    DRT_passenger_count = models.IntegerField(null = False)
    FRT_passenger_count = models.IntegerField(null = False)
    
    completed_passenger_count = models.IntegerField(null = False)
    completed_DRT_passenger_count = models.IntegerField(null = False)
    completed_FRT_passenger_count = models.IntegerField(null = False)
    
    #Time and Distance
    total_DRT_time = models.IntegerField(null = False)
    total_DRT_distance = models.FloatField(null = False)
    total_FRT_time = models.IntegerField(null = False)
    total_FRT_distance = models.FloatField(null = False)
    
    total_DRT_vehicles = models.IntegerField(null = False)
    total_DRT_VMT = models.FloatField(null = False)
    total_FRT_VMT_within_zone = models.FloatField(null = False)

    #Hypothetical FRT Costs
    total_hypothetical_FRT_time = models.IntegerField(null = False)
   

class SurveyPassenger(models.Model):
    """
    Survey Passengesr contain start/end location as well as times of request
    These passengers are created from the survey data and are permanently stored here a source of passengers for the scripts.
    As we reach the time of request from each passenger, we create a Passenger object for the survey_passenger and create the necessary trips
    survey_id : (optional) an identifier of the survey set that this passenger was derived from
    start_lat : lat of passenger's starting location
    start_lng : lng of passenger's starting location
    end_lat : lat of passenger's ending location
    end_lng : lng of passenger's ending location
    time_of_request : the second at which the passenger will make a request.  All times are mapped from datetimes to 'seconds into simulation'.
    """
    survey_id = models.IntegerField(null = True)
    start_lat = models.FloatField(null = False)
    start_lng = models.FloatField(null = False)

    end_lat = models.FloatField(null = False)
    end_lng = models.FloatField(null = False)

    time_of_request = models.IntegerField(null = False)
    

class Passenger(models.Model):
    """
    Represents a passenger's desired trip parameters and statistics

    start_lat : Starting lat of the passenger, represented as an integer in the 101x101 simple city grid.  Bottom left corner is 0,0
    start_lng : Starting lng of the passenger
    end_lat : Ending lat of the passenger
    end_lng : ending lng of the passenger
    
    time_of_request:  The time that the passenger made the his/her request for a ride
    time_waiting_initial : The time between making the request and being picked up
    time_waiting_transfer : In the even of the transfer, the time between arriving at the destination station and being picked up
    time_riding_static : amount of time spent riding static route vehicles (e.g. trains)
    total_time : total time of entire trip
    
    simulation_code : Each time a simulation is run, assign the passengers for that simulation a specific code.
                      This way we can distinguish between passengers of the current simulation from those of previous simulations.
    """
    start_lat = models.FloatField(null = False)
    start_lng = models.FloatField(null = False)

    end_lat = models.FloatField(null = False)
    end_lng = models.FloatField(null = False)

    time_of_request = models.IntegerField(null = False)
    time_waiting_initial = models.IntegerField(null = True)
    time_waiting_transfer = models.IntegerField(null = True)
    time_riding_static = models.IntegerField(null = True)
    total_time = models.IntegerField(null = True)

    simulation_code = models.IntegerField(null = False)

class Gateway (models.Model):
    """
    A gateway is a connection between a DRT subnet and the rail or BRT network. Basically it is a rail or BRT station.
    lat : latitute of the gateway
    lng : longitude of the gateway
    gateway_id : unidque identifier of the gateway
    description : (optional) description of the gatway (e.g., Midtown Marta Station)
    """
    lat = models.FloatField(max_length = 25, null = False)
    lng = models.FloatField(max_length = 25, null = False)
    gateway_id = models.IntegerField(null = False)
    description = models.CharField(max_length = 250, null = True)

class Subnet(models.Model):
    """
    A subnet is a geographical area that defines where DARP area
    TODO: This needs to be update to handle amorphous subnet areas. Non circular and non rectangular subnets are needed to create more efficient coverage areas based on travel time.
    """

    subnet_type = models.IntegerField(null = False, default = 1)
    subnet_id = models.IntegerField(null = False)
    description = models.CharField(max_length = 255, null = True)

    #Simulations across an entire city can be time-consuming.  Deactivating this boolean will prevent trips within this subnet from being simulated, but the presense of this subnet will still be be used to when determing which subnet a passenger belongs to.
    active_in_study = models.BooleanField(null = False, default = False)

    gateway = models.ForeignKey(Gateway, null = False)

    #The maximum time a point can be away from the gateway and still be in the coverage area, measured in seconds
    max_driving_time = models.IntegerField(null = False, default = 300)
    max_walking_time = models.IntegerField(null = False, default = 300)

    #Optional
    center_lat = models.FloatField(max_length=25, null = True)
    center_lng = models.FloatField(max_length=25, null = True)

    #Optional
    #For different types of subnets, these settings have different meanings
    setting1 = models.FloatField(max_length=25, null = True)
    setting2 = models.FloatField(max_length=25, null = True)
    setting3 = models.FloatField(max_length=25, null = True)
    setting4 = models.FloatField(max_length=25, null = True)

    ######Everything below is antiquainted
    #For Type 0
    high_lat = models.FloatField(max_length=25, null = True)
    high_lng = models.FloatField(max_length=25, null = True)
    low_lat = models.FloatField(max_length=25, null = True)
    low_lng = models.FloatField(max_length=25, null = True)

    ###radius is measured in miles
    radius = models.FloatField(null = True, default = 2)


class FlexBus(models.Model):
    """
    A flex bus is a bus with a flexible route.  Each bus will be given a physical boundary in which in can travel
    
    vehicle_id : unique identifier for the vehicle
    subnet : the subnet to which the vehicle is assigned
    """

    vehicle_id = models.IntegerField(null = False)
    subnet = models.ForeignKey(Subnet, null = False)

class TripSegment(models.Model):
    """
    Each Passenger's trip may be divided into multiple segments.  These objects represent those segments
    passenger:  ForeignKey to the passenger to whom this tripsegment belongs

    static : booleanfield, if it is set to true this is a static trip segment, otherwise it is DRT
    flexbus:  ForeignKey to the flexbus serving this tripsegment

    start_time: the time the trip_segment started or is scheduled to start
    end_time:  the time the trip_segment ended or is scheduled to end

    earliest_start_time:  the earliest time the segment can begin.  This is either the time that passenger requested a trip or the time of arrival at a transfer point

    status: the status of this trip 0: no van has been assigned, 1: trip is assigned to a van but not yet into the algorithm 2: trip has been inserted and start/end times have been assigned.

    trip_sequence: The order that these trips are visited.  0 is first leg, 1 is second leg, 2 is third leg. For the simple city, there will only be at most two legs
    """
    passenger = models.ForeignKey(Passenger, null = False)

    static = models.BooleanField(null = False, default = False)
    flexbus = models.ForeignKey(FlexBus, null = True)

    start_time = models.IntegerField(null = True)
    end_time = models.IntegerField(null = False, default = 1000000) #TODO: Set this to double the length of the simulation or find a better solution
    
    #Earliest start time is the earliest time this tripsegment can begin
    #the time is measured in seconds from the simulation start time
    earliest_start_time = models.IntegerField(null = True) #, default =1000000) # TODO: set this to double the length of the simulation 

    #Status:
    #0:  This trip has not been assigned a van
    #1:  This trip has been assigend a van, but not yet inserted into the algorithm
    #2:  This trip has been inserted into the schedule and start/end times have been assigned.
    status = models.IntegerField(null = False, default = 0)
    
    start_lat = models.FloatField(null = False)
    start_lng = models.FloatField(null = False)

    end_lat = models.FloatField(null = False)
    end_lng = models.FloatField(null = False)
  
    #These are for book-keeping purposes.  All times are in seconds.
    walking_time = models.IntegerField(null = True)
    waiting_time = models.IntegerField(null = True)
    riding_time = models.IntegerField(null = True)
      
    trip_sequence = models.IntegerField(null = False, default = 0)

class Stop(models.Model):
    """
    The stops that make up the schedule of the vehicle.  These are subject to change, because it is flexible
    flexbus : foreignkey to the bus visiting this stop
    lat : the latitude of the stop
    lng : the longitude of the stop
    sequence : The order in which the stop is visited
    visit_time : The time that the stop was visited, or is scheduled to be visited
    trip : foreignkey to the trip that this stop was created to handle.
    stop_type : the type of stop this is, dropoff or pickup
    """
    flexbus = models.ForeignKey(FlexBus, null = False)
    lat = models.FloatField(null = False)
    lng = models.FloatField(null = False)
    sequence = models.IntegerField(null = False)
    visit_time = models.IntegerField(null = False)
    trip = models.ForeignKey(TripSegment, null = True)
    #Type: 1 = pickup, 2=dropoff
    type = models.IntegerField(null = False, default = 0)

class FencePost(models.Model):
    """
    This is where the geofences around each gateway are created
    Each gatewaby has a set of ordered fencePosts that make up the perimeter 
    lat : float, latitude of FencePost
    lng : float, longitude of FencePost
    gateway : foreignkey to the gateway that this FencePost belongs to
    sequence : int, sequence of this fencepost
    """
    lat = models.FloatField(null = False)
    lng = models.FloatField(null = False)
    gateway = models.ForeignKey(Gateway, null = True)
    sequence = models.IntegerField(null = False)

################################
## These models below hold GTFS data for calcularing Static VMT
################################

class Route(models.Model):
    route_id = models.IntegerField(null = False)
    short_name = models.CharField(max_length = 100, null = True)
    long_name = models.CharField(max_length = 250, null = True)

class Shape(models.Model):
    shape_id = models.IntegerField(null = False)
    lat = models.FloatField(null = False)
    lng = models.FloatField(null = False)
    sequence = models.IntegerField(null = False)
    shape_dist_traveled = models.FloatField(null = False)

class StaticStop(models.Model):
    stop_id =  models.IntegerField(null = False)
    stop_name = models.CharField(max_length = 100, null = True)
    lat = models.FloatField(null = False)
    lng = models.FloatField(null = False)

class Trip(models.Model):
    trip_id = models.IntegerField(null = False)
    service_id = models.IntegerField(null = True)
    route = models.ForeignKey(Route, null = True)
    headsign = models.CharField(max_length = 100, null = True)
    block_id = models.IntegerField(null = True)
    shape_id = models.IntegerField(null = False)
    
class StopTime(models.Model):
    trip = models.ForeignKey(Trip, null = True)
    arrival_time = models.TimeField(null = False)
    departure_time = models.TimeField(null = False)
    stop = models.ForeignKey(StaticStop, null = True)
    stop_sequence = models.IntegerField(null = True)
    shape_dist_traveled = models.FloatField(null = False)

#######################
# This Model is used in the Particle Swarm Optimizer.  It is referenced in the Results section
######################
class Particle(models.Model):
    """
    This is a model for the particles used in the Particle Swarm Optimizer
    Each particle used to find the optimum inner and outer boundaries for the service areas.
    particle_id : an integer id identfying each particle.  The particles will be analyzed one-by-one in order of the particle_id
    simulation_set : there is a simulation code for each simulation.  A simulation set is an id associated with many simulation codes 
    simulation_code : sim code from the sytems flags
    step : which stop in the optmization process this was step = 0,1,2,...,n
    cost : total cost or fitness of this simulation
    best_cost : the best cost so far
    x1 : outer boundary value (for isochrones this is measured in seconds)
    x2 : inner boundary value (for isochrones this is measured in seconds)
    v1 : outer boundary velocity
    v2 : inner boundary velocity
    """
    particle_id = models.IntegerField(null = False)
    simulation_set = models.IntegerField(null = False)
    simulation_code = models.IntegerField(null = False)
    step = models.IntegerField(null = False, default = 0)
    cost = models.FloatField(null = True)
    best_cost = models.FloatField(null = True)
    x1 = models.FloatField(null = False)
    x2 = models.FloatField(null = False)
    v1 = models.FloatField(null = False, default = 0.0)
    v2 = models.FloatField(null = False, default = 0.0)


class SimulationResult(models.Model):
    """
    For each simulation, store some basic results about that simulation
    description : a string identifying the purpose/settings of this simulation
    timestamp : when did the simulation finish?
    simulation_code : code from system flags
    simulation_set : to which set of simulations does this belong?  It is a part of the Particle Swarm Optimizer
    starte_trips : number of trips started
    completed_trips : number of trips with assigned finish times
    drt_time_avg : average time of all trips with assigned finish times that use DRT for any portion of the trip
    frt_time_avg : if the above drt trips where to use FRT only, what is that average time?
    average_distance : straight line distance between point A and B for each passenger
    total_DRT_VMT : total VMT of all FlexBuses
    total_FRT_VMT_saved : total VMT of all static buses that run within the coverage area
    total_DRT_vehicles_used : total number of DRT vehicles needed

    total_net_cost : passenger_time_value*completed_trips*(FRT_time_avg - DRT_time_avg) + (DRT_vmt_value*total_FRT_VMT_saved - DRT_vmt_value*total_DRT_VMT)
    """
    description = models.CharField(max_length = 100, null = False)
    timestamp = models.DateTimeField(null = False)
    simulation_code = models.IntegerField(null = False)
    simulation_set = models.IntegerField(null = True)
    
    started_trips = models.IntegerField(null = False)
    completed_trips = models.IntegerField(null = False)
    DRT_time_avg = models.FloatField(null = False) #measured in seconds
    FRT_time_avg = models.FloatField(null = False) #measured in seconds
    average_distance = models.FloatField(null = False) #measured in meters
    total_DRT_VMT  = models.FloatField(null = False) #measured in meters
    total_FRT_VMT_saved = models.FloatField(null = False) #measured in meters
    total_DRT_vehicles_used = models.IntegerField(null = False)

    total_net_cost = models.FloatField(null = False)
