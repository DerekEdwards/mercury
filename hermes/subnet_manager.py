from hermes import models
from hermes import utils
from NITS_CODE import settings

###Subnet Types
#1: disc, setting1 = radius
#2: donut, setting1 = outer radius, setting2 = inner radius
#3: subscription subnet: (Not yet built)

def get_subnet_candidates(passenger):
    """
    TODO: This function will be used to determine if/which subnet a passenger belongs to.  It will be necessary for the upcoming amorphous subnet change
    This is the main function for this manager. It is used to find all the potential subnets for a passengers start and end location
    @input : passenger object
    @return : tuple [start_subnet_candidates, end_subnet_candidates]
    """
    start_subnet_candidates = []
    end_subnet_candidates = []
    subnets = models.Subnet.objects.all()
    for subnet in subnets:
        
        ######## Check for each type of subnet #####
        if subnet.subnet_type == 1: #This is a classic disc subnet
            #Check start location
            distance = utils.haversine_dist([float(subnet.center_lat), float(subnet.center_lng)], [float(passenger.start_lat), float(passenger.start_lng)])
            if distance <= subnet.setting1:
                start_subnet_candidates.append(subnet)
            #Check end location
            distance = utils.haversine_dist([float(subnet.center_lat), float(subnet.center_lng)], [float(passenger.end_lat), float(passenger.end_lng)])
            if distance <= subnet.setting1:
                end_subnet_candidates.append(subnet)


    return start_subnet_candidates, end_subnet_candidates



