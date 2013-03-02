from hermes import models
from math import sin, cos, pi, atan2, sqrt
#from googlemaps import GoogleMaps
import time

#gmaps = GoogleMaps('ABQIAAAAsn6aAGbw79H9E1JOWbQQjhSlVGwKjeu8iET79lxLMDKkElrCQBTD0ANguvwut7gCuc8I7Es8GyfDiQ')
EARTH_RADIUS = 6371000 #in meters


def haversine_dist(start, end):
    """
    Finds the straight line distance between two points in meters. 
    """
    dlat = to_rad(end[0] - start[0])
    dlon = to_rad(end[1] - start[1])

    tmp_dist = sin(dlat/2)*sin(dlat/2) + cos(to_rad(start[0]))*cos(to_rad(end[1]))*sin(dlon/2)*sin(dlon/2)
    tmp_dist = 2*atan2(sqrt(tmp_dist), sqrt(1-tmp_dist))
    tmp_dist *= EARTH_RADIUS
    return tmp_dist

def to_rad(deg):
    return deg*pi/180

def to_deg(rad):
    return rad*180/pi

def get_google_distance(lat1, lng1, lat2, lng2):
    
    return 10000
    time.sleep(.5)
    st = (lat1, lng1)
    end = (lat2, lng2)
    #dirs = gmaps.directions(st, end)
    total_seconds = 0
    if dirs:
        steps = dirs['Directions']['Routes'][0]['Steps']
        for step in steps:
            total_seconds += float( step['Duration']['seconds'])

    return total_seconds
