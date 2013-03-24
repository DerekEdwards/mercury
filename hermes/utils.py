import math
import time

from hermes import models

EARTH_RADIUS = 6372800 #in meters
def haversine_dist(start, end):
    """
    The code for this function was taken from http://rosettacode.org/wiki/Haversine_formula on March 24, 2013
    ---------------
    This function returns the straight line distane between two lat,lng points.
    @param start : [start lat, start lng]
    @param end : [end lat, end lng]
    @returns : the distance between these two points given in meters
    """
    
    lat1 = start[0]
    lon1= start[1]
    lat2 = end[0]
    lon2 = end[1]
    
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
 
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.sin(dLon / 2) * math.sin(dLon / 2) * math.cos(lat1) * math.cos(lat2)
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS * c

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

def get_shape_distance(shapes):
    """
    Given an array of lat, lngs, return the total length of the array
    @param shapes : array of shape points
    @return : float representing the length of the shape in meters 
    """
    return 0
    
