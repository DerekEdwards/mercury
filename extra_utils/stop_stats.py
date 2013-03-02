from NITS.hermes import models
from NITS.hermes import views
from NITS.hermes import analyzer
import random, datetime

def find_stats(subnet, stops):
    distance = 1609 #this is one mile measured in meters
    stops_in_range = []
    for stop in stops:
        distance = analyzer.haversine_dist([stop.lat, stop.
           
if __name__ == "__main__":

 #   create_busses()
    now = datetime.datetime.now()
    #subnets = models.Subnet.objects.all().order_by('id')
    stops = models.Stop.objects.all()
    
    for subnet in subnets:
        find_stats(subnet, stops)
    
    print s
